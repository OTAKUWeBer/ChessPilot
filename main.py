import time
import subprocess
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import shutil
from boardreader import get_fen_from_position, get_positions
import mss
import pyautogui
import glob

def is_wayland():
    return os.getenv("XDG_SESSION_TYPE") == "wayland"

def get_binary_path(binary):
    # For Windows, ensure the binary name ends with '.exe'
    if os.name == "nt" and not binary.endswith(".exe"):
        binary += ".exe"
        
    if getattr(sys, 'frozen', False):
        # When bundled with PyInstaller, binaries should be in the _MEIPASS folder
        path = os.path.join(sys._MEIPASS, binary)
    else:
        # Check for binary in system PATH on non-frozen mode
        path = shutil.which(binary)
        if path is None:
            path = binary

    if not (path and os.path.exists(path)):
        messagebox.showerror("Error", f"{binary} is missing! Make sure it's bundled properly.")
        sys.exit(1)
    return path

if is_wayland():
    import io
    from input_capture import WaylandInput
    grim_path = get_binary_path("grim")

# Import Win32 modules for Windows
if os.name == "nt":
    import win32api
    import win32con

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ChessPilot:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Pilot")
        self.root.geometry("350x350")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.color_indicator = None
        self.last_fen = ""
        self.depth_var = tk.IntVar(value=100)
        self.auto_mode_var = tk.BooleanVar(value=False)
        self.board_positions = {}
        self.processing_move = False

        # New: Screenshot delay variable (0.0 to 1.0 seconds)
        self.screenshot_delay_var = tk.DoubleVar(value=0.4)

        # Board cropping parameters for auto mode
        self.chessboard_x = None
        self.chessboard_y = None
        self.square_size = None

        # Modern color scheme
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

    def set_window_icon(self):
        logo_path = resource_path(os.path.join('assets', 'chess-logo.png'))
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                self.icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(False, self.icon)
            except Exception:
                pass

    def handle_esc_key(self, event=None):
        if self.main_frame.winfo_ismapped():
            self.main_frame.pack_forget()
            self.color_frame.pack(expand=True, fill=tk.BOTH)
            self.color_indicator = None
            self.btn_play.config(state=tk.DISABLED)
            self.update_status("")
            self.auto_mode_var.set(False)
            self.btn_play.config(state=tk.NORMAL)

    def create_widgets(self):
        self.color_frame = tk.Frame(self.root, bg=self.bg_color)
        
        header = tk.Label(self.color_frame, text="Chess Pilot", font=('Segoe UI', 18, 'bold'),
                        bg=self.bg_color, fg=self.accent_color)
        header.pack(pady=(20, 10))

        color_panel = tk.Frame(self.color_frame, bg=self.frame_color, padx=20, pady=15)
        tk.Label(color_panel, text="Select Your Color:", font=('Segoe UI', 11),
                bg=self.frame_color, fg=self.text_color).pack(pady=5)
        
        btn_frame = tk.Frame(color_panel, bg=self.frame_color)
        self.btn_white = self.create_color_button(btn_frame, "White", "w")
        self.btn_black = self.create_color_button(btn_frame, "Black", "b")
        btn_frame.pack(pady=5)

        depth_panel = tk.Frame(color_panel, bg=self.frame_color)
        tk.Label(depth_panel, text="Stockfish Depth:", font=('Segoe UI', 10),
                bg=self.frame_color, fg=self.text_color).pack(anchor='w')
        
        self.depth_slider = ttk.Scale(depth_panel, from_=10, to=30, variable=self.depth_var,
                                    style="TScale", command=self.update_depth_label)
        self.depth_slider.pack(fill='x', pady=5)
        
        self.depth_label = tk.Label(depth_panel, text=f"Depth: {self.depth_var.get()}",
                                    font=('Segoe UI', 9), bg=self.frame_color, fg=self.text_color)
        self.depth_label.pack()

        tk.Label(depth_panel, text="\nAuto Move Screenshot Delay (sec):", font=('Segoe UI', 10),
                 bg=self.frame_color, fg=self.text_color).pack(anchor='w')
        self.delay_spinbox = tk.Spinbox(depth_panel, from_=0.0, to=1.0, increment=0.1,
                                        textvariable=self.screenshot_delay_var, format="%.1f", width=5,
                                        state="readonly", justify="center")
        self.delay_spinbox.pack(anchor='w')
        
        depth_panel.pack(fill='x', pady=10)
        color_panel.pack(padx=30, pady=10, fill='x')
        self.color_frame.pack(expand=True, fill=tk.BOTH)

        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        
        control_panel = tk.Frame(self.main_frame, bg=self.frame_color, padx=20, pady=15)
        self.btn_play = self.create_action_button(control_panel, "Play Next Move", self.process_move_thread)
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

        self.status_label = tk.Label(control_panel, text="", font=('Segoe UI', 10),
                                    bg=self.frame_color, fg=self.text_color, wraplength=300)
        self.status_label.pack(fill='x', pady=10)
        control_panel.pack(padx=30, pady=20, fill='both', expand=True)
        
        self.main_frame.pack(expand=True, fill=tk.BOTH)

    def update_depth_label(self, value):
        self.depth_label.config(text=f"Depth: {int(float(value))}")
        self.root.update_idletasks()
        
    def create_color_button(self, parent, text, color):
        btn = tk.Button(parent, text=text, font=('Segoe UI', 10, 'bold'),
                       width=10, bd=0, padx=15, pady=8,
                       bg=self.accent_color, fg=self.text_color,
                       activebackground=self.hover_color,
                       activeforeground=self.text_color,
                       command=lambda: self.set_color(color))
        btn.pack(side=tk.LEFT, padx=5)
        return btn

    def create_action_button(self, parent, text, command):
        return tk.Button(parent, text=text, font=('Segoe UI', 11, 'bold'),
                        bg=self.accent_color, fg=self.text_color,
                        activebackground=self.hover_color,
                        activeforeground=self.text_color,
                        bd=0, pady=10, command=command)

    def create_castling_checkboxes(self):
        style = ttk.Style()
        style.configure("Castling.TCheckbutton",
                        background="#373737",
                        foreground="white",
                        font=("Segoe UI", 10))
        style.map("Castling.TCheckbutton",
                  background=[('active', '#333131'), ('pressed', '#333131')],
                  foreground=[('active', 'white'), ('pressed', 'white')])
        
        ttk.Checkbutton(self.castling_frame, text="Kingside Castle", 
                        variable=self.kingside_var, style="Castling.TCheckbutton"
                        ).grid(row=0, column=0, padx=10, sticky='w')
        ttk.Checkbutton(self.castling_frame, text="Queenside Castle",
                        variable=self.queenside_var, style="Castling.TCheckbutton"
                        ).grid(row=1, column=0, padx=10, sticky='w')

    def set_color(self, color):
        self.color_indicator = color
        self.color_frame.pack_forget()
        self.main_frame.pack(expand=True, fill=tk.BOTH)
        self.btn_play.config(state=tk.NORMAL)
        self.update_status(f"\nPlaying as {'White' if color == 'w' else 'Black'}")

    def update_status(self, message):
        self.status_label.config(text=message)
        self.depth_label.config(text=f"Depth: {self.depth_var.get()}")
        self.root.update_idletasks()

    def capture_screenshot_in_memory(self):
        try:
            if is_wayland():
                result = subprocess.run([grim_path, "-"], stdout=subprocess.PIPE, check=True)
                image = Image.open(io.BytesIO(result.stdout))
            else:
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    image = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            return image
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("Error", f"Screenshot failed: {str(err)}"))
            self.auto_mode_var.set(False)
            return None
        

    def get_best_move(self, fen):
        """
        Use Maia (LCZero binary with Maia weights) to suggest the human-like move.
        Depth var represents visit count.
        """
        try:
            # Locate the lc0 binary and Maia weights file
            lc0_path = get_binary_path("lc0.exe")
            def find_maia_weights(models_dir):
                pattern = os.path.join(models_dir, "maia-*.pb.gz")
                files = glob.glob(pattern)
                if not files:
                    messagebox.showerror("Error", f"No Maia weights found in {models_dir}")
                    sys.exit(1)
                # Optionally, sort by Elo rating embedded in the filename and pick the highest:
                def elo_from_name(path):
                    name = os.path.basename(path)
                    return int(name.split('-')[1].split('.')[0])
                files.sort(key=elo_from_name, reverse=True)
                return files[0]
            
            weights_dir = resource_path("models")
            weights = find_maia_weights(weights_dir)

            # Launch Maia (lc0) in UCI mode
            engine = subprocess.Popen([lc0_path, "--backend=onnx-cpu", f"--weights={weights}", "--verbose-move-stats"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Initialize UCI
            engine.stdin.write("uci\n")
            engine.stdin.flush()
            # Wait for 'uciok'
            while True:
                line = engine.stdout.readline()
                if not line:
                    break
                if "score mate" in line:
                    try:
                        parts = line.split("(T)")
                        mate_val = int(parts[1].split()[0])
                        if abs(mate_val) == 1:
                            mate_flag = True
                    except (IndexError, ValueError):
                        pass
                if line.strip() == 'uciok':
                    break

            # Set position
            engine.stdin.write(f"position fen {fen}\n")
            engine.stdin.write(f"go nodes {self.depth_var.get()}\n")
            engine.stdin.flush()
            
            mate_flag = False
            best_move = None
            # Parse bestmove
            while True:
                line = engine.stdout.readline()
                if not line:
                    break
                if "(T)" in line:
                    try:
                        parts = line.split("(T)")
                        mate_val = int(parts[1].split()[0])
                        if abs(mate_val) == 1:
                            mate_flag = True
                    except (IndexError, ValueError):
                        pass
                if line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        best_move = parts[1]
                    break
            updated_fen = None
            if best_move:
                engine.stdin.write(f"position fen {fen} moves {best_move}\n")
                engine.stdin.write("d\n")
                engine.stdin.flush()
                while True:
                    line = engine.stdout.readline()
                    if "fen" in line:
                        updated_fen = line.split("fen")[1].strip()
                        break

            # Clean up
            engine.stdin.write("quit\n")
            engine.stdin.flush()
            engine.wait()

            return best_move, updated_fen, mate_flag

        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("Error", f"Maia engine error: {err}"))
            self.auto_mode_var.set(False)
            return None

    def chess_notation_to_index(self, move):
        if self.color_indicator == "w":
            col_map = {'a':0, 'b':1, 'c':2, 'd':3, 'e':4, 'f':5, 'g':6, 'h':7}
            row_map = {'1':7, '2':6, '3':5, '4':4, '5':3, '6':2, '7':1, '8':0}
        else:
            col_map = {'a':7, 'b':6, 'c':5, 'd':4, 'e':3, 'f':2, 'g':1, 'h':0}
            row_map = {'1':0, '2':1, '3':2, '4':3, '5':4, '6':5, '7':6, '8':7}
        try:
            start_col = col_map[move[0]]
            start_row = row_map[move[1]]
            end_col = col_map[move[2]]
            end_row = row_map[move[3]]
            return (start_col, start_row), (end_col, end_row)
        except KeyError:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Invalid move notation: {move}"))
            self.auto_mode_var.set(False)
            return None, None

    def move_cursor_to_button(self):
        try:
            x = self.btn_play.winfo_rootx()
            y = self.btn_play.winfo_rooty()
            width = self.btn_play.winfo_width()
            height = self.btn_play.winfo_height()
            center_x = x + (width // 2)
            center_y = y + (height // 2)
            
            if os.name == "nt":  # Windows
                win32api.SetCursorPos((int(center_x), int(center_y)))
            if is_wayland():
                client = WaylandInput()
                client.click(int(center_x), int(center_y))
            else:
                pyautogui.moveTo(center_x, center_y, duration=0.1)
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror(f"Error", f"Could not relocate the mouse\n{str(err)}"))
            self.auto_mode_var.set(False)

    def move_piece(self, move, board_positions):
        start_idx, end_idx = self.chess_notation_to_index(move)
        if not start_idx or not end_idx:
            return
        try:
            start_pos = board_positions[start_idx]
            end_pos = board_positions[end_idx]
        except KeyError:
            self.root.after(0, lambda: messagebox.showerror("Error", "Could not map move to board positions"))
            self.auto_mode_var.set(False)
            return

        start_x, start_y = start_pos
        end_x, end_y = end_pos

        try:
            # Use appropriate click method based on the platform
            if os.name == "nt":  # Windows
                def shake_mouse(x, y, shakes=1):
                    win32api.SetCursorPos((x, y))
                    for _ in range(shakes):
                        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, -1, 0, 0)
                        
                def win_click(x, y):
                    win32api.SetCursorPos((x, y))
                    time.sleep(0.05)
                    shake_mouse(x, y)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                
                # Click on the start position
                win_click(int(start_x), int(start_y))
                # Small delay between clicks
               
                # Click on the end position
                win_click(int(end_x), int(end_y))
            elif is_wayland():
                client = WaylandInput()
                client.click(int(start_x), int(start_y))
                # Small delay between clicks
                time.sleep(0.2)
                client.click(int(end_x), int(end_y))
            else:
                # Fall back to pyautogui for other platforms
                pyautogui.click(start_x, start_y)
                # Small delay between clicks
                time.sleep(0.2)
                # Click on the end position
                pyautogui.click(end_x, end_y)
                
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to move piece: {str(err)}"))
            self.auto_mode_var.set(False)
            return

        if not self.auto_mode_var.get():
            self.root.after(0, self.move_cursor_to_button)

    def expand_fen_row(self, row):
        expanded = ""
        for char in row:
            if char.isdigit():
                expanded += " " * int(char)
            else:
                expanded += char
        return expanded

    def is_castling_possible(self, fen, color, side):
        board = fen.split()[0]
        rows = board.split('/')
        if color == "w":
            last_row = self.expand_fen_row(rows[-1])
            if len(last_row) != 8 or last_row[4] != 'K':
                return False
            if side == 'kingside':
                return last_row[7] == 'R'
            elif side == 'queenside':
                return last_row[0] == 'R'
        else:
            first_row = self.expand_fen_row(rows[0])
            if len(first_row) != 8 or first_row[4] != 'k':
                return False
            if side == 'kingside':
                return first_row[7] == 'r'
            elif side == 'queenside':
                return first_row[0] == 'r'
        return False

    def update_fen_castling_rights(self, fen):
        fields = fen.split()
        white_castling = ""
        if self.is_castling_possible(fen, "w", "kingside"):
            if self.color_indicator == "w":
                if self.kingside_var.get():
                    white_castling += "K"
            else:
                white_castling += "K"
        if self.is_castling_possible(fen, "w", "queenside"):
            if self.color_indicator == "w":
                if self.queenside_var.get():
                    white_castling += "Q"
            else:
                white_castling += "Q"

        black_castling = ""
        if self.is_castling_possible(fen, "b", "kingside"):
            if self.color_indicator == "b":
                if self.kingside_var.get():
                    black_castling += "k"
            else:
                black_castling += "k"
        if self.is_castling_possible(fen, "b", "queenside"):
            if self.color_indicator == "b":
                if self.queenside_var.get():
                    black_castling += "q"
            else:
                black_castling += "q"

        new_castling = white_castling + black_castling
        if new_castling == "":
            new_castling = "-"
        fields[2] = new_castling
        return " ".join(fields)
    
    def execute_normal_move(self, move, mate_flag, expected_fen):
        self.move_piece(move, self.board_positions)
        status_msg = f"Best Move: {move}\nMove Played: {move}"
        if mate_flag:
            status_msg += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
            self.auto_mode_var.set(False)
        self.root.after(0, lambda: self.update_status(status_msg))
        time.sleep(0.05)
        
        if mate_flag:
            # For checkmate moves, verify only once.
            success, _ = self.verify_move(move, expected_fen)
            if not success:
                self.root.after(0, lambda: self.update_status(f"Failed to checkmate\nCheckmate Move: {move}"))
            return
        
        success, _ = self.verify_move(move, expected_fen)
        if not success:
            self.root.after(0, lambda: self.update_status(f"Move verification failed\nBest Move: {move}"))
            self.auto_mode_var.set(False)

    def process_move(self):
        if self.processing_move:
            return
        self.processing_move = True
        self.root.after(0, lambda: self.btn_play.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.update_status("\nAnalyzing board..."))

        try:
            screenshot_image = self.capture_screenshot_in_memory()
            if not screenshot_image:
                return

            boxes = get_positions(screenshot_image)
            if not boxes:
                self.root.after(0, lambda: self.update_status("\nNo board detected"))
                self.auto_mode_var.set(False)
                return

            try:
                chessboard_x, chessboard_y, square_size, fen = get_fen_from_position(
                    self.color_indicator, boxes
                )
            except ValueError as e:
                self.root.after(0, lambda err=e: self.update_status(f"Error: {str(err)}"))
                self.auto_mode_var.set(False)
                return

            fen = self.update_fen_castling_rights(fen)
            self.store_board_positions(chessboard_x, chessboard_y, square_size)

            best_move, updated_fen, mate_flag = self.get_best_move(fen)
            if not best_move:
                self.root.after(0, lambda: self.update_status("No valid move found!"))
                return

            castling_moves = {"e1g1", "e1c1", "e8g8", "e8c8"}
            if best_move in castling_moves:
                side = 'kingside' if best_move in {"e1g1", "e8g8"} else 'queenside'
                if ((side == 'kingside' and self.kingside_var.get()) or 
                    (side == 'queenside' and self.queenside_var.get())):
                    if self.is_castling_possible(fen, self.color_indicator, side):
                        self.move_piece(best_move, self.board_positions)
                        status_msg = f"\nBest Move: {best_move}\nCastling move executed: {best_move}"
                        if mate_flag:
                            status_msg += "\n𝘾𝙝𝙚𝙘𝙠𝙢𝙖𝙩𝙚"
                            self.auto_mode_var.set(False)
                        self.root.after(0, lambda: self.update_status(status_msg))

                        time.sleep(0.3)
                        
                        if mate_flag:
                            # For checkmate, verify once before updating.
                            success, _ = self.verify_move(best_move, updated_fen)
                            if not success:
                                self.root.after(0, lambda: self.update_status(f"Move verification failed on checkmate move\nBest Move: {best_move}"))
                            else:
                                fen_after = self.get_current_fen()
                                if fen_after:
                                    self.last_fen = fen_after.split()[0]
                            self.auto_mode_var.set(False)
                        else:
                            success, _ = self.verify_move(best_move, updated_fen)
                            if not success:
                                self.root.after(0, lambda: self.update_status(f"Move verification failed\nBest Move: {best_move}"))
                                self.auto_mode_var.set(False)
                            else:
                                fen_after = self.get_current_fen()
                                if fen_after:
                                    self.last_fen = fen_after.split()[0]
            else:
                self.execute_normal_move(best_move, mate_flag, updated_fen)

        except Exception as e:
            self.root.after(0, lambda err=e: self.update_status(f"Error: {str(err)}"))
            self.auto_mode_var.set(False)
        finally:
            self.processing_move = False
            if not self.auto_mode_var.get():
                self.root.after(0, lambda: self.btn_play.config(state=tk.NORMAL))

    def store_board_positions(self, x, y, size):
        self.chessboard_x = x
        self.chessboard_y = y
        self.square_size = size
        self.board_positions.clear()
        for row in range(8):
            for col in range(8):
                pos_x = x + col * size + (size // 2)
                pos_y = y + row * size + (size // 2)
                self.board_positions[(col, row)] = (pos_x, pos_y)

    def verify_move(self, _, expected_fen, attempts_limit=3):
        expected_pieces = expected_fen.split()[0]
        for attempt in range(1, attempts_limit + 1):
            if attempt > 1:
                time.sleep(0.2)
            screenshot = self.capture_screenshot_in_memory()
            if not screenshot:
                continue
            boxes = get_positions(screenshot)
            if not boxes:
                continue
            try:
                _, _, _, current_fen = get_fen_from_position(self.color_indicator, boxes)
                fen_parts = current_fen.split()
                # If the active color changed, update last FEN and return.
                if len(fen_parts) > 1 and fen_parts[1] != self.color_indicator:
                    self.last_fen = fen_parts[0]
                    return True, attempt
                if fen_parts[0] == expected_pieces:
                    self.last_fen = fen_parts[0]
                    return True, attempt
            except ValueError:
                pass
        return False, attempts_limit

    def process_move_thread(self):
        threading.Thread(target=self.process_move, daemon=True).start()
        
    def toggle_auto_mode(self):
        if self.auto_mode_var.get():
            self.btn_play.config(state=tk.DISABLED)
            self.process_move_thread()
            threading.Thread(target=self.auto_move_loop, daemon=True).start()
        else:
            self.btn_play.config(state=tk.NORMAL)

    def auto_move_loop(self):
        """Waits for the board FEN to change before analyzing and playing the next move."""
        while self.auto_mode_var.get():
            if self.processing_move or not self.board_positions:
                time.sleep(0.1)
                continue
            try:
                screenshot = self.capture_screenshot_in_memory()
                if not screenshot:
                    continue
                boxes = get_positions(screenshot)
                if not boxes:
                    continue
                _, _, _, current_fen = get_fen_from_position(self.color_indicator, boxes)
                fen_parts = current_fen.split()
                if len(fen_parts) < 2:
                    continue
                current_pieces = fen_parts[0]
                active_color = fen_parts[1]
                # When it's our turn and the board has changed from our stored FEN, play the move.
                if active_color == self.color_indicator and current_pieces != self.last_fen:
                    time.sleep(self.screenshot_delay_var.get())
                    confirm_fen = self.get_current_fen()
                    if confirm_fen and confirm_fen.split()[0] == current_pieces:
                        self.last_fen = current_pieces
                        self.process_move_thread()
                        time.sleep(self.screenshot_delay_var.get())
            except Exception as e:
                self.root.after(0, lambda err=e: self.update_status(f"Error: {str(err)}"))
                self.auto_mode_var.set(False)

    def get_current_fen(self):
        try:
            screenshot = self.capture_screenshot_in_memory()
            boxes = get_positions(screenshot)
            if boxes:
                _, _, _, fen = get_fen_from_position(self.color_indicator, boxes)
                return fen
        except Exception:
            return None

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessPilot(root)
    root.mainloop()