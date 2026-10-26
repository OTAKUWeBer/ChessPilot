"""
Stockfish release resolution, streaming download, and archive extraction subsystem.
Coordinates release asset selection and installation for ChessPilot.
"""

import os
import sys
import time
import shutil
import tarfile
import zipfile
import tempfile
import logging
from pathlib import Path
import requests
from PyQt6.QtWidgets import QApplication

from utils.cpu_features import detect_os, detect_cpu_info, format_bytes
from gui.download_dialog import StockfishDownloaderApp, SILENT_MODE

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# ------------------------ Asset selection ------------------------
def choose_best_asset(assets, os_name, arch, vendor, flags):
    """
    Selects the best matching Stockfish asset for the given OS, architecture, vendor, and CPU flags.
    """
    filtered = _filter_assets_by_os(assets, os_name)
    if not filtered:
        return None
    return _select_best_by_cpu_features(filtered, vendor, flags)


def _filter_assets_by_os(assets, os_name):
    filtered = []
    for a in assets:
        name = a["name"].lower()
        if os_name == "windows" and _matches_os_prefix(name, "windows"):
            filtered.append(a)
        elif os_name == "linux" and _matches_os_prefix(name, "linux"):
            filtered.append(a)
        elif os_name == "mac" and (_matches_os_prefix(name, "mac") or _matches_os_prefix(name, "apple")):
            filtered.append(a)
            
    if not filtered:
        filtered = [a for a in assets if _matches_os_generic(a["name"].lower(), os_name)]
    return filtered


def _matches_os_prefix(name, os_prefix):
    return (name.startswith(f"stockfish-{os_prefix}-") or 
            name.startswith(f"stockfish_{os_prefix}_") or
            name.startswith(f"stockfish-{os_prefix}."))


def _matches_os_generic(name, os_name):
    if os_name == "mac":
        return "mac" in name or "apple" in name or "darwin" in name
    return os_name in name


def _select_best_by_cpu_features(filtered, vendor, flags):
    best_asset = None
    best_score = -1
    
    for a in filtered:
        score = _calculate_cpu_score(a["name"], vendor, flags)
        logger.debug("Scoring asset %s: %s", a["name"], score)
        if score > best_score:
            best_score = score
            best_asset = a
            
    return best_asset


def _calculate_cpu_score(name, vendor, flags):
    """Calculate a score for how well this binary matches the CPU"""
    score = 0
    
    # Define instruction set configurations with their requirements and scoring
    instruction_sets = [
        {
            "keyword": "avx512",
            "required_flags": lambda f: any(flag.startswith("avx512") for flag in f),
            "match_score": 100,
            "mismatch_penalty": -100
        },
        {
            "keyword": "bmi2",
            "required_flags": lambda f: "bmi2" in f,
            "match_score": 80,
            "mismatch_penalty": -50
        },
        {
            "keyword": "avx2",
            "required_flags": lambda f: "avx2" in f or "avx" in f,
            "match_score": 60,
            "mismatch_penalty": -30
        },
        {
            "keywords": ["popcnt", "sse41", "sse4"],
            "required_flags": lambda f: any(x in f for x in ["sse4_1", "sse4_2", "popcnt", "sse4.1", "sse4.2"]),
            "match_score": 50,
            "mismatch_penalty": 0
        }
    ]
    
    # Check instruction set matches
    score += _check_instruction_sets(name, flags, instruction_sets)
    
    # Add vendor bonus if applicable
    score += _calculate_vendor_bonus(name, vendor, flags)
    
    # Add fallback scores
    score += _calculate_fallback_score(name)
    
    # Add format bonus
    score += _calculate_format_bonus(name)
    
    # Apply vendor mismatch penalty
    score += _calculate_vendor_penalty(name, vendor)
    
    return score


def _check_instruction_sets(name, flags, instruction_sets):
    """Check if binary name matches CPU instruction sets"""
    for config in instruction_sets:
        keywords = config.get("keywords", [config.get("keyword")])
        
        if any(kw in name for kw in keywords):
            has_required = config["required_flags"](flags)
            if has_required:
                return config["match_score"]
            else:
                return config["mismatch_penalty"]
    
    return 0


def _calculate_vendor_bonus(name, vendor, flags):
    """Calculate bonus score for vendor-specific optimizations"""
    if "bmi2" not in name or "bmi2" not in flags:
        return 0
    
    vendor_map = {
        "amd": "amd",
        "intel": "intel"
    }
    
    if vendor in vendor_map and vendor_map[vendor] in name:
        return 10
    
    return 0


