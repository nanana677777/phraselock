"""Tests for the Settings window widgets (uikit.py). Widget tests need a display and are skipped without one."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tkinter as tk
    import uikit  # noqa: E402
except ImportError:          # pragma: no cover - Python without Tk
    tk = None
    uikit = None


@unittest.skipIf(uikit is None, "tkinter is not available")
class PaletteTests(unittest.TestCase):
    def test_accent_text_is_readable_on_dark_and_light_accents(self):
        self.assertEqual(uikit.apply_palette("#ffd54f")["ACCENT_TEXT"], "#0b0d13")      # light accent -> dark text
        self.assertEqual(uikit.apply_palette("#0097a7")["ACCENT_TEXT"], "#ffffff")      # darker accent -> white text
        self.assertEqual(uikit.apply_palette("#eeeeee")["ACCENT_TEXT"], "#0b0d13")      # the Blackout theme

    def test_bad_accent_falls_back(self):
        for bad in (None, "", "red", "#12", 5):
            self.assertEqual(uikit.apply_palette(bad)["ACCENT"], "#ff1744")

    def test_every_colour_is_a_hex_value(self):
        for key, value in uikit.apply_palette("#0097a7").items():
            self.assertRegex(value, r"^#[0-9a-fA-F]{6}$", key)

    def test_every_theme_gives_a_palette(self):
        import themes
        for name in themes.THEMES:
            main, second, _third = themes.theme_colors(name)
            self.assertEqual(uikit.apply_palette(main, second)["ACCENT"], main)

    def test_mix(self):
        self.assertEqual(uikit._mix("#000000", "#ffffff", 0.5), "#808080")
        self.assertEqual(uikit._mix("#102030", "#102030", 0.7), "#102030")


def make_root():
    if tk is None:
        raise unittest.SkipTest("tkinter is not available")
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise unittest.SkipTest(f"no display: {exc}")
    root.withdraw()
    uikit.apply_palette("#0097a7", "#00e5ff")
    return root


class WidgetTestCase(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(self.root.destroy)


class SwitchTests(WidgetTestCase):
    def test_click_toggles_the_variable_and_runs_the_command(self):
        var = tk.BooleanVar(self.root, value=False)
        calls = []
        switch = uikit.Switch(self.root, text="x", variable=var, command=lambda: calls.append(var.get()))
        switch._toggle()
        self.assertTrue(var.get())
        switch._toggle()
        self.assertFalse(var.get())
        self.assertEqual(calls, [True, False])

    def test_follows_changes_made_elsewhere(self):
        var = tk.BooleanVar(self.root, value=False)
        switch = uikit.Switch(self.root, text="x", variable=var)
        var.set(True)
        self.assertTrue(switch._on())

    def test_disabled_switch_does_not_toggle(self):
        var = tk.BooleanVar(self.root, value=True)
        switch = uikit.Switch(self.root, text="x", variable=var, state="disabled")
        switch._toggle()
        self.assertTrue(var.get())
        switch.configure(state="normal")
        switch._toggle()
        self.assertFalse(var.get())

    def test_accepts_the_checkbutton_arguments_settings_uses(self):
        uikit.Switch(self.root, text="x", variable=tk.BooleanVar(self.root), font=("Arial", 9))

    def test_text_can_be_changed(self):
        switch = uikit.Switch(self.root, text="a", variable=tk.BooleanVar(self.root))
        switch.configure(text="b")
        self.assertEqual(switch._label.cget("text"), "b")


class DropdownTests(WidgetTestCase):
    def test_values_and_variable(self):
        var = tk.StringVar(self.root, value="easy")
        box = uikit.Dropdown(self.root, var, "all", "easy", "hard")
        self.assertEqual(list(box["values"]), ["all", "easy", "hard"])
        self.assertEqual(box.get(), "easy")
        var.set("hard")
        self.assertEqual(box.get(), "hard")

    def test_values_can_be_replaced(self):
        var = tk.StringVar(self.root)
        box = uikit.Dropdown(self.root, var, "a")
        box["values"] = ["a", "b"]
        self.assertEqual(list(box["values"]), ["a", "b"])


class RadioCardTests(WidgetTestCase):
    def test_click_selects_its_value(self):
        var = tk.StringVar(self.root, value="a")
        card = uikit.RadioCard(self.root, "B", "detail", var, "b")
        card._choose()
        self.assertEqual(var.get(), "b")

    def test_selected_card_is_highlighted(self):
        var = tk.StringVar(self.root, value="a")
        card = uikit.RadioCard(self.root, "A", "", var, "a")
        self.assertEqual(str(card.cget("highlightbackground")), uikit.P["ACCENT"])
        var.set("z")
        self.assertEqual(str(card.cget("highlightbackground")), uikit.P["BORDER"])


class SideNavTests(WidgetTestCase):
    def setUp(self):
        super().setUp()
        self.side = tk.Frame(self.root)
        self.nav = uikit.SideNav(self.root, self.side)
        self.nav.pack()
        self.root.deiconify()
        self.root.update()
        self.pages = {n: tk.Frame(self.nav) for n in ("a", "b", "c")}
        for name, page in self.pages.items():
            self.nav.add(page, text=f"  {name.upper()}  ")

    def test_first_page_is_selected_and_titles_are_trimmed(self):
        self.assertEqual(self.nav.select(), str(self.pages["a"]))
        self.assertEqual(self.nav.title_of(), "A")
        self.assertEqual(self.nav.tabs(), [str(p) for p in self.pages.values()])

    def test_select_by_widget_or_path_and_event(self):
        events = []
        self.nav.bind("<<NotebookTabChanged>>", lambda _e: events.append(self.nav.select()))
        self.nav.select(self.pages["b"])
        self.nav.update()
        self.assertEqual(self.nav.select(), str(self.pages["b"]))
        self.nav.select(str(self.pages["c"]))
        self.nav.update()
        self.assertEqual(events, [str(self.pages["b"]), str(self.pages["c"])])

    def test_insert_moves_a_page_first(self):
        self.nav.insert(0, self.pages["c"])
        self.assertEqual(self.nav.tabs()[0], str(self.pages["c"]))

    def test_hide_and_show(self):
        self.nav.hide(self.pages["b"])
        self.assertEqual(len(self.side.winfo_children()), 2)
        with self.assertRaises(tk.TclError):
            self.nav.select(self.pages["b"])
        self.nav.add(self.pages["b"])
        self.assertEqual(len(self.side.winfo_children()), 3)
        self.assertEqual(self.nav.title_of(self.pages["b"]), "B")      # keeps its title
        self.nav.select(self.pages["b"])

    def test_hiding_the_current_page_selects_another(self):
        self.nav.hide(self.pages["a"])
        self.assertEqual(self.nav.select(), str(self.pages["b"]))

    def test_unknown_page_raises(self):
        with self.assertRaises(tk.TclError):
            self.nav.select(tk.Frame(self.root))


if __name__ == "__main__":
    unittest.main()
