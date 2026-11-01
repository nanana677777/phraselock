import json
import os
import tempfile
import unittest

import crashguard as g


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = os.path.join(self.tmp.name, "crash_guard.json")
        self.config = os.path.join(self.tmp.name, "config.json")

    def test_trips_at_the_limit_not_before(self):
        results = [g.record("monitor_start", now=1000 + i, state_path=self.state) for i in range(g.LIMIT)]
        self.assertEqual(results, [False] * (g.LIMIT - 1) + [True])

    def test_slow_events_never_trip(self):
        for i in range(20):
            self.assertFalse(g.record("monitor_start", now=i * (g.WINDOW_SECONDS + 1), state_path=self.state))

    def test_kinds_are_counted_separately(self):
        for i in range(g.LIMIT - 1):
            g.record("monitor_start", now=1000 + i, state_path=self.state)
        self.assertFalse(g.record("watchdog_restart", now=1010, state_path=self.state))

    def test_clear_history(self):
        for i in range(g.LIMIT - 1):
            g.record("monitor_start", now=1000 + i, state_path=self.state)
        g.clear_history("monitor_start", state_path=self.state)
        self.assertFalse(g.record("monitor_start", now=1010, state_path=self.state))

    def test_recent_ignores_junk(self):
        self.assertEqual(g.recent([1000, "x", None, True, 5, 9_999_999_999], now=1010), [1000.0])
        self.assertEqual(g.recent("nope", now=1), [])

    def test_corrupt_state_is_harmless(self):
        with open(self.state, "w") as f:
            f.write("{not json")
        self.assertFalse(g.record("monitor_start", now=1, state_path=self.state))
        self.assertIsNone(g.tripped(self.state))


class TripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = os.path.join(self.tmp.name, "crash_guard.json")
        self.config = os.path.join(self.tmp.name, "config.json")

    def write_config(self, **values):
        with open(self.config, "w") as f:
            json.dump({"enabled": True, "auto_protection": True, "difficulty": "hard", **values}, f)

    def read_config(self):
        with open(self.config) as f:
            return json.load(f)

    def test_trip_disables_protection_and_keeps_other_settings(self):
        self.write_config()
        note = g.trip("monitor_start", now=1234, state_path=self.state, config_path=self.config)
        cfg = self.read_config()
        self.assertFalse(cfg["enabled"])
        self.assertFalse(cfg["auto_protection"])
        self.assertEqual(cfg["difficulty"], "hard")
        self.assertEqual(g.tripped(self.state)["tripped_at"], 1234)
        self.assertEqual(note["kind"], "monitor_start")

    def test_unreadable_config_is_not_overwritten(self):
        with open(self.config, "w") as f:
            f.write("{broken")
        self.assertFalse(g.disable_protection(self.config))
        with open(self.config) as f:
            self.assertEqual(f.read(), "{broken")

    def test_missing_config_gets_disabled_defaults(self):
        self.assertTrue(g.disable_protection(self.config))
        self.assertEqual((self.read_config()["enabled"], self.read_config()["auto_protection"]), (False, False))

    def test_trip_clears_history_and_reset_clears_note(self):
        self.write_config()
        for i in range(g.LIMIT):
            g.record("monitor_start", now=1000 + i, state_path=self.state)
        g.trip("watchdog_restart", now=1100, state_path=self.state, config_path=self.config)
        self.assertFalse(g.record("monitor_start", now=1101, state_path=self.state))   # fresh start after a trip
        g.reset(self.state)
        self.assertIsNone(g.tripped(self.state))

    def test_describe_mentions_what_happened(self):
        self.assertIn("restart", g.describe({"tripped_at": 1000, "kind": "watchdog_restart"}))
        self.assertIn("start", g.describe({"tripped_at": 1000, "kind": "monitor_start"}))


class IntegrationTests(unittest.TestCase):
    def test_watchdog_loop_trips_after_repeated_restarts(self):
        """Simulates the watchdog: the monitor never stays up, so the guard must stop the restarts."""
        with tempfile.TemporaryDirectory() as tmp:
            state = os.path.join(tmp, "s.json")
            restarts = 0
            for i in range(50):
                if g.record("watchdog_restart", now=2000 + i * 5, state_path=state):
                    break
                restarts += 1
            self.assertEqual(restarts, g.LIMIT - 1)


if __name__ == "__main__":
    unittest.main()
