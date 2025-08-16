import os
import platform
import subprocess
import tarfile
import zipfile
import shutil
import tempfile
import threading
import requests
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import logging
import sys
import time

# ------------------------ Logger ------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
_ch = logging.StreamHandler(sys.stdout)
_ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(_ch)

# ------------------------ Visual style (match ChessPilot) ------------------------
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
    """Detect GPU capabilities for LC0"""
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
            # Check nvidia-smi
            subprocess.run(["nvidia-smi"], capture_output=True, check=True, timeout=5)
            return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    try:
        # Check for NVIDIA driver files on Windows
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
            # Look for cuDNN DLLs
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
                return int(build) >= 10240  # Windows 10 build
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
def choose_best_lc0_asset(assets, os_name, gpu_capabilities):
    """Choose the best LC0 asset based on OS and GPU capabilities.

    If no GPU capabilities are present, prefer CPU builds. If no OS-native
    CPU build is found, fall back to any reasonable CPU build (e.g. amd64/x86).
    """
    logger.debug(f"Choosing best LC0 asset for os={os_name} gpu_caps={gpu_capabilities}")
    filtered = _filter_lc0_assets_by_os(assets, os_name)
    if not filtered:
        logger.debug("No assets after OS filtering; trying relaxed CPU fallback filter")
        # relaxed fallback: consider any assets that look like CPU builds even if they don't mention this OS
        filtered = [a for a in assets if _looks_like_cpu_asset(a["name"])]
        if filtered:
            logger.info("Found CPU-like assets in fallback (non-native); will consider them.")
        else:
            return None

    # If no gpu caps, prefer CPU builds explicitly
    if not gpu_capabilities:
        cpu_candidates = [a for a in filtered if _looks_like_cpu_asset(a["name"])]
        if cpu_candidates:
            logger.info("No GPU detected — preferring CPU builds.")
            return _select_best_lc0_by_gpu(cpu_candidates, gpu_capabilities)
        else:
            logger.info("No explicit CPU build in filtered assets; selecting best available asset (will likely be CPU fallback).")
            return _select_best_lc0_by_gpu(filtered, gpu_capabilities)

    # otherwise pick best for detected GPU/capabilities
    return _select_best_lc0_by_gpu(filtered, gpu_capabilities)

def _filter_lc0_assets_by_os(assets, os_name):
    """Filter LC0 assets by operating system, but allow reasonable cross-platform CPU artifacts.

    This tries to match explicit OS tokens first; if none are found we allow CPU/x86/amd64 archives.
    """
    filtered = []
    for asset in assets:
        name = asset["name"].lower()

        # skip known non-exec packages
        if name.endswith(".apk"):
            continue

        # explicit OS matches
        if os_name == "windows" and "windows" in name:
            filtered.append(asset)
            continue
        if os_name == "linux" and "linux" in name:
            filtered.append(asset)
            continue
        if os_name == "mac" and ("mac" in name or "darwin" in name or "macos" in name):
            filtered.append(asset)
            continue

        # Some releases ship generic archives without an OS token:
        # If the asset looks like a CPU binary for amd64/x86 and doesn't explicitly say "windows",
        # include it as a fallback for linux/mac (useful when maintainers only ship zipped builds).
        if os_name in ("linux", "mac"):
            if ("windows" not in name) and _looks_like_cpu_asset(name):
                filtered.append(asset)
                continue

    logger.debug(f"Assets after OS filter (for {os_name}): {[a['name'] for a in filtered]}")
    return filtered

def _looks_like_cpu_asset(name_lower: str):
    """Heuristic: is this a CPU build / native binary archive?"""
    n = name_lower.lower()
    cpu_tokens = ["cpu", "dnnl", "openblas", "onednn", "onnx", "amd64", "x86_64", "x86", "glibc", "manylinux", ".tar", ".tgz", ".tar.gz", ".tar.xz", ".deb"]
    # Negative tokens to avoid mobile builds etc.
    negative_tokens = ["android", "apk", "arm64", "aarch64", "armv7"]
    if any(tok in n for tok in negative_tokens):
        return False
    return any(tok in n for tok in cpu_tokens)

