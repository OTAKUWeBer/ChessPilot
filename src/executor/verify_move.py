import time
import logging
from board_detection import get_positions, get_fen_from_position
from executor import capture_screenshot_in_memory

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def verify_move(color_indicator, _, expected_fen, attempts_limit=3):
    """
    Verify that a move was executed successfully by checking the board state.
    Returns (success: bool, attempts_used: int)
    """
    expected_pieces = expected_fen.split()[0]
    logger.debug(f"Starting move verification for color {color_indicator} with expected pieces: {expected_pieces}")
    
    for attempt in range(1, attempts_limit + 1):
        if attempt > 1:
            time.sleep(0.5)
            logger.debug(f"Retrying verification attempt {attempt}/{attempts_limit}")
            
        screenshot = capture_screenshot_in_memory()
        if not screenshot:
            logger.warning(f"Attempt {attempt}: Screenshot capture failed")
            continue
        
        boxes = get_positions(screenshot)
        if not boxes:
            logger.warning(f"Attempt {attempt}: Board detection failed - no objects detected")
            continue
        
        chessboard_detected = any(box[5] == 12.0 for box in boxes)
        if not chessboard_detected:
            logger.warning(f"Attempt {attempt}: No chessboard detected (class_id 12.0 not found)")
            continue
        
        try:
            result = get_fen_from_position(color_indicator, boxes)
            if result is None:
                logger.warning(f"Attempt {attempt}: FEN extraction returned None")
                continue
                
            _, _, _, current_fen = result
            fen_parts = current_fen.split()
            logger.debug(f"Attempt {attempt}: Current FEN = {current_fen}")
            
            # Check if active color changed (move was made)
            if len(fen_parts) > 1 and fen_parts[1] != color_indicator:
                logger.info(f"Attempt {attempt}: Active color changed, move verified successfully")
                return True, attempt
            
            # Check if board position matches expected
            if fen_parts[0] == expected_pieces:
                logger.info(f"Attempt {attempt}: Board position matches expected pieces, move verified successfully")
                return True, attempt
                
        except (ValueError, TypeError) as e:
            logger.error(f"Attempt {attempt}: Error parsing FEN - {e}")
        except Exception as e:
            logger.error(f"Attempt {attempt}: Unexpected error - {e}")
    
    logger.error(f"Move verification failed after {attempts_limit} attempts")
    logger.error("This may indicate:")
    logger.error("  1. Board detection model not working properly")
    logger.error("  2. Screenshot not capturing the chess board")
    logger.error("  3. Board animation still in progress")
    return False, attempts_limit
