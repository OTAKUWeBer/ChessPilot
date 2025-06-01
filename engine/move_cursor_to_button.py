from .is_wayland import is_wayland
import pyautogui
from input_capture.wayland import WaylandInput
from tkinter import messagebox
import logging
import os

if os.name == 'nt':
    import win32api
    import win32con

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def move_cursor_to_button(root, auto_mode_var, btn_play):
    try:
        x = btn_play.winfo_rootx()
        y = btn_play.winfo_rooty()
        width = btn_play.winfo_width()
        height = btn_play.winfo_height()
        center_x = x + (width // 2)
        center_y = y + (height // 2)
        if is_wayland():
            client = WaylandInput()
            client.click(int(center_x), int(center_y))        
        elif os.name == 'nt':
            import win32api
            import win32con
            win32api.SetCursorPos((int(center_x), int(center_y)))
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 0)
        else:
            pyautogui.moveTo(center_x, center_y, duration=0.1)
    except Exception as e:
        logger.error(f"Failed to relocate mouse cursor: {e}", exc_info=True)
        root.after(0, lambda err=e: messagebox.showerror(f"Error", f"Could not relocate the mouse\n{str(err)}"))
        auto_mode_var.set(False)