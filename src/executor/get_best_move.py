import os
import subprocess
import shutil
import logging
from tkinter import messagebox
from utils.chess_resources_manager import find_maia_weights
from utils.get_binary_path import get_binary_path
import chess

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_best_move(depth_var, fen, root=None, auto_mode_var=None):
    """
    Use Maia (lc0 with Maia weights) to suggest a human-like move.
    Returns (best_move_uci, resulting_fen, is_mate).
    """
    try:
        lc0_path = get_binary_path("lc0")
        weights = find_maia_weights()
        popen_kwargs = dict(
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        engine = subprocess.Popen(
            [lc0_path,
             f"--weights={weights}",
             "--verbose-move-stats"],
            **popen_kwargs
        )
        engine.stdin.write("uci\n")
        engine.stdin.flush()
        for line in engine.stdout:
            if line.strip() == 'uciok':
                break
        engine.stdin.write(f"position fen {fen}\n")
        engine.stdin.write(f"go nodes {depth_var}\n")
        engine.stdin.flush()
        best_move = None
        for line in engine.stdout:
            if line.startswith("bestmove"):
                parts = line.split()
                best_move = parts[1] if len(parts) > 1 else None
                break
        board = chess.Board(fen)
        
        is_mate = False
        updated_fen = None
        
        if best_move and best_move != '(none)':
            board.push_uci(best_move)
            is_mate = board.is_checkmate()
            updated_fen = board.fen()
        engine.stdin.write("quit\n")
        engine.stdin.flush()
        engine.wait()
        return best_move, updated_fen, is_mate
    
    
    except Exception as e:
        logger.error(f"Maia error: {e}")
        if root:
            root.after(0, lambda err=e: messagebox.showerror("Error", f"Maia error: {str(err)}"))
        if auto_mode_var:
            auto_mode_var.set(False)
        return None, None, False