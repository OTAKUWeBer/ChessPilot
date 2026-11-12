//! Length-delimited UTF-8 JSON across a small C ABI. Returned strings are Rust-owned.
use crate::session::Session;
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    ffi::{c_char, CString},
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc, Mutex, OnceLock,
    },
};
const MAX_REQUEST: usize = 1024 * 1024;
static SESSIONS: OnceLock<Mutex<HashMap<u64, Arc<Session>>>> = OnceLock::new();
static NEXT_ID: AtomicU64 = AtomicU64::new(1);
fn registry() -> &'static Mutex<HashMap<u64, Arc<Session>>> {
    SESSIONS.get_or_init(|| Mutex::new(HashMap::new()))
}
pub fn request(value: Value) -> Result<Value, String> {
    let command = value
        .get("command")
        .and_then(Value::as_str)
        .ok_or("Missing command")?;
    if command == "open" {
        let id = NEXT_ID.fetch_add(1, Ordering::Relaxed);
        let session = Arc::new(Session::default());
        let snapshot = session.snapshot();
        registry()
            .lock()
            .map_err(|_| "Session registry unavailable")?
            .insert(id, session);
        return Ok(json!({"session":id,"state":snapshot}));
    }
    let id = value
        .get("session")
        .and_then(Value::as_u64)
        .ok_or("Missing session ID")?;
    let session = registry()
        .lock()
        .map_err(|_| "Session registry unavailable")?
        .get(&id)
        .cloned()
        .ok_or("Session is closed or unknown")?;
    match command {
        "status" => {}
        "configure" => session.configure(&value)?,
        "initialize_engine" => session.initialize_engine(&value)?,
        "analyze" => session.analyze(
            value
                .get("fen")
                .and_then(Value::as_str)
                .ok_or("Missing FEN")?
                .into(),
        )?,
        "stop" => session.stop(),
        "close" => {
            registry()
                .lock()
                .map_err(|_| "Session registry unavailable")?
                .remove(&id);
            session.close();
            return Ok(json!({"closed":true}));
        }
        _ => return Err("Unknown native command".into()),
    }
    Ok(json!({"session":id,"state":session.snapshot()}))
}

#[no_mangle]
pub extern "C" fn chesspilot_alloc(length: usize) -> *mut u8 {
    if length == 0 || length > MAX_REQUEST {
        return std::ptr::null_mut();
    }
    let mut bytes = Vec::new();
    if bytes.try_reserve_exact(length).is_err() {
        return std::ptr::null_mut();
    }
    bytes.resize(length, 0);
    Box::into_raw(bytes.into_boxed_slice()) as *mut u8
}
/// # Safety
/// `input` must address `length` initialized bytes, alive for the duration of this call.
#[no_mangle]
pub unsafe extern "C" fn chesspilot_request(input: *const u8, length: usize) -> *mut c_char {
    let response = std::panic::catch_unwind(|| {
        if input.is_null() || length == 0 || length > MAX_REQUEST {
            return json!({"ok":false,"error":"Invalid request buffer"});
        }
        let bytes = unsafe { std::slice::from_raw_parts(input, length) };
        let result = serde_json::from_slice(bytes)
            .map_err(|e| e.to_string())
            .and_then(request);
        match result {
            Ok(result) => json!({"ok":true,"result":result}),
            Err(error) => json!({"ok":false,"error":error}),
        }
    })
    .unwrap_or_else(|_| json!({"ok":false,"error":"Native request panicked"}));
    CString::new(response.to_string())
        .expect("JSON escapes NUL")
        .into_raw()
}
/// # Safety
/// `input` must be a buffer returned by chesspilot_alloc with the same length, freed once.
#[no_mangle]
pub unsafe extern "C" fn chesspilot_free_input(input: *mut u8, length: usize) {
    if !input.is_null() {
        drop(unsafe { Box::from_raw(std::ptr::slice_from_raw_parts_mut(input, length)) });
    }
}
/// # Safety
/// `response` must be a live pointer returned by chesspilot_request, freed exactly once.
#[no_mangle]
pub unsafe extern "C" fn chesspilot_free_response(response: *mut c_char) {
    if !response.is_null() {
        drop(unsafe { CString::from_raw(response) });
    }
}
