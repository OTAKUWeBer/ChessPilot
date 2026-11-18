package io.github.otakuweber.chesspilot

import android.content.Context
import org.json.JSONObject
import java.io.File

/** Process owner survives Activity recreation; process death always starts stopped. */
object PilotRuntime {
    @Volatile private var session: Long? = null
    @Volatile private var closing = false
    @Volatile var captureEpoch = 0L
    @Volatile var platformError: String? = null
    @Volatile var dashboardVisible = false
    private var initialization = JSONObject()

    @Synchronized fun connect(context: Context): String {
        check(!closing) { "ChessPilot is stopping. Open it again in a moment." }
        if (session == null) {
            // App-private storage is provided explicitly; Android has no desktop HOME/XDG root.
            val logging=JSONObject(PlatformBridge.request(JSONObject().put("command","configure_diagnostics")
                .put("log_dir",File(context.filesDir,"logs").absolutePath).toString()))
            if(!logging.optBoolean("ok")) platformError="File logging unavailable: ${logging.optString("error") }"
            val directory = File(context.filesDir, "native").apply { mkdirs() }
            installPackagedAsset(File(directory,"nn-1a298aa575a0.nnue"),"1a298aa575a085434d29027978dc36867fe9c5bcea9376654b7a8eba1e52dfc2") {
                context.assets.open("networks/nn-1a298aa575a0.nnue")
            }
            val model = File(directory, "chess_detection.onnx")
            try {
                val expected = context.assets.open("chess_detection.onnx.sha256").bufferedReader().use { it.readText().trim() }
                installPackagedAsset(model,expected) { context.assets.open(model.name) }
            } catch (error: Exception) {
                platformError = "Chess detection model unavailable: ${error.message}"
                throw IllegalStateException(platformError, error)
            }
            val native = context.applicationInfo.nativeLibraryDir
            val features=logging.optJSONObject("result")?.optJSONObject("system")?.optJSONArray("cpu_features")
            val dotprod=features!=null && (0 until features.length()).any { features.optString(it)=="dotprod" }
            val engine=if(dotprod) "libstockfish_dotprod.so" else "libstockfish.so"
            val config = File(context.filesDir, "engine_config.txt")
            if (!config.exists()) config.writeText(
                "# ChessPilot Engine Configuration\nsetoption name Hash value 128\nsetoption name Threads value 2\n"
            )
            initialization = JSONObject()
                .put("engine_path", "$native/$engine")
                .put("fallback_engine_path", "$native/libstockfish.so")
                .put("engine_working_directory",directory.absolutePath)
                .put("model_path", model.absolutePath)
                .put("runtime_path", "$native/libonnxruntime.so")
                .put("config_path", config.absolutePath)
            if (!File(native, engine).isFile) {
                platformError = "Android Stockfish is missing from this build"
            }
            session = envelope(JSONObject().put("command", "open")).getLong("session")
        }
        return JSONObject()
            .put("session", session)
            .put("state", command("status").getJSONObject("state"))
            .put("resources", initialization)
            .put("platform", JSONObject(status())).toString()
    }
    private fun envelope(request: JSONObject): JSONObject {
        val reply = JSONObject(PlatformBridge.request(request.toString()))
        check(reply.optBoolean("ok")) { reply.optString("error", "Native operation failed") }
        return reply.getJSONObject("result")
    }
    @Synchronized fun command(name: String, values: JSONObject = JSONObject()): JSONObject {
        val id = checkNotNull(session) { "Open ChessPilot before starting automation" }
        values.put("command", name).put("session", id)
        return envelope(values)
    }
    fun initializeCapture() {
        val copy = synchronized(this) { JSONObject(initialization.toString()) }
        command("initialize_capture", copy)
    }
    fun dashboard(visible: Boolean) {
        dashboardVisible=visible
        if (visible && !closing && captureEpoch!=0L && session!=null) command("stop")
    }
    @Synchronized fun stopCapture(reason: String) {
        val epoch = captureEpoch
        captureEpoch = 0
        if (epoch != 0L) PlatformBridge.invalidate(epoch, reason)
        platformError = reason
        if (session != null) command("capture_lost", JSONObject().put("reason", reason))
    }
    @Synchronized fun exit(context: Context, done: (String?) -> Unit = {}) {
        if (closing) { done(null); return }
        closing = true
        val id = session
        stopCapture("ChessPilot stopped")
        session = null
        context.stopService(android.content.Intent(context, ProjectionService::class.java))
        Thread({
            val error = runCatching {
                if (id != null) envelope(JSONObject().put("command", "close").put("session", id))
                synchronized(this) { initialization = JSONObject() }
            }.exceptionOrNull()
            if (error != null) synchronized(this) { session = id }
            closing = false
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                if (error != null) {
                    platformError = "Could not stop ChessPilot: ${error.message}"
                    done(platformError)
                } else {
                    done(null)
                    context.getSystemService(android.app.ActivityManager::class.java).appTasks.forEach { it.finishAndRemoveTask() }
                }
            }
        }, "ChessPilot shutdown").start()
    }
    fun status(): Map<String, Any?> = mapOf(
        "touch" to (PilotTouchService.current != null),
        "capture" to (captureEpoch != 0L),
        "error" to platformError,
    )
}
