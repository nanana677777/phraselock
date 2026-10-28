import json
import os
import tempfile
import unittest
from unittest import mock

import emergency
import stats
from config import DEFAULT_CONFIG


class StepsTests(unittest.TestCase):
    def test_count_is_clamped(self):
        self.assertEqual(emergency.count({}), 3)
        self.assertEqual(emergency.count({"emergency_confirmations": 0}), 0)
        self.assertEqual(emergency.count({"emergency_confirmations": 99}), 5)
        self.assertEqual(emergency.count({"emergency_confirmations": "x"}), 3)
        self.assertEqual(emergency.count({"emergency_confirmations": -2}), 0)

    def test_number_of_steps_matches(self):
        for n in range(0, 6):
            self.assertEqual(len(emergency.steps({"emergency_confirmations": n})), n)

    def test_last_step_mentions_penalty(self):
        cfg = {"emergency_confirmations": 2, "emergency_penalty_streak": True, "emergency_penalty_xp": 40}
        steps = emergency.steps(cfg)
        self.assertNotIn("Penalty", steps[0][1])
        self.assertIn("streak will be reset", steps[-1][1])
        self.assertIn("40 XP", steps[-1][1])

    def test_no_penalty_text_by_default(self):
        self.assertEqual(emergency.penalty_text(DEFAULT_CONFIG), "")
        self.assertEqual(emergency.penalty(DEFAULT_CONFIG), {"streak": False, "xp": 0})

    def test_apply_penalty_only_when_configured(self):
        func = mock.Mock(return_value="done")
        self.assertIsNone(emergency.apply_penalty({}, func))
        func.assert_not_called()
        self.assertEqual(emergency.apply_penalty({"emergency_penalty_xp": 10}, func), "done")
        func.assert_called_once_with(False, 10)


class PenaltyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "streak.json")
        patcher = mock.patch.object(stats, "STREAK_PATH", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def write(self, data):
        with open(self.path, "w") as f:
            json.dump(data, f)

    def read(self):
        with open(self.path) as f:
            return json.load(f)

    def test_streak_reset_keeps_best(self):
        self.write({"current_streak": 6, "best_streak": 9, "last_qualifying_day": "2026-01-01", "xp": 100})
        taken = stats.apply_emergency_penalty(True, 0)
        self.assertEqual(taken, {"streak": 6, "xp": 0})
        data = self.read()
        self.assertEqual((data["current_streak"], data["best_streak"], data["xp"]), (0, 9, 100))

    def test_xp_never_below_zero(self):
        self.write({"xp": 30})
        self.assertEqual(stats.apply_emergency_penalty(False, 50)["xp"], 30)
        self.assertEqual(self.read()["xp"], 0)

    def test_nothing_configured_writes_nothing(self):
        stats.apply_emergency_penalty(False, 0)
        self.assertFalse(os.path.exists(self.path))


if __name__ == "__main__":
    unittest.main()


class PackTextTests(unittest.TestCase):
    def test_pack_steps_replace_defaults_by_position(self):
        cfg = {"emergency_confirmations": 5, "ui_texts": {"emergency_steps": [
            {"title": "A", "text": "a"}, {"title": "B", "text": "b"}]}}
        steps = emergency.steps(cfg)
        self.assertEqual(steps[:2], [("A", "a"), ("B", "b")])
        self.assertEqual(steps[2], emergency._STEPS[2])

    def test_pack_last_step_used_when_fewer_screens(self):
        custom = [{"title": str(i), "text": str(i)} for i in range(5)]
        steps = emergency.steps({"emergency_confirmations": 2, "ui_texts": {"emergency_steps": custom}})
        self.assertEqual([t for t, _ in steps], ["0", "4"])

    def test_clean_ui_texts_validates_steps(self):
        import themes
        clean = themes.clean_ui_texts({"emergency_steps": [
            {"title": "ok", "text": "fine"}, {"title": "", "text": "x"}, "junk", {"title": "t" * 99, "text": "x"}],
            "emergency_open": "Out"})
        self.assertEqual(clean["emergency_steps"], [{"title": "ok", "text": "fine"}])
        self.assertEqual(clean["emergency_open"], "Out")

    def test_shipped_packs_have_complete_emergency_texts(self):
        import themes
        for name in ("techdom", "petdom"):
            with open(os.path.join("packs", name, "pack.json"), encoding="utf-8") as f:
                texts = json.load(f)["ui_texts"]
            clean = themes.clean_ui_texts(texts)
            self.assertEqual(len(clean["emergency_steps"]), 5, name)
            for key in themes.UI_TEXT_KEYS:
                self.assertIn(key, clean, f"{name}: {key}")
