//! Serialized capture/analyze/execute/verify port of game/move_processor.py and move_execution.py.
use crate::{
    desktop::{self, input::InputError, Capture, Observation, RawObservation},
    engine::{Analysis, EngineService, Score},
    vision::{BoardReader, Predictor},
};
use chesspilot_core::{
    board::{fen_to_list, BoardGeometry, Point},
    config::{self, MoveMode, Settings},
    detection::get_fen_from_position,
    fen::{is_two_square_king_move, update_fen_castling_rights, CastleSide},
    notation::Move,
    promotion::detect_promotion_pieces,
    validation::{did_castling_move, did_my_piece_move},
    Color,
};
use std::{
    fmt,
    sync::atomic::{AtomicBool, Ordering},
    thread,
    time::{Duration, Instant},
};

pub trait BoardSource {
    fn observe(&mut self, color: Color, cancelled: &AtomicBool) -> Result<Observation, String>;
    fn raw(&mut self, cancelled: &AtomicBool) -> Result<RawObservation, String>;
}
pub struct Perception<'a, C, P> {
    pub capture: C,
    pub reader: &'a mut BoardReader<P>,
}
impl<C: Capture, P: Predictor> BoardSource for Perception<'_, C, P> {
    fn observe(&mut self, color: Color, cancelled: &AtomicBool) -> Result<Observation, String> {
        desktop::observe(&mut self.capture, self.reader, color, cancelled)
    }
    fn raw(&mut self, cancelled: &AtomicBool) -> Result<RawObservation, String> {
        desktop::capture_positions(&mut self.capture, self.reader, false, cancelled)
    }
}
pub trait Automation {
    fn move_piece(
        &mut self,
        start: Point,
        end: Point,
        mode: MoveMode,
        cancelled: &AtomicBool,
    ) -> Result<(), InputError>;
    fn tap(&mut self, point: Point, cancelled: &AtomicBool) -> Result<(), InputError>;
    fn wait(&mut self, duration: Duration, cancelled: &AtomicBool) -> Result<(), InputError> {
        let deadline = Instant::now() + duration;
        loop {
            if cancelled.load(Ordering::Acquire) {
                return Err(InputError::Cancelled { dispatched: false });
            }
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                return Ok(());
            }
            thread::sleep(remaining.min(Duration::from_millis(5)));
        }
    }
}
#[cfg(windows)]
impl Automation for desktop::windows::WindowsPointer {
    fn move_piece(
        &mut self,
        start: Point,
        end: Point,
        mode: MoveMode,
        cancelled: &AtomicBool,
    ) -> Result<(), InputError> {
        desktop::input::windows_move(self, start, end, mode, cancelled)
    }
    fn tap(&mut self, point: Point, cancelled: &AtomicBool) -> Result<(), InputError> {
        desktop::input::windows_tap(self, point, cancelled)
    }
}
pub trait Analyzer {
    fn analyze(
        &mut self,
        depth: u32,
        fen: &str,
        cancelled: &AtomicBool,
        progress: &mut dyn FnMut(u32, Option<Score>),
    ) -> Result<Analysis, String>;
}
impl Analyzer for EngineService {
    fn analyze(
        &mut self,
        depth: u32,
        fen: &str,
        cancelled: &AtomicBool,
        progress: &mut dyn FnMut(u32, Option<Score>),
    ) -> Result<Analysis, String> {
        self.get_best_move(depth, fen, cancelled, progress)
            .map_err(|e| e.to_string())
    }
}
#[derive(Debug)]
pub enum PlayError {
    Stopped,
    Detection(String),
    GeometryChanged,
    PositionChanged,
    StaleCapture,
    Engine(String),
    Input(InputError),
    VerificationFailed,
}
impl fmt::Display for PlayError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Stopped => write!(f, "Stopped"),
            Self::Detection(e) => write!(f, "Board detection failed: {e}"),
            Self::GeometryChanged => write!(
                f,
                "Board or capture geometry changed; rescan before playing"
            ),
            Self::PositionChanged => {
                write!(f, "Board changed during analysis; analyze the new position")
            }
            Self::StaleCapture => write!(f, "Board capture is too old to dispatch input; rescan"),
            Self::Engine(e) => write!(f, "Engine error: {e}"),
            Self::Input(e) => e.fmt(f),
            Self::VerificationFailed => write!(
                f,
                "Move could not be verified; check the board before retrying"
            ),
        }
    }
}
impl std::error::Error for PlayError {}
impl From<InputError> for PlayError {
    fn from(error: InputError) -> Self {
        if matches!(error, InputError::Cancelled { .. }) {
            Self::Stopped
        } else {
            Self::Input(error)
        }
    }
}
pub enum Progress {
    Status(&'static str),
    Analysis(u32, Option<Score>),
    Candidate(Analysis),
}
pub struct MoveOutcome {
    pub analysis: Analysis,
    pub confirmed_fen: Option<String>,
    pub geometry: BoardGeometry,
}
fn check(cancelled: &AtomicBool) -> Result<(), PlayError> {
    if cancelled.load(Ordering::Acquire) {
        Err(PlayError::Stopped)
    } else {
        Ok(())
    }
}
fn placement(fen: &str) -> &str {
    fen.split_whitespace().next().unwrap_or("")
}
fn same_geometry(a: BoardGeometry, b: BoardGeometry) -> bool {
    (a.x - b.x).abs() <= 2.
        && (a.y - b.y).abs() <= 2.
        && (a.square_size - b.square_size).abs() <= 0.25
}
fn geometry(reference: &Observation, current: &Observation) -> Result<(), PlayError> {
    if reference.source != current.source
        || !same_geometry(reference.board.geometry, current.board.geometry)
    {
        Err(PlayError::GeometryChanged)
    } else {
        Ok(())
    }
}
fn fresh(captured_at: Instant) -> Result<(), PlayError> {
    if captured_at.elapsed() > Duration::from_secs(3) {
        Err(PlayError::StaleCapture)
    } else {
        Ok(())
    }
}
fn observe(
    source: &mut impl BoardSource,
    input: &mut impl Automation,
    color: Color,
    cancelled: &AtomicBool,
) -> Result<Observation, PlayError> {
    let mut last = "No board observation".to_owned();
    for attempt in 0..config::MAX_FEN_EXTRACTION_RETRIES {
        check(cancelled)?;
        match source.observe(color, cancelled) {
            Ok(value) => {
                check(cancelled)?;
                return Ok(value);
            }
            Err(e) => last = e,
        }
        if attempt + 1 < config::MAX_FEN_EXTRACTION_RETRIES {
            input.wait(Duration::from_secs_f64(config::FEN_RETRY_DELAY), cancelled)?;
        }
    }
    check(cancelled)?;
    Err(PlayError::Detection(last))
}
fn dispatch(
    input: &mut impl Automation,
    observation: &Observation,
    color: Color,
    mv: Move,
    mode: MoveMode,
    cancelled: &AtomicBool,
) -> Result<(), PlayError> {
    check(cancelled)?;
    fresh(observation.captured_at)?;
    let (from, to) = mv.indices(color);
    let point = |square: (usize, usize)| {
        observation
            .board
            .geometry
            .center(square.0, square.1)
            .and_then(|p| observation.source.input_point(p))
            .map_err(PlayError::Detection)
    };
    input.move_piece(point(from)?, point(to)?, mode, cancelled)?;
    check(cancelled)
}
fn settle(
    input: &mut impl Automation,
    mode: MoveMode,
    cancelled: &AtomicBool,
) -> Result<(), PlayError> {
    input.wait(
        Duration::from_millis(if mode == MoveMode::Click { 400 } else { 100 }),
        cancelled,
    )?;
    Ok(())
}
fn verify(
    source: &mut impl BoardSource,
    input: &mut impl Automation,
    reference: &Observation,
    color: Color,
    expected: &str,
    promotion: bool,
    cancelled: &AtomicBool,
) -> Result<(), PlayError> {
    for _ in 0..if promotion { 4 } else { 2 } {
        input.wait(
            Duration::from_millis(if promotion { 300 } else { 200 }),
            cancelled,
        )?;
        check(cancelled)?;
        if let Ok(current) = source.observe(color, cancelled) {
            geometry(reference, &current)?;
            fresh(current.captured_at)?;
            if placement(&current.board.fen) == placement(expected) {
                check(cancelled)?;
                return Ok(());
            }
        }
    }
    check(cancelled)?;
    Err(PlayError::VerificationFailed)
}
struct CastleMove<'a> {
    king: &'a str,
    side: CastleSide,
    expected: &'a str,
}
fn rook_for(color: Color, side: CastleSide) -> &'static str {
    match (color, side) {
        (Color::White, CastleSide::Kingside) => "h1f1",
        (Color::White, CastleSide::Queenside) => "a1d1",
        (Color::Black, CastleSide::Kingside) => "h8f8",
        (Color::Black, CastleSide::Queenside) => "a8d8",
    }
}
fn castle(
    source: &mut impl BoardSource,
    input: &mut impl Automation,
    reference: &Observation,
    color: Color,
    plan: CastleMove<'_>,
    mode: MoveMode,
    cancelled: &AtomicBool,
) -> Result<bool, PlayError> {
    let CastleMove {
        king,
        side,
        expected,
    } = plan;
    let rook = rook_for(color, side);
    let rook_move = Move::parse(rook).map_err(PlayError::Engine)?;
    input.wait(Duration::from_millis(250), cancelled)?;
    for _ in 0..2 {
        check(cancelled)?;
        if let Ok(current) = source.observe(color, cancelled) {
            geometry(reference, &current)?;
            fresh(current.captured_at)?;
            if placement(&current.board.fen) == placement(expected) {
                return Ok(true);
            }
            let cells = fen_to_list(&current.board.fen).map_err(PlayError::Detection)?;
            let rook_char = if color == Color::White { 'R' } else { 'r' };
            if did_my_piece_move(color, &reference.board.fen, &current.board.fen, king)
                .map_err(PlayError::Detection)?
                && cells[rook_move.from] == rook_char
                && cells[rook_move.to] == ' '
            {
                dispatch(input, &current, color, rook_move, mode, cancelled)?;
                settle(input, mode, cancelled)?;
                return Ok(false);
            }
        }
        input.wait(Duration::from_millis(200), cancelled)?;
    }
    Err(PlayError::VerificationFailed)
}
fn menu_choice(
    raw: &RawObservation,
    board: BoardGeometry,
    color: Color,
    mv: Move,
) -> Result<Option<Point>, PlayError> {
    let Some(wanted) = mv.promotion else {
        return Ok(None);
    };
    let (_, square) = mv.indices(color);
    let target = board
        .center(square.0, square.1)
        .map_err(PlayError::Detection)?;
    let size = board.square_size;
    let pieces = detect_promotion_pieces(&raw.boxes, board, color).map_err(PlayError::Detection)?;
    let mut choice = None;
    // A four-piece aligned menu near the destination is required; ordinary back-rank pieces are insufficient.
    for anchor in pieces.iter().filter(|p| {
        (p.position.x - target.x).abs() <= size * 0.65
            && (p.position.y - target.y).abs() <= size * 0.65
    }) {
        for (dx, dy) in [(0., 1.), (0., -1.), (1., 0.), (-1., 0.)] {
            let mut chars = Vec::new();
            let mut selected = None;
            for step in 0..4 {
                let x = anchor.position.x + dx * size * step as f64;
                let y = anchor.position.y + dy * size * step as f64;
                let matches: Vec<_> = pieces
                    .iter()
                    .filter(|p| {
                        (p.position.x - x).abs() < size * 0.4
                            && (p.position.y - y).abs() < size * 0.4
                    })
                    .collect();
                if matches.len() != 1 {
                    break;
                }
                let piece = matches[0];
                let ch = piece.piece_char.to_ascii_lowercase();
                if chars.contains(&ch) {
                    break;
                }
                chars.push(ch);
                if ch == wanted {
                    selected = Some(piece.position);
                }
            }
            if chars.len() == 4 {
                if choice.is_some() && choice != selected {
                    return Ok(None);
                }
                choice = selected;
            }
        }
    }
    Ok(choice)
}
fn promote(
    source: &mut impl BoardSource,
    input: &mut impl Automation,
    reference: &Observation,
    color: Color,
    mv: Move,
    expected: &str,
    cancelled: &AtomicBool,
) -> Result<bool, PlayError> {
    let deadline = Instant::now() + Duration::from_millis(1500);
    for _ in 0..10 {
        check(cancelled)?;
        if Instant::now() >= deadline {
            break;
        }
        if let Ok(raw) = source.raw(cancelled) {
            check(cancelled)?;
            fresh(raw.captured_at)?;
            if raw.source != reference.source {
                return Err(PlayError::GeometryChanged);
            }
            let Some(board) = raw.boxes.iter().find(|b| b.class_id == 12) else {
                input.wait(Duration::from_millis(150), cancelled)?;
                continue;
            };
            let geometry = BoardGeometry::new(board.x, board.y, board.width / 8.)
                .map_err(PlayError::Detection)?;
            if !same_geometry(reference.board.geometry, geometry) {
                return Err(PlayError::GeometryChanged);
            }
            if let Some(current) =
                get_fen_from_position(color, &raw.boxes).map_err(PlayError::Detection)?
            {
                if placement(&current.fen) == placement(expected) {
                    return Ok(true);
                }
            }
            if Instant::now() >= deadline {
                break;
            }
            if let Some(point) = menu_choice(&raw, geometry, color, mv)? {
                fresh(raw.captured_at)?;
                check(cancelled)?;
                input.tap(
                    raw.source
                        .input_point(point)
                        .map_err(PlayError::Detection)?,
                    cancelled,
                )?;
                input.wait(Duration::from_millis(100), cancelled)?;
                return Ok(false);
            }
        }
        input.wait(Duration::from_millis(150), cancelled)?;
    }
    Ok(false)
}
pub fn play(
    source: &mut impl BoardSource,
    input: &mut impl Automation,
    engine: &mut impl Analyzer,
    settings: &Settings,
    color: Color,
    cancelled: &AtomicBool,
    mut progress: impl FnMut(Progress),
) -> Result<MoveOutcome, PlayError> {
    progress(Progress::Status("Analyzing board..."));
    let original = observe(source, input, color, cancelled)?;
    let fen = update_fen_castling_rights(
        color,
        settings.kingside,
        settings.queenside,
        &original.board.fen,
    )
    .map_err(PlayError::Detection)?;
    check(cancelled)?;
    let analysis = engine
        .analyze(settings.depth, &fen, cancelled, &mut |depth, score| {
            progress(Progress::Analysis(depth, score))
        })
        .map_err(PlayError::Engine)?;
    check(cancelled)?;
    progress(Progress::Candidate(analysis.clone()));
    let Some(value) = analysis.best_move.as_deref() else {
        return Ok(MoveOutcome {
            analysis,
            confirmed_fen: None,
            geometry: original.board.geometry,
        });
    };
    let mv = Move::parse(value).map_err(PlayError::Engine)?;
    let expected = analysis
        .updated_fen
        .as_deref()
        .ok_or_else(|| PlayError::Engine("Missing updated position".into()))?;
    let side = is_two_square_king_move(value, &fen, color).map_err(PlayError::Engine)?;
    let valid = if let Some(side) = side {
        if !(if side == CastleSide::Kingside {
            settings.kingside
        } else {
            settings.queenside
        }) {
            return Err(PlayError::Engine(
                "Engine requested disabled castling".into(),
            ));
        }
        let rook = rook_for(color, side);
        did_castling_move(color, &fen, expected, value, rook)
    } else {
        did_my_piece_move(color, &fen, expected, value)
    }
    .map_err(PlayError::Engine)?;
    if !valid {
        return Err(PlayError::Engine(
            "Best move and updated position disagree".into(),
        ));
    }
    progress(Progress::Status("Checking board before input..."));
    let current = observe(source, input, color, cancelled)?;
    geometry(&original, &current)?;
    if placement(&original.board.fen) != placement(&current.board.fen) {
        return Err(PlayError::PositionChanged);
    }
    progress(Progress::Status("Playing move..."));
    dispatch(input, &current, color, mv, settings.move_mode, cancelled)?;
    let mut confirmed = false;
    if let Some(side) = side {
        confirmed = castle(
            source,
            input,
            &current,
            color,
            CastleMove {
                king: value,
                side,
                expected,
            },
            settings.move_mode,
            cancelled,
        )?;
    } else {
        settle(input, settings.move_mode, cancelled)?;
    }
    if mv.promotion.is_some() {
        progress(Progress::Status("Checking promotion..."));
        confirmed = promote(source, input, &current, color, mv, expected, cancelled)?;
    }
    if !confirmed {
        progress(Progress::Status("Verifying move..."));
        verify(
            source,
            input,
            &current,
            color,
            expected,
            mv.promotion.is_some(),
            cancelled,
        )?;
    }
    check(cancelled)?;
    Ok(MoveOutcome {
        confirmed_fen: Some(expected.into()),
        geometry: current.board.geometry,
        analysis,
    })
}
