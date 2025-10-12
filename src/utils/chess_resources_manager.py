import os
import shutil
import logging
from shutil import which
import sys
from pathlib import Path

from .downloader import download_stockfish

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

README_STOCKFISH_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/main/README.md"
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


def _get_stockfish_binary_name():
    """Returns the appropriate binary name for the current OS."""
    return "stockfish.exe" if os.name == "nt" else "stockfish"


def _check_bundled_stockfish():
    """Check if Stockfish is bundled with PyInstaller."""
    if not getattr(sys, 'frozen', False):
        return None
    
    bundled_name = _get_stockfish_binary_name()
    bundled_path = Path(sys._MEIPASS) / bundled_name
    
    if bundled_path.exists():
        logger.info(f"Using bundled Stockfish at {bundled_path}.")
        return bundled_path
    return None


def _get_working_directory():
    """Determine the appropriate working directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


def _check_system_stockfish():
    """Check if Stockfish is installed system-wide."""
    bundled_name = _get_stockfish_binary_name()
    system_path = which(bundled_name)
    
    if system_path:
        logger.info(f"Found system-installed Stockfish at {system_path}. Skipping download/extract.")
        return system_path
    return None


def _check_existing_stockfish(final_path):
    """Check if Stockfish already exists at the target location."""
    if final_path.exists():
        logger.info(f"Stockfish binary already exists at {final_path}. Skipping download.")
        return True
    return False


def _download_and_handle_stockfish(final_path):
    """Download Stockfish and handle different return value conventions."""
    logger.info(f"Stockfish not found. Attempting to download to {final_path} ...")
    
    try:
        # Try calling downloader with target path if signature accepts it
        try:
            res = download_stockfish(final_path)
        except TypeError:
            # Fallback: call without args
            logger.debug("download_stockfish() didn't accept a target path; calling without args.")
            res = download_stockfish()
        
        return _process_download_result(res, final_path)
    
    except Exception as e:
        logger.exception("Error while attempting to download Stockfish: %s", e)
        return False


def _process_download_result(res, final_path):
    """Process the result from download_stockfish() with different return conventions."""
    bundled_name = _get_stockfish_binary_name()
    
    if isinstance(res, bool):
        ok = res
    elif res is None:
        # assume downloader performed its own placement; check final_path
        ok = final_path.exists() or which(bundled_name) is not None
    else:
        ok = _handle_path_result(res, final_path)
    
    if ok:
        _set_executable_permissions(final_path)
        logger.info(f"Stockfish ready at {final_path}")
        return True
    else:
        logger.error(f"Downloader reported failure or binary not found at {final_path}. See README: {README_STOCKFISH_URL}")
        return False


def _handle_path_result(res, final_path):
    """Handle when downloader returns a path-like object."""
    try:
        returned = Path(res)
        ok = returned.exists()
        
        # if it's not at final_path, try moving it into place
        if ok and returned.resolve() != final_path.resolve():
            try:
                shutil.move(str(returned), str(final_path))
                ok = final_path.exists()
            except Exception as e:
                logger.warning("Could not move downloaded binary into place: %s", e)
        return ok
    except Exception:
        return False


def _set_executable_permissions(final_path):
    """Set executable permissions on non-Windows systems."""
    if os.name != "nt":
        try:
            st = final_path.stat().st_mode
            final_path.chmod(st | 0o111)
        except Exception as e:
            logger.warning("Failed to set executable bit: %s", e)


def extract_stockfish():
    """
    Ensures a Stockfish binary exists at ./stockfish or ./stockfish.exe in cwd.
    If missing, attempts to download via downloader.download_stockfish().
    Returns True on success (binary available), False otherwise.
    """
    logger.info("Checking for Stockfish binary...")
    
    # Check if bundled by PyInstaller
    bundled_stockfish = _check_bundled_stockfish()
    if bundled_stockfish:
        logger.info("Using bundled Stockfish")
        return True
    
    # Determine target path
    cwd = _get_working_directory()
    bundled_name = _get_stockfish_binary_name()
    final_path = cwd / bundled_name
    
    # Check if system installed
    system_stockfish = _check_system_stockfish()
    if system_stockfish:
        logger.info(f"Using system Stockfish: {system_stockfish}")
        return True
    
    # Check if already present in target location
    if _check_existing_stockfish(final_path):
        logger.info(f"Stockfish found at: {final_path}")
        return True
    
    # Download and handle result
    logger.info("Stockfish not found locally. Starting download...")
    return _download_and_handle_stockfish(final_path)


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


def setup_resources(script_dir: Path, project_dir: Path) -> bool:
    """
    Setup all required resources (Stockfish and ONNX model).
    Returns True if all resources are ready, False otherwise.
    """
    logger.info("Setting up ChessPilot resources...")
    
    if os.name != "nt":
        logger.info("Non-Windows system detected, skipping resource moves")
        # Still need to check for resources
        if not extract_stockfish():
            logger.error("Stockfish setup failed")
            return False
        if not rename_onnx_model():
            logger.error("ONNX model setup failed")
            return False
        return True
    
    # Move Stockfish binary from project root if present
    _move_resource_from_project_root(
        project_dir, script_dir, "stockfish.exe", "Stockfish binary"
    )
    
    # Ensure stockfish is present (download if missing)
    if not extract_stockfish():
        logger.error("Stockfish setup failed. Please check your internet connection.")
        return False
    
    # Move ONNX model from project root if present
    _move_resource_from_project_root(
        project_dir, script_dir, "chess_detection.onnx", "ONNX model"
    )
    
    # Ensure ONNX model is present
    if not rename_onnx_model():
        logger.error("ONNX model setup failed. Please download it manually.")
        return False
    
    logger.info("All resources ready!")
    return True


if __name__ == "__main__":
    logger.info("Starting Stockfish download check and ONNX model rename process...")
    # Default behavior: run from cwd (expected to be script_dir)
    script_dir = Path.cwd()
    project_dir = script_dir.parent
    stockfish_ok = extract_stockfish()
    onnx_ok = rename_onnx_model()
    if stockfish_ok and onnx_ok:
        logger.info("Setup complete.")
    else:
        logger.info("Setup incomplete—check errors.")
