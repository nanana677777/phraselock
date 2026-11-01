"""Open the configuration folder and the log file from Settings."""

import os
import subprocess
import sys


def _default_open(path):
    if hasattr(os, "startfile"):
        os.startfile(path)                      # Windows: default app / Explorer
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def open_folder(path, opener=_default_open):
    """Create the folder if needed and open it. Returns (ok, message)."""
    try:
        os.makedirs(path, exist_ok=True)
        opener(path)
        return True, ""
    except Exception as exc:
        return False, f"Could not open {path}:\n{exc}"


def open_file(path, opener=_default_open):
    """Open an existing file. Returns (ok, message); a missing file is explained, not an error."""
    if not os.path.isfile(path):
        return False, "There is no log yet: PhraseLock writes one the first time something goes wrong " \
                      "or the background monitor starts."
    try:
        opener(path)
        return True, ""
    except Exception as exc:
        return False, f"Could not open {path}:\n{exc}"
