"""The "What's new?" window shown after an update.

``config["last_seen_version"]`` remembers the last version the user was told about. When the
running version is newer, the window lists what changed (read from CHANGELOG.md, which ships
inside the .exe) and the version is remembered. The parsing is Tk-free so it can be tested.
"""

import os
import re
import sys

from config import CONFIG_PATH, load_config, log, save_json
from version import __version__

MAX_VERSIONS_SHOWN = 3
_HEADING_RE = re.compile(r"^##\s+\[([^\]]+)\](?:\s*-\s*(.+))?\s*$")
_VERSION_RE = re.compile(r"^\d+(?:\.\d+){0,2}$")


def parse_version(text):
    """'1.0.2' -> (1, 0, 2); anything that is not a plain version -> ()."""
    text = (text or "").strip().lstrip("vV")
    if not _VERSION_RE.match(text):
        return ()
    parts = [int(x) for x in text.split(".")]
    return tuple(parts + [0] * (3 - len(parts)))


def plain_text(markdown):
    """Strip the markdown a changelog line uses (bold, italics, code, links)."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", markdown)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_changelog(text):
    """[{"version": "1.0.2" | "Unreleased", "date": str, "groups": [(title, [item, ...]), ...]}]"""
    sections = []
    section = group = None
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        heading = _HEADING_RE.match(line)
        if heading:
            section = {"version": heading.group(1).strip(), "date": (heading.group(2) or "").strip(), "groups": []}
            sections.append(section)
            group = None
        elif section is None:
            continue
        elif line.startswith("### "):
            group = (line[4:].strip(), [])
            section["groups"].append(group)
        elif line.startswith("- "):
            if group is None:
                group = ("Changes", [])
                section["groups"].append(group)
            group[1].append(line[2:].strip())
        elif line.startswith((" ", "\t")) and group is not None and group[1] and line.strip():
            group[1][-1] += " " + line.strip()
    for section in sections:
        section["groups"] = [(t, [plain_text(i) for i in items if plain_text(i)])
                             for t, items in section["groups"]]
        section["groups"] = [(t, items) for t, items in section["groups"] if items]
    return sections


def entries_since(sections, last_seen, current=__version__, limit=MAX_VERSIONS_SHOWN):
    """The sections the user has not seen, newest first, as the window shows them.

    "[Unreleased]" is shown under *current* while no section for that version exists yet.
    Without a *last_seen* (an install from before this window existed) only the newest
    section is shown.
    """
    cur, seen = parse_version(current), parse_version(last_seen)
    released = [s for s in sections if parse_version(s["version"])]
    top = max((parse_version(s["version"]) for s in released), default=())
    entries = []
    for s in sections:
        if s["version"].lower() == "unreleased":
            if cur and cur > top and s["groups"]:
                entries.append({**s, "version": current})
        elif parse_version(s["version"]) and parse_version(s["version"]) <= (cur or parse_version(s["version"])):
            entries.append(s)
    entries = [e for e in entries if e["groups"]]
    entries.sort(key=lambda e: parse_version(e["version"]), reverse=True)
    if not seen:
        return entries[:1]
    return [e for e in entries if parse_version(e["version"]) > seen][:limit]


def should_show(cfg, current=__version__):
    """True when the running version is newer than the one the user last saw."""
    cur = parse_version(current)
    if not cur:
        return False
    return cur > (parse_version(cfg.get("last_seen_version", "")) or (0, 0, 0))


def changelog_path():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "CHANGELOG.md")


def load_entries(last_seen, current=__version__, path=None):
    try:
        with open(path or changelog_path(), "r", encoding="utf-8") as f:
            return entries_since(parse_changelog(f.read()), last_seen, current)
    except OSError:
        return []


def remember_version(cfg, current=__version__, config_path=None):
    """Save that the user has been told about *current*. Returns the new config."""
    new = {**cfg, "last_seen_version": current}
    try:
        save_json(config_path or CONFIG_PATH, new)
    except OSError as exc:
        log(f"Could not save the last seen version: {exc}")
    return new


def run(cfg=None, force=False):
    """Show the window when there is news (or when *force*d). Remembers the version either way."""
    cfg = cfg if cfg is not None else load_config()
    last_seen = cfg.get("last_seen_version", "")
    if not force and not should_show(cfg):
        return cfg
    entries = load_entries("" if force else last_seen)
    if not entries:
        return remember_version(cfg) if not force else cfg
    import tkinter as tk
    from appicon import apply_window_icon
    import uikit
    from uikit import UI_FONT

    pal = uikit.apply_palette("#ff1744", "#00e5ff")
    BG, CARD, TEXT, MUTED, ACCENT, CYAN = pal["BG"], pal["CARD"], pal["TEXT"], pal["MUTED"], pal["ACCENT"], pal["ACCENT2"]
    root = tk.Tk()
    apply_window_icon(root)
    root.title("PhraseLock - What's new?")
    root.geometry("700x600")
    root.minsize(520, 360)
    root.configure(bg=BG)
    top = tk.Frame(root, bg=BG)
    top.pack(fill="x", padx=32, pady=(26, 0))
    tk.Label(top, text=f"PHRASELOCK {__version__}", font=(UI_FONT, 9, "bold"), fg=ACCENT, bg=BG).pack(anchor="w")
    tk.Label(top, text="What's new?", font=(UI_FONT, 22, "bold"), fg=TEXT, bg=BG).pack(anchor="w", pady=(2, 0))

    footer = tk.Frame(root, bg=BG)
    footer.pack(side="bottom", fill="x", padx=32, pady=(8, 24))
    tk.Button(footer, text="Got it", command=root.destroy, bg=ACCENT, fg=pal["ACCENT_TEXT"], activebackground=ACCENT,
              activeforeground=pal["ACCENT_TEXT"], relief="flat", bd=0, highlightthickness=0, padx=28, pady=9,
              cursor="hand2", font=(UI_FONT, 10, "bold")).pack(side="right")

    box = tk.Frame(root, bg=BG)
    box.pack(fill="both", expand=True, padx=32, pady=(14, 0))
    scroll = tk.Scrollbar(box, orient="vertical", troughcolor=BG, bg=pal["OFF_TRACK"], relief="flat", bd=0,
                          highlightthickness=0, width=10)
    text = tk.Text(box, wrap="word", bg=CARD, fg=TEXT, relief="flat", bd=0, padx=20, pady=14,
                   font=(UI_FONT, 10), yscrollcommand=scroll.set, cursor="arrow", spacing3=5,
                   highlightthickness=1, highlightbackground=pal["BORDER"], selectbackground=pal["ACCENT_SOFT"])
    scroll.configure(command=text.yview)
    scroll.pack(side="right", fill="y")
    text.pack(side="left", fill="both", expand=True)
    text.tag_configure("version", font=(UI_FONT, 15, "bold"), foreground=TEXT, spacing1=10, spacing3=2)
    text.tag_configure("date", font=(UI_FONT, 9), foreground=MUTED, spacing3=6)
    text.tag_configure("group", font=(UI_FONT, 9, "bold"), foreground=CYAN, spacing1=10, spacing3=4)
    text.tag_configure("item", lmargin1=12, lmargin2=26)
    for entry in entries:
        text.insert("end", entry["version"] + "\n", "version")
        if entry["date"]:
            text.insert("end", entry["date"] + "\n", "date")
        for title, items in entry["groups"]:
            text.insert("end", title.upper() + "\n", "group")
            for item in items:
                text.insert("end", "\u2022  " + item + "\n", "item")
    text.configure(state="disabled")
    root.bind("<Escape>", lambda _e: root.destroy())
    root.mainloop()
    return remember_version(cfg) if not force else cfg
