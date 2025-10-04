import logging
import sys
from pathlib import Path
import os
from shutil import which

from .downloader import download_stockfish

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _find_system_stockfish() -> str | None:
    """Find stockfish in system PATH."""
    system_path = which("stockfish")
    if system_path:
        logger.debug(f"Using system Stockfish from PATH: {system_path}")
        return str(Path(system_path))
    return None


def _get_local_stockfish_candidates() -> list[Path]:
    """Get list of local candidate paths for stockfish binary."""
    candidates = []
    
    # if running a frozen app, prefer the executable folder first
    if getattr(sys, 'frozen', False):
        exe_folder = Path(sys.executable).parent
        candidates.append(exe_folder / "stockfish")
    
    # current working directory
    candidates.append(Path.cwd() / "stockfish")
    
    # project/dev layout
    dev_base = Path(__file__).parent.parent
    candidates.append(dev_base / "stockfish")
    
    return candidates


def _find_existing_candidate(candidates: list[Path]) -> str | None:
    """Check candidates and return first existing path."""
    for c in candidates:
        try:
            if c.exists():
                logger.debug(f"Found Stockfish locally at: {c}")
                return str(c)
        except Exception as e:
            logger.warning(f"Could not stat candidate {c}: {e}")
    return None


def _download_stockfish_with_fallback(candidates: list[Path]) -> str | None:
    """Attempt to download stockfish and check for successful installation."""
    logger.info("Stockfish not found in PATH or local dirs. Attempting to download via downloader...")
    
    try:
        try:
            logger.debug("Calling download_stockfish() without target...")
            res = download_stockfish()
        except TypeError:
            logger.debug("download_stockfish() raised TypeError; retrying without args")
            res = download_stockfish()
        logger.debug("Downloader returned: %s", res)
        
        # Check if any candidate now exists after download
        found_path = _find_existing_candidate(candidates)
        if found_path:
            logger.info("Stockfish installed at %s", found_path)
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
            logger.info("Stockfish appeared at %s after download attempt.", found_path)
            return found_path
        raise FileNotFoundError("Stockfish not found in PATH or local dirs; downloader failed") from e


def _handle_stockfish_unix() -> str:
    """Handle stockfish binary resolution on Unix-like systems."""
    # 1) prefer system PATH if available
    system_path = _find_system_stockfish()
    if system_path:
        return system_path
    
    # 2) check common local locations
    candidates = _get_local_stockfish_candidates()
    local_path = _find_existing_candidate(candidates)
    if local_path:
        return local_path
    
    # 3) attempt to download
    downloaded_path = _download_stockfish_with_fallback(candidates)
    if downloaded_path:
        return downloaded_path
    
    raise FileNotFoundError("Stockfish not found in PATH or local directories after download attempt")


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
    # Special handling for the stockfish binary on non-windows OSes
    if relative_path.lower() == "stockfish" and os.name != "nt":
        return _handle_stockfish_unix()
    
    # For frozen apps, prefer bundled resources and external next to exe
    if getattr(sys, 'frozen', False):
        return _handle_frozen_app_resources(relative_path)
    
    # Dev layout: prefer project/src relative path
    return _handle_dev_resources(relative_path)