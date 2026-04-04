import threading
import sys
import logging
from pathlib import Path
import os
import multiprocessing

# Must be at the very top for PyInstaller on Windows
if __name__ == "__main__":
    # Hide console window on Windows when frozen
    if sys.platform == 'win32' and getattr(sys, 'frozen', False):
        import ctypes
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 
            0  # SW_HIDE
        )
    multiprocessing.freeze_support()

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import Qt

from utils.logging_setup import setup_console_logging
from utils.chess_resources_manager import setup_resources
from utils.system_info import log_system_info, log_dependency_status
from utils.downloader import get_linux_install_cmd

setup_console_logging()
logger = logging.getLogger(__name__)

script_dir = Path(__file__).resolve().parent
project_dir = script_dir.parent

os.chdir(script_dir)

logger.info("ChessPilot starting...")
logger.info(f"Version: 2.2.0")

log_system_info()
log_dependency_status()

if not setup_resources(script_dir, project_dir):
    logger.error("Resource setup failed")
    # Show error dialog before exiting
    app = QApplication(sys.argv)
    msg = "Failed to setup required resources (Lc0 or ONNX model).\n\n"
    if sys.platform != "win32":
        cmd = get_linux_install_cmd()
        msg += "Note: For Linux/macOS, Lc0 binaries cannot be auto-downloaded.\n"
        msg += f"Please install Lc0 via your package manager '{cmd}'\n"
        msg += "and ensure it is in your system PATH, or place the binary manually at: src/lc0\n"
    else:
        msg += "Please check:\n"
        msg += "1. Your internet connection\n"
        msg += "2. That you have write permissions\n"
        msg += "3. The logs for more details"
        
    QMessageBox.critical(None, "Setup Failed", msg)
    sys.exit(1)

from core import GameState, AppConfig
from game import MoveExecutor, BoardAnalyzer, MoveValidator, AutoPlayController
from game.move_processor import process_move
from services import EngineService

from gui.set_window_icon import set_window_icon
from gui.create_widget import create_widgets
from gui.shortcuts import bind_shortcuts
from gui.button_and_checkboxes import (
    color_button,
    action_button,
    castling_checkboxes,
    move_mode,
    shortcuts_button,
)

class ChessPilot(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing ChessPilot application")

        self.setWindowTitle(AppConfig.WINDOW_TITLE)
        self.setGeometry(100, 100, AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT)
        self.setFixedSize(AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self.game_state = GameState()
        self.move_executor = MoveExecutor()
        self.board_analyzer = BoardAnalyzer()
        self.move_validator = MoveValidator()
        self.engine_service = EngineService()

        self.color_indicator = None
        self.last_fen = ""
        self.last_fen_by_color = {'w': None, 'b': None}

        self.auto_mode_var = False
        self.board_positions = {}

        self.screenshot_delay_var = AppConfig.DEFAULT_SCREENSHOT_DELAY
        self.maia_elo_var = 1500
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
            logger.error("Lc0 initialization failed at startup")
            QMessageBox.warning(
                self,
                "Engine Warning",
                "Lc0 engine failed to initialize.\n\n"
                "The app will continue, but move analysis won't work.\n"
                "Please restart the application or check the logs."
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
        self.color_frame.hide()
        self.main_frame.show()
        self.btn_play.setEnabled(True)
        self.update_status(f"\nPlaying as {'White' if color == 'w' else 'Black'}")

    def set_move_mode(self, mode):
        logger.info(f"Move method set to: {mode}")
        self.move_mode = mode
        self.update_status(f"\nMove method: {mode.capitalize()}")

    def update_status(self, message):
        logger.debug(f"Status update: {message.strip()}")
        self.status_label.setText(message)

    def update_maia_elo(self):
        elo = getattr(self, 'maia_elo_var', 1500)
        logger.info(f"User selected new Maia ELO: {elo}")
        self.update_status(f"Downloading/Switching to Maia {elo}...")
        self.btn_play.setEnabled(False)
        
        def _bg_update():
            from utils.downloader import download_maia_weights
            success = download_maia_weights(elo)
            if success:
                self.engine_service.set_maia_elo(elo)
                self.update_status(f"Maia engine updated to {elo} ELO")
            else:
                self.update_status(f"Failed to load Maia {elo}")
            
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.btn_play.setEnabled(bool(self.color_indicator)))
            
        threading.Thread(target=_bg_update, daemon=True).start()

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

    def capture_board_screenshot(self):
        return self.board_analyzer.capture_screenshot(self, lambda: self.auto_mode_var)

    def convert_move_to_indices(self, move: str):
        return self.move_executor.convert_move_to_indices(
            self.color_indicator, self, lambda: self.auto_mode_var, move
        )

    def relocate_cursor_to_play_button(self):
        self.move_executor.relocate_cursor_to_button(self, lambda: self.auto_mode_var, self.btn_play)

    def drag_piece(self, move: str):
        self.move_executor.execute_move(
            self.color_indicator, move, self.board_positions,
            lambda: self.auto_mode_var, self, self.btn_play, self.move_mode
        )

    def expand_fen_row(self, row: str):
        return self.board_analyzer.expand_fen_row(row)

    def check_castling(self, fen: str):
        return self.board_analyzer.check_castling_possible(fen, self.color_indicator)

    def adjust_castling_fen(self, fen: str):
        return self.board_analyzer.adjust_castling_fen(
            self.color_indicator, lambda: self.kingside_var, lambda: self.queenside_var, fen
        )

    def check_move_validity(self, before_fen: str, after_fen: str, move: str):
        return self.move_validator.check_move_validity(
            self.color_indicator, before_fen, after_fen, move
        )

    def play_normal_move(self, move: str, mate_flag: bool, expected_fen: str):
        logger.debug(f"Playing normal move via wrapper: {move}")
        return self.move_executor.execute_normal_move(
            self.board_positions,
            self.color_indicator,
            move,
            mate_flag,
            expected_fen,
            self,
            lambda: self.auto_mode_var,
            self.update_status,
            self.btn_play,
            self.move_mode,
        )

    def query_best_move(self, fen: str):
        return self.engine_service.get_best_move(
            fen, self, lambda: self.auto_mode_var
        )

    def read_current_fen(self):
        return self.board_analyzer.read_current_fen(self.color_indicator)

    def store_positions(self, x: int, y: int, size: int):
        from core.board_utils import store_board_positions
        logger.debug(f"Storing board positions: x={x}, y={y}, size={size}")
        store_board_positions(self.board_positions, x, y, size)

    def verify_move_wrapper(self, before_fen: str, expected_fen: str, attempts_limit: int = 3):
        return self.move_validator.verify_move(
            self.color_indicator, before_fen, expected_fen, attempts_limit
        )

    def closeEvent(self, event):
        logger.info("Application closing - cleaning up Lc0 process")
        self.engine_service.cleanup()
        event.accept()

    def update_last_fen_for_color(self, fen: str):
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
            f"An unexpected error occurred:\n\n{str(e)}\n\nPlease check the logs."
        )
        sys.exit(1)
    finally:
        if 'window' in locals() and hasattr(window, 'engine_service'):
            window.engine_service.cleanup()
        logger.info("ChessPilot application closed")
