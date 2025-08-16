import os
import zipfile
import glob
from pathlib import Path
import shutil
import logging
from shutil import which
import sys

from .downloader import download_lc0

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

README_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/maia-support/README.md"


def find_file_with_keyword(keyword, extension=None, search_path=None):
    """
    Finds the first file in search_path containing the keyword in its name
    and optionally matching extension.
    """
    base_path = Path(search_path or Path.cwd())
    logger.debug(f"Searching for files with keyword '{keyword}' and extension '{extension}' in {base_path}")
    for file in base_path.iterdir():
        if keyword.lower() in file.name.lower():
            if extension:
                if file.suffix.lower() == extension.lower():
                    logger.debug(f"Found file: {file}")
                    return file
            else:
                logger.debug(f"Found file: {file}")
                return file
    logger.debug("No matching file found.")
    return None


def download_lc0_if_needed():
    """
    Downloads LC0 using the downloader if not found locally.

    Minimal change: On Linux we do NOT attempt to auto-download. Instead we
    tell the user to install via package manager or build from source.
    """
    # If running on Linux, do not try to auto-download — prefer package manager / source.
    if sys.platform.startswith("linux"):
        logger.info("Detected Linux. Please install lc0 using your distribution's package manager (e.g. apt, pacman) or build from source.")
        logger.info(f"See {README_URL} for details.")
        return False

    try:
        logger.info("LC0 not found locally. Starting download...")
        download_lc0()
        return True
    except ImportError:
        logger.error("LC0 downloader not available. Please download LC0 manually.")
        return False
    except Exception as e:
        logger.error(f"Failed to download LC0: {e}")
        return False


def extract_lc0():
    """
    Ensures an LC0 binary exists at ./lc0 or ./lc0.exe in cwd.
    Extracts from ZIP in cwd if needed, including DLL on Windows.
    If not found, attempts to download using the downloader.

    Minimal change: for Linux we won't attempt to download; just show a message.
    """
    if getattr(sys, 'frozen', False):
        bundled_name = "lc0.exe" if os.name == "nt" else "lc0"
        bundled_path = Path(sys._MEIPASS) / bundled_name
        if bundled_path.exists():
            logger.info(f"Using bundled LC0 at {bundled_path}.")
            return True

    target_name = "lc0.exe" if os.name == "nt" else "lc0"
    cwd = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    final_path = cwd / target_name

    if which(target_name):
        logger.info("Found system-installed LC0. Skipping extraction.")
        return True
    if final_path.exists():
        logger.info(f"LC0 binary already exists at {final_path}. Skipping extraction.")
        return True

    zip_path = find_file_with_keyword("lc0", ".zip", search_path=cwd)
    if not zip_path:
        logger.warning(f"No LC0 ZIP found in {cwd}.")

        # Minimal change: on Linux, don't attempt to download automatically.
        if sys.platform.startswith("linux"):
            logger.info("On Linux, please install lc0 through your package manager (e.g. `sudo apt install lc0`, `sudo pacman -S lc0`) or build from source.")
            logger.info(f"See {README_URL} for build instructions and downloads.")
            return False

        logger.warning("Attempting to download (non-Linux platforms only)...")
        if not download_lc0_if_needed():
            logger.error(f"Failed to download LC0. See README: {README_URL}")
            return False
        
        # Check again after download
        zip_path = find_file_with_keyword("lc0", ".zip", search_path=cwd)
        if not zip_path and final_path.exists():
            logger.info("LC0 binary downloaded successfully.")
            return True
        elif not zip_path:
            logger.error("Download completed but no LC0 ZIP or binary found.")
            return False

    extract_to = cwd / "temp_lc0_extract"
    extract_to.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
    
    # Move executable
    lc0_exe = next((p for p in extract_to.rglob("*")
                    if p.is_file() and "lc0" in p.name.lower() and p.suffix.lower() in [".exe", ""]), None)
    if not lc0_exe:
        logger.error(f"No LC0 executable found in {extract_to}.")
        shutil.rmtree(extract_to)
        return False
    shutil.move(str(lc0_exe), final_path)
    logger.info(f"LC0 extracted to {final_path}")

    # Move DLL on Windows
    if os.name == "nt":
        dlls = list(extract_to.rglob("*.dll"))
        if dlls:
            for dll in dlls:
                dll_target = cwd / dll.name
                shutil.move(str(dll), dll_target)
                logger.info(f"DLL moved to {dll_target}")
        else:
            logger.warning("No DLL files found in extracted files.")

    shutil.rmtree(extract_to)
    if os.name != "nt":
        final_path.chmod(final_path.stat().st_mode | 0o111)
    return True


