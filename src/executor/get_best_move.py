import os
import subprocess
import shutil
import logging
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
import sys
from utils.resource_path import resource_path

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Global Stockfish process
_stockfish_process = None

def get_root_dir():
    # When bundled by PyInstaller, __file__ doesn't point to the EXE location
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

CONFIG_FILE = os.path.join(get_root_dir(), "engine_config.txt")

def create_default_config(config_path):
    """Creates a default config file with user-friendly comments."""
    with open(config_path, "w") as f:
        f.write("# ================================\n")
        f.write("# ChessPilot Engine Configuration\n")
        f.write("# ================================\n")
        f.write("# You can edit these values to change engine behavior.\n")
        f.write("# Be sure to restart the app after editing this file.\n\n")

        f.write("# Memory used in MB (64-1024+ recommended depending on your system)\n")
        f.write("setoption name Hash value 1024\n\n")

        f.write("# CPU threads to use (1-8 usually; match your CPU core count)\n")
        f.write("setoption name Threads value 4\n")
    
    logger.info(f"Created default config file at {config_path}")

def load_engine_config(stockfish_proc, config_path=CONFIG_FILE):
    """Loads Stockfish engine settings from a config file. Creates default with comments if missing."""
    
    # Always check if config exists and create if missing
    if not os.path.exists(config_path):
        create_default_config(config_path)

    # Load and apply the config
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                logger.info(f"Applying engine option: {line}")
                stockfish_proc.stdin.write(f"{line}\n")
            except Exception as e:
                logger.warning(f"Failed to apply config line '{line}': {e}")

    stockfish_proc.stdin.write("isready\n")
    stockfish_proc.stdin.flush()
    while True:
        if stockfish_proc.stdout.readline().strip() == "readyok":
            break

def ensure_config_exists():
    """Ensures the config file exists, creating it if necessary."""
    if not os.path.exists(CONFIG_FILE):
        logger.warning("Config file missing during gameplay, regenerating...")
        create_default_config(CONFIG_FILE)
        return True  # Indicates config was recreated
    return False  # Config already exists

def _initialize_stockfish():
    """Initialize a persistent Stockfish process."""
    global _stockfish_process
    
    if _stockfish_process is not None:
        return _stockfish_process
    
    try:
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
        
        _stockfish_process = subprocess.Popen(
            [stockfish_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=flags
        )

        # Load custom engine config
        load_engine_config(_stockfish_process)
        
        logger.info("Stockfish process initialized")
        return _stockfish_process
        
    except Exception as e:
        logger.error(f"Failed to initialize Stockfish: {e}")
        _stockfish_process = None
        raise

def cleanup_stockfish():
    """Clean up the persistent Stockfish process."""
    global _stockfish_process
    
    if _stockfish_process is not None:
        try:
            _stockfish_process.stdin.write("quit\n")
            _stockfish_process.stdin.flush()
            _stockfish_process.wait(timeout=5)
        except Exception:
            _stockfish_process.terminate()
        finally:
            _stockfish_process = None
            logger.info("Stockfish process cleaned up")

def initialize_stockfish_at_startup():
    """Initialize Stockfish at application startup."""
    try:
        logger.info("Initializing Stockfish at application startup...")
        stockfish_process = _initialize_stockfish()
        if stockfish_process:
            logger.info("Stockfish successfully initialized with config settings")
            return True
        else:
            logger.error("Failed to initialize Stockfish at startup")
            return False
    except Exception as e:
        logger.error(f"Error initializing Stockfish at startup: {e}")
        return False

def get_best_move(depth_var, fen, root=None, auto_mode_var=None):
    """
    Main function to get the best move from Stockfish.
    Complexity reduced by breaking into smaller functions.
    """
    try:
        logger.info("Getting best move from Stockfish")
        
        stockfish = _setup_stockfish_engine()
        if stockfish is None:
            return _handle_stockfish_failure("Failed to initialize Stockfish", root, auto_mode_var)
        
        best_move, mate_flag = _get_move_from_engine(stockfish, depth_var, fen)
        if best_move is None:
            return _handle_stockfish_failure(
                "Stockfish did not respond. Please download the correct version according to your CPU architecture.",
                root, auto_mode_var
            )
        
        updated_fen = _get_updated_fen(stockfish, fen, best_move)
        return best_move, updated_fen, mate_flag

    except Exception as e:
        logger.error(f"Stockfish error: {str(e)}")
        cleanup_stockfish()
        return _handle_error(e, root, auto_mode_var)


def _setup_stockfish_engine():
    """
    Initialize Stockfish engine and handle configuration.
    """
    config_recreated = ensure_config_exists()
    stockfish = _initialize_stockfish()
    
    if config_recreated and stockfish:
        logger.info("Reloading config into existing Stockfish process")
        load_engine_config(stockfish)
    
    return stockfish


def _get_move_from_engine(stockfish, depth_var, fen):
    """
    Send position and depth to engine, parse response for best move and mate detection.
    """
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
        
        mate_flag = _check_for_mate(line, mate_flag)
        best_move = _extract_best_move(line)
        
        if best_move:
            logger.info(f"Best move received: {best_move}")
            break
    
    return best_move, mate_flag


def _check_for_mate(line, current_mate_flag):
    """
    Check if the engine output indicates a mate in 1.
    """
    if "score mate" not in line:
        return current_mate_flag
    
    try:
        parts = line.split("score mate")
        mate_val = int(parts[1].split()[0])
        if abs(mate_val) == 1:
            logger.info("Mate in 1 detected")
            return True
    except (IndexError, ValueError):
        logger.warning("Could not parse mate score")
    
    return current_mate_flag


def _extract_best_move(line):
    """
    Extract best move from engine output line.
    """
    if line.startswith("bestmove"):
        return line.strip().split()[1]
    return None


def _get_updated_fen(stockfish, original_fen, best_move):
    """
    Get the updated FEN position after making the best move.
    """
    if not best_move:
        return None
    
    stockfish.stdin.write(f"position fen {original_fen} moves {best_move}\n")
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
            return updated_fen
    
    return None


def _handle_stockfish_failure(error_msg, root, auto_mode_var):
    """
    Handle cases where Stockfish fails to initialize or respond.
    """
    logger.error(error_msg)
    _show_error_dialog(root, error_msg)
    _disable_auto_mode(auto_mode_var)
    return None, None, False


def _handle_error(error, root, auto_mode_var):
    """
    Handle exceptions that occur during move calculation.
    """
    error_msg = f"Stockfish error: {str(error)}"
    _show_error_dialog(root, error_msg)
    _disable_auto_mode(auto_mode_var)
    return None, None, False


def _show_error_dialog(root, message):
    """
    Show error dialog if root window is available.
    """
    if root:
        QTimer.singleShot(0, lambda: QMessageBox.critical(root, "Error", message))


def _disable_auto_mode(auto_mode_var):
    """
    Disable auto mode if the variable is available.
    """
    if auto_mode_var:
        if callable(auto_mode_var):
            root.auto_mode_var = False
            root.auto_mode_check.setChecked(False)