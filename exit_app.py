"""Exit PhraseLock from the tray icon.

The tray lives inside the background monitor, which cannot show Tk dialogs from its tray thread. So
"Exit PhraseLock" starts a short-lived process (``--exit-monitor <pid>``) that asks for confirmation
(and the emergency password when one is set), then stops the watchdog first, so it cannot restart
anything, and finally the monitor itself.
"""

import os
import sys

from config import load_config, log
from stats import verify_emergency_password

MAX_TRIES = 3


def parse_pid(argv):
    """The monitor pid after --exit-monitor, or None."""
    try:
        return int(argv[argv.index("--exit-monitor") + 1])
    except (ValueError, IndexError):
        return None


def needs_password(cfg):
    return bool(cfg.get("emergency_password_hash"))


def check_password(cfg, ask):
    """True when *ask()* returns the emergency password within MAX_TRIES attempts.

    ask(attempt_number) returns the typed text, or None when the person cancels.
    """
    for attempt in range(1, MAX_TRIES + 1):
        typed = ask(attempt)
        if typed is None:
            return False
        if verify_emergency_password(cfg, typed):
            return True
    return False


def stop_everything(monitor_pid, exe_path, frozen, own_pid=None):
    """Stop the watchdog(s), then the monitor. Returns (stopped, failed) pids."""
    import uninstall
    own = (own_pid if own_pid is not None else os.getpid(),)
    targets = [p for p in uninstall.find_processes(exe_path, frozen, own_pids=own) if p["role"] == "watchdog"]
    if monitor_pid and monitor_pid not in own:
        targets.append({"pid": monitor_pid, "role": "app"})
    return uninstall.stop_processes(targets)


def run(argv):
    """Entry point for ``--exit-monitor <pid>``."""
    import tkinter as tk
    from tkinter import messagebox, simpledialog

    pid = parse_pid(argv)
    cfg = load_config()
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if needs_password(cfg):
            def ask(attempt):
                text = "Enter the emergency password to exit PhraseLock."
                if attempt > 1:
                    text = f"Wrong password ({attempt}/{MAX_TRIES}). Try again."
                return simpledialog.askstring("Exit PhraseLock", text, show="*", parent=root)

            if not check_password(cfg, ask):
                log("Exit from the tray refused (password).")
                return False
        elif not messagebox.askyesno("Exit PhraseLock", "Exit PhraseLock?\n\nThe protection stops until you "
                                     "start PhraseLock again.", icon="warning", default="no", parent=root):
            return False
        stopped, failed = stop_everything(pid, sys.executable, bool(getattr(sys, "frozen", False)))
        log(f"Exit from the tray: stopped {stopped}, failed {failed}.")
        if failed:
            messagebox.showerror("Exit PhraseLock", "Some PhraseLock processes could not be stopped. "
                                 "Close them from the Task Manager.", parent=root)
        return not failed
    finally:
        root.destroy()
