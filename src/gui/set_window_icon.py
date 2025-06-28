import os
import logging
from PIL import Image, ImageTk
from utils.resource_path import resource_path

# Logger setup
logger = logging.getLogger(__name__)

def set_window_icon(app):
    logo_path = resource_path(os.path.join('assets', 'logo.png'))
    if os.path.exists(logo_path):
        try:
            img = Image.open(logo_path)
            app.icon = ImageTk.PhotoImage(img)
            app.root.iconphoto(False, app.icon)
            logger.debug("Window icon set successfully")
        except Exception as e:
            logger.warning(f"Failed to set window icon: {e}")