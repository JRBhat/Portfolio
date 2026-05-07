# Grey Card Brightness Validator

Analyses a batch of images for grey card (white balance reference) brightness, sorts them by EXIF timestamp, and groups them into "white" and "black" categories based on configurable luminance thresholds.

---

## Project Overview

- **Problem**: In multi-session photography studies, correctly identifying and grouping calibration images (grey cards) is done manually — slow and error-prone when dealing with thousands of images.
- **Type**: Image analysis / quality control utility
- **Approach**: Crops the centre region of each image, converts to LAB colour space, extracts the L* (luminance) channel, and classifies the image as "white" (above threshold) or "black" (below threshold). Images are sorted by EXIF capture timestamp before analysis.

---

## Objective

- Automatically separate a mixed batch of grey card images into bright and dark groups for downstream white balance calibration.
- Output a time-sorted plot of L* values and a log file summarising the classification.

---

## Dataset

| Field | Details |
|---|---|
| Source | Local directory of JPEG/TIF images with EXIF metadata |
| Size | Not fixed — scans the configured input directory |
| Features | Centre-cropped L* value (luminance), EXIF DateTimeOriginal |
| Target | Binary classification: "white" (W_THRESH ≤ L* ≤ 255) vs "black" (L* ≤ BLK_THRESH) |

---

## Methodology

1. **EXIF extraction** — `get_original_time_from_exif()` reads `Image DateTime` from each file using `exifread`.
2. **Time-sorted file list** — Files are sorted ascending by EXIF timestamp.
3. **Centre crop** — `crop_center()` extracts a fixed-pixel region from the centre of each image.
4. **LAB conversion** — The cropped region is converted from sRGB to LAB using a custom `sRGB_to_lab` utility.
5. **L* extraction** — The mean L* value of the crop is computed and stored.
6. **Threshold classification** — `group_whites.py` applies configurable `W_THRESH` and `BLK_THRESH` constants to move images into separate output folders.
7. **Visualisation** — `analyse_whites.py` plots L* over time using matplotlib and writes a text log.

---

## Code Structure

```
Grey_card_brightness_validator/
├── analyse_whites.py    # L* extraction, EXIF sorting, plotting, log output
└── group_whites.py      # Threshold-based classification and file sorting
```

---

## Key Logic

Both scripts share an identical `crop_center()` function (a known duplication flagged for future refactoring). The crop always targets the geometric centre of the image regardless of resolution, which works because grey cards are held in front of the camera and occupy the centre of the frame by convention.

The threshold classification in `group_whites.py` uses `os.makedirs(..., exist_ok=True)` to create output directories idempotently, making repeated runs safe.

---

## Results

Output depends on the input image set.

Key outputs:
- Matplotlib plot of L* luminance values over capture time
- Text log listing each file and its classified category
- Sorted image copies in `OUT_DIR_W` and `OUT_DIR_BLK` directories

---

## Limitations

- Requires EXIF `Image DateTime` tag in image metadata; files without it will cause an immediate exit.
- Hardcoded thresholds and crop sizes require source editing to adapt to different camera setups.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Image I/O | OpenCV (`cv2`) |
| Numerical | NumPy |
| EXIF reading | exifread |
| Visualisation | matplotlib |
| Colour conversion | Custom `sRGB_to_lab` (ImageAnalysis library) |

---

## How to Run

```bash
# 1. Set the input path and thresholds in group_whites.py (constants at the bottom)
#    INPATH, OUT_DIR_W, OUT_DIR_BLK, CROP_BOX_SIZE_IN_PX, W_THRESH, BLK_THRESH

# 2. Analyse and plot L* values
python analyse_whites.py

# 3. Group files into white/black folders
python group_whites.py
```

---

## Business / Practical Value

Eliminates manual sorting of calibration images in photography-based clinical studies, ensuring consistent white balance reference selection without operator judgement calls.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
