import pyautogui
import logging
from tkinter import messagebox
import os
import time
from .is_wayland import is_wayland
from wayland_capture.wayland import WaylandInput
from executor.chess_notation_to_index import chess_notation_to_index
from executor.move_cursor_to_button import move_cursor_to_button

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
        if os.name == 'nt':
            logger.debug("Using win32api for Windows input (click-click approach)")
            
            # Step 1: Click on the window to focus it
            win32api.SetCursorPos((int(start_x), int(start_y)))
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.05)
            
            # Step 2: Click on the chess piece to select it
            win32api.SetCursorPos((int(start_x), int(start_y)))
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.05)
            
            # Step 3: Click on the destination square to move the piece
            win32api.SetCursorPos((int(end_x), int(end_y)))
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            
        elif is_wayland():
            logger.debug("Using Wayland input method (click-click approach)")
            client = WaylandInput()
            # Click on piece to select it
            client.click(int(start_x), int(start_y))
            time.sleep(0.05)
            # Click on destination to move it
            client.click(int(end_x), int(end_y))
        else:
            logger.debug("Using PyAutoGUI for input (click-click approach)")
            # Click on piece to select it
            pyautogui.click(start_x, start_y)
            time.sleep(0.05)
            # Click on destination to move it
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
