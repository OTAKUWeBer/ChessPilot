import os
import io
import mss
import logging
import subprocess
from PIL import Image
from typing import Optional, Tuple
from PyQt6.QtCore import QTimer, QRect, QPoint
from PyQt6.QtWidgets import QMessageBox, QPushButton
import pyautogui
from utils.get_binary_path import get_binary_path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CursorMoveError(Exception):
    """Exception raised when cursor movement fails."""
    pass


def is_wayland() -> bool:
    """Check if running on Wayland."""
    return os.getenv("XDG_SESSION_TYPE") == "wayland"


def capture_screenshot_in_memory(root=None, auto_mode_var=None):
    grim_path = get_binary_path("grim") if is_wayland() else None
    try:
        if is_wayland():
            logger.debug("Capturing screenshot using grim (Wayland)...")
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            result = subprocess.run([grim_path, "-"], stdout=subprocess.PIPE, check=True, creationflags=creation_flags)
            image = Image.open(io.BytesIO(result.stdout))
        else:
            logger.debug("Capturing screenshot using mss (non-Wayland)...")
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                image = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        logger.debug("Screenshot captured successfully")
        return image
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        if root:
            QTimer.singleShot(0, lambda: QMessageBox.critical(root, "Error", f"Screenshot failed: {str(e)}"))
        if auto_mode_var and callable(auto_mode_var):
            def _turn_off():
                if root:
                    if hasattr(root, "auto_mode_var"):
                        root.auto_mode_var = False
                    if hasattr(root, "auto_mode_check") and root.auto_mode_check is not None:
                        root.auto_mode_check.setChecked(False)
            QTimer.singleShot(0, _turn_off)
        return None


def get_button_info(btn_play: QPushButton) -> dict:
    """Extract button information for logging."""
    info = {"exists": btn_play is not None}
    
    if not info["exists"]:
        return info
    
    try:
        info["text"] = btn_play.text()
    except Exception:
        info["text"] = "unknown"
        logger.debug("Could not read button text", exc_info=True)
    
    try:
        info["visible"] = btn_play.isVisible()
    except Exception:
        info["visible"] = False
        logger.warning("Could not determine visibility", exc_info=True)
    
    return info


def calculate_button_center(btn_play: QPushButton) -> Tuple[int, int]:
    """Calculate global screen coordinates for button center."""
    try:
        button_rect: QRect = btn_play.rect()
        logger.debug(
            "Button rect: x=%s, y=%s, w=%s, h=%s",
            button_rect.x(), button_rect.y(), 
            button_rect.width(), button_rect.height()
        )
    except Exception as e:
        raise CursorMoveError(f"Failed to get button rectangle: {e}")
    
    try:
        global_top_left: QPoint = btn_play.mapToGlobal(button_rect.topLeft())
        logger.debug("Global top-left: x=%d, y=%d", global_top_left.x(), global_top_left.y())
    except Exception as e:
        raise CursorMoveError(f"Failed to map to global coordinates: {e}")
    
    center_x = global_top_left.x() + (button_rect.width() // 2)
    center_y = global_top_left.y() + (button_rect.height() // 2)
    
    logger.debug("Calculated center: (%d, %d)", center_x, center_y)
    
    if center_x < 0 or center_y < 0:
        raise CursorMoveError(f"Invalid coordinates: ({center_x}, {center_y})")
    
    return center_x, center_y


def move_cursor_platform_specific(x: int, y: int) -> None:
    """Move cursor using platform-specific method."""
    if os.name == 'nt':
        try:
            import win32api
            win32api.SetCursorPos((int(x), int(y)))
            logger.debug("Cursor moved using win32api")
        except Exception as e:
            raise CursorMoveError(f"win32api failed: {e}")
    
    elif is_wayland():
        try:
            from wayland_capture import WaylandInput
            client = WaylandInput()
            client.click(int(x), int(y))
            logger.debug("Cursor moved using Wayland")
        except Exception as e:
            raise CursorMoveError(f"WaylandInput failed: {e}")
    
    else:
        try:
            pyautogui.moveTo(x, y, duration=0.1)
            logger.debug("Cursor moved using pyautogui")
        except Exception as e:
            raise CursorMoveError(f"pyautogui failed: {e}")


def disable_auto_mode(root) -> None:
    """Disable auto mode after error."""
    try:
        if hasattr(root, "auto_mode_var"):
            root.auto_mode_var = False
            logger.debug("Disabled auto_mode_var")
    except Exception:
        logger.debug("Could not disable auto_mode_var", exc_info=True)
    
    try:
        if hasattr(root, "auto_mode_check") and root.auto_mode_check is not None:
            QTimer.singleShot(0, lambda: root.auto_mode_check.setChecked(False))
            logger.debug("Unchecked auto_mode_check")
    except Exception:
        logger.debug("Could not uncheck auto_mode_check", exc_info=True)


def show_error_message(root, error_msg: str) -> None:
    """Display error message on Qt main thread."""
    try:
        QTimer.singleShot(0, lambda: QMessageBox.critical(
            root, "Error", 
            f"Could not relocate the mouse to Play Next Move button\n{error_msg}"
        ))
    except Exception:
        logger.exception("Failed to show error message")


def move_cursor_to_button(root, auto_mode_var, btn_play: Optional[QPushButton]) -> None:
    """Move cursor to the Play Next Move button."""
    logger.debug("Attempting to move cursor to Play Next Move button")
    
    try:
        btn_info = get_button_info(btn_play)
        
        if not btn_info["exists"]:
            logger.error("btn_play is None")
            return
        
        logger.debug("Button info: %s", btn_info)
        
        if not btn_info["visible"]:
            logger.warning("btn_play is not visible, skipping cursor move")
            return
        
        try:
            current_pos = pyautogui.position()
            logger.debug("Current mouse position: %s", current_pos)
        except Exception:
            logger.warning("Could not get current mouse position", exc_info=True)
        
        center_x, center_y = calculate_button_center(btn_play)
        move_cursor_platform_specific(center_x, center_y)
        
        logger.debug("Successfully moved cursor to (%d, %d)", center_x, center_y)
        
    except CursorMoveError as e:
        logger.error("Cursor movement failed: %s", e)
        show_error_message(root, str(e))
        disable_auto_mode(root)
        
    except Exception as e:
        logger.exception("Unexpected error in move_cursor_to_button: %s", e)
        show_error_message(root, str(e))
        disable_auto_mode(root)
