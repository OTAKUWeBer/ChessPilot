import logging
import sys
import os
import shutil
from pathlib import Path
from tkinter import messagebox

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_binary_path(binary):
    logger.debug(f"Resolving binary path for: {binary}")

    # On Windows, ensure the name ends with '.exe'
    if os.name == "nt" and not binary.lower().endswith(".exe"):
        binary += ".exe"

    # If frozen, first check the bundle and then the exe directory
    if getattr(sys, 'frozen', False):
        # 1) Bundled in _MEIPASS
        bundle_path = Path(sys._MEIPASS) / binary
        if bundle_path.exists():
            logger.debug(f"Found bundled binary in _MEIPASS: {bundle_path}")
            return str(bundle_path)

        # 2) Sitting next to your .exe
        exe_dir = Path(sys.executable).parent
        local_path = exe_dir / binary
        if local_path.exists():
            logger.debug(f"Found binary next to exe: {local_path}")
            return str(local_path)

    # Non-frozen or not found above: try system PATH
    path = shutil.which(binary)
    if path:
        logger.debug(f"Found binary on PATH: {path}")
        return path

    # As a last resort, assume it's in cwd or in PATH by name
    fallback = binary
    if Path(fallback).exists():
        logger.debug(f"Found binary in cwd: {fallback}")
        return fallback

    # Nothing found: show error and exit
    logger.error(f"Missing binary: {binary}")
    messagebox.showerror("Error", f"{binary} is missing! Make sure it's bundled properly.")
    sys.exit(1)
