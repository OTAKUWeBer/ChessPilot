"""
PyQt6 graphical interface components, dialogs, and shortcuts for ChessPilot.
"""

from .create_widget import create_widgets
from .button_and_checkboxes import (
    color_button,
    action_button,
    shortcuts_button,
    castling_checkboxes,
    move_mode,
    set_window_icon,
)
from .shortcuts import bind_shortcuts
from .shortcuts_dialog import show_shortcuts_dialog
from .download_dialog import StockfishDownloaderApp

__all__ = [
    'create_widgets',
    'color_button',
    'action_button',
    'shortcuts_button',
    'castling_checkboxes',
    'move_mode',
    'set_window_icon',
    'bind_shortcuts',
    'show_shortcuts_dialog',
    'StockfishDownloaderApp',
]
