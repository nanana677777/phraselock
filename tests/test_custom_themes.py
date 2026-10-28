"""Tests for custom themes (themes.py helpers behind Settings > Look > Theme editor)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import themes  # noqa: E402
from config import DEFAULT_CONFIG  # noqa: E402

OCEAN = ["#0077be", "#00e5ff", "#ffffff"]


class CleanTests(unittest.TestCase):
    def test_valid_theme_is_kept_and_normalised(self):
        clean = themes.clean_custom_themes({" Ocean ": ["#0077BE", " #00E5FF ", "#FFFFFF"]})
        self.assertEqual(clean, {"Ocean": OCEAN})

    def test_bad_shapes_are_ignored(self):
        for raw in (None, "x", 5, [], [("a", OCEAN)]):
            self.assertEqual(themes.clean_custom_themes(raw), {})

    def test_bad_entries_are_dropped_good_ones_kept(self):
        raw = {
            "Good": OCEAN,
            "": OCEAN,
            "   ": OCEAN,
            "Two": ["#000000", "#111111"],
            "Four": ["#000000"] * 4,
            "NotHex": ["red", "#111111", "#222222"],
            "Short": ["#fff", "#111111", "#222222"],
            "Numbers": [1, 2, 3],
            "x" * 31: OCEAN,
            7: OCEAN,
        }
        self.assertEqual(themes.clean_custom_themes(raw), {"Good": OCEAN})

    def test_built_in_names_are_refused_in_any_case(self):
        raw = {"matrix": OCEAN, "CYBER RED": OCEAN, "TechDom": OCEAN, "Mine": OCEAN}
        self.assertEqual(themes.clean_custom_themes(raw), {"Mine": OCEAN})

    def test_names_differing_only_by_case_keep_the_first(self):
        clean = themes.clean_custom_themes({"Ocean": OCEAN, "OCEAN": ["#000000"] * 3})
        self.assertEqual(list(clean), ["Ocean"])

    def test_the_number_of_themes_is_capped(self):
        raw = {f"T{i}": OCEAN for i in range(themes.MAX_CUSTOM_THEMES + 10)}
        self.assertEqual(len(themes.clean_custom_themes(raw)), themes.MAX_CUSTOM_THEMES)

    def test_default_config_has_no_custom_themes(self):
        self.assertEqual(DEFAULT_CONFIG["custom_themes"], {})


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {"custom_themes": {"Ocean": OCEAN, "alpha": OCEAN}}

    def test_custom_theme_colours(self):
        self.assertEqual(themes.theme_colors("Ocean", self.cfg), tuple(OCEAN))
        self.assertEqual(themes.accent_for("Ocean", self.cfg), "#0077be")

    def test_built_in_theme_wins_and_works_without_config(self):
        self.assertEqual(themes.theme_colors("Matrix"), themes.THEMES["Matrix"])
        self.assertEqual(themes.theme_colors("Matrix", self.cfg), themes.THEMES["Matrix"])

    def test_unknown_or_deleted_theme_falls_back_to_the_default(self):
        default = themes.THEMES[themes.DEFAULT_THEME]
        self.assertEqual(themes.theme_colors("Gone", self.cfg), default)
        self.assertEqual(themes.theme_colors("Ocean"), default)           # no cfg given
        self.assertEqual(themes.theme_colors("Ocean", {"custom_themes": "junk"}), default)
        self.assertEqual(themes.theme_colors("Ocean", None), default)

    def test_theme_names_lists_built_ins_then_custom_sorted(self):
        names = themes.theme_names(self.cfg)
        self.assertEqual(names[:len(themes.THEMES)], list(themes.THEMES))
        self.assertEqual(names[len(themes.THEMES):], ["alpha", "Ocean"])
        self.assertEqual(themes.theme_names(), list(themes.THEMES))

    def test_is_hex_colour(self):
        for good in ("#000000", "#AbCdEf", " #123456 "):
            self.assertTrue(themes.is_hex_colour(good), good)
        for bad in ("", "000000", "#12345", "#1234567", "#ggg000", None, 5, "red"):
            self.assertFalse(themes.is_hex_colour(bad), bad)


class NamingTests(unittest.TestCase):
    def test_check_theme_name(self):
        taken = ["Matrix", "Ocean"]
        self.assertIsNone(themes.check_theme_name("Sunset", taken))
        self.assertTrue(themes.check_theme_name("", taken))
        self.assertTrue(themes.check_theme_name("   ", taken))
        self.assertTrue(themes.check_theme_name("x" * 31, taken))
        self.assertTrue(themes.check_theme_name("matrix", taken))
        self.assertTrue(themes.check_theme_name("OCEAN", taken))

    def test_rename_may_keep_or_recase_its_own_name(self):
        taken = ["Matrix", "Ocean"]
        self.assertIsNone(themes.check_theme_name("Ocean", taken, allow="Ocean"))
        self.assertTrue(themes.check_theme_name("matrix", taken, allow="Ocean"))

    def test_copy_name(self):
        self.assertEqual(themes.copy_name("Matrix", ["Matrix"]), "Matrix copy")
        self.assertEqual(themes.copy_name("Matrix", ["Matrix", "Matrix copy"]), "Matrix copy 2")
        self.assertEqual(themes.copy_name("Matrix", ["matrix copy", "Matrix copy 2"]), "Matrix copy 3")

    def test_copy_name_stays_valid_for_long_names(self):
        base = "N" * themes.MAX_THEME_NAME_LENGTH
        name = themes.copy_name(base, [base])
        self.assertLessEqual(len(name), themes.MAX_THEME_NAME_LENGTH)
        self.assertIsNone(themes.check_theme_name(name, [base]))


class UsersOfThemesTests(unittest.TestCase):
    def test_backup_import_cleans_custom_themes(self):
        import backup
        clean, _ = backup.sanitize_config({"custom_themes": {"Ocean": OCEAN, "Matrix": OCEAN, "Bad": ["x"] * 3}})
        self.assertEqual(clean["custom_themes"], {"Ocean": OCEAN})

    def test_backup_import_rejects_the_wrong_type(self):
        import backup
        clean, warnings = backup.sanitize_config({"custom_themes": ["Ocean"]})
        self.assertNotIn("custom_themes", clean)
        self.assertTrue(warnings)

    def test_a_pack_does_not_touch_custom_themes(self):
        import packs
        self.assertNotIn("custom_themes", packs.APPLY_KEYS | packs.PROTECTION_KEYS)


if __name__ == "__main__":
    unittest.main()
