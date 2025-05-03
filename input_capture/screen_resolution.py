import subprocess
import re
import os
import sys
import shutil

def get_binary_path(binary):
    # Append .exe for Windows if necessary.
    if os.name == "nt" and not binary.endswith(".exe"):
        binary += ".exe"
        
    if getattr(sys, 'frozen', False):
        # When bundled, look in the _MEIPASS directory.
        path = os.path.join(sys._MEIPASS, binary)
    else:
        # Look for the binary in the system PATH.
        path = shutil.which(binary)
        if path is None:
            path = binary

    if not (path and os.path.exists(path)):
        raise FileNotFoundError(f"{binary} is missing! Make sure it's bundled properly.")
    return path

def get_resolution():
    try:
        # Use the helper to resolve the binary path for wayland-info
        wayland_info_binary = get_binary_path("wayland-info")
        output = subprocess.run([wayland_info_binary], capture_output=True, text=True, check=True)
        match = re.search(r"width: (\d+) px, height: (\d+) px", output.stdout)
        if match:
            return match.group(1), match.group(2)
        else:
            return "Resolution not found"
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print(get_resolution())
