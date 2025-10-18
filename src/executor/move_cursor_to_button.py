import pyautogui
from wayland_capture.wayland import WaylandInput
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer, QRect
import logging
import os
from .is_wayland import is_wayland

if os.name == 'nt':
    import win32api

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def move_cursor_to_button(root, auto_mode_var, btn_play):
    logger.debug("Attempting to move cursor to Play Next Move button")

    try:
        # Check if button exists
        if btn_play is None:
            logger.error("btn_play is None")
            return

        logger.debug("Button object: %r", btn_play)

        # Try to log button text if available
        try:
            text = btn_play.text()
            logger.debug("Button text: %s", text)
        except Exception:
            logger.debug("Could not read button text (btn_play.text() raised)", exc_info=True)

        # Check if button is visible
        try:
            is_visible = btn_play.isVisible()
        except Exception:
            logger.warning("Could not determine visibility of btn_play; assuming not visible", exc_info=True)
            is_visible = False

        logger.debug("Button visible: %s", is_visible)

        if not is_visible:
            logger.warning("btn_play is not visible, skipping cursor move")
            return

        # Get current mouse position before moving
        try:
            current_pos = pyautogui.position()
            logger.debug("Current mouse position BEFORE move: %s", current_pos)
        except Exception:
            logger.warning("Could not get current mouse position", exc_info=True)

        # Get the button's rectangle in local coordinates
        try:
            button_rect: QRect = btn_play.rect()
            logger.debug(
                "Button rect (local coords): x=%s, y=%s, w=%s, h=%s",
                button_rect.x(), button_rect.y(), button_rect.width(), button_rect.height()
            )
        except Exception:
            logger.exception("Failed to get btn_play.rect()")
            raise

        # Map local top-left to global screen coordinates
        try:
            global_top_left = btn_play.mapToGlobal(button_rect.topLeft())
            logger.debug("Global top-left: x=%d, y=%d", global_top_left.x(), global_top_left.y())
        except Exception:
            logger.exception("Failed to map button top-left to global coordinates")
            raise

        # Calculate center point
        center_x = global_top_left.x() + (button_rect.width() // 2)
        center_y = global_top_left.y() + (button_rect.height() // 2)

        logger.debug("Button dimensions: %dx%d", button_rect.width(), button_rect.height())
        logger.debug(
            "CENTER CALCULATION: (%d + %d, %d + %d)",
            global_top_left.x(), button_rect.width() // 2, global_top_left.y(), button_rect.height() // 2
        )
        logger.debug("FINAL CENTER POSITION: (%d, %d)", center_x, center_y)

        # Verify the calculation makes sense
        if center_x < 0 or center_y < 0:
            logger.error("Invalid coordinates calculated: (%d, %d)", center_x, center_y)
            return

        # Move cursor based on platform
        if os.name == 'nt':
            try:
                win32api.SetCursorPos((int(center_x), int(center_y)))
                logger.debug("Cursor moved to (%d, %d) using win32api", center_x, center_y)
            except Exception:
                logger.exception("Failed to move cursor using win32api")
                raise
        elif is_wayland():
            try:
                client = WaylandInput()
                client.click(int(center_x), int(center_y))
                logger.debug("Cursor moved to (%d, %d) using Wayland", center_x, center_y)
            except Exception:
                logger.exception("Failed to move cursor using WaylandInput")
                raise
        else:
            try:
                pyautogui.moveTo(center_x, center_y, duration=0.1)
                logger.debug("Cursor moved to (%d, %d) using pyautogui", center_x, center_y)
            except Exception:
                logger.exception("Failed to move cursor using pyautogui")
                raise

    except Exception as e:
        logger.exception("Failed to relocate mouse cursor: %s", e)
        # Show a critical message box on the Qt main thread
        try:
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                root,
                "Error",
                f"Could not relocate the mouse to Play Next Move button\n{str(e)}"
            ))
        except Exception:
            logger.exception("Failed to schedule QMessageBox.critical with QTimer.singleShot")

        # Attempt to disable auto mode if provided
        try:
            if callable(auto_mode_var):
                # if auto_mode_var is callable, original code set root.auto_mode_var = False
                # preserve behavior but guard attributes
                try:
                    root.auto_mode_var = False
                except Exception:
                    logger.debug("Could not set root.auto_mode_var = False", exc_info=True)

                if hasattr(root, "auto_mode_check") and root.auto_mode_check is not None:
                    try:
                        root.auto_mode_check.setChecked(False)
                    except Exception:
                        logger.debug("Could not set root.auto_mode_check checked state", exc_info=True)
            else:
                # If auto_mode_var is not callable, try to set it directly if attribute exists
                try:
                    if hasattr(root, "auto_mode_var"):
                        root.auto_mode_var = False
                except Exception:
                    logger.debug("Could not set root.auto_mode_var directly", exc_info=True)

                if hasattr(root, "auto_mode_check") and root.auto_mode_check is not None:
                    try:
                        root.auto_mode_check.setChecked(False)
                    except Exception:
                        logger.debug("Could not set root.auto_mode_check checked state", exc_info=True)
        except Exception:
            logger.exception("Error while trying to disable auto mode after failure")
