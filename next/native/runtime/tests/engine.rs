use chesspilot_runtime::engine::{EngineService, Score, Timeouts};
use std::{
    io::{self, BufRead, Write},
    process::Command,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    time::{Duration, Instant},
};

const START: &str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const AFTER: &str = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1";
fn timeouts() -> Timeouts {
    Timeouts {
        handshake: Duration::from_secs(2),
        search: Duration::from_millis(150),
        stop: Duration::from_millis(150),
    }
}
fn service(mode: &str) -> EngineService {
    let mut command = Command::new(std::env::current_exe().unwrap());
    command
        .args(["--exact", "fake_engine", "--nocapture"])
        .env("CHESSPILOT_TEST_ENGINE", mode);
    EngineService::new(
        command,
        vec!["setoption name Hash value 16".into()],
        timeouts(),
    )
    .unwrap()
}

// The same test executable is a portable subprocess fixture; no Python/shell dependency.
#[test]
fn fake_engine() {
    let Ok(mode) = std::env::var("CHESSPILOT_TEST_ENGINE") else {
        return;
    };
    for line in io::stdin().lock().lines() {
        let line = line.unwrap();
        if mode == "silent" {
            continue;
        }
        match line.as_str() {
            "uci" => {
                println!("id name ChessPilot Test Engine");
                if mode == "stderr" {
                    for n in 0..4096 {
                        eprintln!("diagnostic {n}: {}", "x".repeat(128));
                    }
                }
                println!("uciok");
            }
            "isready" => println!("readyok"),
            "stop" if mode == "stop" => println!("bestmove e2e4"),
            "d" => {
                if mode != "no_fen" {
                    println!("Fen: {AFTER}");
                }
                println!("Checkers:");
            }
            "quit" => break,
            "go perft 1" => match mode.as_str() {
                "no_perft" => {}
                "bad_perft" => println!("e2e4: 1\nNodes searched: 2"),
                "duplicate_perft" => println!("e2e4: 1\ne2e4: 1\nNodes searched: 2"),
                "invalid_perft" => println!("not-a-move: 1\nNodes searched: 1"),
                _ => println!("e2e4: 1\nNodes searched: 1"),
            },
            _ if line.starts_with("go depth") => match mode.as_str() {
                "stop" | "ignore_stop" => {}
                "eof" => std::process::exit(7),
                "critical" => println!("info string CRITICAL ERROR: Incorrect number of kings"),
                "invalid_move" => println!("bestmove nope"),
                _ => {
                    println!("info depth 1 score mate -1");
                    println!("info depth 2 score cp 12");
                    println!("bestmove e2e4 ponder e7e5");
                }
            },
            _ => {}
        }
        io::stdout().flush().unwrap();
    }
}
#[test]
fn file_logging_does_not_block_a_flooded_stderr_pipe() {
    let directory = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join(format!("../target/engine-log-test-{}", std::process::id()));
    chesspilot_runtime::diagnostics::configure(Some(&directory)).unwrap();
    let mut engine = service("stderr");
    engine.initialize().unwrap();
    assert!(engine.process_id().is_some());
    assert!(engine.diagnostics().len() <= 64);
    chesspilot_runtime::diagnostics::flush();
}

#[test]
fn legal_reply_reconciliation_retains_metadata_and_rejects_invalid_changes() {
    let mut engine = service("normal");
    let flag = AtomicBool::new(false);
    assert_eq!(engine.legal_moves(START, &flag).unwrap(), ["e2e4"]);
    let pid = engine.process_id();
    assert_eq!(
        engine
            .reconcile_reply(START, AFTER, &flag)
            .unwrap()
            .as_deref(),
        Some(AFTER)
    );
    assert_eq!(engine.process_id(), pid);
    assert!(engine
        .reconcile_reply(START, START, &flag)
        .unwrap()
        .is_none());
    assert!(engine
        .reconcile_reply(
            START,
            "rnbqkbnr/pppppppp/8/4P3/8/8/PPPP1PPP/RNBQKBNR b - - 0 1",
            &flag
        )
        .unwrap()
        .is_none());
}
#[test]
fn malformed_silent_and_cancelled_legal_move_output_cleans_up_the_engine() {
    for mode in ["bad_perft", "duplicate_perft", "invalid_perft", "no_perft"] {
        let mut engine = EngineService::new(
            engine_command(mode),
            vec![],
            Timeouts {
                handshake: Duration::from_millis(150),
                ..timeouts()
            },
        )
        .unwrap();
        assert!(
            engine.legal_moves(START, &AtomicBool::new(false)).is_err(),
            "{mode}"
        );
        assert!(engine.process_id().is_none());
    }
    let mut engine = service("no_perft");
    engine.initialize().unwrap();
    let flag = Arc::new(AtomicBool::new(false));
    let cancelled = flag.clone();
    let worker = std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(40));
        cancelled.store(true, Ordering::Release);
    });
    assert_eq!(
        engine.legal_moves(START, &flag).unwrap_err().kind(),
        io::ErrorKind::Interrupted
    );
    worker.join().unwrap();
    assert!(engine.process_id().is_none());
}

