import time
import logging
from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from executor.get_current_fen import get_current_fen
from executor.chess_notation_to_index import chess_notation_to_index
from executor.move_piece import move_piece
from executor.did_my_piece_move import did_my_piece_move
from core.config import AppConfig
from executor.pawn_promotion import handle_pawn_promotion, is_pawn_promotion_move

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
    Execute a chess move with retry logic and verification.
    Attempts up to 3 times to successfully execute and verify the move.
    """
    logger.info(f"Attempting move: {move} for {color_indicator}")
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        logger.debug(f"[Attempt {attempt}/{max_retries}] Starting move sequence")
        
        move_result = _attempt_single_move(
            board_positions,
            color_indicator,
            move,
            mate_flag,
            root,
            auto_mode_var,
            update_status,
            btn_play,
            move_mode,
        )
        
        if move_result.success:
            return True
        
        if move_result.should_stop_retrying:
            break
        
        if attempt < max_retries:
            logger.warning(f"Move verification failed, retrying move execution...")

    # All attempts failed
    _handle_move_failure(move, max_retries, update_status, auto_mode_var, root)
    return False


class MoveResult:
    """Result of a move attempt."""
    def __init__(self, success=False, should_stop_retrying=False):
        self.success = success
        self.should_stop_retrying = should_stop_retrying


def _attempt_single_move(
    board_positions,
    color_indicator,
    move,
    mate_flag,
    root,
    auto_mode_var,
    update_status,
    btn_play,
    move_mode,
):
    """Attempt to execute and verify a single move."""
    
    # Get board state before move
    original_fen = get_current_fen(color_indicator)
    if not original_fen:
        logger.warning("Could not fetch original FEN, retrying...")
        time.sleep(0.2)
        return MoveResult()
    
    # Validate and get move positions
    move_positions = _get_move_positions(
        board_positions, color_indicator, move, root, auto_mode_var
    )
    if not move_positions:
        time.sleep(0.2)
        return MoveResult()
    
    # Execute the physical move
    _execute_physical_move(
        color_indicator, move, board_positions, 
        auto_mode_var, root, btn_play, move_mode
    )
    
    if is_pawn_promotion_move(move):
        logger.info(f"Detected pawn promotion move: {move}")
        # Capture current board state to pass to promotion handler
        try:
            img = capture_screenshot_in_memory()
            boxes = get_positions(img) if img else None
            if boxes:
                chessboard_boxes = [box for box in boxes if box[5] == 12.0]
                if chessboard_boxes:
                    result = get_fen_from_position(color_indicator, boxes)
                    if result:
                        chessboard_x, chessboard_y, square_size, fen = result
                        chessboard_data = {
                            'chessboard_x': chessboard_x,
                            'chessboard_y': chessboard_y,
                            'square_size': square_size,
                            'fen': fen
                        }
                        # Handle promotion piece selection
                        promotion_success = handle_pawn_promotion(
                            color_indicator, move, board_positions, chessboard_data,
                            auto_mode_var, root, move_mode, humanize=True, max_retries=2
                        )
                        if not promotion_success:
                            logger.warning("Pawn promotion handling may have failed")
        except Exception as e:
            logger.warning(f"Error in promotion handling: {e}")
    
    # Verify the move was successful
    verification_result = _verify_move_execution(
        color_indicator, original_fen, move
    )
    
    if verification_result.verified:
        _handle_successful_move(
            move, mate_flag, verification_result.current_fen,
            update_status, auto_mode_var, root
        )
        return MoveResult(success=True)
    
    # Handle unverified move with skip flag
    if AppConfig.SKIP_VERIFICATION_ON_FAILURE:
        _handle_unverified_move(
            move, mate_flag, update_status, auto_mode_var, root
        )
        return MoveResult(success=True, should_stop_retrying=True)
    
    return MoveResult()


def _get_move_positions(board_positions, color_indicator, move, root, auto_mode_var):
    """Get and validate start and end positions for the move."""
    start_idx, end_idx = chess_notation_to_index(
        color_indicator, root, auto_mode_var, move
    )
    
    if start_idx is None or end_idx is None:
        logger.warning("Invalid move indices")
        return None
    
    try:
        start_pos = board_positions[start_idx]
        end_pos = board_positions[end_idx]
        logger.debug(f"Dragging from {start_idx} to {end_idx}")
        return (start_idx, end_idx, start_pos, end_pos)
    except KeyError:
        logger.warning(f"Position not found: {start_idx}, {end_idx}")
        return None


def _execute_physical_move(
    color_indicator, move, board_positions,
    auto_mode_var, root, btn_play, move_mode
):
    """Execute the physical move on the board."""
    move_piece(
        color_indicator, move, board_positions,
        auto_mode_var, root, btn_play, move_mode
    )
    
    # Wait for move animation to complete
    delay = 0.4 if move_mode == "click" else 0.1
    time.sleep(delay)


class VerificationResult:
    """Result of move verification."""
    def __init__(self, verified=False, current_fen=None):
        self.verified = verified
        self.current_fen = current_fen


def _verify_move_execution(color_indicator, original_fen, move):
    """Verify that the move was successfully executed."""
    is_promotion = is_pawn_promotion_move(move)
    max_verify_attempts = 4 if is_promotion else 2
    extra_delay = 0.3 if is_promotion else 0.2
    
    for verify_attempt in range(max_verify_attempts):
        time.sleep(extra_delay)  # Extra delay for promotion moves
        
        current_fen = _capture_and_extract_fen(color_indicator, verify_attempt)
        if not current_fen:
            continue
        
        logger.debug(f"Checking if move registered: {move}")
        if did_my_piece_move(color_indicator, original_fen, current_fen, move):
            logger.info(f"Move executed successfully: {move}")
            return VerificationResult(verified=True, current_fen=current_fen)
        
        logger.debug(f"Move not yet registered on attempt {verify_attempt + 1}")
    
    return VerificationResult(verified=False)


def _capture_and_extract_fen(color_indicator, verify_attempt):
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


def _handle_successful_move(move, mate_flag, current_fen, update_status, auto_mode_var, root):
    """Handle a successfully verified move."""
    status = f"Best Move: {move}\nMove Played: {move}"
    
    if mate_flag:
        status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
        _disable_auto_mode(auto_mode_var, root)
        logger.info("Checkmate detected. Auto mode disabled.")
    
    update_status(status)


def _handle_unverified_move(move, mate_flag, update_status, auto_mode_var, root):
    """Handle move when verification fails but skip flag is enabled."""
    logger.warning(f"Move verification failed but SKIP_VERIFICATION_ON_FAILURE is enabled")
    logger.info(f"Assuming move {move} was executed successfully")
    
    status = f"Best Move: {move}\nMove Played: {move} (unverified)"
    
    if mate_flag:
        status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
    
    update_status(status)
    _disable_auto_mode(auto_mode_var, root)
    logger.info("Auto mode disabled due to unverified move")


def _handle_move_failure(move, max_retries, update_status, auto_mode_var, root):
    """Handle complete move failure after all retries."""
    logger.error(f"Move {move} failed after {max_retries} attempts")
    update_status(
        f"Move failed to register after {max_retries} attempts\n"
        f"Check board detection settings"
    )
    _disable_auto_mode(auto_mode_var, root)
    logger.info("Auto mode disabled due to move failure")
