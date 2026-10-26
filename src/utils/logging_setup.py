import os
import sys
import logging
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

COLOR_RESET = "\x1b[0m"
COLOR_RED = "\x1b[31m"
COLOR_YELLOW = "\x1b[33m"
COLOR_GREEN = "\x1b[32m"
COLOR_CYAN = "\x1b[36m"

APP_NAME = "ChessPilot"
LOG_FILENAME = "chesspilot.log"
MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5                  # Retain up to 5 previous rotated log files


class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: COLOR_CYAN,
        logging.INFO: COLOR_GREEN,
        logging.WARNING: COLOR_YELLOW,
        logging.ERROR: COLOR_RED,
        logging.CRITICAL: COLOR_RED,
    }

    def format(self, record):
        # Create a copy so other handlers (like FileHandler) aren't contaminated with ANSI codes
        record_copy = logging.makeLogRecord(record.__dict__)
        color = self.LEVEL_COLORS.get(record_copy.levelno, COLOR_RESET)
        record_copy.levelname = f"{color}{record_copy.levelname}{COLOR_RESET}"
        record_copy.msg = f"{color}{record_copy.msg}{COLOR_RESET}"
        return super().format(record_copy)


def get_log_dir() -> Path:
    """
    Get the standard OS log directory for the application.
    Windows: %LOCALAPPDATA%/ChessPilot/logs
    macOS: ~/Library/Logs/ChessPilot
    Linux/Unix: $XDG_STATE_HOME/chesspilot/logs or ~/.local/share/chesspilot/logs
    """
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_dir = Path(local_app_data) / APP_NAME
        else:
            base_dir = Path.home() / "AppData" / "Local" / APP_NAME
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Logs" / APP_NAME
    else:
        # Linux / Unix XDG standard
        xdg_state = os.environ.get("XDG_STATE_HOME")
        if xdg_state:
            base_dir = Path(xdg_state) / APP_NAME.lower()
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                base_dir = Path(xdg_data) / APP_NAME.lower()
            else:
                base_dir = Path.home() / ".local" / "share" / APP_NAME.lower()

    log_dir = base_dir / "logs"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fallback to local user home or current directory if OS path isn't writable
        try:
            fallback = Path.home() / f".{APP_NAME.lower()}" / "logs"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
        except OSError:
            fallback = Path.cwd() / "logs"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    return log_dir


def get_log_file_path() -> Path:
    """Get the full path to the primary log file."""
    return get_log_dir() / LOG_FILENAME


def setup_logging(level=logging.DEBUG) -> Path:
    """
    Setup production-grade dual logging:
    1. Rotating file handler in standard OS directory.
    2. Colorized console handler (when console stream is available).
    3. Global exception hooks to capture uncaught crashes.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate handlers on multiple calls
    if getattr(root_logger, "_chesspilot_logging_configured", False):
        return get_log_file_path()

    log_file = get_log_file_path()

    # 1. File Handler (Plain text, rotating, UTF-8)
    try:
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_fmt = "[%(asctime)s.%(msecs)03d] [%(levelname)-8s] [%(name)s] %(message)s"
        file_handler.setFormatter(logging.Formatter(file_fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        root_logger.addHandler(file_handler)
    except Exception as e:
        if sys.stderr and hasattr(sys.stderr, "write"):
            sys.stderr.write(f"Failed to setup file logging: {e}\n")

    # 2. Console Handler (Colorized, only if stderr exists and is writable)
    if sys.stderr is not None and hasattr(sys.stderr, "write"):
        try:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(level)
            console_fmt = "[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s"
            console_handler.setFormatter(ColorFormatter(console_fmt, datefmt="%H:%M:%S"))
            root_logger.addHandler(console_handler)
        except (OSError, ValueError) as err:
            root_logger.debug("Console logging initialization skipped: %s", err)

    # 3. Setup global uncaught exception hooks
    def _handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root_logger.critical(
            "Uncaught exception in main process:",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = _handle_uncaught_exception

    if hasattr(threading, "excepthook"):
        def _handle_thread_exception(args):
            if issubclass(args.exc_type, KeyboardInterrupt):
                return
            thread_name = getattr(args.thread, "name", "unknown")
            root_logger.critical(
                f"Uncaught exception in thread '{thread_name}':",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
            )

        threading.excepthook = _handle_thread_exception

    root_logger._chesspilot_logging_configured = True
    return log_file


# Backwards compatibility alias
setup_console_logging = setup_logging