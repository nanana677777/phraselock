"""Theme packs: one-click presets (phrases, look, sounds, interface texts, rules).

A pack is a folder ``packs/<id>/`` that holds a ``pack.json`` plus its assets::

    packs/techdom/
        pack.json        settings to apply, interface texts, optional protections
        phrases.csv      the pack's phrases (phrase,category,difficulty)
        backgrounds/     images / GIFs shown behind the lock screen
        audio/           success.wav, error.wav, ...

Applying a pack:

* copies the pack's files into ``%APPDATA%/PhraseLock/packs/<id>/`` (the .exe
  unpacks itself to a temporary folder on every start, so settings must never
  point into it). Files already there are kept, so your own images, GIFs and
  sounds dropped in that folder are never overwritten;
* changes only settings on a fixed allow-list. The emergency password,
  ``auto_protection`` and everything about the schedule are never touched;
* can turn on the pack's optional *protections* (strict mode, idle lock...), but
  only when the user asks for them AND an emergency password is configured;
* remembers the previous values, so the last pack can be undone.

No UI dependency, so it can be unit-tested.
"""

import json
import os
import re
import shutil
import sys

from config import CONFIG_DIR, DEFAULT_CONFIG, log, save_json
from themes import THEMES, clean_ui_texts

PACK_FILE = "pack.json"
PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
UNDO_PATH = os.path.join(CONFIG_DIR, "pack_undo.json")

# The only settings a pack may change.
APPLY_KEYS = frozenset({
    "title", "phrases_file", "theme", "font_family", "ui_scale",
    "scanlines", "glow_effect", "glitch_effect",
    "panel_color", "panel_opacity", "background_mode",
    "play_sound", "sound_on_error", "success_sound", "error_sound", "sound_volume",
    "required_repeats", "reset_on_error", "disable_paste", "case_insensitive",
    "min_delay_seconds", "max_attempts", "lockout_seconds",
    "difficulty", "difficulty_weighting",
})
# Only applied when the user ticks "enable the pack's protections".
PROTECTION_KEYS = frozenset({
    "strict_mode", "idle_lock_enabled", "idle_lock_minutes",
    "focus_session_enabled", "focus_session_minutes",
})
# Settings holding a file that lives inside the pack folder.
PACK_FILE_KEYS = ("phrases_file", "success_sound", "error_sound")

INT_RANGES = {
    "panel_opacity": (10, 100),
    "required_repeats": (1, 20),
    "min_delay_seconds": (0, 60),
    "max_attempts": (0, 100),
    "lockout_seconds": (1, 300),
    "ui_scale": (75, 150),
    "sound_volume": (0, 100),
    "idle_lock_minutes": (1, 240),
    "focus_session_minutes": (1, 240),
}
HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
BACKGROUND_MODES = ("fill", "fit", "stretch", "center", "tile")
DIFFICULTIES = ("all", "easy", "normal", "hard", "extreme")


class PackError(Exception):
    """A problem with a pack, worded for the end user."""


# --------------------------------------------------------------------------
# locations
# --------------------------------------------------------------------------

