import os
import shutil
import logging
from shutil import which
import sys
from pathlib import Path

from .downloader import download_maia, download_lc0

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

README_ENGINE_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/main/README.md"
README_ONNX_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/main/README.md"

def find_file_with_keyword(keyword, extension=None, search_path=None):
    """
    Finds the first file in `search_path` containing the keyword in its name
    and optionally matching extension.
    Falls back to current working directory if `search_path` is not provided.
    """
    base_path = Path(search_path or Path.cwd())
    logger.debug(f"Searching for files with keyword '{keyword}' and extension '{extension}' in {base_path}")
    try:
        for file in base_path.iterdir():
            if keyword.lower() in file.name.lower():
                if extension:
                    if file.suffix.lower() == extension.lower():
                        logger.debug(f"Found file: {file}")
                        return file
                else:
                    logger.debug(f"Found file: {file}")
                    return file
    except Exception as e:
        logger.debug(f"Error while scanning {base_path}: {e}")
    logger.debug("No matching file found.")
    return None


def _get_working_directory():
    """Determine the appropriate working directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


def _check_bundled_onnx():
    """Check if ONNX model is bundled with PyInstaller."""
    if not getattr(sys, 'frozen', False):
        return None
    
    target_name = "chess_detection.onnx"
    bundled = Path(sys._MEIPASS) / target_name
    
    if bundled.exists():
        logger.info(f"Using bundled ONNX model at {bundled}.")
        return bundled
    
    logger.error(f"ONNX model expected in bundle but not found at {bundled}.")
    return False


def _find_onnx_model(cwd, target_path):
    """Find ONNX model in current directory or parent."""
    if target_path.exists():
        logger.info(f"ONNX model already exists at {target_path}. Skipping rename.")
        return target_path
    
    # Search in current directory first, then parent
    onnx_file = find_file_with_keyword("chess_detection", ".onnx", search_path=cwd)
    if not onnx_file:
        onnx_file = find_file_with_keyword("chess_detection", ".onnx", search_path=cwd.parent)
    
    return onnx_file


def _move_onnx_model(onnx_file, target_path):
    """Move ONNX model to target location."""
    try:
        shutil.move(str(onnx_file), str(target_path))
        logger.info(f"ONNX model moved to {target_path}")
        return True
    except Exception as e:
        logger.exception("Failed to move ONNX model: %s", e)
        return False


def rename_onnx_model():
    """
    Ensures chess_detection.onnx lives in cwd. Searches cwd first, then parent dir.
    """
    logger.info("Checking for ONNX model...")
    
    cwd = Path.cwd()
    target_name = "chess_detection.onnx"
    target_path = cwd / target_name
    
    # Check if bundled
    bundled_result = _check_bundled_onnx()
    if bundled_result is True:
        logger.info("Using bundled ONNX model")
        return True
    elif bundled_result is False:
        logger.error("ONNX model missing from bundle")
        return False
    
    # Find ONNX model
    onnx_file = _find_onnx_model(cwd, target_path)
    if onnx_file == target_path:  # Already exists at target
        logger.info(f"ONNX model found at: {target_path}")
        return True
    
    if not onnx_file:
        logger.error(
            f"ONNX model not found. Please download it from: {README_ONNX_URL}"
        )
        return False
    
    # Move to target location
    logger.info(f"Moving ONNX model to: {target_path}")
    return _move_onnx_model(onnx_file, target_path)


def _move_resource_from_project_root(project_dir, script_dir, filename, resource_type):
    """Generic function to move resources from project root to script directory."""
    root_file = project_dir / filename
    src_file = script_dir / filename
    
    if root_file.exists() and not src_file.exists():
        try:
            shutil.move(str(root_file), str(src_file))
            logger.info(f"Moved {resource_type} from project root into src/: {src_file}")
        except Exception as e:
            logger.warning(f"Could not move {resource_type} from project root to src: %s", e)


def _get_engine_binary_names():
    """Returns the appropriate binary names for both Lc0 and Maia."""
    if os.name == "nt":
        return {"lc0": "lc0.exe", "maia": "maia.exe"}
    else:
        return {"lc0": "lc0", "maia": "maia"}


def _check_bundled_engines():
    """Check if Lc0 or Maia is bundled with PyInstaller."""
    if not getattr(sys, 'frozen', False):
        return None
    
    engine_names = _get_engine_binary_names()
    for engine_type, binary_name in engine_names.items():
        bundled_path = Path(sys._MEIPASS) / binary_name
        if bundled_path.exists():
            logger.info(f"Using bundled {engine_type.upper()} at {bundled_path}.")
            return bundled_path
    return None


def _check_system_engines():
    """Check if Lc0 or Maia is installed system-wide."""
    engine_names = _get_engine_binary_names()
    for engine_type, binary_name in engine_names.items():
        system_path = which(binary_name)
        if system_path:
            logger.info(f"Found system-installed {engine_type.upper()} at {system_path}.")
            return system_path
    return None


def _check_existing_engines(final_dir):
    """Check if Lc0 or Maia already exists in the target directory."""
    engine_names = _get_engine_binary_names()
    for engine_type, binary_name in engine_names.items():
        engine_path = final_dir / binary_name
        if engine_path.exists():
            logger.info(f"{engine_type.upper()} binary already exists at {engine_path}.")
            return engine_path
    return None


def extract_engines():
    """
    Ensures Lc0 or Maia binary exists. If missing, attempts auto-download.
    For Linux, skips Lc0 (requires building from source) and goes straight to Maia.
    Returns True on success (engine available), False otherwise.
    """
    logger.info("Checking for Lc0 or Maia engine binary...")
    
    # Check if bundled by PyInstaller
    bundled_engine = _check_bundled_engines()
    if bundled_engine:
        logger.info("Using bundled engine")
        return True
    
    # Determine target path
    cwd = _get_working_directory()
    
    # Check if system installed
    system_engine = _check_system_engines()
    if system_engine:
        logger.info(f"Using system engine: {system_engine}")
        return True
    
    # Check if already present in target location
    existing_engine = _check_existing_engines(cwd)
    if existing_engine:
        logger.info(f"Engine found at: {existing_engine}")
        return True
    
    logger.info("Engine not found. Attempting auto-download...")
    
    import platform
    os_type = platform.system().lower()
    
    if os_type != "linux":
        # Try downloading Lc0 first on non-Linux systems
        logger.info("Attempting to download Lc0...")
        if download_lc0():
            logger.info("Lc0 downloaded successfully")
            return True
    else:
        logger.info("Linux detected - Lc0 requires building from source, skipping auto-download")
        logger.warning("Lc0 on Linux: https://github.com/LeelaChessZero/lc0/releases (requires building from source)")
    
    # Try downloading Maia (works on all platforms)
    logger.info("Attempting to download Maia...")
    if download_maia():
        logger.info("Maia downloaded successfully")
        return True
    
    # If both fail, log instructions
    logger.error("Auto-download failed. Please manually download:")
    if os_type != "linux":
        logger.warning("  Lc0: https://github.com/LeelaChessZero/lc0/releases")
    else:
        logger.warning("  Lc0 (Linux): https://github.com/LeelaChessZero/lc0/releases (requires building from source)")
    logger.warning("  Maia: https://github.com/CSSLab/maia-chess/releases")
    return False


def setup_resources(script_dir: Path, project_dir: Path) -> bool:
    """
    Setup all required resources (Lc0/Maia engine and ONNX model).
    Returns True if all resources are ready, False otherwise.
    """
    logger.info("Setting up ChessPilot resources...")
    
    if not extract_engines():
        logger.error("Engine setup failed")
        return False
    if not rename_onnx_model():
        logger.error("ONNX model setup failed")
        return False
    
    logger.info("All resources ready!")
    return True


if __name__ == "__main__":
    logger.info("Starting engine setup check...")
    # Default behavior: run from cwd (expected to be script_dir)
    script_dir = Path.cwd()
    project_dir = script_dir.parent
    engine_ok = extract_engines()
    onnx_ok = rename_onnx_model()
    if engine_ok and onnx_ok:
        logger.info("Setup complete.")
    else:
        logger.info("Setup incomplete—check errors.")
