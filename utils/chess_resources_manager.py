import os
import zipfile
from pathlib import Path
import shutil
import logging
from shutil import which
import glob

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

README_MAIA_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/maia-support/README.md"
README_ONNX_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/maia-support/README.md"
README_LC0_URL = "https://github.com/OTAKUWeBer/ChessPilot/blob/maia-support/README.md"

def find_file_with_keyword(keyword, extension=None, search_path=Path.cwd()):
    """
    Finds the first file in `search_path` containing the keyword in its name
    and optionally matching extension.
    """
    logger.debug(f"Searching for files with keyword '{keyword}' and extension '{extension}' in {search_path}")
    for file in search_path.iterdir():
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
    Ensures an Lc0 binary exists at ./lc0 (Unix) or ./lc0.exe (Windows).
    If not already present, looks for a ZIP containing 'lc0' in its name and extracts it.
    If neither is found, logs an error referring the user to the README.
    """
    target_name = "lc0.exe" if os.name == "nt" else "lc0"
    final_path = Path.cwd() / target_name

    # Check for system-wide lc0
    system_path = which("lc0")
    if system_path:
        logger.info(f"Found system-installed Lc0 at {system_path}. Skipping extraction.")
        return True

    if final_path.exists():
        logger.info(f"Lc0 binary already exists at {final_path}. Skipping extraction.")
        return True

    zip_path = find_file_with_keyword("lc0", ".zip")
    if not zip_path:
        message = (
            "No Lc0 executable found on your PATH or in the project root. "
            "Please download a ZIP with “lc0” in its name and place it in the project root.\n"
            f"See README for download links: {README_LC0_URL}"
        )
        logger.error(message)
        return False

    extract_to = Path.cwd() / "temp_lc0_extract"
    extract_to.mkdir(exist_ok=True)

    logger.info(f"Extracting Lc0 from {zip_path} …")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    lc0_exe = None
    for path in extract_to.rglob("*"):
        if (
            path.is_file()
            and "lc0" in path.name.lower()
            and path.suffix.lower() in [".exe", ""]
        ):
            lc0_exe = path
            break

    if not lc0_exe:
        message = (
            "Extraction succeeded but no Lc0 executable was found inside the ZIP. "
            f"Please verify the ZIP contents (see README): {README_MAIA_URL}"
        )
        logger.error(message)
        shutil.rmtree(extract_to)
        return False

    shutil.move(str(lc0_exe), final_path)
    logger.info(f"Lc0 extracted and renamed to {final_path}")

    if os.name != "nt":
        try:
            perms = final_path.stat().st_mode
            final_path.chmod(perms | 0o111)
        except Exception as e:
            logger.warning(f"Could not set execute permissions on {final_path}: {e}")

    shutil.rmtree(extract_to)
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
            f"Please download them using the link in the README: {README_MAIA_URL}"
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


def rename_onnx_model():
    """
    Ensures an ONNX model exists at ./chess_detection.onnx.
    If not already present, looks for any file with 'chess_detection' in its name and '.onnx' extension.
    If neither is found, logs an error referring the user to the README.
    """
    target_path = Path.cwd() / "chess_detection.onnx"

    # If the correctly named model already exists, do nothing
    if target_path.exists():
        logger.info(f"ONNX model already exists at {target_path}. Skipping rename.")
        return True

    # Look for any *.onnx file with 'chess_detection' in its name
    onnx_file = find_file_with_keyword("chess_detection", ".onnx")
    if not onnx_file:
        message = (
            "No ONNX model file found (filename containing 'chess_detection'). "
            f"Please download the ONNX model using the link in the README: {README_ONNX_URL}"
        )
        logger.error(message)
        return False

    # Move or rename into place
    if onnx_file.parent != Path.cwd():
        shutil.move(str(onnx_file), target_path)
    else:
        onnx_file.rename(target_path)

    logger.info(f"ONNX model renamed/moved to {target_path}")
    return True

if __name__ == "__main__":
    logger.info("Starting Maia extraction and ONNX model rename process...")
    onnx_ok = rename_onnx_model()
    lc0_ok = extract_lc0()
    maia_ok = find_maia_weights()
    if lc0_ok and onnx_ok and maia_ok:
        logger.info("Setup complete.")
    else:
        logger.info("Setup incomplete—please check the above errors and consult the README for download links.")
