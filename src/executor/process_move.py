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
    Capture screenshot and extract board position data.
    Returns board data dict or None if failed.
    """
    logger.info("Capturing screenshot")
    screenshot_image = capture_screenshot_in_memory(root, auto_mode_var)
    
    if not screenshot_image:
        logger.warning("Screenshot capture failed.")
        return None
    
    boxes = get_positions(screenshot_image)
    if not boxes:
        logger.error("No chessboard found in screenshot.")
        QTimer.singleShot(0, lambda: update_status("\nNo board detected"))
        if callable(auto_mode_var):
            root.auto_mode_var = False
            root.auto_mode_check.setChecked(False)
        return None
    
    fen_data = _extract_fen_from_boxes(boxes, color_indicator, root, update_status, auto_mode_var)
    if not fen_data:
        return None
    
    return {
        'boxes': boxes,
        'chessboard_x': fen_data['chessboard_x'],
        'chessboard_y': fen_data['chessboard_y'],
        'square_size': fen_data['square_size'],
        'fen': fen_data['fen']
    }


def _extract_fen_from_boxes(boxes, color_indicator, root, update_status, auto_mode_var):
    """
    Extract FEN from detected board boxes with proper error handling.
    """
    try:
        result = get_fen_from_position(color_indicator, boxes)
        
        if result is None:
            logger.error("FEN extraction failed: get_fen_from_position returned None")
            QTimer.singleShot(0, lambda: update_status("Error: Could not detect board/FEN"))
            if callable(auto_mode_var):
                root.auto_mode_var = False
                root.auto_mode_check.setChecked(False)
            return None
        
        chessboard_x, chessboard_y, square_size, fen = result
        logger.debug(f"FEN extracted: {fen}")
        
        return {
            'chessboard_x': chessboard_x,
            'chessboard_y': chessboard_y,
            'square_size': square_size,
            'fen': fen
        }
        
    except IndexError:
        logger.error("FEN extraction failed: encountered unexpected box format (IndexError)")
        QTimer.singleShot(0, lambda: update_status("Error: Bad screenshot"))
        if callable(auto_mode_var):
            root.auto_mode_var = False
            root.auto_mode_check.setChecked(False)
        return None
        
    except ValueError as e:
        logger.error(f"FEN extraction failed: {e}")
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
            board_positions, auto_mode_var, root, btn_play, update_status, last_fen_by_color, move_mode,
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
    board_positions, auto_mode_var, root, btn_play,move_mode, update_status, last_fen_by_color
):
    """
    Perform the actual castling move and verify it.
    """
    move_piece(color_indicator, best_move, board_positions, auto_mode_var, root, btn_play, move_mode)
    
    status_msg = f"\nBest Move: {best_move}\nCastling move executed: {best_move}"
    if mate_flag:
        status_msg += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
        if callable(auto_mode_var):
            root.auto_mode_var = False
            root.auto_mode_check.setChecked(False)

    QTimer.singleShot(0, lambda: update_status(status_msg))
    time.sleep(0.3)
    
    _verify_castling_move(best_move, updated_fen, color_indicator, root, update_status, last_fen_by_color)


def _verify_castling_move(best_move, updated_fen, color_indicator, root, update_status, last_fen_by_color):
    """
    Verify that the castling move was executed correctly.
    """
    success, _ = verify_move(color_indicator, best_move, updated_fen)
    
    if not success:
        logger.error("Move verification failed after castling.")
        QTimer.singleShot(0, lambda: update_status(
            f"Move verification failed on castling move\nBest Move: {best_move}"
        ))
    else:
        fen_after = get_current_fen(color_indicator)
        if fen_after:
            last_fen_by_color[color_indicator] = fen_after.split()[0]
        logger.info("Castling move verified and updated.")


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