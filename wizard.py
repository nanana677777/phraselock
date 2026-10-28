"""First-launch setup wizard.

Asks five short questions (style, difficulty, strictness, emergency password, start now)
and turns the answers into settings. The logic is Tk-free (``apply_choices``) so it can be
unit-tested; ``run`` is the window.

Shown automatically the first time PhraseLock is opened (no config file yet) and again on
request from Settings > Home > "Run the setup wizard again".
"""

import os

import packs
from config import CONFIG_PATH, load_config, log, save_json
from stats import set_emergency_password

MIN_PASSWORD_LENGTH = 6

DIFFICULTY_CHOICES = (
    ("all", "Mix of everything", "Phrases from every difficulty."),
    ("easy", "Easy", "Short, simple phrases."),
    ("normal", "Normal", "Medium-length phrases."),
    ("hard", "Hard", "Long phrases that need care."),
)

# Challenge rules for each strictness level. "pack" keeps whatever the chosen pack sets.
STRICTNESS_CHOICES = (
    ("pack", "Keep the style's own rules", "Use the rules that come with the style you picked."),
    ("gentle", "Gentle", "Type each phrase once; mistakes never lock you out."),
    ("standard", "Standard", "Two rounds; five mistakes lock you out for 30 seconds."),
    ("strict", "Strict", "Three rounds, a typo restarts the phrase, three mistakes lock you out for a minute."),
)
STRICTNESS_RULES = {
    "gentle": {"required_repeats": 1, "reset_on_error": False, "disable_paste": True,
               "min_delay_seconds": 2, "max_attempts": 0, "lockout_seconds": 15},
    "standard": {"required_repeats": 2, "reset_on_error": False, "disable_paste": True,
                 "min_delay_seconds": 3, "max_attempts": 5, "lockout_seconds": 30},
    "strict": {"required_repeats": 3, "reset_on_error": True, "disable_paste": True,
               "min_delay_seconds": 5, "max_attempts": 3, "lockout_seconds": 60},
}

DEFAULT_CHOICES = {
    "pack": "",              # pack id, "" = keep the default look
    "difficulty": "all",
    "strictness": "pack",
    "password": "",          # empty = no emergency password
    "protections": False,    # the pack's protections (needs a password)
    "enabled": True,
}


def should_run(cfg, config_path=None):
    """True on a real first launch: never set up before and no config file on disk yet."""
    if cfg.get("setup_done"):
        return False
    return not os.path.exists(config_path or CONFIG_PATH)


def validate_password(password, confirm):
    """Error message for a bad emergency password, or None. An empty one means 'skip'."""
    if not password and not confirm:
        return None
    if password != confirm:
        return "The two passwords are different."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Use at least {MIN_PASSWORD_LENGTH} characters."
    return None


def apply_choices(cfg, choices, source_root=None, dest_root=None, undo_path=None):
    """Return (new_cfg, warnings) for the wizard's answers. Raises ValueError for a bad password.

    Order matters: password first (so protections are allowed), then the pack, then the
    difficulty and strictness the user chose explicitly, which win over the pack's defaults.
    """
    answers = {**DEFAULT_CHOICES, **(choices or {})}
    problem = validate_password(answers["password"], answers["password"])
    if problem:
        raise ValueError(problem)
    new = dict(cfg)
    warnings = []

    if answers["password"]:
        new.update(set_emergency_password(answers["password"]))
    has_password = bool(new.get("emergency_password_hash"))

    if answers["pack"]:
        kwargs = {}
        if source_root is not None:
            kwargs["source_root"] = source_root
        if dest_root is not None:
            kwargs["dest_root"] = dest_root
        if undo_path is not None:
            kwargs["undo_path"] = undo_path
        new, pack_warnings = packs.apply_pack(
            new, answers["pack"], include_protections=bool(answers["protections"] and has_password), **kwargs)
        warnings.extend(pack_warnings)
    elif answers["protections"]:
        warnings.append("Protections come with a style; none was chosen, so none were switched on.")

    if answers["difficulty"] in {d[0] for d in DIFFICULTY_CHOICES}:
        new["difficulty"] = answers["difficulty"]
    new.update(STRICTNESS_RULES.get(answers["strictness"], {}))

    new["enabled"] = bool(answers["enabled"])
    new["setup_done"] = True
    new["advanced_view"] = False          # new users start on the simple Home tab
    return new, warnings


