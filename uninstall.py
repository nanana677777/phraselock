"""Uninstall and cleanup: stop PhraseLock, remove its start-with-Windows shortcut and its data.

PhraseLock has no installer: it is one .exe plus a data folder (%APPDATA%\\PhraseLock) and an
optional shortcut in the Startup folder. This module undoes all of that on request. Everything
that touches the system takes its paths as arguments so it can be tested; the window that asks
what to remove (``ask_options``) is the only Tk part.
"""

import os
import shutil
import subprocess

SCRIPT_NAMES = ("phrase_lock.py", "PhraseLockWatchdog.py")
WATCHDOG_EXE_NAMES = ("phraselockwatchdog.exe",)


# ---------------------------------------------------------------------------
# processes
# ---------------------------------------------------------------------------

def _norm(path):
    return os.path.normcase(os.path.abspath(str(path)))


def classify(info, exe_path, frozen):
    """"watchdog", "app" or None for a process described by ``{"exe": ..., "cmdline": [...]}``."""
    exe = info.get("exe")
    args = [str(a) for a in (info.get("cmdline") or [])]
    if frozen:
        if exe and str(exe).replace("\\", "/").rsplit("/", 1)[-1].lower() in WATCHDOG_EXE_NAMES:
            return "watchdog"
        if exe and exe_path and _norm(exe) == _norm(exe_path):
            return "watchdog" if "--watchdog" in args else "app"
        return None
    names = [os.path.basename(a) for a in args[:3]]
    if "PhraseLockWatchdog.py" in names:
        return "watchdog"
    if "phrase_lock.py" in names:
        return "watchdog" if "--watchdog" in args else "app"
    return None


def find_processes(exe_path, frozen, own_pids=(), process_iter=None):
    """[{"pid", "role"}] for the other PhraseLock processes (never *own_pids*)."""
    if process_iter is None:
        try:
            import psutil
        except ImportError:
            return []
        process_iter = lambda: psutil.process_iter(["pid", "exe", "cmdline"])   # noqa: E731
    found = []
    for proc in process_iter():
        try:
            info = proc.info
            if info.get("pid") in own_pids:
                continue
            role = classify(info, exe_path, frozen)
        except Exception:
            continue
        if role:
            found.append({"pid": info["pid"], "role": role})
    return sorted(found, key=lambda p: (p["role"] != "watchdog", p["pid"]))


def stop_processes(processes, grace=3.0):
    """Stop the watchdog first (so it cannot restart anything), then the rest.

    Returns (stopped, failed) lists of pids.
    """
    try:
        import psutil
    except ImportError:
        return [], [p["pid"] for p in processes]
    stopped, failed = [], []
    for role in ("watchdog", "app"):
        batch = []
        for item in (p for p in processes if p["role"] == role):
            try:
                proc = psutil.Process(item["pid"])
                proc.terminate()
                batch.append(proc)
            except psutil.NoSuchProcess:
                stopped.append(item["pid"])
            except (psutil.AccessDenied, OSError):
                failed.append(item["pid"])
        gone, alive = psutil.wait_procs(batch, timeout=grace)
        stopped.extend(p.pid for p in gone)
        for proc in alive:
            try:
                proc.kill()
                proc.wait(timeout=grace)
                stopped.append(proc.pid)
            except Exception:
                failed.append(proc.pid)
    return stopped, failed


# ---------------------------------------------------------------------------
# files
# ---------------------------------------------------------------------------

def data_summary(config_dir):
    """(number of files, total bytes) in the data folder; (0, 0) when it does not exist."""
    count = size = 0
    for folder, _dirs, files in os.walk(config_dir):
        for name in files:
            count += 1
            try:
                size += os.path.getsize(os.path.join(folder, name))
            except OSError:
                pass
    return count, size


def human_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0


def remove_data(config_dir):
    """Delete the data folder. Returns the paths that could not be removed."""
    failed = []
    if not os.path.isdir(config_dir):
        return failed

    def on_error(_func, path, _exc):
        failed.append(path)

    shutil.rmtree(config_dir, onerror=on_error)
    return failed


def remove_startup(shortcut_path):
    """Delete the Startup shortcut. True when it existed and is gone."""
    if shortcut_path and os.path.exists(shortcut_path):
        os.remove(shortcut_path)
        return True
    return False


def schedule_exe_delete(exe_path, frozen, popen=subprocess.Popen):
    """After this process exits, delete the .exe. Only for the packaged build."""
    if not frozen or not exe_path or not str(exe_path).lower().endswith(".exe") or '"' in str(exe_path):
        return False
    if not os.path.isfile(exe_path):
        return False
    command = f'ping -n 4 127.0.0.1 >nul & del /f /q "{exe_path}"'
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    popen(["cmd", "/c", command], creationflags=flags, close_fds=True)
    return True


# ---------------------------------------------------------------------------
# the whole thing
# ---------------------------------------------------------------------------

