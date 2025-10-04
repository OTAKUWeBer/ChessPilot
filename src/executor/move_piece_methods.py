import logging
import os
import time
import random
import pyautogui
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
from .is_wayland import is_wayland
from wayland_capture.wayland import WaylandInput

if os.name == 'nt':
    import win32api
    import win32con

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def drag_piece(start_pos, end_pos, humanize=True, offset_range=(-16, 16), root=None, auto_mode_var=None):
    """Simulate a drag from start_pos to end_pos"""
    start_x, start_y = start_pos
    end_x, end_y = end_pos

    # Humanize offsets
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


def click_piece(start_pos, end_pos, humanize=True, offset_range=(-16, 16), root=None, auto_mode_var=None):
    """Simulate a click on start_pos and end_pos"""
    start_x, start_y = start_pos
    end_x, end_y = end_pos

    # Humanize offsets
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
