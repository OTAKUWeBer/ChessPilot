import threading
import sys
import logging
from pathlib import Path
import os
import multiprocessing

# Must be at the very top for PyInstaller on Windows
if __name__ == "__main__":
    # Hide console window on Windows when frozen and register app model ID for taskbar icon
    if sys.platform == 'win32':
        import ctypes
        try:
            # -4 = DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError) as err:
            logging.getLogger(__name__).debug("Per-monitor V2 DPI awareness could not be set: %s", err)
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('otakuweber.chesspilot.2.3.0')
        except (AttributeError, OSError) as err:
            logging.getLogger(__name__).debug("AppUserModelID could not be set: %s", err)
        if getattr(sys, 'frozen', False):
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 
                0  # SW_HIDE
            )
    multiprocessing.freeze_support()

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import Qt

from utils.logging_setup import setup_logging, get_log_file_path
from utils.chess_resources_manager import setup_resources
from utils.system_info import log_system_info, log_dependency_status
from core.config import AppConfig

setup_logging()
logger = logging.getLogger(__name__)

script_dir = Path(__file__).resolve().parent
project_dir = script_dir.parent

os.chdir(script_dir)

logger.info("=" * 60)
logger.info("ChessPilot starting...")
logger.info(f"Version: {AppConfig.VERSION}")
logger.info(f"Log file: {get_log_file_path()}")
logger.info("=" * 60)

log_system_info()
log_dependency_status()

if not setup_resources(script_dir, project_dir):
    logger.error("Resource setup failed")
    # Show error dialog before exiting
    app = QApplication(sys.argv)
    QMessageBox.critical(
        None,
        "Setup Failed",
        "Failed to setup required resources (Stockfish or ONNX model).\n\n"
        "If you are offline, you can manually place 'stockfish' (or 'stockfish.exe') "
        "and 'chess_detection.onnx' in the ChessPilot folder.\n\n"
        f"Log file location:\n{get_log_file_path()}"
    )
    sys.exit(1)

from core import GameState, AppConfig
from game import AutoPlayController, process_move
from services import EngineService

from gui.create_widget import create_widgets
from gui.shortcuts import bind_shortcuts
from gui.button_and_checkboxes import (
    color_button,
    action_button,
    castling_checkboxes,
    move_mode,
    shortcuts_button,
    set_window_icon,
)

