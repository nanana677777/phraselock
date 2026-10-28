import os
import tempfile
import unittest
from unittest import mock

import uninstall


class FakeProc:
    def __init__(self, pid, exe, cmdline):
        self.info = {"pid": pid, "exe": exe, "cmdline": cmdline}


class ClassifyTests(unittest.TestCase):
    EXE = r"C:\Apps\PhraseLock.exe"

    def test_frozen_roles(self):
        self.assertEqual(uninstall.classify({"exe": self.EXE, "cmdline": [self.EXE, "--monitor"]}, self.EXE, True), "app")
        self.assertEqual(uninstall.classify({"exe": self.EXE, "cmdline": [self.EXE, "--watchdog"]}, self.EXE, True), "watchdog")
        self.assertEqual(uninstall.classify({"exe": r"C:\x\PhraseLockWatchdog.exe", "cmdline": []}, self.EXE, True), "watchdog")
        self.assertIsNone(uninstall.classify({"exe": r"C:\Windows\notepad.exe", "cmdline": []}, self.EXE, True))

    def test_source_roles(self):
        self.assertEqual(uninstall.classify({"exe": "python", "cmdline": ["python", "phrase_lock.py", "--monitor"]}, "", False), "app")
        self.assertEqual(uninstall.classify({"exe": "python", "cmdline": ["python", "PhraseLockWatchdog.py"]}, "", False), "watchdog")
        self.assertIsNone(uninstall.classify({"exe": "python", "cmdline": ["python", "other.py"]}, "", False))

    def test_find_skips_own_and_orders_watchdog_first(self):
        procs = [FakeProc(1, self.EXE, [self.EXE]), FakeProc(2, self.EXE, [self.EXE, "--watchdog"]),
                 FakeProc(3, self.EXE, [self.EXE]), FakeProc(4, "x", [])]
        found = uninstall.find_processes(self.EXE, True, own_pids=(3,), process_iter=lambda: procs)
        self.assertEqual([(p["pid"], p["role"]) for p in found], [(2, "watchdog"), (1, "app")])


class FilesTests(unittest.TestCase):
    def test_data_summary_and_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "PhraseLock")
            os.makedirs(os.path.join(data, "packs", "a"))
            for rel in ("config.json", os.path.join("packs", "a", "pack.json")):
                with open(os.path.join(data, rel), "w") as f:
                    f.write("12345")
            self.assertEqual(uninstall.data_summary(data), (2, 10))
            self.assertEqual(uninstall.remove_data(data), [])
            self.assertFalse(os.path.exists(data))
            self.assertEqual(uninstall.data_summary(data), (0, 0))
            self.assertEqual(uninstall.remove_data(data), [])

    def test_remove_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            lnk = os.path.join(tmp, "PhraseLock.lnk")
            self.assertFalse(uninstall.remove_startup(lnk))
            open(lnk, "w").close()
            self.assertTrue(uninstall.remove_startup(lnk))
            self.assertFalse(os.path.exists(lnk))

    def test_exe_delete_only_when_frozen_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "PhraseLock.exe")
            open(exe, "w").close()
            popen = mock.Mock()
            self.assertFalse(uninstall.schedule_exe_delete(exe, False, popen))
            self.assertFalse(uninstall.schedule_exe_delete(os.path.join(tmp, "python"), True, popen))
            popen.assert_not_called()
            self.assertTrue(uninstall.schedule_exe_delete(exe, True, popen))
            self.assertIn(exe, popen.call_args[0][0][-1])

    def test_human_size(self):
        self.assertEqual(uninstall.human_size(512), "512 B")
        self.assertEqual(uninstall.human_size(2048), "2.0 KB")


class RunTests(unittest.TestCase):
    def test_full_run_removes_everything_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "PhraseLock")
            os.makedirs(data)
            open(os.path.join(data, "config.json"), "w").close()
            lnk = os.path.join(tmp, "PhraseLock.lnk")
            open(lnk, "w").close()
            with mock.patch.object(uninstall, "find_processes", return_value=[]) as find:
                report = uninstall.run_uninstall({"startup": True, "data": True}, data, lnk, "x.py", False)
            find.assert_called_once()          # deleting data implies stopping first
            self.assertFalse(os.path.exists(data))
            self.assertFalse(os.path.exists(lnk))
            self.assertTrue(any("Deleted your data" in line for line in report))

    def test_nothing_selected_does_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "PhraseLock")
            os.makedirs(data)
            with mock.patch.object(uninstall, "find_processes") as find:
                self.assertEqual(uninstall.run_uninstall({}, data, "", "x", False), [])
            find.assert_not_called()
            self.assertTrue(os.path.isdir(data))

    def test_confirmation_text(self):
        self.assertEqual(uninstall.confirmation_text({}, True), "")
        text = uninstall.confirmation_text({"data": True, "exe": True}, True)
        self.assertIn("DELETE", text)
        self.assertIn("PhraseLock.exe", text)
        self.assertNotIn("PhraseLock.exe", uninstall.confirmation_text({"data": True, "exe": True}, False))


if __name__ == "__main__":
    unittest.main()
