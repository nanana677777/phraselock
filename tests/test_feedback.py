import os
import unittest
import urllib.parse
from unittest import mock

import feedback as fb


class FeedbackTests(unittest.TestCase):
    def test_url_targets_the_feedback_form_with_the_version(self):
        url = fb.feedback_url("2.0.0")
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "https://github.com/nanana677777/phraselock/issues/new")
        self.assertEqual(query["template"], ["feedback.yml"])
        self.assertEqual(query["version"], ["v2.0.0"])
        self.assertEqual(query["title"], ["[Feedback] "])

    def test_version_prefix_is_not_doubled(self):
        self.assertIn("version=v1.2.3", fb.feedback_url("v1.2.3"))

    def test_template_file_exists_and_declares_the_version_field(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            ".github", "ISSUE_TEMPLATE", fb.TEMPLATE)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("id: version", text)

    def test_open_reports_success_and_failure(self):
        ok, url = fb.open_feedback(opener=mock.Mock(return_value=True), version="2.0.0")
        self.assertTrue(ok)
        self.assertTrue(url.startswith("https://github.com/"))
        self.assertFalse(fb.open_feedback(opener=mock.Mock(return_value=False))[0])
        self.assertFalse(fb.open_feedback(opener=mock.Mock(side_effect=OSError()))[0])


if __name__ == "__main__":
    unittest.main()
