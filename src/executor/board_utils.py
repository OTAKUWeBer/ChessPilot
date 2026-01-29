import logging

from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from board_detection import get_positions, get_fen_from_position

logger = logging.getLogger(__name__)


def capture_and_extract_fen(color_indicator, verify_attempt):
    """Capture screenshot and extract FEN from current board state."""
    img = capture_screenshot_in_memory()
    if not img:
        logger.warning(f"Screenshot failed on verification attempt {verify_attempt + 1}")
        return None
    
    boxes = get_positions(img)
    if not boxes:
        logger.warning(f"Board detection failed on verification attempt {verify_attempt + 1}")
        return None
    
    if not any(box[5] == 12.0 for box in boxes):
        logger.warning(f"No chessboard detected on verification attempt {verify_attempt + 1}")
        return None
    
    try:
        result = get_fen_from_position(color_indicator, boxes)
        if result is None:
            logger.warning(f"FEN extraction returned None on verification attempt {verify_attempt + 1}")
            return None
        
        _, _, _, current_fen = result
        return current_fen
    except (ValueError, TypeError) as e:
        logger.warning(f"FEN extraction error on verification attempt {verify_attempt + 1}: {e}")
        return None


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
    file = ord(sq[0]) - ord('a')         # 0..7
    rank = 8 - int(sq[1])               # '1'→7 down to '8'→0
    return rank * 8 + file