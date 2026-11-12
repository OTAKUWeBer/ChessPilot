use chesspilot_core::{
    board::{BoardGeometry, Point},
    config::{MoveMode, Settings},
    detection::{DetectedBoard, Detection},
    Color,
};
use chesspilot_runtime::{
    controller::{self, Analyzer, Automation, BoardSource, PlayError},
    desktop::{input::InputError, CaptureBounds, Observation, RawObservation},
    engine::{Analysis, Score},
};
use std::{
    collections::VecDeque,
    sync::atomic::{AtomicBool, Ordering},
    time::{Duration, Instant},
};
const START: &str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1";
const E4: &str = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b - e3 0 1";
fn observation(fen: &str) -> Observation {
    Observation {
        board: DetectedBoard {
            geometry: BoardGeometry::new(100., 50., 80.).unwrap(),
            fen: fen.into(),
        },
        source: CaptureBounds {
            x: -1000,
            y: 200,
            width: 1920,
            height: 1080,
        },
        captured_at: Instant::now(),
        inference_count: 1,
    }
}
struct Source {
    positions: VecDeque<Result<Observation, String>>,
    menus: VecDeque<Result<RawObservation, String>>,
    reads: usize,
    raw_reads: usize,
}
impl Source {
    fn new(fens: &[&str]) -> Self {
        Self {
            positions: fens.iter().map(|fen| Ok(observation(fen))).collect(),
            menus: VecDeque::new(),
            reads: 0,
            raw_reads: 0,
        }
    }
}
impl BoardSource for Source {
    fn observe(&mut self, _: Color, _: &AtomicBool) -> Result<Observation, String> {
        self.reads += 1;
        self.positions
            .pop_front()
            .unwrap_or_else(|| Err("No readable board".into()))
    }
    fn raw(&mut self, _: &AtomicBool) -> Result<RawObservation, String> {
        self.raw_reads += 1;
        self.menus
            .pop_front()
            .unwrap_or_else(|| Err("No dialog".into()))
    }
}
struct Engine {
    result: Result<Analysis, String>,
    fen: String,
    stop: bool,
}
impl Engine {
    fn new(mv: &str, fen: &str) -> Self {
        Self {
            result: Ok(Analysis {
                best_move: Some(mv.into()),
                updated_fen: Some(fen.into()),
                score: Some(Score::Centipawns(30)),
                depth: 15,
                stopped: false,
            }),
            fen: String::new(),
            stop: false,
        }
    }
}
impl Analyzer for Engine {
    fn analyze(
        &mut self,
        depth: u32,
        fen: &str,
        cancelled: &AtomicBool,
        progress: &mut dyn FnMut(u32, Option<Score>),
    ) -> Result<Analysis, String> {
        self.fen = fen.into();
        progress(depth, Some(Score::Centipawns(30)));
        if self.stop {
            cancelled.store(true, Ordering::Release);
        }
        self.result.clone()
    }
}
#[derive(Debug, PartialEq)]
enum Event {
    Move(Point, Point, MoveMode),
    Tap(Point),
}
#[derive(Default)]
struct Input {
    events: Vec<Event>,
    fail: Option<InputError>,
    stop: bool,
    waits: Vec<Duration>,
}
impl Automation for Input {
    fn move_piece(
        &mut self,
        start: Point,
        end: Point,
        mode: MoveMode,
        cancelled: &AtomicBool,
    ) -> Result<(), InputError> {
        self.events.push(Event::Move(start, end, mode));
        if self.stop {
            cancelled.store(true, Ordering::Release);
        }
        self.fail.take().map_or(Ok(()), Err)
    }
    fn tap(&mut self, point: Point, _: &AtomicBool) -> Result<(), InputError> {
        self.events.push(Event::Tap(point));
        self.fail.take().map_or(Ok(()), Err)
    }
    fn wait(&mut self, duration: Duration, cancelled: &AtomicBool) -> Result<(), InputError> {
        self.waits.push(duration);
        if cancelled.load(Ordering::Acquire) {
            Err(InputError::Cancelled { dispatched: false })
        } else {
            Ok(())
        }
    }
}
#[test]
fn normal_moves_in_both_orientations_commit_only_visual_confirmation() {
    for (color, before, after, mv, x) in [
        (Color::White, START, E4, "e2e4", -540.),
        (
            Color::Black,
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b - - 0 1",
            "rnbqkbnr/pppp1ppp/8/4p3/8/8/PPPPPPPP/RNBQKBNR w - e6 0 2",
            "e7e5",
            -620.,
        ),
    ] {
        for mode in [MoveMode::Drag, MoveMode::Click] {
            let mut source = Source::new(&[before, before, after]);
            let mut input = Input::default();
            let mut engine = Engine::new(mv, after);
            let settings = Settings {
                move_mode: mode,
                ..Settings::default()
            };
            let result = controller::play(
                &mut source,
                &mut input,
                &mut engine,
                &settings,
                color,
                &AtomicBool::new(false),
                |_| {},
            )
            .unwrap();
            assert_eq!(result.confirmed_fen.as_deref(), Some(after));
            assert_eq!(source.reads, 3);
            assert_eq!(
                input.events,
                vec![Event::Move(
                    Point { x, y: 770. },
                    Point { x, y: 610. },
                    mode
                )]
            );
            assert!(engine.fen.contains(if color == Color::White {
                " w kq "
            } else {
                " b KQ "
            }));
        }
    }
}
#[test]
fn changed_stale_or_cancelled_work_never_dispatches() {
    for case in 0..6 {
        let mut source = Source::new(&[START, START, E4]);
        let mut input = Input::default();
        let mut engine = Engine::new("e2e4", E4);
        match case {
            0 => source.positions[1] = Ok(observation(E4)),
            1 => source.positions[1].as_mut().unwrap().board.geometry.x += 8.,
            2 => source.positions[1].as_mut().unwrap().source.x += 1,
            3 => {
                source.positions[1].as_mut().unwrap().captured_at =
                    Instant::now() - Duration::from_secs(4)
            }
            4 => engine.stop = true,
            5 => engine.result = Err("Engine failed".into()),
            _ => unreachable!(),
        }
        let error = controller::play(
            &mut source,
            &mut input,
            &mut engine,
            &Settings::default(),
            Color::White,
            &AtomicBool::new(false),
            |_| {},
        )
        .err()
        .unwrap();
        assert!(
            match case {
                0 => matches!(error, PlayError::PositionChanged),
                1 | 2 => matches!(error, PlayError::GeometryChanged),
                3 => matches!(error, PlayError::StaleCapture),
                4 => matches!(error, PlayError::Stopped),
                5 => matches!(error, PlayError::Engine(_)),
                _ => false,
            },
            "case {case}: {error}"
        );
        assert!(input.events.is_empty());
    }
}
#[test]
fn uncertain_delivery_missing_confirmation_and_stop_do_not_repeat_the_move() {
    for case in 0..3 {
        let mut source = Source::new(&[START, START, START, START]);
        let mut input = Input::default();
        let mut engine = Engine::new("e2e4", E4);
        if case == 0 {
            input.fail = Some(InputError::Uncertain("lost acknowledgement".into()));
        }
        if case == 2 {
            input.stop = true;
        }
        let error = controller::play(
            &mut source,
            &mut input,
            &mut engine,
            &Settings::default(),
            Color::White,
            &AtomicBool::new(false),
            |_| {},
        )
        .err()
        .unwrap();
        assert!(match case {
            0 => matches!(error, PlayError::Input(InputError::Uncertain(_))),
            1 => matches!(error, PlayError::VerificationFailed),
            2 => matches!(error, PlayError::Stopped),
            _ => false,
        });
        assert_eq!(input.events.len(), 1);
    }
}
#[test]
fn all_castles_observe_automatic_rook_or_dispatch_one_confirmed_fallback() {
    for (color, mv, before, king_only, after) in [
        (
            Color::White,
            "e1g1",
            "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1",
            "r3k2r/8/8/8/8/8/8/R5KR w - - 0 1",
            "r3k2r/8/8/8/8/8/8/R4RK1 b - - 1 1",
        ),
        (
            Color::White,
            "e1c1",
            "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1",
            "r3k2r/8/8/8/8/8/8/R1K4R w - - 0 1",
            "r3k2r/8/8/8/8/8/8/2KR3R b - - 1 1",
        ),
        (
            Color::Black,
            "e8g8",
            "r3k2r/8/8/8/8/8/8/R3K2R b - - 0 1",
            "r5kr/8/8/8/8/8/8/R3K2R b - - 0 1",
            "r4rk1/8/8/8/8/8/8/R3K2R w - - 1 2",
        ),
        (
            Color::Black,
            "e8c8",
            "r3k2r/8/8/8/8/8/8/R3K2R b - - 0 1",
            "r1k4r/8/8/8/8/8/8/R3K2R b - - 0 1",
            "2kr3r/8/8/8/8/8/8/R3K2R w - - 1 2",
        ),
    ] {
        for automatic in [false, true] {
            let positions = if automatic {
                vec![before, before, after]
            } else {
                vec![before, before, king_only, after]
            };
            let mut source = Source::new(&positions);
            let mut input = Input::default();
            let mut engine = Engine::new(mv, after);
            let settings = Settings {
                kingside: true,
                queenside: true,
                ..Settings::default()
            };
            let result = controller::play(
                &mut source,
                &mut input,
                &mut engine,
                &settings,
                color,
                &AtomicBool::new(false),
                |_| {},
            )
            .unwrap();
            assert_eq!(result.confirmed_fen.as_deref(), Some(after));
            assert_eq!(input.events.len(), if automatic { 1 } else { 2 });
        }
        let mut source = Source::new(&[before, before, before, before]);
        let mut input = Input::default();
        let mut engine = Engine::new(mv, after);
        assert!(controller::play(
            &mut source,
            &mut input,
            &mut engine,
            &Settings {
                kingside: true,
                queenside: true,
                ..Settings::default()
            },
            color,
            &AtomicBool::new(false),
            |_| {}
        )
        .is_err());
        assert_eq!(
            input.events.len(),
            1,
            "An unchanged/unreadable board must not trigger a rook move"
        );
    }
}
fn promotion_menu(color: Color) -> RawObservation {
    let col = if color == Color::White { 0 } else { 7 };
    let mut boxes = vec![Detection {
        x: 100.,
        y: 50.,
        width: 640.,
        height: 640.,
        class_id: 12,
        confidence: 0.95,
    }];
    for (step, class_id) in if color == Color::White {
        [10, 7, 9, 8]
    } else {
        [4, 1, 3, 2]
    }
    .into_iter()
    .enumerate()
    {
        boxes.push(Detection {
            x: 110. + col as f64 * 80.,
            y: 60. + step as f64 * 80.,
            width: 60.,
            height: 60.,
            class_id,
            confidence: 0.95,
        });
    }
    RawObservation {
        boxes,
        source: observation(START).source,
        captured_at: Instant::now(),
        inference_count: 1,
    }
}
#[test]
fn every_promotion_piece_is_selected_once_in_both_orientations() {
    for color in [Color::White, Color::Black] {
        for (step, piece) in ['q', 'r', 'b', 'n'].into_iter().enumerate() {
            let before = if color == Color::White {
                "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
            } else {
                "4k3/8/8/8/8/8/p7/4K3 b - - 0 1"
            };
            let after = if color == Color::White {
                format!(
                    "{}3k3/8/8/8/8/8/8/4K3 b - - 0 1",
                    piece.to_ascii_uppercase()
                )
            } else {
                format!("4k3/8/8/8/8/8/8/{}3K3 w - - 0 2", piece)
            };
            let mv = format!(
                "{}{}",
                if color == Color::White {
                    "a7a8"
                } else {
                    "a2a1"
                },
                piece
            );
            let mut source = Source::new(&[before, before, &after]);
            source.menus.push_back(Ok(promotion_menu(color)));
            let mut input = Input::default();
            let mut engine = Engine::new(&mv, &after);
            let result = controller::play(
                &mut source,
                &mut input,
                &mut engine,
                &Settings::default(),
                color,
                &AtomicBool::new(false),
                |_| {},
            )
            .unwrap();
            assert_eq!(result.confirmed_fen.as_deref(), Some(after.as_str()));
            assert_eq!(source.raw_reads, 1);
            assert_eq!(input.events.len(), 2);
            assert_eq!(
                input.events[1],
                Event::Tap(Point {
                    x: if color == Color::White { -860. } else { -300. },
                    y: 290. + step as f64 * 80.
                })
            );
        }
    }
}
#[test]
fn missing_or_ambiguous_promotion_menu_is_never_blindly_clicked() {
    let before = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1";
    let after = "N3k3/8/8/8/8/8/8/4K3 b - - 0 1";
    for ambiguous in [false, true] {
        let mut source = Source::new(&[before, before]);
        if ambiguous {
            let mut raw = promotion_menu(Color::White);
            raw.boxes.push(raw.boxes[1]);
            source.menus.push_back(Ok(raw));
        }
        let mut input = Input::default();
        let mut engine = Engine::new("a7a8n", after);
        assert!(controller::play(
            &mut source,
            &mut input,
            &mut engine,
            &Settings::default(),
            Color::White,
            &AtomicBool::new(false),
            |_| {}
        )
        .is_err());
        assert_eq!(input.events.len(), 1);
        assert_eq!(source.raw_reads, 10);
    }
}
#[test]
fn no_legal_move_and_capture_failure_never_send_input() {
    let mut source = Source::new(&[START]);
    let mut input = Input::default();
    let mut engine = Engine::new("e2e4", E4);
    engine.result = Ok(Analysis {
        best_move: None,
        updated_fen: None,
        score: None,
        depth: 15,
        stopped: false,
    });
    let result = controller::play(
        &mut source,
        &mut input,
        &mut engine,
        &Settings::default(),
        Color::White,
        &AtomicBool::new(false),
        |_| {},
    )
    .unwrap();
    assert!(result.confirmed_fen.is_none());
    assert!(input.events.is_empty());
    let mut source = Source::new(&[]);
    assert!(controller::play(
        &mut source,
        &mut input,
        &mut engine,
        &Settings::default(),
        Color::White,
        &AtomicBool::new(false),
        |_| {}
    )
    .is_err());
    assert_eq!(source.reads, 3);
    assert!(input.events.is_empty());
}

