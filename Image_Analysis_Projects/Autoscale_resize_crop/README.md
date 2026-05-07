# Autoscale Resize & Crop

> Applies binary masks and fixed-coordinate crops to batches of TIF images, with a parallel pipeline for pattern-matched centre-cropping and rescaling.

---

## Project Overview

- **Problem**: Clinical imaging studies produce large batches of TIF images that need to be masked, cropped to a standard region of interest, and optionally rescaled — a process that must be consistent across thousands of files and repeatable across study runs.
- **Type**: Image processing pipeline / batch automation
- **Approach**: Two complementary scripts handle different cropping strategies: one applies a binary mask and fixed-pixel crop coordinates; the other uses filename pattern matching to identify relevant images and centres the crop around a bounding box.

---

## Objective

- Produce standardised, masked, and cropped TIF images ready for downstream analysis.
- Ensure filename consistency and avoid double-extension artefacts in output files.

---

## Dataset

| Field | Details |
|---|---|
| Source | Local directory of TIF images |
| Input | Raw `.tif` files in `data/raw/TIF/` |
| Mask | Single binary mask TIF (`data/masks/mask_1.tif`) |
| Output | `_masked.tif` and `_masked_cropped.tif` files in configured output directories |

---

## Methodology

**Pipeline 1 — Mask & crop (`mask_crop.py`)**
1. Reads a single binary mask once before the image loop (O(1) mask I/O).
2. Iterates over `.tif` files in the input directory.
3. Applies the mask via bitwise AND.
4. Crops to fixed pixel coordinates (`CROP_Y`, `CROP_X`, `CROP_HEIGHT`, `CROP_WIDTH`).
5. Writes `{stem}_masked.tif` and `{stem}_masked_cropped.tif` (stem computed with `os.path.splitext` to avoid double extensions).

**Pipeline 2 — Centre crop & rescale (`CROP_RESCALE_CUSTOM_BHA_Centered.py`)**
1. Scans the input directory using a regex filename pattern (`FILENAME_PATTERN`).
2. Reads matched TIF files using OpenCV.
3. Locates a template region using the `ImageAnalysis.FindTemplateFunctions` module.
4. Centres the crop around the detected bounding box.
5. Rescales to a standard output size using `ImageAnalysis.ResizeAndCropFunctions`.

---

## Code Structure

```
Autoscale_resize_crop/
├── mask_crop.py         # Mask application and fixed-coordinate crop
├── CROP_RESCALE_CUSTOM_BHA_Centered.py  # Pattern-matched centre crop and rescale
├── CROP_RESCALE_CUSTOM_BHA_Centered_old.py  # Superseded; retained for reference
└── ImageAnalysis/                        # Shared image processing library
    ├── ResizeAndCropFunctions.py
    ├── FindTemplateFunctions.py
    ├── MaskFunctions.py
    ├── ContourFunctions.py
    └── ...
```

---

## Key Logic

The mask is loaded once before the image loop rather than inside it — a fix from the original code that re-read the same mask file on every iteration. For large batches this eliminates N redundant disk reads. The output filename stem is extracted with `os.path.splitext` to prevent the `image.tif_masked.tif` double-extension bug that existed in the original.

---

## Results

> No benchmark metrics — output quality is validated visually by the operator.

---

## Limitations

- Crop coordinates (`CROP_Y`, `CROP_X`, `CROP_HEIGHT`, `CROP_WIDTH`) are specific to the imaging setup and must be reconfigured for different camera resolutions or physical setups.
- The `ImageAnalysis/` library is a shared dependency not included in a package install — the script must be run from the project root.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Image processing | OpenCV (`cv2`) |
| Numerical | NumPy |
| Internal library | ImageAnalysis (ResizeAndCrop, FindTemplate, Mask modules) |
| Logging | Python standard `logging` |

---

## How to Run

```bash
# Pipeline 1 — Mask & fixed crop
# 1. Set INPUT_PATH, MASK_PATH, and output paths in the script constants
python mask_crop.py

# Pipeline 2 — Centre crop & rescale
# 1. Set INPATH, OUTPATH, FILENAME_PATTERN, and ORDERING constants
python CROP_RESCALE_CUSTOM_BHA_Centered.py
```

---

## Business / Practical Value

Standardises the image region of interest across an entire study batch in a single run, ensuring that downstream colour analysis and AI-assisted scoring tools receive consistently framed inputs without operator variability.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
