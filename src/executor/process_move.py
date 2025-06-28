import logging
import tkinter as tk
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
            result = get_fen_from_position(color_indicator, boxes)
            
            if result is None:
                logger.error("FEN extraction failed: get_fen_from_position returned None")
                root.after(0, lambda: update_status("Error: Could not detect board/FEN"))
                auto_mode_var.set(False)
                return

            chessboard_x, chessboard_y, square_size, fen = result
            logger.debug(f"FEN extracted: {fen}")
            
        except IndexError:
            # This usually means one of the 'box' entries was too short (e.g. wrong screenshot)
            logger.error("FEN extraction failed: encountered unexpected box format (IndexError)")
            root.after(0, lambda: update_status("Error: Bad screenshot"))
            auto_mode_var.set(False)
            return
        
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

        # Detect if the engine wants to castle:
        is_castle_move, side = is_two_square_king_move(best_move, fen, color_indicator)

        # If neither castling checkbox is checked, skip castling logic entirely:
        if is_castle_move and (kingside_var.get() or queenside_var.get()):
            logger.info(f"Castling move detected by pattern: {side} (move={best_move})")

            # Auto-enable the appropriate checkbox if it’s not already checked:
            if side == "kingside" and not kingside_var.get():
                logger.info("Auto-checking 'Kingside Castle' checkbox")
                kingside_var.set(True)
                root.after(0, lambda: update_status("Auto-enabled Kingside Castle"))
            elif side == "queenside" and not queenside_var.get():
                logger.info("Auto-checking 'Queenside Castle' checkbox")
                queenside_var.set(True)
                root.after(0, lambda: update_status("Auto-enabled Queenside Castle"))

            # Verify that castling is actually possible on the board:
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
                        f"Move verification failed on castling move\nBest Move: {best_move}"
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
