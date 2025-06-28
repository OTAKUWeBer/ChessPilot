import time
import threading
import logging

from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from executor.process_move import process_move
from executor.processing_sync import processing_event

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def process_move_thread(
    root,
    color_indicator,
    auto_mode_var,
    btn_play,
    board_positions,
    update_status,
    kingside_var,
    queenside_var,
    update_last_fen_for_color,
    last_fen_by_color,
    screenshot_delay_var,
):
    """
    Starts a new daemon thread that will run process_move().
    """
    logger.info("Starting new thread to process move")
    threading.Thread(
        target=process_move,
        args=(
            root,
            color_indicator,
            auto_mode_var,
            btn_play,
            board_positions,
            update_status,
            kingside_var,
            queenside_var,
            update_last_fen_for_color,
            last_fen_by_color,
            screenshot_delay_var,
        ),
        daemon=True,
    ).start()


def auto_move_loop(
    root,
    color_indicator,
    auto_mode_var,
    btn_play,
    board_positions,
    last_fen_by_color,
    screenshot_delay_var,
    update_status_callback,
    kingside_var,
    queenside_var,
    update_last_fen_for_color
):
    """
    Continuously checks for the opponent's move and, once detected, spawns a
    process_move_thread to calculate and execute this player's next move.
    """

    logger.info("Auto move loop started")
    opp_color = 'b' if color_indicator == 'w' else 'w'
    logger.info(f"Player color: {color_indicator}, Opponent color: {opp_color}")

    # ─── Initial “seed” capture ───────────────────────────────────────────────
    try:
        logger.debug("Seeding last_fen_by_color with initial board position")
        seed_img = capture_screenshot_in_memory(root, auto_mode_var)
        if seed_img:
            boxes = get_positions(seed_img)
            if boxes:
                result = get_fen_from_position(color_indicator, boxes)
                if result is not None:
                    _, _, _, seed_fen = result
                    parts = seed_fen.split()
                    if len(parts) >= 2:
                        placement = parts[0]
                        last_fen_by_color['w'] = placement
                        last_fen_by_color['b'] = placement
                        logger.info(f"Seeded placement = {placement}")
                    else:
                        logger.warning("Seed FEN malformed; skipping initial seed")
            else:
                logger.warning("No board detected in seed capture")
        else:
            logger.warning("Seed capture returned None; skipping initial seed")
    except Exception as ex:
        logger.error(f"Exception during initial seed: {ex}", exc_info=True)

    # ─── Main loop ─────────────────────────────────────────────────────────────
    while auto_mode_var.get():
        logger.debug("Loop tick")

        if processing_event.is_set():
            logger.debug("Currently processing a move; sleeping 0.5s…")
            time.sleep(0.5)
            continue

        if not board_positions:
            logger.warning("Board positions not yet initialized; sleeping 0.5s…")
            time.sleep(0.5)
            continue

        try:
            logger.debug("Capturing screenshot for auto-move…")
            screenshot = capture_screenshot_in_memory(root, auto_mode_var)
            if not screenshot:
                logger.warning("Screenshot returned None; retrying in 0.02s…")
                time.sleep(0.02)
                continue

            boxes = get_positions(screenshot)
            if not boxes:
                logger.warning("Board detection failed; retrying in 0.2s…")
                time.sleep(0.2)
                continue

            _, _, _, current_fen = get_fen_from_position(color_indicator, boxes)
            logger.info(f"FEN extracted: {current_fen}")
            parts = current_fen.split()
            if len(parts) < 2:
                logger.warning("Malformed FEN; retrying in 0.2s…")
                time.sleep(0.2)
                continue

            placement, active = parts[0], parts[1]
            logger.debug(f"Placement: {placement}, Active side: {active}")

            if active == opp_color:
                old = last_fen_by_color.get(opp_color)
                if old is None or placement != old:
                    logger.info("Opponent moved; updating last_fen_by_color[opp_color].")
                    last_fen_by_color[opp_color] = placement
                else:
                    logger.debug("Opponent placement unchanged.")
                time.sleep(0.02)
                continue

            if active == color_indicator:
                if opp_color not in last_fen_by_color:
                    logger.debug(
                        "Our turn detected but no previous opponent-FEN known; sleeping 0.02s…"
                    )
                    time.sleep(0.02)
                    continue

                if placement == last_fen_by_color[opp_color]:
                    logger.debug(
                        "It's our turn but opponent didn’t move; sleeping 0.02s…"
                    )
                    time.sleep(0.02)
                    continue

                last_fen_by_color[opp_color] = placement
                logger.info("Detected genuine opponent move; launching our move.")

                delay = screenshot_delay_var.get()
                logger.debug(f"Sleeping for {delay}s before calculating move…")
                time.sleep(delay)

                process_move_thread(
                    root,
                    color_indicator,
                    auto_mode_var,
                    btn_play,
                    board_positions,
                    update_status_callback,
                    kingside_var,
                    queenside_var,
                    update_last_fen_for_color,
                    last_fen_by_color,
                    screenshot_delay_var
                )

                logger.debug(f"Sleeping again for {delay}s after launching move…")
                time.sleep(delay)

        except Exception as e:
            logger.error(f"Exception in auto_move_loop: {e}", exc_info=True)
            root.after(0, lambda err=e: update_status_callback(f"Error: {str(err)}"))
            auto_mode_var.set(False)
            break

    logger.info("Exiting auto_move_loop")
