import unittest
from unittest import mock

import exit_app
import stats


class ExitAppTests(unittest.TestCase):
    def test_parse_pid(self):
        self.assertEqual(exit_app.parse_pid(["x", "--exit-monitor", "1234"]), 1234)
        self.assertIsNone(exit_app.parse_pid(["x", "--exit-monitor"]))
        self.assertIsNone(exit_app.parse_pid(["x", "--exit-monitor", "abc"]))
        self.assertIsNone(exit_app.parse_pid(["x"]))

    def test_needs_password_only_when_set(self):
        self.assertFalse(exit_app.needs_password({}))
        self.assertTrue(exit_app.needs_password(stats.set_emergency_password("secret1")))

    def test_password_check(self):
        cfg = stats.set_emergency_password("secret1")
        self.assertTrue(exit_app.check_password(cfg, lambda n: "secret1"))
        answers = iter(["no", "nope", "secret1"])
        self.assertTrue(exit_app.check_password(cfg, lambda n: next(answers)))
        wrong = iter(["a", "b", "c", "secret1"])
        self.assertFalse(exit_app.check_password(cfg, lambda n: next(wrong)))     # 3 tries only
        self.assertFalse(exit_app.check_password(cfg, lambda n: None))             # cancelled

    def test_stop_everything_targets_watchdog_then_monitor_only(self):
        found = [{"pid": 5, "role": "watchdog"}, {"pid": 6, "role": "app"}]
        with mock.patch("uninstall.find_processes", return_value=found) as find, \
                mock.patch("uninstall.stop_processes", return_value=([5, 77], [])) as stop:
            result = exit_app.stop_everything(77, "PhraseLock.exe", True, own_pid=99)
        self.assertEqual(result, ([5, 77], []))
        find.assert_called_once_with("PhraseLock.exe", True, own_pids=(99,))
        self.assertEqual(stop.call_args[0][0], [{"pid": 5, "role": "watchdog"}, {"pid": 77, "role": "app"}])

    def test_never_stops_itself(self):
        with mock.patch("uninstall.find_processes", return_value=[]), \
                mock.patch("uninstall.stop_processes", return_value=([], [])) as stop:
            exit_app.stop_everything(99, "x", False, own_pid=99)
        self.assertEqual(stop.call_args[0][0], [])


if __name__ == "__main__":
    unittest.main()
