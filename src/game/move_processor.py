import logging
import time
import threading
from PyQt6.QtCore import QTimer
from board_detection import get_positions, get_fen_from_position
from utils.system_interaction import capture_screenshot_in_memory
from core.board_utils import capture_and_extract_fen, store_board_positions, fen_to_list, algebraic_to_index
from services.engine_service import EngineService
from core.fen_utils import is_castling_possible, update_fen_castling_rights, get_current_fen, is_two_square_king_move
from game.move_execution import MoveExecutor
from game.move_validator import MoveValidator
from core.config import AppConfig

logger = logging.getLogger(__name__)

processing_lock = threading.Lock()
processing_event = threading.Event()

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
    if not processing_lock.acquire(blocking=False):
        logger.warning("Move already being processed; aborting this call.")
        return
    
    processing_event.set()
    QTimer.singleShot(0, lambda: btn_play.setEnabled(False))
    QTimer.singleShot(0, lambda: update_status("\nAnalyzing board..."))
    
    try:
        board_data = _extract_board_position(root, auto_mode_var, color_indicator, update_status)
        if not board_data:
            return
        
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
    if processing_event.is_set():
        logger.warning("Move already being processed; aborting this call.")
        return False
    return True

def _initialize_move_processing(root, btn_play, update_status):
    processing_event.set()
    QTimer.singleShot(0, lambda: btn_play.setEnabled(False))
    QTimer.singleShot(0, lambda: update_status("\nAnalyzing board..."))

def _extract_board_position(root, auto_mode_var, color_indicator, update_status):
    max_retries = AppConfig.MAX_FEN_EXTRACTION_RETRIES
    
    for attempt in range(max_retries):
        screenshot_image = capture_screenshot_in_memory(root, auto_mode_var)
        
        if not screenshot_image:
            if attempt < max_retries - 1:
                time.sleep(AppConfig.FEN_RETRY_DELAY)
                continue
            return None
        
        boxes = get_positions(screenshot_image)
        if not boxes:
            if attempt < max_retries - 1:
                QTimer.singleShot(0, lambda: update_status(f"\nRetrying board detection ({attempt + 2}/{max_retries})…"))
                time.sleep(AppConfig.FEN_RETRY_DELAY)
                continue
            
            QTimer.singleShot(0, lambda: update_status("\nNo board detected after retries"))
            if callable(auto_mode_var):
                root.auto_mode_var = False
                if hasattr(root, 'auto_mode_check'):
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
        
        if attempt < max_retries - 1:
            time.sleep(AppConfig.FEN_RETRY_DELAY)
    
    return None

def _extract_fen_from_boxes(boxes, color_indicator, root, update_status, auto_mode_var, attempt, max_retries):
    try:
        result = get_fen_from_position(color_indicator, boxes)
        if result is None:
            if attempt < max_retries - 1:
                QTimer.singleShot(0, lambda: update_status(f"Retrying FEN extraction ({attempt + 2}/{max_retries})…"))
            else:
                QTimer.singleShot(0, lambda: update_status("Error: Could not detect board/FEN"))
                if callable(auto_mode_var):
                    root.auto_mode_var = False
                    if hasattr(root, 'auto_mode_check'):
                        root.auto_mode_check.setChecked(False)
            return None
        
        chessboard_x, chessboard_y, square_size, fen = result
        return {
            'chessboard_x': chessboard_x,
            'chessboard_y': chessboard_y,
            'square_size': square_size,
            'fen': fen
        }
    except Exception as e:
        if attempt >= max_retries - 1:
            QTimer.singleShot(0, lambda err=e: update_status(f"Error: {str(err)}"))
            if callable(auto_mode_var):
                root.auto_mode_var = False
                if hasattr(root, 'auto_mode_check'):
                    root.auto_mode_check.setChecked(False)
        return None

def _process_best_move(
    board_data, root, color_indicator, auto_mode_var, btn_play, move_mode,
    board_positions, update_status, kingside_var, queenside_var,
    update_last_fen_for_color, last_fen_by_color
):
    fen = _prepare_position_data(
        board_data, color_indicator, kingside_var, queenside_var, board_positions
    )
    
    move_data = _calculate_best_move(root, fen, auto_mode_var, update_status)
    if not move_data:
        return
    
    best_move, updated_fen, mate_flag = move_data
    update_last_fen_for_color(updated_fen)
    
    _execute_move(
        best_move, fen, updated_fen, mate_flag, color_indicator,
        board_positions, auto_mode_var, root, btn_play, move_mode, update_status,
        kingside_var, queenside_var, last_fen_by_color
    )

