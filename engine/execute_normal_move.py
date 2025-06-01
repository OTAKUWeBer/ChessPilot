import time
import logging
from boardreader import get_positions, get_fen_from_position
from engine.capture_screenshot_in_memory import capture_screenshot_in_memory
from engine.get_current_fen import get_current_fen
from engine.chess_notation_to_index import chess_notation_to_index
from engine.move_piece import move_piece
from engine.did_my_piece_move import did_my_piece_move

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def execute_normal_move(
    board_positions,
    color_indicator,
    move,
    mate_flag,
    expected_fen,
    root,
    auto_mode_var,
    update_status,
    btn_play
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
            end_pos   = board_positions[end_idx]
        except KeyError:
            logger.warning(f"Start or end position not found in board_positions: {start_idx}, {end_idx}")
            time.sleep(0.1)
            continue

        logger.debug(f"Dragging from {start_idx} to {end_idx}")
        move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play)
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
                auto_mode_var.set(False)
                logger.info("Checkmate detected. Auto mode disabled.")

            update_status(status)
            return True

    logger.error(f"Move {move} failed after {max_retries} attempts")
    update_status(f"Move failed to register after {max_retries} attempts")
    auto_mode_var.set(False)
    return False