def rename_lc0():
    """
    Ensures lc0.zip, binary, and any DLLs live in cwd.
    """
    cwd = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    zip_target = cwd / "lc0.zip"
    bin_target = cwd / ("lc0.exe" if os.name == "nt" else "lc0")

    # Move ZIP or binary if not already present
    if not zip_target.exists() and not bin_target.exists():
        parent_zip = find_file_with_keyword("lc0", ".zip", cwd.parent)
        if parent_zip:
            shutil.move(parent_zip, zip_target)
            logger.info(f"Moved {parent_zip.name} to {zip_target}")
        else:
            parent_bin = find_file_with_keyword("lc0", None, cwd.parent)
            if parent_bin and parent_bin.name.lower().startswith("lc0"):
                shutil.move(parent_bin, bin_target)
                logger.info(f"Moved {parent_bin.name} to {bin_target}")

    # Move any DLLs from parent into cwd
    if os.name == "nt":
        for dll in Path(cwd.parent).glob("*.dll"):
            dest = cwd / dll.name
            if not dest.exists():
                shutil.move(dll, dest)
                logger.info(f"Moved {dll.name} to {dest}")
    return True


def rename_onnx_model(target_dir: Path = None) -> bool:
    """
    Ensures chess_detection.onnx is moved into target_dir (or cwd) from project or parent.
    """
    dest = target_dir or Path.cwd()
    target = dest / "chess_detection.onnx"
    if getattr(sys, 'frozen', False):
        bundled = Path(sys._MEIPASS) / "chess_detection.onnx"
        if bundled.exists():
            return True
        logger.error("Bundled ONNX not found.")
        return False
    if target.exists():
        logger.info(f"ONNX model already exists at {target}")
        return True
    # search in cwd and parent
    found = find_file_with_keyword("chess_detection", ".onnx", Path.cwd()) \
         or find_file_with_keyword("chess_detection", ".onnx", Path.cwd().parent)
    if not found:
        logger.error(f"No ONNX model found. See {README_URL}")
        return False
    shutil.move(str(found), str(target))
    logger.info(f"ONNX model moved to {target}")
    return True



def rename_maia_model(target_dir: Path = None) -> bool:
    """
    Ensures a maia-*.pb.gz model exists in the executable's directory (or cwd when not frozen).
    Does NOT move the file; simply verifies its presence.
    """
    # Determine search base: exe directory when frozen, otherwise cwd
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path.cwd()
    logger.debug(f"Searching for Maia model in {base} (and its parent)")

    # Search in base and its parent
    candidates = list(base.glob("maia-*.pb.gz")) + list(base.parent.glob("maia-*.pb.gz"))
    if not candidates:
        logger.error(f"No Maia model found in {base} or {base.parent}. See README: {README_URL}")
        return False

    # Choose highest-elo weight if multiple
    def extract_elo(path: Path) -> int:
        try:
            return int(path.stem.split('-')[1])
        except Exception:
            return 0

    best = max(candidates, key=extract_elo)
    logger.info(f"Using Maia model: {best}")
    return True


def find_maia_weights() -> str:
    """
    Locate the Maia weight file (*.pb.gz) next to the executable or cwd.
    """
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path.cwd()
    logger.debug(f"Looking for Maia weights in {base}")

    pattern = str(base / "maia-*.pb.gz")
    candidates = glob.glob(pattern)

    if not candidates:
        logger.error(f"No Maia weights found in {base}. Please download from: {README_URL}")
        raise FileNotFoundError(f"No Maia weights in {base}")

    # Sort by Elo descending
    def extract_elo(path: str) -> int:
        try:
            return int(Path(path).stem.split('-')[1])
        except Exception:
            return 0

    candidates.sort(key=extract_elo, reverse=True)
    best_weight = candidates[0]
    logger.info(f"Selected Maia weights file: {best_weight}")
    return best_weight


def setup_resources(script_dir: Path, project_dir: Path) -> bool:
    """
    Prepare LC0, ONNX, and Maia resources in the src directory for all platforms.
    """
    # Always ensure models are in the script directory
    rename_onnx_model(script_dir)
    rename_maia_model(script_dir)

    # On non-Windows, nothing more is needed
    if os.name != "nt":
        return True

    # On Windows, handle LC0 ZIP, binary, and copy artifacts
    if not rename_lc0() or not extract_lc0():
        return False

    # Move LC0 and ONNX artifacts into script_dir
    for name in ["lc0.zip", "lc0.exe", "lc0.dll", "chess_detection.onnx"]:
        root = project_dir / name
        dest = script_dir / name
        if root.exists() and not dest.exists():
            shutil.move(root, dest)
            logger.info(f"Copied {name} to src/: {dest}")

    # Move Maia model into script_dir
    rename_maia_model(script_dir)

    return True


if __name__ == "__main__":
    logger.info("Starting resource setup...")
    success = extract_lc0() and rename_onnx_model() and rename_maia_model()
    logger.info("Setup complete." if success else "Setup incomplete—check logs.")