#[test]
#[ignore = "Requires CHESSPILOT_STOCKFISH for real legal move and history reconciliation"]
fn real_stockfish_reconciles_special_moves_and_preserves_history() {
    let mut engine = EngineService::new(
        Command::new(std::env::var_os("CHESSPILOT_STOCKFISH").unwrap()),
        vec!["setoption name Hash value 16".into()],
        Timeouts::default(),
    )
    .unwrap();
    let flag = AtomicBool::new(false);
    let moves = engine.legal_moves(START, &flag).unwrap();
    assert_eq!(moves.len(), 20);
    assert!(moves.contains(&"e2e4".into()));
    for (before, after) in [
        (
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 10",
            "4k3/8/3P4/8/8/8/8/4K3 b - - 0 10",
        ),
        (
            "4k3/8/8/8/8/8/8/4K2R w K - 4 20",
            "4k3/8/8/8/8/8/8/5RK1 b - - 5 20",
        ),
        (
            "r3k3/8/8/8/8/8/8/4K3 b q - 4 20",
            "2kr4/8/8/8/8/8/8/4K3 w - - 5 21",
        ),
        (
            "4k3/P7/8/8/8/8/8/4K3 w - - 0 10",
            "N3k3/8/8/8/8/8/8/4K3 b - - 0 10",
        ),
        (
            "4k2r/6B1/8/8/8/8/8/4K3 w k - 3 4",
            "4k2B/8/8/8/8/8/8/4K3 b - - 0 4",
        ),
    ] {
        assert_eq!(
            engine
                .reconcile_reply(before, after, &flag)
                .unwrap()
                .as_deref(),
            Some(after)
        );
    }
    assert!(engine
        .legal_moves("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", &flag)
        .unwrap()
        .is_empty());
}

#[test]
fn persistent_engine_returns_move_fen_progress_and_latest_score() {
    let mut engine = service("normal");
    engine.initialize().unwrap();
    let pid = engine.process_id().unwrap();
    let mut progress = Vec::new();
    for _ in 0..2 {
        let analysis = engine
            .get_best_move(5, START, &AtomicBool::new(false), |d, s| {
                progress.push((d, s))
            })
            .unwrap();
        assert_eq!(analysis.best_move.as_deref(), Some("e2e4"));
        assert_eq!(analysis.updated_fen.as_deref(), Some(AFTER));
        assert_eq!(analysis.score, Some(Score::Centipawns(12)));
        assert!(!analysis.stopped);
        assert_eq!(engine.process_id(), Some(pid));
    }
    assert!(progress.contains(&(1, Some(Score::Mate(-1)))));
    assert!(progress.contains(&(2, Some(Score::Centipawns(12)))));
    engine.cleanup();
    assert!(engine.process_id().is_none());
    engine.initialize().unwrap();
    assert!(engine.process_id().is_some());
}

