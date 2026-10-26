import os
import subprocess
import shutil
import logging
import time
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

def get_config_file_path() -> str:
    """Get writable engine_config.txt path with user directory fallback."""
    root_cfg = os.path.join(get_root_dir(), "engine_config.txt")
    if os.path.exists(root_cfg):
        return root_cfg
    try:
        # Test if we can write to root dir
        test_file = os.path.join(get_root_dir(), ".test_write")
        with open(test_file, "w") as f:
            f.write("")
        os.remove(test_file)
        return root_cfg
    except (PermissionError, OSError) as err:
        logger.debug("Root directory not writable, using user config fallback: %s", err)

    # Fallback to standard user config directory
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    user_cfg_dir = os.path.join(base, "ChessPilot")
    try:
        os.makedirs(user_cfg_dir, exist_ok=True)
        return os.path.join(user_cfg_dir, "engine_config.txt")
    except OSError:
        return root_cfg

CONFIG_FILE = get_config_file_path()

def create_default_config(config_path):
    """Creates a default config file with user-friendly comments."""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
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
    except Exception as e:
        logger.warning(f"Could not create default config file at {config_path}: {e}")

def load_engine_config(stockfish_proc, config_path=None):
    """Loads Stockfish engine settings from a config file. Creates default with comments if missing."""
    if config_path is None:
        config_path = get_config_file_path()

    if not os.path.exists(config_path):
        create_default_config(config_path)

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        logger.info(f"Applying engine option: {line}")
                        stockfish_proc.stdin.write(f"{line}\n")
                    except Exception as e:
                        logger.warning(f"Failed to apply config line '{line}': {e}")
        except Exception as e:
            logger.warning(f"Could not read config file {config_path}: {e}")

    try:
        stockfish_proc.stdin.write("isready\n")
        stockfish_proc.stdin.flush()
        while True:
            line = stockfish_proc.stdout.readline()
            if not line:
                raise RuntimeError("Stockfish exited unexpectedly during isready")
            if line.strip() == "readyok":
                break
    except Exception as e:
        logger.error(f"Error during isready check: {e}")
        raise

def ensure_config_exists():
    """Ensures the config file exists, creating it if necessary."""
    cfg_path = get_config_file_path()
    if not os.path.exists(cfg_path):
        logger.warning("Config file missing, regenerating...")
        create_default_config(cfg_path)
        return True
    return False

def _initialize_stockfish():
    """Initialize a persistent Stockfish process."""
    global _stockfish_process
    
    if _stockfish_process is not None:
        if _stockfish_process.poll() is None:
            return _stockfish_process
        else:
            logger.warning("Existing Stockfish process has terminated; restarting")
            _cleanup_stockfish()
    
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

        # Standard UCI handshake
        _stockfish_process.stdin.write("uci\n")
        _stockfish_process.stdin.flush()
        while True:
            line = _stockfish_process.stdout.readline()
            if not line:
                raise RuntimeError("Stockfish process terminated during UCI handshake")
            if line.strip() == "uciok":
                break

        load_engine_config(_stockfish_process)
        
        logger.info("Stockfish process initialized")
        return _stockfish_process
        
    except Exception as e:
        logger.error(f"Failed to initialize Stockfish: {e}")
        _cleanup_stockfish()
        raise

def _cleanup_stockfish():
    """Clean up the persistent Stockfish process."""
    global _stockfish_process
    
    if _stockfish_process is not None:
        try:
            if _stockfish_process.stdin:
                try:
                    _stockfish_process.stdin.write("quit\n")
                    _stockfish_process.stdin.flush()
                except (BrokenPipeError, OSError) as err:
                    logger.debug("Engine stdin already closed during quit: %s", err)
            _stockfish_process.wait(timeout=2)
        except Exception as e:
            logger.error(f"Error terminating Stockfish process: {e}")
            try:
                _stockfish_process.kill()
            except Exception as kill_e:
                logger.debug(f"Ignored error during kill(): {kill_e}")
        finally:
            for pipe in ('stdin', 'stdout', 'stderr'):
                p = getattr(_stockfish_process, pipe, None)
                if p:
                    try:
                        p.close()
                    except Exception as close_e:
                        logger.debug(f"Ignored error closing {pipe}: {close_e}")
            _stockfish_process = None
            logger.info("Stockfish process cleaned up")

def _initialize_stockfish_at_startup():
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

def _setup_stockfish_engine():
    config_recreated = ensure_config_exists()
    stockfish = _initialize_stockfish()
    
    if config_recreated and stockfish:
        logger.info("Reloading config into existing Stockfish process")
        load_engine_config(stockfish)
    
    return stockfish

