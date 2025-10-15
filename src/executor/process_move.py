import logging
from PyQt6.QtCore import QTimer
import time
from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from executor.get_best_move import get_best_move
from executor.is_castling_possible import is_castling_possible
from executor.update_fen_castling_rights import update_fen_castling_rights
from executor.execute_normal_move import execute_normal_move
from executor.store_board_positions import store_board_positions
from executor.get_current_fen import get_current_fen
from executor.verify_move import verify_move
from executor.move_piece import move_piece
from executor.is_two_square_king_move import is_two_square_king_move
from executor.processing_sync import processing_event
from core.config import AppConfig
from executor.did_castling_move import did_castling_move 

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def process_move(
    root,
    color_indicator,
    auto_mode_var,
    btn_play,
    move_mode,
    board_positions,
    update_status,
    kingside_var,
    queenside_var,
    update_last_fen_for_color,
    last_fen_by_color,
    screenshot_delay_var,
):
    """
    Main function to process a chess move.
    Complexity reduced by delegating to specialized functions.
    """
    # Check if already processing
    if not _can_start_processing():
        return
    
    # Initialize processing state
    _initialize_move_processing(root, btn_play, update_status)
    
    try:
        # Extract board position
        board_data = _extract_board_position(root, auto_mode_var, color_indicator, update_status)
        if not board_data:
            return
        
        # Get and execute the best move
        _process_best_move(
            board_data, root, color_indicator, auto_mode_var, btn_play, move_mode,
            board_positions, update_status, kingside_var, queenside_var,
            update_last_fen_for_color, last_fen_by_color
        )
        
    except Exception as e:
        _handle_processing_error(e, root, update_status, auto_mode_var)
    finally:
        _finalize_move_processing(root, auto_mode_var, btn_play)


def _can_start_processing():
    """
    Check if we can start processing a new move.
    """
    if processing_event.is_set():
        logger.warning("Move already being processed; aborting this call.")
        return False
    return True


def _initialize_move_processing(root, btn_play, update_status):
    """
    Set up the initial state for move processing.
    """
    processing_event.set()
    QTimer.singleShot(0, lambda: btn_play.setEnabled(False))
    QTimer.singleShot(0, lambda: update_status("\nAnalyzing board..."))