def _select_best_lc0_by_gpu(filtered_assets, gpu_capabilities):
    """Select the best LC0 build based on GPU capabilities"""
    scored_assets = []
    
    for asset in filtered_assets:
        name = asset["name"].lower()
        score = _calculate_lc0_score(name, gpu_capabilities)
        scored_assets.append((asset, score))
        logger.debug(f"Asset {asset['name']}: score {score}")
    
    if not scored_assets:
        return None
    
    # Sort by score (highest first)
    scored_assets.sort(key=lambda x: x[1], reverse=True)
    best_asset = scored_assets[0][0]
    
    logger.info(f"Selected best asset: {best_asset['name']} (score: {scored_assets[0][1]})")
    return best_asset

def _calculate_lc0_score(asset_name, gpu_capabilities):
    """Calculate score for LC0 asset based on capabilities"""
    n = asset_name.lower()
    score = 0
    
    # GPU-accelerated builds get higher scores
    if "cudnn" in n and "cudnn" in gpu_capabilities:
        score += 200  # top preference for NVIDIA + cuDNN
    if "cuda" in n and "cuda" in gpu_capabilities:
        score += 180
    if "dx12" in n and "dx12" in gpu_capabilities:
        score += 170
    if "opencl" in n and "opencl" in gpu_capabilities:
        score += 150
    if "gpu" in n and gpu_capabilities:
        score += 120

    # If no GPU capabilities, prefer CPU-related tokens
    if not gpu_capabilities:
        if any(tok in n for tok in ("dnnl", "openblas", "onednn", "cpu", "amd64", "x86_64", "x86")):
            score += 120

    # Prefer builds with DLLs included (easier setup) -- for Windows platforms this helps
    if "nodll" not in n:
        score += 20

    # Prefer optimized CPU builds over basic ones
    if "dnnl" in n or "openblas" in n or "onednn" in n:
        score += 40
    elif "cpu" in n:
        score += 15   # Basic CPU fallback

    # ONNX builds are often optimized
    if "onnx" in n:
        score += 25

    # Slight preference for native OS mention (avoid choosing a windows build for linux unless nothing else)
    if "linux" in n:
        score += 10
    if "windows" in n:
        score += 5

    # Avoid android/apk unless explicitly running android
    if "apk" in n or "android" in n:
        score -= 200

    return score

