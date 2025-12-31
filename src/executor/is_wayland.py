import os

def is_wayland():
    return os.getenv("XDG_SESSION_TYPE") == "wayland"
