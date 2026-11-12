use chesspilot_core::{
    board::{BoardGeometry, Point},
    config::MoveMode,
    detection::Detection,
    Color,
};
use chesspilot_runtime::{
    desktop::{
        input::{windows_move, windows_tap, InputError, PixelPoint, Pointer},
        observe, Capture, CaptureBounds, CapturedFrame,
    },
    vision::{BoardReader, Predictor, RgbFrame},
};
use std::{
    sync::atomic::{AtomicBool, Ordering},
    time::Duration,
};

#[test]
fn capture_points_keep_origin_and_python_rounding() {
    let source = CaptureBounds {
        x: -1920,
        y: -100,
        width: 1920,
        height: 1080,
    };
    let center = BoardGeometry::new(100.5, 50., 80.5)
        .unwrap()
        .center(4, 7)
        .unwrap();
    let mapped = source.input_point(center).unwrap();
    assert_eq!(
        mapped,
        Point {
            x: -1457.5,
            y: 553.5
        }
    );
    assert_eq!(
        PixelPoint::try_from(mapped).unwrap(),
        PixelPoint { x: -1458, y: 554 }
    );
    for point in [
        Point { x: -0.1, y: 0. },
        Point { x: 1920., y: 0. },
        Point { x: 0., y: 1080. },
        Point { x: f64::NAN, y: 0. },
    ] {
        assert!(source.input_point(point).is_err());
    }
    assert!(PixelPoint::try_from(Point {
        x: i32::MAX as f64 + 1.,
        y: 0.
    })
    .is_err());
}
struct Source {
    calls: usize,
}
impl Capture for Source {
    fn capture(&mut self) -> Result<CapturedFrame, String> {
        self.calls += 1;
        Ok(CapturedFrame::new(
            RgbFrame::new(800, 800, vec![0; 800 * 800 * 3])?,
            -1000,
            200,
        ))
    }
}
struct Model;
impl Predictor for Model {
    fn predict(&mut self, _: &RgbFrame) -> Result<Vec<Detection>, String> {
        Ok([
            (0., 0., 800., 800., 12),
            (410., 10., 80., 80., 5),
            (410., 710., 80., 80., 11),
        ]
        .into_iter()
        .map(|(x, y, width, height, class_id)| Detection {
            x,
            y,
            width,
            height,
            class_id,
            confidence: 0.95,
        })
        .collect())
    }
}
#[test]
fn observation_uses_one_capture_and_keeps_model_and_desktop_spaces_separate() {
    let mut source = Source { calls: 0 };
    let mut reader = BoardReader::new(Model);
    for (color, expected) in [
        (Color::White, "4k3/8/8/8/8/8/8/4K3 w - - 0 1"),
        (Color::Black, "3K4/8/8/8/8/8/8/3k4 b - - 0 1"),
    ] {
        let observation =
            observe(&mut source, &mut reader, color, &AtomicBool::new(false)).unwrap();
        assert_eq!(observation.board.fen, expected);
        assert_eq!(observation.inference_count, 1);
        assert_eq!(observation.board.geometry.x, 0.);
        assert_eq!(
            observation
                .source
                .input_point(observation.board.geometry.center(4, 7).unwrap())
                .unwrap(),
            Point { x: -550., y: 950. }
        );
        assert!(observation.captured_at.elapsed() < Duration::from_secs(1));
    }
    assert_eq!(source.calls, 2);
    assert!(observe(
        &mut source,
        &mut reader,
        Color::White,
        &AtomicBool::new(true)
    )
    .is_err());
    assert_eq!(source.calls, 2);
}
#[derive(Debug, Clone, PartialEq, Eq)]
enum Event {
    Move(PixelPoint),
    Button(bool),
    Wait(u64),
}
struct Recording<'a> {
    events: Vec<Event>,
    fail_at: Option<usize>,
    stop_at: Option<usize>,
    cancelled: &'a AtomicBool,
}
impl Recording<'_> {
    fn record(&mut self, event: Event) -> Result<(), String> {
        let index = self.events.len();
        self.events.push(event);
        if self.stop_at == Some(index) {
            self.cancelled.store(true, Ordering::Release);
        }
        if self.fail_at == Some(index) {
            Err("injected OS failure".into())
        } else {
            Ok(())
        }
    }
}
impl Pointer for Recording<'_> {
    fn move_to(&mut self, point: PixelPoint) -> Result<(), String> {
        self.record(Event::Move(point))
    }
    fn left_button(&mut self, down: bool) -> Result<(), String> {
        self.record(Event::Button(down))
    }
    fn wait(&mut self, duration: Duration) {
        self.record(Event::Wait(duration.as_millis() as u64))
            .unwrap();
    }
}
fn points() -> (Point, Point) {
    (Point { x: 10.5, y: 20.5 }, Point { x: 80.5, y: 90.5 })
}
#[test]
fn windows_drag_and_click_preserve_python_order_and_timing() {
    for mode in [MoveMode::Drag, MoveMode::Click] {
        let cancelled = AtomicBool::new(false);
        let mut pointer = Recording {
            events: vec![],
            fail_at: None,
            stop_at: None,
            cancelled: &cancelled,
        };
        let (start, end) = points();
        windows_move(&mut pointer, start, end, mode, &cancelled).unwrap();
        let physical: Vec<_> = pointer
            .events
            .iter()
            .filter(|e| !matches!(e, Event::Wait(_)))
            .cloned()
            .collect();
        let expected = if mode == MoveMode::Drag {
            vec![
                Event::Move(PixelPoint { x: 10, y: 20 }),
                Event::Button(true),
                Event::Move(PixelPoint { x: 46, y: 56 }),
                Event::Move(PixelPoint { x: 80, y: 90 }),
                Event::Button(false),
            ]
        } else {
            vec![
                Event::Move(PixelPoint { x: 10, y: 20 }),
                Event::Button(true),
                Event::Button(false),
                Event::Move(PixelPoint { x: 80, y: 90 }),
                Event::Button(true),
                Event::Button(false),
            ]
        };
        assert_eq!(physical, expected);
        let elapsed: u64 = pointer
            .events
            .iter()
            .map(|e| if let Event::Wait(ms) = e { *ms } else { 0 })
            .sum();
        assert_eq!(elapsed, if mode == MoveMode::Drag { 100 } else { 40 });
    }
}
#[test]
fn cancellation_or_failure_never_replays_and_always_attempts_button_release() {
    for mode in [MoveMode::Drag, MoveMode::Click] {
        for stopped in [false, true] {
            for index in 0..30 {
                let cancelled = AtomicBool::new(false);
                let mut pointer = Recording {
                    events: vec![],
                    fail_at: None,
                    stop_at: None,
                    cancelled: &cancelled,
                };
                // Inject OS failure only at physical events; cancellation can happen at any wait.
                let (start, end) = points();
                windows_move(&mut pointer, start, end, mode, &cancelled).unwrap();
                if index >= pointer.events.len() {
                    continue;
                }
                if !stopped && matches!(pointer.events[index], Event::Wait(_)) {
                    continue;
                }
                pointer.events.clear();
                if stopped {
                    pointer.stop_at = Some(index);
                } else {
                    pointer.fail_at = Some(index);
                }
                let result = windows_move(&mut pointer, start, end, mode, &cancelled);
                if stopped
                    && index == pointer.events.len() - 1
                    && pointer.events[index] == Event::Button(false)
                {
                    assert!(matches!(result, Err(InputError::Cancelled { .. })));
                } else {
                    assert!(result.is_err(), "mode {mode:?}, index {index}");
                }
                if pointer.events.contains(&Event::Button(true)) {
                    assert_eq!(
                        pointer
                            .events
                            .iter()
                            .rev()
                            .find(|e| matches!(e, Event::Button(_))),
                        Some(&Event::Button(false))
                    );
                }
                assert!(
                    pointer.events.len() <= index + 3,
                    "No replay after a failure"
                );
                if !stopped && index == 0 {
                    assert!(matches!(result, Err(InputError::NotDispatched(_))));
                }
                if !stopped && index > 0 {
                    assert!(matches!(result, Err(InputError::Uncertain(_))));
                }
            }
        }
    }
}

