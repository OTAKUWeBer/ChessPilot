package io.github.otakuweber.chesspilot

import android.app.*
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.BroadcastReceiver
import android.content.pm.ServiceInfo
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.*
import android.util.DisplayMetrics
import android.view.Display
import android.view.WindowManager
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicBoolean

class ProjectionService : Service() {
    companion object {
        @Volatile private var current: ProjectionService? = null
        fun geometryIsCurrent() = current?.geometryMatches() == true
        const val START = "start_capture"
        const val END = "end_capture"
        const val STOP = "stop_moves"
        const val PLAY = "play"
        const val AUTO = "auto"
        private const val CHANNEL = "screen_capture"
        private const val NOTIFICATION = 1
    }
    private val main = Handler(Looper.getMainLooper())
    private val worker = HandlerThread("ChessPilot capture")
    private lateinit var frames: Handler
    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var epoch = 0L
    private var dimensions = Pair(0, 0)
    private var rotation = 0
    private val closing = AtomicBoolean(false)
    private val screenOff = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) { end("Display locked or switched off; restart capture") }
    }
    private var lastFrame = 0L
    private val refresh = object : Runnable {
        override fun run() {
            if (closing.get()) return
            try {
                if (PlatformBridge.takeFrameRequest(epoch)) {
                    // Static displays may not produce new buffers until the sink is reattached.
                    display?.surface = null
                    display?.surface = reader?.surface
                }
            } catch (error: Exception) { end("Capture refresh failed: ${error.message}") }
            frames.postDelayed(this, 50)
        }
    }
    private val displays by lazy { getSystemService(DisplayManager::class.java) }
    private val listener = object : DisplayManager.DisplayListener {
        override fun onDisplayAdded(id: Int) = Unit
        override fun onDisplayRemoved(id: Int) { if (id == Display.DEFAULT_DISPLAY) end("Display disconnected") }
        override fun onDisplayChanged(id: Int) {
            if (id == Display.DEFAULT_DISPLAY && epoch != 0L && !geometryMatches()) {
                end("Display size or rotation changed; restart capture")
            }
        }
    }
    private val callback = object : MediaProjection.Callback() {
        override fun onStop() { end("Screen sharing ended; restart capture to continue") }
        override fun onCapturedContentResize(width: Int, height: Int) {
            if (Pair(width, height) != dimensions) end("Capture source changed; share the entire display again")
        }
    }
    override fun onCreate() {
        super.onCreate()
        worker.start()
        frames = Handler(worker.looper)
        displays.registerDisplayListener(listener, main)
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(screenOff, IntentFilter(Intent.ACTION_SCREEN_OFF), RECEIVER_NOT_EXPORTED)
        else @Suppress("DEPRECATION") registerReceiver(screenOff, IntentFilter(Intent.ACTION_SCREEN_OFF))
    }
    @Suppress("DEPRECATION")
    private fun screenSize(): Pair<Int, Int> {
        val manager = getSystemService(WindowManager::class.java)
        if (Build.VERSION.SDK_INT >= 30) {
            val bounds = manager.maximumWindowMetrics.bounds
            return Pair(bounds.width(), bounds.height())
        }
        val metrics = DisplayMetrics()
        manager.defaultDisplay.getRealMetrics(metrics)
        return Pair(metrics.widthPixels, metrics.heightPixels)
    }
    private fun geometryMatches() = screenSize() == dimensions &&
        displays.getDisplay(Display.DEFAULT_DISPLAY)?.rotation == rotation

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            START -> {
                if (projection != null || closing.get()) return START_NOT_STICKY
                try { start(intent) } catch (error: Exception) { end("Capture could not start: ${error.message}") }
            }
            END -> end("Screen sharing stopped")
            STOP, PLAY, AUTO -> {
                if (projection == null) { stopSelf(); return START_NOT_STICKY }
                try {
                    when (intent.action) {
                        STOP -> PilotRuntime.command("stop")
                        PLAY -> PilotRuntime.command("play")
                        AUTO -> {
                            val state = PilotRuntime.command("status").getJSONObject("state")
                            PilotRuntime.command("set_auto", JSONObject().put("enabled", !state.getBoolean("auto_mode")))
                        }
                    }
                } catch (error: Exception) { PilotRuntime.platformError = error.message }
            }
            else -> stopSelf()
        }
        return START_NOT_STICKY
    }
    private fun start(intent: Intent) {
        check(PilotTouchService.current != null) { "Enable ChessPilot touch control first" }
        val token = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra("token", Intent::class.java)
            else @Suppress("DEPRECATION") (intent.getParcelableExtra("token") as? Intent)
        checkNotNull(token) { "Screen-sharing consent is missing" }
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(
            NotificationChannel(CHANNEL, "Screen sharing", NotificationManager.IMPORTANCE_LOW)
        )
        val builder = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, CHANNEL) else @Suppress("DEPRECATION") Notification.Builder(this)
        val dashboard = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        builder.setSmallIcon(android.R.drawable.ic_media_play).setContentTitle("ChessPilot screen sharing")
            .setContentText("Play or Auto on your shared board. Stop cancels automation.")
            .setContentIntent(dashboard).setOngoing(true)
        for ((action, label) in listOf(PLAY to "Play", AUTO to "Auto", STOP to "Stop")) {
            val pending = PendingIntent.getService(this, action.hashCode(), Intent(this, ProjectionService::class.java).setAction(action), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            builder.addAction(Notification.Action.Builder(null, label, pending).build())
        }
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTIFICATION, builder.build(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        else startForeground(NOTIFICATION, builder.build())
        dimensions = screenSize()
        rotation = checkNotNull(displays.getDisplay(Display.DEFAULT_DISPLAY)).rotation
        epoch = PlatformBridge.beginCapture(dimensions.first, dimensions.second)
        PilotRuntime.captureEpoch = epoch
        PilotRuntime.platformError = null
        projection = getSystemService(MediaProjectionManager::class.java).getMediaProjection(Activity.RESULT_OK, token)
        val sharing = checkNotNull(projection)
        sharing.registerCallback(callback, frames)
        val source = ImageReader.newInstance(dimensions.first, dimensions.second, PixelFormat.RGBA_8888, 3)
        reader = source
        source.setOnImageAvailableListener({ images ->
            if (closing.get()) return@setOnImageAvailableListener
            val image = images.acquireLatestImage() ?: return@setOnImageAvailableListener
            image.use {
                if (closing.get() || epoch != PilotRuntime.captureEpoch) return@use
                try {
                    val now = System.nanoTime()
                    if (now - lastFrame < 100_000_000) return@use
                    lastFrame = now
                    check(geometryMatches()) { "Display geometry changed" }
                    check(image.cropRect.left == 0 && image.cropRect.top == 0 &&
                        image.cropRect.width() == dimensions.first && image.cropRect.height() == dimensions.second) {
                        "Cropped capture cannot map to display touches"
                    }
                    val plane = image.planes.single()
                    val age = (now - image.timestamp) / 1_000_000
                    check(age in 0..3000) { "Capture timestamp is stale or incompatible" }
                    PlatformBridge.frame(epoch, plane.buffer.slice(), image.width, image.height, plane.rowStride, plane.pixelStride, age)
                } catch (error: Exception) { end("Screen capture failed: ${error.message}") }
            }
        }, frames)
        display = sharing.createVirtualDisplay("ChessPilot shared display", dimensions.first, dimensions.second,
            resources.displayMetrics.densityDpi, DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            source.surface, null, frames)
        frames.post(refresh)
        current = this
    }
    private fun end(reason: String) {
        if (!closing.compareAndSet(false, true)) return
        PilotRuntime.stopCapture(reason)
        main.post { stopSelf() }
    }
    override fun onDestroy() {
        closing.set(true)
        if (current === this) current = null
        frames.removeCallbacks(refresh)
        if (epoch != 0L && epoch == PilotRuntime.captureEpoch) PilotRuntime.stopCapture("Screen sharing ended")
        displays.unregisterDisplayListener(listener)
        unregisterReceiver(screenOff)
        display?.release()
        projection?.unregisterCallback(callback)
        projection?.stop()
        // Close on the frame handler after any synchronous JNI copy has finished.
        frames.post { reader?.close(); worker.quitSafely() }
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }
    override fun onBind(intent: Intent?) = null
}
