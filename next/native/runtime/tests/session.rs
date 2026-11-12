use chesspilot_runtime::ffi::{
    chesspilot_alloc, chesspilot_free_input, chesspilot_free_response, chesspilot_request, request,
};
use serde_json::{json, Value};
use std::{
    ffi::CStr,
    time::{Duration, Instant},
};

#[test]
fn settings_are_transactional_and_sessions_are_isolated() {
    let first = request(json!({"command":"open"})).unwrap();
    let a = first["session"].as_u64().unwrap();
    let b = request(json!({"command":"open"})).unwrap()["session"]
        .as_u64()
        .unwrap();
    assert_eq!(first["state"]["depth"], 15);
    assert!(request(json!({"command":"play","session":a})).is_err());
    assert!(request(json!({"command":"set_auto","session":a,"enabled":true})).is_err());
    assert!(request(json!({"command":"set_auto","session":a,"enabled":"yes"})).is_err());
    assert!(request(json!({"command":"configure","session":a,"depth":18,"delay":2})).is_err());
    assert_eq!(
        request(json!({"command":"status","session":a})).unwrap()["state"]["depth"],
        15
    );
    let configured=request(json!({"command":"configure","session":a,"depth":18,"delay":0.6,"mode":"click","color":"b","kingside":true})).unwrap();
    assert_eq!(configured["state"]["depth"], 18);
    assert_eq!(configured["state"]["color"], "b");
    assert_eq!(
        request(json!({"command":"status","session":b})).unwrap()["state"]["depth"],
        15
    );
    request(json!({"command":"close","session":a})).unwrap();
    assert!(request(json!({"command":"status","session":a})).is_err());
    request(json!({"command":"close","session":b})).unwrap();
}

#[test]
#[cfg(windows)]
#[ignore = "Requires CHESSPILOT_MODEL, CHESSPILOT_ORT and CHESSPILOT_STOCKFISH; probes native capture without sending input"]
fn initialized_capture_gates_play_and_failed_reload_preserves_engine() {
    let engine = std::env::var("CHESSPILOT_STOCKFISH").unwrap();
    let model = std::env::var("CHESSPILOT_MODEL").unwrap();
    let runtime = std::env::var("CHESSPILOT_ORT").unwrap();
    let id = request(json!({"command":"open"})).unwrap()["session"]
        .as_u64()
        .unwrap();
    request(json!({"command":"initialize","session":id,"engine_path":engine,"model_path":model,"runtime_path":runtime})).unwrap();
    request(json!({"command":"configure","session":id,"color":"b"})).unwrap();
    let ready = wait_idle(id);
    assert!(ready["error"].is_null(), "{ready}");
    assert_eq!(ready["engine_ready"], true);
    assert_eq!(ready["capture_ready"], true);
    assert_eq!(ready["automation_ready"], true);
    assert!(ready["confirmed_fen"].is_null());
    request(json!({"command":"configure","session":id,"color":null})).unwrap();
    assert!(request(json!({"command":"play","session":id})).is_err());
    request(json!({"command":"initialize_capture","session":id,"model_path":"missing.onnx","runtime_path":runtime})).unwrap();
    let failed = wait_idle(id);
    assert!(failed["error"].is_string());
    assert_eq!(failed["capture_ready"], false);
    assert_eq!(failed["engine_ready"], true);
    assert!(request(json!({"command":"play","session":id})).is_err());
    request(json!({"command":"close","session":id})).unwrap();
}

#[test]
fn ffi_handles_bad_buffers_json_utf8_and_allocations() {
    for bytes in [b"{".as_slice(), &[255u8], b"{}"] {
        let input = chesspilot_alloc(bytes.len());
        assert!(!input.is_null());
        unsafe {
            std::ptr::copy_nonoverlapping(bytes.as_ptr(), input, bytes.len());
            let response = chesspilot_request(input, bytes.len());
            let envelope: Value =
                serde_json::from_slice(CStr::from_ptr(response).to_bytes()).unwrap();
            assert_eq!(envelope["ok"], false);
            chesspilot_free_response(response);
            chesspilot_free_input(input, bytes.len());
        }
    }
    assert!(chesspilot_alloc(0).is_null());
    assert!(chesspilot_alloc(1024 * 1024 + 1).is_null());
    unsafe {
        let response = chesspilot_request(std::ptr::null(), 1);
        assert!(!response.is_null());
        chesspilot_free_response(response);
    }
}

fn wait_idle(id: u64) -> Value {
    let deadline = Instant::now() + Duration::from_secs(15);
    loop {
        let state = request(json!({"command":"status","session":id})).unwrap()["state"].clone();
        if state["busy"] == false {
            return state;
        }
        assert!(
            Instant::now() < deadline,
            "Session operation did not finish"
        );
        std::thread::sleep(Duration::from_millis(10));
    }
}

#[test]
#[ignore = "Requires CHESSPILOT_STOCKFISH for real native session integration"]
fn asynchronous_engine_and_stop_invalidate_analysis() {
    let path = std::env::var("CHESSPILOT_STOCKFISH").unwrap();
    let id = request(json!({"command":"open"})).unwrap()["session"]
        .as_u64()
        .unwrap();
    let accepted =
        request(json!({"command":"initialize_engine","session":id,"engine_path":path})).unwrap();
    assert_eq!(accepted["state"]["busy"], true);
    request(json!({"command":"configure","session":id,"color":"b"})).unwrap();
    assert_eq!(wait_idle(id)["engine_ready"], true);
    request(json!({"command":"configure","session":id,"color":"w"})).unwrap();
    request(json!({"command":"configure","session":id,"depth":10})).unwrap();
    let fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    request(json!({"command":"analyze","session":id,"fen":fen})).unwrap();
    let analysis = wait_idle(id);
    assert!(analysis["analysis"]["best_move"].is_string());
    assert!(analysis["analysis"]["updated_fen"]
        .as_str()
        .unwrap()
        .contains(" b "));
    request(json!({"command":"configure","session":id,"depth":30})).unwrap();
    request(json!({"command":"analyze","session":id,"fen":fen})).unwrap();
    request(json!({"command":"configure","session":id,"color":"b"})).unwrap();
    request(json!({"command":"stop","session":id})).unwrap();
    let stopped = wait_idle(id);
    assert_eq!(stopped["color"], "b");
    assert_eq!(stopped["status"], "Stopped");
    assert!(stopped["analysis"].is_null());
    request(json!({"command":"close","session":id})).unwrap();
}
