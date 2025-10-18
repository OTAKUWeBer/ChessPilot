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
    print("\n" + "="*60)
    print("DEBUG: move_cursor_to_button called")
    print("="*60)
    logger.debug("Attempting to move cursor to Play Next Move button")
    
    try:
        # Check if button exists
        if btn_play is None:
            print("ERROR: btn_play is None!")
            logger.error("btn_play is None")
            return
        
        print(f"Button object: {btn_play}")
        print(f"Button text: {btn_play.text()}")
        
        # Check if button is visible
        is_visible = btn_play.isVisible()
        print(f"Button visible: {is_visible}")
        logger.debug(f"Button visible: {is_visible}")
        
        if not is_visible:
            print("WARNING: btn_play is not visible, skipping cursor move")
            logger.warning("btn_play is not visible, skipping cursor move")
            return
        
        # Get current mouse position before moving
        try:
            current_pos = pyautogui.position()
            print(f"Current mouse position BEFORE move: {current_pos}")
        except:
            print("Could not get current mouse position")
        
        # Get the button's rectangle in global screen coordinates
        button_rect = btn_play.rect()
        print(f"Button rect (local coords): x={button_rect.x()}, y={button_rect.y()}, w={button_rect.width()}, h={button_rect.height()}")
        
        global_top_left = btn_play.mapToGlobal(button_rect.topLeft())
        print(f"Global top-left: x={global_top_left.x()}, y={global_top_left.y()}")
        
        # Calculate center point
        center_x = global_top_left.x() + (button_rect.width() // 2)
        center_y = global_top_left.y() + (button_rect.height() // 2)
        
        print(f"Button width: {button_rect.width()}, height: {button_rect.height()}")
        print(f"CENTER CALCULATION: ({global_top_left.x()} + {button_rect.width()//2}, {global_top_left.y()} + {button_rect.height()//2})")
        print(f"FINAL CENTER POSITION: ({center_x}, {center_y})")
        
        logger.debug(f"Button rect: {button_rect}")
        logger.debug(f"Global top-left: ({global_top_left.x()}, {global_top_left.y()})")
        logger.debug(f"Button dimensions: {button_rect.width()}x{button_rect.height()}")
        logger.debug(f"Calculated center: ({center_x}, {center_y})")
        
        # Verify the calculation makes sense
        if center_x < 0 or center_y < 0:
            logger.error(f"Invalid coordinates calculated: ({center_x}, {center_y})")
            return
        
        # Move cursor based on platform
        if os.name == 'nt':
            win32api.SetCursorPos((int(center_x), int(center_y)))
            logger.debug(f"Cursor moved to ({center_x}, {center_y}) using win32api")
        elif is_wayland():
            client = WaylandInput()
            client.move_cursor(int(center_x), int(center_y))
            logger.debug(f"Cursor moved to ({center_x}, {center_y}) using Wayland")
        else:
            pyautogui.moveTo(center_x, center_y, duration=0.1)
            logger.debug(f"Cursor moved to ({center_x}, {center_y}) using pyautogui")
            
    except Exception as e:
        logger.error(f"Failed to relocate mouse cursor: {e}", exc_info=True)
        QTimer.singleShot(0, lambda: QMessageBox.critical(
            root, 
            "Error", 
            f"Could not relocate the mouse to Play Next Move button\n{str(e)}"
        ))
        if callable(auto_mode_var):
            root.auto_mode_var = False
            root.auto_mode_check.setChecked(False)