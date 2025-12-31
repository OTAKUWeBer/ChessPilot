import os
import platform
import subprocess
import zipfile
import shutil
import tempfile
import threading
import requests
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QUrl
from pathlib import Path
import logging
import sys
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

SILENT_MODE = False

class ProgressSignals(QObject):
    """Signals for thread-safe UI updates"""
    progress_update = pyqtSignal(int)  # percentage
    label_update = pyqtSignal(str)
    sub_label_update = pyqtSignal(str)
    show_retry = pyqtSignal()
    close_window = pyqtSignal(int)  # delay in ms

# ------------------------ Visual style ------------------------
BG_COLOR = "#2D2D2D"
FRAME_COLOR = "#373737"
ACCENT_COLOR = "#4CAF50"
TEXT_COLOR = "#FFFFFF"
HOVER_COLOR = "#45a049"

# ------------------------ Helpers ------------------------
def detect_os():
    p = platform.system().lower()
    if "windows" in p:
        return "windows"
    if "linux" in p:
        return "linux"
    if "darwin" in p:
        return "mac"
    return p

def detect_gpu_capabilities():
    """Detect GPU capabilities for neural network engines"""
    capabilities = set()
    
    # Check for NVIDIA GPU
    if _has_nvidia_gpu():
        capabilities.add("cuda")
        if _has_cudnn():
            capabilities.add("cudnn")
    
    # Check for DirectX 12 (Windows 10+)
    if detect_os() == "windows" and _has_dx12():
        capabilities.add("dx12")
    
    # Check for OpenCL
    if _has_opencl():
        capabilities.add("opencl")
    
    return capabilities

def _has_nvidia_gpu():
    """Check for NVIDIA GPU"""
    try:
        if detect_os() == "windows":
            subprocess.run(["nvidia-smi"], capture_output=True, check=True, timeout=5)
            return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    try:
        if detect_os() == "windows":
            nvidia_files = [
                Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32" / "nvapi64.dll",
                Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32" / "nvcuda.dll"
            ]
            return any(f.exists() for f in nvidia_files)
    except Exception:
        pass
    
    return False

def _has_cudnn():
    """Check for cuDNN availability"""
    try:
        if detect_os() == "windows":
            cudnn_files = [
                Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32" / "cudnn64_8.dll",
                Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32" / "cudnn_cnn_infer64_8.dll"
            ]
            return any(f.exists() for f in cudnn_files)
    except Exception:
        pass
    return False

def _has_dx12():
    """Check for DirectX 12 support (Windows 10+)"""
    try:
        if detect_os() == "windows":
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                build = winreg.QueryValueEx(key, "CurrentBuild")[0]
                return int(build) >= 10240
    except Exception:
        pass
    return False

def _has_opencl():
    """Check for OpenCL support"""
    try:
        if detect_os() == "windows":
            opencl_files = [
                Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32" / "OpenCL.dll"
            ]
            return any(f.exists() for f in opencl_files)
    except Exception:
        pass
    return False

def format_bytes(n):
    n = float(n or 0)
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

# ------------------------ Asset selection ------------------------
def choose_best_maia_asset(assets, os_name, gpu_capabilities):
    """Choose the best Maia model file (pb.gz format)"""
    pb_files = [a for a in assets if a["name"].endswith(".pb.gz")]
    
    if not pb_files:
        logger.error("No .pb.gz model files found in Maia release")
        return None
    
    preferred = [a for a in pb_files if "1700" in a["name"]]
    if preferred:
        logger.info(f"Using preferred Maia 1700 model: {preferred[0]['name']}")
        return preferred[0]
    
    # Sort by model number (extracted from filename) descending
    def get_model_number(asset_name):
        import re
        match = re.search(r'maia-(\d+)', asset_name)
        return int(match.group(1)) if match else 0
    
    sorted_files = sorted(pb_files, key=lambda a: get_model_number(a["name"]), reverse=True)
    logger.info(f"Selected highest-rated Maia model: {sorted_files[0]['name']}")
    return sorted_files[0]

def _filter_maia_assets_by_os(assets, os_name):
    """Filter Maia assets by operating system - not needed for model files"""
    return [a for a in assets if a["name"].endswith(".pb.gz")]

def _select_best_maia_by_gpu(filtered_assets, gpu_capabilities):
    """Select the best Maia build based on GPU capabilities - not needed for model files"""
    if not filtered_assets:
        return None
    return filtered_assets[0]

