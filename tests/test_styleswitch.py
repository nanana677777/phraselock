import json
import os
import tempfile
import unittest
from unittest import mock

import packs
import styleswitch
import tray


class StyleSwitchTests(unittest.TestCase):
    def test_parse_pack_id(self):
        self.assertEqual(styleswitch.parse_pack_id(["x", "--switch-style", "techdom"]), "techdom")
        self.assertIsNone(styleswitch.parse_pack_id(["x", "--switch-style", "../evil"]))
        self.assertIsNone(styleswitch.parse_pack_id(["x", "--switch-style"]))
        self.assertIsNone(styleswitch.parse_pack_id(["x"]))

    def test_switch_applies_pack_without_protections_and_saves(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            cfg = {"strict_mode": False, "difficulty": "all", "emergency_password_hash": "x"}
            with mock.patch.object(packs, "UNDO_PATH", os.path.join(tmp, "undo.json")), \
                    mock.patch.object(packs, "install_pack_assets", return_value=os.path.join(tmp, "pk")):
                ok, message = styleswitch.switch("petdom", cfg, cfg_path)
            self.assertTrue(ok, message)
            with open(cfg_path, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["theme"], "PetDom")
            self.assertFalse(saved["strict_mode"])                      # protections stay as they were
            self.assertEqual(saved["emergency_password_hash"], "x")     # never touched

    def test_unknown_pack_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok, message = styleswitch.switch("nope-pack", {}, os.path.join(tmp, "c.json"))
            self.assertFalse(ok)
            self.assertTrue(message)
            self.assertFalse(os.path.exists(os.path.join(tmp, "c.json")))


class TrayMenuTests(unittest.TestCase):
    def test_entries_mark_the_current_style(self):
        with mock.patch.object(packs, "last_applied_pack", return_value="petdom"):
            entries = tray.style_menu_entries()
        ids = {pid: current for pid, _name, current in entries}
        self.assertTrue(ids["petdom"])
        self.assertFalse(ids["techdom"])

    def test_checker_takes_one_argument(self):
        self.assertTrue(tray._checker(True)(object()))
        self.assertFalse(tray._checker(False)(object()))


if __name__ == "__main__":
    unittest.main()
