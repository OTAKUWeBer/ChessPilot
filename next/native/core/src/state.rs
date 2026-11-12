//! Source: core/game_state.py. Keep FEN histories keyed by active color.
use crate::{board::BoardGeometry, config::MoveMode, Color};

#[derive(Debug, Clone, Default)]
pub struct GameState {
    pub color_indicator: Option<Color>,
    pub last_fen: String,
    pub last_fen_by_color: [Option<String>; 2],
    pub move_mode: MoveMode,
    pub geometry: Option<BoardGeometry>,
}
impl GameState {
    pub fn set_color(&mut self, color: Color) {
        self.color_indicator = Some(color);
    }
    pub fn set_move_mode(&mut self, mode: MoveMode) {
        self.move_mode = mode;
    }
    pub fn store_board_positions(&mut self, x: f64, y: f64, size: f64) -> Result<(), String> {
        self.geometry = Some(BoardGeometry::new(x, y, size)?);
        Ok(())
    }
    pub fn update_last_fen_for_color(&mut self, fen: &str) -> Result<(), String> {
        crate::board::fen_to_list(fen)?;
        let fields: Vec<_> = fen.split_whitespace().collect();
        let color = Color::parse(fields.get(1).ok_or("Missing active color")?)?;
        self.last_fen_by_color[if color == Color::White { 0 } else { 1 }] = Some(fields[0].into());
        Ok(())
    }
}
