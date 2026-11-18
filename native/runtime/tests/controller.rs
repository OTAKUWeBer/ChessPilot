use chesspilot_core::{
    board::{BoardGeometry, Point},
    config::{MoveMode, Settings},
    detection::{DetectedBoard, Detection},
    Color,
};
use chesspilot_runtime::{
    controller::{
        self, Analyzer, AutoRequest, Automation, BoardSource, History, KnownPosition, PlayError,
        Progress,
    },
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
    fn reconcile_reply(
        &mut self,
        _: &str,
        observed: &str,
        _: &AtomicBool,
    ) -> Result<Option<String>, String> {
        Ok(self
            .result
            .as_ref()
            .ok()
            .and_then(|a| a.updated_fen.as_ref())
            .filter(|fen| fen.split_whitespace().next() == observed.split_whitespace().next())
            .cloned())
    }
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
impl History for Engine {
    fn has_legal_moves(&mut self, _: &str, _: &AtomicBool) -> Result<bool, String> {
        Ok(true)
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
    stop_after_wait: Option<usize>,
}
impl Automation for Input {
    fn humanize(&mut self, point: Point, _: f64, _: f64) -> Result<Point, String> {
        Ok(point)
    }
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
        if self.stop_after_wait == Some(self.waits.len()) {
            cancelled.store(true, Ordering::Release);
        }
        if cancelled.load(Ordering::Acquire) {
            Err(InputError::Cancelled { dispatched: false })
        } else {
            Ok(())
        }
    }
}

const E5: &str = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2";
const NF3: &str = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2";
fn rights(fen: &str, value: &str) -> String {
    let mut parts: Vec<_> = fen.split_whitespace().collect();
    parts[2] = value;
    parts.join(" ")
}
fn known(fen: &str) -> KnownPosition {
    let o = observation(fen);
    KnownPosition {
        fen: fen.into(),
        geometry: o.board.geometry,
        source: o.source,
    }
}
struct HistoryEngine {
    analysis: Analysis,
    expected_input: String,
    replies: Vec<(String, String, String)>,
    analyzed: usize,
    reconciled: usize,
    has_moves: bool,
}
impl HistoryEngine {
    fn new(fen: &str, mv: &str, after: &str) -> Self {
        Self {
            analysis: Engine::new(mv, after).result.unwrap(),
            expected_input: fen.into(),
            replies: vec![],
            analyzed: 0,
            reconciled: 0,
            has_moves: true,
        }
    }
}
impl Analyzer for HistoryEngine {
    fn analyze(
        &mut self,
        _: u32,
        fen: &str,
        _: &AtomicBool,
        _: &mut dyn FnMut(u32, Option<Score>),
    ) -> Result<Analysis, String> {
        assert_eq!(fen, self.expected_input);
        self.analyzed += 1;
        Ok(self.analysis.clone())
    }
    fn reconcile_reply(
        &mut self,
        before: &str,
        observed: &str,
        _: &AtomicBool,
    ) -> Result<Option<String>, String> {
        self.reconciled += 1;
        Ok(self
            .replies
            .iter()
            .find(|(a, b, _)| {
                a == before && b.split_whitespace().next() == observed.split_whitespace().next()
            })
            .map(|(_, _, fen)| fen.clone()))
    }
}
impl History for HistoryEngine {
    fn has_legal_moves(&mut self, _: &str, _: &AtomicBool) -> Result<bool, String> {
        Ok(self.has_moves)
    }
}
#[test]
fn auto_without_history_plays_and_verifies_once_before_waiting_for_the_opponent() {
    for color in [Color::White, Color::Black] {
        for mode in [MoveMode::Drag, MoveMode::Click] {
            let (before, mv, after) = if color == Color::White {
                (rights(START, "KQkq"), "e2e4", rights(E4, "KQkq"))
            } else {
                (
                    rights(START, "KQkq").replace(" w ", " b "),
                    "e7e5",
                    "rnbqkbnr/pppp1ppp/8/4p3/8/8/PPPPPPPP/RNBQKBNR w KQkq e6 0 2".into(),
                )
            };
            let mut source = Source::new(&[&before, &before, &after]);
            let mut input = Input::default();
            let mut engine = HistoryEngine::new(&before, mv, &after);
            let settings = Settings {
                kingside: true,
                queenside: true,
                move_mode: mode,
                ..Settings::default()
            };
            let cancelled = AtomicBool::new(false);
            let mut confirmed = Vec::new();
            let result = controller::auto_play(
                &mut source,
                &mut input,
                &mut engine,
                AutoRequest {
                    settings: &settings,
                    color,
                    position: None,
                },
                &cancelled,
                |event| match event {
                    Progress::Played(outcome) => confirmed.push(outcome.confirmed_fen.unwrap()),
                    Progress::Status("Waiting for opponent...") => {
                        cancelled.store(true, Ordering::Release)
                    }
                    _ => {}
                },
            );
            assert!(matches!(result, Err(PlayError::Stopped)));
            assert_eq!(confirmed, [after]);
            assert_eq!(source.reads, 3);
            assert_eq!(engine.analyzed, 1);
            assert_eq!(input.events.len(), 1);
            assert!(input.waits.contains(&Duration::from_millis(300)));
        }
    }
}
#[test]
fn initial_auto_detection_cancellation_and_uncertain_moves_never_start_a_reply_loop() {
    let start = rights(START, "KQkq");
    let after = rights(E4, "KQkq");
    let settings = Settings {
        kingside: true,
        queenside: true,
        ..Settings::default()
    };
    for case in 0..6 {
        let fens: &[&str] = match case {
            0 => &[],
            1 => &[&start, &after],
            _ => &[&start, &start, &start, &start],
        };
        let mut source = Source::new(fens);
        let mut input = Input {
            fail: (case == 2).then(|| InputError::Uncertain("unknown delivery".into())),
            stop: case == 5,
            ..Input::default()
        };
        let mut engine = HistoryEngine::new(&start, "e2e4", &after);
        let mut committed = false;
        let result = controller::auto_play(
            &mut source,
            &mut input,
            &mut engine,
            AutoRequest {
                settings: &settings,
                color: Color::White,
                position: None,
            },
            &AtomicBool::new(case == 4),
            |event| {
                if matches!(event, Progress::Played(_) | Progress::Observed(_)) {
                    committed = true;
                }
            },
        );
        assert!(result.is_err(), "case {case}");
        assert!(!committed, "case {case}");
        assert_eq!(
            input.events.len(),
            usize::from(matches!(case, 2 | 3 | 5)),
            "case {case}"
        );
        assert!(engine.analyzed <= 1);
    }
}
#[test]
fn initial_auto_with_no_legal_move_stops_without_input() {
    let start = rights(START, "KQkq");
    let mut source = Source::new(&[&start]);
    let mut input = Input::default();
    let mut engine = HistoryEngine::new(&start, "e2e4", E4);
    engine.analysis.best_move = None;
    engine.analysis.updated_fen = None;
    let settings = Settings {
        kingside: true,
        queenside: true,
        ..Settings::default()
    };
    let mut terminal = false;
    controller::auto_play(
        &mut source,
        &mut input,
        &mut engine,
        AutoRequest {
            settings: &settings,
            color: Color::White,
            position: None,
        },
        &AtomicBool::new(false),
        |event| {
            if matches!(event, Progress::Terminal) {
                terminal = true;
            }
        },
    )
    .unwrap();
    assert!(terminal);
    assert!(input.events.is_empty());
    assert_eq!(source.reads, 1);
    assert_eq!(engine.analyzed, 1);
}
#[test]
fn auto_waits_for_a_stable_legal_reply_and_preserves_lost_rights_and_en_passant_metadata() {
    for flags in ["KQkq", "q"] {
        let seed = rights(E4, flags);
        let reply = rights(E5, flags);
        let after = rights(NF3, flags);
        let mut source = Source::new(&[&seed, &reply, &reply, &reply, &reply, &after]);
        let mut input = Input::default();
        let mut engine = HistoryEngine::new(&reply, "g1f3", &after);
        engine
            .replies
            .push((seed.clone(), reply.clone(), reply.clone()));
        let settings = Settings {
            kingside: true,
            queenside: true,
            ..Settings::default()
        };
        let flag = AtomicBool::new(false);
        let mut observed = vec![];
        let mut played = vec![];
        let result = controller::auto_play(
            &mut source,
            &mut input,
            &mut engine,
            AutoRequest {
                settings: &settings,
                color: Color::White,
                position: Some(known(&seed)),
            },
            &flag,
            |event| match event {
                Progress::Observed(p) => observed.push(p.fen),
                Progress::Played(outcome) => {
                    played.push(outcome.confirmed_fen.unwrap());
                    flag.store(true, Ordering::Release);
                }
                _ => {}
            },
        );
        assert!(matches!(result, Err(PlayError::Stopped)));
        assert_eq!(observed, [reply]);
        assert_eq!(played, [after]);
        assert_eq!(engine.analyzed, 1);
        assert_eq!(engine.reconciled, 1);
        assert_eq!(input.events.len(), 1);
        assert!(input.waits.contains(&Duration::from_millis(900)));
        assert_eq!(source.reads, 6);
    }
}

#[test]
fn disabling_castling_for_analysis_does_not_erase_still_legal_history_rights() {
    let filtered_before = rights(E5, "kq");
    let filtered_after = rights(NF3, "kq");
    let mut source = Source::new(&[E5, E5, NF3]);
    let mut input = Input::default();
    let mut engine = HistoryEngine::new(&filtered_before, "g1f3", &filtered_after);
    engine
        .replies
        .push((E5.into(), filtered_after.clone(), NF3.into()));
    let position = known(E5);
    let outcome = controller::play_position(
        &mut source,
        &mut input,
        &mut engine,
        controller::PlayRequest {
            settings: &Settings::default(),
            color: Color::White,
            known_position: Some(&position),
        },
        &AtomicBool::new(false),
        |_| {},
    )
    .unwrap();
    assert_eq!(
        outcome.analysis.updated_fen.as_deref(),
        Some(filtered_after.as_str())
    );
    assert_eq!(outcome.confirmed_fen.as_deref(), Some(NF3));
    assert_eq!(input.events.len(), 1);
}
#[test]
fn unchanged_auto_frames_and_stop_do_not_search_or_move() {
    let mut source = Source::new(&[E4, E4]);
    let mut input = Input {
        stop_after_wait: Some(2),
        ..Input::default()
    };
    let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
    let result = controller::auto_play(
        &mut source,
        &mut input,
        &mut engine,
        AutoRequest {
            settings: &Settings::default(),
            color: Color::White,
            position: Some(known(E4)),
        },
        &AtomicBool::new(false),
        |_| {},
    );
    assert!(matches!(result, Err(PlayError::Stopped)));
    assert!(input.events.is_empty());
    assert_eq!(engine.analyzed, 0);
    assert_eq!(engine.reconciled, 0);
}

#[test]
fn manual_play_waits_for_a_legal_opponent_reply_instead_of_queueing_a_premove() {
    let seed = rights(E4, "KQkq");
    let mut source = Source::new(&[&seed, E5, E5, E5, E5, NF3]);
    let mut input = Input::default();
    let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
    engine.replies.push((seed.clone(), E5.into(), E5.into()));
    let settings = Settings {
        kingside: true,
        queenside: true,
        ..Settings::default()
    };
    let baseline = known(&seed);
    let result = controller::play_position(
        &mut source,
        &mut input,
        &mut engine,
        controller::PlayRequest {
            settings: &settings,
            color: Color::White,
            known_position: Some(&baseline),
        },
        &AtomicBool::new(false),
        |_| {},
    )
    .unwrap();
    assert_eq!(result.confirmed_fen.as_deref(), Some(NF3));
    assert_eq!(engine.analyzed, 1);
    assert_eq!(engine.reconciled, 1);
    assert_eq!(input.events.len(), 1);
    assert_eq!(source.reads, 6);
    assert!(input.waits.contains(&Duration::from_millis(900)));
}

#[test]
fn early_manual_play_can_be_stopped_without_searching_or_sending_input() {
    let mut source = Source::new(&[E4, E4]);
    let mut input = Input {
        stop_after_wait: Some(2),
        ..Input::default()
    };
    let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
    let baseline = known(E4);
    let result = controller::play_position(
        &mut source,
        &mut input,
        &mut engine,
        controller::PlayRequest {
            settings: &Settings::default(),
            color: Color::White,
            known_position: Some(&baseline),
        },
        &AtomicBool::new(false),
        |_| {},
    );
    assert!(matches!(result, Err(PlayError::Stopped)));
    assert_eq!(engine.analyzed, 0);
    assert!(input.events.is_empty());
}
#[test]
fn early_manual_play_returns_game_over_when_the_opponent_has_no_legal_reply() {
    let mut source = Source::new(&[]);
    let mut input = Input::default();
    let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
    engine.has_moves = false;
    let baseline = known(E4);
    let result = controller::play_position(
        &mut source,
        &mut input,
        &mut engine,
        controller::PlayRequest {
            settings: &Settings::default(),
            color: Color::White,
            known_position: Some(&baseline),
        },
        &AtomicBool::new(false),
        |_| {},
    )
    .unwrap();
    assert!(result.analysis.best_move.is_none());
    assert!(result.confirmed_fen.is_none());
    assert_eq!(engine.analyzed, 0);
    assert!(input.events.is_empty());
    assert_eq!(source.reads, 0);
}

#[test]
fn auto_ignores_the_three_pixel_detector_jitter_seen_in_the_windows_log() {
    let mut source = Source::new(&[E4, E4]);
    for current in &mut source.positions {
        current.as_mut().unwrap().board.geometry = BoardGeometry::new(724., 191., 130.88).unwrap();
    }
    let mut baseline = known(E4);
    baseline.geometry = BoardGeometry::new(724., 188., 130.75).unwrap();
    let mut input = Input {
        stop_after_wait: Some(2),
        ..Input::default()
    };
    let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
    let result = controller::auto_play(
        &mut source,
        &mut input,
        &mut engine,
        AutoRequest {
            settings: &Settings::default(),
            color: Color::White,
            position: Some(baseline),
        },
        &AtomicBool::new(false),
        |_| {},
    );
    assert!(matches!(result, Err(PlayError::Stopped)));
    assert_eq!(engine.analyzed, 0);
    assert!(input.events.is_empty());
}

#[test]
fn auto_rejects_changed_source_geometry_or_stale_frames_before_input() {
    for case in 0..3 {
        let mut source = Source::new(&[E4]);
        let current = source.positions[0].as_mut().unwrap();
        match case {
            0 => current.source.x += 1,
            1 => current.board.geometry.x += 8.,
            _ => current.captured_at = Instant::now() - Duration::from_secs(4),
        }
        let mut input = Input::default();
        let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
        let result = controller::auto_play(
            &mut source,
            &mut input,
            &mut engine,
            AutoRequest {
                settings: &Settings::default(),
                color: Color::White,
                position: Some(known(E4)),
            },
            &AtomicBool::new(false),
            |_| {},
        );
        assert!(if case == 2 {
            matches!(result, Err(PlayError::StaleCapture))
        } else {
            matches!(result, Err(PlayError::GeometryChanged))
        });
        assert!(input.events.is_empty());
        assert_eq!(engine.analyzed, 0);
    }
}
#[test]
fn auto_recovers_from_missing_and_partial_frames_before_one_legal_reply() {
    let mut source = Source::new(&[NF3, E4, E4, E5, E5, E5, E5, NF3]);
    for _ in 0..3 {
        source
            .positions
            .push_front(Err("Board temporarily hidden".into()));
    }
    let mut input = Input::default();
    let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
    engine.replies.push((E4.into(), E5.into(), E5.into()));
    let flag = AtomicBool::new(false);
    let mut confirmed = Vec::new();
    let result = controller::auto_play(
        &mut source,
        &mut input,
        &mut engine,
        AutoRequest {
            settings: &Settings {
                kingside: true,
                queenside: true,
                ..Settings::default()
            },
            color: Color::White,
            position: Some(known(E4)),
        },
        &flag,
        |event| {
            if let Progress::Played(outcome) = event {
                confirmed.push(outcome.confirmed_fen.unwrap());
                flag.store(true, Ordering::Release);
            }
        },
    );
    assert!(matches!(result, Err(PlayError::Stopped)));
    assert_eq!(confirmed, [NF3]);
    assert_eq!(engine.analyzed, 1);
    assert_eq!(engine.reconciled, 1);
    assert_eq!(input.events.len(), 1);
    assert_eq!(source.reads, 11);
    assert_eq!(
        &input.waits[..3],
        &[
            Duration::from_millis(500),
            Duration::from_millis(500),
            Duration::from_millis(200)
        ]
    );
}

#[test]
fn auto_bounds_capture_failures_and_unmatched_changes_without_sending_input() {
    for missing in [false, true] {
        let mut source = if missing {
            Source::new(&[])
        } else {
            Source::new(&[NF3; 6])
        };
        let mut input = Input::default();
        let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
        let result = controller::auto_play(
            &mut source,
            &mut input,
            &mut engine,
            AutoRequest {
                settings: &Settings::default(),
                color: Color::White,
                position: Some(known(E4)),
            },
            &AtomicBool::new(false),
            |_| {},
        );
        assert!(if missing {
            matches!(result, Err(PlayError::Detection(_)))
        } else {
            matches!(result, Err(PlayError::HistoryMismatch))
        });
        assert!(input.events.is_empty());
        assert_eq!(engine.analyzed, 0);
        assert_eq!(source.reads, if missing { 9 } else { 6 });
    }
}
#[test]
fn auto_terminal_and_uncertain_dispatch_stop_without_a_replay() {
    for terminal in [false, true] {
        let mut source = Source::new(&[E5, E5]);
        let mut input = Input {
            fail: Some(InputError::Uncertain("unknown delivery".into())),
            ..Input::default()
        };
        let mut engine = HistoryEngine::new(E5, "g1f3", NF3);
        engine.has_moves = !terminal;
        let settings = Settings {
            kingside: true,
            queenside: true,
            ..Settings::default()
        };
        let mut ended = false;
        let result = controller::auto_play(
            &mut source,
            &mut input,
            &mut engine,
            AutoRequest {
                settings: &settings,
                color: Color::White,
                position: Some(known(if terminal { E4 } else { E5 })),
            },
            &AtomicBool::new(false),
            |event| {
                if matches!(event, Progress::Terminal) {
                    ended = true;
                }
            },
        );
        if terminal {
            result.unwrap();
            assert!(ended);
            assert!(input.events.is_empty());
            assert_eq!(source.reads, 0);
        } else {
            assert!(matches!(
                result,
                Err(PlayError::Input(InputError::Uncertain(_)))
            ));
            assert_eq!(input.events.len(), 1);
        }
    }
}
#[test]
fn a_legal_immediate_opponent_reply_confirms_the_latest_board_without_replaying() {
    let seed = rights(E4, "KQkq");
    let start = rights(START, "KQkq");
    let mut source = Source::new(&[START, START, E5]);
    let mut input = Input::default();
    let mut engine = HistoryEngine::new(&start, "e2e4", &seed);
    engine.replies.push((seed.clone(), E5.into(), E5.into()));
    let result = controller::play(
        &mut source,
        &mut input,
        &mut engine,
        &Settings {
            kingside: true,
            queenside: true,
            ..Settings::default()
        },
        Color::White,
        &AtomicBool::new(false),
        |_| {},
    )
    .unwrap();
    assert_eq!(result.confirmed_fen.as_deref(), Some(E5));
    assert_eq!(result.analysis.updated_fen.as_deref(), Some(seed.as_str()));
    assert_eq!(input.events.len(), 1);
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
fn mating_move_is_verified_when_a_result_popup_hides_opponent_pieces() {
    let before = "4k3/2R3R1/7K/2p5/p7/6p1/6P1/8 w - - 1 28";
    let after = "2R1k3/6R1/7K/2p5/p7/6p1/6P1/8 b - - 2 28";
    let covered = "2R1k3/6R1/7K/8/p7/6p1/6P1/8 w - - 0 1";
    let mut source = Source::new(&[before, before, covered, covered]);
    for frame in source.positions.iter_mut().skip(2) {
        frame.as_mut().unwrap().board.geometry.y += 20.;
    }
    let mut engine = HistoryEngine::new(before, "c7c8", after);
    engine.analysis.score = Some(Score::Mate(1));
    engine.has_moves = false;
    let mut input = Input::default();
    let mut confirmed = None;
    let mut terminal = false;
    controller::auto_play(
        &mut source,
        &mut input,
        &mut engine,
        AutoRequest {
            settings: &Settings::default(),
            color: Color::White,
            position: None,
        },
        &AtomicBool::new(false),
        |progress| match progress {
            Progress::Played(outcome) => confirmed = outcome.confirmed_fen,
            Progress::Terminal => terminal = true,
            _ => {}
        },
    )
    .unwrap();
    assert_eq!(confirmed.as_deref(), Some(after));
    assert!(terminal);
    assert_eq!(input.events.len(), 1);
    assert_eq!(source.reads, 4);
}

#[test]
fn result_popup_verification_requires_delivered_mate_and_fresh_consistent_frames() {
    for color in [Color::White, Color::Black] {
        let orient = |fen: &str| {
            if color == Color::White {
                fen.to_owned()
            } else {
                fen.chars()
                    .map(|ch| {
                        if ch.is_ascii_uppercase() {
                            ch.to_ascii_lowercase()
                        } else if ch.is_ascii_lowercase() {
                            ch.to_ascii_uppercase()
                        } else {
                            ch
                        }
                    })
                    .collect::<String>()
                    .replace(" W ", " b ")
                    .replace(" B ", " w ")
            }
        };
        let before = orient("4k3/2R3R1/7K/2p5/p7/6p1/6P1/8 w - - 1 28");
        let after = orient("2R1k3/6R1/7K/2p5/p7/6p1/6P1/8 b - - 2 28");
        let covered = orient("2R1k3/6R1/7K/8/p7/6p1/6P1/8 w - - 0 1");
        for case in 0..11 {
            let mut source = Source::new(&[&before, &before, &covered, &covered]);
            for frame in source.positions.iter_mut().skip(2) {
                frame.as_mut().unwrap().board.geometry.y += 20.;
            }
            let mut engine = HistoryEngine::new(&before, "c7c8", &after);
            engine.analysis.score = Some(Score::Mate(1));
            engine.has_moves = false;
            let mut input = Input::default();
            match case {
                1 => source.positions[2].as_mut().unwrap().board.fen = before.clone(),
                2 => {
                    source.positions[2].as_mut().unwrap().board.fen =
                        orient("2R1k3/8/7K/8/p7/6p1/6P1/8 w - - 0 1")
                }
                3 => {
                    source.positions[2].as_mut().unwrap().board.fen =
                        orient("2R5/6R1/7K/8/p7/6p1/6P1/8 w - - 0 1")
                }
                4 => {
                    source.positions[2].as_mut().unwrap().board.fen =
                        orient("2R1k3/6R1/7K/2q5/p7/6p1/6P1/8 w - - 0 1")
                }
                5 => source.positions[2].as_mut().unwrap().source.x += 1,
                6 => {
                    source.positions[2].as_mut().unwrap().captured_at =
                        Instant::now() - Duration::from_secs(4)
                }
                7 => engine.analysis.score = Some(Score::Mate(3)),
                8 => engine.analysis.score = Some(Score::Mate(-1)),
                9 => engine.has_moves = true,
                10 => {
                    source.positions.pop_back();
                }
                _ => {}
            }
            let result = controller::play(
                &mut source,
                &mut input,
                &mut engine,
                &Settings::default(),
                color,
                &AtomicBool::new(false),
                |_| {},
            );
            if case == 0 {
                assert_eq!(
                    result.unwrap().confirmed_fen.as_deref(),
                    Some(after.as_str())
                );
            } else {
                assert!(result.is_err(), "color {color:?}, case {case}");
            }
            assert_eq!(input.events.len(), 1, "never replay an unverified move");
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
fn delayed_board_rendering_is_verified_without_sending_the_move_again() {
    let mut source = Source::new(&[START, START, START, START, START, E4]);
    let mut input = Input::default();
    let mut engine = Engine::new("e2e4", E4);
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
    assert_eq!(result.confirmed_fen.as_deref(), Some(E4));
    assert_eq!(input.events.len(), 1);
    assert_eq!(source.reads, 6);
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
        for (automatic, positions) in [
            (true, vec![before, before, after]),
            (true, vec![before, before, king_only, after]),
            (
                true,
                vec![before, before, king_only, king_only, king_only, after],
            ),
            (
                false,
                [vec![before; 2], vec![king_only; 10], vec![after]].concat(),
            ),
            (
                false,
                [vec![before; 4], vec![king_only; 8], vec![after]].concat(),
            ),
        ] {
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
#[test]
fn stopping_or_losing_geometry_during_castling_never_dispatches_the_rook() {
    let before = "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1";
    let king_only = "r3k2r/8/8/8/8/8/8/R5KR w - - 0 1";
    let after = "r3k2r/8/8/8/8/8/8/R4RK1 b - - 1 1";
    for geometry_changed in [false, true] {
        let mut source = Source::new(&[before, before, king_only, king_only, after]);
        let mut input = Input::default();
        if geometry_changed {
            source.positions[3].as_mut().unwrap().board.geometry.x += 20.;
        } else {
            input.stop_after_wait = Some(2);
        }
        let error = controller::play(
            &mut source,
            &mut input,
            &mut Engine::new("e1g1", after),
            &Settings {
                kingside: true,
                ..Settings::default()
            },
            Color::White,
            &AtomicBool::new(false),
            |_| {},
        )
        .err()
        .unwrap();
        assert!(if geometry_changed {
            matches!(error, PlayError::GeometryChanged)
        } else {
            matches!(error, PlayError::Stopped)
        });
        assert_eq!(input.events.len(), 1);
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
