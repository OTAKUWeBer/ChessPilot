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

# Global Lc0 process
_lc0_process = None

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

        f.write("# Lc0 specific optimizations\n")
        f.write("# Backend to use (e.g. opencl, cuda, or dnnl)\n")
        f.write("# setoption name Backend value dnnl\n")
    
    logger.info(f"Created default config file at {config_path}")

def load_engine_config(lc0_proc, config_path=CONFIG_FILE):
    """Loads Lc0 engine settings from a config file. Creates default with comments if missing."""
    if not os.path.exists(config_path):
        create_default_config(config_path)

    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                logger.info(f"Applying engine option: {line}")
                lc0_proc.stdin.write(f"{line}\n")
            except Exception as e:
                logger.warning(f"Failed to apply config line '{line}': {e}")
                
    # Add Maia weights option securely
    weights_path = resource_path("maia-1500.pb.gz")
    lc0_proc.stdin.write(f"setoption name WeightsFile value {weights_path}\n")


    lc0_proc.stdin.write("isready\n")
    lc0_proc.stdin.flush()
    while True:
        if lc0_proc.stdout.readline().strip() == "readyok":
            break

def ensure_config_exists():
    """Ensures the config file exists, creating it if necessary."""
    if not os.path.exists(CONFIG_FILE):
        logger.warning("Config file missing during gameplay, regenerating...")
        create_default_config(CONFIG_FILE)
        return True
    return False

def _initialize_lc0():
    """Initialize a persistent Lc0 process."""
    global _lc0_process
    
    if _lc0_process is not None:
        return _lc0_process
    
    try:
        lc0_path = resource_path("lc0.exe" if os.name == "nt" else "lc0")
        
        if os.name != "nt" and not os.path.exists(lc0_path):
            sys_stock = shutil.which("lc0")
            if sys_stock:
                logger.debug(f"Falling back to system Lc0 at {sys_stock}")
                lc0_path = sys_stock
                
        if not os.path.exists(lc0_path) and shutil.which(lc0_path) is None:
            raise FileNotFoundError(f"Lc0 not found at {lc0_path}")
        
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        logger.debug(f"Using Lc0 path: {lc0_path}")
        
        _lc0_process = subprocess.Popen(
            [lc0_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=flags
        )

        load_engine_config(_lc0_process)
        
        logger.info("Lc0 process initialized")
        return _lc0_process
        
    except Exception as e:
        logger.error(f"Failed to initialize Lc0: {e}")
        _lc0_process = None
        raise

def _cleanup_lc0():
    """Clean up the persistent Lc0 process."""
    global _lc0_process
    
    if _lc0_process is not None:
        try:
            if _lc0_process.stdin:
                try:
                    _lc0_process.stdin.write("quit\n")
                    _lc0_process.stdin.flush()
                except BrokenPipeError:
                    pass
            _lc0_process.wait(timeout=2)
        except Exception as e:
            logger.error(f"Error terminating Lc0 process: {e}")
            try:
                _lc0_process.terminate()
            except Exception as term_e:
                logger.debug(f"Ignored error during terminate(): {term_e}")
        finally:
            # Explicitly close pipes to prevent "Exception ignored" during GC
            for pipe in ('stdin', 'stdout', 'stderr'):
                p = getattr(_lc0_process, pipe, None)
                if p:
                    try:
                        p.close()
                    except Exception as close_e:
                        logger.debug(f"Ignored error closing {pipe}: {close_e}")
            _lc0_process = None
            logger.info("Lc0 process cleaned up")

def _initialize_lc0_at_startup():
    """Initialize Lc0 at application startup."""
    try:
        logger.info("Initializing Lc0 at application startup...")
        lc0_process = _initialize_lc0()
        if lc0_process:
            logger.info("Lc0 successfully initialized with config settings")
            return True
        else:
            logger.error("Failed to initialize Lc0 at startup")
            return False
    except Exception as e:
        logger.error(f"Error initializing Lc0 at startup: {e}")
        return False

def _setup_lc0_engine():
    config_recreated = ensure_config_exists()
    lc0 = _initialize_lc0()
    
    if config_recreated and lc0:
        logger.info("Reloading config into existing Lc0 process")
        load_engine_config(lc0)
    
    return lc0

def _get_move_from_engine(lc0, depth_var, fen, root=None):
    lc0.stdin.write(f"position fen {fen}\n")
    lc0.stdin.write(f"go depth {depth_var}\n")
    lc0.stdin.flush()
    
    best_move = None
    mate_flag = False
    last_depth = 0
    
    while True:
        line = lc0.stdout.readline()
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
    if line.startswith("bestmove"):
        return line.strip().split()[1]
    return None

def _get_updated_fen(lc0, original_fen, best_move):
    if not best_move:
        return None
    
    lc0.stdin.write(f"position fen {original_fen} moves {best_move}\n")
    lc0.stdin.write("d\n")
    lc0.stdin.flush()
    
    while True:
        line = lc0.stdout.readline()
        if not line:
            break
            
        logger.debug(f"Engine output for new FEN: {line.strip()}")
        
        if "Fen:" in line:
            updated_fen = line.split("Fen:")[1].strip()
            logger.info(f"Updated FEN: {updated_fen}")
            return updated_fen
    
    return None

def _handle_lc0_failure(error_msg, root, auto_mode_var):
    logger.error(error_msg)
    _show_error_dialog(root, error_msg)
    _disable_auto_mode(auto_mode_var, root)
    return None, None, False

def _handle_error(error, root, auto_mode_var):
    error_msg = f"Lc0 error: {str(error)}"
    _show_error_dialog(root, error_msg)
    _disable_auto_mode(auto_mode_var, root)
    return None, None, False

def _show_error_dialog(root, message):
    if root:
        QTimer.singleShot(0, lambda: QMessageBox.critical(root, "Error", message))

def _disable_auto_mode(auto_mode_var, root):
    if auto_mode_var and root:
        if callable(auto_mode_var):
            root.auto_mode_var = False
            if hasattr(root, 'auto_mode_check'):
                root.auto_mode_check.setChecked(False)

class EngineService:
    @staticmethod
    def initialize():
        logger.info("Initializing engine service")
        return _initialize_lc0_at_startup()

    @staticmethod
    def cleanup():
        logger.info("Cleaning up engine service")
        _cleanup_lc0()

    @staticmethod
    def get_best_move(depth: int, fen: str, root=None, auto_mode_var=None):
        logger.debug(f"Querying best move for FEN: {fen} at depth {depth}")
        try:
            logger.info("Getting best move from Lc0")
            
            if root and hasattr(root, 'update_status'):
                root.update_status("Processing... Lc0 is thinking...")
            
            lc0 = _setup_lc0_engine()
            if lc0 is None:
                return _handle_lc0_failure("Failed to initialize Lc0", root, auto_mode_var)
            
            best_move, mate_flag = _get_move_from_engine(lc0, depth, fen, root)
            if best_move is None:
                return _handle_lc0_failure(
                    "Lc0 did not respond. Please download the correct version according to your CPU architecture.",
                    root, auto_mode_var
                )
            
            if root and hasattr(root, 'update_status'):
                root.update_status(f"Best move found: {best_move}")
            
            updated_fen = _get_updated_fen(lc0, fen, best_move)
            return best_move, updated_fen, mate_flag

        except Exception as e:
            logger.error(f"Lc0 error: {str(e)}")
            _cleanup_lc0()
            return _handle_error(e, root, auto_mode_var)