# ------------------------ Download & extraction ------------------------
def download_file(url, dest_path, progress_callback=None, chunk_size=8192, timeout=30):
    """
    Downloads a file while calling progress_callback(downloaded_bytes, total_bytes_or_None, speed_bytes_per_sec)
    """
    logger.debug(f"Starting download: {url} -> {dest_path}")
    start_time = time.time()
    downloaded = 0
    last_report_time = start_time

    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
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
                        
                        if (now - last_report_time) >= 0.4 or downloaded == total:
                            last_report_time = now
                            if progress_callback:
                                try:
                                    progress_callback(downloaded, total, speed)
                                except Exception as e:
                                    logger.warning(f"Progress callback error: {e}")
                                    
    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed: {e}")
        raise
    except IOError as e:
        logger.error(f"File write error: {e}")
        raise
        
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
            elif self._is_tar_archive():
                extracted = self._extract_tar()
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

        binary_path = self._find_lc0_binary(extracted)
        if binary_path:
            self._set_binary_permissions(binary_path)
        else:
            self._cleanup()
        
        return binary_path
    
    def _is_tar_archive(self):
        return self.archive_path.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".tar.bz2", ".tar.lz"))
    
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
    
    def _extract_tar(self):
        extracted = []
        with tarfile.open(self.archive_path, "r:*") as t:
            for member in t.getmembers():
                if self._is_safe_path(member.name):
                    try:
                        t.extract(member, self.tmpdir)
                    except Exception as e:
                        logger.debug(f"Could not extract member {member.name}: {e}")
                    
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
    
    def _find_lc0_binary(self, extracted):
        """Find LC0 binary in extracted files"""
        for f in extracted:
            name = os.path.basename(f).lower()
            # Match exe for windows or files named lc0/leela for linux/mac
            if ("lc0" in name or "leela" in name) and (name.endswith(".exe") or not "." in name or name.endswith(".bin")):
                if os.path.isfile(f):  # Make sure it's a file, not a directory
                    return f
        # If above didn't match, try any file that looks executable and mentions lc0/leela anywhere
        for f in extracted:
            name = os.path.basename(f).lower()
            if ("lc0" in name or "leela" in name) and os.path.isfile(f):
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
class LC0DownloadWorkflow:
    def __init__(self, ui_callbacks):
        self.ui = ui_callbacks
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
            self.ui.set_label("Error occurred")
            self.ui.set_sub_label(str(ex))
            self.ui.close_after(1600)
    
    def _is_already_installed(self):
        target_path = self._get_target_path()
        if target_path.exists():
            logger.info(f"LC0 already installed at {target_path} — exiting")
            self.ui.set_label("Already installed")
            self.ui.set_sub_label(str(target_path))
            self.ui.set_progress(100)
            self.ui.close_after(800)
            return True
        return False
    
    def _get_target_path(self):
        # Install next to executable (if frozen) or to current working directory
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
        self.ui.set_label("Fetching latest LC0 release...")
        logger.info("Fetching latest LC0 release metadata from GitHub")
        
        try:
            r = requests.get("https://api.github.com/repos/LeelaChessZero/lc0/releases/latest", timeout=15)
            r.raise_for_status()
            rel = r.json()
            
            tag = rel.get("tag_name", "unknown")
            assets = [{"name": a["name"], "url": a["browser_download_url"], "size": a.get("size", 0)} 
                     for a in rel.get("assets", []) if not a["name"].endswith(".apk")]  # Skip Android APK
            
            logger.debug(f"Found {len(assets)} assets: {[a['name'] for a in assets]}")
            return {"tag_name": tag, "assets": assets}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch release metadata: {e}")
            self.ui.set_label("Network error")
            self.ui.set_sub_label("Could not fetch release info")
            self.ui.close_after(1200)
            return None
    
    def _select_asset(self, release_data):
        best_asset = choose_best_lc0_asset(release_data["assets"], self.os_name, self.gpu_capabilities)
        if not best_asset:
            logger.error("No matching LC0 build found for this OS/GPU")
            self.ui.set_label("No matching build found")
            self.ui.set_sub_label("See logs for details")
            self.ui.close_after(1200)
            return None
            
        logger.info(f"Selected asset: {best_asset['name']} (release {release_data['tag_name']})")
        return best_asset
    
    def _download_asset(self, best_asset, tag_name):
        self.ui.set_label(f"{tag_name} — {best_asset['name']}")
        asset_name = best_asset["name"]
        archive_path = os.path.join(tempfile.gettempdir(), asset_name)

        if self._is_cached_and_valid(archive_path, best_asset):
            self.ui.set_sub_label("Using existing archive")
            self.ui.set_progress(5)
            return archive_path

        self.ui.set_label(f"Downloading {asset_name}...")
        try:
            download_file(best_asset["url"], archive_path, progress_callback=self._create_progress_callback())
            return archive_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.ui.set_label("Download failed")
            self.ui.set_sub_label("See logs for details")
            self.ui.close_after(1400)
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
            self.ui.set_progress(pct)
            mbps = (speed_bytes_per_s * 8) / (1000 * 1000)
            speed_mb_s = speed_bytes_per_s / (1024 * 1024)
            if t:
                self.ui.set_sub_label(f"{format_bytes(d)} / {format_bytes(t)} — {speed_mb_s:.2f} MB/s ({mbps:.2f} Mbps)")
            else:
                self.ui.set_sub_label(f"{format_bytes(d)} — {speed_mb_s:.2f} MB/s ({mbps:.2f} Mbps)")
        return progress_cb
    
    def _extract_binary(self, archive_path):
        self.ui.set_label("Extracting binary...")
        logger.info("Extracting LC0 binary from archive")
        bin_path = extract_binary(archive_path)
        if not bin_path:
            logger.error("Could not find LC0 binary inside the archive")
            self.ui.set_label("Binary not found in archive")
            self.ui.set_sub_label("See logs")
            self.ui.close_after(1400)
            return None
        
        self.ui.set_progress(75)
        return bin_path
    
    def _install_binary(self, bin_path):
        self.ui.set_label("Installing...")
        target_path = self._get_target_path()
        
        try:
            # Copy all files from the extraction directory to preserve DLLs
            extraction_dir = os.path.dirname(bin_path)
            target_dir = target_path.parent
            
            # Copy the main binary
            shutil.copy2(bin_path, target_path)
            
            # Copy any DLL files if on Windows (MINIMAL CHANGE: use recursive glob to pick DLLs in subdirs)
            if self.os_name == "windows":
                # copy all dlls found anywhere under extraction_dir into the target_dir (do not overwrite existing files)
                for file_path in Path(extraction_dir).glob("**/*.dll"):
                    dll_target = target_dir / file_path.name
                    if not dll_target.exists():  # Don't overwrite system DLLs
                        try:
                            shutil.copy2(file_path, dll_target)
                            logger.info(f"Copied DLL: {file_path.relative_to(extraction_dir)} -> {dll_target}")
                        except Exception as e:
                            logger.warning(f"Failed to copy DLL {file_path}: {e}")
            
            if self.os_name != "windows":
                os.chmod(target_path, 0o755)
                
            logger.info("Installed LC0 to %s", target_path)
            self.ui.set_label(f"Installed LC0")
            self.ui.set_sub_label(f"Location: {target_path}")
            self.ui.set_progress(100)
            self.ui.close_after(1200)
            
        except (OSError, IOError) as e:
            logger.error(f"Failed to install LC0: {e}")
            self.ui.set_label("Install failed")
            self.ui.set_sub_label(str(e))
            self.ui.close_after(1400)

