"""Typing help for the lock screen: how much of the phrase is right so far.

Pure functions (no Tk) so they can be tested. They compare character by character with the same
rules as the challenge itself: surrounding spaces are ignored, and with case-insensitive mode
capitals and accents do not matter.
"""

import unicodedata


def _key(char, case_insensitive):
    if not case_insensitive:
        return char
    folded = unicodedata.normalize("NFKD", char.lower())
    return "".join(c for c in folded if not unicodedata.combining(c))


def correct_prefix(typed, target, case_insensitive=False):
    """(good, keep): how many characters of the phrase were typed correctly, and the part of
    *typed* (as the person typed it, leading spaces included) that is that correct beginning."""
    typed = typed or ""
    lead = len(typed) - len(typed.lstrip())
    body = typed[lead:]
    goal = (target or "").strip()
    good = 0
    for a, b in zip(body, goal):
        if _key(a, case_insensitive) != _key(b, case_insensitive):
            break
        good += 1
    return good, typed[:lead + good]


def progress_fraction(typed, target, case_insensitive=False):
    """0.0 to 1.0: the correct beginning, as a share of the phrase."""
    goal = (target or "").strip()
    if not goal:
        return 0.0
    good, _ = correct_prefix(typed, target, case_insensitive)
    return max(0.0, min(1.0, good / len(goal)))
