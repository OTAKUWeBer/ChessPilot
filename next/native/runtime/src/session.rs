//! Session ownership behind the Flutter/native boundary. Heavy work stays off Dart's UI isolate.
#[cfg(any(windows, target_os = "linux", target_os = "android"))]
use crate::controller::{MoveOutcome, Progress};
use crate::{
    controller::KnownPosition,
    desktop::CaptureBounds,
    engine::{Analysis, EngineService, Score, Timeouts},
    resources,
    vision::{BoardReader, OnnxPredictor},
};
use chesspilot_core::{
    config::{MoveMode, Settings},
    state::GameState,
    Color,
};
use serde_json::{json, Value};
use std::{
    path::PathBuf,
    process::Command,
    sync::{
        atomic::{AtomicBool, AtomicU64, Ordering},
        Arc, Mutex,
    },
    thread::{self, JoinHandle},
};
#[cfg(any(windows, target_os = "linux", target_os = "android"))]
static DESKTOP_INPUT_OWNER: Mutex<()> = Mutex::new(());

struct State {
    settings: Settings,
    game: GameState,
    busy: bool,
    operation: Option<&'static str>,
    status: String,
    engine_ready: bool,
    capture_ready: bool,
    analysis: Option<Analysis>,
    error: Option<String>,
    auto_mode: bool,
    history_valid: bool,
    input_in_flight: bool,
    confirmed_source: Option<CaptureBounds>,
    download: Option<Value>,
}
impl Default for State {
    fn default() -> Self {
        Self {
            settings: Settings::default(),
            game: GameState::default(),
            busy: false,
            operation: None,
            status: "Choose your color".into(),
            engine_ready: false,
            capture_ready: false,
            analysis: None,
            error: None,
            auto_mode: false,
            history_valid: false,
            input_in_flight: false,
            confirmed_source: None,
            download: None,
        }
    }
}
pub struct Session {
    state: Mutex<State>,
    engine: Mutex<Option<EngineService>>,
    vision: Mutex<Option<BoardReader<OnnxPredictor>>>,
    cancelled: AtomicBool,
    closed: AtomicBool,
    generation: AtomicU64,
    worker: Mutex<Option<JoinHandle<()>>>,
}
impl Default for Session {
    fn default() -> Self {
        Self {
            state: Mutex::new(State::default()),
            engine: Mutex::new(None),
            vision: Mutex::new(None),
            cancelled: AtomicBool::new(false),
            closed: AtomicBool::new(false),
            generation: AtomicU64::new(0),
            worker: Mutex::new(None),
        }
    }
}
fn lock<T>(value: &Mutex<T>) -> std::sync::MutexGuard<'_, T> {
    value.lock().unwrap_or_else(|e| e.into_inner())
}
fn score(value: Option<Score>) -> Value {
    match value {
        Some(Score::Centipawns(n)) => json!({"kind":"cp","value":n}),
        Some(Score::Mate(n)) => json!({"kind":"mate","value":n}),
        None => Value::Null,
    }
}
fn known_position(state: &State) -> Option<KnownPosition> {
    if !state.history_valid || state.game.last_fen.is_empty() {
        return None;
    }
    Some(KnownPosition {
        fen: state.game.last_fen.clone(),
        geometry: state.game.geometry?,
        source: state.confirmed_source?,
    })
}
#[cfg(any(windows, target_os = "linux", target_os = "android"))]
fn confirm(state: &mut State, position: KnownPosition) -> Result<(), String> {
    state.game.update_last_fen_for_color(&position.fen)?;
    state.game.last_fen = position.fen;
    state.game.geometry = Some(position.geometry);
    state.confirmed_source = Some(position.source);
    state.history_valid = true;
    state.input_in_flight = false;
    Ok(())
}
#[cfg(any(windows, target_os = "linux", target_os = "android"))]
fn played(state: &mut State, outcome: MoveOutcome) -> Result<(), String> {
    if let Some(position) = outcome.position() {
        confirm(state, position)?;
        let value = outcome.analysis.best_move.as_deref().unwrap_or("");
        state.status = format!("Best Move: {value}\nMove Played: {value}");
    } else {
        state.history_valid = false;
        state.status = "No legal moves".into();
    }
    state.analysis = Some(outcome.analysis);
    Ok(())
}
impl Session {
    pub fn snapshot(&self) -> Value {
        let s = lock(&self.state);
        json!({"depth":s.settings.depth,"delay":s.settings.screenshot_delay,
            "mode":if s.settings.move_mode==MoveMode::Drag {"drag"} else {"click"},
            "kingside":s.settings.kingside,"queenside":s.settings.queenside,
            "color":s.game.color_indicator.map(Color::fen),"busy":s.busy,"operation":s.operation,"status":s.status,
            "engine_ready":s.engine_ready,"capture_ready":s.capture_ready,"automation_ready":s.capture_ready && crate::desktop::SUPPORTED,
            "confirmed_fen":if s.game.last_fen.is_empty(){None}else{Some(&s.game.last_fen)},
            "auto_mode":s.auto_mode,"auto_available":s.engine_ready && s.capture_ready && s.game.color_indicator.is_some() && known_position(&s).is_some(),
            "generation":self.generation.load(Ordering::Acquire),"error":s.error,
            "download":s.download,
            "analysis":s.analysis.as_ref().map(|a|json!({"best_move":a.best_move,"updated_fen":a.updated_fen,"depth":a.depth,"score":score(a.score),"stopped":a.stopped}))})
    }
    pub fn configure(&self, args: &Value) -> Result<(), String> {
        let mut s = lock(&self.state);
        if self.closed.load(Ordering::Acquire) {
            return Err("Session is closed".into());
        }
        let mut settings = s.settings.clone();
        let mut color = s.game.color_indicator;
        if let Some(value) = args.get("depth") {
            settings.depth = value
                .as_u64()
                .filter(|n| (10..=30).contains(n))
                .ok_or("Depth must be between 10 and 30")? as u32;
        }
        if let Some(value) = args.get("delay") {
            settings.screenshot_delay = value
                .as_f64()
                .filter(|n| n.is_finite() && (0.0..=1.0).contains(n))
                .ok_or("Delay must be between 0 and 1")?;
        }
        if let Some(value) = args.get("mode") {
            settings.move_mode = match value.as_str() {
                Some("drag") => MoveMode::Drag,
                Some("click") => MoveMode::Click,
                _ => return Err("Expected drag or click mode".into()),
            };
        }
        if let Some(value) = args.get("kingside") {
            settings.kingside = value.as_bool().ok_or("Expected kingside boolean")?;
        }
        if let Some(value) = args.get("queenside") {
            settings.queenside = value.as_bool().ok_or("Expected queenside boolean")?;
        }
        if let Some(value) = args.get("color") {
            color = if value.is_null() {
                None
            } else {
                Some(Color::parse(
                    value.as_str().ok_or("Expected color w or b")?,
                )?)
            };
        }
        if color != s.game.color_indicator || settings != s.settings {
            s.auto_mode = false;
            if s.input_in_flight {
                s.history_valid = false;
            }
            // Startup services are independent of the selected side/settings.
            if !s
                .operation
                .is_some_and(|name| name.starts_with("initialize"))
            {
                self.generation.fetch_add(1, Ordering::AcqRel);
                self.cancel();
            }
            s.analysis = None;
        }
        if color != s.game.color_indicator {
            s.game.last_fen.clear();
            s.game.last_fen_by_color = [None, None];
            s.game.geometry = None;
            s.history_valid = false;
            s.confirmed_source = None;
        }
        s.settings = settings;
        s.error = None;
        s.game.color_indicator = color;
        s.game.move_mode = s.settings.move_mode;
        if !s.busy {
            s.status = match color {
                Some(Color::White) => "Playing as White",
                Some(Color::Black) => "Playing as Black",
                None => "Choose your color",
            }
            .into();
        }
        Ok(())
    }
    fn cancel(&self) {
        self.cancelled.store(true, Ordering::Release);
        #[cfg(target_os = "android")]
        crate::android::bridge().cancel_pending();
    }
    pub fn stop(&self) {
        let mut s = lock(&self.state);
        self.cancel();
        self.generation.fetch_add(1, Ordering::AcqRel);
        s.auto_mode = false;
        if s.input_in_flight {
            s.history_valid = false;
        }
        s.status = if s.busy { "Stopping..." } else { "Stopped" }.into();
    }
    pub fn capture_lost(&self, reason: &str) {
        log::warn!(target:"capture","Capture lost: {reason}");
        self.stop();
        let mut s = lock(&self.state);
        s.capture_ready = false;
        s.history_valid = false;
        s.status = "Capture stopped; reconnect to continue".into();
        s.error = Some(reason.chars().take(512).collect());
    }
    fn launch(
        self: &Arc<Self>,
        operation: &'static str,
        task: impl FnOnce(&Arc<Self>, u64) -> Result<(), String> + Send + 'static,
    ) -> Result<(), String> {
        let mut slot = lock(&self.worker);
        let id;
        {
            let mut state = lock(&self.state);
            if self.closed.load(Ordering::Acquire) {
                return Err("Session is closed".into());
            }
            if state.busy {
                return Err("A native operation is already running".into());
            }
            state.busy = true;
            state.auto_mode = operation == "auto";
            state.input_in_flight = false;
            state.operation = Some(operation);
            state.error = None;
            state.download = None;
            self.cancelled.store(false, Ordering::Release);
            id = self.generation.fetch_add(1, Ordering::AcqRel) + 1;
        }
        if let Some(old) = slot.take() {
            let _ = old.join();
        }
        let session = self.clone();
        log::info!(target:"session","Starting {operation} generation {id}");
        match thread::Builder::new()
            .name("chesspilot-session".into())
            .spawn(move || {
                let started=std::time::Instant::now();
                let result =
                    std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| task(&session, id)))
                        .unwrap_or_else(|_| Err("Native operation panicked".into()));
                let mut state = lock(&session.state);
                if session.generation.load(Ordering::Acquire) == id {
                    if let Err(error) = result {
                        log::error!(target:"session","{operation} generation {id} failed: {error}");
                        state.status = error.clone();
                        state.error = Some(error);
                    }
                } else {
                    state.status = "Stopped".into();
                }
                state.busy = false;
                log::info!(target:"session","{operation} generation {id} ended after {:?}: {}",started.elapsed(),state.status);
                state.auto_mode = false;
                if state.input_in_flight {
                    state.history_valid = false;
                    state.input_in_flight = false;
                }
                state.operation = None;
            }) {
            Ok(worker) => {
                *slot = Some(worker);
                Ok(())
            }
            Err(error) => {
                let mut state = lock(&self.state);
                state.busy = false;
                state.auto_mode = false;
                state.operation = None;
                Err(error.to_string())
            }
        }
    }
    pub fn initialize_engine(self: &Arc<Self>, args: &Value) -> Result<(), String> {
        self.initialize(args, false)
    }
    pub fn initialize(self: &Arc<Self>, args: &Value, with_capture: bool) -> Result<(), String> {
        let path = args
            .get("engine_path")
            .map(|v| v.as_str().map(PathBuf::from).ok_or("Expected engine path"))
            .transpose()?;
        let config = args
            .get("config_path")
            .map(|v| v.as_str().map(PathBuf::from).ok_or("Expected config path"))
            .transpose()?;
        let fallback = args
            .get("fallback_engine_path")
            .map(|v| {
                v.as_str()
                    .map(PathBuf::from)
                    .ok_or("Expected fallback engine path")
            })
            .transpose()?;
        let working_directory = args
            .get("engine_working_directory")
            .map(|v| {
                v.as_str()
                    .map(PathBuf::from)
                    .ok_or("Expected engine working directory")
            })
            .transpose()?;
        if working_directory.as_ref().is_some_and(|p| !p.is_absolute()) {
            return Err("Engine working directory must be absolute".into());
        }
        let args = args.clone();
        self.launch(
            if with_capture {
                "initialize"
            } else {
                "initialize_engine"
            },
            move |session, id| {
                let config = config
                    .map(Ok)
                    .unwrap_or_else(resources::default_config_path)
                    .map_err(|e| e.to_string())?;
                let options = resources::load_options(&config).map_err(|e| e.to_string())?;
                let path = match path {
                    Some(path) => path,
                    None => crate::installer::ensure_stockfish(&session.cancelled, |progress| {
                        let mut state = lock(&session.state);
                        if session.generation.load(Ordering::Acquire) == id {
                            state.status = progress["stage"]
                                .as_str()
                                .unwrap_or("Preparing engine")
                                .into();
                            state.download = Some(progress);
                        }
                    })?,
                };
                if session.cancelled.load(Ordering::Acquire) {
                    return Err("Engine setup cancelled".into());
                }
                {
                    let mut state = lock(&session.state);
                    if session.generation.load(Ordering::Acquire) != id {
                        return Ok(());
                    }
                    state.status = "Initializing Stockfish...".into();
                    state.engine_ready = false;
                }
                let old = lock(&session.engine).take();
                drop(old);
                let start = |path: &std::path::Path| -> Result<EngineService, String> {
                    let mut command=Command::new(path);
                    if let Some(directory)=&working_directory { command.current_dir(directory); }
                    let mut engine=EngineService::new(command,options.clone(),Timeouts::default()).map_err(|e|e.to_string())?;
                    engine.initialize().map_err(|e|e.to_string())?;
                    Ok(engine)
                };
                let engine=match start(&path) {
                    Ok(engine)=>engine,
                    Err(error)=> {
                        if session.cancelled.load(Ordering::Acquire) { return Err("Engine setup cancelled".into()); }
                        match fallback.filter(|p|p!=&path) {
                            Some(fallback)=> {
                                log::warn!(target:"setup","Optimized engine startup failed: {error}; trying {}",fallback.display());
                                start(&fallback).map_err(|e|format!("Engine startup failed: {error}; baseline fallback: {e}"))?
                            },
                            None=>return Err(error),
                        }
                    }
                };
                {
                    let mut state = lock(&session.state);
                    if session.generation.load(Ordering::Acquire) != id {
                        return Ok(());
                    }
                    *lock(&session.engine) = Some(engine);
                    state.engine_ready = true;
                    state.status = "Stockfish ready".into();
                    state.download = None;
                }
                if with_capture {
                    session.load_capture(id, &args)?;
                }
                Ok(())
            },
        )
    }
    fn load_capture(&self, id: u64, args: &Value) -> Result<(), String> {
        {
            let mut state = lock(&self.state);
            if self.generation.load(Ordering::Acquire) != id {
                return Ok(());
            }
            state.capture_ready = false;
            state.status = "Initializing board detection...".into();
        }
        *lock(&self.vision) = None;
        let path = |key| -> Result<Option<&str>, String> {
            args.get(key)
                .map(|v| v.as_str().ok_or_else(|| format!("Expected {key} string")))
                .transpose()
        };
        let (model, runtime) = resources::vision_paths(path("model_path")?, path("runtime_path")?)
            .map_err(|e| e.to_string())?;
        let reader = BoardReader::new(OnnxPredictor::load(&model, &runtime)?);
        #[cfg(any(windows, target_os = "linux", target_os = "android"))]
        {
            use crate::desktop::Capture;
            let (mut capture, _input) = crate::desktop::open()?;
            capture.capture()?;
        }
        if !crate::desktop::SUPPORTED {
            return Err("Native capture/input for this platform is not connected yet".into());
        }
        let mut state = lock(&self.state);
        if self.generation.load(Ordering::Acquire) != id {
            return Ok(());
        }
        *lock(&self.vision) = Some(reader);
        state.capture_ready = true;
        state.status = "Ready to play".into();
        Ok(())
    }
    pub fn initialize_capture(self: &Arc<Self>, args: &Value) -> Result<(), String> {
        let args = args.clone();
        self.launch("initialize_capture", move |session, id| {
            session.load_capture(id, &args)
        })
    }
    pub fn play(self: &Arc<Self>) -> Result<(), String> {
        self.run_moves(false)
    }
    pub fn start_auto(self: &Arc<Self>) -> Result<(), String> {
        self.run_moves(true)
    }
    #[cfg(any(windows, target_os = "linux", target_os = "android"))]
    fn progress(&self, id: u64, target_depth: u32, progress: Progress) -> Result<(), String> {
        let mut state = lock(&self.state);
        if self.generation.load(Ordering::Acquire) != id {
            return Ok(());
        }
        match progress {
            Progress::Status(status) => state.status = status.into(),
            Progress::Dispatching => {
                state.input_in_flight = true;
                state.status = "Playing move...".into();
            }
            Progress::Analysis(depth, score) => {
                state.status = format!("Processing... Depth {depth}/{target_depth}");
                state.analysis = Some(Analysis {
                    best_move: None,
                    updated_fen: None,
                    depth,
                    score,
                    stopped: false,
                });
            }
            Progress::Candidate(analysis) => state.analysis = Some(analysis),
            Progress::Observed(position) => confirm(&mut state, position)?,
            Progress::Played(outcome) => played(&mut state, outcome)?,
            Progress::Terminal => {
                state.history_valid = false;
                state.status = "Game over: no legal moves".into();
            }
        }
        Ok(())
    }
    fn run_moves(self: &Arc<Self>, automatic: bool) -> Result<(), String> {
        #[cfg(not(any(windows, target_os = "linux", target_os = "android")))]
        {
            let _ = automatic;
            Err("Native capture/input for this platform is not connected yet".into())
        }
        #[cfg(any(windows, target_os = "linux", target_os = "android"))]
        {
            {
                let state = lock(&self.state);
                if !state.engine_ready || !state.capture_ready {
                    return Err("Initialize the engine and board capture first".into());
                }
                if state.game.color_indicator.is_none() {
                    return Err("Choose your color first".into());
                }
                if automatic && known_position(&state).is_none() {
                    return Err("Play one move before enabling Auto to establish the turn".into());
                }
            }
            self.launch(
                if automatic { "auto" } else { "play" },
                move |session, id| {
                    let _owner =
                        match DESKTOP_INPUT_OWNER.try_lock() {
                            Ok(owner) => owner,
                            Err(std::sync::TryLockError::Poisoned(error)) => error.into_inner(),
                            Err(std::sync::TryLockError::WouldBlock) => return Err(
                                "Another session is controlling the desktop; wait for it to finish"
                                    .into(),
                            ),
                        };
                    use crate::controller::{self, Perception, PlayError};
                    let (settings, color, position) = {
                        let state = lock(&session.state);
                        if session.generation.load(Ordering::Acquire) != id {
                            return Ok(());
                        }
                        (
                            state.settings.clone(),
                            state
                                .game
                                .color_indicator
                                .ok_or("Choose your color first")?,
                            known_position(&state),
                        )
                    };
                    let mut vision = lock(&session.vision);
                    let (capture, mut input) = crate::desktop::open()?;
                    let mut source = Perception {
                        capture,
                        reader: vision.as_mut().ok_or("Board detector is unavailable")?,
                    };
                    let mut engine = lock(&session.engine);
                    let mut progress_error = None;
                    let mut progress = |event| {
                        if let Err(error) = session.progress(id, settings.depth, event) {
                            progress_error = Some(error);
                            session.cancel();
                        }
                    };
                    let engine = engine.as_mut().ok_or("Engine is unavailable")?;
                    let result = if automatic {
                        controller::auto_play(
                            &mut source,
                            &mut input,
                            engine,
                            controller::AutoRequest {
                                settings: &settings,
                                color,
                                position: position.ok_or("Play one move before enabling Auto")?,
                            },
                            &session.cancelled,
                            &mut progress,
                        )
                        .map(|_| None)
                    } else {
                        controller::play_position(
                            &mut source,
                            &mut input,
                            engine,
                            controller::PlayRequest {
                                settings: &settings,
                                color,
                                known_position: position.as_ref().filter(|p| {
                                    p.fen.split_whitespace().nth(1) == Some(color.fen())
                                }),
                            },
                            &session.cancelled,
                            &mut progress,
                        )
                        .map(Some)
                    };
                    let mut state = lock(&session.state);
                    if session.generation.load(Ordering::Acquire) != id {
                        return Ok(());
                    }
                    if let Some(error) = progress_error {
                        return Err(error);
                    }
                    match result {
                        Ok(Some(outcome)) => played(&mut state, outcome),
                        Ok(None) => Ok(()),
                        Err(error) => {
                            if matches!(error, PlayError::Engine(_)) {
                                state.engine_ready = false;
                            }
                            if state.input_in_flight || matches!(error, PlayError::GeometryChanged)
                            {
                                state.history_valid = false;
                            }
                            Err(error.to_string())
                        }
                    }
                },
            )
        }
    }
    pub fn analyze(self: &Arc<Self>, fen: String) -> Result<(), String> {
        if !lock(&self.state).engine_ready {
            return Err("Initialize Stockfish first".into());
        }
        self.launch("analyze", move |session, id| {
            let depth = lock(&session.state).settings.depth;
            let result = lock(&session.engine)
                .as_mut()
                .ok_or("Engine is unavailable")?
                .get_best_move(depth, &fen, &session.cancelled, |depth, score_value| {
                    let mut state = lock(&session.state);
                    if session.generation.load(Ordering::Acquire) == id {
                        state.status = format!("Processing... Depth {depth}");
                        state.analysis = Some(Analysis {
                            best_move: None,
                            updated_fen: None,
                            score: score_value,
                            depth,
                            stopped: false,
                        });
                    }
                });
            match result {
                Ok(analysis) => {
                    let mut state = lock(&session.state);
                    if session.generation.load(Ordering::Acquire) != id {
                        return Ok(());
                    }
                    state.status = analysis
                        .best_move
                        .as_ref()
                        .map(|mv| format!("Best move found: {mv}"))
                        .unwrap_or_else(|| "No legal moves".into());
                    state.analysis = Some(analysis);
                    Ok(())
                }
                Err(error) => {
                    lock(&session.state).engine_ready = false;
                    Err(error.to_string())
                }
            }
        })
    }
    pub fn close(&self) {
        if self.closed.swap(true, Ordering::AcqRel) {
            return;
        }
        self.stop();
        if let Some(worker) = lock(&self.worker).take() {
            let _ = worker.join();
        }
        *lock(&self.engine) = None;
        *lock(&self.vision) = None;
        let mut state = lock(&self.state);
        state.engine_ready = false;
        state.capture_ready = false;
    }
}