#[test]
fn auto_queen_needs_no_menu_tap_and_never_confirms_an_underpromotion() {
    let before = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1";
    let queen = "Q3k3/8/8/8/8/8/8/4K3 b - - 0 1";
    for wanted in ['q', 'n'] {
        let mut source = Source::new(&[before, before, queen, queen, queen, queen]);
        let boxes = [
            (100., 50., 640., 640., 12),
            (110., 60., 60., 60., 10),
            (430., 60., 60., 60., 5),
            (430., 620., 60., 60., 11),
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
        .collect();
        source.menus.push_back(Ok(RawObservation {
            boxes,
            source: observation(before).source,
            captured_at: Instant::now(),
            inference_count: 1,
        }));
        let expected = if wanted == 'q' {
            queen
        } else {
            "N3k3/8/8/8/8/8/8/4K3 b - - 0 1"
        };
        let mut engine = Engine::new(&format!("a7a8{wanted}"), expected);
        let mut input = Input::default();
        let result = controller::play(
            &mut source,
            &mut input,
            &mut engine,
            &Settings::default(),
            Color::White,
            &AtomicBool::new(false),
            |_| {},
        );
        if wanted == 'q' {
            assert_eq!(result.unwrap().confirmed_fen.as_deref(), Some(queen));
            assert_eq!(source.reads, 2);
        } else {
            assert!(matches!(result, Err(PlayError::VerificationFailed)));
        }
        assert_eq!(
            input.events.len(),
            1,
            "Auto-promotion must not cause a menu tap or another pawn move"
        );
    }
}
