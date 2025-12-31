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

# Global engine process (Lc0 or Maia)
_engine_process = None
# Engine selection: 'lc0' or 'maia'
_current_engine = 'lc0'

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

        f.write("# Engine selection: lc0 or maia\n")
        f.write("engine = lc0\n\n")

        f.write("# For Lc0: Network file to use (if applicable)\n")
        f.write("# setoption name Network value <network_file>\n\n")

        f.write("# For both engines: Number of playouts per move\n")
        f.write("# setoption name Visits value 1000\n")
    
    logger.info(f"Created default config file at {config_path}")

def load_engine_config(engine_proc, config_path=CONFIG_FILE):
    """Loads engine settings from a config file. Creates default with comments if missing."""
    
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
                engine_proc.stdin.write(f"{line}\n")
            except Exception as e:
                logger.warning(f"Failed to apply config line '{line}': {e}")

    engine_proc.stdin.write("isready\n")
    engine_proc.stdin.flush()
    while True:
        if engine_proc.stdout.readline().strip() == "readyok":
            break

def ensure_config_exists():
    """Ensures the config file exists, creating it if necessary."""
    if not os.path.exists(CONFIG_FILE):
        logger.warning("Config file missing during gameplay, regenerating...")
        create_default_config(CONFIG_FILE)
        return True  # Indicates config was recreated
    return False  # Config already exists

def _initialize_engine():
    """Initialize a persistent Lc0 or Maia process."""
    global _engine_process
    
    if _engine_process is not None:
        return _engine_process
    
    try:
        engine_path = None
        
        # Try Lc0
        lc0_path = resource_path("lc0.exe" if os.name == "nt" else "lc0")
        if os.path.exists(lc0_path) or shutil.which("lc0"):
            engine_path = lc0_path if os.path.exists(lc0_path) else shutil.which("lc0")
            logger.info(f"Found Lc0 at {engine_path}")
        else:
            # Try Maia
            maia_path = resource_path("maia.exe" if os.name == "nt" else "maia")
            if os.path.exists(maia_path) or shutil.which("maia"):
                engine_path = maia_path if os.path.exists(maia_path) else shutil.which("maia")
                logger.info(f"Found Maia at {engine_path}")
        
        if engine_path is None:
            raise FileNotFoundError("Neither Lc0 nor Maia found in PATH or local directories")
        
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        logger.debug(f"Using engine path: {engine_path}")
        
        _engine_process = subprocess.Popen(
            [engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=flags
        )

        # Load custom engine config
        load_engine_config(_engine_process)
        
        logger.info("Engine process initialized")
        return _engine_process
        
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}")
        _engine_process = None
        raise

def cleanup_engine():
    """Clean up the persistent engine process."""
    global _engine_process
    
    if _engine_process is not None:
        try:
            _engine_process.stdin.write("quit\n")
            _engine_process.stdin.flush()
            _engine_process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error terminating engine process: {e}")
            _engine_process.terminate()
        finally:
            _engine_process = None
            logger.info("Engine process cleaned up")

def initialize_engine_at_startup():
    """Initialize engine at application startup."""
    try:
        logger.info("Initializing engine at application startup...")
        engine_process = _initialize_engine()
        if engine_process:
            logger.info("Engine successfully initialized with config settings")
            return True
        else:
            logger.error("Failed to initialize engine at startup")
            return False
    except Exception as e:
        logger.error(f"Error initializing engine at startup: {e}")
        return False

def get_best_move(depth_var, fen, root=None, auto_mode_var=None):
    """
    Main function to get the best move from the engine (Lc0 or Maia).
    Complexity reduced by breaking into smaller functions.
    """
    try:
        logger.info("Getting best move from engine")
        
        if root and hasattr(root, 'update_status'):
            root.update_status("Processing... Engine is thinking...")
        
        engine = _setup_engine()
        if engine is None:
            return _handle_engine_failure("Failed to initialize engine", root, auto_mode_var)
        
        best_move, mate_flag = _get_move_from_engine(engine, depth_var, fen, root)
        if best_move is None:
            return _handle_engine_failure(
                "Engine did not respond. Please ensure Lc0 or Maia is installed correctly.",
                root, auto_mode_var
            )
        
        if root and hasattr(root, 'update_status'):
            root.update_status(f"Best move found: {best_move}")
        
        updated_fen = _get_updated_fen(engine, fen, best_move)
        return best_move, updated_fen, mate_flag

    except Exception as e:
        logger.error(f"Engine error: {str(e)}")
        cleanup_engine()
        return _handle_error(e, root, auto_mode_var)


def _setup_engine():
    """
    Initialize engine and handle configuration.
    """
    config_recreated = ensure_config_exists()
    engine = _initialize_engine()
    
    if config_recreated and engine:
        logger.info("Reloading config into existing engine process")
        load_engine_config(engine)
    
    return engine


def _get_move_from_engine(engine, depth_var, fen, root=None):
    """
    Send position and depth to engine, parse response for best move and mate detection.
    """
    engine.stdin.write(f"position fen {fen}\n")
    engine.stdin.write(f"go depth {depth_var}\n")
    engine.stdin.flush()
    
    best_move = None
    mate_flag = False
    last_depth = 0
    
    while True:
        line = engine.stdout.readline()
        if not line:
            break
            
        logger.debug(f"Engine output: {line.strip()}")
        
        if "info depth" in line and root and hasattr(root, 'update_status'):
            try:
                depth_part = line.split("info depth")[1].split()[0]
                current_depth = int(depth_part)
                if current_depth > last_depth:
                    last_depth = current_depth
                    root.update_status(f"Processing... Depth {current_depth}/{depth_var}")
            except (IndexError, ValueError):
                pass
        
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


def _get_updated_fen(engine, original_fen, best_move):
    """
    Get the updated FEN position after making the best move.
    """
    if not best_move:
        return None
    
    engine.stdin.write(f"position fen {original_fen} moves {best_move}\n")
    engine.stdin.write("d\n")
    engine.stdin.flush()
    
    while True:
        line = engine.stdout.readline()
        if not line:
            break
            
        logger.debug(f"Engine output for new FEN: {line.strip()}")
        
        if "Fen:" in line:
            updated_fen = line.split("Fen:")[1].strip()
            logger.info(f"Updated FEN: {updated_fen}")
            return updated_fen
    
    return None


def _handle_engine_failure(error_msg, root, auto_mode_var):
    """
    Handle cases where engine fails to initialize or respond.
    """
    logger.error(error_msg)
    _show_error_dialog(root, error_msg)
    _disable_auto_mode(auto_mode_var)
    return None, None, False


def _handle_error(error, root, auto_mode_var):
    """
    Handle exceptions that occur during move calculation.
    """
    error_msg = f"Engine error: {str(error)}"
    _show_error_dialog(root, error_msg)
    _disable_auto_mode(auto_mode_var)
    return None, None, False


def _show_error_dialog(root, message):
    """
    Show error dialog if root window is available.
    """
    if root:
        QTimer.singleShot(0, lambda: QMessageBox.critical(root, "Error", message))


def _disable_auto_mode(auto_mode_var, root):
    """
    Disable auto mode if the variable is available.
    """
    if auto_mode_var:
        if callable(auto_mode_var):
            root.auto_mode_var = False
            root.auto_mode_check.setChecked(False)
