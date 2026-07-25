import sys
import webbrowser
from utils.logger import setup_logger

log = setup_logger("aria.spotify")


def play_song(uri=None):
    if not uri:
        uri = "https://open.spotify.com/track/39shmbIHICJ2Wxnk1fPSdz?si=2900c75c2e2d4b82"
    try:
        if sys.platform == "win32":
            import os
            os.startfile(uri)
        else:
            webbrowser.open(uri)
        return f"Playing {uri}"
    except Exception as e:
        return f"Failed to open Spotify: {e}"
