# 🚀 Quick Drop

> A lightweight Windows desktop app that turns any folder into a drag-and-drop target, so you can copy files to your most-used directories without hunting through Explorer.

---

## 🧠 Project Overview

- **Problem**: I kept opening the same half-dozen folders every day (downloads sink, project scratch dirs, a network share for handoffs) just to paste files into them. Alt-tabbing through Explorer windows was the slowest part of an otherwise fast workflow.
- **Type**: Desktop utility — Tkinter GUI with native Windows drag-and-drop.
- **Approach**: A tiled panel of user-defined "drop boxes." Each box is bound to one target directory; dropping files or folders onto a box copies them there via `robocopy` (folders) or `shutil` (files) on a background thread.

---

## 🎯 Objective

- Eliminate the repetitive "open Explorer → navigate → paste" dance for a small number of frequently-used directories.
- Stay out of the way: no installer, no background service, one Python file, config persisted as plain JSON.
- Feel instant — the UI must never freeze while a large folder is copying.

---

## 🖼️ Preview

*ToBeAdded: add a screenshot or GIF of the app*

---

## ✨ Features

- **Drag-and-drop onto any box** — uses `windnd` to hook native Windows file drops.
- **Per-box destination** — each box is labeled and tied to one folder.
- **Threaded copy** — `robocopy` for folders (recursive, preserves structure), shell `copy` for single files. UI stays responsive; status bar updates live.
- **Persistence** — boxes survive restart. Stored as JSON next to the script.
- **Responsive grid** — boxes reflow into columns based on window width.
- **Click title to open** — tapping a box's title bar opens the destination in Explorer.
- **Safe writes** — config is written atomically (`.tmp` + `os.replace`) so a crash mid-save can't corrupt it.
- **Encoding-tolerant paths** — drop payloads are decoded through a cascade of `mbcs` → `utf-8` → `latin-1` to handle paths with non-ASCII characters.

---

## 🧩 Code Structure

```
Custom_quick_access_toolbar/
├── main.py                  # Entire app — UI, copy engine, config I/O
├── quickdrop_config.json    # Runtime-generated, stores your box list (gitignored)
└── .pixi/                   # Local pixi environment (gitignored)
```

`main.py` is organized into four commented sections:

| Section | Responsibility |
|---|---|
| **Config I/O** | `load_config`, `save_config` — read/write the JSON box list |
| **Path decoding** | `decode_path` — robustly decodes drop-payload bytes |
| **Copy logic** | `_run_copy`, `copy_items` — threaded dispatch to `robocopy` / `copy` |
| **UI** | `DropBox` widget + `QuickDropApp` main window |

---

## 🧠 Key Logic

**Why `robocopy` for folders?** A Python-level recursive copy blocks the GIL and can take seconds on large trees. `robocopy` is built for this: it's multi-threaded internally, handles long paths, and returns a well-defined exit code (≤ 7 means success, including "nothing to copy"). The UI layer only has to interpret the return code.

**How the UI stays responsive.** Drops are handed to a daemon `threading.Thread`; that worker calls `status_cb(...)` with progress strings. The callback is wrapped with `self.after(0, ...)`, which schedules the Tkinter update back on the main thread — the only thread allowed to touch widgets.

**Responsive reflow.** `QuickDropApp._reflow` recalculates column count from the current canvas width on every resize event, then re-grids every box. No fixed layout — resize the window and boxes reorganize.

---

## ⚠️ Limitations

- **Windows only.** Relies on `robocopy`, `copy /Y`, `subprocess.CREATE_NO_WINDOW`, and Windows-style wheel deltas. Will fail immediately on macOS/Linux.
- **No conflict resolution.** `copy /Y` overwrites silently; `robocopy` merges and overwrites newer files by default. If you need confirmation prompts, they aren't here.
- **No copy progress bar** — only a ready/copying/done status label per box. Fine for small drops; on a multi-GB folder you're staring at "Copying…" for a while.
- **No undo.** A dropped file is copied immediately. If you drop onto the wrong box, you have to clean up manually.
- **Shell-interpolated paths.** `_run_copy` builds commands via `shell=True` with f-string interpolation. For a single-user local tool this is fine, but pathological filenames (containing quotes) could misbehave. Swapping to argv-list `subprocess.run` is a low-effort hardening.

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| GUI | Tkinter (stdlib) |
| Drag-and-drop | [`windnd`](https://pypi.org/project/windnd/) |
| File copy | `robocopy` (folders), `shutil` / shell `copy` (files) |
| Concurrency | `threading` |
| Persistence | JSON (stdlib) |
| Env management | [Pixi](https://pixi.sh) (optional — the repo ships a `.pixi/` cache) |

---

## ▶️ How to Run

```bash
# 1. Clone
git clone https://github.com/<your-username>/Custom_quick_access_toolbar.git
cd Custom_quick_access_toolbar

# 2. Install the one external dependency
pip install windnd

# 3. Launch
python main.py
```

Then:
1. Click **＋ Add Folder**, pick a destination directory, give the box a label.
2. Drag files or folders from Explorer onto the box.
3. Click the box's title bar to open the destination in Explorer.
4. Click **✕** on a box to remove it.

Box definitions are saved automatically to `quickdrop_config.json` next to `main.py`.

---

## 💡 Practical Value

A personal productivity tool, not a product. The payoff is the hundreds of small "where was that folder again?" context switches it removes per week. It's also a compact demonstration of:

- Keeping a Tkinter UI responsive with background threads and `after()`-dispatched callbacks,
- Bridging a native Windows drag-and-drop hook (`windnd`) into a cross-thread-safe GUI,
- Atomic JSON persistence, and
- Responsive grid layout driven by canvas resize events.

---

## 👤 Author

**Jayesh Bhat** · [LinkedIn](www.linkedin.com/in/jayeshbhat) · [GitHub](https://github.com/JRBhat)

