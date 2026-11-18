package io.github.otakuweber.chesspilot

import java.nio.ByteBuffer

/** IDs cross JNI, never callback-owned pointers or Android objects. */
object PlatformBridge {
    init { System.loadLibrary("chesspilot_runtime") }
    external fun request(json: String): String
    external fun beginCapture(width: Int, height: Int): Long
    external fun frame(epoch: Long, buffer: ByteBuffer, width: Int, height: Int,
                       rowStride: Int, pixelStride: Int, ageMs: Long)
    external fun invalidate(epoch: Long, reason: String)
    external fun inputConnected(connected: Boolean)
    external fun takeGesture(epoch: Long): String?
    external fun gestureCurrent(epoch: Long, id: Long): Boolean
    external fun overlay(epoch: Long, left: Int, top: Int, right: Int, bottom: Int, visible: Boolean)
    external fun takeFrameRequest(epoch: Long): Boolean
    external fun gestureResult(epoch: Long, id: Long, result: Int)
}
