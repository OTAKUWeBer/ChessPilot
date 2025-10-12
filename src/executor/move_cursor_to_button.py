import pyautogui
from wayland_capture.wayland import WaylandInput
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
import logging
import os
from .is_wayland import is_wayland

if os.name == 'nt':
    import win32api

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def move_cursor_to_button(root, auto_mode_var, btn_play):
    try:
        geometry = btn_play.geometry()
        pos = btn_play.mapToGlobal(geometry.topLeft())
        x = pos.x()
        y = pos.y()
        width = geometry.width()
        height = geometry.height()
        center_x = x + (width // 2)
        center_y = y + (height // 2)
        if os.name == 'nt':
            win32api.SetCursorPos((int(center_x), int(center_y)))
        elif is_wayland():
            client = WaylandInput()
            client.click(int(center_x), int(center_y))
        else:
            pyautogui.moveTo(center_x, center_y, duration=0.1)
    except Exception as e:
        logger.error(f"Failed to relocate mouse cursor: {e}", exc_info=True)
        QTimer.singleShot(0, lambda: QMessageBox.critical(root, "Error", f"Could not relocate the mouse\n{str(e)}"))
        if callable(auto_mode_var):
            root.auto_mode_var = False
            root.auto_mode_check.setChecked(False)