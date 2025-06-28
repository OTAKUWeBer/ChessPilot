import os
import zipfile
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
    Finds the first file in `search_path` containing the keyword in its name
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
        lc0_dll = next((p for p in extract_to.rglob("*.dll") if "lc0" in p.name.lower()), None)
        if lc0_dll:
            dll_target = cwd / lc0_dll.name
            shutil.move(str(lc0_dll), dll_target)
            logger.info(f"LC0 DLL moved to {dll_target}")
        else:
            logger.warning("LC0 DLL not found in extracted files.")

    shutil.rmtree(extract_to)
    if os.name != "nt":
        final_path.chmod(final_path.stat().st_mode | 0o111)
    return True


def rename_lc0():
    """
    Ensures lc0.zip or the raw LC0 binary and DLL live in cwd.
    """
    cwd = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    zip_target = cwd / "lc0.zip"
    bin_target = cwd / ("lc0.exe" if os.name == "nt" else "lc0")

    if zip_target.exists() or bin_target.exists():
        logger.info("LC0 ZIP or binary already present.")
    else:
        parent_zip = find_file_with_keyword("lc0", ".zip", cwd.parent)
        if parent_zip:
            shutil.move(parent_zip, zip_target)
            logger.info(f"Moved {parent_zip.name} to {zip_target}")
        else:
            parent_bin = find_file_with_keyword("lc0", None, cwd.parent)
            if parent_bin and parent_bin.name.lower().startswith("lc0"):
                shutil.move(parent_bin, bin_target)
                logger.info(f"Moved {parent_bin.name} to {bin_target}")

    # Copy DLL on Windows
    if os.name == "nt":
        dll_target = cwd / "lc0.dll"
        if not dll_target.exists():
            parent_dll = find_file_with_keyword("lc0", ".dll", cwd.parent)
            if parent_dll:
                shutil.move(parent_dll, dll_target)
                logger.info(f"Moved {parent_dll.name} to {dll_target}")
            else:
                logger.warning("No LC0 DLL found in parent directory.")
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
    found = find_file_with_keyword("chess_detection", ".onnx", cwd) or find_file_with_keyword("chess_detection", ".onnx", cwd.parent)
    if not found:
        logger.error(f"No ONNX model found. See {README_ONNX_URL}")
        return False
    shutil.move(str(found), str(target))
    logger.info(f"ONNX model moved to {target}")
    return True


def rename_maia_model():
    """
    Detects any maia-*.pb.gz model in cwd or parent. No renaming or moving.
    """
    cwd = Path.cwd()
    candidates = list(cwd.glob("maia-*.pb.gz")) + list(cwd.parent.glob("maia-*.pb.gz"))
    if candidates:
        logger.info(f"Using Maia model: {candidates[0].name}")
        return True
    else:
        logger.error("No Maia model found. Place a maia-*.pb.gz file in project or parent directory.")
        return False


def setup_resources(script_dir: Path, project_dir: Path) -> bool:
    if os.name != "nt": return True
    if not rename_lc0() or not extract_lc0(): return False

    # Move artifacts into script_dir
    for name in ["lc0.zip", "lc0.exe", "lc0.dll", "chess_detection.onnx"]:
        root = project_dir / name
        dest = script_dir / name
        if root.exists() and not dest.exists():
            shutil.move(root, dest)
            logger.info(f"Copied {name} to src/: {dest}")

    return rename_onnx_model(), rename_maia_model()

if __name__ == "__main__":
    logger.info("Starting LC0/MAIA setup...")
    success = extract_lc0() and rename_onnx_model() and rename_maia_model()
    logger.info("Setup complete." if success else "Setup incomplete—check logs.")
