//! Source: core/board_utils.py and GameState.store_board_positions.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BoardGeometry {
    pub x: f64,
    pub y: f64,
    pub square_size: f64,
}

impl BoardGeometry {
    pub fn new(x: f64, y: f64, square_size: f64) -> Result<Self, String> {
        if !x.is_finite() || !y.is_finite() || !square_size.is_finite() || square_size <= 0.0 {
            return Err("Board geometry must be finite with a positive square size".into());
        }
        Ok(Self { x, y, square_size })
    }
    pub fn center(self, col: usize, row: usize) -> Result<Point, String> {
        if col >= 8 || row >= 8 {
            return Err("Square is outside the board".into());
        }
        // Python uses size // 2, including for fractional detector sizes.
        let half = (self.square_size / 2.0).floor();
        Ok(Point {
            x: self.x + col as f64 * self.square_size + half,
            y: self.y + row as f64 * self.square_size + half,
        })
    }
    pub fn positions(self) -> [[Point; 8]; 8] {
        std::array::from_fn(|row| {
            std::array::from_fn(|col| self.center(col, row).expect("Indices generated in bounds"))
        })
    }
}

pub fn expand_row(row: &str) -> Result<Vec<char>, String> {
    let mut cells = Vec::with_capacity(8);
    for ch in row.chars() {
        match ch {
            '1'..='8' => cells.extend(std::iter::repeat_n(' ', ch.to_digit(10).unwrap() as usize)),
            ch if "pnbrqkPNBRQK".contains(ch) => cells.push(ch),
            _ => return Err("Invalid FEN piece or empty-square count".into()),
        }
    }
    if cells.len() != 8 {
        return Err("FEN row must contain eight squares".into());
    }
    Ok(cells)
}

pub fn fen_to_list(fen: &str) -> Result<[char; 64], String> {
    let placement = fen.split_whitespace().next().ok_or("Empty FEN")?;
    let rows: Vec<_> = placement.split('/').collect();
    if rows.len() != 8 {
        return Err("FEN must contain eight rows".into());
    }
    let mut cells = Vec::with_capacity(64);
    for row in rows {
        cells.extend(expand_row(row)?);
    }
    cells
        .try_into()
        .map_err(|_| "FEN must contain 64 squares".into())
}

pub fn algebraic_to_index(square: &str) -> Result<usize, String> {
    let bytes = square.as_bytes();
    if bytes.len() != 2 || !(b'a'..=b'h').contains(&bytes[0]) || !(b'1'..=b'8').contains(&bytes[1])
    {
        return Err("Expected square a1 through h8".into());
    }
    Ok((b'8' - bytes[1]) as usize * 8 + (bytes[0] - b'a') as usize)
}