# ------------------------ Download & extraction ------------------------
def download_file(url, dest_path, progress_callback=None, chunk_size=8192, timeout=60):
    """Downloads a file with progress reporting"""
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
        raise Exception(f"Download timed out. Please check your internet connection.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise Exception(f"Connection failed. Please check your internet connection.")
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
            if self._is_zip_archive():
                extracted = self._extract_zip()
            else:
                extracted = self._copy_single_file()
                
        except zipfile.BadZipFile as e:
            logger.error(f"Archive extraction failed: {e}")
            self._cleanup()
            return None
        except Exception as e:
            logger.error(f"Unexpected extraction error: {e}")
            self._cleanup()
            return None

        binary_path = self._find_maia_binary(extracted)
        if not binary_path:
            binary_path = self._find_maia_model(extracted)
            
        if binary_path:
            self._set_binary_permissions(binary_path)
        else:
            self._cleanup()
        
        return binary_path
    
    def _is_zip_archive(self):
        return self.archive_path.endswith(".zip")
    
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
    
    def _find_maia_binary(self, extracted):
        """Find Maia binary executable in extracted files"""
        for f in extracted:
            name = os.path.basename(f).lower()
            if ("maia" in name or "lc0" in name) and (name.endswith(".exe") or not "." in name):
                if os.path.isfile(f):
                    return f
        
        # Fallback: any executable that mentions maia
        for f in extracted:
            name = os.path.basename(f).lower()
            if "maia" in name and os.path.isfile(f):
                return f
        return None
    
    def _find_maia_model(self, extracted):
        """Find Maia model file (.pb.gz) in extracted files"""
        for f in extracted:
            name = os.path.basename(f).lower()
            if name.endswith(".pb.gz"):
                if os.path.isfile(f):
                    logger.info(f"Found Maia model file: {name}")
                    return f
        return None
    
    def _set_binary_permissions(self, binary_path):
        try:
            os.chmod(binary_path, 0o755)
        except OSError as e:
            logger.warning(f"Could not set permissions on {binary_path}: {e}")
    
    def _cleanup(self):
        if self.tmpdir:
            shutil.rmtree(self.tmpdir, ignore_errors=True)

def extract_binary(archive_path):
    extractor = BinaryExtractor(archive_path)
    return extractor.extract_binary()

# ------------------------ Download workflow ------------------------
class DownloadWorkflow:
    def __init__(self, signals):
        self.signals = signals
        self.os_name = detect_os()
        self.gpu_capabilities = detect_gpu_capabilities()
        
    def execute(self):
        try:
            logger.info(f"Detected OS={self.os_name}, GPU capabilities={self.gpu_capabilities}")
            
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
            logger.info(f"Maia already installed at {target_path} — exiting")
            self.signals.label_update.emit("Already installed")
            self.signals.sub_label_update.emit(str(target_path))
            self.signals.progress_update.emit(100)
            self.signals.close_window.emit(800)
            return True
        return False
    
    def _get_target_path(self):
        if self.os_name == "windows":
            if getattr(sys, 'frozen', False):
                return Path(sys.executable).parent / "maia.exe"
            else:
                return Path.cwd() / "maia.exe"
        else:
            if getattr(sys, 'frozen', False):
                return Path(sys.executable).parent / "maia"
            else:
                return Path.cwd() / "maia"
    
    def _fetch_release_data(self):
        self.signals.label_update.emit("Fetching latest Maia release...")
        logger.info("Fetching latest Maia release metadata from GitHub")
        
        try:
            # Maia engines are distributed via LeelaChessZero/lc0 releases
            r = requests.get("https://api.github.com/repos/CSSLab/maia-chess/releases/latest", timeout=30)
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
        best_asset = choose_best_maia_asset(release_data["assets"], self.os_name, self.gpu_capabilities)
        if not best_asset:
            logger.error("No matching Maia build found for this OS/GPU")
            self.signals.label_update.emit("No matching build found")
            self.signals.sub_label_update.emit("See logs for details")
            self.signals.show_retry.emit()
            return None
            
        logger.info(f"Selected asset: {best_asset['name']} (release {release_data['tag_name']})")
        gpu_info = "GPU" if self.gpu_capabilities else "CPU"
        self.signals.sub_label_update.emit(f"Mode: {gpu_info} | Selected: {best_asset['name']}")
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
        logger.info("Extracting Maia binary from archive")
        bin_path = extract_binary(archive_path)
        if not bin_path:
            logger.error("Could not find Maia binary inside the archive")
            self.signals.label_update.emit("Binary not found in archive")
            self.signals.sub_label_update.emit("See logs")
            self.signals.show_retry.emit()
            return None
        
        self.signals.progress_update.emit(75)
        return bin_path
    
    def _install_binary(self, bin_path):
        self.signals.label_update.emit("Installing...")
        target_path = self._get_target_path()
        
        try:
            extraction_dir = os.path.dirname(bin_path)
            target_dir = target_path.parent
            
            bin_name = os.path.basename(bin_path)
            
            if bin_name.endswith(".pb.gz"):
                # Maia model file - install as-is with .pb.gz extension
                model_target = target_dir / bin_name
                shutil.copy2(bin_path, model_target)
                logger.info(f"Installed Maia model to {model_target}")
                self.signals.label_update.emit(f"Installed {bin_name}")
                self.signals.sub_label_update.emit(str(model_target))
            else:
                # Binary executable - copy and handle DLLs
                shutil.copy2(bin_path, target_path)
                
                # Copy any DLL files if on Windows
                if self.os_name == "windows":
                    for file_path in Path(extraction_dir).glob("**/*.dll"):
                        dll_target = target_dir / file_path.name
                        if not dll_target.exists():
                            try:
                                shutil.copy2(file_path, dll_target)
                                logger.info(f"Copied DLL: {file_path.name}")
                            except Exception as e:
                                logger.warning(f"Failed to copy DLL {file_path}: {e}")
                
                if self.os_name != "windows":
                    os.chmod(target_path, 0o755)
                    
                logger.info("Installed binary to %s", target_path)
                self.signals.label_update.emit(f"Installed to {target_path.name}")
                self.signals.sub_label_update.emit(str(target_path))
            
            self.signals.progress_update.emit(100)
            self.signals.close_window.emit(700)
            
        except (OSError, IOError) as e:
            logger.error(f"Failed to install: {e}")
            self.signals.label_update.emit("Install failed")
            self.signals.sub_label_update.emit(str(e))
            self.signals.show_retry.emit()

# ------------------------ Downloader UI ------------------------
class MaiaDownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maia Chess Engine Downloader")
        self.setFixedSize(420, 180)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        
        if SILENT_MODE:
            self.hide()

        self.signals = ProgressSignals()
        self.signals.progress_update.connect(self._update_progress)
        self.signals.label_update.connect(self._update_label)
        self.signals.sub_label_update.connect(self._update_sub_label)
        self.signals.show_retry.connect(self._show_retry_button)
        self.signals.close_window.connect(self._close_after)

        self._setup_styles()
        self._create_widgets()

        threading.Thread(target=self._start_download_flow, daemon=True).start()

    def _setup_styles(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_COLOR};
            }}
            QLabel {{
                color: {TEXT_COLOR};
                background-color: {BG_COLOR};
            }}
            QProgressBar {{
                border: 1px solid {FRAME_COLOR};
                background-color: {FRAME_COLOR};
                text-align: center;
                color: {TEXT_COLOR};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT_COLOR};
                border-radius: 2px;
            }}
            QPushButton {{
                background-color: {ACCENT_COLOR};
                color: {TEXT_COLOR};
                border: none;
                border-radius: 3px;
                font-family: 'Segoe UI';
                font-size: 10pt;
                font-weight: bold;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: {HOVER_COLOR};
            }}
        """)

    def _create_widgets(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        self.label = QLabel("Preparing download...")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.pb = QProgressBar()
        self.pb.setMinimum(0)
        self.pb.setMaximum(100)
        self.pb.setValue(0)
        self.pb.setFixedHeight(25)
        layout.addWidget(self.pb)

        self.sub_label = QLabel("")
        self.sub_label.setWordWrap(True)
        layout.addWidget(self.sub_label)

        self.retry_button = QPushButton("Retry Download")
        self.retry_button.clicked.connect(self._retry_download)
        self.retry_button.hide()
        layout.addWidget(self.retry_button)

        self.setLayout(layout)

    def _update_label(self, text):
        self.label.setText(text)

    def _update_sub_label(self, text):
        self.sub_label.setText(text)

    def _update_progress(self, pct):
        self.pb.setValue(pct)

    def _show_retry_button(self):
        self.retry_button.show()

    def _close_after(self, ms):
        logger.debug("Window will close in %d ms", ms)
        if SILENT_MODE:
            QTimer.singleShot(100, self.close)
        else:
            QTimer.singleShot(ms, self.close)

    def _retry_download(self):
        self.retry_button.hide()
        self.pb.setValue(0)
        threading.Thread(target=self._start_download_flow, daemon=True).start()

    def _start_download_flow(self):
        workflow = DownloadWorkflow(self.signals)
        workflow.execute()

# ------------------------ Lc0 Downloader UI ------------------------
class Lc0DownloaderApp(QWidget):
    """GUI for downloading and installing Lc0"""
    def __init__(self):
        super().__init__()
        self.os_name = detect_os()
        self.gpu_capabilities = detect_gpu_capabilities()
        
        self.signals = ProgressSignals()
        self.signals.progress_update.connect(self._on_progress)
        self.signals.label_update.connect(self._on_label)
        self.signals.sub_label_update.connect(self._on_sublabel)
        self.signals.show_retry.connect(self._on_show_retry)
        self.signals.close_window.connect(self._on_close)
        
        self._init_ui()
        self._start_download()
    
    def _init_ui(self):
        """Initialize UI elements"""
        self.setWindowTitle("Lc0 Chess Engine Installer")
        self.setGeometry(100, 100, 500, 300)
        self.setStyleSheet(f"background-color: {BG_COLOR}; color: {TEXT_COLOR};")
        
        layout = QVBoxLayout()
        
        self.label = QLabel("Checking for Lc0...")
        self.label.setStyleSheet(f"color: {TEXT_COLOR}; font-size: 14px;")
        layout.addWidget(self.label)
        
        self.sub_label = QLabel("")
        self.sub_label.setStyleSheet(f"color: #AAA; font-size: 12px;")
        self.sub_label.setWordWrap(True)
        layout.addWidget(self.sub_label)
        
        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"QProgressBar {{ background-color: {FRAME_COLOR}; }} QProgressBar::chunk {{ background-color: {ACCENT_COLOR}; }}")
        layout.addWidget(self.progress)
        
        self.link_btn = QPushButton("Open Build Instructions")
        self.link_btn.setStyleSheet(f"background-color: {ACCENT_COLOR}; color: {TEXT_COLOR};")
        self.link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/LeelaChessZero/lc0/releases")))
        self.link_btn.hide()
        layout.addWidget(self.link_btn)
        
        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setStyleSheet(f"background-color: {ACCENT_COLOR}; color: {TEXT_COLOR};")
        self.retry_btn.clicked.connect(self._start_download)
        self.retry_btn.hide()
        layout.addWidget(self.retry_btn)
        
        self.setLayout(layout)
    
    def _on_progress(self, val):
        self.progress.setValue(val)
    
    def _on_label(self, text):
        self.label.setText(text)
    
    def _on_sublabel(self, text):
        self.sub_label.setText(text)
    
    def _on_show_retry(self):
        self.retry_btn.show()
    
    def _on_close(self, delay):
        QTimer.singleShot(delay, self.close)
    
    def _start_download(self):
        """Start download in background thread"""
        self.retry_btn.hide()
        self.link_btn.hide()
        thread = threading.Thread(target=self._download_lc0, daemon=True)
        thread.start()
    
    def _download_lc0(self):
        """Download and install Lc0"""
        try:
            release_data = self._fetch_release_data()
            if not release_data:
                return
            
            best_asset = self._select_asset(release_data)
            if not best_asset:
                return
            
            archive_path = self._download_asset(best_asset, release_data["tag_name"])
            if not archive_path:
                return
            
            target_path = self._get_target_path()
            if self._is_already_installed(target_path):
                return
            
            self.signals.label_update.emit(f"Extracting {best_asset['name']}...")
            self.signals.progress_update.emit(85)
            
            extracted = self._extract_archive(archive_path)
            if not extracted:
                self.signals.label_update.emit("Extraction failed")
                self.signals.sub_label_update.emit("Could not extract archive")
                self.signals.show_retry.emit()
                return
            
            binary = self._find_lc0_binary(extracted)
            if not binary:
                self.signals.label_update.emit("Binary not found")
                self.signals.sub_label_update.emit("Could not locate lc0 executable")
                self.signals.show_retry.emit()
                return
            
            self._set_binary_permissions(binary)
            shutil.move(binary, str(target_path))
            
            self.signals.label_update.emit("✓ Lc0 installed successfully")
            self.signals.sub_label_update.emit(str(target_path))
            self.signals.progress_update.emit(100)
            self.signals.close_window.emit(800)
            
        except Exception as e:
            logger.error(f"Lc0 download error: {e}")
            self.signals.label_update.emit("Error during installation")
            self.signals.sub_label_update.emit(str(e))
            self.signals.show_retry.emit()
    
    def _get_target_path(self):
        if self.os_name == "windows":
            if getattr(sys, 'frozen', False):
                return Path(sys.executable).parent / "lc0.exe"
            else:
                return Path.cwd() / "lc0.exe"
        else:
            if getattr(sys, 'frozen', False):
                return Path(sys.executable).parent / "lc0"
            else:
                return Path.cwd() / "lc0"
    
    def _fetch_release_data(self):
        self.signals.label_update.emit("Fetching latest Lc0 release...")
        try:
            r = requests.get("https://api.github.com/repos/LeelaChessZero/lc0/releases/latest", timeout=30)
            r.raise_for_status()
            rel = r.json()
            
            tag = rel.get("tag_name", "unknown")
            assets = [{"name": a["name"], "url": a["browser_download_url"], "size": a.get("size", 0)} 
                     for a in rel.get("assets", [])]
            
            return {"tag_name": tag, "assets": assets}
            
        except Exception as e:
            logger.error(f"Failed to fetch Lc0 release: {e}")
            self.signals.label_update.emit("Network error")
            self.signals.sub_label_update.emit("Could not fetch release info")
            self.signals.show_retry.emit()
            return None
    
    def _select_asset(self, release_data):
        """Select best Lc0 build for this OS"""
        assets = release_data["assets"]
        filtered = []
        
        if self.os_name == "windows":
            # Filter Windows binaries - prefer CPU builds for compatibility
            for asset in assets:
                name = asset["name"].lower()
                if "windows" in name and ".zip" in name:
                    filtered.append(asset)
            
            if not filtered:
                logger.error("No Windows build found for Lc0")
                self.signals.label_update.emit("No Windows build available")
                self.signals.sub_label_update.emit("Could not find compatible Lc0 build")
                self.signals.show_retry.emit()
                return None
            
            # Sort by size and prefer dnnl/openblas (smaller, universal)
            def sort_key(asset):
                name = asset["name"].lower()
                if "dnnl" in name or "openblas" in name:
                    return (0, asset.get("size", 0))
                return (1, asset.get("size", 0))
            
            best_asset = min(filtered, key=sort_key)
            
        elif self.os_name == "linux":
            # Linux: No pre-built binaries, show build instructions
            self.signals.label_update.emit("Lc0 requires building from source on Linux")
            self.signals.sub_label_update.emit(
                "Lc0 does not provide pre-built Linux binaries.\n\n"
                "To build Lc0 from source, visit the releases page and follow the build instructions.\n\n"
                "Alternatively, you can use Maia chess engine which will be downloaded automatically."
            )
            self.link_btn.show()
            return None
            
        elif self.os_name == "mac":
            for asset in assets:
                name = asset["name"].lower()
                if "mac" in name or "macos" in name:
                    filtered.append(asset)
            
            if not filtered:
                logger.error("No macOS build found for Lc0")
                self.signals.label_update.emit("No macOS build available")
                self.signals.sub_label_update.emit("Could not find compatible Lc0 build")
                self.signals.show_retry.emit()
                return None
            
            best_asset = max(filtered, key=lambda a: a.get("size", 0))
        else:
            logger.error(f"Unknown OS: {self.os_name}")
            self.signals.label_update.emit("Unsupported platform")
            self.signals.show_retry.emit()
            return None
        
        logger.info(f"Selected Lc0: {best_asset['name']}")
        self.signals.sub_label_update.emit(f"Selected: {best_asset['name']}")
        return best_asset
    
    def _download_asset(self, asset, tag_name):
        self.signals.label_update.emit(f"Downloading {asset['name']}...")
        asset_name = asset["name"]
        archive_path = os.path.join(tempfile.gettempdir(), asset_name)
        
        if os.path.exists(archive_path):
            local_size = os.path.getsize(archive_path)
            if local_size == int(asset.get("size", 0)):
                logger.info("Using cached download")
                self.signals.sub_label_update.emit("Using cached download")
                return archive_path
        
        try:
            download_file(asset["url"], archive_path, progress_callback=self._create_progress_callback())
            return archive_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.signals.label_update.emit("Download failed")
            self.signals.sub_label_update.emit(str(e))
            self.signals.show_retry.emit()
            return None
    
    def _create_progress_callback(self):
        def progress_cb(d, t, speed_bytes_per_s):
            pct = (d * 100 / t) if t else min(99, d / (1024 * 1024))
            self.signals.progress_update.emit(int(pct))
            speed_mb_s = speed_bytes_per_s / (1024 * 1024)
            if t:
                self.signals.sub_label_update.emit(f"{format_bytes(d)} / {format_bytes(t)} — {speed_mb_s:.2f} MB/s")
        return progress_cb
    
    def _is_already_installed(self, target_path):
        if target_path.exists():
            logger.info(f"Lc0 already installed at {target_path}")
            self.signals.label_update.emit("Already installed")
            self.signals.sub_label_update.emit(str(target_path))
            self.signals.progress_update.emit(100)
            self.signals.close_window.emit(800)
            return True
        return False
    
    def _extract_archive(self, archive_path):
        """Extract archive and return list of extracted files"""
        try:
            extract_dir = os.path.join(tempfile.gettempdir(), "lc0_extract")
            os.makedirs(extract_dir, exist_ok=True)
            
            if archive_path.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(extract_dir)
            else:
                # Handle tar.gz if needed
                import tarfile
                with tarfile.open(archive_path, "r:gz") as tf:
                    tf.extractall(extract_dir)
            
            extracted = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    extracted.append(os.path.join(root, file))
            
            return extracted
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return None
    
    def _find_lc0_binary(self, extracted):
        """Find Lc0 binary in extracted files"""
        for f in extracted:
            name = os.path.basename(f).lower()
            if "lc0" in name and (name.endswith(".exe") or not "." in name):
                if os.path.isfile(f):
                    return f
        return None
    
    def _set_binary_permissions(self, binary_path):
        """Set executable permissions on Unix systems"""
        if self.os_name != "windows":
            try:
                st = Path(binary_path).stat().st_mode
                Path(binary_path).chmod(st | 0o111)
            except Exception as e:
                logger.warning(f"Failed to set permissions: {e}")

# ------------------------ Main ------------------------
def download_maia(target_path=None):
    """
    Main entry point for downloading Maia Chess Engine.
    Creates a QApplication and shows the downloader UI (unless SILENT_MODE is True).
    
    Args:
        target_path: Optional path where to install Maia (currently unused, 
                    the downloader determines the path automatically)
    
    Returns:
        True if download/install succeeded, False otherwise
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app_created = True
    else:
        app_created = False
    
    downloader = MaiaDownloaderApp()
    if not SILENT_MODE:
        downloader.show()
    app.exec()
    
    # Check if maia was successfully installed
    if target_path:
        return Path(target_path).exists()
    
    # Check default locations
    if detect_os() == "windows":
        if getattr(sys, 'frozen', False):
            default_path = Path(sys.executable).parent / "maia.exe"
        else:
            default_path = Path.cwd() / "maia.exe"
    else:
        if getattr(sys, 'frozen', False):
            default_path = Path(sys.executable).parent / "maia"
        else:
            default_path = Path.cwd() / "maia"
    
    return default_path.exists()

def download_lc0(target_path=None):
    """
    Main entry point for downloading Lc0 Chess Engine.
    
    Args:
        target_path: Optional path where to install Lc0
    
    Returns:
        True if download/install succeeded, False otherwise
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app_created = True
    else:
        app_created = False
    
    downloader = Lc0DownloaderApp()
    if not SILENT_MODE:
        downloader.show()
    app.exec()
    
    # Check if lc0 was successfully installed
    if target_path:
        return Path(target_path).exists()
    
    # Check default locations
    if detect_os() == "windows":
        if getattr(sys, 'frozen', False):
            default_path = Path(sys.executable).parent / "lc0.exe"
        else:
            default_path = Path.cwd() / "lc0.exe"
    else:
        if getattr(sys, 'frozen', False):
            default_path = Path(sys.executable).parent / "lc0"
        else:
            default_path = Path.cwd() / "lc0"
    
    return default_path.exists()

if __name__ == "__main__":
    success = download_maia()
    sys.exit(0 if success else 1)
