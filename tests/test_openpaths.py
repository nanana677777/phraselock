import os
import tempfile
import unittest
from unittest import mock

import openpaths as op


class OpenPathsTests(unittest.TestCase):
    def test_folder_is_created_and_opened(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "PhraseLock")
            opener = mock.Mock()
            self.assertEqual(op.open_folder(target, opener), (True, ""))
            self.assertTrue(os.path.isdir(target))
            opener.assert_called_once_with(target)

    def test_folder_open_failure_is_reported(self):
        ok, message = op.open_folder(tempfile.gettempdir(), mock.Mock(side_effect=OSError("denied")))
        self.assertFalse(ok)
        self.assertIn("denied", message)

    def test_missing_log_is_explained_not_opened(self):
        opener = mock.Mock()
        ok, message = op.open_file(os.path.join(tempfile.gettempdir(), "does-not-exist.log"), opener)
        self.assertFalse(ok)
        self.assertIn("no log", message)
        opener.assert_not_called()

    def test_existing_log_is_opened(self):
        with tempfile.NamedTemporaryFile(suffix=".log") as f:
            opener = mock.Mock()
            self.assertEqual(op.open_file(f.name, opener), (True, ""))
            opener.assert_called_once_with(f.name)


if __name__ == "__main__":
    unittest.main()
