import os
import subprocess
import sys
from utils.logger import setup_logger

log = setup_logger("aria.cursor")


def _cursor_executable():
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        for sub in ("Programs\\cursor\\Cursor.exe", "Programs\\Cursor\\Cursor.exe"):
            p = os.path.join(local, sub) if local else ""
            if p and os.path.isfile(p):
                return p
    return None


def focus_cursor():
    exe = _cursor_executable()
    if not exe:
        return "Cursor not found. Install Cursor or add it to PATH."
    try:
        subprocess.Popen([exe], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Cursor opened"
    except OSError as e:
        return f"Failed to open Cursor: {e}"
