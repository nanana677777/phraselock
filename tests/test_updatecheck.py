import io
import json
import unittest
from unittest import mock

import updatecheck as u


class VersionTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(u.parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(u.parse_version("1.2"), (1, 2, 0))
        self.assertEqual(u.parse_version("PhraseLock 2.0.1-beta"), (2, 0, 1))
        self.assertIsNone(u.parse_version("latest"))
        self.assertIsNone(u.parse_version(None))

    def test_is_newer(self):
        self.assertTrue(u.is_newer("1.10.0", "1.9.9"))      # numbers, not text
        self.assertTrue(u.is_newer("v1.1.1", "1.1.0"))
        self.assertFalse(u.is_newer("1.1.0", "1.1.0"))
        self.assertFalse(u.is_newer("1.0.9", "1.1.0"))
        self.assertFalse(u.is_newer("junk", "1.1.0"))


class ReleaseTests(unittest.TestCase):
    GOOD = {"tag_name": "v1.2.0", "name": "Big one", "html_url": "https://github.com/a/b/releases/tag/v1.2.0"}

    def test_parse_release(self):
        self.assertEqual(u.parse_release(self.GOOD),
                         {"version": "1.2.0", "url": self.GOOD["html_url"], "name": "Big one"})

    def test_rejects_drafts_prereleases_and_junk(self):
        self.assertIsNone(u.parse_release({**self.GOOD, "draft": True}))
        self.assertIsNone(u.parse_release({**self.GOOD, "prerelease": True}))
        self.assertIsNone(u.parse_release({"tag_name": "nightly"}))
        self.assertIsNone(u.parse_release([]))

    def test_foreign_url_replaced(self):
        release = u.parse_release({**self.GOOD, "html_url": "http://evil.example/x"})
        self.assertEqual(release["url"], u.RELEASES_URL)

    def test_fetch_latest_reads_json(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(self.GOOD).encode()
        self.assertEqual(u.fetch_latest(opener=lambda *a, **k: response)["version"], "1.2.0")


class CheckTests(unittest.TestCase):
    def test_statuses(self):
        newer = u.check("1.1.0", fetch=lambda: {"version": "1.2.0", "url": "https://github.com/x", "name": ""})
        self.assertEqual((newer["status"], newer["latest"]), ("newer", "1.2.0"))
        same = u.check("1.2.0", fetch=lambda: {"version": "1.2.0", "url": "https://github.com/x", "name": ""})
        self.assertEqual(same["status"], "current")

    def test_network_error_is_a_result(self):
        def boom():
            raise OSError("offline")
        result = u.check("1.1.0", fetch=boom)
        self.assertEqual(result["status"], "error")
        self.assertIn("offline", u.describe(result))

    def test_due(self):
        self.assertTrue(u.due({}, today="2026-10-28"))
        self.assertFalse(u.due({"last_update_check": "2026-10-28"}, today="2026-10-28"))
        self.assertTrue(u.due({"last_update_check": "2026-10-27"}, today="2026-10-28"))
        self.assertFalse(u.due({"check_updates": False}, today="2026-10-28"))

    def test_background_calls_back(self):
        got = []
        thread = u.check_in_background(got.append, "1.1.0",
                                       fetch=lambda: {"version": "1.1.0", "url": "https://github.com/x", "name": ""})
        thread.join(2)
        self.assertEqual(got[0]["status"], "current")


if __name__ == "__main__":
    unittest.main()
