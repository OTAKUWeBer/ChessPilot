import os
import zipfile
import glob
from pathlib import Path
import shutil
import logging
from shutil import which
import sys

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

README_LC0_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/main/README.md"
README_ONNX_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/main/README.md"


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


def extract_lc0():
    """
    Ensures an LC0 binary exists at ./lc0 or ./lc0.exe in cwd.
    Extracts from ZIP in cwd if needed, including DLL on Windows.
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
        logger.error(f"No LC0 ZIP found in {cwd}. See README: {README_LC0_URL}")
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

def rename_onnx_model():
    cwd = Path.cwd()
    target = cwd / "chess_detection.onnx"
    if getattr(sys, 'frozen', False):
        bundled = Path(sys._MEIPASS) / "chess_detection.onnx"
        if bundled.exists(): return True
        logger.error("Bundled ONNX not found.")
        return False
    if target.exists(): return True
    found = find_file_with_keyword("chess_detection", ".onnx", cwd) \
         or find_file_with_keyword("chess_detection", ".onnx", cwd.parent)
    if not found:
        logger.error(f"No ONNX model found. See {README_ONNX_URL}")
        return False
    shutil.move(str(found), str(target))
    logger.info(f"ONNX model moved to {target}")
    return True


def rename_maia_model(target_dir: Path = None) -> bool:
    """
    Finds the first maia-*.pb.gz model in cwd or parent and moves it to target_dir.
    """
    cwd = Path.cwd()
    dest = target_dir or cwd
    candidates = list(cwd.glob("maia-*.pb.gz")) + list(cwd.parent.glob("maia-*.pb.gz"))
    if not candidates:
        logger.error("No Maia model found. Place a maia-*.pb.gz file in project or parent directory.")
        return False

    # pick first candidate
    maia_file = candidates[0]
    target_path = dest / maia_file.name
    if not target_path.exists():
        shutil.move(str(maia_file), target_path)
        logger.info(f"Maia model moved to {target_path}")
    else:
        logger.info(f"Maia model already at {target_path}")
    return True


def find_maia_weights() -> str:
    """
    Search for Maia weight files (*.pb.gz) in the current working directory
    and return the highest-Elo file.
    """
    models_dir = Path.cwd()
    pattern = str(models_dir / "maia-*.pb.gz")
    candidates = glob.glob(pattern)

    logger.debug(f"Looking for Maia weight files in {models_dir}")

    if not candidates:
        logger.error("No Maia weights found.")
        raise FileNotFoundError(
            f"No Maia weights found in {models_dir}. "
            f"Please download them using the link in the README: {README_ONNX_URL}"
        )

    def extract_elo(path: str) -> int:
        name = os.path.basename(path)
        try:
            elo = int(name.split('-')[1].split('.')[0])
            logger.debug(f"Extracted Elo {elo} from {name}")
        except (IndexError, ValueError):
            logger.warning(f"Could not extract Elo from {name}, defaulting to 0")
            elo = 0
        return elo

    candidates.sort(key=extract_elo, reverse=True)
    best_weight = candidates[0]
    logger.info(f"Selected Maia weights file: {best_weight}")
    return best_weight


def setup_resources(script_dir: Path, project_dir: Path) -> bool:
    if os.name != "nt":
        return True

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

    # Finally, ensure ONNX and Maia are correctly named/placed
    return rename_onnx_model(), True


if __name__ == "__main__":
    logger.info("Starting LC0/MAIA setup...")
    success = extract_lc0() and rename_onnx_model() and rename_maia_model()
    logger.info("Setup complete." if success else "Setup incomplete—check logs.")
