#![cfg(target_os = "linux")]
use chesspilot_runtime::desktop::{self, Capture};
#[test]
#[ignore = "Requires CHESSPILOT_LINUX_CAPTURE_TEST=1 on a real X11 or supported wlroots desktop; sends no input"]
fn native_linux_capture_and_input_capability_probe() {
    assert_eq!(
        std::env::var("CHESSPILOT_LINUX_CAPTURE_TEST").as_deref(),
        Ok("1")
    );
    let (mut capture, _input) = desktop::open().unwrap();
    let frame = capture.capture().unwrap();
    assert_eq!(
        frame.image.pixels().len(),
        frame.image.width() * frame.image.height() * 3
    );
    assert!(frame.image.width() > 0 && frame.image.height() > 0);
    let next = capture.capture().unwrap();
    assert_eq!(frame.bounds, next.bounds, "Layout changed during probe");
    println!(
        "Captured {}x{} at ({}, {}); native input capability negotiated without a gesture",
        frame.bounds.width, frame.bounds.height, frame.bounds.x, frame.bounds.y
    );
}
