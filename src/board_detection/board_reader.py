"""
Live board visual perception service.
Captures desktop screenshots and extracts FEN notation using ONNX model detections.
"""

import logging
from board_detection.get_positions import get_positions
from board_detection.fen_extractor import get_fen_from_position
from utils.system_interaction import capture_screenshot_in_memory

logger = logging.getLogger(__name__)


def capture_and_extract_fen(color_indicator, verify_attempt=0):
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


def get_current_fen(color_indicator):
    """Convenience helper to read current board FEN."""
    return capture_and_extract_fen(color_indicator, 0)