def _calculate_fallback_score(name):
    """Calculate score for fallback builds"""
    fallback_scores = {
        "modern": 40,
        "x86-64": 35,
        "x86_64": 35
    }
    
    for keyword, score in fallback_scores.items():
        if keyword in name:
            return score
    
    return 0


def _calculate_format_bonus(name):
    """Add bonus for compressed archive formats"""
    compression_formats = (".tar.gz", ".tgz", ".zip", ".tar")
    return 5 if name.endswith(compression_formats) else 0


def _calculate_vendor_penalty(name, vendor):
    """Apply penalty for vendor-specific mismatches"""
    penalty = 0
    
    if "amd" in name and vendor not in ["amd", "generic", "unknown"]:
        penalty -= 5
    
    if "intel" in name and vendor not in ["intel", "generic", "unknown"]:
        penalty -= 5
    
    return penalty


# ------------------------ Download & Extraction ------------------------
def download_file(url, dest_path, progress_callback=None, chunk_size=8192, timeout=60):
    """
    Downloads a file while calling progress_callback(downloaded_bytes, total_bytes_or_None, speed_bytes_per_sec)
    """
    logger.debug(f"Starting download: {url} -> {dest_path}")
    start_time = time.time()
    downloaded = 0
    last_report_time = start_time

    try:
        with requests.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
            r.raise_for_status()
            total = r.headers.get("Content-Length")
            total = int(total) if total else None
            
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        elapsed = now - start_time if (now - start_time) > 0 else 1e-6
                        speed = downloaded / elapsed
                        
                        if (now - last_report_time) >= 0.1 or (total and downloaded >= total):
                            last_report_time = now
                            if progress_callback:
                                try:
                                    progress_callback(downloaded, total, speed)
                                except Exception as e:
                                    logger.warning(f"Progress callback error: {e}")
                                    
    except requests.exceptions.Timeout as e:
        logger.error(f"Download timeout: {e}")
        raise Exception("Download timed out. Please check your internet connection.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise Exception("Connection failed. Please check your internet connection.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed: {e}")
        raise Exception(f"Download failed: {str(e)}")
    except IOError as e:
        logger.error(f"File write error: {e}")
        raise Exception(f"Could not write file: {str(e)}")
        
    logger.debug("Download finished")


class BinaryExtractor:
    def __init__(self, archive_path):
        self.archive_path = archive_path
        self.tmpdir = None
        
    def extract_binary(self):
        self.tmpdir = tempfile.mkdtemp()
        extracted = []
        
        try:
            if self._is_tar_archive():
                extracted = self._extract_tar()
            elif self._is_zip_archive():
                extracted = self._extract_zip()
            else:
                extracted = self._copy_single_file()
                
        except (tarfile.TarError, zipfile.BadZipFile) as e:
            logger.error(f"Archive extraction failed: {e}")
            self._cleanup()
            return None
        except Exception as e:
            logger.error(f"Unexpected extraction error: {e}")
            self._cleanup()
            return None

        binary_path = self._find_stockfish_binary(extracted)
        if binary_path:
            self._set_binary_permissions(binary_path)
        else:
            self._cleanup()
        
        return binary_path
    
    def _is_tar_archive(self):
        return self.archive_path.endswith((".tar", ".tar.gz", ".tgz"))
    
    def _is_zip_archive(self):
        return self.archive_path.endswith(".zip")
    
    def _extract_tar(self):
        extracted = []
        with tarfile.open(self.archive_path, "r:*") as t:
            for member in t.getmembers():
                if self._is_safe_path(member.name):
                    t.extract(member, self.tmpdir)
                    
            for root, _, files in os.walk(self.tmpdir):
                for f in files:
                    extracted.append(os.path.join(root, f))
        return extracted
    
    def _extract_zip(self):
        extracted = []
        with zipfile.ZipFile(self.archive_path, "r") as z:
            for member in z.namelist():
                if self._is_safe_path(member):
                    z.extract(member, self.tmpdir)
                    
            for root, _, files in os.walk(self.tmpdir):
                for f in files:
                    extracted.append(os.path.join(root, f))
        return extracted
    
    def _copy_single_file(self):
        dest = os.path.join(self.tmpdir, os.path.basename(self.archive_path))
        shutil.copy2(self.archive_path, dest)
        return [dest]
    
    def _is_safe_path(self, path):
        if os.path.isabs(path) or ".." in path:
            logger.warning(f"Skipping potentially dangerous path: {path}")
            return False
        return True
    
    def _find_stockfish_binary(self, extracted):
        for f in extracted:
            name = os.path.basename(f).lower()
            if "stockfish" in name:
                return f
        return None
    
    def _set_binary_permissions(self, binary_path):
        try:
            os.chmod(binary_path, 0o744)
        except OSError as e:
            logger.warning(f"Could not set permissions on {binary_path}: {e}")
    
    def _cleanup(self):
        if self.tmpdir:
            shutil.rmtree(self.tmpdir, ignore_errors=True)


def extract_binary(archive_path):
    extractor = BinaryExtractor(archive_path)
    return extractor.extract_binary()


# ------------------------ Download Workflow ------------------------
class DownloadWorkflow:
    def __init__(self, signals):
        self.signals = signals
        self.os_name = detect_os()
        self.arch, self.vendor, self.flags = detect_cpu_info()
        
    def execute(self):
        try:
            logger.info(f"Detected OS={self.os_name}, arch={self.arch}, vendor={self.vendor}")
            
            if self._is_already_installed():
                return
                
            release_data = self._fetch_release_data()
            if not release_data:
                return
                
            best_asset = self._select_asset(release_data)
            if not best_asset:
                return
                
            archive_path = self._download_asset(best_asset, release_data["tag_name"])
            if not archive_path:
                return
                
            binary_path = self._extract_binary(archive_path)
            if not binary_path:
                return
                
            self._install_binary(binary_path)
            
        except Exception as ex:
            logger.exception("Unexpected error during download/install")
            self.signals.label_update.emit("Error occurred")
            self.signals.sub_label_update.emit(str(ex))
            self.signals.show_retry.emit()
    
    def _is_already_installed(self):
        target_path = self._get_target_path()
        if target_path.exists():
            logger.info(f"Stockfish already installed at {target_path} — exiting")
            self.signals.label_update.emit("Already installed")
            self.signals.sub_label_update.emit(str(target_path))
            self.signals.progress_update.emit(100)
            self.signals.close_window.emit(800)
            return True
        return False
    
    def _get_target_path(self):
        if self.os_name == "windows":
            if getattr(sys, 'frozen', False):
                return Path(sys.executable).parent / "stockfish.exe"
            else:
                return Path.cwd() / "stockfish.exe"
        else:
            if getattr(sys, 'frozen', False):
                return Path(sys.executable).parent / "stockfish"
            else:
                return Path.cwd() / "stockfish"
    
    def _fetch_release_data(self):
        self.signals.label_update.emit("Fetching latest release metadata...")
        logger.info("Fetching latest Stockfish release metadata from GitHub")
        
        try:
            r = requests.get("https://api.github.com/repos/official-stockfish/Stockfish/releases/latest", timeout=30)
            r.raise_for_status()
            rel = r.json()
            
            tag = rel.get("tag_name", "unknown")
            assets = [{"name": a["name"], "url": a["browser_download_url"], "size": a.get("size", 0)} 
                     for a in rel.get("assets", [])]
            
            return {"tag_name": tag, "assets": assets}
            
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching release metadata")
            self.signals.label_update.emit("Connection timeout")
            self.signals.sub_label_update.emit("Please check your internet connection")
            self.signals.show_retry.emit()
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch release metadata: {e}")
            self.signals.label_update.emit("Network error")
            self.signals.sub_label_update.emit("Could not fetch release info. Check your connection.")
            self.signals.show_retry.emit()
            return None
    
    def _select_asset(self, release_data):
        best_asset = choose_best_asset(release_data["assets"], self.os_name, 
                                       self.arch, self.vendor, self.flags)
        if not best_asset:
            logger.error("No matching build found for this OS/arch")
            self.signals.label_update.emit("No matching build found")
            self.signals.sub_label_update.emit("See logs for details")
            self.signals.show_retry.emit()
            return None
            
        logger.info(f"Selected asset: {best_asset['name']} (release {release_data['tag_name']})")
        self.signals.sub_label_update.emit(f"CPU: {self.vendor.upper()} | Selected: {best_asset['name']}")
        return best_asset
    
    def _download_asset(self, best_asset, tag_name):
        self.signals.label_update.emit(f"{tag_name} — {best_asset['name']}")
        asset_name = best_asset["name"]
        archive_path = os.path.join(tempfile.gettempdir(), asset_name)

        if self._is_cached_and_valid(archive_path, best_asset):
            self.signals.sub_label_update.emit("Using cached download")
            self.signals.progress_update.emit(5)
            return archive_path

        self.signals.label_update.emit(f"Downloading {asset_name}...")
        try:
            download_file(best_asset["url"], archive_path, progress_callback=self._create_progress_callback())
            return archive_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.signals.label_update.emit("Download failed")
            self.signals.sub_label_update.emit(str(e))
            self.signals.show_retry.emit()
            return None
    
    def _is_cached_and_valid(self, archive_path, asset):
        if not os.path.exists(archive_path):
            return False
            
        if not asset.get("size"):
            return True
            
        try:
            local_size = os.path.getsize(archive_path)
            if local_size == int(asset.get("size", 0)):
                logger.info("Archive already downloaded and size matches; skipping re-download")
                return True
            else:
                logger.info("Local archive exists but size differs; re-downloading")
                return False
        except OSError as e:
            logger.warning(f"Could not check local archive: {e}")
            return False
    
    def _create_progress_callback(self):
        def progress_cb(d, t, speed_bytes_per_s):
            pct = (d * 100 / t) if t else min(99.9, d / 1024 / 1024)
            self.signals.progress_update.emit(int(pct))
            mbps = (speed_bytes_per_s * 8) / (1000 * 1000)
            speed_mb_s = speed_bytes_per_s / (1024 * 1024)
            if t:
                self.signals.sub_label_update.emit(f"{format_bytes(d)} / {format_bytes(t)} — {speed_mb_s:.2f} MB/s ({mbps:.2f} Mbps)")
            else:
                self.signals.sub_label_update.emit(f"{format_bytes(d)} — {speed_mb_s:.2f} MB/s ({mbps:.2f} Mbps)")
        return progress_cb
    
    def _extract_binary(self, archive_path):
        self.signals.label_update.emit("Extracting binary...")
        logger.info("Extracting binary from archive")
        bin_path = extract_binary(archive_path)
        if not bin_path:
            logger.error("Could not find Stockfish binary inside the archive")
            self.signals.label_update.emit("Binary not found in archive")
            self.signals.sub_label_update.emit("See logs")
            self.signals.show_retry.emit()
            return None
        
        self.signals.progress_update.emit(75)
        return bin_path
    
    def _install_binary(self, bin_path):
        self.signals.label_update.emit("Installing...")
        target_path = self._get_target_path()
        
        if self.os_name == "windows":
            self._install_windows(bin_path, target_path)
        else:
            self._install_unix(bin_path, target_path)
    
    def _install_windows(self, bin_path, target_path):
        try:
            shutil.copy2(bin_path, target_path)
            logger.info("Installed Stockfish to %s", target_path)
            self.signals.label_update.emit(f"Installed to {target_path.name}")
            self.signals.progress_update.emit(100)
            self.signals.close_window.emit(700)
        except (OSError, IOError) as e:
            logger.error(f"Failed to copy binary on Windows: {e}")
            self.signals.label_update.emit("Install failed")
            self.signals.sub_label_update.emit(str(e))
            self.signals.show_retry.emit()
    
    def _install_unix(self, bin_path, target_path):
        try:
            shutil.copy2(bin_path, target_path)
            os.chmod(target_path, 0o700)
            logger.info("Installed Stockfish to %s", target_path)
            self.signals.label_update.emit(f"Installed to {target_path.name}")
            self.signals.progress_update.emit(100)
            self.signals.close_window.emit(700)
        except (OSError, IOError) as e:
            logger.error(f"Failed to copy binary on Unix-like OS: {e}")
            self.signals.label_update.emit("Install failed")
            self.signals.sub_label_update.emit(str(e))
            self.signals.show_retry.emit()


# ------------------------ Main Entrypoint ------------------------
def download_stockfish(target_path=None):
    """
    Main entry point for downloading Stockfish.
    Creates a QApplication and shows the downloader UI (unless SILENT_MODE is True).
    
    Args:
        target_path: Optional path where to install Stockfish
    
    Returns:
        True if download/install succeeded, False otherwise
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    downloader = StockfishDownloaderApp(workflow_factory=DownloadWorkflow)
    if not SILENT_MODE:
        downloader.show()
    app.exec()
    
    if target_path:
        return Path(target_path).exists()
    
    if detect_os() == "windows":
        if getattr(sys, 'frozen', False):
            default_path = Path(sys.executable).parent / "stockfish.exe"
        else:
            default_path = Path.cwd() / "stockfish.exe"
    else:
        if getattr(sys, 'frozen', False):
            default_path = Path(sys.executable).parent / "stockfish"
        else:
            default_path = Path.cwd() / "stockfish"
    
    return default_path.exists()


if __name__ == "__main__":
    success = download_stockfish()
    sys.exit(0 if success else 1)
