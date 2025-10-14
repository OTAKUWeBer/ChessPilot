import time
import logging
from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from executor.get_current_fen import get_current_fen
from executor.chess_notation_to_index import chess_notation_to_index
from executor.move_piece import move_piece
from executor.did_my_piece_move import did_my_piece_move
from core.config import AppConfig

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def _disable_auto_mode(auto_mode_var, root):
    """
    Disable auto mode by:
    1. Setting the auto_mode_var to False
    2. Unchecking the auto_mode_check checkbox
    3. Re-enabling the play button
    """
    try:
        if root is not None:
            # Set the variable
            if hasattr(root, "auto_mode_var"):
                root.auto_mode_var = False
                logger.info("Set auto_mode_var to False")
            
            # Uncheck the checkbox (this is the key fix)
            if hasattr(root, "auto_mode_check"):
                root.auto_mode_check.setChecked(False)
                logger.info("Unchecked auto_mode_check checkbox")
            
            # Re-enable the play button
            if hasattr(root, "btn_play"):
                root.btn_play.setEnabled(True)
                logger.info("Re-enabled play button")
        
        # Also try to set via the auto_mode_var parameter if it has a set method
        if hasattr(auto_mode_var, "set") and callable(auto_mode_var.set):
            auto_mode_var.set(False)
            
    except Exception as e:
        logger.error(f"Error disabling auto mode: {e}", exc_info=True)

def execute_normal_move(
    board_positions,
    color_indicator,
    move,
    mate_flag,
    expected_fen,
    root,
    auto_mode_var,
    update_status,
    btn_play,
    move_mode,
):
    """
    Try up to 3 times to drag your piece; only succeed if
    did_my_piece_move(before_fen, current_fen, move) is True.
    """

    logger.info(f"Attempting move: {move} for {color_indicator}")
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        logger.debug(f"[Attempt {attempt}/{max_retries}] Starting move sequence")

        original_fen = get_current_fen(color_indicator)
        if not original_fen:
            logger.warning("Could not fetch original FEN, retrying...")
            time.sleep(0.2)
            continue

        start_idx, end_idx = chess_notation_to_index(
            color_indicator,
            root,
            auto_mode_var,
            move
        )
        if start_idx is None or end_idx is None:
            logger.warning("Invalid move indices, retrying...")
            time.sleep(0.2)
            continue

        try:
            start_pos = board_positions[start_idx]
            end_pos = board_positions[end_idx]
        except KeyError:
            logger.warning(f"Start or end position not found in board_positions: {start_idx}, {end_idx}")
            time.sleep(0.2)
            continue

        logger.debug(f"Dragging from {start_idx} to {end_idx}")
        move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode)
        
        if move_mode == "click":
            time.sleep(0.6)  # Longer delay for click mode to allow animation
        else:
            time.sleep(0.3)  # Increased delay for drag mode

        verification_success = False
        for verify_attempt in range(2):  # Try verification twice
            time.sleep(0.2)  # Small delay before verification
            
            img = capture_screenshot_in_memory()
            if not img:
                logger.warning(f"Screenshot failed on verification attempt {verify_attempt + 1}")
                continue

            boxes = get_positions(img)
            if not boxes:
                logger.warning(f"Board detection failed on verification attempt {verify_attempt + 1}")
                continue
            
            chessboard_detected = any(box[5] == 12.0 for box in boxes)
            if not chessboard_detected:
                logger.warning(f"No chessboard detected on verification attempt {verify_attempt + 1}")
                continue

            try:
                result = get_fen_from_position(color_indicator, boxes)
                if result is None:
                    logger.warning(f"FEN extraction returned None on verification attempt {verify_attempt + 1}")
                    continue
                    
                _, _, _, current_fen = result
            except (ValueError, TypeError) as e:
                logger.warning(f"FEN extraction error on verification attempt {verify_attempt + 1}: {e}")
                continue

            logger.debug(f"Checking if move registered: {move}")
            if did_my_piece_move(color_indicator, original_fen, current_fen, move):
                verification_success = True
                last_fen = current_fen.split()[0]
                status = f"Best Move: {move}\nMove Played: {move}"
                logger.info(f"Move executed successfully: {move}")

                if mate_flag:
                    status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
                    _disable_auto_mode(auto_mode_var, root)
                    logger.info("Checkmate detected. Auto mode disabled.")

                update_status(status)
                return True
            else:
                logger.debug(f"Move not yet registered on verification attempt {verify_attempt + 1}")
        
        if not verification_success and AppConfig.SKIP_VERIFICATION_ON_FAILURE:
            logger.warning(f"Move verification failed but SKIP_VERIFICATION_ON_FAILURE is enabled")
            logger.info(f"Assuming move {move} was executed successfully")
            status = f"Best Move: {move}\nMove Played: {move} (unverified)"
            
            if mate_flag:
                status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
                _disable_auto_mode(auto_mode_var, root)
                logger.info("Checkmate detected. Auto mode disabled.")
            
            update_status(status)
            _disable_auto_mode(auto_mode_var, root)
            logger.info("Auto mode disabled due to unverified move")
            return True
        
        # If we get here, verification failed and we should retry
        if attempt < max_retries:
            logger.warning(f"Move verification failed, retrying move execution...")

    logger.error(f"Move {move} failed after {max_retries} attempts")
    update_status(f"Move failed to register after {max_retries} attempts\nCheck board detection settings")
    _disable_auto_mode(auto_mode_var, root)
    logger.info("Auto mode disabled due to move failure")
    return False