def _extract_board_position(root, auto_mode_var, color_indicator, update_status):
    """
    Capture screenshot and extract board position data with retry logic.
    Returns board data dict or None if failed.
    """
    max_retries = AppConfig.MAX_FEN_EXTRACTION_RETRIES
    
    for attempt in range(max_retries):
        logger.info(f"Capturing screenshot (attempt {attempt + 1}/{max_retries})")
        screenshot_image = capture_screenshot_in_memory(root, auto_mode_var)
        
        if not screenshot_image:
            logger.warning(f"Screenshot capture failed on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(AppConfig.FEN_RETRY_DELAY)
                continue
            return None
        
        boxes = get_positions(screenshot_image)
        if not boxes:
            logger.error(f"No chessboard found in screenshot (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                QTimer.singleShot(0, lambda: update_status(f"\nRetrying board detection ({attempt + 2}/{max_retries})…"))
                time.sleep(AppConfig.FEN_RETRY_DELAY)
                continue
            
            QTimer.singleShot(0, lambda: update_status("\nNo board detected after retries"))
            if callable(auto_mode_var):
                root.auto_mode_var = False
                root.auto_mode_check.setChecked(False)
            return None
        
        fen_data = _extract_fen_from_boxes(boxes, color_indicator, root, update_status, auto_mode_var, attempt, max_retries)
        if fen_data:
            return {
                'boxes': boxes,
                'chessboard_x': fen_data['chessboard_x'],
                'chessboard_y': fen_data['chessboard_y'],
                'square_size': fen_data['square_size'],
                'fen': fen_data['fen']
            }
        
        # If FEN extraction failed and we have retries left
        if attempt < max_retries - 1:
            logger.warning(f"FEN extraction failed, retrying in {AppConfig.FEN_RETRY_DELAY}s…")
            time.sleep(AppConfig.FEN_RETRY_DELAY)
    
    logger.error(f"Failed to extract board position after {max_retries} attempts")
    return None

def _extract_fen_from_boxes(boxes, color_indicator, root, update_status, auto_mode_var, attempt, max_retries):
    """
    Extract FEN from detected board boxes with proper error handling.
    """
    try:
        result = get_fen_from_position(color_indicator, boxes)
        
        if result is None:
            logger.error(f"FEN extraction failed: get_fen_from_position returned None (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                QTimer.singleShot(0, lambda: update_status(f"Retrying FEN extraction ({attempt + 2}/{max_retries})…"))
            else:
                QTimer.singleShot(0, lambda: update_status("Error: Could not detect board/FEN"))
                if callable(auto_mode_var):
                    root.auto_mode_var = False
                    root.auto_mode_check.setChecked(False)
            return None
        
        chessboard_x, chessboard_y, square_size, fen = result
        logger.debug(f"FEN extracted successfully: {fen}")
        
        return {
            'chessboard_x': chessboard_x,
            'chessboard_y': chessboard_y,
            'square_size': square_size,
            'fen': fen
        }
        
    except IndexError as e:
        logger.error(f"FEN extraction failed: unexpected box format (attempt {attempt + 1}): {e}")
        if attempt >= max_retries - 1:
            QTimer.singleShot(0, lambda: update_status("Error: Bad screenshot"))
            if callable(auto_mode_var):
                root.auto_mode_var = False
                root.auto_mode_check.setChecked(False)
        return None
        
    except ValueError as e:
        logger.error(f"FEN extraction failed (attempt {attempt + 1}): {e}")
        if attempt >= max_retries - 1:
            QTimer.singleShot(0, lambda err=e: update_status(f"Error: {str(err)}"))
            if callable(auto_mode_var):
                root.auto_mode_var = False
                root.auto_mode_check.setChecked(False)
        return None
    except Exception as e:
        logger.error(f"Unexpected error during FEN extraction (attempt {attempt + 1}): {e}", exc_info=True)
        if attempt >= max_retries - 1:
            QTimer.singleShot(0, lambda err=e: update_status(f"Error: {str(err)}"))
            if callable(auto_mode_var):
                root.auto_mode_var = False
                root.auto_mode_check.setChecked(False)
        return None


def _process_best_move(
    board_data, root, color_indicator, auto_mode_var, btn_play, move_mode,
    board_positions, update_status, kingside_var, queenside_var,
    update_last_fen_for_color, last_fen_by_color
):
    """
    Calculate and execute the best move for the current position.
    """
    # Update FEN with castling rights and store board positions
    fen = _prepare_position_data(
        board_data, color_indicator, kingside_var, queenside_var, board_positions
    )
    
    # Get best move from engine
    move_data = _calculate_best_move(root, fen, auto_mode_var, update_status)
    if not move_data:
        return
    
    best_move, updated_fen, mate_flag = move_data
    update_last_fen_for_color(updated_fen)
    
    # Execute the move (castling or normal)
    _execute_move(
        best_move, fen, updated_fen, mate_flag, color_indicator,
        board_positions, auto_mode_var, root, btn_play, move_mode, update_status,
        kingside_var, queenside_var, last_fen_by_color
    )


def _prepare_position_data(board_data, color_indicator, kingside_var, queenside_var, board_positions):
    """
    Update FEN with castling rights and store board position data.
    """
    fen = update_fen_castling_rights(
        color_indicator, kingside_var, queenside_var, board_data['fen']
    )
    logger.debug(f"FEN after castling update: {fen}")
    
    store_board_positions(
        board_positions, 
        board_data['chessboard_x'], 
        board_data['chessboard_y'], 
        board_data['square_size']
    )
    
    return fen


def _calculate_best_move(root, fen, auto_mode_var, update_status):
    """
    Get the best move from the chess engine.
    """
    depth = root.depth_var if hasattr(root, "depth_var") else 15
    logger.info(f"Asking engine for best move at depth {depth}")
    
    best_move, updated_fen, mate_flag = get_best_move(depth, fen, root, auto_mode_var)
    
    if not best_move:
        logger.warning("No move returned by engine.")
        QTimer.singleShot(0, lambda: update_status("No valid move found!"))
        return None
    
    logger.info(f"Best move suggested: {best_move}")
    return best_move, updated_fen, mate_flag


def _execute_move(
    best_move, fen, updated_fen, mate_flag, color_indicator,
    board_positions, auto_mode_var, root, btn_play, move_mode, update_status,
    kingside_var, queenside_var, last_fen_by_color
):
    """
    Execute either a castling move or normal move based on detection.
    """
    is_castle_move, side = is_two_square_king_move(best_move, fen, color_indicator)
    
    if _should_execute_castling(is_castle_move, kingside_var, queenside_var):
        _execute_castling_move(
            best_move, side, fen, updated_fen, mate_flag, color_indicator,
            board_positions, auto_mode_var, root, btn_play, move_mode, update_status,
            kingside_var, queenside_var, last_fen_by_color
        )
    else:
        logger.info("Executing normal (non-castling) move.")
        success = execute_normal_move(
            board_positions, color_indicator, best_move, mate_flag,
            updated_fen, root, auto_mode_var, update_status, btn_play, move_mode,
        )
        if not success:
            logger.error("Normal move execution failed.")


def _should_execute_castling(is_castle_move, kingside_var, queenside_var):
    """
    Determine if we should execute castling logic.
    """
    k_val = kingside_var() if callable(kingside_var) else kingside_var
    q_val = queenside_var() if callable(queenside_var) else queenside_var
    return is_castle_move and (k_val or q_val)


def _execute_castling_move(
    best_move, side, fen, updated_fen, mate_flag, color_indicator,
    board_positions, auto_mode_var, root, btn_play, move_mode, update_status,
    kingside_var, queenside_var, last_fen_by_color
):
    """
    Execute a castling move with all necessary checks and updates.
    """
    logger.info(f"Castling move detected by pattern: {side} (move={best_move})")
    
    # Auto-enable castling checkbox if needed
    _auto_enable_castling_checkbox(side, kingside_var, queenside_var, root, update_status)
    
    # Verify and execute castling
    if is_castling_possible(fen, color_indicator, side):
        _perform_castling_move(
            best_move, updated_fen, mate_flag, color_indicator,
            board_positions, auto_mode_var, root, btn_play, move_mode, update_status, last_fen_by_color
        )
    else:
        logger.warning("Castling not possible according to board state.")


def _auto_enable_castling_checkbox(side, kingside_var, queenside_var, root, update_status):
    """
    Automatically enable the appropriate castling checkbox if not already checked.
    """
    k_val = kingside_var() if callable(kingside_var) else kingside_var
    q_val = queenside_var() if callable(queenside_var) else queenside_var

    if side == "kingside" and not k_val:
        logger.info("Auto-checking 'Kingside Castle' checkbox")
        root.kingside_check.setChecked(True)
        QTimer.singleShot(0, lambda: update_status("Auto-enabled Kingside Castle"))
    elif side == "queenside" and not q_val:
        logger.info("Auto-checking 'Queenside Castle' checkbox")
        root.queenside_check.setChecked(True)
        QTimer.singleShot(0, lambda: update_status("Auto-enabled Queenside Castle"))


def _perform_castling_move(
    best_move, updated_fen, mate_flag, color_indicator,
    board_positions, auto_mode_var, root, btn_play, move_mode, update_status, last_fen_by_color
):
    """
    Perform the actual castling move with retry logic and verification.
    """
    logger.info(f"Attempting castling move: {best_move} for {color_indicator}")
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        logger.debug(f"[Castling Attempt {attempt}/{max_retries}] Starting move sequence")
        
        # Get board state before move
        original_fen = get_current_fen(color_indicator)
        if not original_fen:
            logger.warning("Could not fetch original FEN, retrying...")
            time.sleep(0.2)
            continue
        
        # Execute the castling move (king + rook)
        _execute_castling_pieces(
            best_move, color_indicator, board_positions,
            auto_mode_var, root, btn_play, move_mode
        )
        
        # Verify the move was successful
        verification_result = _verify_castling_execution(
            color_indicator, original_fen, best_move
        )
        
        if verification_result['verified']:
            _handle_successful_castling(
                best_move, mate_flag, verification_result['current_fen'],
                update_status, auto_mode_var, root, last_fen_by_color, color_indicator
            )
            return True
        
        # Handle unverified move with skip flag
        if AppConfig.SKIP_VERIFICATION_ON_FAILURE:
            _handle_unverified_castling(
                best_move, mate_flag, update_status, auto_mode_var, root
            )
            return True
        
        if attempt < max_retries:
            logger.warning(f"Castling verification failed, retrying move execution...")

    # All attempts failed
    _handle_castling_failure(best_move, max_retries, update_status, auto_mode_var, root)
    return False


def _execute_castling_pieces(
    best_move, color_indicator, board_positions,
    auto_mode_var, root, btn_play, move_mode
):
    """
    Execute both king and rook moves for castling.
    """
    # Determine castling side from the king's move
    from_file, to_file = best_move[0], best_move[2]
    is_kingside = ord(to_file) > ord(from_file)
    
    # Calculate rook move based on castling side and color
    if color_indicator == "w":
        rook_move = "h1f1" if is_kingside else "a1d1"
    else:  # black
        rook_move = "h8f8" if is_kingside else "a8d8"
    
    logger.info(f"Executing castling: King move {best_move}, Rook move {rook_move}")
    
    # Move the king first
    move_piece(color_indicator, best_move, board_positions, auto_mode_var, root, btn_play, move_mode)
    time.sleep(0.2)  # Small delay between king and rook moves
    
    # Move the rook
    move_piece(color_indicator, rook_move, board_positions, auto_mode_var, root, btn_play, move_mode)
    
    # Wait for move animation to complete
    delay = 0.4 if move_mode == "click" else 0.1
    time.sleep(delay)


def _verify_castling_execution(color_indicator, original_fen, king_move):
    """
    Verify that the castling move was successfully executed.
    """
    max_verify_attempts = 2
    
    from_file, to_file = king_move[0], king_move[2]
    is_kingside = ord(to_file) > ord(from_file)
    
    if color_indicator == "w":
        rook_move = "h1f1" if is_kingside else "a1d1"
    else:  # black
        rook_move = "h8f8" if is_kingside else "a8d8"
    
    for verify_attempt in range(max_verify_attempts):
        time.sleep(0.2)  # Delay before verification
        
        current_fen = _capture_and_extract_fen(color_indicator, verify_attempt)
        if not current_fen:
            continue
        
        logger.debug(f"Checking if castling move registered: King {king_move}, Rook {rook_move}")
        if did_castling_move(color_indicator, original_fen, current_fen, king_move, rook_move):
            logger.info(f"Castling move executed successfully: King {king_move}, Rook {rook_move}")
            return {'verified': True, 'current_fen': current_fen}
        
        logger.debug(f"Castling move not yet registered on attempt {verify_attempt + 1}")
    
    return {'verified': False, 'current_fen': None}


def _capture_and_extract_fen(color_indicator, verify_attempt):
    """
    Capture screenshot and extract FEN from current board state.
    Used by both normal moves and castling moves.
    """
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


def _handle_successful_castling(move, mate_flag, current_fen, update_status, auto_mode_var, root, last_fen_by_color, color_indicator):
    """
    Handle a successfully verified castling move.
    """
    status = f"Best Move: {move}\nMove Played: {move}"
    
    if mate_flag:
        status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
        _disable_auto_mode(auto_mode_var, root)
        logger.info("Checkmate detected. Auto mode disabled.")
    
    # Update last FEN
    if current_fen:
        last_fen_by_color[color_indicator] = current_fen.split()[0]
    
    update_status(status)
    logger.info("Castling move verified and updated.")


def _handle_unverified_castling(move, mate_flag, update_status, auto_mode_var, root):
    """
    Handle castling when verification fails but skip flag is enabled.
    """
    logger.warning(f"Castling verification failed but SKIP_VERIFICATION_ON_FAILURE is enabled")
    logger.info(f"Assuming castling move {move} was executed successfully")
    
    status = f"Best Move: {move}\nMove Played: {move} (unverified)"
    
    if mate_flag:
        status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
    
    update_status(status)
    _disable_auto_mode(auto_mode_var, root)
    logger.info("Auto mode disabled due to unverified castling move")


def _handle_castling_failure(move, max_retries, update_status, auto_mode_var, root):
    """
    Handle complete castling failure after all retries.
    """
    logger.error(f"Castling move {move} failed after {max_retries} attempts")
    update_status(
        f"Move failed to register after {max_retries} attempts\n"
        f"Check board detection settings"
    )
    _disable_auto_mode(auto_mode_var, root)
    logger.info("Auto mode disabled due to castling failure")


def _disable_auto_mode(auto_mode_var, root):
    """
    Disable auto mode by setting the variable and unchecking the checkbox.
    Matches the pattern used in execute_normal_move.py
    """
    try:
        if root is not None:
            # Set the variable
            if hasattr(root, "auto_mode_var"):
                root.auto_mode_var = False
                logger.info("Set auto_mode_var to False")
            
            # Uncheck the checkbox
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

def _handle_processing_error(error, root, update_status, auto_mode_var):
    """
    Handle unexpected errors during move processing.
    """
    logger.exception("Unexpected error during process_move")
    QTimer.singleShot(0, lambda err=error: update_status(f"Error: {str(err)}"))
    if callable(auto_mode_var):
        root.auto_mode_var = False
        root.auto_mode_check.setChecked(False)


def _finalize_move_processing(root, auto_mode_var, btn_play):
    """
    Clean up after move processing is complete.
    """
    processing_event.clear()
    auto_val = auto_mode_var() if callable(auto_mode_var) else auto_mode_var
    if not auto_val:
        QTimer.singleShot(0, lambda: btn_play.setEnabled(True))
    logger.info("process_move completed.")
