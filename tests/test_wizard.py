"""Tests for the first-launch setup wizard (wizard.py, Tk-free parts)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import packs  # noqa: E402
import stats  # noqa: E402
import wizard  # noqa: E402
from config import DEFAULT_CONFIG  # noqa: E402

REPO_PACKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "packs")


class WizardTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest = os.path.join(self.tmp.name, "user")
        self.undo = os.path.join(self.tmp.name, "undo.json")

    def apply(self, choices, cfg=None):
        return wizard.apply_choices(dict(cfg if cfg is not None else DEFAULT_CONFIG), choices,
                                    source_root=REPO_PACKS, dest_root=self.dest, undo_path=self.undo)


class ShouldRunTests(WizardTestCase):
    def test_runs_on_a_first_launch(self):
        self.assertTrue(wizard.should_run(dict(DEFAULT_CONFIG), os.path.join(self.tmp.name, "config.json")))

    def test_does_not_run_when_a_config_file_exists(self):
        path = os.path.join(self.tmp.name, "config.json")
        with open(path, "w") as f:
            f.write("{}")
        self.assertFalse(wizard.should_run(dict(DEFAULT_CONFIG), path))

    def test_does_not_run_once_done(self):
        self.assertFalse(wizard.should_run({**DEFAULT_CONFIG, "setup_done": True},
                                           os.path.join(self.tmp.name, "config.json")))

    def test_defaults_keep_existing_users_on_the_full_view(self):
        self.assertIs(DEFAULT_CONFIG["advanced_view"], True)
        self.assertIs(DEFAULT_CONFIG["setup_done"], False)


class PasswordTests(unittest.TestCase):
    def test_empty_is_a_skip(self):
        self.assertIsNone(wizard.validate_password("", ""))

    def test_mismatch_and_short_are_refused(self):
        self.assertTrue(wizard.validate_password("abcdef", "abcdeg"))
        self.assertTrue(wizard.validate_password("abc", "abc"))
        self.assertTrue(wizard.validate_password("abcdef", ""))

    def test_good_password(self):
        self.assertIsNone(wizard.validate_password("abcdef", "abcdef"))


class ApplyChoicesTests(WizardTestCase):
    def test_marks_setup_done_and_simple_view(self):
        new, _ = self.apply({})
        self.assertIs(new["setup_done"], True)
        self.assertIs(new["advanced_view"], False)
        self.assertIs(new["enabled"], True)

    def test_does_not_modify_the_input(self):
        cfg = dict(DEFAULT_CONFIG)
        self.apply({"pack": "techdom", "password": "secret1"}, cfg)
        self.assertEqual(cfg, DEFAULT_CONFIG)

    def test_pack_is_applied(self):
        new, warnings = self.apply({"pack": "techdom"})
        self.assertEqual(new["theme"], "TechDom")
        self.assertEqual(warnings, [])
        self.assertTrue(new["background_images"])

    def test_no_pack_keeps_the_default_look(self):
        new, _ = self.apply({"pack": ""})
        self.assertEqual(new["theme"], DEFAULT_CONFIG["theme"])
        self.assertEqual(new["ui_texts"], {})

    def test_difficulty_choice_wins_over_the_pack(self):
        new, _ = self.apply({"pack": "techdom", "difficulty": "easy"})
        self.assertEqual(new["difficulty"], "easy")

    def test_unknown_difficulty_is_ignored(self):
        new, _ = self.apply({"difficulty": "nightmare"})
        self.assertEqual(new["difficulty"], DEFAULT_CONFIG["difficulty"])

    def test_strictness_overrides_the_pack_rules(self):
        new, _ = self.apply({"pack": "petdom", "strictness": "strict"})
        for key, value in wizard.STRICTNESS_RULES["strict"].items():
            self.assertEqual(new[key], value, key)

    def test_pack_rules_are_kept_by_default(self):
        packed, _ = self.apply({"pack": "petdom"})
        self.assertEqual(packed["lockout_seconds"], 20)
        self.assertEqual(packed["max_attempts"], 6)

    def test_every_strictness_rule_is_a_real_setting_and_pack_allowed(self):
        for rules in wizard.STRICTNESS_RULES.values():
            for key in rules:
                self.assertIn(key, DEFAULT_CONFIG)
                self.assertIn(key, packs.APPLY_KEYS)

    def test_password_is_stored_hashed_and_verifies(self):
        new, _ = self.apply({"password": "secret1"})
        self.assertNotIn("secret1", json.dumps(new))
        self.assertTrue(stats.verify_emergency_password(new, "secret1"))
        self.assertFalse(stats.verify_emergency_password(new, "secret2"))

    def test_bad_password_raises(self):
        with self.assertRaises(ValueError):
            self.apply({"password": "abc"})

    def test_no_password_leaves_an_existing_one_alone(self):
        cfg = {**DEFAULT_CONFIG, "emergency_password_hash": "ab12", "emergency_password_salt": "cd34"}
        new, _ = self.apply({"password": ""}, cfg)
        self.assertEqual((new["emergency_password_hash"], new["emergency_password_salt"]), ("ab12", "cd34"))

    def test_protections_need_a_password(self):
        without, _ = self.apply({"pack": "techdom", "protections": True})
        self.assertFalse(without["strict_mode"])
        with_pw, _ = self.apply({"pack": "techdom", "protections": True, "password": "secret1"})
        self.assertTrue(with_pw["strict_mode"])
        self.assertTrue(with_pw["idle_lock_enabled"])

    def test_protections_without_a_pack_warn(self):
        new, warnings = self.apply({"pack": "", "protections": True, "password": "secret1"})
        self.assertFalse(new["strict_mode"])
        self.assertTrue(warnings)

    def test_enabled_choice(self):
        new, _ = self.apply({"enabled": False})
        self.assertIs(new["enabled"], False)

    def test_existing_settings_survive(self):
        cfg = {**DEFAULT_CONFIG, "daily_goal": 9, "schedule_enabled": True, "schedule_start": "09:00"}
        new, _ = self.apply({"pack": "petdom"}, cfg)
        self.assertEqual((new["daily_goal"], new["schedule_enabled"], new["schedule_start"]), (9, True, "09:00"))

    def test_unknown_pack_raises(self):
        with self.assertRaises(packs.PackError):
            self.apply({"pack": "nope"})

    def test_result_survives_a_json_round_trip(self):
        new, _ = self.apply({"pack": "techdom", "password": "secret1", "protections": True})
        self.assertEqual(json.loads(json.dumps(new)), new)


class SummaryTests(unittest.TestCase):
    def test_summary_mentions_every_answer(self):
        text = "\n".join(wizard.summary_lines(
            {"difficulty": "hard", "strictness": "strict", "password": "secret1", "protections": True}, "TechDom"))
        for word in ("TechDom", "Hard", "Strict", "set", "Protections"):
            self.assertIn(word, text)

    def test_summary_defaults(self):
        text = "\n".join(wizard.summary_lines({}))
        self.assertIn("default look", text)
        self.assertIn("none", text)

    def test_every_choice_has_a_label(self):
        for group in (wizard.DIFFICULTY_CHOICES, wizard.STRICTNESS_CHOICES):
            for key, label, detail in group:
                self.assertTrue(key is not None and label and detail)


class SkipTests(WizardTestCase):
    def test_skip_keeps_settings_and_shows_everything(self):
        path = os.path.join(self.tmp.name, "config.json")
        new = wizard.mark_skipped({**DEFAULT_CONFIG, "theme": "Matrix"}, config_path=path)
        self.assertEqual(new["theme"], "Matrix")
        self.assertIs(new["setup_done"], True)
        self.assertIs(new["advanced_view"], True)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f), new)


if __name__ == "__main__":
    unittest.main()
