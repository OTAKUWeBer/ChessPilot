import os
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import logging
import sys

from utils.logging_setup import setup_console_logging
from utils.resource_path import resource_path
from utils.chess_resources_manager import rename_onnx_model, extract_lc0

# Initialize Logging
setup_console_logging()
logger = logging.getLogger("main")

if not extract_lc0():
    logger.error(
        "Lc0 extraction failed. Please check the logs "
        "and ensure the Lc0 binary is downloaded correctly."
    )
    sys.exit(1)

if not rename_onnx_model():
    logger.error(
        "ONNX model rename failed. Please check the logs "
        "and ensure the model is downloaded correctly."
    )
    sys.exit(1)

from engine.capture_screenshot_in_memory import capture_screenshot_in_memory
from engine.chess_notation_to_index import chess_notation_to_index
from engine.move_cursor_to_button import move_cursor_to_button
from engine.move_piece import move_piece
from engine.expend_fen_row import expend_fen_row
from engine.is_castling_possible import is_castling_possible
from engine.update_fen_castling_rights import update_fen_castling_rights
from engine.did_my_piece_move import did_my_piece_move
from engine.execute_normal_move import execute_normal_move
from engine.process_move import process_move
from engine.store_board_positions import store_board_positions
from engine.verify_move import verify_move
from engine.auto_move import auto_move_loop
from engine.get_best_move import get_best_move
from engine.get_current_fen import get_current_fen


