import mss
from PIL import Image
import io
from .is_wayland import is_wayland
import subprocess
from tkinter import messagebox
import logging
from utils.get_binary_path import get_binary_path

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def capture_screenshot_in_memory(root=None, auto_mode_var=None):
    grim_path = get_binary_path("grim") if is_wayland() else None
    try:
        if is_wayland():
            logger.info("Capturing screenshot using grim (Wayland)...")
            result = subprocess.run([grim_path, "-"], stdout=subprocess.PIPE, check=True)
            image = Image.open(io.BytesIO(result.stdout))
        else:
            logger.info("Capturing screenshot using mss (non-Wayland)...")
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                image = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        logger.debug("Screenshot captured successfully")
        return image
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        if root:
            root.after(0, lambda err=e: messagebox.showerror("Error", f"Screenshot failed: {str(err)}"))
        if auto_mode_var:
            auto_mode_var.set(False)
        return None
