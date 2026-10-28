"""Tests for the "What's new?" window logic (whatsnew.py, Tk-free parts)."""
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import whatsnew  # noqa: E402
import wizard  # noqa: E402
from config import DEFAULT_CONFIG  # noqa: E402
from version import __version__  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SAMPLE = """# Changelog

Intro text.

## [Unreleased]

### Added
- **Shiny thing.** It does `stuff`, see [docs](http://x.y).
  Second line of the same item.
- Plain item

### Fixed
- A bug

## [1.0.2] - 2026-10-18

### Fixed
- Crash on start

## [1.0.1] - 2026-10-17

### Added
- Tray icon

### Changed
- Nothing much

## [1.0.0] - 2026-10-16

### Added
- First release
"""


class ParseTests(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(whatsnew.parse_version("1.0.2"), (1, 0, 2))
        self.assertEqual(whatsnew.parse_version("v1.2"), (1, 2, 0))
        self.assertEqual(whatsnew.parse_version(" 2 "), (2, 0, 0))
        for bad in ("", None, "Unreleased", "1.x", "1.2.3.4", "abc"):
            self.assertEqual(whatsnew.parse_version(bad), ())
        self.assertLess(whatsnew.parse_version("1.0.2"), whatsnew.parse_version("1.0.10"))

    def test_markdown_is_stripped(self):
        self.assertEqual(whatsnew.plain_text("**Bold** and `code` and [link](http://a.b) and *it*"),
                         "Bold and code and link and it")
        self.assertEqual(whatsnew.plain_text("  many   spaces "), "many spaces")

    def test_sections_groups_and_items(self):
        sections = whatsnew.parse_changelog(SAMPLE)
        self.assertEqual([s["version"] for s in sections], ["Unreleased", "1.0.2", "1.0.1", "1.0.0"])
        self.assertEqual(sections[1]["date"], "2026-10-18")
        unreleased = dict(sections[0]["groups"])
        self.assertEqual(unreleased["Added"][0], "Shiny thing. It does stuff, see docs. Second line of the same item.")
        self.assertEqual(unreleased["Added"][1], "Plain item")
        self.assertEqual(unreleased["Fixed"], ["A bug"])

    def test_junk_input(self):
        for text in ("", None, "no headings here\n- orphan", "## not a version heading"):
            self.assertEqual(whatsnew.parse_changelog(text), [])

    def test_empty_groups_are_dropped(self):
        sections = whatsnew.parse_changelog("## [1.0.0]\n\n### Added\n\n### Fixed\n- x\n")
        self.assertEqual(sections[0]["groups"], [("Fixed", ["x"])])


class EntriesTests(unittest.TestCase):
    def setUp(self):
        self.sections = whatsnew.parse_changelog(SAMPLE)

    def versions(self, last_seen, current):
        return [e["version"] for e in whatsnew.entries_since(self.sections, last_seen, current)]

    def test_unreleased_is_shown_as_the_current_version(self):
        self.assertEqual(self.versions("1.0.1", "1.1.0"), ["1.1.0", "1.0.2"])

    def test_nothing_new_when_up_to_date(self):
        self.assertEqual(self.versions("1.1.0", "1.1.0"), [])
        self.assertEqual(self.versions("1.0.2", "1.0.2"), [])

    def test_unreleased_is_hidden_while_the_version_is_not_bumped(self):
        self.assertEqual(self.versions("1.0.1", "1.0.2"), ["1.0.2"])

    def test_sections_newer_than_the_running_version_are_not_shown(self):
        self.assertEqual(self.versions("1.0.0", "1.0.1"), ["1.0.1"])

    def test_no_last_seen_shows_only_the_newest(self):
        self.assertEqual(self.versions("", "1.1.0"), ["1.1.0"])
        self.assertEqual(self.versions(None, "1.0.2"), ["1.0.2"])

    def test_the_list_is_capped(self):
        text = "\n".join(f"## [1.0.{i}]\n### Added\n- item {i}\n" for i in range(10))
        shown = whatsnew.entries_since(whatsnew.parse_changelog(text), "0.1.0", "1.0.9")
        self.assertEqual(len(shown), whatsnew.MAX_VERSIONS_SHOWN)
        self.assertEqual(shown[0]["version"], "1.0.9")

    def test_newest_first(self):
        shown = self.versions("0.9.0", "1.0.2")
        self.assertEqual(shown, sorted(shown, key=whatsnew.parse_version, reverse=True))


class ShouldShowTests(unittest.TestCase):
    def test_new_version_shows(self):
        self.assertTrue(whatsnew.should_show({"last_seen_version": "1.0.2"}, "1.1.0"))
        self.assertTrue(whatsnew.should_show({}, "1.1.0"))

    def test_same_or_older_does_not(self):
        self.assertFalse(whatsnew.should_show({"last_seen_version": "1.1.0"}, "1.1.0"))
        self.assertFalse(whatsnew.should_show({"last_seen_version": "2.0.0"}, "1.1.0"))

    def test_bad_values_never_crash(self):
        self.assertTrue(whatsnew.should_show({"last_seen_version": "junk"}, "1.1.0"))
        self.assertFalse(whatsnew.should_show({}, "not a version"))

    def test_default_config_has_no_last_seen_version(self):
        self.assertEqual(DEFAULT_CONFIG["last_seen_version"], "")


class FilesTests(unittest.TestCase):
    def test_remember_version_saves(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            new = whatsnew.remember_version({**DEFAULT_CONFIG, "theme": "Matrix"}, "1.2.3", config_path=path)
            self.assertEqual(new["last_seen_version"], "1.2.3")
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["theme"], "Matrix")

    def test_missing_changelog_means_no_window(self):
        self.assertEqual(whatsnew.load_entries("", "1.1.0", path=os.path.join(REPO, "nope.md")), [])

    def test_real_changelog_gives_entries_for_the_current_version(self):
        entries = whatsnew.load_entries("", __version__, path=os.path.join(REPO, "CHANGELOG.md"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["version"], __version__)
        self.assertTrue(entries[0]["groups"])

    def test_version_is_valid_and_not_older_than_the_last_release(self):
        self.assertTrue(whatsnew.parse_version(__version__))
        with open(os.path.join(REPO, "CHANGELOG.md"), encoding="utf-8") as f:
            released = [whatsnew.parse_version(s["version"]) for s in whatsnew.parse_changelog(f.read())
                        if whatsnew.parse_version(s["version"])]
        self.assertGreaterEqual(whatsnew.parse_version(__version__), max(released))

    def test_the_build_ships_the_changelog(self):
        for rel in ("bat.bat", os.path.join(".github", "workflows", "build.yml")):
            with open(os.path.join(REPO, rel), encoding="utf-8") as f:
                self.assertIn('--add-data "CHANGELOG.md;."', f.read(), rel)


class WizardInteropTests(unittest.TestCase):
    def test_a_fresh_install_has_nothing_to_catch_up_on(self):
        new, _ = wizard.apply_choices(dict(DEFAULT_CONFIG), {})
        self.assertEqual(new["last_seen_version"], __version__)
        self.assertFalse(whatsnew.should_show(new))

    def test_skipping_the_wizard_does_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            new = wizard.mark_skipped(dict(DEFAULT_CONFIG), config_path=os.path.join(tmp, "c.json"))
        self.assertFalse(whatsnew.should_show(new))


if __name__ == "__main__":
    unittest.main()
