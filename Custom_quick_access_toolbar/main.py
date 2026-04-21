import os
import json
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import windnd

# ── Constants ──────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quickdrop_config.json")
BOX_WIDTH   = 230
BOX_HEIGHT  = 120

# ── Config I/O ─────────────────────────────────────────────────────────────────

def load_config() -> list:
    if not os.path.exists(CONFIG_PATH):
        return []
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [e for e in data if isinstance(e, dict) and "label" in e and "path" in e]
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_config(entries: list) -> None:
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)

# ── Path decoding ──────────────────────────────────────────────────────────────

def decode_path(raw) -> str:
    if isinstance(raw, bytes):
        for enc in ("mbcs", "utf-8", "latin-1"):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("latin-1", errors="replace")
    return raw

# ── Copy logic ─────────────────────────────────────────────────────────────────

def _run_copy(src: str, dest_dir: str, status_cb):
    src  = src.strip().rstrip("\\/")
    name = os.path.basename(src)
    if not name:
        status_cb("ERROR: could not determine filename")
        return

    flags = subprocess.CREATE_NO_WINDOW

    if os.path.isdir(src):
        dest_sub = os.path.join(dest_dir, name)
        cmd = f'robocopy "{src}" "{dest_sub}" /E /NFL /NDL /NJH /NJS /nc /ns /np'
        proc = subprocess.Popen(cmd, shell=True, creationflags=flags,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc.wait()
        if proc.returncode <= 7:
            status_cb(f"Copied folder: {name}")
        else:
            status_cb(f"ERROR copying {name} (code {proc.returncode})")
    else:
        cmd = f'copy /Y "{src}" "{dest_dir}\\{name}"'
        proc = subprocess.Popen(cmd, shell=True, creationflags=flags,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc.wait()
        if proc.returncode == 0:
            status_cb(f"Copied: {name}")
        else:
            status_cb(f"ERROR copying {name}")


def copy_items(raw_paths: list, dest_dir: str, status_cb) -> None:
    def worker():
        paths = [decode_path(p) for p in raw_paths]
        status_cb(f"Copying {len(paths)} item(s)...")
        for src in paths:
            _run_copy(src, dest_dir, status_cb)
    threading.Thread(target=worker, daemon=True).start()

# ── DropBox widget ─────────────────────────────────────────────────────────────

class DropBox(tk.Frame):
    C_TITLE   = "#1a4a8a"
    C_IDLE    = "#0f2a50"
    C_COPYING = "#5a3a00"
    C_OK      = "#0a3a0a"
    C_ERROR   = "#5a0a0a"
    C_STATUS  = "#091c36"

    def __init__(self, parent, label: str, path: str, on_remove, **kw):
        super().__init__(parent, bd=2, relief="groove", **kw)
        self.label_text = label
        self.path       = path
        self.on_remove  = on_remove
        self._build_ui()
        self._hook_drop()

    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self, bg=self.C_TITLE, cursor="hand2")
        title_bar.pack(fill="x")

        remove_btn = tk.Button(
            title_bar, text="✕", bg=self.C_TITLE, fg="#cccccc",
            relief="flat", padx=5, pady=1,
            font=("Segoe UI", 9), cursor="hand2",
            activebackground="#c0392b", activeforeground="white",
            command=self._on_remove
        )
        remove_btn.pack(side="right")

        title_lbl = tk.Label(
            title_bar, text=self.label_text,
            bg=self.C_TITLE, fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=6, pady=5, anchor="w", cursor="hand2"
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        for w in (title_bar, title_lbl):
            w.bind("<Button-1>", self._open_explorer)

        # Drop zone
        self.drop_zone = tk.Label(
            self,
            text=_short_path(self.path),
            bg=self.C_IDLE, fg="#6688bb",
            font=("Segoe UI", 8),
            wraplength=BOX_WIDTH - 20,
            justify="center",
        )
        self.drop_zone.pack(fill="both", expand=True, padx=4, pady=(4, 2))

        # Status bar
        self.status_lbl = tk.Label(
            self, text="ready", bg=self.C_STATUS, fg="#5577aa",
            font=("Segoe UI", 7), anchor="w", padx=6, pady=2
        )
        self.status_lbl.pack(fill="x")

    def _hook_drop(self):
        for widget in (self, self.drop_zone, self.status_lbl):
            windnd.hook_dropfiles(widget, func=self._on_drop)

    def _on_drop(self, raw_files):
        self._set_status("Copying...", self.C_COPYING)
        copy_items(raw_files, self.path, self._thread_status)

    def _thread_status(self, msg: str):
        color = self.C_ERROR if msg.upper().startswith("ERROR") else self.C_OK
        self.after(0, self._set_status, msg, color)

    def _set_status(self, msg: str, bg=None):
        self.status_lbl.config(text=msg)
        if bg:
            self.drop_zone.config(bg=bg)
            self.after(3000, lambda: self.drop_zone.config(bg=self.C_IDLE))

    def _open_explorer(self, _event=None):
        if os.path.isdir(self.path):
            subprocess.Popen(["explorer", self.path])
        else:
            messagebox.showwarning(
                "Path not found",
                f"Directory does not exist:\n{self.path}",
                parent=self.winfo_toplevel()
            )

    def _on_remove(self):
        self.on_remove(self)


def _short_path(path: str, max_len: int = 38) -> str:
    if len(path) <= max_len:
        return path
    half = (max_len - 3) // 2
    return path[:half] + "..." + path[-half:]

# ── Main application window ────────────────────────────────────────────────────

class QuickDropApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quick Drop")
        self.geometry("750x520")
        self.minsize(320, 240)
        self.configure(bg="#060f1e")
        self.boxes: list = []
        self._build_ui()
        self._load_and_render()

    def _build_ui(self):
        # Toolbar
        toolbar = tk.Frame(self, bg="#060f1e", pady=6)
        toolbar.pack(fill="x", side="top")

        tk.Label(
            toolbar, text="Quick Drop",
            bg="#060f1e", fg="white",
            font=("Segoe UI", 14, "bold"), padx=12
        ).pack(side="left")

        tk.Button(
            toolbar, text="＋  Add Folder",
            command=self._add_box,
            bg="#1a4a8a", fg="white", relief="flat",
            font=("Segoe UI", 10), padx=12, pady=4,
            cursor="hand2",
            activebackground="#2a6abf", activeforeground="white"
        ).pack(side="right", padx=12)

        # Separator
        tk.Frame(self, bg="#1a3060", height=1).pack(fill="x")

        # Scrollable canvas
        container = tk.Frame(self, bg="#060f1e")
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg="#060f1e", highlightthickness=0)
        scrollbar   = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.boxes_frame = tk.Frame(self.canvas, bg="#060f1e")
        self._cwin = self.canvas.create_window((0, 0), window=self.boxes_frame, anchor="nw")

        self.boxes_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self._cwin, width=event.width)
        self._reflow()

    def _load_and_render(self):
        for entry in load_config():
            self._create_box(entry["label"], entry["path"], save=False)

    def _create_box(self, label: str, path: str, save: bool = True):
        box = DropBox(
            self.boxes_frame,
            label=label,
            path=path,
            on_remove=self._remove_box,
            bg="#060f1e"
        )
        self.boxes.append(box)
        self._reflow()
        if save:
            self._save()

    def _reflow(self):
        for box in self.boxes:
            box.grid_forget()

        canvas_w = self.canvas.winfo_width() or 750
        cols = max(1, canvas_w // (BOX_WIDTH + 14))

        for i, box in enumerate(self.boxes):
            row, col = divmod(i, cols)
            box.grid(row=row, column=col, padx=7, pady=7, sticky="nsew")
            box.config(width=BOX_WIDTH, height=BOX_HEIGHT)

        for c in range(cols):
            self.boxes_frame.columnconfigure(c, weight=1)

    def _add_box(self):
        path = filedialog.askdirectory(title="Select folder for drop box", parent=self)
        if not path:
            return
        path  = os.path.normpath(path)
        label = self._ask_label(default=os.path.basename(path) or path)
        if label is None:
            return
        self._create_box(label, path)

    def _ask_label(self, default: str):
        dialog = tk.Toplevel(self)
        dialog.title("Box Label")
        dialog.geometry("330x130")
        dialog.resizable(False, False)
        dialog.configure(bg="#0d1f40")
        dialog.grab_set()
        dialog.transient(self)

        tk.Label(dialog, text="Label for this drop box:",
                 bg="#0d1f40", fg="white",
                 font=("Segoe UI", 10)).pack(pady=(16, 4))

        var   = tk.StringVar(value=default)
        entry = tk.Entry(dialog, textvariable=var, width=36,
                         bg="#1a3060", fg="white", insertbackground="white",
                         relief="flat", font=("Segoe UI", 10))
        entry.pack(ipady=4)
        entry.select_range(0, "end")
        entry.focus_set()

        result = [None]

        def ok(_event=None):
            result[0] = var.get().strip() or default
            dialog.destroy()

        def cancel(_event=None):
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg="#0d1f40")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=ok, width=10,
                  bg="#1a4a8a", fg="white", relief="flat").pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", command=cancel, width=10,
                  bg="#333333", fg="white", relief="flat").pack(side="left", padx=4)
        entry.bind("<Return>", ok)
        entry.bind("<Escape>", cancel)

        dialog.wait_window()
        return result[0]

    def _remove_box(self, box: DropBox):
        if messagebox.askyesno("Remove", f'Remove drop box "{box.label_text}"?', parent=self):
            self.boxes.remove(box)
            box.destroy()
            self._reflow()
            self._save()

    def _save(self):
        save_config([{"label": b.label_text, "path": b.path} for b in self.boxes])


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QuickDropApp()
    app.mainloop()
