use chesspilot_core::{board::Point, config::MoveMode};
use chesspilot_runtime::{
    android::{rgba_frame, Bridge},
    controller::Automation,
    desktop::{input::InputError, Capture},
    vision::RgbFrame,
};
use std::{
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc, Arc,
    },
    thread,
    time::{Duration, Instant},
};
const A: Point = Point { x: 20., y: 30. };
const B: Point = Point { x: 60., y: 70. };
fn ready() -> (Arc<Bridge>, u64) {
    let bridge = Arc::new(Bridge::default());
    bridge.input_connected(true);
    let epoch = bridge.begin(100, 100).unwrap();
    bridge
        .frame(
            epoch,
            RgbFrame::new(100, 100, vec![0; 30_000]).unwrap(),
            Duration::ZERO,
        )
        .unwrap();
    (bridge, epoch)
}
fn action(bridge: &Bridge, epoch: u64) -> serde_json::Value {
    let until = Instant::now() + Duration::from_secs(2);
    loop {
        if let Some(a) = bridge.take_action(epoch) {
            return a;
        }
        assert!(Instant::now() < until, "Gesture was not queued");
        thread::sleep(Duration::from_millis(1));
    }
}
#[test]
fn rgba_strides_and_bounds_are_checked_before_reading() {
    let bytes = [
        1, 2, 3, 255, 0, 0, 4, 5, 6, 255, 0, 0, 0, 0, 7, 8, 9, 255, 0, 0, 10, 11, 12, 255,
    ];
    assert_eq!(
        rgba_frame(&bytes, 2, 2, 14, 6).unwrap().pixels(),
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    );
    for (w, h, row, pixel) in [
        (0, 1, 4, 4),
        (2, 2, 14, 3),
        (2, 2, 4, 4),
        (usize::MAX, 2, 4, 4),
        (2, 3, 14, 6),
    ] {
        assert!(rgba_frame(&bytes, w, h, row, pixel).is_err());
    }
}
#[test]
fn one_drag_waits_for_its_exact_completion_callback() {
    let (bridge, epoch) = ready();
    let (_, mut input) = bridge.open().unwrap();
    let (tx, rx) = mpsc::channel();
    let job = thread::spawn(move || {
        tx.send(input.move_piece(A, B, MoveMode::Drag, &AtomicBool::new(false)))
            .unwrap()
    });
    let a = action(&bridge, epoch);
    assert!(bridge.gesture_current(epoch, a["id"].as_u64().unwrap()));
    let id = a["id"].as_u64().unwrap();
    assert_eq!(a["duration"], 200);
    assert_eq!(a["x1"], 20.);
    assert_eq!(a["y2"], 70.);
    assert!(bridge.take_action(epoch).is_none());
    bridge.complete(epoch + 1, id, 0);
    bridge.complete(epoch, id + 1, 0);
    assert!(rx.recv_timeout(Duration::from_millis(25)).is_err());
    bridge.complete(epoch, id, 0);
    assert_eq!(rx.recv_timeout(Duration::from_secs(1)).unwrap(), Ok(()));
    job.join().unwrap();
    bridge.complete(epoch, id, 0);
    assert!(bridge.take_action(epoch).is_none());
}
#[test]
fn click_taps_are_callback_sequenced_and_second_rejection_is_uncertain() {
    let (bridge, epoch) = ready();
    let (_, mut input) = bridge.open().unwrap();
    assert!(matches!(
        input.move_piece(
            A,
            Point { x: 100., y: 2. },
            MoveMode::Click,
            &AtomicBool::new(false)
        ),
        Err(InputError::NotDispatched(_))
    ));
    assert!(bridge.take_action(epoch).is_none());
    let job =
        thread::spawn(move || input.move_piece(A, B, MoveMode::Click, &AtomicBool::new(false)));
    let first = action(&bridge, epoch);
    assert_eq!(first["x1"], first["x2"]);
    assert_eq!(first["duration"], 50);
    assert!(bridge.take_action(epoch).is_none());
    bridge.complete(epoch, first["id"].as_u64().unwrap(), 0);
    let second = action(&bridge, epoch);
    assert_eq!(second["x1"], 60.);
    bridge.complete(epoch, second["id"].as_u64().unwrap(), 1);
    assert!(matches!(job.join().unwrap(), Err(InputError::Uncertain(_))));
}
#[test]
fn stopped_dispatched_gesture_keeps_ownership_until_late_callback() {
    let (bridge, epoch) = ready();
    let (_, mut input) = bridge.open().unwrap();
    let cancelled = Arc::new(AtomicBool::new(false));
    let flag = cancelled.clone();
    let job = thread::spawn(move || input.tap(A, &flag));
    let a = action(&bridge, epoch);
    cancelled.store(true, Ordering::Release);
    assert_eq!(
        job.join().unwrap(),
        Err(InputError::Cancelled { dispatched: true })
    );
    assert!(!bridge.gesture_current(epoch, a["id"].as_u64().unwrap()));
    let (_, mut next) = bridge.open().unwrap();
    assert!(matches!(
        next.tap(B, &AtomicBool::new(false)),
        Err(InputError::NotDispatched(_))
    ));
    bridge.complete(epoch, a["id"].as_u64().unwrap(), 0);
    let job = thread::spawn(move || next.tap(B, &AtomicBool::new(false)));
    let b = action(&bridge, epoch);
    assert_ne!(a["id"], b["id"]);
    bridge.complete(epoch, b["id"].as_u64().unwrap(), 0);
    assert!(job.join().unwrap().is_ok());
}
#[test]
fn capture_generation_disconnect_and_stale_frames_invalidate_input() {
    let (bridge, epoch) = ready();
    let (mut capture, mut input) = bridge.open().unwrap();
    assert_eq!(capture.capture().unwrap().bounds.width, 100);
    bridge
        .frame(
            epoch,
            RgbFrame::new(100, 100, vec![0; 30_000]).unwrap(),
            Duration::from_secs(4),
        )
        .unwrap();
    assert!(capture.capture().is_err());
    assert!(matches!(
        input.tap(A, &AtomicBool::new(false)),
        Err(InputError::NotDispatched(_))
    ));
    let next = bridge.begin(200, 100).unwrap();
    assert!(capture.capture().is_err());
    assert!(bridge
        .frame(
            epoch,
            RgbFrame::new(100, 100, vec![0; 30_000]).unwrap(),
            Duration::ZERO
        )
        .is_err());
    bridge.invalidate(epoch, "old callback");
    assert!(bridge.open().is_ok());
    bridge.invalidate(next, "rotation");
    assert!(bridge.open().is_err());
    bridge.input_connected(false);
    bridge.begin(100, 100).unwrap();
    assert!(bridge.open().is_err());
}
#[test]
fn cancellation_before_dispatch_does_not_leave_a_queued_gesture() {
    let (bridge, epoch) = ready();
    let (_, mut input) = bridge.open().unwrap();
    let flag = Arc::new(AtomicBool::new(false));
    let cancelled = flag.clone();
    let job = thread::spawn(move || input.tap(A, &cancelled));
    thread::sleep(Duration::from_millis(30));
    flag.store(true, Ordering::Release);
    assert_eq!(
        job.join().unwrap(),
        Err(InputError::Cancelled { dispatched: false })
    );
    assert!(bridge.take_action(epoch).is_none());
}
#[test]
fn missing_callback_times_out_without_releasing_the_inflight_owner() {
    let (bridge, epoch) = ready();
    let (_, mut input) = bridge.open().unwrap();
    let job = thread::spawn(move || input.tap(A, &AtomicBool::new(false)));
    let a = action(&bridge, epoch);
    assert!(matches!(job.join().unwrap(), Err(InputError::Uncertain(_))));
    assert!(bridge.take_action(epoch).is_none());
    let (_, mut next) = bridge.open().unwrap();
    assert!(matches!(
        next.tap(B, &AtomicBool::new(false)),
        Err(InputError::NotDispatched(_))
    ));
    bridge.complete(epoch, a["id"].as_u64().unwrap(), 0);
}
#[test]
fn static_screen_capture_requests_a_new_buffer_instead_of_relabeling_old_pixels() {
    let (bridge, epoch) = ready();
    bridge
        .frame(
            epoch,
            RgbFrame::new(100, 100, vec![1; 30_000]).unwrap(),
            Duration::from_secs(1),
        )
        .unwrap();
    let (mut capture, _) = bridge.open().unwrap();
    let job = thread::spawn(move || capture.capture());
    let until = Instant::now() + Duration::from_secs(2);
    while !bridge.take_frame_request(epoch) {
        assert!(Instant::now() < until);
        thread::sleep(Duration::from_millis(1));
    }
    bridge
        .frame(
            epoch,
            RgbFrame::new(100, 100, vec![2; 30_000]).unwrap(),
            Duration::ZERO,
        )
        .unwrap();
    let frame = job.join().unwrap().unwrap();
    assert_eq!(frame.image.pixels()[0], 2);
    assert!(frame.captured_at.elapsed() < Duration::from_millis(500));
}
#[test]
fn stop_and_immediate_late_callback_cannot_lose_cancellation() {
    let (bridge, epoch) = ready();
    let (_, mut input) = bridge.open().unwrap();
    let job = thread::spawn(move || input.tap(A, &AtomicBool::new(false)));
    let a = action(&bridge, epoch);
    bridge.cancel_pending();
    bridge.complete(epoch, a["id"].as_u64().unwrap(), 0);
    assert_eq!(
        job.join().unwrap(),
        Err(InputError::Cancelled { dispatched: true })
    );
}
#[test]
fn replacing_capture_during_dispatch_reports_uncertain_and_ignores_old_callback() {
    let (bridge, epoch) = ready();
    let (_, mut input) = bridge.open().unwrap();
    let job = thread::spawn(move || input.tap(A, &AtomicBool::new(false)));
    let a = action(&bridge, epoch);
    let next = bridge.begin(100, 100).unwrap();
    assert!(matches!(job.join().unwrap(), Err(InputError::Uncertain(_))));
    bridge.complete(epoch, a["id"].as_u64().unwrap(), 0);
    assert_ne!(next, epoch);
    assert!(bridge.take_action(next).is_none());
}
#[test]
fn overlay_is_masked_and_a_covered_board_is_rejected() {
    use chesspilot_core::board::BoardGeometry;
    let (bridge, epoch) = ready();
    bridge.overlay(epoch, Some([-5, 0, 10, 10])).unwrap();
    bridge
        .frame(
            epoch,
            RgbFrame::new(100, 100, vec![7; 30_000]).unwrap(),
            Duration::ZERO,
        )
        .unwrap();
    let (mut capture, _) = bridge.open().unwrap();
    let frame = capture.capture().unwrap();
    assert_eq!(&frame.image.pixels()[..3], &[45; 3]);
    assert_eq!(&frame.image.pixels()[10 * 3..11 * 3], &[7; 3]);
    assert!(capture
        .validate_board(BoardGeometry::new(0., 0., 5.).unwrap())
        .is_err());
    assert!(capture
        .validate_board(BoardGeometry::new(20., 20., 5.).unwrap())
        .is_ok());
    assert!(bridge.overlay(epoch, Some([3, 3, 2, 4])).is_err());
    let mut frame = RgbFrame::new(1, 1, vec![0; 3]).unwrap();
    assert!(frame.mask([0, 0, 2, 1], 1).is_err());
}
#[test]
fn overlay_blocks_taps_and_the_entire_drag_path_including_after_analysis() {
    let (bridge, epoch) = ready();
    bridge.overlay(epoch, Some([35, 45, 45, 55])).unwrap();
    bridge
        .frame(
            epoch,
            RgbFrame::new(100, 100, vec![7; 30_000]).unwrap(),
            Duration::ZERO,
        )
        .unwrap();
    let (_, mut input) = bridge.open().unwrap();
    assert!(matches!(
        input.move_piece(A, B, MoveMode::Drag, &AtomicBool::new(false)),
        Err(InputError::NotDispatched(_))
    ));
    assert!(matches!(
        input.tap(Point { x: 40., y: 50. }, &AtomicBool::new(false)),
        Err(InputError::NotDispatched(_))
    ));
    // This segment's bounding box overlaps the controls, but its line stays outside them.
    let job = thread::spawn(move || {
        input.move_piece(
            Point { x: 20., y: 20. },
            Point { x: 60., y: 50. },
            MoveMode::Drag,
            &AtomicBool::new(false),
        )
    });
    let a = action(&bridge, epoch);
    bridge.overlay(epoch, Some([20, 20, 30, 30])).unwrap();
    assert!(!bridge.gesture_current(epoch, a["id"].as_u64().unwrap()));
    bridge.complete(epoch, a["id"].as_u64().unwrap(), 1);
    assert!(matches!(
        job.join().unwrap(),
        Err(InputError::NotDispatched(_))
    ));
    bridge.overlay(epoch, None).unwrap();
    assert!(bridge.take_frame_request(epoch));
}
#[test]
fn moving_controls_away_still_requires_a_new_observation_before_input() {
    let (bridge, epoch) = ready();
    let (mut capture, mut input) = bridge.open().unwrap();
    capture.capture().unwrap();
    bridge.overlay(epoch, Some([0, 0, 10, 10])).unwrap();
    bridge
        .frame(
            epoch,
            RgbFrame::new(100, 100, vec![0; 30_000]).unwrap(),
            Duration::ZERO,
        )
        .unwrap();
    assert!(matches!(
        input.move_piece(A, B, MoveMode::Drag, &AtomicBool::new(false)),
        Err(InputError::NotDispatched(_))
    ));
    capture.capture().unwrap();
    let geometry = chesspilot_core::board::BoardGeometry::new(20., 20., 5.).unwrap();
    assert!(capture.validate_board(geometry).is_ok());
    bridge.overlay(epoch, Some([80, 80, 90, 90])).unwrap();
    assert!(capture.validate_board(geometry).is_err());
}