def bundled_root():
    """Folder with the packs shipped with PhraseLock (inside the .exe when packaged)."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "packs")


def user_root():
    """Folder where applied packs live and where the user can drop their own files."""
    return os.path.join(CONFIG_DIR, "packs")


def pack_folder(pack_id, root=None):
    return os.path.join(root or user_root(), pack_id)


# --------------------------------------------------------------------------
# reading packs
# --------------------------------------------------------------------------

def _check_id(pack_id):
    if not isinstance(pack_id, str) or not PACK_ID_RE.match(pack_id):
        raise PackError(f"Invalid pack name: {pack_id!r}")


def load_pack(pack_id, root=None):
    """Read and minimally validate ``packs/<id>/pack.json``."""
    _check_id(pack_id)
    path = os.path.join(root or bundled_root(), pack_id, PACK_FILE)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise PackError(f"Pack '{pack_id}' was not found.")
    except (OSError, ValueError) as exc:
        raise PackError(f"Pack '{pack_id}' could not be read: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not data["name"].strip():
        raise PackError(f"Pack '{pack_id}' has no name.")
    if not isinstance(data.get("config", {}), dict):
        raise PackError(f"Pack '{pack_id}': 'config' must be an object.")
    data["id"] = pack_id
    return data


def list_packs(root=None):
    """[{"id", "name", "description"}] for every valid pack, sorted by name."""
    root = root or bundled_root()
    found = []
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return found
    for name in names:
        if not PACK_ID_RE.match(name) or not os.path.isfile(os.path.join(root, name, PACK_FILE)):
            continue
        try:
            data = load_pack(name, root)
        except PackError as exc:
            log(f"Skipping pack: {exc}")
            continue
        found.append({"id": name, "name": data["name"].strip(),
                      "description": str(data.get("description", "") or "").strip()})
    return sorted(found, key=lambda p: p["name"].lower())


# --------------------------------------------------------------------------
# installing the pack files
# --------------------------------------------------------------------------

def install_pack_assets(pack_id, source_root=None, dest_root=None, overwrite=False):
    """Copy the pack's files to the user folder and return that folder.

    Files that already exist are kept (unless *overwrite*), so a background or a
    sound the user dropped in or replaced is never lost.
    """
    _check_id(pack_id)
    src = os.path.join(source_root or bundled_root(), pack_id)
    dst = pack_folder(pack_id, dest_root)
    if not os.path.isdir(src):
        raise PackError(f"Pack '{pack_id}' was not found.")
    for folder, _dirs, files in os.walk(src):
        rel = os.path.relpath(folder, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            if rel == "." and name == PACK_FILE:
                continue
            if name == ".gitkeep":
                continue
            target = os.path.join(target_dir, name)
            if overwrite or not os.path.exists(target):
                shutil.copy2(os.path.join(folder, name), target)
    os.makedirs(os.path.join(dst, "backgrounds"), exist_ok=True)
    os.makedirs(os.path.join(dst, "audio"), exist_ok=True)
    return dst


def _inside(folder, path):
    folder = os.path.realpath(folder)
    path = os.path.realpath(path)
    return path == folder or path.startswith(folder + os.sep)


def _backgrounds(folder):
    bg_dir = os.path.join(folder, "backgrounds")
    try:
        names = sorted(os.listdir(bg_dir), key=str.lower)
    except OSError:
        return []
    return [os.path.join(bg_dir, n) for n in names
            if n.lower().endswith(IMAGE_EXTS) and os.path.isfile(os.path.join(bg_dir, n))]


# --------------------------------------------------------------------------
# applying and undoing
# --------------------------------------------------------------------------

def _type_ok(key, value):
    default = DEFAULT_CONFIG[key]
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    return True


def _clean_settings(raw, allowed, warnings):
    """Keep known, well-typed, in-range settings from a pack section."""
    clean = {}
    for key, value in (raw or {}).items():
        if key not in allowed or key not in DEFAULT_CONFIG:
            warnings.append(f"Ignored '{key}': a pack is not allowed to change it.")
            continue
        if not _type_ok(key, value):
            warnings.append(f"Ignored '{key}': wrong type.")
            continue
        if key in INT_RANGES:
            lo, hi = INT_RANGES[key]
            value = max(lo, min(hi, value))
        if key == "panel_color" and not HEX_COLOR_RE.match(value.strip()):
            warnings.append("Ignored 'panel_color': use a hex colour like #0b0f14.")
            continue
        if key == "theme" and value not in THEMES:
            warnings.append(f"Ignored 'theme': unknown theme '{value}'.")
            continue
        if key == "background_mode" and value not in BACKGROUND_MODES:
            warnings.append(f"Ignored 'background_mode': '{value}'.")
            continue
        if key == "difficulty" and value not in DIFFICULTIES:
            warnings.append(f"Ignored 'difficulty': '{value}'.")
            continue
        clean[key] = value.strip() if isinstance(value, str) else value
    return clean


def apply_pack(cfg, pack_id, include_protections=False, source_root=None,
               dest_root=None, undo_path=None):
    """Return ``(new_cfg, warnings)``: *cfg* with the pack applied. *cfg* is not modified.

    Raises PackError when the pack is broken or when protections are requested
    without an emergency password.
    """
    undo_path = undo_path or UNDO_PATH
    pack = load_pack(pack_id, source_root)
    if include_protections and not cfg.get("emergency_password_hash"):
        raise PackError("Set an emergency password (Protection tab) before enabling a pack's "
                        "protections, so you can always get back in.")

    warnings = []
    changes = _clean_settings(pack.get("config", {}), APPLY_KEYS, warnings)
    folder = install_pack_assets(pack_id, source_root, dest_root)

    # Files inside the pack folder: "audio/success.wav" -> absolute path.
    for key in PACK_FILE_KEYS:
        value = changes.get(key)
        if not value:
            continue
        path = os.path.normpath(os.path.join(folder, value))
        if not _inside(folder, path):
            warnings.append(f"Ignored '{key}': the file must be inside the pack folder.")
            del changes[key]
        elif not os.path.isfile(path):
            warnings.append(f"Ignored '{key}': file not found ({value}).")
            del changes[key]
        else:
            changes[key] = path

    # Backgrounds: every image / GIF found in the pack's backgrounds/ folder.
    images = _backgrounds(folder)
    changes["background_images"] = images
    changes["background_image"] = images[0] if images else ""
    if not images:
        warnings.append("No background images yet: drop images or GIFs in "
                        f"{os.path.join(folder, 'backgrounds')} and apply the pack again.")

    if "ui_texts" in pack:
        changes["ui_texts"] = clean_ui_texts(pack["ui_texts"])
    else:
        changes["ui_texts"] = {}

    if include_protections:
        changes.update(_clean_settings(pack.get("protections", {}), PROTECTION_KEYS, warnings))

    previous = {key: cfg.get(key, DEFAULT_CONFIG.get(key)) for key in changes}
    # Applying the same pack again (to pick up new images, say) must not lose the way
    # back to the settings you had before it: keep the first snapshot.
    if last_applied_pack(undo_path) == pack_id:
        try:
            with open(undo_path, "r", encoding="utf-8") as f:
                previous = {**previous, **json.load(f)["previous"]}
        except (OSError, ValueError, KeyError, TypeError):
            pass
    new_cfg = {**cfg, **changes}
    try:
        save_json(undo_path, {"pack": pack_id, "previous": previous})
    except OSError as exc:
        log(f"Could not save the pack undo file: {exc}")
        warnings.append("The previous settings could not be saved, so this cannot be undone.")
    return new_cfg, warnings


def last_applied_pack(undo_path=None):
    """Name of the pack that "Undo" would revert, or "" when there is nothing to undo."""
    try:
        with open(undo_path or UNDO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("previous"), dict):
            return str(data.get("pack", ""))
    except (OSError, ValueError):
        pass
    return ""


def undo_last_pack(cfg, undo_path=None):
    """Return *cfg* with the settings the last pack changed put back. One undo only."""
    undo_path = undo_path or UNDO_PATH
    try:
        with open(undo_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        raise PackError("There is no pack to undo.")
    previous = data.get("previous") if isinstance(data, dict) else None
    if not isinstance(previous, dict) or not previous:
        raise PackError("There is no pack to undo.")
    # Only settings a pack can change are ever restored; the password stays as it is now.
    allowed = APPLY_KEYS | PROTECTION_KEYS | {"background_images", "background_image", "ui_texts"}
    restored = {k: v for k, v in previous.items() if k in allowed and k in DEFAULT_CONFIG}
    try:
        os.remove(undo_path)
    except OSError:
        pass
    return {**cfg, **restored}
