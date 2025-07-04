import os
import subprocess
import shutil
import logging
from tkinter import messagebox
from utils.resource_path import resource_path

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_best_move(depth_var, fen, root=None, auto_mode_var=None):
    try:
        logger.info("Getting best move from Stockfish")
        
        stockfish_path = resource_path("stockfish.exe" if os.name == "nt" else "stockfish")
        
        if os.name != "nt" and not os.path.exists(stockfish_path):
            sys_stock = shutil.which("stockfish")
            if sys_stock:
                logger.debug(f"Falling back to system Stockfish at {sys_stock}")
                stockfish_path = sys_stock
                
        if not os.path.exists(stockfish_path) and shutil.which(stockfish_path) is None:
            raise FileNotFoundError(f"Stockfish not found at {stockfish_path}")
        
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        logger.debug(f"Using Stockfish path: {stockfish_path}")
        
        stockfish = subprocess.Popen(
            [stockfish_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=flags
        )
        
        stockfish.stdin.write(f"position fen {fen}\n")
        stockfish.stdin.write(f"go depth {depth_var}\n")
        stockfish.stdin.flush()
        
        best_move = None
        mate_flag = False
        
        while True:
            line = stockfish.stdout.readline()
            if not line:
                break
            logger.debug(f"Engine output: {line.strip()}")
            if "score mate" in line:
                try:
                    parts = line.split("score mate")
                    mate_val = int(parts[1].split()[0])
                    if abs(mate_val) == 1:
                        mate_flag = True
                        logger.info("Mate in 1 detected")
                except (IndexError, ValueError):
                    logger.warning("Could not parse mate score")
            if line.startswith("bestmove"):
                best_move = line.strip().split()[1]
                logger.info(f"Best move received: {best_move}")
                break

        # If Stockfish did not return a best move, inform the user
        if best_move is None:
            error_msg = "Stockfish did not respond. Please download the correct version according to your CPU architecture."
            logger.error(error_msg)
            if root:
                root.after(0, lambda: messagebox.showerror("Error", error_msg))
            if auto_mode_var:
                auto_mode_var.set(False)
            stockfish.stdin.write("quit\n")
            stockfish.stdin.flush()
            stockfish.wait()
            return None, None, False

        updated_fen = None
        if best_move:
            stockfish.stdin.write(f"position fen {fen} moves {best_move}\n")
            stockfish.stdin.write("d\n")
            stockfish.stdin.flush()
            while True:
                line = stockfish.stdout.readline()
                if not line:
                    break
                logger.debug(f"Engine output for new FEN: {line.strip()}")
                if "Fen:" in line:
                    updated_fen = line.split("Fen:")[1].strip()
                    logger.info(f"Updated FEN: {updated_fen}")
                    break
        
        stockfish.stdin.write("quit\n")
        stockfish.stdin.flush()
        stockfish.wait()
        
        return best_move, updated_fen, mate_flag

    except Exception as e:
        logger.error(f"Stockfish error: {str(e)}")
        if root:
            root.after(0, lambda err=e: messagebox.showerror("Error", f"Stockfish error: {str(err)}"))
        if auto_mode_var:
            auto_mode_var.set(False)
        return None, None, False
