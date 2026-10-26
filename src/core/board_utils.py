from board_detection.board_reader import capture_and_extract_fen


def expand_row(row):
    """Expand a FEN row by replacing numbers with spaces."""
    out = []
    for ch in row:
        if ch.isdigit():
            out += [' '] * int(ch)
        else:
            out.append(ch)
    return out


def fen_to_list(fen):
    """Convert FEN string to a 64-element list representing the board."""
    rows = fen.split()[0].split('/')
    flat = []
    for r in rows:
        flat += expand_row(r)
    return flat  # len=64


def algebraic_to_index(sq):
    """Convert algebraic notation to board index (0-63)."""
    if not sq or len(sq) < 2 or not sq[0].isalpha() or not sq[1].isdigit():
        return 0
    file = ord(sq[0].lower()) - ord('a')         # 0..7
    rank = 8 - int(sq[1])                       # '1'→7 down to '8'→0
    file = max(0, min(7, file))
    rank = max(0, min(7, rank))
    return rank * 8 + file

def store_board_positions(board_positions, x, y, size):
    chessboard_x = x
    chessboard_y = y
    square_size = size
    board_positions.clear()
    for row in range(8):
        for col in range(8):
            pos_x = x + col * size + (size // 2)
            pos_y = y + row * size + (size // 2)
            board_positions[(col, row)] = (pos_x, pos_y)
