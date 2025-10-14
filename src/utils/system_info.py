"""
System information utilities for diagnostics and troubleshooting.
"""
import platform
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_system_info():
    """
    Gather comprehensive system information for diagnostics.
    
    Returns:
        dict: System information including OS, Python version, CPU, etc.
    """
    info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'os_release': platform.release(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'python_version': sys.version,
        'python_implementation': platform.python_implementation(),
        'executable': sys.executable,
    }
    
    # Try to get CPU info
    try:
        import cpuinfo
        cpu_info = cpuinfo.get_cpu_info()
        info['cpu_brand'] = cpu_info.get('brand_raw', 'Unknown')
        info['cpu_hz'] = cpu_info.get('hz_advertised_friendly', 'Unknown')
        info['cpu_count'] = cpu_info.get('count', 'Unknown')
        info['cpu_flags'] = len(cpu_info.get('flags', []))
    except ImportError:
        logger.debug("cpuinfo module not available")
        info['cpu_brand'] = 'Unknown (cpuinfo not installed)'
    except Exception as e:
        logger.warning(f"Could not get CPU info: {e}")
        info['cpu_brand'] = 'Unknown'
    
    return info


def log_system_info():
    """
    Log system information for debugging purposes.
    """
    logger.info("=" * 60)
    logger.info("ChessPilot System Information")
    logger.info("=" * 60)
    
    info = get_system_info()
    
    logger.info(f"Operating System: {info['os']} {info['os_release']}")
    logger.info(f"OS Version: {info['os_version']}")
    logger.info(f"Architecture: {info['architecture']}")
    logger.info(f"Processor: {info['processor']}")
    
    if 'cpu_brand' in info:
        logger.info(f"CPU Brand: {info['cpu_brand']}")
    if 'cpu_hz' in info:
        logger.info(f"CPU Speed: {info['cpu_hz']}")
    if 'cpu_count' in info:
        logger.info(f"CPU Cores: {info['cpu_count']}")
    if 'cpu_flags' in info:
        logger.info(f"CPU Features: {info['cpu_flags']} flags detected")
    
    logger.info(f"Python Version: {info['python_implementation']} {platform.python_version()}")
    logger.info(f"Python Executable: {info['executable']}")
    logger.info(f"Working Directory: {Path.cwd()}")
    
    logger.info("=" * 60)


def check_dependencies():
    """
    Check if all required dependencies are installed.
    
    Returns:
        dict: Dictionary of dependency names and their availability
    """
    dependencies = {
        'PyQt6': False,
        'PIL': False,
        'numpy': False,
        'onnxruntime': False,
        'mss': False,
        'pyautogui': False,
        'requests': False,
        'cpuinfo': False,
    }
    
    for dep in dependencies.keys():
        try:
            if dep == 'PIL':
                __import__('PIL')
            else:
                __import__(dep.lower())
            dependencies[dep] = True
        except ImportError:
            dependencies[dep] = False
    
    return dependencies


def log_dependency_status():
    """
    Log the status of all dependencies.
    """
    logger.info("Checking dependencies...")
    deps = check_dependencies()
    
    all_present = True
    for name, available in deps.items():
        status = "✓ Installed" if available else "✗ Missing"
        level = logging.INFO if available else logging.WARNING
        logger.log(level, f"  {name}: {status}")
        if not available:
            all_present = False
    
    if all_present:
        logger.info("All dependencies are installed")
    else:
        logger.warning("Some dependencies are missing. Run: pip install -r requirements.txt")
    
    return all_present
