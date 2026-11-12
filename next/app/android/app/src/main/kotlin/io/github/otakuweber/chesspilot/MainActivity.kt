package io.github.otakuweber.chesspilot

import android.app.Activity
import android.content.Intent
import android.media.projection.MediaProjectionConfig
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.provider.Settings
import android.Manifest
import android.content.pm.PackageManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var consentPending = false
    override fun onResume() { super.onResume();PilotRuntime.dashboard(true) }
    override fun onPause() { PilotRuntime.dashboard(false);super.onPause() }
    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)
        MethodChannel(engine.dartExecutor.binaryMessenger, "chesspilot/android").setMethodCallHandler { call, result ->
            try {
                when (call.method) {
                    "connect" -> result.success(PilotRuntime.connect(applicationContext))
                    "status" -> result.success(PilotRuntime.status())
                    "shareLogs" -> {
                        val reply=org.json.JSONObject(PlatformBridge.request(org.json.JSONObject().put("command","diagnostics").put("include_tail",true).toString()))
                        check(reply.optBoolean("ok")) {reply.optString("error")}
                        val details=reply.getJSONObject("result")
                        val folder=java.io.File(cacheDir,"diagnostics").apply{mkdirs()}
                        val file=java.io.File(folder,"chesspilot-diagnostics.txt")
                        file.writeText("ChessPilot diagnostics\n${details.getJSONObject("system").toString(2)}\nFile logging: ${details.optString("write_error")}\nDropped file records: ${details.optLong("dropped_records")}\n\n${details.optString("tail")}")
                        val uri=androidx.core.content.FileProvider.getUriForFile(this,"$packageName.diagnostics",file)
                        val send=Intent(Intent.ACTION_SEND).setType("text/plain")
                            .putExtra(Intent.EXTRA_STREAM,uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        send.clipData=android.content.ClipData.newRawUri("ChessPilot recent logs",uri)
                        startActivity(Intent.createChooser(send,"Share recent ChessPilot logs"))
                        result.success(null)
                    }
                    "enableTouch" -> {
                        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                        result.success(null)
                    }
                    "startCapture" -> {
                        check(PilotTouchService.current != null) { "Enable ChessPilot touch control in Accessibility first" }
                        check(!consentPending && PilotRuntime.captureEpoch == 0L) { "Capture is already starting or active" }
                        consentPending = true
                        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 902)
                        } else requestCaptureConsent()
                        result.success(null)
                    }
                    "stopCapture" -> {
                        PilotRuntime.stopCapture("Screen sharing stopped")
                        stopService(Intent(this, ProjectionService::class.java))
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            } catch (error: Exception) { result.error("android_setup", error.message, null) }
        }
    }
    private fun requestCaptureConsent() {
        try {
            val manager = getSystemService(MediaProjectionManager::class.java)
            val intent = if (Build.VERSION.SDK_INT >= 34) manager.createScreenCaptureIntent(MediaProjectionConfig.createConfigForDefaultDisplay())
                else manager.createScreenCaptureIntent()
            @Suppress("DEPRECATION") startActivityForResult(intent, 901)
        } catch (error: Exception) {
            consentPending = false
            PilotRuntime.platformError = "Cannot request screen sharing: ${error.message}"
        }
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 902 && consentPending) requestCaptureConsent()
    }
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 901) return
        consentPending = false
        if (resultCode != Activity.RESULT_OK || data == null) {
            PilotRuntime.platformError = "Screen sharing permission was not granted"
            return
        }
        val intent = Intent(this, ProjectionService::class.java).setAction(ProjectionService.START).putExtra("token", data)
        try {
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent) else startService(intent)
        } catch (error: Exception) { PilotRuntime.platformError = "Capture service could not start: ${error.message}" }
    }
}
