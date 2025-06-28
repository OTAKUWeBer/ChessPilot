import threading
import tkinter as tk
from tkinter import ttk
import logging
import sys
from pathlib import Path
import os

from utils.logging_setup import setup_console_logging
from utils.chess_resources_manager import setup_resources

# Initialize Logging
setup_console_logging()
logger = logging.getLogger("main")

script_dir = Path(__file__).resolve().parent
project_dir = script_dir.parent

os.chdir(script_dir)

if not setup_resources(script_dir, project_dir):
    logger.error("Resource setup failed")
    sys.exit(1)

from executor import (
    auto_move_loop,
    capture_screenshot_in_memory,
    did_my_piece_move,
    expend_fen_row,
    get_best_move,
    get_current_fen,
    is_castling_possible,
    move_cursor_to_button,
    move_piece,
    process_move,
    store_board_positions,
    update_fen_castling_rights,
    verify_move,
    chess_notation_to_index,
    execute_normal_move
)

from gui.set_window_icon import set_window_icon
from gui.create_widget import create_widgets
from gui.shortcuts import handle_esc_key, bind_shortcuts
from gui.button_and_checkboxes import (
    color_button,
    action_button,
    castling_checkboxes
)

class ChessPilot:
    def __init__(self, root):
        logger.info("Initializing ChessPilot application")
        self.root = root
        self.root.title("ChessPilot")
        self.root.geometry("350x350")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        # Game state variables
        self.color_indicator = None
        self.last_fen = ""
        self.last_fen_by_color = {'w': None, 'b': None}
        self.depth_var = tk.IntVar(value=600)
        self.auto_mode_var = tk.BooleanVar(value=False)
        self.board_positions = {}

        # Screenshot delay (0.0 to 1.0 seconds)
        self.screenshot_delay_var = tk.DoubleVar(value=0.4)

        # Board cropping parameters (unused until you set them)
        self.chessboard_x = None
        self.chessboard_y = None
        self.square_size = None

        # UI color scheme
        self.bg_color = "#2D2D2D"
        self.frame_color = "#373737"
        self.accent_color = "#4CAF50"
        self.text_color = "#FFFFFF"
        self.hover_color = "#45a049"
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TScale", troughcolor=self.frame_color, background=self.bg_color)
        self.style.configure("TCheckbutton", background=self.bg_color, foreground=self.text_color)
        
        set_window_icon(self)
        create_widgets(self)
        bind_shortcuts(self)

        # Log initial window size for debugging
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        logger.debug(f"Initial window size: {width}x{height}")
        

        self.root.bind('<Escape>', self.take_esc_key)
        self.root.focus_set()
        logger.info("ChessPilot UI initialized")
        
    # Handle ESC key to return to color selection
    def take_esc_key(self, event=None):
        if self.color_indicator is not None:
            handle_esc_key(self, event)
        
    # def log_button_sizes(self):
    #     w_w = self.btn_white.winfo_width()
    #     w_h = self.btn_white.winfo_height()
    #     b_w = self.btn_black.winfo_width()
    #     b_h = self.btn_black.winfo_height()
    #     logger.debug(f"[SIZE DEBUG] White button size: {w_w}×{w_h}")
    #     logger.debug(f"[SIZE DEBUG] Black button size: {b_w}×{b_h}")

    def create_color_button(self, parent, text, color):
        return color_button(self, parent, text, color)

    def create_action_button(self, parent, text, command):
        return action_button(self, parent, text, command)
        
    def create_castling_checkboxes(self):
        castling_checkboxes(self)

    def update_last_fen_for_color(self, fen: str):
        parts = fen.split()
        placement, active_color = parts[0], parts[1]
        self.last_fen_by_color[active_color] = placement
        logger.debug(f"Updated last FEN for {active_color}: {placement}")

    def set_color(self, color):
        logger.info(f"Color selected: {'White' if color == 'w' else 'Black'}")
        self.color_indicator = color
        self.color_frame.pack_forget()
        self.main_frame.pack(expand=True, fill=tk.BOTH)
        self.btn_play.config(state=tk.NORMAL)
        self.update_status(f"\nPlaying as {'White' if color == 'w' else 'Black'}")

    def update_status(self, message):
        logger.debug(f"Status update: {message.strip()}")
        self.status_label.config(text=message)
        self.depth_label.config(text=f"Depth: {self.depth_var.get()}")
        self.root.update_idletasks()

    def process_move_thread(self):
        logger.info("Play Next Move button pressed; starting process_move thread")
        threading.Thread(
            target=process_move,
            args=(
                self.root,
                self.color_indicator,
                self.auto_mode_var,
                self.btn_play,
                self.board_positions,
                self.update_status,
                self.kingside_var,
                self.queenside_var,
                self.update_last_fen_for_color,
                self.last_fen_by_color,
                self.screenshot_delay_var,
            ),
            daemon=True,
        ).start()

    def toggle_auto_mode(self):
        if self.auto_mode_var.get():
            logger.info("Auto mode enabled")
            self.btn_play.config(state=tk.DISABLED)
            # First, play a single move to initialize if needed
            self.process_move_thread()
            # Then start continuous auto loop
            threading.Thread(
                target=auto_move_loop,
                args=(
                    self.root,
                    self.color_indicator,
                    self.auto_mode_var,
                    self.btn_play,
                    self.board_positions,
                    self.last_fen_by_color,
                    self.screenshot_delay_var,
                    self.update_status,
                    self.kingside_var,
                    self.queenside_var,
                    self.update_last_fen_for_color
                ),
                daemon=True
            ).start()

        else:
            logger.info("Auto mode disabled")
            self.btn_play.config(state=tk.NORMAL)

    def capture_board_screenshot(self):
        logger.debug("Capturing board screenshot via wrapper")
        return capture_screenshot_in_memory(self.root, self.auto_mode_var)

    def convert_move_to_indices(self, move: str):
        logger.debug(f"Converting move to indices: {move}")
        return chess_notation_to_index(
            self.color_indicator,
            self.root,
            self.auto_mode_var,
            move
        )

    def relocate_cursor_to_play_button(self):
        logger.debug("Relocating cursor to Play button via wrapper")
        move_cursor_to_button(self.root, self.auto_mode_var, self.btn_play)

    def drag_piece(self, move: str):
        logger.debug(f"Dragging piece for move: {move}")
        move_piece(self.color_indicator, move, self.board_positions, self.auto_mode_var, self.root, self.btn_play)

    def expand_fen_row(self, row: str):
        logger.debug(f"Expanding FEN row: {row}")
        return expend_fen_row(row)

    def check_castling(self, fen: str):
        result = is_castling_possible(fen, self.color_indicator, "kingside") or \
                 is_castling_possible(fen, self.color_indicator, "queenside")
        logger.debug(f"Check castling possibility for '{fen}': {result}")
        return result

    def adjust_castling_fen(self, fen: str):
        logger.debug(f"Adjusting castling rights for FEN: {fen}")
        return update_fen_castling_rights(
            self.color_indicator,
            self.kingside_var,
            self.queenside_var,
            fen
        )

    def check_move_validity(self, before_fen: str, after_fen: str, move: str):
        logger.debug(f"Verifying move validity: {move}")
        return did_my_piece_move(self.color_indicator, before_fen, after_fen, move)

    def play_normal_move(self, move: str, mate_flag: bool, expected_fen: str):
        logger.debug(f"Playing normal move via wrapper: {move}")
        return execute_normal_move(
            self.board_positions,
            self.color_indicator,
            move,
            mate_flag,
            expected_fen,
            self.root,
            self.auto_mode_var,
            self.update_status,
            self.btn_play
        )

    def query_best_move(self, fen: str):
        logger.debug(f"Querying best move for FEN: {fen}")
        return get_best_move(
            self.depth_var.get(),
            fen,
            self.root,
            self.auto_mode_var
        )

    def read_current_fen(self):
        logger.debug("Reading current FEN via wrapper")
        return get_current_fen(self.color_indicator)

    def store_positions(self, x: int, y: int, size: int):
        logger.debug(f"Storing board positions: x={x}, y={y}, size={size}")
        store_board_positions(self.board_positions, x, y, size)

    def verify_move_wrapper(self, before_fen: str, expected_fen: str, attempts_limit: int = 3):
        logger.debug(f"Verifying move via wrapper; expected FEN: {expected_fen}")
        return verify_move(
            self.color_indicator,
            before_fen,
            expected_fen,
            attempts_limit
        )

if __name__ == "__main__":

    logger.info("LC0, maia and ONNX model setup completed successfully")
    logger.info("Starting ChessPilot main loop")
    root = tk.Tk()
    app = ChessPilot(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Exiting APP")
        root.destroy()
    logger.info("ChessPilot application closed")