def _get_move_from_engine(stockfish, depth_var, fen, root=None, timeout_seconds=15.0):
    stockfish.stdin.write(f"position fen {fen}\n")
    stockfish.stdin.write(f"go depth {depth_var}\n")
    stockfish.stdin.flush()
    
    best_move = None
    mate_flag = False
    last_depth = 0
    start_time = time.time()
    sent_stop = False
    
    while True:
        # Prevent engine hangs by sending stop if calculation exceeds timeout
        if not sent_stop and (time.time() - start_time) > timeout_seconds:
            logger.warning(f"Engine analysis exceeded {timeout_seconds}s; requesting stop")
            try:
                stockfish.stdin.write("stop\n")
                stockfish.stdin.flush()
                sent_stop = True
            except Exception as e:
                logger.error(f"Failed to send stop command: {e}")

        line = stockfish.stdout.readline()
        if not line:
            logger.error("Stockfish exited before sending bestmove")
            break
            
        logger.debug(f"Engine output: {line.strip()}")
        
        if "info depth" in line and root and hasattr(root, 'update_status'):
            try:
                depth_part = line.split("info depth")[1].split()[0]
                current_depth = int(depth_part)
                if current_depth > last_depth:
                    last_depth = current_depth
                    root.update_status(f"Processing... Depth {current_depth}/{depth_var}")
            except (IndexError, ValueError) as err:
                logger.debug("Could not parse depth from engine output line: %s", err)
        
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
        if abs(mate_val) <= 1:
            logger.info(f"Mate detected (score mate {mate_val})")
            return True
    except (IndexError, ValueError):
        logger.warning("Could not parse mate score")
    
    return current_mate_flag

def _extract_best_move(line):
    if line.startswith("bestmove"):
        parts = line.strip().split()
        if len(parts) > 1:
            return parts[1]
    return None

def _get_updated_fen(stockfish, original_fen, best_move):
    if not best_move or best_move == "(none)":
        return None
    
    try:
        stockfish.stdin.write(f"position fen {original_fen} moves {best_move}\n")
        stockfish.stdin.write("d\n")
        stockfish.stdin.flush()
        
        updated_fen = None
        while True:
            line = stockfish.stdout.readline()
            if not line:
                break
                
            logger.debug(f"Engine output for new FEN: {line.strip()}")
            
            if "Fen:" in line:
                updated_fen = line.split("Fen:")[1].strip()
                logger.info(f"Updated FEN: {updated_fen}")
            elif line.startswith("Checkers:"):
                # "Checkers:" marks end of 'd' board display in Stockfish
                break
        
        # Keep pipe synchronized with readyok
        stockfish.stdin.write("isready\n")
        stockfish.stdin.flush()
        while True:
            line = stockfish.stdout.readline()
            if not line or line.strip() == "readyok":
                break

        return updated_fen
    except Exception as e:
        logger.error(f"Error querying updated FEN: {e}")
        return None

def _handle_stockfish_failure(error_msg, root, auto_mode_var):
    logger.error(error_msg)
    _show_error_dialog(root, error_msg)
    _disable_auto_mode(auto_mode_var, root)
    return None, None, False

def _handle_error(error, root, auto_mode_var):
    error_msg = f"Stockfish error: {str(error)}"
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
        return _initialize_stockfish_at_startup()

    @staticmethod
    def cleanup():
        logger.info("Cleaning up engine service")
        _cleanup_stockfish()

    @staticmethod
    def get_best_move(depth: int, fen: str, root=None, auto_mode_var=None):
        logger.debug(f"Querying best move for FEN: {fen} at depth {depth}")
        try:
            logger.info("Getting best move from Stockfish")
            
            if root and hasattr(root, 'update_status'):
                root.update_status("Processing... Stockfish is thinking...")
            
            stockfish = _setup_stockfish_engine()
            if stockfish is None:
                return _handle_stockfish_failure("Failed to initialize Stockfish", root, auto_mode_var)
            
            best_move, mate_flag = _get_move_from_engine(stockfish, depth, fen, root)
            if best_move is None or best_move == "(none)":
                if best_move == "(none)":
                    logger.info("Stockfish returned (none) - game over (checkmate or stalemate)")
                    return "(none)", None, mate_flag
                return _handle_stockfish_failure(
                    "Stockfish did not respond. Please download the correct version according to your CPU architecture.",
                    root, auto_mode_var
                )
            
            if root and hasattr(root, 'update_status'):
                root.update_status(f"Best move found: {best_move}")
            
            updated_fen = _get_updated_fen(stockfish, fen, best_move)
            return best_move, updated_fen, mate_flag

        except Exception as e:
            logger.error(f"Stockfish error: {str(e)}")
            _cleanup_stockfish()
            return _handle_error(e, root, auto_mode_var)

