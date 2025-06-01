import logging
import tkinter as tk
import time
from types import Tuple
from boardreader import get_positions, get_fen_from_position
from engine.capture_screenshot_in_memory import capture_screenshot_in_memory
from engine.get_best_move import get_best_move
from engine.is_castling_possible import is_castling_possible
from engine.update_fen_castling_rights import update_fen_castling_rights
from engine.execute_normal_move import execute_normal_move
from engine.store_board_positions import store_board_positions
from engine.get_current_fen import get_current_fen
from engine.verify_move import verify_move
from engine.move_piece import move_piece
from engine.processing_sync import processing_event

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def process_move(
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
    # If another move is already running, just return
    if processing_event.is_set():
        logger.warning("Move already being processed; aborting this call.")
        return

    # Mark “we are processing a move”
    processing_event.set()
    root.after(0, lambda: btn_play.config(state=tk.DISABLED))
    root.after(0, lambda: update_status("\nAnalyzing board..."))

    try:
        logger.info("Capturing screenshot")
        screenshot_image = capture_screenshot_in_memory(root, auto_mode_var)
        if not screenshot_image:
            logger.warning("Screenshot capture failed.")
            return

        boxes = get_positions(screenshot_image)
        if not boxes:
            logger.error("No chessboard found in screenshot.")
            root.after(0, lambda: update_status("\nNo board detected"))
            auto_mode_var.set(False)
            return

        try:
            chessboard_x, chessboard_y, square_size, fen = get_fen_from_position(
                color_indicator, boxes
            )
            logger.debug(f"FEN extracted: {fen}")
        except ValueError as e:
            logger.error(f"FEN extraction failed: {e}")
            root.after(0, lambda err=e: update_status(f"Error: {str(err)}"))
            auto_mode_var.set(False)
            return

        fen = update_fen_castling_rights(
            color_indicator,
            kingside_var,
            queenside_var,
            fen
        )
        logger.debug(f"FEN after castling update: {fen}")

        store_board_positions(board_positions, chessboard_x, chessboard_y, square_size)

        depth = root.depth_var.get() if hasattr(root, "depth_var") else 15
        logger.info(f"Asking engine for best move at depth {depth}")
        best_move, updated_fen, mate_flag = get_best_move(depth, fen, root, auto_mode_var)

        update_last_fen_for_color(updated_fen)

        if not best_move:
            logger.warning("No move returned by engine.")
            root.after(0, lambda: update_status("No valid move found!"))
            return

        logger.info(f"Best move suggested: {best_move}")

        def is_two_square_king_move(move_str: str, current_fen: str, color: str) -> Tuple[(bool, str)]:
            """
            Return (True, side) if `move_str` is a legal castling-style king move
            from current_fen for this color.  side is either 'kingside' or 'queenside'.
            Otherwise returns (False, "").
            """
            # move_str is always four characters, e.g. 'e8c8'.
            f_file, f_rank, t_file, t_rank = move_str[0], move_str[1], move_str[2], move_str[3]

            if f_rank != t_rank:
                return False, ""

            col_diff = abs(ord(f_file) - ord(t_file))
            if col_diff != 2:
                return False, ""

            placement = current_fen.split()[0]
            rows = placement.split("/")
            try:
                rank_idx = 8 - int(f_rank)  # rank '8' → index 0, rank '1' → index 7.
            except ValueError:
                return False, ""

            row_str = rows[rank_idx]
            expanded = []
            for ch in row_str:
                if ch.isdigit():
                    expanded += [""] * int(ch)
                else:
                    expanded.append(ch)

            file_idx = ord(f_file) - ord("a")
            if file_idx < 0 or file_idx > 7:
                return False, ""

            piece_at_source = expanded[file_idx]
            if color == "w" and piece_at_source != "K":
                return False, ""
            if color == "b" and piece_at_source != "k":
                return False, ""

            side_choice = "kingside" if (ord(t_file) > ord(f_file)) else "queenside"
            return True, side_choice

        is_castle_move, side = is_two_square_king_move(best_move, fen, color_indicator)
        if is_castle_move:
            logger.info(f"Castling move detected by pattern: {side} (move={best_move})")

            # Auto-enable the checkbox if it’s not already checked:
            if side == "kingside" and not kingside_var.get():
                logger.info("Auto-checking 'Kingside Castle' checkbox")
                kingside_var.set(True)
                root.after(0, lambda: update_status("Auto-enabled Kingside Castle"))
            elif side == "queenside" and not queenside_var.get():
                logger.info("Auto-checking 'Queenside Castle' checkbox")
                queenside_var.set(True)
                root.after(0, lambda: update_status("Auto-enabled Queenside Castle"))

            if is_castling_possible(fen, color_indicator, side):
                move_piece(color_indicator, best_move, board_positions, auto_mode_var, root, btn_play)
                status_msg = f"\nBest Move: {best_move}\nCastling move executed: {best_move}"
                if mate_flag:
                    status_msg += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
                    auto_mode_var.set(False)
                root.after(0, lambda: update_status(status_msg))
                time.sleep(0.3)

                success, _ = verify_move(color_indicator, best_move, updated_fen)
                if not success:
                    logger.error("Move verification failed after castling.")
                    root.after(0, lambda: update_status(
                        f"Move verification failed on checkmate move\nBest Move: {best_move}"
                    ))
                else:
                    fen_after = get_current_fen(color_indicator)
                    if fen_after:
                        last_fen_by_color[color_indicator] = fen_after.split()[0]
                    logger.info("Castling move verified and updated.")
            else:
                logger.warning("Castling not possible according to board state.")
        else:
            logger.info("Executing normal (non-castling) move.")
            success = execute_normal_move(
                board_positions,
                color_indicator,
                best_move,
                mate_flag,
                updated_fen,
                root,
                auto_mode_var,
                update_status,
                btn_play
            )
            if not success:
                logger.error("Normal move execution failed.")
                return

    except Exception as e:
        logger.exception("Unexpected error during process_move")
        root.after(0, lambda err=e: update_status(f"Error: {str(err)}"))
        auto_mode_var.set(False)

    finally:
        # Clear the Event so auto_move_loop knows we’re done
        processing_event.clear()
        if not auto_mode_var.get():
            root.after(0, lambda: btn_play.config(state=tk.NORMAL))
        logger.info("process_move completed.")
