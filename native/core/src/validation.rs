//! Source: game/move_validator.py, including promotion and en-passant comparisons.
use crate::{board::fen_to_list, notation::Move, Color};

pub fn did_my_piece_move(
    color: Color,
    before: &str,
    after: &str,
    value: &str,
) -> Result<bool, String> {
    let before = fen_to_list(before)?;
    let after = fen_to_list(after)?;
    let mv = Move::parse(value)?;
    let piece = before[mv.from];
    let target = if "Pp".contains(piece) {
        mv.promotion
            .map(|ch| {
                if color == Color::White {
                    ch.to_ascii_uppercase()
                } else {
                    ch
                }
            })
            .unwrap_or(piece)
    } else {
        piece
    };
    let mut allowed = [false; 64];
    allowed[mv.from] = true;
    allowed[mv.to] = true;
    if "Pp".contains(piece) && (mv.from % 8).abs_diff(mv.to % 8) == 1 && before[mv.to] == ' ' {
        let captured = mv.from / 8 * 8 + mv.to % 8;
        let opponent = if color == Color::White { 'p' } else { 'P' };
        if before[captured] == opponent && after[captured] == ' ' {
            allowed[captured] = true;
        }
    }
    Ok(color.owns(piece)
        && after[mv.from] == ' '
        && after[mv.to] == target
        && (0..64).all(|i| before[i] == after[i] || allowed[i]))
}

pub fn did_castling_move(
    color: Color,
    before: &str,
    after: &str,
    king: &str,
    rook: &str,
) -> Result<bool, String> {
    let before = fen_to_list(before)?;
    let after = fen_to_list(after)?;
    let king = Move::parse(king)?;
    let rook = Move::parse(rook)?;
    // Retain the current four-square verification contract during the domain port.
    Ok([king, rook].iter().all(|mv| {
        color.owns(before[mv.from]) && after[mv.from] == ' ' && after[mv.to] == before[mv.from]
    }))
}
