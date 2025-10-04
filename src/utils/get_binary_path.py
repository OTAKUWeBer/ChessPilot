import logging
import sys
import os
import shutil
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_binary_path(binary):
    logger.debug(f"Resolving binary path for: {binary}")
    if os.name == "nt" and not binary.endswith(".exe"):
        binary += ".exe"

    if getattr(sys, 'frozen', False):
        path = os.path.join(sys._MEIPASS, binary)
    else:
        path = shutil.which(binary)
        if path is None:
            path = binary

    if not (path and os.path.exists(path)):
        logger.error(f"Missing binary: {binary}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(f"{binary} is missing! Make sure it's bundled properly.")
        msg.setWindowTitle("Error")
        msg.exec()
        sys.exit(1)
    logger.debug(f"Binary path resolved: {path}")
    return path