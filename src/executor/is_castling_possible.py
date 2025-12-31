from executor.expend_fen_row import expend_fen_row
import logging

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def is_castling_possible(fen, color, side):
    board = fen.split()[0]
    rows = board.split('/')
    if color == "w":
        last_row = expend_fen_row(rows[-1])
        if len(last_row) != 8 or last_row[4] != 'K':
            logger.debug(f"Invalid last row for white castling: {last_row}")
            return False
        if side == 'kingside':
            logger.debug(f"Checking kingside castling for white: {last_row[7]}")
            return last_row[7] == 'R'
        elif side == 'queenside':
            logger.debug(f"Checking queenside castling for white: {last_row[0]}")
            return last_row[0] == 'R'
    else:
        first_row = expend_fen_row(rows[0])
        if len(first_row) != 8 or first_row[4] != 'k':
            logger.debug(f"Invalid first row for black castling: {first_row}")
            return False
        if side == 'kingside':
            logger.debug(f"Checking kingside castling for black: {first_row[7]}")
            return first_row[7] == 'r'
        elif side == 'queenside':
            logger.debug(f"Checking queenside castling for black: {first_row[0]}")
            return first_row[0] == 'r'
    return False