class ChessPilot:
    def __init__(self, root):
        logger.info("Initializing ChessPilot application")
        self.root = root
        self.root.title("Chess Pilot")
        self.root.geometry("350x350")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        # Game state variables
        self.color_indicator = None
        self.last_fen = ""
        self.last_fen_by_color = {'w': None, 'b': None}
        self.depth_var = tk.IntVar(value=15)
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
        
        self.set_window_icon()
        self.create_widgets()
        self.root.bind('<Escape>', self.handle_esc_key)
        logger.info("ChessPilot UI initialized")

    def set_window_icon(self):
        logo_path = resource_path(os.path.join('assets', 'chess-logo.png'))
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                self.icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(False, self.icon)
                logger.debug("Window icon set successfully")
            except Exception as e:
                logger.warning(f"Failed to set window icon: {e}")

    def handle_esc_key(self, event=None):
        """Return to color‐selection screen if ESC is pressed."""
        logger.info("ESC key pressed; returning to color selection")
        if self.main_frame.winfo_ismapped():
            self.main_frame.pack_forget()
            self.color_frame.pack(expand=True, fill=tk.BOTH)
            self.color_indicator = None
            self.btn_play.config(state=tk.DISABLED)
            self.update_status("")
            self.auto_mode_var.set(False)
            self.btn_play.config(state=tk.NORMAL)

    def create_widgets(self):
        # Color selection screen
        logger.debug("Creating color selection widgets")
        self.color_frame = tk.Frame(self.root, bg=self.bg_color)
        header = tk.Label(
            self.color_frame,
            text="Chess Pilot",
            font=('Segoe UI', 18, 'bold'),
            bg=self.bg_color,
            fg=self.accent_color
        )
        header.pack(pady=(20, 10))

        color_panel = tk.Frame(self.color_frame, bg=self.frame_color, padx=20, pady=15)
        tk.Label(
            color_panel,
            text="Select Your Color:",
            font=('Segoe UI', 11),
            bg=self.frame_color,
            fg=self.text_color
        ).pack(pady=5)

        btn_frame = tk.Frame(color_panel, bg=self.frame_color)
        self.btn_white = self.create_color_button(btn_frame, "White", "w")
        self.btn_black = self.create_color_button(btn_frame, "Black", "b")
        btn_frame.pack(pady=5)

        depth_panel = tk.Frame(color_panel, bg=self.frame_color)
        tk.Label(
            depth_panel,
            text="Maia Nodes:",
            font=('Segoe UI', 10),
            bg=self.frame_color,
            fg=self.text_color
        ).pack(anchor='w')

        self.depth_slider = ttk.Scale(
            depth_panel,
            from_=10,
            to=30,
            variable=self.depth_var,
            style="TScale",
            command=self.update_depth_label
        )
        self.depth_slider.pack(fill='x', pady=5)

        self.depth_label = tk.Label(
            depth_panel,
            text=f"Depth: {self.depth_var.get()}",
            font=('Segoe UI', 9),
            bg=self.frame_color,
            fg=self.text_color
        )
        self.depth_label.pack()

        tk.Label(
            depth_panel,
            text="\nAuto Move Screenshot Delay (sec):",
            font=('Segoe UI', 10),
            bg=self.frame_color,
            fg=self.text_color
        ).pack(anchor='w')
        self.delay_spinbox = tk.Spinbox(
            depth_panel,
            from_=0.0,
            to=1.0,
            increment=0.1,
            textvariable=self.screenshot_delay_var,
            format="%.1f",
            width=5,
            state="readonly",
            justify="center"
        )
        self.delay_spinbox.pack(anchor='w')

        depth_panel.pack(fill='x', pady=10)
        color_panel.pack(padx=30, pady=10, fill='x')
        self.color_frame.pack(expand=True, fill=tk.BOTH)

        # Main control screen (after color is chosen)
        logger.debug("Creating main control widgets")
        self.main_frame = tk.Frame(self.root, bg=self.bg_color)

        control_panel = tk.Frame(self.main_frame, bg=self.frame_color, padx=20, pady=15)
        self.btn_play = self.create_action_button(
            control_panel,
            "Play Next Move",
            self.process_move_thread
        )
        self.btn_play.pack(fill='x', pady=5)

        self.castling_frame = tk.Frame(control_panel, bg=self.frame_color)
        self.kingside_var = tk.BooleanVar()
        self.queenside_var = tk.BooleanVar()
        self.create_castling_checkboxes()
        self.castling_frame.pack(pady=10)

        self.auto_mode_check = ttk.Checkbutton(
            control_panel,
            text="Auto Next Moves",
            variable=self.auto_mode_var,
            command=self.toggle_auto_mode,
            style="Castling.TCheckbutton"
        )
        self.auto_mode_check.pack(pady=5, anchor="center")

        self.status_label = tk.Label(
            control_panel,
            text="",
            font=('Segoe UI', 10),
            bg=self.frame_color,
            fg=self.text_color,
            wraplength=300
        )
        self.status_label.pack(fill='x', pady=10)

        control_panel.pack(padx=30, pady=20, fill='both', expand=True)
        self.main_frame.pack(expand=True, fill=tk.BOTH)

        # Disable "Play Next Move" until a color is chosen
        self.btn_play.config(state=tk.DISABLED)

        logger.debug("Widgets created successfully")

    def update_depth_label(self, value):
        logger.debug(f"Depth slider changed to {value}")
        self.depth_label.config(text=f"Depth: {int(float(value))}")
        self.root.update_idletasks()

    def create_color_button(self, parent, text, color):
        btn = tk.Button(
            parent,
            text=text,
            font=('Segoe UI', 10, 'bold'),
            width=10,
            bd=0,
            padx=15,
            pady=8,
            bg=self.accent_color,
            fg=self.text_color,
            activebackground=self.hover_color,
            activeforeground=self.text_color,
            command=lambda: self.set_color(color)
        )
        btn.pack(side=tk.LEFT, padx=5)
        return btn

    def create_action_button(self, parent, text, command):
        btn = tk.Button(
            parent,
            text=text,
            font=('Segoe UI', 11, 'bold'),
            bg=self.accent_color,
            fg=self.text_color,
            activebackground=self.hover_color,
            activeforeground=self.text_color,
            bd=0,
            pady=10,
            command=command
        )
        btn.pack()
        return btn

    def create_castling_checkboxes(self):
        logger.debug("Creating castling checkboxes")
        style = ttk.Style()
        style.configure(
            "Castling.TCheckbutton",
            background="#373737",
            foreground="white",
            font=("Segoe UI", 10)
        )
        style.map(
            "Castling.TCheckbutton",
            background=[('active', '#333131'), ('pressed', '#333131')],
            foreground=[('active', 'white'), ('pressed', 'white')]
        )

        ttk.Checkbutton(
            self.castling_frame,
            text="Kingside Castle",
            variable=self.kingside_var,
            style="Castling.TCheckbutton"
        ).grid(row=0, column=0, padx=10, sticky='w')
        ttk.Checkbutton(
            self.castling_frame,
            text="Queenside Castle",
            variable=self.queenside_var,
            style="Castling.TCheckbutton"
        ).grid(row=1, column=0, padx=10, sticky='w')

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

    logger.info("Maia and ONNX model setup completed successfully")
    logger.info("Starting ChessPilot main loop")
    root = tk.Tk()
    app = ChessPilot(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Exiting APP")
        root.destroy()
    logger.info("ChessPilot application closed")

