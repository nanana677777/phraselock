"""Emergency unlock: the "are you sure?" screens shown before the password, and the penalty.

Pure functions so they can be tested; overlay.py draws the screens and calls apply_penalty.
"""

MAX_CONFIRMATIONS = 5
CONFIRM_DELAY_SECONDS = 3

_STEPS = (
    ("Skip the challenge?", "You are about to bypass the typing challenge. Typing the phrase is the point of PhraseLock."),
    ("Is it really an emergency?", "An emergency is something that cannot wait. 'I don't feel like it' is not one."),
    ("Take a breath.", "Most urges pass in a minute or two. You can close this window and type the phrase instead."),
    ("Think about your streak.", "Using the emergency password is recorded in your stats as an emergency unlock."),
    ("Last chance.", "After this you will only need the emergency password."),
)


def count(cfg):
    try:
        n = int(cfg.get("emergency_confirmations", 3))
    except (TypeError, ValueError):
        n = 3
    return max(0, min(MAX_CONFIRMATIONS, n))


def penalty(cfg):
    """{"streak": bool, "xp": int} as configured."""
    try:
        xp = int(cfg.get("emergency_penalty_xp", 0))
    except (TypeError, ValueError):
        xp = 0
    return {"streak": bool(cfg.get("emergency_penalty_streak", False)), "xp": max(0, min(500, xp))}


def penalty_text(cfg):
    """One sentence describing the penalty, or '' when there is none."""
    p = penalty(cfg)
    parts = []
    if p["streak"]:
        parts.append("your current streak will be reset to 0")
    if p["xp"]:
        parts.append(f"you will lose {p['xp']} XP")
    if not parts:
        return ""
    return "Penalty: " + " and ".join(parts) + "."


def steps(cfg):
    """[(title, message)] for each confirmation screen, the last one spelling out the penalty."""
    n = count(cfg)
    if n == 0:
        return []
    # The pack's own wording wins, position by position; the rest keeps the built-in text.
    texts = cfg.get("ui_texts") if isinstance(cfg, dict) else None
    custom = texts.get("emergency_steps") if isinstance(texts, dict) else None
    pool = list(_STEPS)
    if isinstance(custom, list):
        for i, item in enumerate(custom[:len(pool)]):
            if isinstance(item, dict) and item.get("title") and item.get("text"):
                pool[i] = (str(item["title"]), str(item["text"]))
    # Always start with the first and finish with the last wording, whatever n is.
    picks = [pool[0]] if n == 1 else ([pool[0]] + pool[1:n - 1] + [pool[-1]])
    out = list(picks)
    extra = penalty_text(cfg)
    if extra:
        title, message = out[-1]
        out[-1] = (title, f"{message}\n\n{extra}")
    return out


def apply_penalty(cfg, apply_func):
    """Call apply_func(reset_streak, xp_loss) when a penalty is configured. Returns its result or None."""
    p = penalty(cfg)
    if not p["streak"] and not p["xp"]:
        return None
    return apply_func(p["streak"], p["xp"])
