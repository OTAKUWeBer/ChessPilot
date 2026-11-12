//! Pure piece discovery from game/promotion.py; gesture/menu ownership stays in runtime.
use crate::{
    board::{BoardGeometry, Point},
    detection::{Detection, CLASS_TO_FEN, PROMOTION_PIECE_IDS, PROMOTION_PIECE_IDS_BLACK},
    Color,
};
#[derive(Debug, Clone, PartialEq)]
pub struct PromotionPiece {
    pub class_id: u8,
    pub confidence: f64,
    pub position: Point,
    pub file: Option<usize>,
    pub rank: Option<usize>,
    pub is_promotion_rank: bool,
    pub piece_char: char,
}
pub fn detect_promotion_pieces(
    boxes: &[Detection],
    board: BoardGeometry,
    color: Color,
) -> Result<Vec<PromotionPiece>, String> {
    BoardGeometry::new(board.x, board.y, board.square_size)?;
    let ids = if color == Color::White {
        PROMOTION_PIECE_IDS
    } else {
        PROMOTION_PIECE_IDS_BLACK
    };
    let mut pieces = Vec::new();
    for b in boxes
        .iter()
        .filter(|b| ids.contains(&b.class_id) && b.confidence > 0.4)
    {
        if [b.x, b.y, b.width, b.height, b.confidence]
            .iter()
            .any(|n| !n.is_finite())
            || b.width < 0.
            || b.height < 0.
        {
            return Err("Invalid promotion detection".into());
        }
        let position = Point {
            x: b.x + b.width / 2.,
            y: b.y + b.height / 2.,
        };
        let rel_x = position.x - board.x;
        let rel_y = position.y - board.y;
        let size = board.square_size;
        if rel_x <= -size || rel_x >= 9. * size || rel_y <= -size || rel_y >= 9. * size {
            continue;
        }
        let file = (rel_x / size).floor();
        let rank = (rel_y / size).floor();
        pieces.push(PromotionPiece {
            class_id: b.class_id,
            confidence: b.confidence,
            position,
            file: if (0.0..8.).contains(&file) {
                Some(file as usize)
            } else {
                None
            },
            rank: if (0.0..8.).contains(&rank) {
                Some(rank as usize)
            } else {
                None
            },
            is_promotion_rank: rank == if color == Color::White { 0. } else { 7. },
            piece_char: CLASS_TO_FEN[b.class_id as usize],
        });
    }
    Ok(pieces)
}
pub fn find_promotion_dialog_pieces(
    boxes: &[Detection],
    board: BoardGeometry,
    color: Color,
) -> Result<Vec<PromotionPiece>, String> {
    let mut pieces = detect_promotion_pieces(boxes, board, color)?;
    pieces.sort_by(|a, b| {
        a.position
            .y
            .total_cmp(&b.position.y)
            .then(a.position.x.total_cmp(&b.position.x))
    });
    pieces.truncate(4);
    Ok(pieces)
}
