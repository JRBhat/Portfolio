# Recursive Image Watermarking

> Recursively walks a directory tree, detects image files, and applies a watermark batch script to each unique directory exactly once — with progress tracking and timing.

---

## Project Overview

- **Problem**: Adding watermarks to large collections of images organised in nested folder structures requires running a watermarking tool on each directory, but doing this manually is slow and risks skipping or double-processing folders.
- **Type**: Batch automation / file processing utility
- **Approach**: Uses `os.walk` to traverse the directory tree, identifies directories containing images, and triggers a `.bat` watermarking script for each unique directory. A second variant adds file-level validation before processing.

---

## Objective

- Apply a watermark to every image in a nested directory structure in a single run.
- Avoid processing the same directory twice and report total elapsed time.

---

## Dataset

| Field | Details |
|---|---|
| Source | Local directory tree of JPEG, PNG, and TIF/TIFF images |
| Input | Root path configured as `PATH` constant |
| Watermark source | `.bat` script path configured as `BAT_SOURCE` constant |
| Output | Watermarked images in-place (overwrite or alongside originals, depending on the `.bat` script) |

---

## Methodology

1. **Directory walk** — `os.walk(PATH)` yields each subdirectory with its file list.
2. **Image detection** — Files are checked with `file.endswith(('.jpg', '.png', '.tif', '.tiff'))`.
3. **First-image trigger** — When the first image in a directory is encountered (`not bat_placed`), the batch script is invoked via `subprocess` and the directory is tracked as "done".
4. **Skip logic** — Subsequent images in the same directory are skipped (`bat_placed = True`); the flag resets at the next directory.
5. **Timing** — Total elapsed time is printed in minutes or hours depending on duration.

A separate `watermarking_withFileValidation.py` variant adds pre-processing file validation using `os.path.basename` for portable path handling.

---

## Code Structure

```
Recursive_Image_watermarking/
└── source/
    ├── watermarking_Final_Stable.py          # Main stable implementation
    ├── watermarking_withFileValidation.py    # Variant with file validation
    ├── watermarking_Final.py                 # Older variant (review before deleting)
    └── Transperent_watermarks_code/          # Alpha-channel watermark variant
```

---

## Key Logic

The `bat_placed` boolean (renamed from the original integer `count`) tracks whether the batch script has been triggered for the current directory. It resets to `False` at the start of each new directory in the walk. This ensures exactly one watermark application per directory regardless of how many images it contains.

The extension check uses `endswith(('.jpg', '.png', '.tif', '.tiff'))` — a fix from the original `'tif'in file` substring check that would incorrectly match filenames like `notification.jpg`.

---

## Results

> No benchmark metrics. Output quality depends on the watermarking `.bat` script.

Key outputs:
- Watermarked images across the full directory tree
- Console report of total elapsed time in minutes or hours

---

## Limitations

- The watermark logic is delegated entirely to the external `.bat` script — the Python code only triggers it. Watermark appearance and placement are controlled by that script.
- `BAT_SOURCE` and `PATH` are hardcoded constants; each run for a different root directory requires source editing.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| File traversal | os.walk (standard library) |
| Process execution | subprocess (standard library) |
| Timing | time (standard library) |

---

## How to Run

```bash
# 1. Set the constants in source/watermarking_Final_Stable.py:
#    PATH = r"C:\path\to\your\image\folder"
#    BAT_SOURCE = r"C:\path\to\watermark_batch.bat"

# 2. Run
python source/watermarking_Final_Stable.py
```

---

## Business / Practical Value

Eliminates the need to manually navigate nested study folders and trigger the watermarking tool for each one — a task that scales poorly beyond a few dozen directories.

---

## Author

Jayesh Bhat · [LinkedIn] · [GitHub]
