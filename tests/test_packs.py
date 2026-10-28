"""Tests for theme packs (packs.py), themes and interface texts (themes.py)."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import packs  # noqa: E402
import phrases  # noqa: E402
import themes  # noqa: E402
from config import DEFAULT_CONFIG  # noqa: E402

REPO_PACKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "packs")
PASSWORD_KEYS = ("emergency_password_salt", "emergency_password_hash", "emergency_password_iterations")


def write(path, text="x", mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        f.write(text)


class PackTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = os.path.join(self.tmp.name, "source")
        self.dest = os.path.join(self.tmp.name, "user")
        self.undo = os.path.join(self.tmp.name, "undo.json")
        for target in (config, packs):
            patcher = mock.patch.object(target, "log", lambda *_a, **_k: None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_pack(self, pack_id="demo", data=None, files=("phrases.csv", "audio/ok.wav")):
        folder = os.path.join(self.source, pack_id)
        body = {"name": "Demo", "config": {"theme": "Matrix", "phrases_file": "phrases.csv",
                                           "success_sound": "audio/ok.wav"}}
        body.update(data or {})
        write(os.path.join(folder, "pack.json"), json.dumps(body))
        for rel in files:
            write(os.path.join(folder, rel), "phrase,category,difficulty\nHello,General,easy\n")
        return folder

    def apply(self, cfg=None, pack_id="demo", **kwargs):
        return packs.apply_pack(dict(cfg if cfg is not None else DEFAULT_CONFIG), pack_id,
                                source_root=self.source, dest_root=self.dest,
                                undo_path=self.undo, **kwargs)


class ShippedTechDomTests(unittest.TestCase):
    """The packs that ship in the repository must be valid and safe."""

    PACK_ID = "techdom"
    PACK_NAME = "TechDom"

    def setUp(self):
        self.pack = packs.load_pack(self.PACK_ID, REPO_PACKS)

    def test_it_is_listed(self):
        found = {p["id"]: p for p in packs.list_packs(REPO_PACKS)}
        self.assertIn(self.PACK_ID, found)
        self.assertEqual(found[self.PACK_ID]["name"], self.PACK_NAME)
        self.assertTrue(found[self.PACK_ID]["description"])

    def test_every_setting_is_allowed_and_well_typed(self):
        warnings = []
        clean = packs._clean_settings(self.pack["config"], packs.APPLY_KEYS, warnings)
        self.assertEqual(warnings, [])
        self.assertEqual(set(clean), set(self.pack["config"]))

    def test_protections_are_allowed(self):
        warnings = []
        clean = packs._clean_settings(self.pack["protections"], packs.PROTECTION_KEYS, warnings)
        self.assertEqual(warnings, [])
        self.assertEqual(set(clean), set(self.pack["protections"]))

    def test_theme_exists_and_files_are_there(self):
        self.assertIn(self.pack["config"]["theme"], themes.THEMES)
        folder = os.path.join(REPO_PACKS, self.PACK_ID)
        for key in packs.PACK_FILE_KEYS:
            rel = self.pack["config"].get(key)
            if rel:
                self.assertTrue(os.path.isfile(os.path.join(folder, rel)), rel)

    def test_phrases_load_with_every_difficulty(self):
        items = phrases.load_external_phrases(os.path.join(REPO_PACKS, self.PACK_ID, "phrases.csv"))
        self.assertGreaterEqual(len(items), 20)
        self.assertEqual({i["difficulty"] for i in items}, {"easy", "normal", "hard", "extreme"})
        texts = [i["text"] for i in items]
        self.assertEqual(len(texts), len(set(texts)))

    def test_ui_texts_survive_cleaning_and_format(self):
        clean = themes.clean_ui_texts(self.pack["ui_texts"])
        self.assertEqual(set(clean), set(self.pack["ui_texts"]))
        cfg = {"ui_texts": clean}
        self.assertIn("2", themes.ui_text(cfg, "round", "?", done=1, total=2))
        self.assertIn("5", themes.ui_text(cfg, "lockout", "?", n=5))
        self.assertIn("3", themes.ui_text(cfg, "wait", "?", n=3))
        self.assertIn(themes.error_text(cfg, "default"), clean["errors"])

    def test_it_ships_default_backgrounds_and_sounds(self):
        folder = os.path.join(REPO_PACKS, self.PACK_ID)
        images = [n for n in os.listdir(os.path.join(folder, "backgrounds"))
                  if n.lower().endswith(packs.IMAGE_EXTS)]
        self.assertGreaterEqual(len(images), 3)
        for name in ("success.wav", "error.wav"):
            self.assertTrue(os.path.isfile(os.path.join(folder, "audio", name)), name)
        try:
            from PIL import Image
        except ImportError:
            return
        for name in images:
            with Image.open(os.path.join(folder, "backgrounds", name)) as img:
                img.verify()

    def test_applying_it_uses_the_shipped_backgrounds_without_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            new, warnings = packs.apply_pack(
                dict(DEFAULT_CONFIG), self.PACK_ID, source_root=REPO_PACKS,
                dest_root=os.path.join(tmp, "user"), undo_path=os.path.join(tmp, "undo.json"))
            self.assertEqual(warnings, [])
            self.assertGreaterEqual(len(new["background_images"]), 3)
            self.assertEqual(new["background_image"], new["background_images"][0])
            for path in new["background_images"] + [new["success_sound"], new["error_sound"],
                                                    new["phrases_file"]]:
                self.assertTrue(os.path.isfile(path), path)

    def test_pack_never_sets_password_or_auto_protection(self):
        for section in ("config", "protections"):
            for key in self.pack[section]:
                self.assertNotIn(key, PASSWORD_KEYS)
                self.assertNotIn(key, ("auto_protection", "enabled", "schedule_enabled"))



class ShippedPetDomTests(ShippedTechDomTests):
    PACK_ID = "petdom"
    PACK_NAME = "PetDom"

class ThemeTests(unittest.TestCase):
    def test_existing_themes_keep_their_accent(self):
        self.assertEqual(themes.accent_for("Cyber Red"), "#ff1744")
        self.assertEqual(themes.accent_for("Matrix"), "#00e676")
        self.assertEqual(themes.theme_colors("Blackout"), ("#eeeeee", "#777777", "#444444"))

    def test_unknown_theme_falls_back(self):
        self.assertEqual(themes.theme_colors("Nope"), themes.THEMES["Cyber Red"])

    def test_ui_text_defaults_and_bad_overrides(self):
        self.assertEqual(themes.ui_text({}, "button", "GO"), "GO")
        self.assertEqual(themes.ui_text({"ui_texts": "junk"}, "button", "GO"), "GO")
        self.assertEqual(themes.ui_text({"ui_texts": {"button": "  "}}, "button", "GO"), "GO")
        self.assertEqual(themes.ui_text({"ui_texts": {"wait": "{oops} {n}"}}, "wait", "Wait {n}s", n=4), "{oops} 4")
        self.assertEqual(themes.ui_text({"ui_texts": {"wait": "{ {n}s }"}}, "wait", "Wait {n}s", n=4), "{ 4s }")
        self.assertEqual(themes.ui_text({"ui_texts": {"wait": "Hold {n}"}}, "wait", "Wait {n}s", n=4), "Hold 4")
        self.assertEqual(themes.error_text({"ui_texts": {"errors": []}}, "DEFAULT"), "DEFAULT")
        self.assertEqual(themes.error_text({"ui_texts": {"errors": [1, " "]}}, "DEFAULT"), "DEFAULT")

    def test_placeholders_are_replaced_without_str_format(self):
        cfg = {"ui_texts": {"wait": "{n.__class__} / {n:>5}"}}
        self.assertEqual(themes.ui_text(cfg, "wait", "d", n=3), "{n.__class__} / {n:>5}")

    def test_clean_ui_texts_drops_unknown_and_too_long(self):
        clean = themes.clean_ui_texts({"header": "Hi", "evil": "x", "button": "y" * 500,
                                       "errors": ["a", 5, "b"]})
        self.assertEqual(clean, {"header": "Hi", "errors": ["a", "b"]})
        self.assertEqual(themes.clean_ui_texts("nope"), {})

    def test_default_config_has_empty_ui_texts(self):
        self.assertEqual(DEFAULT_CONFIG["ui_texts"], {})


class ListAndLoadTests(PackTestCase):
    def test_list_skips_broken_and_oddly_named_folders(self):
        self.make_pack("good")
        write(os.path.join(self.source, "broken", "pack.json"), "{not json")
        write(os.path.join(self.source, "Bad Name", "pack.json"), json.dumps({"name": "X"}))
        write(os.path.join(self.source, "noname", "pack.json"), json.dumps({"config": {}}))
        self.assertEqual([p["id"] for p in packs.list_packs(self.source)], ["good"])

    def test_list_of_missing_folder_is_empty(self):
        self.assertEqual(packs.list_packs(os.path.join(self.tmp.name, "nothing")), [])

    def test_load_rejects_path_tricks_and_missing_packs(self):
        for bad in ("../x", "a/b", "", "UPPER", None):
            with self.assertRaises(packs.PackError):
                packs.load_pack(bad, self.source)
        with self.assertRaises(packs.PackError):
            packs.load_pack("absent", self.source)


class ApplyTests(PackTestCase):
    def test_settings_applied_and_paths_resolved(self):
        self.make_pack()
        new, warnings = self.apply()
        folder = os.path.join(self.dest, "demo")
        self.assertEqual(new["theme"], "Matrix")
        self.assertEqual(new["phrases_file"], os.path.join(folder, "phrases.csv"))
        self.assertEqual(new["success_sound"], os.path.join(folder, "audio", "ok.wav"))
        self.assertTrue(os.path.isfile(new["phrases_file"]))
        self.assertTrue(os.path.isfile(new["success_sound"]))
        self.assertTrue(any("No background images" in w for w in warnings))

    def test_input_config_is_not_modified(self):
        self.make_pack()
        cfg = dict(DEFAULT_CONFIG)
        self.apply(cfg)
        self.assertEqual(cfg, DEFAULT_CONFIG)

    def test_password_and_unlisted_settings_are_never_touched(self):
        self.make_pack(data={"config": {
            "theme": "Matrix", "emergency_password_hash": "abcd", "auto_protection": True,
            "strict_mode": True, "idle_lock_enabled": True, "enabled": False,
            "schedule_enabled": True, "xp": 999}})
        cfg = {**DEFAULT_CONFIG, "emergency_password_salt": "ab12", "emergency_password_hash": "cd34"}
        new, warnings = self.apply(cfg, include_protections=True)
        self.assertEqual(new["emergency_password_hash"], "cd34")
        self.assertEqual(new["emergency_password_salt"], "ab12")
        for key in ("auto_protection", "strict_mode", "idle_lock_enabled", "enabled",
                    "schedule_enabled", "xp"):
            self.assertEqual(new[key], DEFAULT_CONFIG[key], key)
        self.assertGreaterEqual(len([w for w in warnings if "not allowed" in w]), 7)

    def test_wrong_types_unknown_theme_and_ranges(self):
        self.make_pack(data={"config": {"theme": "Nope", "required_repeats": "3",
                                        "scanlines": 1, "max_attempts": 9999,
                                        "panel_color": "red", "background_mode": "weird"}})
        new, _ = self.apply()
        self.assertEqual(new["theme"], DEFAULT_CONFIG["theme"])
        self.assertEqual(new["required_repeats"], DEFAULT_CONFIG["required_repeats"])
        self.assertEqual(new["scanlines"], DEFAULT_CONFIG["scanlines"])
        self.assertEqual(new["max_attempts"], 100)
        self.assertEqual(new["panel_color"], DEFAULT_CONFIG["panel_color"])
        self.assertEqual(new["background_mode"], DEFAULT_CONFIG["background_mode"])

    def test_files_outside_the_pack_or_missing_are_ignored(self):
        outside = os.path.join(self.tmp.name, "secret.wav")
        write(outside)
        self.make_pack(data={"config": {"success_sound": "../../secret.wav",
                                        "error_sound": outside, "phrases_file": "gone.csv"}})
        new, warnings = self.apply()
        for key in ("success_sound", "error_sound", "phrases_file"):
            self.assertEqual(new[key], DEFAULT_CONFIG[key])
        self.assertEqual(len([w for w in warnings if "Ignored" in w]), 3)

    def test_backgrounds_are_every_image_sorted(self):
        folder = self.make_pack(files=("phrases.csv", "audio/ok.wav", "backgrounds/b.gif",
                                       "backgrounds/A.png", "backgrounds/notes.txt"))
        new, warnings = self.apply()
        base = os.path.join(self.dest, "demo", "backgrounds")
        self.assertEqual(new["background_images"], [os.path.join(base, "A.png"), os.path.join(base, "b.gif")])
        self.assertEqual(new["background_image"], os.path.join(base, "A.png"))
        self.assertFalse(any("No background" in w for w in warnings))
        self.assertTrue(os.path.isdir(folder))

    def test_images_added_by_the_user_are_found_on_reapply(self):
        self.make_pack()
        self.apply()
        write(os.path.join(self.dest, "demo", "backgrounds", "mine.gif"), "gif", "w")
        new, _ = self.apply()
        self.assertEqual(new["background_images"], [os.path.join(self.dest, "demo", "backgrounds", "mine.gif")])

    def test_user_edited_files_are_kept_on_reapply(self):
        self.make_pack()
        self.apply()
        mine = os.path.join(self.dest, "demo", "phrases.csv")
        write(mine, "phrase\nMy own phrase\n")
        self.apply()
        with open(mine, encoding="utf-8") as f:
            self.assertIn("My own phrase", f.read())

    def test_pack_json_is_not_copied(self):
        self.make_pack()
        self.apply()
        self.assertFalse(os.path.exists(os.path.join(self.dest, "demo", "pack.json")))

    def test_ui_texts_are_cleaned_and_replace_old_ones(self):
        self.make_pack(data={"ui_texts": {"header": "HELLO", "junk": "x"}})
        new, _ = self.apply({**DEFAULT_CONFIG, "ui_texts": {"button": "OLD"}})
        self.assertEqual(new["ui_texts"], {"header": "HELLO"})

    def test_pack_without_ui_texts_clears_previous_ones(self):
        self.make_pack()
        new, _ = self.apply({**DEFAULT_CONFIG, "ui_texts": {"button": "OLD"}})
        self.assertEqual(new["ui_texts"], {})


class ProtectionTests(PackTestCase):
    PROTECT = {"protections": {"strict_mode": True, "idle_lock_enabled": True, "idle_lock_minutes": 20,
                               "auto_protection": True, "xp": 5}}

    def test_protections_need_an_emergency_password(self):
        self.make_pack(data=self.PROTECT)
        with self.assertRaises(packs.PackError):
            self.apply(include_protections=True)
        self.assertFalse(os.path.exists(self.undo))

    def test_protections_are_off_unless_requested(self):
        self.make_pack(data=self.PROTECT)
        cfg = {**DEFAULT_CONFIG, "emergency_password_hash": "cd34", "emergency_password_salt": "ab"}
        new, _ = self.apply(cfg)
        self.assertFalse(new["strict_mode"])
        self.assertFalse(new["idle_lock_enabled"])

    def test_requested_protections_apply_only_allowed_keys(self):
        self.make_pack(data=self.PROTECT)
        cfg = {**DEFAULT_CONFIG, "emergency_password_hash": "cd34", "emergency_password_salt": "ab"}
        new, _ = self.apply(cfg, include_protections=True)
        self.assertTrue(new["strict_mode"])
        self.assertTrue(new["idle_lock_enabled"])
        self.assertEqual(new["idle_lock_minutes"], 20)
        self.assertFalse(new["auto_protection"])
        self.assertEqual(new["xp"], DEFAULT_CONFIG["xp"])


class UndoTests(PackTestCase):
    def test_undo_restores_what_the_pack_changed(self):
        self.make_pack()
        cfg = {**DEFAULT_CONFIG, "theme": "Blackout", "phrases": ["mine"], "daily_goal": 7,
               "background_images": ["a.png"], "background_image": "a.png",
               "ui_texts": {"button": "OLD"}}
        new, _ = self.apply(cfg)
        self.assertEqual(packs.last_applied_pack(self.undo), "demo")
        # a setting changed by the user after the pack stays as it is
        new["daily_goal"] = 9
        restored = packs.undo_last_pack(new, self.undo)
        self.assertEqual(restored["theme"], "Blackout")
        self.assertEqual(restored["background_images"], ["a.png"])
        self.assertEqual(restored["background_image"], "a.png")
        self.assertEqual(restored["ui_texts"], {"button": "OLD"})
        self.assertEqual(restored["phrases_file"], DEFAULT_CONFIG["phrases_file"])
        self.assertEqual(restored["daily_goal"], 9)
        self.assertEqual(restored["phrases"], ["mine"])

    def test_reapplying_the_same_pack_keeps_the_original_way_back(self):
        self.make_pack()
        orig = {**DEFAULT_CONFIG, "theme": "Blackout", "title": "MY TITLE"}
        first, _ = self.apply(orig)
        second, _ = self.apply(first)
        restored = packs.undo_last_pack(second, self.undo)
        self.assertEqual(restored["theme"], "Blackout")
        self.assertEqual(restored["title"], "MY TITLE")

    def test_reapplying_with_protections_still_restores_everything(self):
        self.make_pack(data={"protections": {"strict_mode": True}})
        orig = {**DEFAULT_CONFIG, "emergency_password_hash": "cd34", "emergency_password_salt": "ab"}
        first, _ = self.apply(orig)
        second, _ = self.apply(first, include_protections=True)
        self.assertTrue(second["strict_mode"])
        restored = packs.undo_last_pack(second, self.undo)
        self.assertFalse(restored["strict_mode"])
        self.assertEqual(restored["theme"], DEFAULT_CONFIG["theme"])

    def test_applying_another_pack_snapshots_the_state_before_it(self):
        self.make_pack("one", data={"name": "One", "config": {"theme": "Matrix"}}, files=())
        self.make_pack("two", data={"name": "Two", "config": {"theme": "Blackout"}}, files=())
        first, _ = self.apply(dict(DEFAULT_CONFIG), pack_id="one")
        second, _ = self.apply(first, pack_id="two")
        self.assertEqual(packs.last_applied_pack(self.undo), "two")
        self.assertEqual(packs.undo_last_pack(second, self.undo)["theme"], "Matrix")

    def test_undo_keeps_a_password_set_after_the_pack(self):
        self.make_pack()
        self.apply()
        new = {**DEFAULT_CONFIG, "emergency_password_hash": "ee", "emergency_password_salt": "ff"}
        restored = packs.undo_last_pack(new, self.undo)
        self.assertEqual(restored["emergency_password_hash"], "ee")

    def test_undo_only_works_once(self):
        self.make_pack()
        self.apply()
        packs.undo_last_pack(dict(DEFAULT_CONFIG), self.undo)
        self.assertEqual(packs.last_applied_pack(self.undo), "")
        with self.assertRaises(packs.PackError):
            packs.undo_last_pack(dict(DEFAULT_CONFIG), self.undo)

    def test_undo_without_file_or_with_garbage(self):
        self.assertEqual(packs.last_applied_pack(self.undo), "")
        with self.assertRaises(packs.PackError):
            packs.undo_last_pack({}, self.undo)
        write(self.undo, "{nope")
        with self.assertRaises(packs.PackError):
            packs.undo_last_pack({}, self.undo)

    def test_undo_ignores_settings_a_pack_may_not_change(self):
        write(self.undo, json.dumps({"pack": "x", "previous": {
            "theme": "Matrix", "emergency_password_hash": "evil", "auto_protection": True}}))
        restored = packs.undo_last_pack({"emergency_password_hash": "mine", "auto_protection": False}, self.undo)
        self.assertEqual(restored["theme"], "Matrix")
        self.assertEqual(restored["emergency_password_hash"], "mine")
        self.assertFalse(restored["auto_protection"])


class BackupInteropTests(unittest.TestCase):
    """A backup file is untrusted: pack-related settings must be cleaned on import."""

    def setUp(self):
        import backup
        self.backup = backup

    def test_ui_texts_from_a_backup_are_cleaned(self):
        clean, _ = self.backup.sanitize_config({"ui_texts": {
            "button": "y" * 5000, "header": " Hello ", "evil": 1, "errors": ["a", 7, "b"]}})
        self.assertEqual(clean["ui_texts"], {"header": "Hello", "errors": ["a", "b"]})

    def test_ui_texts_of_the_wrong_type_are_rejected(self):
        clean, warnings = self.backup.sanitize_config({"ui_texts": "junk"})
        self.assertNotIn("ui_texts", clean)
        self.assertTrue(any("ui_texts" in w for w in warnings))

    def test_a_valid_pack_config_survives_the_round_trip(self):
        pack = packs.load_pack("techdom", REPO_PACKS)
        clean, _ = self.backup.sanitize_config({"ui_texts": pack["ui_texts"], "theme": "TechDom"})
        self.assertEqual(clean["ui_texts"], themes.clean_ui_texts(pack["ui_texts"]))
        self.assertEqual(clean["theme"], "TechDom")

    def test_background_list_must_be_a_list_of_text(self):
        for bad in ("a.png", [1, 2], {"a": 1}):
            clean, warnings = self.backup.sanitize_config({"background_images": bad})
            self.assertNotIn("background_images", clean)
            self.assertTrue(any("background_images" in w for w in warnings), bad)
        clean, _ = self.backup.sanitize_config({"background_images": [" http://x/a.png ", "", "  "]})
        self.assertEqual(clean["background_images"], ["http://x/a.png"])
        clean, _ = self.backup.sanitize_config({"background_images": None})
        self.assertIsNone(clean["background_images"])

    def test_missing_pack_files_get_a_hint_to_apply_the_pack_again(self):
        gone = r"C:\Users\old\AppData\Roaming\PhraseLock\packs\techdom\backgrounds\grid.png"
        _, warnings = self.backup.sanitize_config({"background_images": [gone],
                                                   "success_sound": gone.replace("backgrounds", "audio")})
        text = "\n".join(warnings)
        self.assertIn("apply the pack again", text)
        self.assertIn("background_images", text)
        self.assertIn("success_sound", text)

    def test_missing_ordinary_files_get_no_pack_hint(self):
        _, warnings = self.backup.sanitize_config({"background_images": [r"C:\pics\gone.png"]})
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("pack", warnings[0])


if __name__ == "__main__":
    unittest.main()


class UserPackTests(unittest.TestCase):
    """Packs made by the user live in %APPDATA%\\PhraseLock\\packs and must work like shipped ones."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mine = os.path.join(self.tmp.name, "mine")
        os.makedirs(self.mine)
        self.undo = os.path.join(self.tmp.name, "undo.json")
        patcher = mock.patch.object(packs, "user_root", return_value=self.mine)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_pack(self, pack_id, name, **extra):
        data = {"name": name, "config": {"theme": "Matrix", "title": "Mine"}, **extra}
        write(os.path.join(self.mine, pack_id, "pack.json"), json.dumps(data))

    def test_user_packs_are_listed_with_the_shipped_ones(self):
        self.write_pack("cozy", "Cozy")
        ids = {p["id"] for p in packs.list_packs()}
        self.assertTrue({"techdom", "petdom", "cozy"} <= ids)

    def test_user_pack_wins_over_a_shipped_one_with_the_same_id(self):
        self.write_pack("techdom", "My TechDom")
        found = {p["id"]: p["name"] for p in packs.list_packs()}
        self.assertEqual(found["techdom"], "My TechDom")

    def test_a_broken_user_pack_is_skipped(self):
        write(os.path.join(self.mine, "broken", "pack.json"), "{not json")
        self.assertNotIn("broken", {p["id"] for p in packs.list_packs()})

    def test_user_pack_can_be_applied_in_place(self):
        self.write_pack("cozy", "Cozy", ui_texts={"app_title": "COZY CORNER"})
        write(os.path.join(self.mine, "cozy", "backgrounds", "a.png"), "x")
        new, warnings = packs.apply_pack(dict(DEFAULT_CONFIG), "cozy", undo_path=self.undo)
        self.assertEqual((new["theme"], new["title"]), ("Matrix", "Mine"))
        self.assertEqual(new["ui_texts"]["app_title"], "COZY CORNER")
        self.assertEqual(new["background_images"], [os.path.join(self.mine, "cozy", "backgrounds", "a.png")])
        self.assertTrue(os.path.isfile(os.path.join(self.mine, "cozy", "pack.json")))   # nothing lost
        self.assertEqual(warnings, [])

    def test_shipped_packs_still_apply_with_user_packs_around(self):
        self.write_pack("cozy", "Cozy")
        new, _ = packs.apply_pack(dict(DEFAULT_CONFIG), "techdom", undo_path=self.undo)
        self.assertEqual(new["theme"], "TechDom")

    def test_every_shipped_pack_has_its_window_title(self):
        for pack_id in ("techdom", "petdom"):
            texts = packs.load_pack(pack_id, REPO_PACKS)["ui_texts"]
            self.assertTrue(texts["app_title"].strip() and texts["app_kicker"].strip(), pack_id)

    def test_window_title_texts_use_the_pack_and_fall_back(self):
        cfg = {"ui_texts": themes.clean_ui_texts({"app_title": "COZY CORNER"})}
        self.assertEqual(themes.ui_text(cfg, "app_title", "DEFAULT"), "COZY CORNER")
        self.assertEqual(themes.ui_text(cfg, "app_kicker", "// DEFAULT"), "// DEFAULT")
        self.assertEqual(themes.ui_text({}, "app_title", "DEFAULT"), "DEFAULT")


class ExportPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest = os.path.join(self.tmp.name, "mine")
        self.src = os.path.join(self.tmp.name, "files")
        self.phrases = os.path.join(self.src, "my phrases.csv")
        self.sound = os.path.join(self.src, "ding.wav")
        self.image = os.path.join(self.src, "wall.png")
        write(self.phrases, "phrase,category,difficulty\nHello there,x,easy\n")
        write(self.sound, "RIFF")
        write(self.image, "png")
        self.cfg = {**DEFAULT_CONFIG, "theme": "Matrix", "title": "Mine", "required_repeats": 3,
                    "phrases_file": self.phrases, "success_sound": self.sound,
                    "background_images": [self.image, "https://example.com/x.png"],
                    "ui_texts": {"button": "[ GO ]"}, "emergency_password_hash": "ab12"}

    def export(self, name="Cozy Corner", cfg=None):
        return packs.export_pack(self.cfg if cfg is None else cfg, name, dest_root=self.dest)

    def test_creates_a_valid_pack_folder(self):
        pack_id, folder, warnings = self.export()
        self.assertEqual(pack_id, "cozy-corner")
        data = packs.load_pack(pack_id, self.dest)
        self.assertEqual(data["name"], "Cozy Corner")
        self.assertEqual(data["config"]["theme"], "Matrix")
        self.assertEqual(data["config"]["required_repeats"], 3)
        self.assertEqual(data["ui_texts"]["button"], "[ GO ]")
        self.assertEqual(data["ui_texts"]["app_title"], "COZY CORNER")
        self.assertEqual(warnings, [])
        for rel in ("phrases_file", "success_sound"):
            self.assertTrue(os.path.isfile(os.path.join(folder, data["config"][rel])), rel)
        self.assertEqual(os.listdir(os.path.join(folder, "backgrounds")), ["wall.png"])

    def test_it_never_copies_secrets_or_unlisted_settings(self):
        pack_id, _folder, _ = self.export()
        text = json.dumps(packs.load_pack(pack_id, self.dest))
        self.assertNotIn("ab12", text)
        self.assertNotIn("emergency", text)
        self.assertNotIn("schedule", text)

    def test_exported_pack_applies_back_to_the_same_settings(self):
        pack_id, _folder, _ = self.export()
        new, warnings = packs.apply_pack(dict(DEFAULT_CONFIG), pack_id, source_root=self.dest,
                                         dest_root=self.dest, undo_path=os.path.join(self.tmp.name, "u.json"))
        self.assertEqual(warnings, [])
        self.assertEqual((new["theme"], new["required_repeats"], new["title"]), ("Matrix", 3, "Mine"))
        self.assertTrue(os.path.isfile(new["phrases_file"]) and os.path.isfile(new["success_sound"]))
        self.assertEqual(len(new["background_images"]), 1)

    def test_custom_theme_is_left_out_with_a_warning(self):
        _id, _folder, warnings = self.export("Odd", {**self.cfg, "theme": "My own"})
        self.assertTrue(warnings)
        self.assertNotIn("theme", packs.load_pack("odd", self.dest)["config"])

    def test_existing_or_shipped_names_are_refused(self):
        self.export("Cozy")
        with self.assertRaises(packs.PackError):
            self.export("cozy")
        with mock.patch.object(packs, "bundled_root", return_value=REPO_PACKS):
            with self.assertRaises(packs.PackError):
                packs.export_pack(self.cfg, "TechDom")

    def test_bad_names_are_refused(self):
        for bad in ("", "   ", "x" * 41, "!!!", "***"):
            with self.assertRaises(packs.PackError, msg=bad):
                self.export(bad)

    def test_name_to_id(self):
        self.assertEqual(packs.pack_id_from_name("  My Cozy_Pack! "), "my-cozy_pack")
        self.assertEqual(packs.pack_id_from_name("???"), "")