def _prepare_position_data(board_data, color_indicator, kingside_var, queenside_var, board_positions):
    fen = update_fen_castling_rights(
        color_indicator, kingside_var, queenside_var, board_data['fen']
    )
    store_board_positions(
        board_positions, 
        board_data['chessboard_x'], 
        board_data['chessboard_y'], 
        board_data['square_size']
    )
    return fen

def _calculate_best_move(root, fen, auto_mode_var, update_status):
    depth = root.depth_var if hasattr(root, "depth_var") else 15
    best_move, updated_fen, mate_flag = EngineService.get_best_move(depth, fen, root, auto_mode_var)
    
    if not best_move or best_move == "(none)":
        if best_move == "(none)":
            msg = "Game Over: Checkmate!" if mate_flag else "Game Over: Stalemate / No legal moves"
            QTimer.singleShot(0, lambda: update_status(f"\n{msg}"))
            _disable_auto_mode(auto_mode_var, root)
        else:
            QTimer.singleShot(0, lambda: update_status("No valid move found!"))
        return None
    return best_move, updated_fen, mate_flag

def _execute_move(
    best_move, fen, updated_fen, mate_flag, color_indicator,
    board_positions, auto_mode_var, root, btn_play, move_mode, update_status,
    kingside_var, queenside_var, last_fen_by_color
):
    is_castle_move, side = is_two_square_king_move(best_move, fen, color_indicator)
    
    if _should_execute_castling(is_castle_move, kingside_var, queenside_var):
        _execute_castling_move(
            best_move, side, fen, updated_fen, mate_flag, color_indicator,
            board_positions, auto_mode_var, root, btn_play, move_mode, update_status,
            kingside_var, queenside_var, last_fen_by_color
        )
    else:
        success = MoveExecutor.execute_normal_move(
            board_positions, color_indicator, best_move, mate_flag,
            updated_fen, root, auto_mode_var, update_status, btn_play, move_mode,
        )

def _should_execute_castling(is_castle_move, kingside_var, queenside_var):
    k_val = kingside_var() if callable(kingside_var) else kingside_var
    q_val = queenside_var() if callable(queenside_var) else queenside_var
    return is_castle_move and (k_val or q_val)

def _execute_castling_move(
    best_move, side, fen, updated_fen, mate_flag, color_indicator,
    board_positions, auto_mode_var, root, btn_play, move_mode, update_status,
    kingside_var, queenside_var, last_fen_by_color
):
    _auto_enable_castling_checkbox(side, kingside_var, queenside_var, root, update_status)
    if is_castling_possible(fen, color_indicator, side):
        _perform_castling_move(
            best_move, updated_fen, mate_flag, color_indicator,
            board_positions, auto_mode_var, root, btn_play, move_mode, update_status, last_fen_by_color
        )

def _auto_enable_castling_checkbox(side, kingside_var, queenside_var, root, update_status):
    k_val = kingside_var() if callable(kingside_var) else kingside_var
    q_val = queenside_var() if callable(queenside_var) else queenside_var

    if side == "kingside" and not k_val:
        root.kingside_check.setChecked(True)
        QTimer.singleShot(0, lambda: update_status("Auto-enabled Kingside Castle"))
    elif side == "queenside" and not q_val:
        root.queenside_check.setChecked(True)
        QTimer.singleShot(0, lambda: update_status("Auto-enabled Queenside Castle"))

def _perform_castling_move(
    best_move, updated_fen, mate_flag, color_indicator,
    board_positions, auto_mode_var, root, btn_play, move_mode, update_status, last_fen_by_color
):
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        original_fen = get_current_fen(color_indicator)
        if not original_fen:
            time.sleep(0.2)
            continue
        
        _execute_castling_pieces(
            best_move, color_indicator, board_positions,
            auto_mode_var, root, btn_play, move_mode
        )
        
        verification_result = _verify_castling_execution(
            color_indicator, original_fen, best_move
        )
        
        if verification_result['verified']:
            _handle_successful_castling(
                best_move, mate_flag, verification_result['current_fen'],
                update_status, auto_mode_var, root, last_fen_by_color, color_indicator
            )
            return True
        
        if AppConfig.SKIP_VERIFICATION_ON_FAILURE:
            _handle_unverified_castling(
                best_move, mate_flag, update_status, auto_mode_var, root
            )
            return True
    
    _handle_castling_failure(best_move, max_retries, update_status, auto_mode_var, root)
    return False

