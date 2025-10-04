import os
import logging
from PyQt6.QtGui import QIcon
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

def set_window_icon(app):
    logo_path = resource_path(os.path.join('assets', 'logo.png'))
    if os.path.exists(logo_path):
        try:
            icon = QIcon(logo_path)
            app.setWindowIcon(icon)
            logger.debug("Window icon set successfully")
        except Exception as e:
            logger.warning(f"Failed to set window icon: {e}")
