import pyautogui
import logging
import os
from tkinter import messagebox
from .is_wayland import is_wayland
from input_capture.wayland import WaylandInput
from engine.chess_notation_to_index import chess_notation_to_index
from engine.move_cursor_to_button import move_cursor_to_button
import time

if os.name == 'nt':
    import win32api
    import win32con

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play):
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

    try:
        if is_wayland():
            logger.debug("Using Wayland input method")
            client = WaylandInput()
            client.click(int(start_x), int(start_y))
            time.sleep(0.2)
            client.move(int(end_x), int(end_y))
        elif os.name == 'nt':
            logger.debug("Using win32api for Windows input")
            win32api.SetCursorPos((int(start_x), int(start_y)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            win32api.SetCursorPos((int(end_x), int(end_y)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
        else:
            logger.debug("Using PyAutoGUI for input")
            pyautogui.click(start_x, start_y)
            time.sleep(0.2)
            pyautogui.click(end_x, end_y)
        logger.info("Move simulated successfully")
    except Exception as e:
        logger.error(f"Failed to move piece: {e}")
        root.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to move piece: {str(err)}"))
        auto_mode_var.set(False)
        return

    if not auto_mode_var.get():
        logger.debug("Auto mode off after move; restoring cursor to Play button")
        root.after(0, lambda: move_cursor_to_button(root, auto_mode_var, btn_play))
