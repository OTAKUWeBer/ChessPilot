package io.github.otakuweber.chesspilot

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

/** Process owner survives Activity recreation; process death always starts stopped. */
object PilotRuntime {
    private var session: Long? = null
    @Volatile var captureEpoch = 0L
    @Volatile var platformError: String? = null
    @Volatile var dashboardVisible = false
    private var initialization = JSONObject()

    private fun installNetwork(context: Context, directory: File, name: String, expected: String) {
        fun digest(file: File): String {
            val hash=MessageDigest.getInstance("SHA-256")
            file.inputStream().use { input ->
                val buffer=ByteArray(65536)
                while(true) { val size=input.read(buffer);if(size<0) break;hash.update(buffer,0,size) }
            }
            return hash.digest().joinToString("") { "%02x".format(it) }
        }
        val target=File(directory,name)
        if(target.isFile && digest(target)==expected) return
        val temporary=File(directory,"$name.part")
        try {
            context.assets.open("networks/$name").use { input ->
                temporary.outputStream().use { output -> input.copyTo(output);output.fd.sync() }
            }
            check(digest(temporary)==expected) { "Invalid packaged Stockfish network: $name" }
            check(temporary.renameTo(target)) { "Cannot install Stockfish network: $name" }
        } finally { temporary.delete() }
    }

    @Synchronized fun connect(context: Context): String {
        if (session == null) {
            // App-private storage is provided explicitly; Android has no desktop HOME/XDG root.
            val logging=JSONObject(PlatformBridge.request(JSONObject().put("command","configure_diagnostics")
                .put("log_dir",File(context.filesDir,"logs").absolutePath).toString()))
            if(!logging.optBoolean("ok")) platformError="File logging unavailable: ${logging.optString("error") }"
            val directory = File(context.filesDir, "native").apply { mkdirs() }
            installNetwork(context,directory,"nn-1c0000000000.nnue","1c0000000000a67d629999d932d0c373f7450ce43cd12d0562868f4eaf9ae2ad")
            installNetwork(context,directory,"nn-37f18f62d772.nnue","37f18f62d772f3107e1d6aaca3898c130c3c86f2ab63e6555fbbca20635a899d")
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
