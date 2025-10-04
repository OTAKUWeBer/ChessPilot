# ...existing code...
import time
import logging
from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from executor.get_current_fen import get_current_fen
from executor.chess_notation_to_index import chess_notation_to_index
from executor.move_piece import move_piece
from executor.did_my_piece_move import did_my_piece_move

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def _disable_auto_mode(auto_mode_var, root):
    """
    Try to disable auto mode given different possible representations:
      - object with .set(False)
      - a callable (like lambda: root.auto_mode_var) -> fallback to setting root.auto_mode_var
      - object with 'value' attribute
      - direct attribute on root
    """
    try:
        # If object exposes .set(), use it
        set_fn = getattr(auto_mode_var, "set", None)
        if callable(set_fn):
            set_fn(False)
            return
    except Exception:
        pass

    # If it's a callable (e.g. lambda returning current value), try to set attribute on root
    try:
        if callable(auto_mode_var):
            if root is not None and hasattr(root, "auto_mode_var"):
                try:
                    setattr(root, "auto_mode_var", False)
                    return
                except Exception:
                    pass
    except Exception:
        pass

    # If it has a 'value' attribute, try to set that
    try:
        if hasattr(auto_mode_var, "value"):
            try:
                setattr(auto_mode_var, "value", False)
                return
            except Exception:
                pass
    except Exception:
        pass

    # Final fallback: set attribute on root if available
    if root is not None and hasattr(root, "auto_mode_var"):
        try:
            setattr(root, "auto_mode_var", False)
            return
        except Exception:
            pass

    logger.warning("Unable to disable auto_mode_var via known methods")

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
            time.sleep(0.1)
            continue

        start_idx, end_idx = chess_notation_to_index(
            color_indicator,
            root,
            auto_mode_var,
            move
        )
        if start_idx is None or end_idx is None:
            logger.warning("Invalid move indices, retrying...")
            time.sleep(0.1)
            continue

        try:
            start_pos = board_positions[start_idx]
            end_pos = board_positions[end_idx]
        except KeyError:
            logger.warning(f"Start or end position not found in board_positions: {start_idx}, {end_idx}")
            time.sleep(0.1)
            continue

        logger.debug(f"Dragging from {start_idx} to {end_idx}")
        move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode)
        time.sleep(0.1)

        img = capture_screenshot_in_memory()
        if not img:
            logger.warning("Screenshot failed, retrying...")
            continue

        boxes = get_positions(img)
        if not boxes:
            logger.warning("Board detection failed, retrying...")
            continue

        try:
            _, _, _, current_fen = get_fen_from_position(color_indicator, boxes)
        except ValueError as e:
            logger.warning(f"FEN extraction error: {e}, retrying...")
            continue

        logger.debug(f"Checking if move registered: {move}")
        if did_my_piece_move(color_indicator, original_fen, current_fen, move):
            last_fen = current_fen.split()[0]
            status = f"Best Move: {move}\nMove Played: {move}"
            logger.info(f"Move executed successfully: {move}")

            if mate_flag:
                status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
                _disable_auto_mode(auto_mode_var, root)
                logger.info("Checkmate detected. Auto mode disabled.")

            update_status(status)
            return True

    logger.error(f"Move {move} failed after {max_retries} attempts")
    update_status(f"Move failed to register after {max_retries} attempts")
    _disable_auto_mode(auto_mode_var, root)
    return False
# ...existing code...