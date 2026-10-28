"""Update checker: compares the installed version with the latest GitHub release.

Only one request is made (the public "latest release" endpoint, no account, nothing about you is
sent). Everything that decides something is a pure function so it can be tested; ``fetch_latest``
is the only part that touches the network.
"""

import json
import re
import threading
import urllib.request
from datetime import date

from version import __version__

REPO = "nanana677777/phraselock"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
TIMEOUT_SECONDS = 8
_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text):
    """(major, minor, patch) from '1.2.3', 'v1.2' or 'PhraseLock 1.2.3-beta'; None when there is none."""
    match = _VERSION_RE.search(str(text or ""))
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def is_newer(latest, current):
    a, b = parse_version(latest), parse_version(current)
    return bool(a and b and a > b)


def parse_release(data):
    """{"version", "url", "name"} from the GitHub API answer, or None when it is not a usable release."""
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag = data.get("tag_name")
    if not isinstance(tag, str) or parse_version(tag) is None:
        return None
    url = data.get("html_url")
    if not (isinstance(url, str) and url.startswith("https://github.com/")):
        url = RELEASES_URL
    name = data.get("name") if isinstance(data.get("name"), str) else ""
    return {"version": tag.strip().lstrip("vV"), "url": url, "name": name.strip()}


def fetch_latest(opener=urllib.request.urlopen):
    """Latest release as parse_release() describes it. Raises on a network or format problem."""
    request = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json", "User-Agent": f"PhraseLock/{__version__}"})
    with opener(request, timeout=TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))
    release = parse_release(data)
    if release is None:
        raise ValueError("no published release found")
    return release


def check(current=__version__, fetch=fetch_latest):
    """{"status": "newer"|"current"|"error", "current", "latest", "url", "error"}"""
    try:
        release = fetch()
    except Exception as exc:
        return {"status": "error", "current": current, "latest": "", "url": RELEASES_URL,
                "error": str(exc) or exc.__class__.__name__}
    status = "newer" if is_newer(release["version"], current) else "current"
    return {"status": status, "current": current, "latest": release["version"], "url": release["url"], "error": ""}


def due(cfg, today=None):
    """True when the automatic check is on and has not run today."""
    if not cfg.get("check_updates", True):
        return False
    return cfg.get("last_update_check", "") != (today or date.today().isoformat())


def check_in_background(callback, current=__version__, fetch=fetch_latest):
    """Run check() in a thread; callback(result) is called from that thread."""
    def work():
        callback(check(current, fetch))
    thread = threading.Thread(target=work, name="PhraseLockUpdateCheck", daemon=True)
    thread.start()
    return thread


def describe(result):
    """One line for the Settings window."""
    if result["status"] == "newer":
        return f"A new version is available: {result['latest']} (you have {result['current']})."
    if result["status"] == "current":
        return f"You are up to date ({result['current']})."
    return f"Could not check for updates: {result['error']}"