#[test]
fn invalid_or_already_cancelled_input_sends_no_events() {
    for cancelled in [false, true] {
        let flag = AtomicBool::new(cancelled);
        let mut pointer = Recording {
            events: vec![],
            fail_at: None,
            stop_at: None,
            cancelled: &flag,
        };
        let (mut start, end) = points();
        if !cancelled {
            start.x = f64::NAN;
        }
        let result = windows_move(&mut pointer, start, end, MoveMode::Drag, &flag);
        assert!(result.is_err());
        assert!(pointer.events.is_empty());
    }
}

#[test]
fn promotion_tap_uses_fifty_milliseconds_and_releases_on_cancellation() {
    for stop_at in [None, Some(3)] {
        let flag = AtomicBool::new(false);
        let mut pointer = Recording {
            events: vec![],
            fail_at: None,
            stop_at,
            cancelled: &flag,
        };
        let result = windows_tap(&mut pointer, Point { x: 10., y: 20. }, &flag);
        if stop_at.is_some() {
            assert!(matches!(
                result,
                Err(InputError::Cancelled { dispatched: true })
            ));
        } else {
            result.unwrap();
            assert_eq!(
                pointer
                    .events
                    .iter()
                    .filter(|e| matches!(e, Event::Wait(5)))
                    .count(),
                10
            );
        }
        assert_eq!(
            pointer
                .events
                .iter()
                .filter(|e| **e == Event::Button(true))
                .count(),
            1
        );
        assert_eq!(pointer.events.last(), Some(&Event::Button(false)));
    }
}
