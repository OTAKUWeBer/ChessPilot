//! Source: core/fen_utils.py and board_detection/fen_extractor.py:flip_board.
use crate::{board::fen_to_list, notation::Move, Color};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CastleSide {
    Kingside,
    Queenside,
}

pub fn flip_board(fen: &str) -> Result<String, String> {
    fen_to_list(fen)?;
    let mut fields: Vec<String> = fen.split_whitespace().map(str::to_owned).collect();
    fields[0] = fields[0]
        .split('/')
        .rev()
        .map(|row| row.chars().rev().collect::<String>())
        .collect::<Vec<_>>()
        .join("/");
    Ok(fields.join(" "))
}

/// Placement-based compatibility check, matching Python; not full legal rights.
pub fn is_castling_possible(fen: &str, color: Color, side: CastleSide) -> Result<bool, String> {
    let board = fen_to_list(fen)?;
    let (base, king, rook) = match color {
        Color::White => (56, 'K', 'R'),
        Color::Black => (0, 'k', 'r'),
    };
    Ok(board[base + 4] == king
        && board[base
            + match side {
                CastleSide::Kingside => 7,
                CastleSide::Queenside => 0,
            }]
            == rook)
}

pub fn is_two_square_king_move(
    value: &str,
    fen: &str,
    color: Color,
) -> Result<Option<CastleSide>, String> {
    if value.is_empty() || value == "(none)" {
        return Ok(None);
    }
    let mv = Move::parse(value)?;
    let board = fen_to_list(fen)?;
    let king = if color == Color::White { 'K' } else { 'k' };
    if mv.from / 8 != mv.to / 8 || (mv.from % 8).abs_diff(mv.to % 8) != 2 || board[mv.from] != king
    {
        return Ok(None);
    }
    Ok(Some(if mv.to > mv.from {
        CastleSide::Kingside
    } else {
        CastleSide::Queenside
    }))
}

pub fn update_fen_castling_rights(
    player: Color,
    kingside: bool,
    queenside: bool,
    fen: &str,
) -> Result<String, String> {
    let mut fields: Vec<_> = fen.split_whitespace().map(str::to_owned).collect();
    if fields.len() != 6 {
        return Err("Expected six FEN fields".into());
    }
    let mut rights = String::new();
    for (color, side, symbol, enabled) in [
        (Color::White, CastleSide::Kingside, 'K', kingside),
        (Color::White, CastleSide::Queenside, 'Q', queenside),
        (Color::Black, CastleSide::Kingside, 'k', kingside),
        (Color::Black, CastleSide::Queenside, 'q', queenside),
    ] {
        if is_castling_possible(fen, color, side)? && (color != player || enabled) {
            rights.push(symbol);
        }
    }
    fields[2] = if rights.is_empty() {
        "-".into()
    } else {
        rights
    };
    Ok(fields.join(" "))
}
