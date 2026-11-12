//! Source: board_detection/model_classes.py and fen_extractor.py.
use crate::{board::BoardGeometry, fen::flip_board, Color};

pub const CHESSBOARD_CLASS_ID: u8 = 12;
pub const CLASS_TO_FEN: [char; 12] = ['p', 'r', 'n', 'b', 'q', 'k', 'P', 'R', 'N', 'B', 'Q', 'K'];
pub const PROMOTION_PIECE_IDS: [u8; 4] = [10, 7, 9, 8];
pub const PROMOTION_PIECE_IDS_BLACK: [u8; 4] = [4, 1, 3, 2];

#[derive(Debug, Clone, Copy)]
pub struct Detection {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
    pub confidence: f64,
    pub class_id: u8,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DetectedBoard {
    pub geometry: BoardGeometry,
    pub fen: String,
}

pub fn get_fen_from_position(
    color: Color,
    boxes: &[Detection],
) -> Result<Option<DetectedBoard>, String> {
    let Some(board) = boxes.iter().find(|b| b.class_id == CHESSBOARD_CLASS_ID) else {
        return Ok(None);
    };
    let geometry = BoardGeometry::new(board.x, board.y, board.width / 8.0)?;
    let mut grid = [[' '; 8]; 8];
    let mut confidence = [[0.0; 8]; 8];
    for b in boxes.iter().filter(|b| b.class_id != CHESSBOARD_CLASS_ID) {
        if [b.x, b.y, b.width, b.height, b.confidence]
            .iter()
            .any(|v| !v.is_finite())
            || b.width < 0.0
            || b.height < 0.0
        {
            return Err("Invalid detection coordinates".into());
        }
        let col = ((b.x + b.width / 2.0 - board.x) / geometry.square_size).floor();
        let row = ((b.y + b.height / 2.0 - board.y) / geometry.square_size).floor();
        if !(0.0..8.0).contains(&col) || !(0.0..8.0).contains(&row) {
            continue;
        }
        let (col, row) = (col as usize, row as usize);
        if b.confidence > confidence[row][col] {
            grid[row][col] = *CLASS_TO_FEN
                .get(b.class_id as usize)
                .ok_or("Unknown piece class")?;
            confidence[row][col] = b.confidence;
        }
    }
    if grid.iter().flatten().filter(|&&p| p == 'K').count() != 1
        || grid.iter().flatten().filter(|&&p| p == 'k').count() != 1
    {
        return Ok(None);
    }
    let mut rows = Vec::new();
    for row in grid {
        let mut text = String::new();
        let mut empty = 0u8;
        for cell in row {
            if cell == ' ' {
                empty += 1;
            } else {
                if empty > 0 {
                    text.push(char::from(b'0' + empty));
                    empty = 0;
                }
                text.push(cell);
            }
        }
        if empty > 0 {
            text.push(char::from(b'0' + empty));
        }
        rows.push(text);
    }
    // Preserve Python's supplied active-color/default-history contract during porting.
    let mut fen = format!("{} {} - - 0 1", rows.join("/"), color.fen());
    if color == Color::Black {
        fen = flip_board(&fen)?;
    }
    Ok(Some(DetectedBoard { geometry, fen }))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn kings_orientation_confidence_and_missing_board() {
        let detection = |x, y, width, height, class_id| Detection {
            x,
            y,
            width,
            height,
            class_id,
            confidence: 0.95,
        };
        let mut boxes = vec![
            detection(0.0, 0.0, 800.0, 800.0, 12),
            detection(410.0, 10.0, 80.0, 80.0, 5),
            detection(410.0, 710.0, 80.0, 80.0, 11),
        ];
        assert_eq!(
            get_fen_from_position(Color::White, &boxes)
                .unwrap()
                .unwrap()
                .fen,
            "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
        );
        assert_eq!(
            get_fen_from_position(Color::Black, &boxes)
                .unwrap()
                .unwrap()
                .fen,
            "3K4/8/8/8/8/8/8/3k4 b - - 0 1"
        );
        assert!(get_fen_from_position(Color::White, &[]).unwrap().is_none());
        boxes.push(Detection {
            confidence: 0.99,
            ..detection(410.0, 10.0, 80.0, 80.0, 4)
        });
        assert!(get_fen_from_position(Color::White, &boxes)
            .unwrap()
            .is_none());
    }
}