def _execute_castling_pieces(
    best_move, color_indicator, board_positions,
    auto_mode_var, root, btn_play, move_mode
):
    from_file, to_file = best_move[0], best_move[2]
    is_kingside = ord(to_file) > ord(from_file)
    
    if color_indicator == "w":
        rook_move = "h1f1" if is_kingside else "a1d1"
    else:
        rook_move = "h8f8" if is_kingside else "a8d8"
    
    MoveExecutor.move_piece(color_indicator, best_move, board_positions, auto_mode_var, root, btn_play, move_mode)
    time.sleep(0.25)

    # Check if the platform automatically moved the rook on king castling
    current_fen = capture_and_extract_fen(color_indicator, 0)
    rook_auto_castled = False
    if current_fen:
        rook_target = rook_move[2:4]
        target_idx = algebraic_to_index(rook_target)
        fen_list = fen_to_list(current_fen)
        expected_rook = 'R' if color_indicator == 'w' else 'r'
        if 0 <= target_idx < len(fen_list) and fen_list[target_idx] == expected_rook:
            rook_auto_castled = True
            logger.info(f"Platform auto-castled rook to {rook_target}; skipping manual rook move")

    if not rook_auto_castled:
        MoveExecutor.move_piece(color_indicator, rook_move, board_positions, auto_mode_var, root, btn_play, move_mode)
    delay = 0.4 if move_mode == "click" else 0.1
    time.sleep(delay)

def _verify_castling_execution(color_indicator, original_fen, king_move):
    max_verify_attempts = 2
    from_file, to_file = king_move[0], king_move[2]
    is_kingside = ord(to_file) > ord(from_file)
    
    if color_indicator == "w":
        rook_move = "h1f1" if is_kingside else "a1d1"
    else:
        rook_move = "h8f8" if is_kingside else "a8d8"
    
    for verify_attempt in range(max_verify_attempts):
        time.sleep(0.2)
        current_fen = capture_and_extract_fen(color_indicator, verify_attempt)
        if not current_fen:
            continue
        
        if MoveValidator.did_castling_move(color_indicator, original_fen, current_fen, king_move, rook_move):
            return {'verified': True, 'current_fen': current_fen}
    return {'verified': False, 'current_fen': None}

def _handle_successful_castling(move, mate_flag, current_fen, update_status, auto_mode_var, root, last_fen_by_color, color_indicator):
    status = f"Best Move: {move}\nMove Played: {move}"
    if mate_flag:
        status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
        _disable_auto_mode(auto_mode_var, root)
    if current_fen:
        last_fen_by_color[color_indicator] = current_fen.split()[0]
    update_status(status)

def _handle_unverified_castling(move, mate_flag, update_status, auto_mode_var, root):
    status = f"Best Move: {move}\nMove Played: {move} (unverified)"
    if mate_flag:
        status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
    update_status(status)
    _disable_auto_mode(auto_mode_var, root)

def _handle_castling_failure(move, max_retries, update_status, auto_mode_var, root):
    update_status(f"Move failed to register after {max_retries} attempts\nCheck board detection")
    _disable_auto_mode(auto_mode_var, root)

def _disable_auto_mode(auto_mode_var, root):
    try:
        if hasattr(auto_mode_var, "set") and callable(auto_mode_var.set):
            auto_mode_var.set(False)

        def _update_ui():
            if root is not None:
                if hasattr(root, "auto_mode_var"):
                    root.auto_mode_var = False
                if hasattr(root, "auto_mode_check") and root.auto_mode_check is not None:
                    root.auto_mode_check.setChecked(False)
                if hasattr(root, "btn_play") and root.btn_play is not None:
                    root.btn_play.setEnabled(True)

        QTimer.singleShot(0, _update_ui)
    except Exception as e:
        logger.error(f"Error disabling auto mode: {e}", exc_info=True)

def _handle_processing_error(error, root, update_status, auto_mode_var):
    logger.exception("Unexpected error during process_move")
    QTimer.singleShot(0, lambda err=error: update_status(f"Error: {str(err)}"))
    if callable(auto_mode_var):
        root.auto_mode_var = False
        if hasattr(root, "auto_mode_check"):
            root.auto_mode_check.setChecked(False)

def _finalize_move_processing(root, auto_mode_var, btn_play):
    processing_event.clear()
    if processing_lock.locked():
        try:
            processing_lock.release()
        except RuntimeError as err:
            logger.debug("Processing lock already released or not owned: %s", err)
    auto_val = auto_mode_var() if callable(auto_mode_var) else auto_mode_var
    if not auto_val:
        QTimer.singleShot(0, lambda: btn_play.setEnabled(True))
