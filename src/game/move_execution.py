import time
import logging
import os
import random
import pyautogui
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
from board_detection import get_positions, get_fen_from_position
from utils.system_interaction import capture_screenshot_in_memory, is_wayland, move_cursor_to_button
from core.fen_utils import get_current_fen
from core.notation import chess_notation_to_index
from game.move_validator import MoveValidator
from core.board_utils import capture_and_extract_fen
from core.config import AppConfig

from game.promotion import handle_pawn_promotion, is_pawn_promotion_move

if os.name == 'nt':
    import win32api
    import win32con

logger = logging.getLogger(__name__)

class MoveExecutionMethods:
    @staticmethod
    def drag_piece(start_pos, end_pos, humanize=True, offset_range=(-16, 16), root=None, auto_mode_var=None):
        start_x, start_y = start_pos
        end_x, end_y = end_pos

        if humanize and offset_range is not None:
            try:
                min_off, max_off = offset_range
                if min_off > max_off:
                    min_off, max_off = max_off, min_off
                start_x += random.uniform(min_off, max_off)
                start_y += random.uniform(min_off, max_off)
                end_x += random.uniform(min_off, max_off)
                end_y += random.uniform(min_off, max_off)
            except Exception as e:
                logger.warning(f"Failed to apply humanize offsets: {e}")

        try:
            if os.name == 'nt':
                win32api.SetCursorPos((int(round(start_x)), int(round(start_y))))
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                win32api.SetCursorPos((int(round(end_x)), int(round(end_y))))
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif is_wayland():
                from wayland_capture.wayland import WaylandInput
                client = WaylandInput()
                client.swipe(int(round(start_x)), int(round(start_y)),
                             int(round(end_x)), int(round(end_y)), 0.001)
            else:
                pyautogui.mouseDown(start_x, start_y)
                pyautogui.moveTo(end_x, end_y, duration=0.05)
                pyautogui.mouseUp(end_x, end_y)
            logger.info("Drag move simulated successfully")
        except Exception as e:
            logger.error(f"Failed to drag piece: {e}")
            if root and auto_mode_var:
                QTimer.singleShot(0, lambda err=e: QMessageBox.critical(root, "Error", f"Failed to drag piece: {str(err)}"))
                if callable(auto_mode_var):
                    root.auto_mode_var = False
                    root.auto_mode_check.setChecked(False)

    @staticmethod
    def click_piece(start_pos, end_pos, humanize=True, offset_range=(-16, 16), root=None, auto_mode_var=None):
        start_x, start_y = start_pos
        end_x, end_y = end_pos

        if humanize and offset_range is not None:
            try:
                min_off, max_off = offset_range
                if min_off > max_off:
                    min_off, max_off = max_off, min_off
                start_x += random.uniform(min_off, max_off)
                start_y += random.uniform(min_off, max_off)
                end_x += random.uniform(min_off, max_off)
                end_y += random.uniform(min_off, max_off)
            except Exception as e:
                logger.warning(f"Failed to apply humanize offsets: {e}")

        try:
            if os.name == 'nt':
                for x, y in [(start_x, start_y), (end_x, end_y)]:
                    win32api.SetCursorPos((int(round(x)), int(round(y))))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif is_wayland():
                from wayland_capture.wayland import WaylandInput
                client = WaylandInput()
                for x, y in [(start_x, start_y), (end_x, end_y)]:
                    client.click(int(round(x)), int(round(y)), button="left")
                    time.sleep(0.02)
            else:
                for x, y in [(start_x, start_y), (end_x, end_y)]:
                    pyautogui.click(x, y)
                    time.sleep(0.02)
            logger.info("Click move simulated successfully")
        except Exception as e:
            logger.error(f"Failed to click piece: {e}")
            if root and auto_mode_var:
                QTimer.singleShot(0, lambda err=e: QMessageBox.critical(root, "Error", f"Failed to click piece: {str(err)}"))
                if callable(auto_mode_var):
                    root.auto_mode_var = False
                    root.auto_mode_check.setChecked(False)

