import os
import logging
from typing import Optional, Tuple
from PyQt6.QtCore import QTimer, QRect, QPoint
from PyQt6.QtWidgets import QMessageBox, QPushButton
import pyautogui

logger = logging.getLogger(__name__)


class CursorMoveError(Exception):
    """Exception raised when cursor movement fails."""
    pass


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
    """Calculate global screen coordinates for button center.
    
    Raises:
        CursorMoveError: If coordinates cannot be calculated.
    """
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
        logger.debug("Global top-left: x=%d, y=%d", 
                    global_top_left.x(), global_top_left.y())
    except Exception as e:
        raise CursorMoveError(f"Failed to map to global coordinates: {e}")
    
    center_x = global_top_left.x() + (button_rect.width() // 2)
    center_y = global_top_left.y() + (button_rect.height() // 2)
    
    logger.debug("Calculated center: (%d, %d)", center_x, center_y)
    
    if center_x < 0 or center_y < 0:
        raise CursorMoveError(f"Invalid coordinates: ({center_x}, {center_y})")
    
    return center_x, center_y


def move_cursor_platform_specific(x: int, y: int) -> None:
    """Move cursor using platform-specific method.
    
    Raises:
        CursorMoveError: If cursor movement fails.
    """
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
            root.auto_mode_check.setChecked(False)
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
    """Move cursor to the Play Next Move button.
    
    Args:
        root: The main window/root widget
        auto_mode_var: Auto mode variable (unused, kept for compatibility)
        btn_play: The button to move cursor to
    """
    logger.debug("Attempting to move cursor to Play Next Move button")
    
    try:
        # Validate button
        btn_info = get_button_info(btn_play)
        
        if not btn_info["exists"]:
            logger.error("btn_play is None")
            return
        
        logger.debug("Button info: %s", btn_info)
        
        if not btn_info["visible"]:
            logger.warning("btn_play is not visible, skipping cursor move")
            return
        
        # Log current position
        try:
            current_pos = pyautogui.position()
            logger.debug("Current mouse position: %s", current_pos)
        except Exception:
            logger.warning("Could not get current mouse position", exc_info=True)
        
        # Calculate target position and move cursor
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


def is_wayland() -> bool:
    """Check if running on Wayland (placeholder - implement based on your system)."""
    return False