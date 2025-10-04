import logging
from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from executor.expend_fen_row import expend_fen_row
from executor.is_castling_possible import is_castling_possible
from executor.update_fen_castling_rights import update_fen_castling_rights
from executor.get_current_fen import get_current_fen

logger = logging.getLogger(__name__)

class BoardAnalyzer:
    @staticmethod
    def capture_screenshot(root, auto_mode_var):
        logger.debug("Capturing board screenshot")
        return capture_screenshot_in_memory(root, auto_mode_var)

    @staticmethod
    def get_board_fen(color_indicator, root, auto_mode_var):
        logger.debug("Getting current board FEN")
        screenshot = capture_screenshot_in_memory(root, auto_mode_var)
        if not screenshot:
            logger.warning("Screenshot capture failed")
            return None

        boxes = get_positions(screenshot)
        if not boxes:
            logger.error("No chessboard found in screenshot")
            return None

        result = get_fen_from_position(color_indicator, boxes)
        if not result:
            logger.error("FEN extraction failed")
            return None

        chessboard_x, chessboard_y, square_size, fen = result
        return {
            'fen': fen,
            'chessboard_x': chessboard_x,
            'chessboard_y': chessboard_y,
            'square_size': square_size
        }

    @staticmethod
    def read_current_fen(color_indicator):
        logger.debug("Reading current FEN")
        return get_current_fen(color_indicator)

    @staticmethod
    def expand_fen_row(row: str):
        logger.debug(f"Expanding FEN row: {row}")
        return expend_fen_row(row)

    @staticmethod
    def check_castling_possible(fen: str, color_indicator: str):
        result = is_castling_possible(fen, color_indicator, "kingside") or \
                 is_castling_possible(fen, color_indicator, "queenside")
        logger.debug(f"Check castling possibility for '{fen}': {result}")
        return result

    @staticmethod
    def adjust_castling_fen(color_indicator, kingside_var, queenside_var, fen: str):
        logger.debug(f"Adjusting castling rights for FEN: {fen}")
        return update_fen_castling_rights(color_indicator, kingside_var, queenside_var, fen)
