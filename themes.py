"""Colour themes and the interface texts a theme pack can change.

No UI dependency, so it can be unit-tested. The lock overlay, the focus-session
window and the Settings window all read their theme from here instead of each
keeping its own copy of the colour table.
"""

import random
import re

DEFAULT_THEME = "Cyber Red"

# name -> (primary accent, secondary accent, third accent)
THEMES = {
    "Cyber Red": ("#ff1744", "#00e5ff", "#b400ff"),
    "Neon Pink": ("#ff2aa3", "#7df9ff", "#c86bff"),
    "Cyber Blue": ("#2979ff", "#00e5ff", "#7c4dff"),
    "Matrix": ("#00e676", "#00ff41", "#76ff03"),
    "Dark Purple": ("#9c27ff", "#e040fb", "#ff4081"),
    "Blackout": ("#eeeeee", "#777777", "#444444"),
    # Theme pack colours (see packs/<name>/pack.json).
    "TechDom": ("#0097a7", "#00e5ff", "#39ff88"),
    "PetDom": ("#ff8a3d", "#ffd54f", "#ff6f91"),
}


# --------------------------------------------------------------------------
# custom themes (made in Settings > Look > Theme editor)
# --------------------------------------------------------------------------

MAX_THEME_NAME_LENGTH = 30
MAX_CUSTOM_THEMES = 30
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_hex_colour(value):
    return isinstance(value, str) and bool(_HEX_RE.match(value.strip()))


def clean_custom_themes(raw):
    """Validated copy of the ``custom_themes`` setting: {name: [primary, secondary, third]}.

    Entries with an empty or over-long name, a name that is already a built-in theme
    (case-insensitive), or anything other than three #rrggbb colours are dropped.
    """
    clean = {}
    if not isinstance(raw, dict):
        return clean
    builtin = {n.lower() for n in THEMES}
    for name, colours in raw.items():
        if not isinstance(name, str):
            continue
        name = name.strip()
        if not name or len(name) > MAX_THEME_NAME_LENGTH or name.lower() in builtin:
            continue
        if any(name.lower() == k.lower() for k in clean):
            continue
        if not isinstance(colours, (list, tuple)) or len(colours) != 3:
            continue
        if not all(is_hex_colour(c) for c in colours):
            continue
        clean[name] = [c.strip().lower() for c in colours]
        if len(clean) >= MAX_CUSTOM_THEMES:
            break
    return clean


def custom_themes(cfg):
    return clean_custom_themes(cfg.get("custom_themes")) if isinstance(cfg, dict) else {}


def is_builtin(name):
    return name in THEMES


def theme_names(cfg=None):
    """Built-in themes first, then the custom ones (sorted)."""
    return list(THEMES) + sorted(custom_themes(cfg), key=str.lower)


def theme_colors(name, cfg=None):
    """(primary, secondary, third) for *name*; unknown names fall back to the default."""
    if name in THEMES:
        return THEMES[name]
    custom = custom_themes(cfg)
    if name in custom:
        return tuple(custom[name])
    return THEMES[DEFAULT_THEME]


def accent_for(name, cfg=None):
    return theme_colors(name, cfg)[0]


def check_theme_name(name, taken, allow=None):
    """Return an error message for a bad new theme name, or None when it is fine.

    *taken* are the names already in use; *allow* is one name that may be reused
    (the theme being renamed, so that only changing the case is accepted).
    """
    name = (name or "").strip()
    if not name:
        return "Give the theme a name."
    if len(name) > MAX_THEME_NAME_LENGTH:
        return f"Use at most {MAX_THEME_NAME_LENGTH} characters."
    for other in taken:
        if other.lower() == name.lower() and other != allow:
            return "A theme with that name already exists."
    return None


def copy_name(base, taken):
    """'Matrix' -> 'Matrix copy', then 'Matrix copy 2', ... (never in *taken*, never too long)."""
    lowered = {t.lower() for t in taken}
    stem = base[: MAX_THEME_NAME_LENGTH - 8].rstrip()
    candidate = f"{stem} copy"
    n = 2
    while candidate.lower() in lowered:
        candidate = f"{stem} copy {n}"
        n += 1
    return candidate


# --------------------------------------------------------------------------
# interface texts
# --------------------------------------------------------------------------

# Every text the lock screen (and the Settings window title) shows that a theme pack may replace. A pack stores
# its own versions in the ``ui_texts`` setting; anything it leaves out keeps the
# default given at the call site in overlay.py.
UI_TEXT_KEYS = ("app_kicker", "app_title", "header", "subtitle", "button", "errors", "lockout", "wait", "round",
                "emergency_open", "emergency_title", "emergency_prompt", "emergency_submit", "emergency_back",
                "emergency_continue", "emergency_wrong", "emergency_steps")
MAX_STEP_TITLE_LENGTH = 60
MAX_STEP_TEXT_LENGTH = 240
MAX_EMERGENCY_STEPS = 5
MAX_UI_TEXT_LENGTH = 80


def ui_text(cfg, key, default, **values):
    """Text for *key* from the ``ui_texts`` setting, filled in with *values*.

    ``{n}``, ``{done}`` and ``{total}`` placeholders are replaced. A missing,
    empty or wrongly typed override never breaks the lock screen: the default
    is used instead.
    """
    texts = cfg.get("ui_texts") if isinstance(cfg, dict) else None
    candidate = texts.get(key) if isinstance(texts, dict) else None
    if isinstance(candidate, str) and candidate.strip():
        return _fill(candidate, values)
    return _fill(default, values)


def _fill(template, values):
    """Replace {name} placeholders. Anything else, braces included, stays as plain text.

    str.format is deliberately not used: it would also evaluate things like
    ``{n.__class__}`` or fail on a stray brace in a text written by someone else.
    """
    for name, value in values.items():
        template = template.replace("{" + name + "}", str(value))
    return template


def error_text(cfg, default):
    """Message shown after a typo: one of the pack's ``errors``, picked at random."""
    texts = cfg.get("ui_texts") if isinstance(cfg, dict) else None
    options = texts.get("errors") if isinstance(texts, dict) else None
    if isinstance(options, list):
        options = [x for x in options if isinstance(x, str) and x.strip()]
        if options:
            return random.choice(options)
    return default


def clean_ui_texts(raw):
    """Keep only known keys with sane text; returns a new dict (possibly empty)."""
    clean = {}
    if not isinstance(raw, dict):
        return clean
    for key in UI_TEXT_KEYS:
        value = raw.get(key)
        if key == "emergency_steps":
            steps = []
            if isinstance(value, list):
                for item in value[:MAX_EMERGENCY_STEPS]:
                    if not isinstance(item, dict):
                        continue
                    title, text = item.get("title"), item.get("text")
                    if (isinstance(title, str) and title.strip() and len(title) <= MAX_STEP_TITLE_LENGTH
                            and isinstance(text, str) and text.strip() and len(text) <= MAX_STEP_TEXT_LENGTH):
                        steps.append({"title": title.strip(), "text": text.strip()})
            if steps:
                clean[key] = steps
        elif key == "errors":
            if isinstance(value, list):
                items = [x.strip() for x in value
                         if isinstance(x, str) and x.strip() and len(x) <= MAX_UI_TEXT_LENGTH]
                if items:
                    clean[key] = items[:20]
        elif isinstance(value, str) and value.strip() and len(value) <= MAX_UI_TEXT_LENGTH:
            clean[key] = value.strip()
    return clean
