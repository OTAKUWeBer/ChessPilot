import logging
import sys
from pathlib import Path
import os
from shutil import which

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _find_system_engines() -> str | None:
    """Find Lc0 or Maia in system PATH."""
    for engine_name in ["lc0", "maia"]:
        system_path = which(engine_name)
        if system_path:
            logger.debug(f"Using system {engine_name.upper()} from PATH: {system_path}")
            return str(Path(system_path))
    return None


def _get_local_engine_candidates() -> list[Path]:
    """Get list of local candidate paths for engine binaries."""
    candidates = []
    
    # if running a frozen app, prefer the executable folder first
    if getattr(sys, 'frozen', False):
        exe_folder = Path(sys.executable).parent
        for engine_name in ["lc0", "maia"]:
            candidates.append(exe_folder / engine_name)
    
    # current working directory
    for engine_name in ["lc0", "maia"]:
        candidates.append(Path.cwd() / engine_name)
    
    # project/dev layout
    dev_base = Path(__file__).parent.parent
    for engine_name in ["lc0", "maia"]:
        candidates.append(dev_base / engine_name)
    
    return candidates


def _find_existing_candidate(candidates: list[Path]) -> str | None:
    """Check candidates and return first existing engine path."""
    for c in candidates:
        try:
            if c.exists():
                logger.debug(f"Found engine locally at: {c}")
                return str(c)
        except Exception as e:
            logger.warning(f"Could not stat candidate {c}: {e}")
    return None


def _handle_engines_unix() -> str:
    """Handle engine binary resolution on Unix-like systems."""
    # 1) prefer system PATH if available
    system_path = _find_system_engines()
    if system_path:
        return system_path
    
    # 2) check common local locations
    candidates = _get_local_engine_candidates()
    local_path = _find_existing_candidate(candidates)
    if local_path:
        return local_path
    
    raise FileNotFoundError("Neither Lc0 nor Maia found in PATH or local directories")


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
    # Special handling for engine binaries on non-windows OSes
    if relative_path.lower() in ["lc0", "maia"] and os.name != "nt":
        return _handle_engines_unix()
    
    # For frozen apps, prefer bundled resources and external next to exe
    if getattr(sys, 'frozen', False):
        return _handle_frozen_app_resources(relative_path)
    
    # Dev layout: prefer project/src relative path
    return _handle_dev_resources(relative_path)
