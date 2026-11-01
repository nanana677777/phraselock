import os
import tempfile
import unittest

import dropfiles as d


class SplitImagesTests(unittest.TestCase):
    def test_images_are_kept_in_order(self):
        images, rejected = d.split_images(["a.PNG", "b.gif", r"C:\x\c.jpeg", "d.webp", "e.bmp", "f.jpg"])
        self.assertEqual(images, ["a.PNG", "b.gif", r"C:\x\c.jpeg", "d.webp", "e.bmp", "f.jpg"])
        self.assertEqual(rejected, [])

    def test_everything_else_is_rejected(self):
        images, rejected = d.split_images(["a.png", "clip.mp4", "p.txt", "s.wav", "noext", "z.zip"])
        self.assertEqual(images, ["a.png"])
        self.assertEqual(rejected, ["clip.mp4", "p.txt", "s.wav", "noext", "z.zip"])

    def test_folder_named_like_an_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "pics.png")
            os.mkdir(folder)
            self.assertEqual(d.split_images([folder]), ([], [folder]))

    def test_empty(self):
        self.assertEqual(d.split_images([]), ([], []))

    def test_hook_is_a_noop_off_windows(self):
        if os.name == "nt":
            self.skipTest("Windows")
        self.assertFalse(d.enable_widget(object(), lambda paths: None))


if __name__ == "__main__":
    unittest.main()
