import logging
import sys
from pathlib import Path
import os
from shutil import which

from .downloader import download_lc0

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _find_system_lc0() -> str | None:
    """Find lc0 in system PATH."""
    system_path = which("lc0")
    if system_path:
        logger.debug(f"Using system lc0 from PATH: {system_path}")
        return str(Path(system_path))
    return None


def _get_local_lc0_candidates() -> list[Path]:
    """Get list of local candidate paths for lc0 binary."""
    candidates = []
    
    # if running a frozen app, prefer the executable folder first
    if getattr(sys, 'frozen', False):
        exe_folder = Path(sys.executable).parent
        candidates.append(exe_folder / "lc0")
    
    # current working directory
    candidates.append(Path.cwd() / "lc0")
    
    # project/dev layout
    dev_base = Path(__file__).parent.parent
    candidates.append(dev_base / "lc0")
    
    return candidates


def _find_existing_candidate(candidates: list[Path]) -> str | None:
    """Check candidates and return first existing path."""
    for c in candidates:
        try:
            if c.exists():
                logger.debug(f"Found lc0 locally at: {c}")
                return str(c)
        except Exception as e:
            logger.warning(f"Could not stat candidate {c}: {e}")
    return None


def _download_lc0_with_fallback(candidates: list[Path]) -> str | None:
    """Attempt to download lc0 and check for successful installation."""
    logger.info("lc0 not found in PATH or local dirs. Attempting to download via downloader...")
    
    try:
        try:
            logger.debug("Calling download_lc0() without target...")
            res = download_lc0()
        except TypeError:
            logger.debug("download_lc0() raised TypeError; retrying without args")
            res = download_lc0()
        logger.debug("Downloader returned: %s", res)
        
        # Check if any candidate now exists after download
        found_path = _find_existing_candidate(candidates)
        if found_path:
            logger.info("lc0 installed at %s", found_path)
            return found_path
        
        # Check if downloader returned a valid path
        if res:
            returned = Path(res)
            if returned.exists():
                logger.info("Downloader returned a valid path: %s", returned)
                return str(returned)
        
        return None
        
    except Exception as e:
        logger.exception("Downloader call failed: %s", e)
        # Final check for candidates in case downloader placed binary despite exception
        found_path = _find_existing_candidate(candidates)
        if found_path:
            logger.info("lc0 appeared at %s after download attempt.", found_path)
            return found_path
        raise FileNotFoundError("lc0 not found in PATH or local dirs; downloader failed") from e


def _handle_lc0_unix() -> str:
    """Handle lc0 binary resolution on Unix-like systems."""
    # 1) prefer system PATH if available
    system_path = _find_system_lc0()
    if system_path:
        return system_path
    
    # 2) check common local locations
    candidates = _get_local_lc0_candidates()
    local_path = _find_existing_candidate(candidates)
    if local_path:
        return local_path
    
    # 3) attempt to download
    downloaded_path = _download_lc0_with_fallback(candidates)
    if downloaded_path:
        return downloaded_path
    
    raise FileNotFoundError("lc0 not found in PATH or local directories after download attempt")


def _handle_frozen_app_resources(relative_path: str) -> str:
    """Handle resource resolution for frozen applications."""
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        bundled = Path(meipass) / relative_path
        if bundled.exists():
            logger.debug(f"Using bundled resource for '{relative_path}': {bundled}")
            return str(bundled)
    
    exe_folder = Path(sys.executable).parent
    external = exe_folder / relative_path
    logger.debug(f"Using external resource for '{relative_path}': {external}")
    return str(external)


def _handle_dev_resources(relative_path: str) -> str:
    """Handle resource resolution for development layout."""
    dev_base = Path(__file__).parent.parent
    dev_path = dev_base / relative_path
    logger.debug(f"Dev resource path for '{relative_path}': {dev_path}")
    return str(dev_path)


def resource_path(relative_path: str) -> str:
    # Special handling for the lc0 binary on non-windows OSes
    if relative_path.lower() == "lc0" and os.name != "nt":
        return _handle_lc0_unix()
    
    # For frozen apps, prefer bundled resources and external next to exe
    if getattr(sys, 'frozen', False):
        return _handle_frozen_app_resources(relative_path)
    
    # Dev layout: prefer project/src relative path
    return _handle_dev_resources(relative_path)