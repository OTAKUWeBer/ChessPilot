use chesspilot_runtime::{
    cpu,
    diagnostics::{self, RotatingLog, LOG_FILENAME},
    ffi,
};
use std::{
    collections::HashMap,
    fs,
    path::PathBuf,
    sync::atomic::{AtomicU64, Ordering},
};
static NEXT: AtomicU64 = AtomicU64::new(0);
struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "chesspilot-log-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
#[test]
fn rotation_retains_order_reopens_existing_data_and_does_not_touch_python_logs() {
    let temp = Temp::new();
    fs::write(temp.0.join("chesspilot.log"), b"Python reference").unwrap();
    {
        let mut log = RotatingLog::new(&temp.0, 12, 2).unwrap();
        for text in [
            "first-line\n",
            "second-line\n",
            "third-line\n",
            "fourth-line\n",
        ] {
            log.append(text).unwrap();
        }
        assert_eq!(
            fs::read_to_string(temp.0.join(LOG_FILENAME)).unwrap(),
            "fourth-line\n"
        );
        assert_eq!(
            fs::read_to_string(temp.0.join(format!("{LOG_FILENAME}.1"))).unwrap(),
            "third-line\n"
        );
        assert_eq!(
            fs::read_to_string(temp.0.join(format!("{LOG_FILENAME}.2"))).unwrap(),
            "second-line\n"
        );
        assert!(
            RotatingLog::new(&temp.0, 12, 2).is_err(),
            "A second writer must not race rotation"
        );
    }
    let mut reopened = RotatingLog::new(&temp.0, 12, 2).unwrap();
    reopened.append("new\n").unwrap();
    assert_eq!(
        fs::read_to_string(temp.0.join(LOG_FILENAME)).unwrap(),
        "new\n"
    );
    assert_eq!(
        fs::read_to_string(temp.0.join(format!("{LOG_FILENAME}.1"))).unwrap(),
        "fourth-line\n"
    );
    assert_eq!(
        fs::read(temp.0.join("chesspilot.log")).unwrap(),
        b"Python reference"
    );
}
#[test]
fn oversize_unicode_records_stay_valid_and_file_conflicts_preserve_data() {
    let temp = Temp::new();
    let mut log = RotatingLog::new(&temp.0, 7, 0).unwrap();
    log.append("😀😀😀").unwrap();
    assert_eq!(fs::read_to_string(temp.0.join(LOG_FILENAME)).unwrap(), "😀");
    drop(log);
    fs::remove_file(temp.0.join(LOG_FILENAME)).unwrap();
    fs::create_dir(temp.0.join(LOG_FILENAME)).unwrap();
    assert!(RotatingLog::new(&temp.0, 100, 2).is_err());
    assert!(temp.0.join(LOG_FILENAME).is_dir());
}
#[test]
fn path_order_matches_windows_and_xdg_with_explicit_android_private_storage() {
    let temp = Temp::new();
    let env = HashMap::from([
        ("HOME", temp.0.clone()),
        ("USERPROFILE", temp.0.clone()),
        ("LOCALAPPDATA", temp.0.join("local")),
        ("XDG_STATE_HOME", temp.0.join("state")),
        ("XDG_DATA_HOME", temp.0.join("data")),
    ]);
    let lookup = |key: &str| env.get(key).cloned();
    assert_eq!(
        diagnostics::default_directories("windows", lookup, &temp.0)[0],
        temp.0.join("local/ChessPilot/logs")
    );
    assert_eq!(
        diagnostics::default_directories("linux", lookup, &temp.0)[0],
        temp.0.join("state/chesspilot/logs")
    );
    assert!(diagnostics::default_directories("android", lookup, &temp.0).is_empty());
    let relative = |key: &str| (key == "XDG_STATE_HOME").then(|| PathBuf::from("relative"));
    assert_eq!(
        diagnostics::default_directories("linux", relative, &temp.0),
        [temp.0.join("logs")]
    );
}
#[test]
fn messages_are_bounded_utf8_single_lines_and_plain_text() {
    let long = "😀".repeat(20_000);
    let line = diagnostics::render(
        &log::Record::builder()
            .target("engine")
            .level(log::Level::Error)
            .args(format_args!("injected\n[INFO]\r\u{1b}[31m{long}"))
            .build(),
    );
    assert!(line.len() <= 16 * 1024);
    assert_eq!(line.lines().count(), 1);
    assert!(line.contains("\\n[INFO]\\r\\u001b"));
    assert!(line.ends_with("[truncated]\n"));
    assert!(line.contains("Z] [ERROR] [engine]"));
}
#[test]
fn native_boundary_records_frontend_errors_and_flushes_to_disk() {
    let temp = Temp::new();
    ffi::request(serde_json::json!({"command":"configure_diagnostics","log_dir":temp.0})).unwrap();
    ffi::request(
        serde_json::json!({"command":"report_error","message":"Flutter failed\nstack: fixture"}),
    )
    .unwrap();
    diagnostics::flush();
    let info =
        ffi::request(serde_json::json!({"command":"diagnostics","include_tail":true})).unwrap();
    assert!(info["tail"]
        .as_str()
        .unwrap()
        .contains("Flutter failed\\nstack: fixture"));
    assert!(info["write_error"].is_null());
    assert!(fs::read_to_string(temp.0.join(LOG_FILENAME))
        .unwrap()
        .contains("Flutter failed\\nstack: fixture"));
    assert!(ffi::request(
        serde_json::json!({"command":"configure_diagnostics","log_dir":temp.0.join("different")})
    )
    .is_err());
    // The process-global writer owns its directory until process exit.
    std::mem::forget(temp);
}
#[test]
fn native_cpu_info_and_legacy_size_formatting_have_real_values() {
    for (n, expected) in [
        (500., "500.0 B"),
        (1024., "1.0 KB"),
        (1048576., "1.0 MB"),
        (1073741824., "1.0 GB"),
    ] {
        assert_eq!(cpu::format_bytes(n), expected);
    }
    let info = cpu::detect();
    assert!(!info.architecture.is_empty());
    assert!(info.cores > 0);
    #[cfg(target_arch = "x86_64")]
    {
        assert!(info.features.contains("sse2"));
        assert_eq!(
            info.features.contains("avx2"),
            std::is_x86_feature_detected!("avx2")
        );
    }
}
