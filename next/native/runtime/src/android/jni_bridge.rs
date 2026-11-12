use super::{bridge, rgba_frame};
use jni::{
    objects::{JByteBuffer, JObject, JString},
    sys::{jboolean, jint, jlong, jstring},
    JNIEnv,
};
use serde_json::json;
use std::time::{Duration, Instant};
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_overlay(
    mut env: JNIEnv,
    _this: JObject,
    epoch: jlong,
    left: jint,
    top: jint,
    right: jint,
    bottom: jint,
    visible: jboolean,
) {
    if let Err(error) = bridge().overlay(
        epoch as u64,
        (visible != 0).then_some([left, top, right, bottom]),
    ) {
        throw(&mut env, error);
    }
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_gestureCurrent(
    _env: JNIEnv,
    _this: JObject,
    epoch: jlong,
    id: jlong,
) -> jboolean {
    u8::from(bridge().gesture_current(epoch as u64, id as u64))
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_takeFrameRequest(
    _env: JNIEnv,
    _this: JObject,
    epoch: jlong,
) -> jboolean {
    u8::from(bridge().take_frame_request(epoch as u64))
}
fn text(env: &mut JNIEnv<'_>, value: String) -> jstring {
    match env.new_string(value) {
        Ok(s) => s.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}
fn throw(env: &mut JNIEnv<'_>, error: String) {
    let _ = env.throw_new("java/lang/IllegalStateException", error);
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_request(
    mut env: JNIEnv,
    _this: JObject,
    input: JString,
) -> jstring {
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let raw: String = env.get_string(&input).map_err(|e| e.to_string())?.into();
        if raw.len() > 1024 * 1024 {
            return Err("Android request exceeded limit".to_owned());
        }
        let value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
        crate::ffi::request(value)
    }))
    .unwrap_or_else(|_| Err("Android native request panicked".into()));
    let envelope = match result {
        Ok(result) => json!({"ok":true,"result":result}),
        Err(error) => json!({"ok":false,"error":error}),
    };
    text(&mut env, envelope.to_string())
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_beginCapture(
    mut env: JNIEnv,
    _this: JObject,
    width: jint,
    height: jint,
) -> jlong {
    let result = usize::try_from(width)
        .ok()
        .zip(usize::try_from(height).ok())
        .ok_or_else(|| "Invalid Android display size".to_owned())
        .and_then(|(w, h)| bridge().begin(w, h));
    match result {
        Ok(epoch) => epoch as jlong,
        Err(error) => {
            throw(&mut env, error);
            0
        }
    }
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_frame(
    mut env: JNIEnv,
    _this: JObject,
    epoch: jlong,
    buffer: JByteBuffer,
    width: jint,
    height: jint,
    row_stride: jint,
    pixel_stride: jint,
    age_ms: jlong,
) {
    let received = Instant::now();
    let result = (|| {
        if epoch <= 0
            || width <= 0
            || height <= 0
            || row_stride <= 0
            || pixel_stride <= 0
            || !(0..=3000).contains(&age_ms)
        {
            return Err("Invalid Android frame metadata".to_owned());
        }
        let length = env
            .get_direct_buffer_capacity(&buffer)
            .map_err(|e| e.to_string())?;
        if length > 64 * 1024 * 1024 * 64 {
            return Err("Android frame buffer exceeded limit".into());
        }
        let ptr = env
            .get_direct_buffer_address(&buffer)
            .map_err(|e| e.to_string())?;
        if ptr.is_null() || length == 0 {
            return Err("Android frame buffer is empty".into());
        }
        // The Image remains acquired in Kotlin until this synchronous copy returns.
        let bytes = unsafe { std::slice::from_raw_parts(ptr, length) };
        let image = rgba_frame(
            bytes,
            width as usize,
            height as usize,
            row_stride as usize,
            pixel_stride as usize,
        )?;
        bridge().frame(
            epoch as u64,
            image,
            Duration::from_millis(age_ms as u64) + received.elapsed(),
        )
    })();
    if let Err(error) = result {
        throw(&mut env, error);
    }
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_invalidate(
    mut env: JNIEnv,
    _this: JObject,
    epoch: jlong,
    reason: JString,
) {
    match env.get_string(&reason) {
        Ok(s) => bridge().invalidate(epoch as u64, &s.to_string_lossy()),
        Err(error) => throw(&mut env, error.to_string()),
    }
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_inputConnected(
    _env: JNIEnv,
    _this: JObject,
    connected: jboolean,
) {
    bridge().input_connected(connected != 0);
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_takeGesture(
    mut env: JNIEnv,
    _this: JObject,
    epoch: jlong,
) -> jstring {
    match bridge().take_action(epoch as u64) {
        Some(value) => text(&mut env, value.to_string()),
        None => std::ptr::null_mut(),
    }
}
#[no_mangle]
pub extern "system" fn Java_io_github_otakuweber_chesspilot_PlatformBridge_gestureResult(
    _env: JNIEnv,
    _this: JObject,
    epoch: jlong,
    id: jlong,
    result: jint,
) {
    bridge().complete(epoch as u64, id as u64, result);
}