def run_uninstall(options, config_dir, startup_path, exe_path, frozen, own_pids=(), grace=3.0):
    """Do what *options* asks for. Returns the report as a list of text lines.

    options: {"stop": bool, "startup": bool, "data": bool, "exe": bool}. Deleting data or the .exe
    always stops the running PhraseLock first, otherwise it would just come back.
    """
    report = []
    stop = options.get("stop") or options.get("data") or options.get("exe")

    if options.get("startup"):
        try:
            report.append("Start-with-Windows shortcut removed." if remove_startup(startup_path)
                          else "There was no start-with-Windows shortcut.")
        except OSError as exc:
            report.append(f"Could not remove the start-with-Windows shortcut: {exc}")

    if stop:
        processes = find_processes(exe_path, frozen, own_pids)
        stopped, failed = stop_processes(processes, grace) if processes else ([], [])
        if processes:
            report.append(f"Stopped {len(stopped)} PhraseLock process(es).")
        else:
            report.append("No other PhraseLock process was running.")
        if failed:
            report.append(f"Could not stop process(es) {', '.join(map(str, failed))}: close them from the Task Manager.")

    if options.get("data"):
        count, size = data_summary(config_dir)
        failed_paths = remove_data(config_dir)
        if failed_paths:
            report.append(f"Some data could not be deleted ({len(failed_paths)} item(s)); delete the folder {config_dir} yourself.")
        else:
            report.append(f"Deleted your data ({count} file(s), {human_size(size)}).")

    if options.get("exe"):
        report.append("PhraseLock.exe will be deleted a few seconds after this window closes."
                      if schedule_exe_delete(exe_path, frozen)
                      else "PhraseLock.exe was not deleted: delete it yourself.")
    elif frozen and options.get("data"):
        report.append(f"You can now delete PhraseLock.exe ({exe_path}).")
    return report


# ---------------------------------------------------------------------------
# window
# ---------------------------------------------------------------------------

def ask_options(root, frozen, config_dir, startup_exists):
    """Modal dialog: what to remove. Returns an options dict, or None when cancelled."""
    import tkinter as tk
    import uikit
    from uikit import UI_FONT, Switch

    P = uikit.P
    count, size = data_summary(config_dir)
    result = {"value": None}
    win = tk.Toplevel(root)
    win.title("Uninstall and cleanup")
    win.configure(bg=P["BG"])
    win.geometry("600x560")
    win.resizable(False, False)
    win.transient(root)

    tk.Label(win, text="Uninstall and cleanup", font=(UI_FONT, 18, "bold"), fg=P["TEXT"], bg=P["BG"]).pack(
        anchor="w", padx=28, pady=(24, 4))
    tk.Label(win, text="Choose what to remove. Nothing happens until you confirm on the next screen.",
             font=(UI_FONT, 10), fg=P["MUTED"], bg=P["BG"], wraplength=540, justify="left").pack(anchor="w", padx=28)

    stop_var = tk.BooleanVar(value=True)
    startup_var = tk.BooleanVar(value=True)
    data_var = tk.BooleanVar(value=False)
    exe_var = tk.BooleanVar(value=False)

    def row(text, detail, var, enabled=True):
        box = tk.Frame(win, bg=P["BG"])
        box.pack(fill="x", padx=28, pady=(14, 0))
        Switch(box, text=text, variable=var, state="normal" if enabled else "disabled",
               font=(UI_FONT, 11, "bold")).pack(anchor="w")
        tk.Label(box, text=detail, font=(UI_FONT, 9), fg=P["MUTED"], bg=P["BG"], wraplength=520,
                 justify="left").pack(anchor="w", padx=(48, 0), pady=(0, 0))

    row("Stop PhraseLock", "Closes the background monitor, the tray icon and the watchdog (Auto-protection) "
        "so nothing restarts.", stop_var)
    row("Remove the start-with-Windows shortcut",
        "It is there now." if startup_exists else "There is none at the moment.", startup_var)
    row("Delete my settings, stats and packs",
        f"The folder {config_dir} ({count} file(s), {human_size(size)}): settings, emergency password, "
        "stats, your own packs and logs. Use Export in the main window first if you want a backup.", data_var)
    row("Delete PhraseLock.exe afterwards",
        "Removes the program file a few seconds after the window closes." if frozen
        else "Only available in the packaged PhraseLock.exe. From source, delete the folder yourself.",
        exe_var, enabled=frozen)

    def on_continue():
        result["value"] = {"stop": stop_var.get(), "startup": startup_var.get(),
                           "data": data_var.get(), "exe": bool(exe_var.get() and frozen)}
        win.destroy()

    buttons = tk.Frame(win, bg=P["BG"])
    buttons.pack(side="bottom", fill="x", padx=28, pady=22)
    tk.Button(buttons, text="Continue", command=on_continue, bg=P["ACCENT"], fg=P["ACCENT_TEXT"], relief="flat",
              bd=0, highlightthickness=0, padx=24, pady=9, cursor="hand2",
              font=(UI_FONT, 10, "bold")).pack(side="right")
    tk.Button(buttons, text="Cancel", command=win.destroy, bg=P["CARD_ALT"], fg=P["TEXT"], relief="flat", bd=0,
              highlightthickness=0, padx=24, pady=9, cursor="hand2",
              font=(UI_FONT, 10, "bold")).pack(side="right", padx=(0, 10))
    win.bind("<Escape>", lambda _e: win.destroy())
    win.grab_set()
    win.wait_window()
    return result["value"]


def confirmation_text(options, frozen):
    """The summary shown before anything is done."""
    lines = []
    if options.get("stop") or options.get("data") or options.get("exe"):
        lines.append("- stop PhraseLock, its tray icon and its watchdog")
    if options.get("startup"):
        lines.append("- remove the start-with-Windows shortcut")
    if options.get("data"):
        lines.append("- DELETE your settings, emergency password, stats, packs and logs")
    if options.get("exe") and frozen:
        lines.append("- delete PhraseLock.exe")
    if not lines:
        return ""
    return "PhraseLock will:\n" + "\n".join(lines) + "\n\nThis cannot be undone. Continue?"
