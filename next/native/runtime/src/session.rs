//! Session ownership behind the Flutter/native boundary. Heavy work stays off Dart's UI isolate.
#[cfg(any(windows, target_os = "linux"))]
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
#[cfg(any(windows, target_os = "linux"))]
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
#[cfg(any(windows, target_os = "linux"))]
fn confirm(state: &mut State, position: KnownPosition) -> Result<(), String> {
    state.game.update_last_fen_for_color(&position.fen)?;
    state.game.last_fen = position.fen;
    state.game.geometry = Some(position.geometry);
    state.confirmed_source = Some(position.source);
    state.history_valid = true;
    state.input_in_flight = false;
    Ok(())
}
#[cfg(any(windows, target_os = "linux"))]
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
                self.cancelled.store(true, Ordering::Release);
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
    pub fn stop(&self) {
        let mut s = lock(&self.state);
        self.cancelled.store(true, Ordering::Release);
        self.generation.fetch_add(1, Ordering::AcqRel);
        s.auto_mode = false;
        if s.input_in_flight {
            s.history_valid = false;
        }
        s.status = if s.busy { "Stopping..." } else { "Stopped" }.into();
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
            self.cancelled.store(false, Ordering::Release);
            id = self.generation.fetch_add(1, Ordering::AcqRel) + 1;
        }
        if let Some(old) = slot.take() {
            let _ = old.join();
        }
        let session = self.clone();
        match thread::Builder::new()
            .name("chesspilot-session".into())
            .spawn(move || {
                let result =
                    std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| task(&session, id)))
                        .unwrap_or_else(|_| Err("Native operation panicked".into()));
                let mut state = lock(&session.state);
                if session.generation.load(Ordering::Acquire) == id {
                    if let Err(error) = result {
                        state.status = error.clone();
                        state.error = Some(error);
                    }
                } else {
                    state.status = "Stopped".into();
                }
                state.busy = false;
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
        let path = if let Some(path) = args.get("engine_path") {
            PathBuf::from(path.as_str().ok_or("Expected engine path")?)
        } else {
            let directories = resources::native_asset_directories().map_err(|e| e.to_string())?;
            resources::stockfish_path(&directories).map_err(|e| e.to_string())?
        };
        let options = if let Some(path) = args.get("config_path") {
            resources::engine_options(
                &std::fs::read_to_string(path.as_str().ok_or("Expected config path")?)
                    .map_err(|e| e.to_string())?,
            )
            .map_err(|e| e.to_string())?
        } else {
            resources::engine_options(resources::DEFAULT_CONFIG).map_err(|e| e.to_string())?
        };
        let args = args.clone();
        self.launch(
            if with_capture {
                "initialize"
            } else {
                "initialize_engine"
            },
            move |session, id| {
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
                let mut engine =
                    EngineService::new(Command::new(path), options, Timeouts::default())
                        .map_err(|e| e.to_string())?;
                engine.initialize().map_err(|e| e.to_string())?;
                {
                    let mut state = lock(&session.state);
                    if session.generation.load(Ordering::Acquire) != id {
                        return Ok(());
                    }
                    *lock(&session.engine) = Some(engine);
                    state.engine_ready = true;
                    state.status = "Stockfish ready".into();
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
        #[cfg(any(windows, target_os = "linux"))]
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
    #[cfg(any(windows, target_os = "linux"))]
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
        #[cfg(not(any(windows, target_os = "linux")))]
        {
            let _ = automatic;
            Err("Native capture/input for this platform is not connected yet".into())
        }
        #[cfg(any(windows, target_os = "linux"))]
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
                            session.cancelled.store(true, Ordering::Release);
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

#[cfg(all(test, any(windows, target_os = "linux")))]
mod tests {
    use super::*;
    use std::time::{Duration, Instant};
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
