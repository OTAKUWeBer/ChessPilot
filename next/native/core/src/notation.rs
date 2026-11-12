//! Source: core/notation.py; GUI error reporting belongs to the caller.
use crate::{board::algebraic_to_index, Color};

pub type ScreenSquare = (usize, usize);

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Move {
    pub from: usize,
    pub to: usize,
    pub promotion: Option<char>,
}

impl Move {
    pub fn parse(value: &str) -> Result<Self, String> {
        if !value.is_ascii() || !matches!(value.len(), 4 | 5) {
            return Err("Expected a UCI move such as e2e4 or e7e8q".into());
        }
        let promotion = value.as_bytes().get(4).map(|ch| *ch as char);
        if promotion.is_some_and(|ch| !"qrbn".contains(ch)) {
            return Err("Invalid promotion piece".into());
        }
        Ok(Self {
            from: algebraic_to_index(&value[..2])?,
            to: algebraic_to_index(&value[2..4])?,
            promotion,
        })
    }
    pub fn indices(self, orientation: Color) -> (ScreenSquare, ScreenSquare) {
        let transform = |index: usize| match orientation {
            Color::White => (index % 8, index / 8),
            Color::Black => (7 - index % 8, 7 - index / 8),
        };
        (transform(self.from), transform(self.to))
    }
}

pub fn chess_notation_to_index(
    color: Color,
    value: &str,
) -> Result<(ScreenSquare, ScreenSquare), String> {
    Ok(Move::parse(value)?.indices(color))
}
