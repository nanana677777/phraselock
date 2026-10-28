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
from version import __version__
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
    new["last_seen_version"] = __version__   # a brand-new install has nothing to catch up on
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
    new = {**cfg, "setup_done": True, "advanced_view": True, "last_seen_version": __version__}
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
    import uikit
    from uikit import UI_FONT, RadioCard, Switch

    cfg = cfg if cfg is not None else load_config()
    pal = uikit.apply_palette("#ff1744", "#00e5ff")
    BG, CARD, TEXT, MUTED, ACCENT, DANGER = pal["BG"], pal["CARD"], pal["TEXT"], pal["MUTED"], pal["ACCENT"], pal["DANGER"]
    available = packs.list_packs()

    root = tk.Tk()
    apply_window_icon(root)
    root.title("PhraseLock - Setup")
    root.geometry("700x680")
    root.minsize(640, 600)
    root.configure(bg=BG)
    root.option_add("*Font", f"{{{UI_FONT}}} 10")
    root.option_add("*Frame.Background", BG)
    root.option_add("*Label.Background", BG)
    root.option_add("*Label.Foreground", TEXT)
    root.option_add("*Entry.Background", pal["INPUT"])
    root.option_add("*Entry.Foreground", TEXT)
    root.option_add("*Entry.InsertBackground", ACCENT)
    root.option_add("*Entry.Relief", "flat")
    root.option_add("*Entry.HighlightThickness", 1)
    root.option_add("*Entry.HighlightBackground", pal["BORDER"])
    root.option_add("*Entry.HighlightColor", ACCENT)

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
    header.pack(fill="x", padx=32, pady=(26, 0))
    tk.Label(header, text="PHRASELOCK SETUP", font=(UI_FONT, 9, "bold"), fg=ACCENT).pack(anchor="w")
    tk.Label(header, textvariable=step_var, font=(UI_FONT, 10), fg=MUTED).pack(anchor="w", pady=(2, 8))
    progress = tk.Canvas(header, height=4, bg=BG, highlightthickness=0, bd=0)
    progress.pack(fill="x")

    nav = tk.Frame(root)
    nav.pack(side="bottom", fill="x", padx=32, pady=(6, 24))
    error_label = tk.Label(root, textvariable=error_var, font=(UI_FONT, 9), fg=DANGER, wraplength=620, justify="left")
    error_label.pack(side="bottom", fill="x", padx=32)
    body = tk.Frame(root)
    body.pack(fill="both", expand=True, padx=32, pady=(18, 8))

    def title(text):
        tk.Label(body, text=text, font=(UI_FONT, 20, "bold")).pack(anchor="w", pady=(0, 6))

    def para(text, color=MUTED, size=10):
        tk.Label(body, text=text, font=(UI_FONT, size), fg=color, wraplength=620, justify="left").pack(
            anchor="w", pady=(0, 10))

    def choice(var, value, label, detail):
        RadioCard(body, label, detail, var, value, wraplength=560).pack(fill="x", pady=4)

    def page_welcome():
        title("Welcome")
        para("PhraseLock asks you to type a phrase before the computer unlocks. A few quick questions "
             "set it up for you; everything can be changed later in Settings.", size=11)
        para("This takes about a minute. Nothing is switched on until you press Finish.", size=11)

    def page_style():
        title("Pick a style")
        para("A style sets the phrases, colours, pictures, sounds and wording in one go.")
        for p in available:
            choice(pack_var, p["id"], p["name"], p["description"])
        choice(pack_var, "", "Default look", "The plain PhraseLock look and the built-in phrase.")

    def page_difficulty():
        title("How hard should the phrases be?")
        for key, label, detail in DIFFICULTY_CHOICES:
            choice(difficulty_var, key, label, detail)

    def page_rules():
        title("How strict should it be?")
        for key, label, detail in STRICTNESS_CHOICES:
            choice(strictness_var, key, label, detail)

    def page_password():
        title("Emergency password")
        para("A password that unlocks the computer if you ever get stuck. Strongly recommended, and "
             f"needed for a style's protections. At least {MIN_PASSWORD_LENGTH} characters; skip it to set one later.")
        for text, var in (("Password", password_var), ("Repeat it", confirm_var)):
            tk.Label(body, text=text, font=(UI_FONT, 10), fg=MUTED).pack(anchor="w", pady=(8, 3))
            tk.Entry(body, textvariable=var, show="*", width=34, font=(UI_FONT, 11)).pack(anchor="w", ipady=5)
        Switch(body, text="Also switch on the style's protections (strict mode, idle lock)",
               variable=protections_var).pack(anchor="w", pady=(22, 0))
        para("Only applies when a style and a password are chosen.", size=9)

    def current_choices():
        return {"pack": pack_var.get(), "difficulty": difficulty_var.get(), "strictness": strictness_var.get(),
                "password": password_var.get(), "protections": protections_var.get(), "enabled": enabled_var.get()}

    def page_finish():
        title("All set")
        name = next((p["name"] for p in available if p["id"] == pack_var.get()), None)
        card = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=pal["BORDER"])
        card.pack(fill="x", pady=(0, 14))
        for line in summary_lines(current_choices(), name):
            tk.Label(card, text=line, font=(UI_FONT, 10), bg=CARD, anchor="w", justify="left",
                     wraplength=580).pack(anchor="w", padx=16, pady=3)
        Switch(body, text="Start protecting me now", variable=enabled_var).pack(anchor="w", pady=(4, 0))
        para("Settings opens next, on a simple Home tab. Advanced options stay one click away.", size=9)

    progress.bind("<Configure>", lambda _e: draw_progress(state["i"]))
    pages = [page_welcome, page_style, page_difficulty, page_rules, page_password, page_finish]
    state = {"i": 0}

    def draw_progress(i):
        progress.delete("all")
        width = max(progress.winfo_width(), 100)
        gap, count = 6, len(pages)
        seg = (width - gap * (count - 1)) / count
        for n in range(count):
            x = n * (seg + gap)
            progress.create_rectangle(x, 0, x + seg, 4, fill=ACCENT if n <= i else pal["OFF_TRACK"], outline="")

    def show(i):
        state["i"] = i
        error_var.set("")
        for child in body.winfo_children():
            child.destroy()
        for child in nav.winfo_children():
            child.destroy()
        step_var.set("Welcome" if i == 0 else f"Step {i} of {len(pages) - 2}" if i < len(pages) - 1 else "Last step")
        pages[i]()

        def button(text, command, primary=False, side="left", muted=False):
            tk.Button(nav, text=text, command=command, bg=ACCENT if primary else (BG if muted else pal["CARD_ALT"]),
                      fg=pal["ACCENT_TEXT"] if primary else (MUTED if muted else TEXT),
                      activebackground=ACCENT, activeforeground=pal["ACCENT_TEXT"], relief="flat", bd=0,
                      highlightthickness=0, padx=22, pady=9, cursor="hand2",
                      font=(UI_FONT, 10, "bold")).pack(side=side, padx=(0, 8))

        button("Finish" if i == len(pages) - 1 else "Next", on_next, primary=True, side="right")
        if i > 0:
            button("Back", lambda: show(i - 1), side="right")
        button("Skip setup", on_skip, muted=True)
        draw_progress(i)

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
