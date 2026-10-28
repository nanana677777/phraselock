"""A small set of modern-looking widgets for the Settings window.

Plain Tk/ttk only (no extra dependency): toggle switches, flat dropdowns, a left
navigation bar and a colour palette that follows the active theme's accent colour.
``apply_palette`` must be called once before any widget is created.
"""

import tkinter as tk
from tkinter import ttk

UI_FONT = "Segoe UI"
SYMBOL_FONT = "Segoe UI Symbol"

P = {}          # the active palette, filled by apply_palette()


def _luminance(colour):
    colour = colour.lstrip("#")
    if len(colour) != 6:
        return 0.0
    r, g, b = (int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mix(a, b, t):
    """Blend colour *a* towards *b* by *t* (0..1)."""
    a, b = a.lstrip("#"), b.lstrip("#")
    out = [round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(out)


def apply_palette(accent, accent2=None):
    """Fill the palette. *accent* is the active theme's main colour."""
    if not (isinstance(accent, str) and len(accent) == 7 and accent.startswith("#")):
        accent = "#ff1744"
    P.clear()
    P.update(
        BG="#0e1016", SIDEBAR="#0a0c11", CARD="#151822", CARD_ALT="#1c2030", INPUT="#0b0d13",
        BORDER="#262b3a", HOVER="#1a1e2b", TEXT="#eceef4", MUTED="#8a90a4",
        ACCENT=accent, ACCENT2=accent2 or accent,
        ACCENT_TEXT="#0b0d13" if _luminance(accent) > 0.55 else "#ffffff",
        ACCENT_SOFT=_mix("#0e1016", accent, 0.16),
        DANGER="#ff5470", BAD_BG="#2b1118", OK="#2ee59d", WARN="#ffb86b",
        OFF_TRACK="#2c3244",
    )
    return P


def style_ttk(root):
    """Scrollbars and dropdowns in the palette."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    # A thin scrollbar without arrows.
    style.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {
        "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})], "sticky": "ns"})])
    style.configure("Vertical.TScrollbar", background=P["OFF_TRACK"], troughcolor=P["BG"],
                    bordercolor=P["BG"], lightcolor=P["OFF_TRACK"], darkcolor=P["OFF_TRACK"], width=9)
    style.map("Vertical.TScrollbar", background=[("active", P["ACCENT"]), ("pressed", P["ACCENT"])])
    style.configure("Modern.TCombobox", fieldbackground=P["INPUT"], background=P["CARD_ALT"],
                    foreground=P["TEXT"], arrowcolor=P["MUTED"], bordercolor=P["BORDER"],
                    lightcolor=P["BORDER"], darkcolor=P["BORDER"], padding=(8, 5), relief="flat")
    style.map("Modern.TCombobox",
              fieldbackground=[("readonly", P["INPUT"]), ("disabled", P["INPUT"])],
              foreground=[("readonly", P["TEXT"]), ("disabled", P["MUTED"])],
              selectbackground=[("readonly", P["INPUT"])], selectforeground=[("readonly", P["TEXT"])],
              bordercolor=[("focus", P["ACCENT"])], lightcolor=[("focus", P["ACCENT"])],
              darkcolor=[("focus", P["ACCENT"])], arrowcolor=[("active", P["ACCENT"])])
    root.option_add("*TCombobox*Listbox.background", P["CARD"])
    root.option_add("*TCombobox*Listbox.foreground", P["TEXT"])
    root.option_add("*TCombobox*Listbox.selectBackground", P["ACCENT"])
    root.option_add("*TCombobox*Listbox.selectForeground", P["ACCENT_TEXT"])
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.font", f"{{{UI_FONT}}} 10")
    return style


# ---------------------------------------------------------------------------
# dropdown
# ---------------------------------------------------------------------------

def Dropdown(master, variable, *values, width=None):
    """Flat read-only dropdown bound to *variable* (a drop-in for tk.OptionMenu)."""
    values = [str(v) for v in values]
    box = ttk.Combobox(master, textvariable=variable, values=values, state="readonly",
                       width=width or max(12, max((len(v) for v in values), default=0) + 3),
                       style="Modern.TCombobox", font=(UI_FONT, 10))
    # The wheel must scroll the page, not silently change the setting under the cursor.
    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        box.bind(sequence, lambda _e: "break")
    return box


# ---------------------------------------------------------------------------
# switch
# ---------------------------------------------------------------------------

class Switch(tk.Frame):
    """A toggle switch with a label; a drop-in for tk.Checkbutton (text, variable, command)."""

    W, H = 38, 20

    def __init__(self, master, text="", variable=None, command=None, font=None, wraplength=560,
                 state="normal", fg=None, **_ignored):
        super().__init__(master, bg=master.cget("bg") if "bg" in master.keys() else P["BG"])
        self._bg = self.cget("bg")
        self._variable = variable
        self._command = command
        self._state = state
        self._canvas = tk.Canvas(self, width=self.W, height=self.H, bg=self._bg, highlightthickness=0, bd=0,
                                 cursor="hand2", takefocus=1)
        self._canvas.pack(side="left", pady=4)
        self._label = tk.Label(self, text=text, bg=self._bg, fg=fg or P["TEXT"], font=font or (UI_FONT, 10),
                               wraplength=wraplength, justify="left", cursor="hand2")
        self._label.pack(side="left", padx=(10, 0))
        for widget in (self._canvas, self._label):
            widget.bind("<Button-1>", self._toggle)
        self._canvas.bind("<space>", self._toggle)
        self._canvas.bind("<Return>", self._toggle)
        self._canvas.bind("<FocusIn>", lambda _e: self._canvas.configure(highlightthickness=1,
                                                                        highlightbackground=P["ACCENT"]))
        self._canvas.bind("<FocusOut>", lambda _e: self._canvas.configure(highlightthickness=0))
        if variable is not None:
            variable.trace_add("write", lambda *_a: self._draw())
        self._draw()

    def _on(self):
        try:
            return bool(self._variable.get()) if self._variable is not None else False
        except tk.TclError:
            return False

    def _draw(self):
        c, w, h = self._canvas, self.W, self.H
        c.delete("all")
        on = self._on()
        enabled = self._state != "disabled"
        track = (P["ACCENT"] if on else P["OFF_TRACK"]) if enabled else P["BORDER"]
        r = h / 2
        c.create_oval(0, 0, h, h, fill=track, outline=track)
        c.create_oval(w - h, 0, w, h, fill=track, outline=track)
        c.create_rectangle(r, 0, w - r, h, fill=track, outline=track)
        knob_x = (w - h + 3) if on else 3
        knob = (P["ACCENT_TEXT"] if on else P["MUTED"]) if enabled else P["MUTED"]
        c.create_oval(knob_x, 3, knob_x + h - 6, h - 3, fill=knob, outline=knob)
        self._label.configure(fg=P["TEXT"] if enabled else P["MUTED"])

    def _toggle(self, _event=None):
        if self._state == "disabled" or self._variable is None:
            return "break"
        self._variable.set(not self._on())
        if self._command:
            self._command()
        return "break"

    def configure(self, cnf=None, **kw):
        cnf = {**(cnf or {}), **kw}
        if "state" in cnf:
            self._state = cnf.pop("state")
            self._draw()
        if "text" in cnf:
            self._label.configure(text=cnf.pop("text"))
        if cnf:
            super().configure(**cnf)

    config = configure


# ---------------------------------------------------------------------------
# side navigation
# ---------------------------------------------------------------------------

class SideNav(tk.Frame):
    """Pages with a navigation list on the side (the ttk.Notebook methods Settings uses).

    The widget itself is the page area: pages are created with it as their master and
    added with ``add``. Navigation rows are drawn in *sidebar*.
    """

    def __init__(self, master, sidebar):
        super().__init__(master, bg=P["BG"])
        self._sidebar = sidebar
        self._items = []          # {"widget", "text", "icon", "hidden"}
        self._current = None
        self._rows = []

    # -- ttk.Notebook-style API -------------------------------------------
    def add(self, child, text=None, icon=None, **_ignored):
        item = self._find(child)
        if item is None:
            item = {"widget": child, "text": (text or "").strip(), "icon": icon or "", "hidden": False}
            self._items.append(item)
        else:
            item["hidden"] = False
            if text:
                item["text"] = text.strip()
        self._rebuild()
        if self._current is None:
            self.select(child)

    def insert(self, index, child):
        item = self._find(child)
        if item is None:
            raise tk.TclError("unknown page")
        self._items.remove(item)
        self._items.insert(max(0, int(index)), item)
        self._rebuild()

    def hide(self, child):
        item = self._find(child)
        if item is None:
            return
        item["hidden"] = True
        if self._current is item["widget"]:
            visible = [i for i in self._items if not i["hidden"]]
            if visible:
                self.select(visible[0]["widget"])
        self._rebuild()

    def tabs(self):
        return [str(i["widget"]) for i in self._items]

    def select(self, child=None):
        if child is None:
            return str(self._current) if self._current is not None else ""
        item = self._find(child)
        if item is None:
            raise tk.TclError("unknown page")
        if item["hidden"]:
            raise tk.TclError("page is hidden")
        for other in self._items:
            if other is not item:
                other["widget"].place_forget()
        item["widget"].place(x=0, y=0, relwidth=1, relheight=1)
        item["widget"].lift()
        changed = self._current is not item["widget"]
        self._current = item["widget"]
        self._restyle()
        if changed:
            self.event_generate("<<NotebookTabChanged>>")

    def title_of(self, child=None):
        item = self._find(child if child is not None else self._current)
        return item["text"] if item else ""

    # -- internals --------------------------------------------------------
    def _find(self, child):
        for item in self._items:
            if item["widget"] is child or str(item["widget"]) == str(child):
                return item
        return None

    def _rebuild(self):
        for row in self._rows:
            row["frame"].destroy()
        self._rows = []
        for item in self._items:
            if item["hidden"]:
                continue
            frame = tk.Frame(self._sidebar, bg=P["SIDEBAR"], cursor="hand2")
            frame.pack(fill="x", pady=1)
            bar = tk.Frame(frame, width=3, bg=P["SIDEBAR"])
            bar.pack(side="left", fill="y")
            icon = tk.Label(frame, text=item["icon"], font=(SYMBOL_FONT, 12), width=2, bg=P["SIDEBAR"],
                            fg=P["MUTED"], cursor="hand2")
            icon.pack(side="left", padx=(12, 0), pady=9)
            label = tk.Label(frame, text=item["text"], font=(UI_FONT, 11), anchor="w", bg=P["SIDEBAR"],
                             fg=P["MUTED"], cursor="hand2")
            label.pack(side="left", padx=(6, 12), fill="x", expand=True)
            row = {"item": item, "frame": frame, "bar": bar, "icon": icon, "label": label}
            for widget in (frame, icon, label):
                widget.bind("<Button-1>", lambda _e, w=item["widget"]: self.select(w))
                widget.bind("<Enter>", lambda _e, r=row: self._hover(r, True))
                widget.bind("<Leave>", lambda _e, r=row: self._hover(r, False))
            self._rows.append(row)
        self._restyle()

    def _hover(self, row, inside):
        if row["item"]["widget"] is self._current:
            return
        colour = P["HOVER"] if inside else P["SIDEBAR"]
        for key in ("frame", "icon", "label", "bar"):
            row[key].configure(bg=colour)
        row["label"].configure(fg=P["TEXT"] if inside else P["MUTED"])

    def _restyle(self):
        for row in self._rows:
            selected = row["item"]["widget"] is self._current
            bg = P["ACCENT_SOFT"] if selected else P["SIDEBAR"]
            for key in ("frame", "icon", "label"):
                row[key].configure(bg=bg)
            row["bar"].configure(bg=P["ACCENT"] if selected else P["SIDEBAR"])
            row["icon"].configure(fg=P["ACCENT"] if selected else P["MUTED"])
            row["label"].configure(fg=P["TEXT"] if selected else P["MUTED"],
                                   font=(UI_FONT, 11, "bold") if selected else (UI_FONT, 11))


# ---------------------------------------------------------------------------
# radio card
# ---------------------------------------------------------------------------

class RadioCard(tk.Frame):
    """A selectable card (title + detail) bound to *variable*; replaces a plain radio button."""

    def __init__(self, master, text, detail, variable, value, command=None, wraplength=520):
        super().__init__(master, bg=P["CARD"], highlightthickness=1, highlightbackground=P["BORDER"],
                         highlightcolor=P["BORDER"], cursor="hand2")
        self._variable, self._value, self._command = variable, value, command
        self._dot = tk.Canvas(self, width=18, height=18, bg=P["CARD"], highlightthickness=0, bd=0, cursor="hand2")
        self._dot.pack(side="left", padx=(14, 0), pady=14)
        text_box = tk.Frame(self, bg=P["CARD"], cursor="hand2")
        text_box.pack(side="left", fill="x", expand=True, padx=(12, 14), pady=10)
        self._title = tk.Label(text_box, text=text, font=(UI_FONT, 11, "bold"), bg=P["CARD"], fg=P["TEXT"],
                               anchor="w", cursor="hand2")
        self._title.pack(anchor="w")
        self._detail = tk.Label(text_box, text=detail, font=(UI_FONT, 9), bg=P["CARD"], fg=P["MUTED"],
                                anchor="w", justify="left", wraplength=wraplength, cursor="hand2")
        if detail:
            self._detail.pack(anchor="w", pady=(2, 0))
        for widget in (self, self._dot, text_box, self._title, self._detail):
            widget.bind("<Button-1>", self._choose)
        variable.trace_add("write", lambda *_a: self._refresh())
        self._refresh()

    def _choose(self, _event=None):
        self._variable.set(self._value)
        if self._command:
            self._command()

    def _refresh(self):
        selected = self._variable.get() == self._value
        bg = P["ACCENT_SOFT"] if selected else P["CARD"]
        for widget in (self, self._dot, self._title, self._detail, *self.winfo_children()):
            try:
                widget.configure(bg=bg)
            except tk.TclError:
                pass
        for child in self.winfo_children():
            for sub in getattr(child, "winfo_children", lambda: [])():
                try:
                    sub.configure(bg=bg)
                except tk.TclError:
                    pass
        self.configure(highlightbackground=P["ACCENT"] if selected else P["BORDER"])
        self._dot.delete("all")
        self._dot.create_oval(1, 1, 17, 17, outline=P["ACCENT"] if selected else P["MUTED"], width=2)
        if selected:
            self._dot.create_oval(5, 5, 13, 13, fill=P["ACCENT"], outline=P["ACCENT"])
