from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_current_fen(color_indicator):
    try:
        screenshot = capture_screenshot_in_memory()
        boxes = get_positions(screenshot)
        if boxes:
            _, _, _, fen = get_fen_from_position(color_indicator, boxes)          
            return fen
    except Exception:
        logging.error("Failed to get current FEN", exc_info=True)
        return None
