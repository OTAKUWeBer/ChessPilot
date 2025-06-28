import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        # 1) bundled in one‑file?
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            bundled = Path(meipass) / relative_path
            if bundled.exists():
                logger.debug(f"Using bundled resource for '{relative_path}': {bundled}")
                return str(bundled)
        # 2) otherwise, external beside the exe
        exe_folder = Path(sys.executable).parent
        external = exe_folder / relative_path
        logger.debug(f"Using external resource for '{relative_path}': {external}")
        return str(external)

    # Development mode: look in src/
    dev_base = Path(__file__).parent.parent
    dev_path = dev_base / relative_path
    logger.debug(f"Dev resource path for '{relative_path}': {dev_path}")
    return str(dev_path)
