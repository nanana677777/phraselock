"""Thumbnail gallery for the background list: each image or GIF is shown as a small picture with a
cross to remove it, in a scrollable grid.

``item_kind`` and ``columns`` are plain functions (tested); ``ThumbGallery`` is the Tk widget. Pictures
are decoded one at a time between UI events, so a long list never freezes the window.
"""

import os
import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageOps, ImageTk
except Exception:                 # Pillow missing: tiles show text only
    Image = ImageOps = ImageTk = None

TILE_W, THUMB_H, GAP = 112, 64, 8
CAPTION_CHARS = 16


def item_kind(item, exists=os.path.isfile):
    """"url", "missing", "gif" or "image" for a background list entry."""
    text = str(item or "").strip()
    if text.lower().startswith(("http://", "https://")):
        return "url"
    if not exists(text):
        return "missing"
    return "gif" if text.lower().endswith(".gif") else "image"


def columns(width, tile_w=TILE_W, gap=GAP):
    """How many tiles fit in a row of *width* pixels (at least one)."""
    return max(1, (max(0, int(width)) + gap) // (tile_w + gap))


def caption(item, limit=CAPTION_CHARS):
    text = str(item or "").strip()
    name = text.rsplit("/", 1)[-1] if text.lower().startswith(("http://", "https://")) else os.path.basename(text)
    name = name or text
    return name if len(name) <= limit else name[:limit - 1] + "…"


class ThumbGallery(tk.Frame):
    def __init__(self, master, on_remove, colors, height=190, font=("Segoe UI", 8)):
        super().__init__(master, bg=colors["INPUT"], highlightthickness=1, highlightbackground=colors["BORDER"])
        self.on_remove = on_remove
        self.c = colors
        self.font = font
        self.items = []
        self._cache = {}          # (path, mtime) -> PhotoImage
        self._generation = 0
        self._tiles = []
        self._cols = 0
        self._canvas = tk.Canvas(self, height=height, bg=colors["INPUT"], highlightthickness=0, bd=0)
        self._scroll = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._on_scroll_set)
        self._inner = tk.Frame(self._canvas, bg=colors["INPUT"])
        self._window = self._canvas.create_window(0, 0, window=self._inner, anchor="nw")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scroll.pack(side="right", fill="y")
        self._empty = tk.Label(self._inner, text="No background image: a plain colour is used.",
                               bg=colors["INPUT"], fg=colors["MUTED"], font=font, pady=18)
        self._canvas.bind("<Configure>", self._on_configure)
        self._inner.bind("<Configure>", lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._bind_wheel(self._canvas)
        self._bind_wheel(self._inner)

    # ----- scrolling
    def _on_scroll_set(self, first, last):
        self._scroll.set(first, last)
        # Hide the scrollbar when everything fits.
        if float(first) <= 0.0 and float(last) >= 1.0:
            self._scroll.pack_forget()
        elif not self._scroll.winfo_ismapped():
            self._scroll.pack(side="right", fill="y")

    def _scrollable(self):
        first, last = self._canvas.yview()
        return not (first <= 0.0 and last >= 1.0)

    def _on_wheel(self, event):
        if not self._scrollable():
            return None            # let the page scroll
        self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def _bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_wheel)

    # ----- layout
    def _on_configure(self, event):
        self._canvas.itemconfigure(self._window, width=event.width)
        cols = columns(event.width - 2 * GAP)
        if cols != self._cols:
            self._cols = cols
            self._layout()

    def _layout(self):
        for index, tile in enumerate(self._tiles):
            tile.grid(row=index // max(1, self._cols), column=index % max(1, self._cols),
                      padx=(GAP, 0), pady=(GAP, 0), sticky="nw")
        self._inner.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # ----- content
    def set_items(self, items):
        self.items = list(items)
        self._generation += 1
        for tile in self._tiles:
            tile.destroy()
        self._tiles = []
        self._empty.pack_forget()
        if not self.items:
            self._empty.pack(fill="x")
            self._canvas.yview_moveto(0)
            return
        pending = []
        for item in self.items:
            tile, label = self._make_tile(item)
            self._tiles.append(tile)
            pending.append((item, label))
        self._layout()
        self._load(self._generation, pending)

    def _make_tile(self, item):
        c = self.c
        kind = item_kind(item)
        tile = tk.Frame(self._inner, bg=c["CARD"], width=TILE_W, highlightthickness=1,
                        highlightbackground=c["BORDER"])
        holder = tk.Frame(tile, bg=c["CARD_ALT"], width=TILE_W - 8, height=THUMB_H)
        holder.pack(padx=3, pady=(3, 0))
        holder.pack_propagate(False)
        picture = tk.Label(holder, bg=c["CARD_ALT"], fg=c["MUTED"], font=self.font,
                           text={"url": "online", "missing": "file missing"}.get(kind, "..."))
        picture.pack(fill="both", expand=True)
        tk.Label(tile, text=caption(item), bg=c["CARD"], fg=c["MUTED"], font=self.font, anchor="w").pack(
            fill="x", padx=4, pady=(1, 2))
        if kind == "gif":
            tk.Label(tile, text="GIF", bg=c["ACCENT"], fg=c["ACCENT_TEXT"], font=(self.font[0], 7, "bold"),
                     padx=3).place(x=6, y=6)
        remove = tk.Button(tile, text="\u00d7", command=lambda i=item: self.on_remove(i), relief="flat", bd=0,
                           highlightthickness=0, bg=c["CARD"], fg=c["TEXT"], activebackground=c["DANGER"],
                           activeforeground="#ffffff", font=(self.font[0], 11, "bold"), padx=4, pady=0,
                           cursor="hand2")
        remove.place(relx=1.0, x=-5, y=5, anchor="ne")
        for widget in (tile, holder, picture):
            self._bind_wheel(widget)
        return tile, picture

    def _load(self, generation, pending):
        """Decode the pictures one by one between UI events."""
        if generation != self._generation or not pending:
            return
        item, label = pending.pop(0)
        photo = self._thumbnail(item) if item_kind(item) in ("image", "gif") else None
        try:
            if photo is not None:
                label.configure(image=photo, text="")
                label.image = photo
            elif item_kind(item) in ("image", "gif"):
                label.configure(text="unreadable")
            else:
                label.configure(text={"url": "online", "missing": "file missing"}[item_kind(item)])
        except tk.TclError:
            return
        self.after(5, lambda: self._load(generation, pending))

    def _thumbnail(self, path):
        if Image is None:
            return None
        try:
            key = (path, os.path.getmtime(path))
            if key in self._cache:
                return self._cache[key]
            with Image.open(path) as img:
                img.draft("RGB", (TILE_W * 2, THUMB_H * 2))
                img.seek(0)
                frame = img.convert("RGB")
            fitted = ImageOps.fit(frame, (TILE_W - 8, THUMB_H), Image.LANCZOS)
            photo = ImageTk.PhotoImage(fitted, master=self)
            self._cache[key] = photo
            return photo
        except Exception:
            return None
