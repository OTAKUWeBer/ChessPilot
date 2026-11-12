//! Ports of the Python domain modules; OS input and UI stay outside this crate.
pub mod board;
pub mod config;
pub mod detection;
pub mod fen;
pub mod notation;
pub mod state;
pub mod validation;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Color {
    White,
    Black,
}

impl Color {
    pub fn parse(value: &str) -> Result<Self, String> {
        match value {
            "w" => Ok(Self::White),
            "b" => Ok(Self::Black),
            _ => Err("Expected color w or b".into()),
        }
    }
    pub fn fen(self) -> &'static str {
        match self {
            Self::White => "w",
            Self::Black => "b",
        }
    }
    pub fn owns(self, piece: char) -> bool {
        match self {
            Self::White => "PNBRQK".contains(piece),
            Self::Black => "pnbrqk".contains(piece),
        }
    }
}