class ChessPilot(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing ChessPilot application")

        self.setWindowTitle(AppConfig.WINDOW_TITLE)

        # Scale window size to occupy a similar screen fraction across
        # resolutions.  The 380×520 default was designed for 1920×1080
        # (common on Windows with no extra scaling).  On higher-res
        # displays without OS scaling (typical on Linux), the window
        # appears physically too small, so we scale it up.
        scale = 1.0
        try:
            qapp = QApplication.instance()
            if qapp is not None:
                screen = qapp.primaryScreen()
                if screen is not None:
                    ratio = screen.devicePixelRatio()
                    if not ratio or ratio <= 0:
                        ratio = 1.0
                    avail = screen.availableSize()
                    logical_h = avail.height() / ratio
                    # Reference: 1080 logical pixels (1920×1080 at 100%).
                    # Use sqrt to dampen the growth so the window doesn't
                    # become overly large on high-res screens.
                    raw = logical_h / 1080.0
                    scale = max(raw ** 0.5, 1.0)
                    logger.debug(
                        f"Screen: {avail.width()}x{avail.height()}, "
                        f"pixelRatio: {ratio}, scale factor: {scale:.2f}"
                    )
        except Exception as e:
            logger.debug("Failed to calculate screen resolution scale factor: %s", e)
            scale = 1.0

        self.resize(int(AppConfig.WINDOW_WIDTH * scale),
                    int(AppConfig.WINDOW_HEIGHT * scale))
        self.setMinimumSize(int(360 * scale), int(480 * scale))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self.game_state = GameState()
        self.engine_service = EngineService()

        self.color_indicator = None
        self.last_fen = ""
        self.last_fen_by_color = {'w': None, 'b': None}
        self.depth_var = AppConfig.DEFAULT_DEPTH
        self.auto_mode_var = False
        self.board_positions = {}

        self.screenshot_delay_var = AppConfig.DEFAULT_SCREENSHOT_DELAY
        self.move_mode = AppConfig.DEFAULT_MOVE_MODE

        self.chessboard_x = None
        self.chessboard_y = None
        self.square_size = None

        self.bg_color = AppConfig.BG_COLOR
        self.frame_color = AppConfig.FRAME_COLOR
        self.accent_color = AppConfig.ACCENT_COLOR
        self.text_color = AppConfig.TEXT_COLOR
        self.hover_color = AppConfig.HOVER_COLOR

        # Initialize GUI components
        set_window_icon(self)
        create_widgets(self)
        bind_shortcuts(self)

        logger.debug(f"Initial window size: {self.width()}x{self.height()}")

        if not self.engine_service.initialize():
            logger.error("Stockfish initialization failed at startup")
            QMessageBox.warning(
                self,
                "Engine Warning",
                "Stockfish engine failed to initialize.\n\n"
                "The app will continue, but move analysis won't work.\n\n"
                f"Log file location:\n{get_log_file_path()}"
            )

    def create_color_button(self, parent, text, color):
        return color_button(self, parent, text, color)

    def create_action_button(self, parent, text, command):
        return action_button(self, parent, text, command)

    def create_move_method_radiobuttons(self, parent, text, method):
        return move_mode(self, parent, text, method)

    def create_castling_checkboxes(self):
        castling_checkboxes(self)

    def create_shortcuts_button(self, parent, command):
        return shortcuts_button(self, parent, command)

    def set_color(self, color):
        logger.info(f"Color selected: {'White' if color == 'w' else 'Black'}")
        self.color_indicator = color
        self.game_state.set_color(color)
        self.color_frame.hide()
        self.main_frame.show()
        self.btn_play.setEnabled(True)
        self.update_status(f"\nPlaying as {'White' if color == 'w' else 'Black'}")

    def set_move_mode(self, mode):
        logger.info(f"Move method set to: {mode}")
        self.move_mode = mode
        self.game_state.set_move_mode(mode)
        self.update_status(f"\nMove method: {mode.capitalize()}")

    def update_status(self, message):
        logger.debug(f"Status update: {message.strip()}")
        self.status_label.setText(message)
        self.depth_label.setText(f"Depth: {self.depth_var}")

    def process_move_thread(self):
        logger.info("Play Next Move button pressed; starting process_move thread")
        threading.Thread(
            target=process_move,
            args=(
                self,
                self.color_indicator,
                lambda: self.auto_mode_var,
                self.btn_play,
                self.move_mode,
                self.board_positions,
                self.update_status,
                lambda: self.kingside_var,
                lambda: self.queenside_var,
                self.update_last_fen_for_color,
                self.last_fen_by_color,
                lambda: self.screenshot_delay_var,
            ),
            daemon=True,
        ).start()

    def toggle_auto_mode(self):
        if self.auto_mode_var:
            logger.info("Auto mode enabled")
            self.btn_play.setEnabled(False)
            self.process_move_thread()
            threading.Thread(
                target=AutoPlayController.start_auto_play,
                args=(
                    self,
                    self.color_indicator,
                    lambda: self.auto_mode_var,
                    self.btn_play,
                    self.move_mode,
                    self.board_positions,
                    self.last_fen_by_color,
                    lambda: self.screenshot_delay_var,
                    self.update_status,
                    lambda: self.kingside_var,
                    lambda: self.queenside_var,
                    self.update_last_fen_for_color
                ),
                daemon=True
            ).start()
        else:
            logger.info("Auto mode disabled")
            self.btn_play.setEnabled(True)

    def closeEvent(self, event):
        logger.info("Application closing - cleaning up Stockfish process")
        self.auto_mode_var = False
        self.engine_service.cleanup()
        event.accept()

    def update_last_fen_for_color(self, fen: str):
        self.game_state.update_last_fen_for_color(fen)
        parts = fen.split()
        placement, active_color = parts[0], parts[1]
        self.last_fen_by_color[active_color] = placement
        logger.debug(f"Updated last FEN for {active_color}: {placement}")

import signal
from PyQt6.QtCore import QTimer

if __name__ == "__main__":
    logger.info("Starting ChessPilot main loop")
    app = QApplication(sys.argv)
    
    # Allow Python to catch Ctrl+C by letting the interpreter run every 100ms
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)
    
    def sigint_handler(signum, frame):
        logger.info("Ctrl+C detected! Shutting down gracefully...")
        QApplication.quit()
        
    signal.signal(signal.SIGINT, sigint_handler)
    
    try:
        window = ChessPilot()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.exception("Fatal error in main loop")
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\nLog file location:\n{get_log_file_path()}"
        )
        sys.exit(1)
    finally:
        if 'window' in locals() and hasattr(window, 'engine_service'):
            window.engine_service.cleanup()
        logger.info("ChessPilot application closed")
