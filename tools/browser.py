import os
import subprocess
import sys
import webbrowser
from utils.logger import setup_logger

log = setup_logger("aria.browser")


def _chrome_executable():
    if sys.platform == "win32":
        for base in (
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ):
            if not base:
                continue
            p = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.isfile(p):
                return p
    return None


def open_chrome(url=None, monitor=1, fullscreen=False):
    chrome = _chrome_executable()
    if not chrome:
        log.warning("Chrome not found, opening in default browser")
        if url:
            webbrowser.open(url)
        return "Chrome not found, opened in default browser"
    args = [chrome, "--new-window"]
    if fullscreen and sys.platform == "win32":
        args.append("--start-fullscreen")
    if url:
        args.append(url)
    try:
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opened Chrome with {url if url else 'new tab'}"
    except OSError as e:
        return f"Failed to open Chrome: {e}"


def open_url(url):
    webbrowser.open(url)
    return f"Opened {url}"
