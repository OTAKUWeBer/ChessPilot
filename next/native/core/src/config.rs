//! Source: src/core/config.py. Preserve runtime defaults during the port.
pub const VERSION: &str = "2.3.1";
pub const WINDOW_WIDTH: f64 = 380.0;
pub const WINDOW_HEIGHT: f64 = 520.0;
pub const DEFAULT_DEPTH: u32 = 15;
pub const DEFAULT_SCREENSHOT_DELAY: f64 = 0.4;
pub const OPPONENT_MOVE_SETTLE_DELAY: f64 = 0.5;
pub const AUTO_MODE_POLL_INTERVAL: f64 = 0.1;
pub const MAX_FEN_EXTRACTION_RETRIES: usize = 3;
pub const FEN_RETRY_DELAY: f64 = 0.5;
pub const MIN_MOVE_INTERVAL: f64 = 0.3;
pub const MAX_CONSECUTIVE_FAILURES: usize = 3;
pub const BOARD_DETECTION_CONFIDENCE: f32 = 0.5;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum MoveMode {
    #[default]
    Drag,
    Click,
}

#[derive(Debug, Clone)]
pub struct Settings {
    pub depth: u32,
    pub screenshot_delay: f64,
    pub move_mode: MoveMode,
    pub kingside: bool,
    pub queenside: bool,
}
impl Default for Settings {
    fn default() -> Self {
        Self {
            depth: DEFAULT_DEPTH,
            screenshot_delay: DEFAULT_SCREENSHOT_DELAY,
            move_mode: MoveMode::Drag,
            kingside: false,
            queenside: false,
        }
    }
}