# ------------------------ Downloader UI ------------------------
class LC0DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LC0 (Leela Chess Zero) Downloader")
        self.root.geometry("400x160")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self._setup_styles()
        self._create_widgets()
        
        # Start the operation in a daemon thread
        threading.Thread(target=self._start_download_flow, daemon=True).start()

    def _setup_styles(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            logger.warning("Could not set clam theme")
            
        self.style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR)
        self.style.configure("TButton", background=FRAME_COLOR, foreground=TEXT_COLOR)
        self.style.configure("TProgressbar", troughcolor=FRAME_COLOR)
        self.root.configure(bg=BG_COLOR)
    
    def _create_widgets(self):
        self.label = ttk.Label(self.root, text="Preparing...", anchor="w")
        self.label.pack(fill="x", padx=12, pady=(12, 6))

        self.progress = tk.DoubleVar(value=0.0)
        self.pb = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", 
                                 variable=self.progress, length=360)
        self.pb.pack(padx=12, pady=(0, 6))

        self.sub_label = ttk.Label(self.root, text="", anchor="w")
        self.sub_label.pack(fill="x", padx=12, pady=(0, 6))

    def set_label(self, text):
        self.root.after(0, lambda: self.label.config(text=text))
        
    def set_sub_label(self, text):
        self.root.after(0, lambda: self.sub_label.config(text=text))
        
    def set_progress(self, pct):
        self.root.after(0, lambda: self.progress.set(pct))

    def close_after(self, ms=900):
        logger.debug("Window will close in %d ms", ms)
        self.root.after(ms, self.root.destroy)

    def _start_download_flow(self):
        workflow = LC0DownloadWorkflow(self)
        workflow.execute()

def download_lc0(target: Path | None = None):
    """
    Main entry point to run the LC0 downloader app.
    Accepts optional `target` Path (e.g. Path('/usr/bin/lc0')).
    """
    root = tk.Tk()
    app = LC0DownloaderApp(root)
    root.mainloop()
    return str(target) if target else None

# ------------------------ Main ------------------------
if __name__ == "__main__":
    download_lc0()
