import logging
import sys
import os
import shutil
from tkinter import messagebox

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_binary_path(binary):
    logger.debug(f"Resolving binary path for: {binary}")
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
        logger.error(f"Missing binary: {binary}")
        messagebox.showerror("Error", f"{binary} is missing! Make sure it's bundled properly.")
        sys.exit(1)
    logger.debug(f"Binary path resolved: {path}")
    return path