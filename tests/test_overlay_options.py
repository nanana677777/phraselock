import unittest

import panelpos as pp
import typingaid as ta
from backup import sanitize_config
from config import DEFAULT_CONFIG


class PrefixTests(unittest.TestCase):
    def test_prefix_and_fraction(self):
        self.assertEqual(ta.correct_prefix("I obx", "I obey."), (4, "I ob"))
        self.assertEqual(ta.correct_prefix("", "abc"), (0, ""))
        self.assertEqual(ta.correct_prefix("abc", "abc"), (3, "abc"))
        self.assertEqual(ta.progress_fraction("ab", "abcd"), 0.5)
        self.assertEqual(ta.progress_fraction("x", "abcd"), 0.0)
        self.assertEqual(ta.progress_fraction("abcdzzz", "abcd"), 1.0)
        self.assertEqual(ta.progress_fraction("a", ""), 0.0)

    def test_leading_space_ignored_like_the_challenge(self):
        self.assertEqual(ta.correct_prefix("  ab", "abc"), (2, "  ab"))
        self.assertEqual(ta.correct_prefix("ab", "  abc"), (2, "ab"))

    def test_case_and_accents(self):
        self.assertEqual(ta.correct_prefix("ECOLE", "école", True)[0], 5)
        self.assertEqual(ta.correct_prefix("ECOLE", "école", False)[0], 0)

    def test_spaces_inside_count(self):
        self.assertEqual(ta.correct_prefix("a b x", "a b c"), (4, "a b "))


class PositionTests(unittest.TestCase):
    W, H, PW, PH = 1920, 1080, 700, 420

    def origin(self, position, cx=50, cy=50):
        return pp.panel_origin(position, self.W, self.H, self.PW, self.PH, cx, cy)

    def test_center_top_bottom(self):
        self.assertEqual(self.origin("center"), (610, 330))
        x, y = self.origin("top")
        self.assertEqual((x, y < 330), (610, True))
        x, y = self.origin("bottom")
        self.assertEqual(x, 610)
        self.assertTrue(330 < y and y + self.PH <= self.H)

    def test_custom_corners_stay_on_screen(self):
        self.assertEqual(self.origin("custom", 0, 0), (0, 0))
        self.assertEqual(self.origin("custom", 100, 100), (self.W - self.PW, self.H - self.PH))
        self.assertEqual(self.origin("custom", 250, -5), (self.W - self.PW, 0))   # clamped
        self.assertEqual(self.origin("custom", "x", None), (610, 330))             # junk -> centre values

    def test_unknown_position_is_centre_and_small_screen_is_safe(self):
        self.assertEqual(self.origin("sideways"), (610, 330))
        self.assertEqual(pp.panel_origin("bottom", 500, 300, 700, 420), (0, 0))
        self.assertEqual(pp.normalize_position("nope"), "center")


class ConfigTests(unittest.TestCase):
    def test_defaults_keep_the_old_behaviour(self):
        self.assertEqual(DEFAULT_CONFIG["panel_position"], "center")
        self.assertFalse(DEFAULT_CONFIG["show_typing_progress"])
        self.assertFalse(DEFAULT_CONFIG["keep_correct_on_error"])

    def test_backup_clamps_custom_position(self):
        clean, _ = sanitize_config({"panel_custom_x": 500, "panel_custom_y": -4, "panel_position": "top"})
        self.assertEqual((clean["panel_custom_x"], clean["panel_custom_y"], clean["panel_position"]), (100, 0, "top"))


if __name__ == "__main__":
    unittest.main()
