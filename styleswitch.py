"""Switch the style (theme pack) from the tray menu.

Like "Exit PhraseLock", the work is done by a short-lived process (``--switch-style <pack id>``)
because the tray cannot show Tk dialogs from its own thread. A style can change the challenge rules
(difficulty, rounds, paste...), so when an emergency password is set it is asked first; otherwise
the tray would be a way around a strict setup. Protections (strict mode, idle lock...) are never
touched by a switch, exactly as with "Apply" in Settings.
"""

from config import load_config, save_json, log, CONFIG_PATH
import packs
import exit_app


def parse_pack_id(argv):
    """The pack id after --switch-style, or None."""
    try:
        value = argv[argv.index("--switch-style") + 1]
    except (ValueError, IndexError):
        return None
    return value if packs.PACK_ID_RE.match(value) else None


def switch(pack_id, cfg=None, config_path=None):
    """Apply the pack and save the config. Returns (ok, message)."""
    cfg = cfg if cfg is not None else load_config()
    try:
        new_cfg, warnings = packs.apply_pack(cfg, pack_id)
    except packs.PackError as exc:
        return False, str(exc)
    save_json(config_path or CONFIG_PATH, new_cfg)
    return True, "Style switched." + (" " + warnings[0] if warnings else "")


def run(argv):
    """Entry point for ``--switch-style <pack id>``."""
    import tkinter as tk
    from tkinter import messagebox, simpledialog
    from tray import settings_is_open

    pack_id = parse_pack_id(argv)
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if pack_id is None:
            return False
        if settings_is_open():
            messagebox.showinfo("Switch style", "Close the Settings window first, then try again.", parent=root)
            return False
        cfg = load_config()
        if exit_app.needs_password(cfg):
            def ask(attempt):
                text = "Enter the emergency password to change the style."
                if attempt > 1:
                    text = f"Wrong password ({attempt}/{exit_app.MAX_TRIES}). Try again."
                return simpledialog.askstring("Switch style", text, show="*", parent=root)

            if not exit_app.check_password(cfg, ask):
                log("Style switch from the tray refused (password).")
                return False
        ok, message = switch(pack_id, cfg)
        log(f"Style switch from the tray to '{pack_id}': {message}")
        (messagebox.showinfo if ok else messagebox.showerror)("Switch style", message, parent=root)
        return ok
    finally:
        root.destroy()