def summary_lines(choices, pack_name=None):
    answers = {**DEFAULT_CHOICES, **(choices or {})}
    labels = {k: label for k, label, _ in DIFFICULTY_CHOICES}
    rules = {k: label for k, label, _ in STRICTNESS_CHOICES}
    lines = [
        f"Style: {pack_name or 'default look'}",
        f"Difficulty: {labels.get(answers['difficulty'], answers['difficulty'])}",
        f"Rules: {rules.get(answers['strictness'], answers['strictness'])}",
        "Emergency password: " + ("set" if answers["password"] else "none (you can add one later)"),
    ]
    if answers["protections"] and answers["password"]:
        lines.append("Protections: on (strict mode, idle lock)")
    lines.append("PhraseLock will start " + ("protecting you right away." if answers["enabled"]
                                           else "switched off (turn it on from Settings)."))
    return lines


def mark_skipped(cfg, config_path=None):
    """The user closed the wizard: remember that, keep every setting, show all tabs."""
    new = {**cfg, "setup_done": True, "advanced_view": True}
    save_json(config_path or CONFIG_PATH, new)
    return new


# ---------------------------------------------------------------------------
# window
# ---------------------------------------------------------------------------

def run(cfg=None):
    """Show the wizard. Saves the config and returns it (also when skipped)."""
    import tkinter as tk
    from tkinter import messagebox
    from appicon import apply_window_icon

    cfg = cfg if cfg is not None else load_config()
    BG, CARD, TEXT, MUTED, ACCENT, DANGER = "#050507", "#0d0d12", "#f7f7fb", "#9aa0b4", "#ff1744", "#ff5252"
    available = packs.list_packs()

    root = tk.Tk()
    apply_window_icon(root)
    root.title("PhraseLock - Setup")
    root.geometry("640x540")
    root.resizable(False, False)
    root.configure(bg=BG)
    root.option_add("*Frame.Background", BG)
    root.option_add("*Label.Background", BG)
    root.option_add("*Label.Foreground", TEXT)
    root.option_add("*Radiobutton.Background", BG)
    root.option_add("*Radiobutton.Foreground", TEXT)
    root.option_add("*Radiobutton.SelectColor", CARD)
    root.option_add("*Radiobutton.ActiveBackground", BG)
    root.option_add("*Radiobutton.ActiveForeground", TEXT)
    root.option_add("*Checkbutton.Background", BG)
    root.option_add("*Checkbutton.Foreground", TEXT)
    root.option_add("*Checkbutton.SelectColor", CARD)
    root.option_add("*Checkbutton.ActiveBackground", BG)
    root.option_add("*Checkbutton.ActiveForeground", TEXT)
    root.option_add("*Entry.Background", CARD)
    root.option_add("*Entry.Foreground", TEXT)
    root.option_add("*Entry.InsertBackground", ACCENT)

    result = {"cfg": cfg, "finished": False}
    pack_var = tk.StringVar(value=available[0]["id"] if available else "")
    difficulty_var = tk.StringVar(value=DEFAULT_CHOICES["difficulty"])
    strictness_var = tk.StringVar(value=DEFAULT_CHOICES["strictness"])
    password_var = tk.StringVar()
    confirm_var = tk.StringVar()
    protections_var = tk.BooleanVar(value=False)
    enabled_var = tk.BooleanVar(value=True)
    error_var = tk.StringVar()
    step_var = tk.StringVar()

    header = tk.Frame(root)
    header.pack(fill="x", padx=24, pady=(20, 0))
    tk.Label(header, text="PHRASELOCK SETUP", font=("Consolas", 16, "bold"), fg=ACCENT).pack(anchor="w")
    tk.Label(header, textvariable=step_var, font=("Consolas", 9), fg=MUTED).pack(anchor="w")

    body = tk.Frame(root)
    body.pack(fill="both", expand=True, padx=24, pady=12)
    error_label = tk.Label(root, textvariable=error_var, font=("Consolas", 9), fg=DANGER, wraplength=580, justify="left")
    error_label.pack(fill="x", padx=24)
    nav = tk.Frame(root)
    nav.pack(fill="x", padx=24, pady=(6, 18))

    def title(text):
        tk.Label(body, text=text, font=("Consolas", 13, "bold")).pack(anchor="w", pady=(0, 6))

    def para(text, color=MUTED, size=10):
        tk.Label(body, text=text, font=("Consolas", size), fg=color, wraplength=580, justify="left").pack(anchor="w", pady=(0, 8))

    def choice(var, value, label, detail):
        tk.Radiobutton(body, text=label, variable=var, value=value, font=("Consolas", 11, "bold"),
                       anchor="w", indicatoron=True).pack(anchor="w")
        tk.Label(body, text=detail, font=("Consolas", 9), fg=MUTED, wraplength=540, justify="left").pack(
            anchor="w", padx=(26, 0), pady=(0, 6))

    def page_welcome():
        title("Welcome")
        para("PhraseLock asks you to type a phrase before the computer unlocks. A few quick questions "
             "set it up for you; everything can be changed later in Settings.")
        para("This takes about a minute. Nothing is switched on until you press Finish.")

    def page_style():
        title("1. Pick a style")
        para("A style sets the phrases, colours, pictures, sounds and wording in one go.")
        for p in available:
            choice(pack_var, p["id"], p["name"], p["description"])
        choice(pack_var, "", "Default look", "The plain PhraseLock look and the built-in phrase.")

    def page_difficulty():
        title("2. How hard should the phrases be?")
        for key, label, detail in DIFFICULTY_CHOICES:
            choice(difficulty_var, key, label, detail)

    def page_rules():
        title("3. How strict should it be?")
        for key, label, detail in STRICTNESS_CHOICES:
            choice(strictness_var, key, label, detail)

    def page_password():
        title("4. Emergency password (optional)")
        para("A password that unlocks the computer if you ever get stuck. Strongly recommended, and "
             f"needed for a style's protections. At least {MIN_PASSWORD_LENGTH} characters; skip it to set one later.")
        for text, var in (("Password:", password_var), ("Repeat it:", confirm_var)):
            row = tk.Frame(body)
            row.pack(anchor="w", pady=2)
            tk.Label(row, text=text, width=12, anchor="w", font=("Consolas", 10)).pack(side="left")
            tk.Entry(row, textvariable=var, show="*", width=28).pack(side="left")
        tk.Checkbutton(body, text="Also switch on the style's protections (strict mode, idle lock)",
                       variable=protections_var, font=("Consolas", 10)).pack(anchor="w", pady=(14, 0))
        para("Only applies when a style and a password are chosen.", size=8)

    def current_choices():
        return {"pack": pack_var.get(), "difficulty": difficulty_var.get(), "strictness": strictness_var.get(),
                "password": password_var.get(), "protections": protections_var.get(), "enabled": enabled_var.get()}

    def page_finish():
        title("All set")
        name = next((p["name"] for p in available if p["id"] == pack_var.get()), None)
        for line in summary_lines(current_choices(), name):
            tk.Label(body, text="- " + line, font=("Consolas", 10), anchor="w", justify="left",
                     wraplength=580).pack(anchor="w", pady=1)
        tk.Checkbutton(body, text="Start protecting me now", variable=enabled_var,
                       font=("Consolas", 10)).pack(anchor="w", pady=(16, 0))
        para("Settings opens next, on a simple Home tab. Advanced options stay one click away.", size=9)

    pages = [page_welcome, page_style, page_difficulty, page_rules, page_password, page_finish]
    state = {"i": 0}

    def show(i):
        state["i"] = i
        error_var.set("")
        for child in body.winfo_children():
            child.destroy()
        for child in nav.winfo_children():
            child.destroy()
        step_var.set("Welcome" if i == 0 else f"Step {i} of {len(pages) - 1}" if i < len(pages) - 1 else "Last step")
        pages[i]()

        def button(text, command, primary=False):
            tk.Button(nav, text=text, command=command, bg=ACCENT if primary else CARD, fg="white" if primary else TEXT,
                      activebackground=ACCENT, activeforeground="white", relief="flat", bd=0, padx=18, pady=7,
                      cursor="hand2", font=("Consolas", 10, "bold")).pack(side="right" if primary else "left", padx=(0, 8))

        if i > 0:
            button("Back", lambda: show(i - 1))
        button("Skip setup", on_skip)
        button("Finish" if i == len(pages) - 1 else "Next", on_next, primary=True)

    def on_next():
        i = state["i"]
        if pages[i] is page_password:
            problem = validate_password(password_var.get(), confirm_var.get())
            if problem:
                error_var.set(problem)
                return
        if i == len(pages) - 1:
            return finish()
        show(i + 1)

    def finish():
        try:
            new, warnings = apply_choices(result["cfg"], current_choices())
            save_json(CONFIG_PATH, new)
        except (ValueError, packs.PackError, OSError) as exc:
            error_var.set(str(exc))
            return
        result["cfg"] = new
        result["finished"] = True
        if warnings:
            messagebox.showinfo("Setup", "Done. Notes:\n- " + "\n- ".join(warnings), parent=root)
        root.destroy()

    def on_skip():
        if messagebox.askyesno("Skip setup", "Skip the setup and keep the default settings?\n\n"
                               "You can run it again from Settings > Home.", parent=root):
            try:
                result["cfg"] = mark_skipped(result["cfg"])
            except OSError as exc:
                log(f"Could not save the skipped-setup flag: {exc}")
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_skip)
    show(0)
    root.mainloop()
    return result["cfg"]
