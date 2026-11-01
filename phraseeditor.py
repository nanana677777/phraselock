"""Phrase file editor: build a phrase file (CSV, JSON or TXT) without writing it by hand.

The pure functions (parsing pasted text, cleaning, saving) come first so they can be tested; the
Tk window (``open_editor``) is at the bottom. Files written here are read back by
``phrases.load_external_phrases`` exactly as they were typed.
"""

import csv
import json
import os
import re

DIFFICULTIES = ("easy", "normal", "hard", "extreme")
HEADER_WORDS = ("phrase", "phrases", "sentence", "text")
LONG_PHRASE = 150
DEFAULT_CATEGORY = "General"


def default_folder(config_dir=None):
    if config_dir is None:
        from config import CONFIG_DIR as config_dir
    return os.path.join(config_dir, "phrases")


def make_item(text, category=DEFAULT_CATEGORY, difficulty="normal"):
    difficulty = str(difficulty or "normal").strip().lower()
    return {"text": str(text).strip(),
            "category": (str(category).strip() or DEFAULT_CATEGORY),
            "difficulty": difficulty if difficulty in DIFFICULTIES else "normal"}


def check_text(text):
    """A problem with a single phrase, or '' when it is fine."""
    text = (text or "").strip()
    if not text:
        return "The phrase is empty."
    if text.startswith("#"):
        return "A phrase cannot start with '#': such lines are treated as comments."
    if "\n" in text or "\r" in text:
        return "A phrase must be on one line."
    return ""


def parse_lines(text, default_category=DEFAULT_CATEGORY, default_difficulty="normal"):
    """Phrases from pasted text, one per line. Returns (items, problems).

    A line is ``phrase``, ``phrase | difficulty``, ``phrase | category`` or
    ``phrase | category | difficulty`` (a tab works instead of ``|``, so a copy from a spreadsheet
    works). Blank lines, ``#`` comments and a ``phrase,category,difficulty`` header are skipped.
    """
    items, problems = [], []
    for number, raw in enumerate(str(text or "").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in (line.split("\t") if "\t" in line else line.split("|"))]
        parts = [p for p in parts] or [line]
        if not items and parts[0].lower() in HEADER_WORDS:
            continue
        phrase, category, difficulty = parts[0], default_category, default_difficulty
        if len(parts) == 2:
            if parts[1].lower() in DIFFICULTIES:
                difficulty = parts[1].lower()
            elif parts[1]:
                category = parts[1]
        elif len(parts) >= 3:
            category = parts[1] or default_category
            if parts[2].lower() in DIFFICULTIES or not parts[2]:
                difficulty = parts[2].lower() or default_difficulty
            else:
                problems.append(f"Line {number}: unknown difficulty '{parts[2]}', used '{default_difficulty}'.")
        if not phrase:
            problems.append(f"Line {number}: empty phrase, skipped.")
            continue
        items.append(make_item(phrase, category, difficulty))
    return items, problems


def clean_items(items):
    """Drop empty phrases and exact duplicates (first one wins). Returns (items, removed_count)."""
    seen, result, removed = set(), [], 0
    for item in items:
        text = str(item.get("text", "")).strip()
        if not text or text in seen:
            removed += 1
            continue
        seen.add(text)
        result.append(make_item(text, item.get("category"), item.get("difficulty")))
    return result, removed


def warnings(items):
    """Soft warnings about a phrase list."""
    out = []
    long_ones = sum(1 for i in items if len(i["text"]) > LONG_PHRASE)
    if long_ones:
        out.append(f"{long_ones} phrase(s) are longer than {LONG_PHRASE} characters: hard to type.")
    bad = sum(1 for i in items if check_text(i["text"]))
    if bad:
        out.append(f"{bad} phrase(s) cannot be saved as they are (empty, start with '#' or span several lines).")
    return out


def summary(items):
    counts = {d: sum(1 for i in items if i["difficulty"] == d) for d in DIFFICULTIES}
    detail = ", ".join(f"{n} {d}" for d, n in counts.items() if n)
    return f"{len(items)} phrase(s)" + (f" ({detail})" if detail else "")


