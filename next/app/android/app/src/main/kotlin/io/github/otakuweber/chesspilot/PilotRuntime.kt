package io.github.otakuweber.chesspilot

import android.content.Context
import org.json.JSONObject
import java.io.File

/** Process owner survives Activity recreation; process death always starts stopped. */
object PilotRuntime {
    private var session: Long? = null
    @Volatile var captureEpoch = 0L
    @Volatile var platformError: String? = null
    @Volatile var dashboardVisible = false
    private var initialization = JSONObject()

    @Synchronized fun connect(context: Context): String {
        if (session == null) {
            // App-private storage is provided explicitly; Android has no desktop HOME/XDG root.
            val logging=JSONObject(PlatformBridge.request(JSONObject().put("command","configure_diagnostics")
                .put("log_dir",File(context.filesDir,"logs").absolutePath).toString()))
            if(!logging.optBoolean("ok")) platformError="File logging unavailable: ${logging.optString("error") }"
            session = envelope(JSONObject().put("command", "open")).getLong("session")
            val directory = File(context.filesDir, "native").apply { mkdirs() }
            val model = File(directory, "chess_detection.onnx")
            try {
                if (!model.isFile) {
                    val temporary = File(directory, "model.part")
                    context.assets.open("chess_detection.onnx").use { input ->
                        temporary.outputStream().use { output -> input.copyTo(output) }
                    }
                    check(temporary.renameTo(model)) { "Cannot install chess detection model" }
                }
            } catch (error: Exception) {
                platformError = "Chess detection model unavailable: ${error.message}"
            }
            val native = context.applicationInfo.nativeLibraryDir
            val config = File(context.filesDir, "engine_config.txt")
            if (!config.exists()) config.writeText(
                "# ChessPilot Engine Configuration\nsetoption name Hash value 128\nsetoption name Threads value 2\n"
            )
            initialization = JSONObject()
                .put("engine_path", "$native/libstockfish.so")
                .put("model_path", model.absolutePath)
                .put("runtime_path", "$native/libonnxruntime.so")
                .put("config_path", config.absolutePath)
            if (!File(native, "libstockfish.so").isFile) {
                platformError = "Android Stockfish is missing from this build"
            }
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
        if (visible && captureEpoch!=0L && session!=null) command("stop")
    }
    fun stopCapture(reason: String) {
        val epoch = captureEpoch
        captureEpoch = 0
        if (epoch != 0L) PlatformBridge.invalidate(epoch, reason)
        platformError = reason
        if (session != null) command("capture_lost", JSONObject().put("reason", reason))
    }
    fun status(): Map<String, Any?> = mapOf(
        "touch" to (PilotTouchService.current != null),
        "capture" to (captureEpoch != 0L),
        "error" to platformError,
    )
}
