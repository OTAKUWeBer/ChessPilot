import pyautogui
import logging
from tkinter import messagebox
import os
import time
from .is_wayland import is_wayland
from wayland_capture.wayland import WaylandInput
import random
from executor.chess_notation_to_index import chess_notation_to_index
from executor.move_cursor_to_button import move_cursor_to_button

if os.name == 'nt':
    import win32api
    import win32con
    

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play,
               humanize=True, offset_range=(-16, 16)):
    logger.info(f"Attempting move: {move}")
    
    start_idx, end_idx = chess_notation_to_index(color_indicator, root, auto_mode_var, move)
    if not start_idx or not end_idx:
        logger.warning("Invalid notation to index mapping; move aborted")
        return

    try:
        start_pos = board_positions[start_idx]
        end_pos = board_positions[end_idx]
        logger.debug(f"Start: {start_idx} -> {start_pos}, End: {end_idx} -> {end_pos}")
    except KeyError:
        logger.error("Could not map move to board positions")
        root.after(0, lambda: messagebox.showerror("Error", "Could not map move to board positions"))
        auto_mode_var.set(False)
        return

    start_x, start_y = start_pos
    end_x, end_y = end_pos

    if humanize and offset_range is not None:
        try:
            min_off, max_off = offset_range
            # clamp sensible values if user passed reversed tuple
            if min_off > max_off:
                min_off, max_off = max_off, min_off
            sx_off = random.uniform(min_off, max_off)
            sy_off = random.uniform(min_off, max_off)
            ex_off = random.uniform(min_off, max_off)
            ey_off = random.uniform(min_off, max_off)

            start_x = float(start_x) + sx_off
            start_y = float(start_y) + sy_off
            end_x = float(end_x) + ex_off
            end_y = float(end_y) + ey_off

            logger.debug(f"Applied humanized offsets: start +({sx_off:.2f},{sy_off:.2f}), "
                         f"end +({ex_off:.2f},{ey_off:.2f})")
        except Exception as e:
            logger.warning(f"Failed to apply humanize offsets: {e}")

    try:
        if os.name == 'nt':
            logger.debug("Using win32api for Windows input (drag simulation)")
            win32api.SetCursorPos((int(start_x), int(start_y)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.SetCursorPos((int(end_x), int(end_y)))
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif is_wayland():
            logger.debug("Using Wayland input method")
            client = WaylandInput()
            client.swipe(int(start_x), int(start_y), int(end_x), int(end_y), 0.001)
        else:
            logger.debug("Using PyAutoGUI for input")
            pyautogui.mouseDown(start_x, start_y)
            pyautogui.moveTo(end_x, end_y)
            pyautogui.mouseUp(end_x, end_y)
        logger.info("Move simulated successfully")
    except Exception as e:
        logger.error(f"Failed to move piece: {e}")
        root.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to move piece: {str(err)}"))
        auto_mode_var.set(False)
        return

    if not auto_mode_var.get():
        logger.debug("Auto mode off after move; restoring cursor to Play button")
        root.after(0, lambda: move_cursor_to_button(root, auto_mode_var, btn_play))