#[test]
fn silent_startup_has_a_real_deadline() {
    let mut engine = EngineService::new(
        engine_command("silent"),
        vec![],
        Timeouts {
            handshake: Duration::from_millis(150),
            ..timeouts()
        },
    )
    .unwrap();
    let start = Instant::now();
    assert_eq!(
        engine.initialize().unwrap_err().kind(),
        io::ErrorKind::TimedOut
    );
    assert!(start.elapsed() < Duration::from_secs(3));
    assert!(engine.process_id().is_none());
}
fn engine_command(mode: &str) -> Command {
    let mut command = Command::new(std::env::current_exe().unwrap());
    command
        .args(["--exact", "fake_engine", "--nocapture"])
        .env("CHESSPILOT_TEST_ENGINE", mode);
    command
}

#[test]
fn search_deadline_requests_stop_and_returns_best_available_move() {
    let mut engine = service("stop");
    let start = Instant::now();
    let analysis = engine
        .get_best_move(30, START, &AtomicBool::new(false), |_, _| {})
        .unwrap();
    assert!(analysis.stopped);
    assert_eq!(analysis.best_move.as_deref(), Some("e2e4"));
    assert!(start.elapsed() < Duration::from_secs(3));
}

#[test]
fn cancellation_of_silent_search_stops_and_cleans_up() {
    let mut engine = service("stop");
    engine.initialize().unwrap();
    let cancelled = Arc::new(AtomicBool::new(false));
    let flag = cancelled.clone();
    let worker = std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(40));
        flag.store(true, Ordering::Release);
    });
    assert_eq!(
        engine
            .get_best_move(30, START, &cancelled, |_, _| {})
            .unwrap_err()
            .kind(),
        io::ErrorKind::Interrupted
    );
    worker.join().unwrap();
    assert!(engine.process_id().is_none());
}

#[test]
fn failure_modes_do_not_leave_a_running_engine() {
    for mode in ["ignore_stop", "critical", "invalid_move", "no_fen", "eof"] {
        let mut engine = service(mode);
        let start = Instant::now();
        let error = engine
            .get_best_move(5, START, &AtomicBool::new(false), |_, _| {})
            .unwrap_err();
        assert!(start.elapsed() < Duration::from_secs(4), "{mode}");
        assert!(engine.process_id().is_none(), "{mode}");
        if mode == "critical" {
            assert!(error.to_string().contains("Incorrect number of kings"));
        }
    }
}

#[test]
fn stderr_is_drained_and_diagnostics_are_bounded() {
    let mut engine = service("stderr");
    engine.initialize().unwrap();
    assert_eq!(engine.diagnostics().len(), 64);
    assert!(engine
        .get_best_move(5, START, &AtomicBool::new(false), |_, _| {})
        .is_ok());
    engine.cleanup();
    assert_eq!(engine.diagnostics().len(), 64);
}

#[test]
fn invalid_positions_and_protocol_injection_never_start_a_process() {
    let mut engine = service("normal");
    for fen in [
        "8/8/8/8/8/8/8/8 w - - 0 1",
        "garbage",
        &format!("{START}\nquit"),
    ] {
        assert!(engine
            .get_best_move(5, fen, &AtomicBool::new(false), |_, _| {})
            .is_err());
        assert!(engine.process_id().is_none());
    }
    assert!(EngineService::new(
        engine_command("normal"),
        vec!["setoption name Hash value 16\nquit".into()],
        timeouts()
    )
    .is_err());
}

#[test]
#[ignore = "Requires CHESSPILOT_STOCKFISH pointing to a native Stockfish executable"]
fn real_stockfish_opening_checkmate_and_persistent_reuse() {
    let path = std::env::var_os("CHESSPILOT_STOCKFISH")
        .expect("Set CHESSPILOT_STOCKFISH for integration test");
    let mut engine = EngineService::new(
        Command::new(path),
        vec![
            "setoption name Hash value 16".into(),
            "setoption name Threads value 1".into(),
        ],
        Timeouts::default(),
    )
    .unwrap();
    let first = engine
        .get_best_move(5, START, &AtomicBool::new(false), |_, _| {})
        .unwrap();
    assert!(first.best_move.is_some());
    assert!(first.updated_fen.unwrap().contains(" b "));
    let pid = engine.process_id();
    let mate = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3";
    let result = engine
        .get_best_move(5, mate, &AtomicBool::new(false), |_, _| {})
        .unwrap();
    assert!(result.best_move.is_none());
    assert!(result.updated_fen.is_none());
    assert_eq!(pid, engine.process_id());
}
