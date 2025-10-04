import time
import logging
from board_detection import get_positions, get_fen_from_position
from executor import capture_screenshot_in_memory

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def verify_move(color_indicator, _, expected_fen, attempts_limit=3):
    expected_pieces = expected_fen.split()[0]
    logger.debug(f"Starting move verification for color {color_indicator} with expected pieces: {expected_pieces}")
    
    for attempt in range(1, attempts_limit + 1):
        if attempt > 1:
            time.sleep(0.2)
            logger.debug(f"Retrying verification attempt {attempt}/{attempts_limit}")
            
        screenshot = capture_screenshot_in_memory()
        if not screenshot:
            logger.warning(f"Attempt {attempt}: Screenshot capture failed")
            continue
        
        boxes = get_positions(screenshot)
        if not boxes:
            logger.warning(f"Attempt {attempt}: Board detection failed")
            continue
        
        try:
            _, _, _, current_fen = get_fen_from_position(color_indicator, boxes)
            fen_parts = current_fen.split()
            logger.debug(f"Attempt {attempt}: Current FEN = {current_fen}")
            
            if len(fen_parts) > 1 and fen_parts[1] != color_indicator:
                last_fen = fen_parts[0]
                logger.info(f"Attempt {attempt}: Active color changed, move verified successfully")
                return True, attempt
            
            if fen_parts[0] == expected_pieces:
                last_fen = fen_parts[0]
                logger.info(f"Attempt {attempt}: Board position matches expected pieces, move verified successfully")
                return True, attempt
                
        except ValueError as e:
            logger.error(f"Attempt {attempt}: Error parsing FEN - {e}")
    
    logger.error(f"Move verification failed after {attempts_limit} attempts")
    return False, attempts_limit
