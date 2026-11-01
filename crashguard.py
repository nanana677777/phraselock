"""Crash-loop guard: if PhraseLock (or its watchdog) keeps failing, it turns itself off.

Why: with Auto-protection a watchdog restarts the monitor whenever it disappears. If the monitor
crashes at startup, that would loop forever. This module counts how often the monitor started, and
how often the watchdog restarted it, inside a sliding window. Past the limit it switches the
protection off (``enabled`` and ``auto_protection`` set to false in config.json), writes a note that
the Settings window shows, and the caller stops. Re-enabling is one click in Settings > Home.

It only uses the standard library, so the watchdog can import it cheaply, and it never raises:
a guard that crashes would be worse than none.
"""

import json
import os
import time

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", "."), "PhraseLock")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
STATE_PATH = os.path.join(CONFIG_DIR, "crash_guard.json")

LIMIT = 5                 # this many events ...
WINDOW_SECONDS = 600      # ... within this many seconds trips the guard
STABLE_SECONDS = 180      # a monitor that stays up this long clears its start history
KINDS = ("monitor_start", "watchdog_restart")


def _read(path=None):
    try:
        with open(path or STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write(data, path=None):
    path = path or STATE_PATH
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def recent(times, now, window=WINDOW_SECONDS):
    """The timestamps in *times* that are inside the window ending at *now* (junk is dropped)."""
    good = []
    for value in times if isinstance(times, list) else []:
        if isinstance(value, (int, float)) and not isinstance(value, bool) and now - window <= value <= now + 60:
            good.append(float(value))
    return good


def record(kind, now=None, state_path=None, limit=LIMIT, window=WINDOW_SECONDS):
    """Note one event of *kind*. Returns True when this event trips the guard (limit reached)."""
    try:
        now = time.time() if now is None else now
        state = _read(state_path)
        history = state.get("history") if isinstance(state.get("history"), dict) else {}
        times = recent(history.get(kind), now, window)
        times.append(now)
        history[kind] = times
        state["history"] = history
        _write(state, state_path)
        return len(times) >= limit
    except Exception:
        return False


def clear_history(kind=None, state_path=None):
    """Forget the counted events (all kinds, or just one). The trip note is kept."""
    try:
        state = _read(state_path)
        history = state.get("history") if isinstance(state.get("history"), dict) else {}
        if kind is None:
            history = {}
        else:
            history.pop(kind, None)
        state["history"] = history
        _write(state, state_path)
    except Exception:
        pass


def disable_protection(config_path=None):
    """Set enabled and auto_protection to false in config.json. True when it was written."""
    path = config_path or CONFIG_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            cfg = {}
    except FileNotFoundError:
        cfg = {}
    except Exception:
        return False        # unreadable config: do not overwrite what we cannot parse
    cfg["enabled"] = False
    cfg["auto_protection"] = False
    return _write(cfg, path)


def trip(kind, now=None, state_path=None, config_path=None):
    """Turn the protection off and leave a note for Settings. Returns the note."""
    now = time.time() if now is None else now
    note = {"tripped_at": now, "kind": kind if kind in KINDS else "monitor_start"}
    state = _read(state_path)
    state["tripped"] = note
    state["history"] = {}
    _write(state, state_path)
    disable_protection(config_path)
    return note


def tripped(state_path=None):
    """The note left by trip(), or None."""
    note = _read(state_path).get("tripped")
    if isinstance(note, dict) and isinstance(note.get("tripped_at"), (int, float)):
        return note
    return None


def reset(state_path=None):
    """Remove the note and the history (after the user turned protection back on)."""
    try:
        _write({"history": {}}, state_path)
    except Exception:
        pass


def describe(note):
    """One sentence for the Settings banner."""
    when = time.strftime("%H:%M", time.localtime(note["tripped_at"]))
    if note.get("kind") == "watchdog_restart":
        what = "kept having to restart"
    else:
        what = "kept failing to start"
    return (f"PhraseLock turned itself off at {when} because it {what} "
            f"({LIMIT} times in {WINDOW_SECONDS // 60} minutes). Look at phraselock.log, then turn it back on.")


def start_stability_timer(seconds=STABLE_SECONDS):
    """After *seconds* of the monitor staying alive, forget its recent starts. Returns the timer."""
    import threading
    timer = threading.Timer(seconds, lambda: clear_history("monitor_start"))
    timer.daemon = True
    timer.start()
    return timer
