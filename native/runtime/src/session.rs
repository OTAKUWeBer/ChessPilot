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
    config::{MoveMode, Settings, MAX_DEPTH, MIN_DEPTH},
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
    game_result: Option<&'static str>,
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
            game_result: None,
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
fn sync_castling(state: &mut State) {
    if let Some(color) = state.game.color_indicator {
        if !state.game.last_fen.is_empty() {
            let rights = state.game.last_fen.split_whitespace().nth(2).unwrap_or("-");
            let (king, queen) = if color == Color::White {
                ('K', 'Q')
            } else {
                ('k', 'q')
            };
            // Confirmed FEN retains lost rights even if the king or rook returns home.
            state.settings.kingside &= rights.contains(king);
            state.settings.queenside &= rights.contains(queen);
        }
    }
}
#[cfg(any(windows, target_os = "linux", target_os = "android"))]
fn confirm(state: &mut State, position: KnownPosition) -> Result<(), String> {
    state.game.update_last_fen_for_color(&position.fen)?;
    state.game.last_fen = position.fen;
    sync_castling(state);
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
        // A verified mate-in-one is checkmate; a negative mate score is still a future threat.
        if outcome.analysis.score == Some(Score::Mate(1)) {
            state.game_result = Some("checkmate");
            state.status = format!("Checkmate!\nMove played: {value}");
        }
    } else {
        state.history_valid = false;
        let score = outcome
            .analysis
            .score
            .or_else(|| state.analysis.as_ref().and_then(|analysis| analysis.score));
        finish_game(state, score);
    }
    state.analysis = Some(outcome.analysis);
    Ok(())
}
fn finish_game(state: &mut State, score: Option<Score>) {
    state.game_result = state.game_result.or(Some(match score {
        Some(Score::Mate(0 | 1)) => "checkmate",
        Some(Score::Centipawns(_)) => "stalemate",
        _ => "game_over",
    }));
    state.auto_mode = false;
    state.status = match state.game_result {
        Some("checkmate") => "Checkmate!",
        Some("stalemate") => "Draw by stalemate",
        _ => "Game over",
    }
    .into();
}
#[cfg(any(windows, target_os = "linux", target_os = "android"))]
fn move_failed(state: &mut State, error: &crate::controller::PlayError) {
    use crate::controller::PlayError;
    // EngineService restarts a failed process on the next request; this is not a setup failure.
    if state.input_in_flight
        || matches!(
            error,
            PlayError::GeometryChanged | PlayError::PositionChanged | PlayError::HistoryMismatch
        )
    {
        state.history_valid = false;
    }
}
impl Session {
    pub fn snapshot(&self) -> Value {
        let s = lock(&self.state);
        json!({"depth":s.settings.depth,"delay":s.settings.screenshot_delay,
            "mode":if s.settings.move_mode==MoveMode::Drag {"drag"} else {"click"},
            "kingside":s.settings.kingside,"queenside":s.settings.queenside,
            "color":s.game.color_indicator.map(Color::fen),"busy":s.busy,"operation":s.operation,"status":s.status,
            "game_result":s.game_result,
            "engine_ready":s.engine_ready,"capture_ready":s.capture_ready,"automation_ready":s.capture_ready && crate::desktop::SUPPORTED,
            "confirmed_fen":if s.game.last_fen.is_empty(){None}else{Some(&s.game.last_fen)},
            "auto_mode":s.auto_mode,"auto_available":s.game_result.is_none() && s.engine_ready && s.capture_ready && s.game.color_indicator.is_some(),
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
                .filter(|n| (u64::from(MIN_DEPTH)..=u64::from(MAX_DEPTH)).contains(n))
                .ok_or_else(|| format!("Depth must be between {MIN_DEPTH} and {MAX_DEPTH}"))?
                as u32;
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
            s.game_result = None;
            s.game.last_fen.clear();
            s.game.last_fen_by_color = [None, None];
            s.game.geometry = None;
            s.history_valid = false;
            s.confirmed_source = None;
        }
        s.settings = settings;
        s.error = None;
        s.game.color_indicator = color;
        sync_castling(&mut s);
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
                    engine.initialize(&session.cancelled).map_err(|e|e.to_string())?;
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
    pub fn play(self: &Arc<Self>, args: &Value) -> Result<(), String> {
        let target = args
            .get("return_target")
            .map(crate::desktop::return_target::ReturnTarget::parse)
            .transpose()?;
        if cfg!(target_os = "android") && target.is_some() {
            return Err("Android has no desktop pointer".into());
        }
        self.run_moves(false, target)
    }
    pub fn start_auto(self: &Arc<Self>) -> Result<(), String> {
        self.run_moves(true, None)
    }
    #[cfg(any(windows, target_os = "linux", target_os = "android"))]
    fn progress(&self, id: u64, target_depth: u32, progress: Progress) -> Result<(), String> {
        let mut state = lock(&self.state);
        if self.generation.load(Ordering::Acquire) != id {
            return Ok(());
        }
        match progress {
            Progress::Status(status) => {
                log::debug!(target:"session", "Generation {id}: {status}");
                state.status = status.into();
            }
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
                let score = state.analysis.as_ref().and_then(|analysis| analysis.score);
                finish_game(&mut state, score);
            }
        }
        Ok(())
    }
    fn run_moves(
        self: &Arc<Self>,
        automatic: bool,
        return_target: Option<crate::desktop::return_target::ReturnTarget>,
    ) -> Result<(), String> {
        #[cfg(not(any(windows, target_os = "linux", target_os = "android")))]
        {
            let _ = (automatic, return_target);
            Err("Native capture/input for this platform is not connected yet".into())
        }
        #[cfg(any(windows, target_os = "linux", target_os = "android"))]
        {
            {
                let state = lock(&self.state);
                if !state.engine_ready || !state.capture_ready {
                    return Err("Initialize the engine and board capture first".into());
                }
                if state.game_result.is_some() {
                    return Err("This game is over. Choose New game to play again".into());
                }
                if state.game.color_indicator.is_none() {
                    return Err("Choose your color first".into());
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
                    use crate::controller::{self, Automation, Perception};
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
                                position,
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
                                known_position: position.as_ref(),
                            },
                            &session.cancelled,
                            &mut progress,
                        )
                        .map(Some)
                    };
                    if let (Ok(Some(outcome)),Some(target))=(&result,return_target) {
                        if outcome.confirmed_fen.is_some() && !session.cancelled.load(Ordering::Acquire) {
                            if let Err(error)=input.return_pointer(target,&session.cancelled) {
                                log::warn!(target:"input","Move verified; pointer return skipped: {error}");
                            }
                        }
                    }
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
                            move_failed(&mut state, &error);
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
                    if let Some(mv) = &analysis.best_move {
                        state.status = format!("Best move found: {mv}");
                    } else {
                        finish_game(&mut state, analysis.score);
                    }
                    state.analysis = Some(analysis);
                    Ok(())
                }
                Err(error) => Err(error.to_string()),
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
    fn castling_checkboxes_follow_confirmed_rights_for_both_colors() {
        for (color, rights, king, queen) in [
            ("w", "Qkq", false, true),
            ("w", "Kkq", true, false),
            ("w", "kq", false, false),
            ("w", "KQq", true, true),
            ("b", "KQq", false, true),
            ("b", "KQk", true, false),
            ("b", "KQ", false, false),
            ("b", "Qkq", true, true),
        ] {
            let session = Session::default();
            session
                .configure(&json!({"color":color,"kingside":true,"queenside":true}))
                .unwrap();
            let position = KnownPosition {
                // Returning to the original squares must not restore lost rights.
                fen: format!("r3k2r/8/8/8/8/8/8/R3K2R w {rights} - 0 1"),
                geometry: chesspilot_core::board::BoardGeometry::new(0., 0., 80.).unwrap(),
                source: CaptureBounds {
                    x: 0,
                    y: 0,
                    width: 800,
                    height: 800,
                },
            };
            confirm(&mut lock(&session.state), position.clone()).unwrap();
            assert_eq!(session.snapshot()["kingside"], king, "{color} {rights}");
            assert_eq!(session.snapshot()["queenside"], queen, "{color} {rights}");
            session
                .configure(&json!({"kingside":true,"queenside":true}))
                .unwrap();
            assert_eq!(session.snapshot()["kingside"], king);
            assert_eq!(session.snapshot()["queenside"], queen);
            session
                .configure(&json!({"kingside":false,"queenside":false}))
                .unwrap();
            confirm(&mut lock(&session.state), position).unwrap();
            assert_eq!(session.snapshot()["kingside"], false);
            assert_eq!(session.snapshot()["queenside"], false);
            session.configure(&json!({"color":null})).unwrap();
            session
                .configure(&json!({"color":color,"kingside":true,"queenside":true}))
                .unwrap();
            assert_eq!(session.snapshot()["kingside"], true);
            assert_eq!(session.snapshot()["queenside"], true);
        }
    }
    #[test]
    fn game_results_preserve_readiness_and_only_reset_for_a_new_game() {
        for (score, confirmed, expected) in [
            (Some(Score::Mate(1)), true, Some("checkmate")),
            (Some(Score::Mate(-1)), true, None),
            (Some(Score::Mate(3)), true, None),
            (Some(Score::Mate(0)), false, Some("checkmate")),
            (Some(Score::Centipawns(0)), false, Some("stalemate")),
            (None, false, Some("game_over")),
            (None, false, Some("stalemate")),
        ] {
            let session = Arc::new(Session::default());
            session.configure(&json!({"color":"w"})).unwrap();
            {
                let mut state = lock(&session.state);
                state.engine_ready = true;
                state.capture_ready = true;
                if score.is_none() && expected == Some("stalemate") {
                    state.analysis = Some(Analysis {
                        best_move: Some("b6a6".into()),
                        updated_fen: None,
                        score: Some(Score::Centipawns(0)),
                        depth: 10,
                        stopped: false,
                    });
                }
                played(
                    &mut state,
                    MoveOutcome {
                        analysis: Analysis {
                            best_move: confirmed.then(|| "b6b7".into()),
                            updated_fen: None,
                            score,
                            depth: 10,
                            stopped: false,
                        },
                        confirmed_fen: confirmed.then(|| "k7/1Q6/2K5/8/8/8/8/8 b - - 1 1".into()),
                        geometry: chesspilot_core::board::BoardGeometry::new(0., 0., 80.).unwrap(),
                        source: CaptureBounds {
                            x: 0,
                            y: 0,
                            width: 800,
                            height: 800,
                        },
                    },
                )
                .unwrap();
            }
            assert_eq!(session.snapshot()["game_result"], json!(expected));
            assert_eq!(session.snapshot()["error"], Value::Null);
            if expected.is_some() {
                assert!(session.play(&json!({})).unwrap_err().contains("New game"));
                assert_eq!(session.snapshot()["busy"], false);
                assert_eq!(session.snapshot()["auto_available"], false);
                session
                    .progress(
                        session.generation.load(Ordering::Acquire),
                        10,
                        Progress::Terminal,
                    )
                    .unwrap();
                assert_eq!(session.snapshot()["game_result"], json!(expected));
                session.configure(&json!({"depth":16})).unwrap();
                assert_eq!(session.snapshot()["game_result"], json!(expected));
            }
            session.configure(&json!({"color":null})).unwrap();
            assert_eq!(session.snapshot()["game_result"], Value::Null);
            assert_eq!(session.snapshot()["confirmed_fen"], Value::Null);
            assert_eq!(session.snapshot()["engine_ready"], true);
            assert_eq!(session.snapshot()["capture_ready"], true);
        }
    }
    #[test]
    fn a_position_error_does_not_turn_a_ready_engine_into_a_setup_failure() {
        let mut state = State {
            engine_ready: true,
            capture_ready: true,
            ..State::default()
        };
        move_failed(
            &mut state,
            &crate::controller::PlayError::Engine(
                "Unsupported position. King can be captured".into(),
            ),
        );
        assert!(state.engine_ready);
        assert!(state.capture_ready);
        assert!(state.game_result.is_none());
    }
    #[test]
    fn a_rejected_baseline_is_discarded_so_the_next_play_can_resynchronize() {
        use crate::controller::PlayError;
        for error in [
            PlayError::PositionChanged,
            PlayError::HistoryMismatch,
            PlayError::GeometryChanged,
        ] {
            let mut state = State::default();
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
            confirm(&mut state, position.clone()).unwrap();
            assert!(known_position(&state).is_some());
            move_failed(&mut state, &error);
            assert!(known_position(&state).is_none(), "{error}");
            assert_eq!(state.game.last_fen, position.fen);
            confirm(&mut state, position).unwrap();
            assert!(known_position(&state).is_some());
        }
    }
    #[test]
    fn auto_is_available_before_the_first_manual_move_when_services_and_color_are_ready() {
        let session = Session::default();
        assert_eq!(session.snapshot()["auto_available"], false);
        {
            let mut state = lock(&session.state);
            state.engine_ready = true;
            state.capture_ready = true;
        }
        assert_eq!(session.snapshot()["auto_available"], false);
        session.configure(&json!({"color":"w"})).unwrap();
        assert_eq!(session.snapshot()["auto_available"], true);
        assert_eq!(session.snapshot()["confirmed_fen"], Value::Null);
        session.configure(&json!({"color":null})).unwrap();
        assert_eq!(session.snapshot()["auto_available"], false);
    }
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
            assert_eq!(session.snapshot()["auto_available"], true);
            assert_eq!(lock(&session.state).history_valid, !dispatched);
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
        session.play(&json!({})).unwrap();
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
