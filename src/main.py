import threading
import sys
import logging
from pathlib import Path
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import Qt

from utils.logging_setup import setup_console_logging
from utils.chess_resources_manager import setup_resources

setup_console_logging()
logger = logging.getLogger("main")

script_dir = Path(__file__).resolve().parent
project_dir = script_dir.parent

os.chdir(script_dir)

logger.info("ChessPilot starting...")
if not setup_resources(script_dir, project_dir):
    logger.error("Resource setup failed")
    # Show error dialog before exiting
    app = QApplication(sys.argv)
    QMessageBox.critical(
        None,
        "Setup Failed",
        "Failed to setup required resources (Stockfish or ONNX model).\n\n"
        "Please check:\n"
        "1. Your internet connection\n"
        "2. That you have write permissions\n"
        "3. The logs for more details"
    )
    sys.exit(1)

from executor import process_move, execute_normal_move
from core import GameState, AppConfig
from game import MoveExecutor, BoardAnalyzer, MoveValidator, AutoPlayController
from services import EngineService

from gui.set_window_icon import set_window_icon
from gui.create_widget import create_widgets
from gui.shortcuts import bind_shortcuts
from gui.button_and_checkboxes import (
    color_button,
    action_button,
    castling_checkboxes,
    move_mode,
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
        return execute_normal_move(
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
            self.depth_var, fen, self, lambda: self.auto_mode_var
        )

    def read_current_fen(self):
        return self.board_analyzer.read_current_fen(self.color_indicator)

    def store_positions(self, x: int, y: int, size: int):
        from executor.store_board_positions import store_board_positions
        logger.debug(f"Storing board positions: x={x}, y={y}, size={size}")
        store_board_positions(self.board_positions, x, y, size)

    def verify_move_wrapper(self, before_fen: str, expected_fen: str, attempts_limit: int = 3):
        return self.move_validator.verify_move(
            self.color_indicator, before_fen, expected_fen, attempts_limit
        )

    def closeEvent(self, event):
        logger.info("Application closing - cleaning up Stockfish process")
        self.engine_service.cleanup()
        event.accept()

    def update_last_fen_for_color(self, fen: str):
        parts = fen.split()
        placement, active_color = parts[0], parts[1]
        self.last_fen_by_color[active_color] = placement
        logger.debug(f"Updated last FEN for {active_color}: {placement}")

if __name__ == "__main__":
    logger.info("Starting ChessPilot main loop")
    app = QApplication(sys.argv)
    
    try:
        window = ChessPilot()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("Exiting APP")
        if 'window' in locals() and hasattr(window, 'engine_service'):
            window.engine_service.cleanup()
    except Exception as e:
        logger.exception("Fatal error in main loop")
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\nPlease check the logs."
        )
        sys.exit(1)
    finally:
        logger.info("ChessPilot application closed")
