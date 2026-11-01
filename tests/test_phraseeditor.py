import json
import os
import tempfile
import unittest

import phraseeditor as pe
from phrases import load_external_phrases


class ParseTests(unittest.TestCase):
    def test_plain_lines_and_comments(self):
        items, problems = pe.parse_lines("One\n\n# comment\n  Two  \n")
        self.assertEqual([i["text"] for i in items], ["One", "Two"])
        self.assertEqual(problems, [])
        self.assertTrue(all(i["difficulty"] == "normal" and i["category"] == "General" for i in items))

    def test_second_column_is_difficulty_or_category(self):
        items, _ = pe.parse_lines("A | hard\nB | Obedience\nC | Rules | extreme\nD\tTabbed\teasy")
        self.assertEqual([(i["category"], i["difficulty"]) for i in items],
                         [("General", "hard"), ("Obedience", "normal"), ("Rules", "extreme"), ("Tabbed", "easy")])

    def test_defaults_are_used(self):
        items, _ = pe.parse_lines("A\nB | hard", "Mine", "easy")
        self.assertEqual([(i["category"], i["difficulty"]) for i in items], [("Mine", "easy"), ("Mine", "hard")])

    def test_unknown_difficulty_reported(self):
        items, problems = pe.parse_lines("A | Cat | impossible")
        self.assertEqual(items[0]["difficulty"], "normal")
        self.assertIn("impossible", problems[0])

    def test_header_row_skipped(self):
        items, _ = pe.parse_lines("phrase | category | difficulty\nReal | x | hard")
        self.assertEqual([i["text"] for i in items], ["Real"])

    def test_check_text(self):
        self.assertEqual(pe.check_text("fine"), "")
        self.assertTrue(pe.check_text(""))
        self.assertTrue(pe.check_text("# no"))
        self.assertTrue(pe.check_text("two\nlines"))


class CleanTests(unittest.TestCase):
    def test_duplicates_and_empty_removed(self):
        items = [pe.make_item("A"), pe.make_item("A", "x", "hard"), {"text": "  "}, pe.make_item("B")]
        cleaned, removed = pe.clean_items(items)
        self.assertEqual([i["text"] for i in cleaned], ["A", "B"])
        self.assertEqual(removed, 2)

    def test_warnings_and_summary(self):
        items = [pe.make_item("x" * 200), pe.make_item("ok", difficulty="hard")]
        self.assertIn("longer than", pe.warnings(items)[0])
        self.assertEqual(pe.summary(items), "2 phrase(s) (1 normal, 1 hard)")

    def test_safe_filename(self):
        self.assertEqual(pe.safe_filename("My list: v2!"), "My-list-v2.csv")
        self.assertEqual(pe.safe_filename("///", ".json"), "my-phrases.json")


class SaveRoundTripTests(unittest.TestCase):
    ITEMS = [pe.make_item("Hello, world", "Gree,ting", "easy"), pe.make_item("Zoë says \"hi\"", "Quotes", "extreme"),
             pe.make_item("Plain", "General", "normal")]

    def roundtrip(self, name):
        with tempfile.TemporaryDirectory() as tmp:
            path = pe.save_phrases(os.path.join(tmp, name), self.ITEMS)
            return load_external_phrases(path)

    def test_csv_roundtrip_keeps_everything(self):
        self.assertEqual(self.roundtrip("a.csv"), self.ITEMS)

    def test_json_roundtrip_keeps_everything(self):
        self.assertEqual(self.roundtrip("a.json"), self.ITEMS)

    def test_txt_keeps_only_text(self):
        loaded = self.roundtrip("a.txt")
        self.assertEqual([i["text"] for i in loaded], [i["text"] for i in self.ITEMS])

    def test_unknown_extension_becomes_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pe.save_phrases(os.path.join(tmp, "list"), self.ITEMS)
            self.assertTrue(path.endswith(".csv"))
            self.assertTrue(os.path.isfile(path))

    def test_unsavable_phrases_are_left_out_and_empty_list_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pe.save_phrases(os.path.join(tmp, "a.csv"), [pe.make_item("# hidden"), pe.make_item("kept")])
            self.assertEqual([i["text"] for i in load_external_phrases(path)], ["kept"])
            with self.assertRaises(ValueError):
                pe.save_phrases(os.path.join(tmp, "b.csv"), [])

    def test_no_temp_file_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            pe.save_phrases(os.path.join(tmp, "a.json"), self.ITEMS)
            self.assertEqual(os.listdir(tmp), ["a.json"])


if __name__ == "__main__":
    unittest.main()
