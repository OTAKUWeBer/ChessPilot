package io.github.otakuweber.chesspilot

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.BitmapFactory
import android.graphics.PixelFormat
import android.graphics.Rect
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.RippleDrawable
import android.os.Build
import android.text.TextUtils
import android.view.*
import android.widget.Button
import android.widget.ImageButton
import android.widget.ImageView
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
    private var bubble: ImageButton? = null
    private val bubbleLogo by lazy {
        // Decode the 1024 px app logo once at a size appropriate for the small control.
        BitmapDrawable(service.resources,BitmapFactory.decodeResource(service.resources,R.drawable.chesspilot_logo,
            BitmapFactory.Options().apply {inSampleSize=4}))
    }
    private val stopIcon by lazy {service.getDrawable(R.drawable.ic_overlay_stop)}
    private var identity: TextView? = null
    private var title: TextView? = null
    private var play: Button? = null
    private var auto: Button? = null
    private var stop: Button? = null
    private val root = LinearLayout(service).apply {
        orientation = LinearLayout.VERTICAL
        background = GradientDrawable().apply { setColor(Color.rgb(38, 43, 40)); setStroke(dp(1), Color.rgb(67, 91, 73)) }
        clipToOutline = true
        elevation = 0f
    }
    // Secure overlays block the whole capture on some devices; the bridge masks our measured bounds.
    private val params = WindowManager.LayoutParams(
        dp(if (expanded) 216 else 48), WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
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
        text=label;contentDescription=description;isAllCaps=false;textSize=13f
        setTypeface(null,Typeface.BOLD);isSingleLine=true;includeFontPadding=false
        stateListAnimator=null;elevation=0f
        minimumWidth=dp(48);minimumHeight=dp(48)
        setPadding(dp(4),0,dp(4),0)
        setTextColor(ColorStateList(arrayOf(intArrayOf(-android.R.attr.state_enabled),intArrayOf()),
            intArrayOf(Color.rgb(117,128,121),Color.WHITE)))
        background=RippleDrawable(ColorStateList.valueOf(0x28FFFFFF),GradientDrawable().apply {
            setColor(Color.WHITE);cornerRadius=dp(10).toFloat()
        },null)
        backgroundTintList=buttonTint(Color.rgb(54,73,59),Color.rgb(61,123,70))
        setOnClickListener { action() }
    }
    private fun buttonTint(normal: Int, active: Int=normal) = ColorStateList(
        arrayOf(intArrayOf(-android.R.attr.state_enabled),intArrayOf(android.R.attr.state_activated),intArrayOf()),
        intArrayOf(Color.rgb(47,54,49),active,normal)
    )
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
        params.width=dp(if(expanded)216 else 48)
        windows.updateViewLayout(root,params)
        root.post { dock() }
    }
    private fun openApp() {
        try { service.startActivity(Intent(service,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)) }
        catch(error: Exception) {PilotRuntime.platformError="Cannot open dashboard: ${error.message}"}
    }
    private fun render() {
        root.removeAllViews();bubble=null;identity=null;title=null;play=null;auto=null;stop=null
        (root.background as GradientDrawable).cornerRadius=dp(if(expanded)16 else 24).toFloat()
        if (!expanded) {
            root.setPadding(0,0,0,0)
            val control=ImageButton(service).apply {
                minimumWidth=dp(48);minimumHeight=dp(48);setPadding(dp(6),dp(6),dp(6),dp(6))
                scaleType=ImageView.ScaleType.FIT_CENTER;imageTintList=ColorStateList.valueOf(Color.WHITE)
                stateListAnimator=null;elevation=0f
                background=RippleDrawable(ColorStateList.valueOf(0x28FFFFFF),GradientDrawable().apply {
                    setColor(Color.WHITE);cornerRadius=dp(24).toFloat()
                },null)
            }
            bubble=control
            draggable(control) {if(state.optBoolean("busy"))command("stop") else toggle()}
            root.addView(control,LinearLayout.LayoutParams(-1,dp(48)))
        } else {
            root.setPadding(dp(6),dp(2),dp(6),dp(6))
            val largeText=service.resources.configuration.fontScale>1.3f
            val header=LinearLayout(service)
            val metadata=TextView(service).apply {
                textSize=12f;setTextColor(Color.rgb(209,219,212));maxLines=if(largeText)2 else 1;ellipsize=TextUtils.TruncateAt.END
                setTypeface(null,Typeface.BOLD);setPadding(dp(2),0,0,0)
                gravity=Gravity.CENTER_VERTICAL;contentDescription="Drag controls or tap to open ChessPilot"
            }
            identity=metadata;draggable(metadata) { openApp() }
            val status=TextView(service).apply {
                textSize=12f;setTextColor(Color.rgb(171,192,177));maxLines=if(largeText)2 else 1;ellipsize=TextUtils.TruncateAt.END
                minHeight=dp(20);setPadding(dp(2),0,dp(2),0)
                contentDescription="Drag controls or tap for status details"
            }
            title=status;draggable(status) { openApp() }
            val information=LinearLayout(service).apply {
                orientation=LinearLayout.VERTICAL;gravity=Gravity.CENTER_VERTICAL;minimumHeight=dp(48)
                addView(metadata,LinearLayout.LayoutParams(-1,-2))
                addView(status,LinearLayout.LayoutParams(-1,-2))
            }
            header.addView(information,LinearLayout.LayoutParams(0,-2,1f))
            header.addView(button("−","Collapse controls") {toggle()}.apply {
                textSize=22f;setTypeface(null,Typeface.NORMAL);backgroundTintList=ColorStateList.valueOf(Color.TRANSPARENT)
            },LinearLayout.LayoutParams(dp(48),dp(48)))
            root.addView(header)
            root.addView(View(service).apply {setBackgroundColor(Color.rgb(63,76,66))},
                LinearLayout.LayoutParams(-1,dp(1)).apply {topMargin=dp(2);bottomMargin=dp(4)})
            val controls=LinearLayout(service).apply {
                isBaselineAligned=false
                orientation=if(largeText)LinearLayout.VERTICAL else LinearLayout.HORIZONTAL
            }
            play=button("Play","Play next move") {command("play")}.apply {
                backgroundTintList=buttonTint(Color.rgb(61,123,70))
            }
            auto=button("Auto","Toggle automatic moves") {command("set_auto",JSONObject().put("enabled",!state.optBoolean("auto_mode")))}
            stop=button("Stop","Stop ChessPilot") {command("stop")}.apply {backgroundTintList=buttonTint(Color.rgb(132,56,53))}
            val exit=button("×","Stop sharing and exit ChessPilot") {PilotRuntime.exit(service)}.apply {
                textSize=22f;setTypeface(null,Typeface.NORMAL);setTextColor(Color.rgb(255,180,171))
                backgroundTintList=buttonTint(Color.rgb(63,49,49))
            }
            for((index,control) in listOf(play,auto,stop,exit).withIndex()) {
                val size=if(controls.orientation==LinearLayout.HORIZONTAL)LinearLayout.LayoutParams(0,dp(48),1f) else LinearLayout.LayoutParams(-1,dp(48))
                if(index>0) {
                    if(controls.orientation==LinearLayout.HORIZONTAL) size.marginStart=dp(4) else size.topMargin=dp(4)
                }
                controls.addView(control,size)
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
            setImageDrawable(if(busy)stopIcon else bubbleLogo)
            contentDescription=if(busy)"Stop ChessPilot" else "Expand ChessPilot controls"
            backgroundTintList=buttonTint(if(busy)Color.rgb(132,56,53) else Color.rgb(54,90,61))
        }
        val color=when(state.optString("color")){"w"->"White";"b"->"Black";else->"Choose color"}
        val status=when {
            state.optString("game_result")=="checkmate"->"Checkmate!"
            state.optString("game_result")=="stalemate"->"Draw · stalemate"
            !state.isNull("game_result")->"Game over"
            state.optString("status")=="Stopping..."->"Stopping…"
            state.optString("operation")=="auto"->if(state.optString("status").startsWith("Waiting"))"Waiting" else "Auto running"
            busy->"Working"
            !state.isNull("error")->"Open app for details"
            state.optString("color") !in listOf("w","b")->"Choose color in app"
            !state.optBoolean("automation_ready")->"Restart screen sharing"
            state.optString("status")=="Stopped"->"Stopped"
            else->"Ready"
        }
        identity?.text="$color · ${state.optInt("depth",10)}"
        title?.text=status
        title?.setTextColor(if(!state.isNull("error"))Color.rgb(255,180,171) else Color.rgb(171,192,177))
        val ready=!busy && state.isNull("game_result") && state.optBoolean("engine_ready") && state.optBoolean("automation_ready") && state.optString("color") in listOf("w","b")
        play?.isEnabled=ready && !state.optBoolean("auto_mode")
        auto?.isEnabled=state.optBoolean("auto_mode") || ready && state.optBoolean("auto_available")
        auto?.isActivated=state.optBoolean("auto_mode")
        auto?.isSelected=state.optBoolean("auto_mode")
        auto?.contentDescription=if(state.optBoolean("auto_mode"))"Turn automatic moves off" else "Turn automatic moves on"
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