#[cfg(all(test, any(windows, target_os = "linux", target_os = "android")))]
mod tests {
    use super::*;
    use std::time::{Duration, Instant};
    #[test]
    fn capture_loss_stops_work_and_invalidates_auto_history() {
        let session = Session::default();
        {
            let mut s = lock(&session.state);
            s.engine_ready = true;
            s.capture_ready = true;
            s.auto_mode = true;
            s.history_valid = true;
            s.busy = true;
            s.input_in_flight = true;
        }
        session.capture_lost("Display rotated");
        let snapshot = session.snapshot();
        assert_eq!(snapshot["engine_ready"], true);
        assert_eq!(snapshot["capture_ready"], false);
        assert_eq!(snapshot["auto_mode"], false);
        assert_eq!(snapshot["auto_available"], false);
        assert_eq!(snapshot["error"], "Display rotated");
        assert!(!lock(&session.state).history_valid);
        assert!(session.cancelled.load(Ordering::Acquire));
    }
    #[test]
    fn stop_preserves_waiting_history_but_invalidates_uncertain_input_and_ignores_late_events() {
        for dispatched in [false, true] {
            let session = Session::default();
            let position = KnownPosition {
                fen: "4k3/8/8/8/4P3/8/8/4K3 b - e3 0 1".into(),
                geometry: chesspilot_core::board::BoardGeometry::new(0., 0., 80.).unwrap(),
                source: CaptureBounds {
                    x: 0,
                    y: 0,
                    width: 800,
                    height: 800,
                },
            };
            {
                let mut state = lock(&session.state);
                state.engine_ready = true;
                state.capture_ready = true;
                state.game.color_indicator = Some(Color::White);
                confirm(&mut state, position.clone()).unwrap();
                state.auto_mode = true;
            }
            assert_eq!(session.snapshot()["auto_available"], true);
            if dispatched {
                session.progress(0, 15, Progress::Dispatching).unwrap();
            }
            session.stop();
            assert_eq!(session.snapshot()["auto_mode"], false);
            assert_eq!(session.snapshot()["auto_available"], !dispatched);
            session
                .progress(
                    0,
                    15,
                    Progress::Observed(KnownPosition {
                        fen: "4k3/8/8/8/4P3/8/8/4K3 w - - 0 2".into(),
                        ..position.clone()
                    }),
                )
                .unwrap();
            assert_eq!(session.snapshot()["confirmed_fen"], position.fen);
        }
    }
    #[test]
    fn another_session_cannot_start_desktop_work_while_a_move_owns_input() {
        let owner = lock(&DESKTOP_INPUT_OWNER);
        let session = Arc::new(Session::default());
        {
            let mut state = lock(&session.state);
            state.engine_ready = true;
            state.capture_ready = true;
            state.game.color_indicator = Some(Color::White);
        }
        session.play().unwrap();
        let deadline = Instant::now() + Duration::from_secs(2);
        while session.snapshot()["busy"] == true {
            assert!(Instant::now() < deadline);
            std::thread::sleep(Duration::from_millis(5));
        }
        assert!(session.snapshot()["error"]
            .as_str()
            .unwrap()
            .contains("Another session"));
        drop(owner);
        session.close();
    }
}