def safe_filename(name, extension=".csv"):
    base = re.sub(r"[^\w\- ]+", "", str(name or "")).strip().replace(" ", "-") or "my-phrases"
    return base + extension


def save_phrases(path, items):
    """Write *items* to *path* as CSV, JSON or TXT (by extension; anything else becomes CSV).

    Returns the path actually written (an unknown extension gets '.csv' added). Phrases that would
    not read back correctly (see check_text) are not written; the count of those is not an error.
    """
    items = [i for i in clean_items(items)[0] if not check_text(i["text"])]
    if not items:
        raise ValueError("There is no phrase to save.")
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".csv", ".json", ".txt"):
        path += ".csv"
        ext = ".csv"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    if ext == ".csv":
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["phrase", "category", "difficulty"])
            for i in items:
                writer.writerow([i["text"], i["category"], i["difficulty"]])
    elif ext == ".json":
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"phrases": [{"phrase": i["text"], "category": i["category"], "difficulty": i["difficulty"]}
                                   for i in items]}, f, ensure_ascii=False, indent=2)
    else:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(i["text"] for i in items) + "\n")
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------------------
# window
# ---------------------------------------------------------------------------

def open_editor(root, items, source_label="the built-in list", start_dir=None):
    """Modal editor. *items* is the starting list. Returns the saved file path, or None."""
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import uikit
    from phrases import load_external_phrases
    from uikit import UI_FONT, Dropdown

    P = uikit.P
    uikit.style_ttk(root)
    state = {"items": clean_items([make_item(i.get("text", ""), i.get("category"), i.get("difficulty"))
                                   for i in items])[0], "saved": None, "dirty": False}
    win = tk.Toplevel(root)
    win.title("Phrase file editor")
    win.configure(bg=P["BG"])
    win.geometry("820x680")
    win.minsize(720, 600)
    win.transient(root)

    def label(parent, text, size=9, bold=False, color=None, **kw):
        return tk.Label(parent, text=text, font=(UI_FONT, size, "bold" if bold else "normal"),
                        fg=color or P["TEXT"], bg=P["BG"], **kw)

    def button(parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0, highlightthickness=0,
                         bg=P["ACCENT"] if primary else P["CARD_ALT"],
                         fg=P["ACCENT_TEXT"] if primary else P["TEXT"], padx=14, pady=6, cursor="hand2",
                         font=(UI_FONT, 9, "bold"))

    label(win, "Phrase file editor", 18, True).pack(anchor="w", padx=22, pady=(18, 0))
    label(win, f"Starting from {source_label}. Add, edit and paste phrases, then save a file you can use "
               "right away or share.", 9, color=P["MUTED"], wraplength=760, justify="left").pack(
        anchor="w", padx=22, pady=(0, 8))

    # --- list
    list_frame = tk.Frame(win, bg=P["BG"])
    list_frame.pack(fill="both", expand=True, padx=22)
    style = ttk.Style(win)
    style.configure("Phrases.Treeview", background=P["INPUT"], fieldbackground=P["INPUT"], foreground=P["TEXT"],
                    rowheight=24, borderwidth=0, font=(UI_FONT, 10))
    style.configure("Phrases.Treeview.Heading", background=P["CARD_ALT"], foreground=P["MUTED"],
                    relief="flat", font=(UI_FONT, 9, "bold"))
    style.map("Phrases.Treeview", background=[("selected", P["ACCENT"])], foreground=[("selected", P["ACCENT_TEXT"])])
    tree = ttk.Treeview(list_frame, columns=("text", "category", "difficulty"), show="headings",
                        style="Phrases.Treeview", selectmode="extended", height=10)
    for col, title, width in (("text", "Phrase", 480), ("category", "Category", 110), ("difficulty", "Difficulty", 90)):
        tree.heading(col, text=title)
        tree.column(col, width=width, anchor="w", stretch=(col == "text"))
    scroll = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    status_var = tk.StringVar()

    def refresh(select=None):
        tree.delete(*tree.get_children())
        for index, item in enumerate(state["items"]):
            tree.insert("", "end", iid=str(index), values=(item["text"], item["category"], item["difficulty"]))
        if select is not None and str(select) in tree.get_children():
            tree.selection_set(str(select))
            tree.see(str(select))
        extra = warnings(state["items"])
        status_var.set(summary(state["items"]) + ("   |   " + extra[0] if extra else ""))

    # --- one phrase form
    form = tk.Frame(win, bg=P["BG"])
    form.pack(fill="x", padx=22, pady=(10, 0))
    text_var, cat_var, diff_var = tk.StringVar(), tk.StringVar(value=DEFAULT_CATEGORY), tk.StringVar(value="normal")
    label(form, "Phrase").grid(row=0, column=0, sticky="w")
    entry_kw = dict(bg=P["INPUT"], fg=P["TEXT"], insertbackground=P["TEXT"], relief="flat", bd=0,
                    highlightthickness=1, highlightbackground=P["BORDER"], highlightcolor=P["ACCENT"],
                    font=(UI_FONT, 10))
    text_entry = tk.Entry(form, textvariable=text_var, **entry_kw)
    text_entry.grid(row=1, column=0, sticky="ew", ipady=5, padx=(0, 8))
    label(form, "Category").grid(row=0, column=1, sticky="w")
    tk.Entry(form, textvariable=cat_var, width=14, **entry_kw).grid(row=1, column=1, ipady=5, padx=(0, 8))
    label(form, "Difficulty").grid(row=0, column=2, sticky="w")
    Dropdown(form, diff_var, *DIFFICULTIES).grid(row=1, column=2)
    form.columnconfigure(0, weight=1)

    def mark_dirty():
        state["dirty"] = True

    def read_form():
        problem = check_text(text_var.get())
        if problem:
            messagebox.showerror("Phrase", problem, parent=win)
            return None
        return make_item(text_var.get(), cat_var.get(), diff_var.get())

    def on_add(_event=None):
        item = read_form()
        if not item:
            return
        state["items"].append(item)
        mark_dirty()
        text_var.set("")
        refresh(len(state["items"]) - 1)
        text_entry.focus_set()

    def selected_indexes():
        return sorted(int(i) for i in tree.selection())

    def on_update():
        picked = selected_indexes()
        if len(picked) != 1:
            messagebox.showinfo("Phrase", "Select one phrase in the list first.", parent=win)
            return
        item = read_form()
        if item:
            state["items"][picked[0]] = item
            mark_dirty()
            refresh(picked[0])

    def on_delete(_event=None):
        picked = selected_indexes()
        for index in reversed(picked):
            del state["items"][index]
        if picked:
            mark_dirty()
            refresh()

    def on_select(_event=None):
        picked = selected_indexes()
        if len(picked) == 1:
            item = state["items"][picked[0]]
            text_var.set(item["text"])
            cat_var.set(item["category"])
            diff_var.set(item["difficulty"])

    tree.bind("<<TreeviewSelect>>", on_select)
    tree.bind("<Delete>", on_delete)
    text_entry.bind("<Return>", on_add)
    row = tk.Frame(win, bg=P["BG"])
    row.pack(fill="x", padx=22, pady=(8, 0))
    button(row, "Add", on_add, primary=True).pack(side="left")
    button(row, "Update selected", on_update).pack(side="left", padx=(8, 0))
    button(row, "Delete selected", on_delete).pack(side="left", padx=(8, 0))

    # --- paste many
    label(win, "Paste several phrases (one per line). Optional: phrase | category | difficulty "
               "(easy, normal, hard, extreme).", 9, color=P["MUTED"]).pack(anchor="w", padx=22, pady=(12, 3))
    paste = tk.Text(win, height=4, bg=P["INPUT"], fg=P["TEXT"], insertbackground=P["TEXT"], relief="flat", bd=0,
                    highlightthickness=1, highlightbackground=P["BORDER"], highlightcolor=P["ACCENT"],
                    font=(UI_FONT, 10), wrap="none")
    paste.pack(fill="x", padx=22)

    def on_paste_add():
        items_in, problems = parse_lines(paste.get("1.0", "end"), cat_var.get().strip() or DEFAULT_CATEGORY,
                                         diff_var.get())
        if not items_in:
            messagebox.showinfo("Paste", "Nothing to add. Type or paste one phrase per line.", parent=win)
            return
        before = len(state["items"])
        state["items"], removed = clean_items(state["items"] + items_in)
        added = len(state["items"]) - before
        paste.delete("1.0", "end")
        mark_dirty()
        refresh()
        notes = [f"{added} phrase(s) added."]
        if removed:
            notes.append(f"{removed} duplicate or empty one(s) skipped.")
        notes += problems[:5]
        messagebox.showinfo("Paste", "\n".join(notes), parent=win)

    row2 = tk.Frame(win, bg=P["BG"])
    row2.pack(fill="x", padx=22, pady=(6, 0))
    button(row2, "Add pasted phrases", on_paste_add).pack(side="left")

    def on_import():
        path = filedialog.askopenfilename(parent=win, title="Import phrases", filetypes=[
            ("Phrase files", "*.txt *.csv *.json"), ("All files", "*.*")])
        if not path:
            return
        loaded = load_external_phrases(path)
        if not loaded:
            messagebox.showerror("Import", "No phrase could be read from that file.", parent=win)
            return
        state["items"], removed = clean_items(state["items"] + loaded)
        mark_dirty()
        refresh()

    def on_sort():
        order = {d: n for n, d in enumerate(DIFFICULTIES)}
        state["items"].sort(key=lambda i: (order[i["difficulty"]], i["category"].lower(), i["text"].lower()))
        mark_dirty()
        refresh()

    button(row2, "Import file...", on_import).pack(side="left", padx=(8, 0))
    button(row2, "Sort by difficulty", on_sort).pack(side="left", padx=(8, 0))

    # --- footer
    tk.Label(win, textvariable=status_var, font=(UI_FONT, 9), fg=P["MUTED"], bg=P["BG"], anchor="w").pack(
        fill="x", padx=22, pady=(10, 0))
    footer = tk.Frame(win, bg=P["BG"])
    footer.pack(fill="x", padx=22, pady=14)
    use_var = tk.BooleanVar(value=True)
    uikit.Switch(footer, text="Use this file in PhraseLock after saving", variable=use_var,
                 font=(UI_FONT, 9)).pack(side="left")

    def on_save():
        if not state["items"]:
            messagebox.showinfo("Save", "Add at least one phrase first.", parent=win)
            return
        folder = start_dir or default_folder()
        os.makedirs(folder, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=win, title="Save phrase file", initialdir=folder, initialfile="my-phrases.csv",
            defaultextension=".csv", filetypes=[("CSV (phrase, category, difficulty)", "*.csv"),
                                                ("JSON", "*.json"), ("Text, one phrase per line", "*.txt")])
        if not path:
            return
        try:
            written = save_phrases(path, state["items"])
        except Exception as exc:
            messagebox.showerror("Save", f"Could not save the file:\n{exc}", parent=win)
            return
        if written.lower().endswith(".txt"):
            messagebox.showinfo("Save", "A .txt file keeps only the phrases, not their category or difficulty.",
                                parent=win)
        state["saved"] = (written, bool(use_var.get()))
        state["dirty"] = False
        win.destroy()

    def on_close():
        if state["dirty"] and not messagebox.askyesno(
                "Close", "Close without saving your changes?", icon="warning", default="no", parent=win):
            return
        win.destroy()

    button(footer, "Save as...", on_save, primary=True).pack(side="right")
    button(footer, "Close", on_close).pack(side="right", padx=(0, 8))
    win.protocol("WM_DELETE_WINDOW", on_close)
    refresh()
    text_entry.focus_set()
    win.grab_set()
    win.wait_window()
    return state["saved"]
