package io.github.otakuweber.chesspilot

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Rect
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.text.TextUtils
import android.view.*
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject
import kotlin.math.abs
import kotlin.math.roundToInt

/** A small native window; the full Flutter dashboard remains the settings surface. */
class PhoneOverlay(private val service: AccessibilityService) {
    private val windows = service.getSystemService(WindowManager::class.java)
    private val preferences = service.getSharedPreferences("phone_controls", 0)
    private var expanded = preferences.getBoolean("expanded", false)
    private var right = preferences.getBoolean("right", true)
    private var vertical = preferences.getFloat("vertical", 0.03f).coerceIn(0f, 1f)
    private var dragging = false
    private var closed = false
    private var layoutPending = true
    private var epoch = 0L
    private var lastBounds: Rect? = null
    private var state = JSONObject()
    private var bubble: Button? = null
    private var title: TextView? = null
    private var play: Button? = null
    private var auto: Button? = null
    private var stop: Button? = null
    private val root = LinearLayout(service).apply {
        orientation = LinearLayout.VERTICAL
        background = GradientDrawable().apply { setColor(Color.rgb(45, 45, 45)); cornerRadius = dp(16).toFloat(); setStroke(dp(1), Color.rgb(76,175,80)) }
        setPadding(dp(4), dp(4), dp(4), dp(4))
        elevation = 0f
    }
    private val params = WindowManager.LayoutParams(
        dp(if (expanded) 184 else 48), WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or WindowManager.LayoutParams.FLAG_SECURE,
        PixelFormat.TRANSLUCENT
    ).apply { gravity = Gravity.TOP or Gravity.LEFT }
    init {
        render()
        windows.addView(root, params)
        root.viewTreeObserver.addOnPreDrawListener {
            val moved = !dragging && dock()
            if (!moved) publishBounds()
            !moved
        }
    }
    private fun dp(value: Int) = (value * service.resources.displayMetrics.density).roundToInt()
    @Suppress("DEPRECATION")
    private fun usable(): Rect {
        val size = if (Build.VERSION.SDK_INT >= 30) windows.maximumWindowMetrics.bounds else {
            val metrics = android.util.DisplayMetrics()
            windows.defaultDisplay.getRealMetrics(metrics)
            Rect(0, 0, metrics.widthPixels, metrics.heightPixels)
        }
        val insets = root.rootWindowInsets
        if (Build.VERSION.SDK_INT >= 30 && insets != null) {
            val bars = insets.getInsetsIgnoringVisibility(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            return Rect(size.left+bars.left,size.top+bars.top,size.right-bars.right,size.bottom-bars.bottom)
        } else if (insets != null) {
            return Rect(size.left+insets.stableInsetLeft,size.top+insets.stableInsetTop,size.right-insets.stableInsetRight,size.bottom-insets.stableInsetBottom)
        }
        return size
    }
    private fun dock(): Boolean {
        if (closed) return false
        val safe = usable()
        val width = root.width.takeIf { it > 0 } ?: params.width
        val height = root.height.takeIf { it > 0 } ?: dp(48)
        val x = if (right) (safe.right-width).coerceAtLeast(safe.left) else safe.left
        val y = safe.top + ((safe.height()-height).coerceAtLeast(0)*vertical).roundToInt()
        if (params.x != x || params.y != y) {
            params.x=x;params.y=y;layoutPending=true
            windows.updateViewLayout(root, params)
            return true
        }
        return false
    }
    private fun publishBounds() {
        if (closed) return
        val current = PilotRuntime.captureEpoch
        if (current == 0L || root.width <= 0 || root.height <= 0) return
        val point=IntArray(2);root.getLocationOnScreen(point)
        val bounds=Rect(point[0]-dp(2),point[1]-dp(2),point[0]+root.width+dp(2),point[1]+root.height+dp(2))
        if (current != epoch || bounds != lastBounds) {
            try { PlatformBridge.overlay(current,bounds.left,bounds.top,bounds.right,bounds.bottom,true) }
            catch(error: Exception) {
                layoutPending=true
                if (current==PilotRuntime.captureEpoch) PilotRuntime.stopCapture("Floating controls lost capture mapping: ${error.message}")
                return
            }
            epoch=current;lastBounds=bounds
        }
        layoutPending=false
    }
    fun inputReady() = !closed && root.isShown && !layoutPending && !dragging && epoch != 0L && epoch == PilotRuntime.captureEpoch
    private fun draggable(view: View, click: () -> Unit) {
        view.setOnClickListener { click() }
        var downX=0f;var downY=0f;var originX=0;var originY=0
        val slop=ViewConfiguration.get(service).scaledTouchSlop
        view.setOnTouchListener { target,event ->
            when(event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    downX=event.rawX;downY=event.rawY;originX=params.x;originY=params.y;dragging=false
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx=event.rawX-downX;val dy=event.rawY-downY
                    if (!dragging && (abs(dx)>slop || abs(dy)>slop)) {
                        dragging=true
                        command("stop")
                    }
                    if (dragging) {
                        val safe=usable()
                        params.x=(originX+dx.roundToInt()).coerceIn(safe.left,(safe.right-root.width).coerceAtLeast(safe.left))
                        params.y=(originY+dy.roundToInt()).coerceIn(safe.top,(safe.bottom-root.height).coerceAtLeast(safe.top))
                        layoutPending=true;windows.updateViewLayout(root,params)
                    }
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    val moved=dragging;dragging=false
                    if (moved) {
                        val safe=usable()
                        right=params.x+root.width/2>=safe.centerX()
                        vertical=((params.y-safe.top).toFloat()/(safe.height()-root.height).coerceAtLeast(1)).coerceIn(0f,1f)
                        preferences.edit().putBoolean("right",right).putFloat("vertical",vertical).apply()
                        dock()
                    } else if(event.actionMasked==MotionEvent.ACTION_UP) target.performClick()
                    true
                }
                else -> false
            }
        }
    }
    private fun button(label: String, description: String, action: () -> Unit): Button = Button(service).apply {
        text=label;contentDescription=description;isAllCaps=false;textSize=12f
        minimumWidth=dp(48);minimumHeight=dp(48)
        setPadding(0,0,0,0);setTextColor(Color.WHITE)
        backgroundTintList=ColorStateList.valueOf(Color.rgb(56,86,58))
        setOnClickListener { action() }
    }
    private fun command(name: String, values: JSONObject=JSONObject()) {
        try { state=PilotRuntime.command(name,values).getJSONObject("state");update(state) }
        catch(error: Exception) { PilotRuntime.platformError=error.message;title?.text="Open app for details" }
    }
    private fun toggle() {
        if (closed) return
        expanded=!expanded
        preferences.edit().putBoolean("expanded",expanded).apply()
        layoutPending=true
        render()
        params.width=dp(if(expanded)184 else 48)
        windows.updateViewLayout(root,params)
        root.post { dock() }
    }
    private fun openApp() {
        try { service.startActivity(Intent(service,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)) }
        catch(error: Exception) {PilotRuntime.platformError="Cannot open dashboard: ${error.message}"}
    }
    private fun render() {
        root.removeAllViews();bubble=null;title=null;play=null;auto=null;stop=null
        if (!expanded) {
            root.setPadding(0,0,0,0)
            val control=button("CP","Expand ChessPilot controls") {
                if(state.optBoolean("busy")) command("stop") else toggle()
            }
            bubble=control
            draggable(control) {if(state.optBoolean("busy"))command("stop") else toggle()}
            root.addView(control,LinearLayout.LayoutParams(-1,dp(48)))
        } else {
            root.setPadding(dp(4),dp(4),dp(4),dp(4))
            val header=LinearLayout(service)
            val status=TextView(service).apply {
                textSize=12f;setTextColor(Color.WHITE);maxLines=2;ellipsize=TextUtils.TruncateAt.END
                gravity=Gravity.CENTER_VERTICAL;minHeight=dp(48);contentDescription="Drag controls or tap to open ChessPilot"
            }
            title=status;draggable(status) { openApp() }
            header.addView(status,LinearLayout.LayoutParams(0,-2,1f))
            header.addView(button("−","Collapse controls") {toggle()},LinearLayout.LayoutParams(dp(48),dp(48)))
            root.addView(header)
            val controls=LinearLayout(service).apply {
                orientation=if(service.resources.configuration.fontScale>1.3f)LinearLayout.VERTICAL else LinearLayout.HORIZONTAL
            }
            play=button("Play","Play next move") {command("play")}
            auto=button("Auto","Toggle automatic moves") {command("set_auto",JSONObject().put("enabled",!state.optBoolean("auto_mode")))}
            stop=button("Stop","Stop ChessPilot") {command("stop")}.apply {backgroundTintList=ColorStateList.valueOf(Color.rgb(165,48,48))}
            for(control in listOf(play,auto,stop)) {
                controls.addView(control,if(controls.orientation==LinearLayout.HORIZONTAL)LinearLayout.LayoutParams(0,dp(48),1f) else LinearLayout.LayoutParams(-1,dp(48)))
            }
            root.addView(controls)
        }
        update(state)
    }
    fun update(snapshot: JSONObject) {
        if (closed) return
        state=snapshot
        val busy=state.optBoolean("busy")
        bubble?.apply {
            text=if(busy)"■" else "CP"
            contentDescription=if(busy)"Stop ChessPilot" else "Expand ChessPilot controls"
            backgroundTintList=ColorStateList.valueOf(if(busy)Color.rgb(165,48,48) else Color.rgb(56,86,58))
        }
        val color=when(state.optString("color")){"w"->"White";"b"->"Black";else->"Choose color"}
        val status=when {state.optString("operation")=="auto"->if(state.optString("status").startsWith("Waiting"))"Waiting" else "Auto running";busy->"Working";!state.isNull("error")->"Open app for details";else->"Ready"}
        title?.text="$color · ${state.optInt("depth",15)}\n$status"
        val ready=!busy && state.optBoolean("engine_ready") && state.optBoolean("automation_ready") && state.optString("color") in listOf("w","b")
        play?.isEnabled=ready
        auto?.isEnabled=state.optBoolean("auto_mode") || ready && state.optBoolean("auto_available")
        auto?.text=if(state.optBoolean("auto_mode"))"Auto ✓" else "Auto"
        stop?.isEnabled=busy || state.optBoolean("auto_mode")
    }
    fun close() {
        if (closed) return
        closed=true
        windows.removeViewImmediate(root)
        if(epoch!=0L && epoch==PilotRuntime.captureEpoch) PlatformBridge.overlay(epoch,0,0,0,0,false)
        epoch=0
    }
}
