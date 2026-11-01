"""Tests for the background thumbnail gallery. The widget test needs a display and is skipped without one."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import gallery as g  # noqa: E402
except ImportError:          # pragma: no cover - Python without Tk
    g = None


@unittest.skipIf(g is None, "tkinter is not available")
class HelperTests(unittest.TestCase):
    def test_item_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            png, gif = os.path.join(tmp, "a.png"), os.path.join(tmp, "b.GIF")
            for path in (png, gif):
                open(path, "wb").close()
            self.assertEqual(g.item_kind(png), "image")
            self.assertEqual(g.item_kind(gif), "gif")
            self.assertEqual(g.item_kind(os.path.join(tmp, "gone.png")), "missing")
        self.assertEqual(g.item_kind("https://x.example/a.gif"), "url")
        self.assertEqual(g.item_kind("HTTP://x.example/a.png"), "url")

    def test_columns_always_at_least_one(self):
        self.assertEqual(g.columns(0), 1)
        self.assertEqual(g.columns(50), 1)
        self.assertEqual(g.columns(g.TILE_W * 3 + g.GAP * 2), 3)
        self.assertGreater(g.columns(900), g.columns(300))

    def test_caption(self):
        self.assertEqual(g.caption("C:/pics/short.png"), "short.png")
        self.assertEqual(len(g.caption("a" * 80 + ".png")), g.CAPTION_CHARS)
        self.assertEqual(g.caption("https://x.example/img/cool.gif"), "cool.gif")


try:
    import tkinter as tk
    if g is None:
        raise ImportError
    _root = tk.Tk()
    _root.withdraw()
    HAVE_DISPLAY = True
except Exception:            # no display / no Tk
    tk = None
    HAVE_DISPLAY = False


@unittest.skipUnless(HAVE_DISPLAY, "needs a display")
class WidgetTests(unittest.TestCase):
    def test_tiles_and_remove(self):
        import uikit
        removed = []
        widget = g.ThumbGallery(_root, removed.append, uikit.apply_palette("#ff1744"))
        widget.pack()
        widget.set_items(["a.png", "https://x.example/b.gif"])
        _root.update()
        self.assertEqual(len(widget._tiles), 2)
        buttons = [w for w in widget._tiles[1].winfo_children() if isinstance(w, tk.Button)]
        buttons[0].invoke()
        self.assertEqual(removed, ["https://x.example/b.gif"])
        widget.set_items([])
        self.assertEqual(widget._tiles, [])


if __name__ == "__main__":
    unittest.main()