class MoveExecutor:
    @staticmethod
    def move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play, mode, humanize=True, offset_range=(-16, 16)):
        logger.debug(f"Moving piece: {move} in mode: {mode}")
        start_idx, end_idx = chess_notation_to_index(color_indicator, root, auto_mode_var, move)
        if not start_idx or not end_idx:
            return

        try:
            start_pos = board_positions[start_idx]
            end_pos = board_positions[end_idx]
        except KeyError:
            QTimer.singleShot(0, lambda: QMessageBox.critical(root, "Error", "Could not map move to board positions"))
            if callable(auto_mode_var):
                root.auto_mode_var = False
                root.auto_mode_check.setChecked(False)
            return

        if mode == "drag":
            MoveExecutionMethods.drag_piece(start_pos, end_pos, humanize, offset_range, root, auto_mode_var)
        elif mode == "click":
            MoveExecutionMethods.click_piece(start_pos, end_pos, humanize, offset_range, root, auto_mode_var)

        auto_val = auto_mode_var() if callable(auto_mode_var) else auto_mode_var
        if not auto_val:
            move_cursor_to_button(root, auto_mode_var, btn_play)

    @staticmethod
    def execute_move(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode):
        logger.debug(f"Executing move: {move}")
        MoveExecutor.move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode)
        time.sleep(0.1)

    @staticmethod
    def convert_move_to_indices(color_indicator, root, auto_mode_var, move):
        logger.debug(f"Converting move to indices: {move}")
        return chess_notation_to_index(color_indicator, root, auto_mode_var, move)

    @staticmethod
    def relocate_cursor_to_button(root, auto_mode_var, btn_play):
        logger.debug("Relocating cursor to Play button")
        move_cursor_to_button(root, auto_mode_var, btn_play)

    @staticmethod
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
        logger.info(f"Attempting move: {move} for {color_indicator}")
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            logger.debug(f"[Attempt {attempt}/{max_retries}] Starting move sequence")
            
            success, should_stop = MoveExecutor._attempt_single_move(
                board_positions, color_indicator, move, mate_flag,
                root, auto_mode_var, update_status, btn_play, move_mode
            )
            
            if success:
                return True
            
            if should_stop:
                break
            
            if attempt < max_retries:
                logger.warning(f"Move verification failed, retrying move...")

        MoveExecutor._handle_move_failure(move, max_retries, update_status, auto_mode_var, root)
        return False

    @staticmethod
    def _attempt_single_move(
        board_positions, color_indicator, move, mate_flag,
        root, auto_mode_var, update_status, btn_play, move_mode
    ):
        original_fen = get_current_fen(color_indicator)
        if not original_fen:
            logger.warning("Could not fetch original FEN, retrying...")
            time.sleep(0.2)
            return False, False
        
        move_positions = MoveExecutor._get_move_positions(board_positions, color_indicator, move, root, auto_mode_var)
        if not move_positions:
            time.sleep(0.2)
            return False, False
        
        MoveExecutor._execute_physical_move(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode)
        
        if is_pawn_promotion_move(move):
            logger.info(f"Detected pawn promotion move: {move}")
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
                            promotion_success = handle_pawn_promotion(
                                color_indicator, move, board_positions, chessboard_data,
                                auto_mode_var, root, move_mode, humanize=True, max_retries=2
                            )
                            if not promotion_success:
                                logger.warning("Pawn promotion handling may have failed")
            except Exception as e:
                logger.warning(f"Error in promotion handling: {e}")
        
        verified, current_fen = MoveExecutor._verify_move_execution(color_indicator, original_fen, move)
        
        if verified:
            MoveExecutor._handle_successful_move(move, mate_flag, current_fen, update_status, auto_mode_var, root)
            return True, False
        
        if AppConfig.SKIP_VERIFICATION_ON_FAILURE:
            MoveExecutor._handle_unverified_move(move, mate_flag, update_status, auto_mode_var, root)
            return True, True
        
        return False, False

    @staticmethod
    def _get_move_positions(board_positions, color_indicator, move, root, auto_mode_var):
        start_idx, end_idx = chess_notation_to_index(color_indicator, root, auto_mode_var, move)
        if start_idx is None or end_idx is None:
            return None
        try:
            start_pos = board_positions[start_idx]
            end_pos = board_positions[end_idx]
            return (start_idx, end_idx, start_pos, end_pos)
        except KeyError:
            return None

    @staticmethod
    def _execute_physical_move(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode):
        MoveExecutor.move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode)
        delay = 0.4 if move_mode == "click" else 0.1
        time.sleep(delay)

    @staticmethod
    def _verify_move_execution(color_indicator, original_fen, move):
        is_promotion = is_pawn_promotion_move(move)
        max_verify_attempts = 4 if is_promotion else 2
        extra_delay = 0.3 if is_promotion else 0.2
        
        for verify_attempt in range(max_verify_attempts):
            time.sleep(extra_delay)
            current_fen = capture_and_extract_fen(color_indicator, verify_attempt)
            if not current_fen:
                continue
            
            if MoveValidator.did_my_piece_move(color_indicator, original_fen, current_fen, move):
                logger.info(f"Move executed successfully: {move}")
                return True, current_fen
        
        return False, None

    @staticmethod
    def _handle_successful_move(move, mate_flag, current_fen, update_status, auto_mode_var, root):
        status = f"Best Move: {move}\nMove Played: {move}"
        if mate_flag:
            status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
            MoveExecutor._disable_auto_mode(auto_mode_var, root)
        update_status(status)

    @staticmethod
    def _handle_unverified_move(move, mate_flag, update_status, auto_mode_var, root):
        status = f"Best Move: {move}\nMove Played: {move} (unverified)"
        if mate_flag:
            status += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
        update_status(status)
        MoveExecutor._disable_auto_mode(auto_mode_var, root)

    @staticmethod
    def _handle_move_failure(move, max_retries, update_status, auto_mode_var, root):
        update_status(f"Move failed to register after {max_retries} attempts\nCheck board detection")
        MoveExecutor._disable_auto_mode(auto_mode_var, root)

    @staticmethod
    def _disable_auto_mode(auto_mode_var, root):
        try:
            if root is not None:
                if hasattr(root, "auto_mode_var"):
                    root.auto_mode_var = False
                if hasattr(root, "auto_mode_check"):
                    root.auto_mode_check.setChecked(False)
                if hasattr(root, "btn_play"):
                    root.btn_play.setEnabled(True)
            if hasattr(auto_mode_var, "set") and callable(auto_mode_var.set):
                auto_mode_var.set(False)
        except Exception as e:
            logger.error(f"Error disabling auto mode: {e}", exc_info=True)
