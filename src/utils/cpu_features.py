"""
CPU architecture and feature detection for ChessPilot.
Determines OS, vendor, CPU architecture, and SIMD instruction sets (AVX512, AVX2, SSE4.2, etc.).
"""

import os
import platform
import subprocess
import logging
import cpuinfo

logger = logging.getLogger(__name__)


def detect_os() -> str:
    """Detect operating system name normalized to 'windows', 'linux', or 'mac'."""
    p = platform.system().lower()
    if "windows" in p:
        return "windows"
    if "linux" in p:
        return "linux"
    if "darwin" in p:
        return "mac"
    return p


def format_bytes(n: int) -> str:
    """Formats a byte count into a human-readable string (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(n) < 1024.0:
            return f"{n:3.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def detect_cpu_info():
    """
    Detect CPU architecture, vendor, and instruction flags.
    Returns: (arch: str, vendor: str, flags: set)
    """
    arch = platform.machine().lower()
    os_name = detect_os()
    
    vendor = "unknown"
    flags = set()
    
    try:
        if os_name == "linux":
            vendor, flags = _detect_linux_cpu_info()
        elif os_name == "mac":
            vendor, flags = _detect_mac_cpu_info()
        elif os_name == "windows":
            vendor, flags = _detect_windows_cpu_info()
    except Exception as e:
        logger.warning(f"CPU detection failed, using defaults: {e}")
        vendor = "generic"
        flags = {"sse4_1", "sse4_2", "popcnt"}
    
    logger.info(f"CPU Vendor: {vendor}, Flags: {sorted(flags)[:10]}...")
    return arch, vendor, flags


def _detect_linux_cpu_info():
    vendor = "unknown"
    flags = set()
    
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                line_lower = line.lower()
                if "vendor_id" in line_lower:
                    if "amd" in line_lower:
                        vendor = "amd"
                    elif "intel" in line_lower:
                        vendor = "intel"
                elif "flags" in line_lower:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        flags.update(parts[1].strip().split())
    except Exception as e:
        logger.warning(f"Could not read /proc/cpuinfo: {e}")
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            out = subprocess.check_output(["/usr/bin/lscpu"], text=True, timeout=10, creationflags=creation_flags)
            for line in out.splitlines():
                if "vendor id" in line.lower():
                    if "amd" in line.lower():
                        vendor = "amd"
                    elif "intel" in line.lower():
                        vendor = "intel"
                elif "flags" in line.lower():
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        flags.update(parts[1].strip().split())
        except Exception as e2:
            logger.warning(f"lscpu also failed: {e2}")
            
    return vendor, flags


def _detect_mac_cpu_info():
    vendor = "apple" if "arm" in platform.machine().lower() else "intel"
    flags = set()
    
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.features"], text=True, timeout=10, creationflags=creation_flags)
        flags.update(out.lower().split())
        
        try:
            out2 = subprocess.check_output(["sysctl", "-n", "machdep.cpu.leaf7_features"], text=True, timeout=10, creationflags=creation_flags)
            flags.update(out2.lower().split())
        except (subprocess.SubprocessError, OSError) as err:
            logger.debug("Optional leaf7 features not available on macOS: %s", err)
    except Exception as e:
        logger.warning(f"Could not get Mac CPU features: {e}")
        
    return vendor, flags


def _detect_windows_cpu_info():
    vendor = _get_cpu_vendor()
    flags = _get_cpu_flags()
    return vendor, flags


def _get_cpu_vendor():
    vendor = _try_cpuinfo_vendor()
    if vendor != "unknown":
        return vendor
        
    vendor = _try_platform_vendor()
    if vendor != "unknown":
        return vendor
        
    return _try_wmic_vendor()


def _try_cpuinfo_vendor():
    try:
        info = cpuinfo.get_cpu_info()
        brand = info.get('brand_raw', '').lower()
        vendor_id = info.get('vendor_id_raw', '').lower()
        
        if 'amd' in brand or 'amd' in vendor_id:
            return "amd"
        elif 'intel' in brand or 'intel' in vendor_id:
            return "intel"
    except Exception as e:
        logger.debug(f"py-cpuinfo vendor detection failed: {e}")
    return "unknown"


def _try_platform_vendor():
    proc = platform.processor().lower()
    if 'amd' in proc:
        return "amd"
    elif 'intel' in proc:
        return "intel"
    return "unknown"


def _try_wmic_vendor():
    wmic_path = _get_wmic_path()
    if not wmic_path:
        return "unknown"
        
    try:
        out = _run_wmic_command(wmic_path)
        return _parse_vendor_from_string(out)
    except Exception as e:
        logger.warning(f"WMIC query failed: {e}")
        return "unknown"


def _get_wmic_path():
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    wmic_path = os.path.join(system_root, "System32", "wbem", "WMIC.exe")
    
    if os.path.exists(wmic_path):
        return wmic_path
        
    import shutil
    return shutil.which("wmic")


def _run_wmic_command(wmic_path):
    cmd = [wmic_path, "cpu", "get", "name,manufacturer", "/format:list"]
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.check_output(cmd, text=True, timeout=10, creationflags=creation_flags).lower()


def _parse_vendor_from_string(text):
    if "amd" in text or "authenticamd" in text:
        return "amd"
    elif "intel" in text or "genuineintel" in text:
        return "intel"
    return "unknown"


def _get_cpu_flags():
    flags = _try_cpuinfo_flags()
    if flags:
        return flags
        
    return _get_default_windows_flags()


def _try_cpuinfo_flags():
    try:
        info = cpuinfo.get_cpu_info()
        flags = set(info.get('flags', []))
        if flags:
            logger.debug(f"Got {len(flags)} flags from py-cpuinfo")
            return flags
    except Exception as e:
        logger.debug(f"py-cpuinfo flags detection failed: {e}")
    return set()


def _get_default_windows_flags():
    flags = {"sse", "sse2", "sse3", "ssse3", "sse4_1", "sse4_2", "popcnt"}
    if _is_64bit_system():
        flags.add("avx")
        flags.add("avx2")
    logger.debug("Using default Windows flags based on architecture")
    return flags


def _is_64bit_system():
    machine = platform.machine().lower()
    return "64" in machine or "arm64" in machine


def detect_arch_flags():
    """Detect CPU architecture flags."""
    arch, _, flags = detect_cpu_info()
    return flags
