package io.github.otakuweber.chesspilot

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Handler
import android.os.Looper
import android.view.accessibility.AccessibilityEvent
import org.json.JSONObject

class PilotTouchService : AccessibilityService() {
    companion object { @Volatile var current: PilotTouchService? = null; private set }
    private val handler = Handler(Looper.getMainLooper())
    private var active = false
    private var overlay: PhoneOverlay? = null
    private var lastSnapshot = 0L
    private val poll = object : Runnable {
        override fun run() {
            if (current !== this@PilotTouchService) return
            try {
                val epoch = PilotRuntime.captureEpoch
                if (epoch != 0L && !PilotRuntime.dashboardVisible) {
                    if (overlay == null) overlay = PhoneOverlay(this@PilotTouchService)
                    val now=android.os.SystemClock.uptimeMillis()
                    if (now-lastSnapshot>=250) {
                        overlay?.update(PilotRuntime.command("status").getJSONObject("state"))
                        lastSnapshot=now
                    }
                } else {
                    overlay?.close();overlay=null
                }
                if (!active && epoch != 0L && overlay?.inputReady() == true) {
                    PlatformBridge.takeGesture(epoch)?.let { dispatch(JSONObject(it)) }
                }
            } catch (error: Exception) {
                PilotRuntime.stopCapture("Touch service failed: ${error.message}")
            }
            handler.postDelayed(this, 16)
        }
    }
    override fun onServiceConnected() {
        current = this
        PlatformBridge.inputConnected(true)
        handler.post(poll)
    }
    private fun dispatch(action: JSONObject) {
        val epoch = action.getLong("epoch")
        val id = action.getLong("id")
        if (epoch != PilotRuntime.captureEpoch || active) {
            PlatformBridge.gestureResult(epoch, id, 1)
            return
        }
        try {
            if (!ProjectionService.geometryIsCurrent() || magnificationController.scale != 1f) {
                PlatformBridge.gestureResult(epoch, id, 1)
                PilotRuntime.stopCapture("Display geometry or magnification changed; restart capture")
                return
            }
            val x1 = action.getDouble("x1").toFloat()
            val y1 = action.getDouble("y1").toFloat()
            val x2 = action.getDouble("x2").toFloat()
            val y2 = action.getDouble("y2").toFloat()
            val path = Path().apply {
                moveTo(x1, y1)
                if (x1 != x2 || y1 != y2) lineTo(x2, y2)
            }
            val gesture = GestureDescription.Builder().addStroke(
                GestureDescription.StrokeDescription(path, 0, action.getLong("duration"))
            ).build()
            if (overlay?.inputReady() != true || !PlatformBridge.gestureCurrent(epoch, id)) {
                PlatformBridge.gestureResult(epoch, id, 1)
                return
            }
            active = true
            val accepted = dispatchGesture(gesture, object : GestureResultCallback() {
                override fun onCompleted(description: GestureDescription) { finish(0) }
                override fun onCancelled(description: GestureDescription) { finish(2) }
                private fun finish(result: Int) {
                    active = false
                    PlatformBridge.gestureResult(epoch, id, result)
                }
            }, handler)
            if (!accepted) {
                active = false
                PlatformBridge.gestureResult(epoch, id, 1)
            }
        } catch (error: Exception) {
            active = false
            PlatformBridge.gestureResult(epoch, id, 2)
            PilotRuntime.stopCapture("Touch dispatch failed: ${error.message}")
        }
    }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit
    override fun onConfigurationChanged(configuration: android.content.res.Configuration) {
        super.onConfigurationChanged(configuration)
        if(PilotRuntime.captureEpoch!=0L) PilotRuntime.command("stop")
        overlay?.close();overlay=null
    }
    override fun onInterrupt() { PilotRuntime.stopCapture("Accessibility service interrupted") }
    override fun onDestroy() {
        handler.removeCallbacks(poll)
        overlay?.close();overlay=null
        if (current === this) current = null
        PlatformBridge.inputConnected(false)
        PilotRuntime.stopCapture("Accessibility service disconnected; restart capture")
        super.onDestroy()
    }
}
