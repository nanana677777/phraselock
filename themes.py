"""Colour themes and the interface texts a theme pack can change.

No UI dependency, so it can be unit-tested. The lock overlay, the focus-session
window and the Settings window all read their theme from here instead of each
keeping its own copy of the colour table.
"""

import random

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
}


def theme_names():
    return list(THEMES)


def theme_colors(name):
    """(primary, secondary, third) for *name*; unknown names fall back to the default."""
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def accent_for(name):
    return theme_colors(name)[0]


# --------------------------------------------------------------------------
# interface texts
# --------------------------------------------------------------------------

# Every text the lock screen shows that a theme pack may replace. A pack stores
# its own versions in the ``ui_texts`` setting; anything it leaves out keeps the
# default given at the call site in overlay.py.
UI_TEXT_KEYS = ("header", "subtitle", "button", "errors", "lockout", "wait", "round")
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
        if key == "errors":
            if isinstance(value, list):
                items = [x.strip() for x in value
                         if isinstance(x, str) and x.strip() and len(x) <= MAX_UI_TEXT_LENGTH]
                if items:
                    clean[key] = items[:20]
        elif isinstance(value, str) and value.strip() and len(value) <= MAX_UI_TEXT_LENGTH:
            clean[key] = value.strip()
    return clean
