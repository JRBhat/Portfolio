# Visia ColorChart Validation

> Validates LAB colour accuracy of Visia camera captures against Macbeth ColorChecker reference values, and generates deviation plots across all imaging modes.

---

## Project Overview

- **Problem**: Visia cameras used in dermatological imaging need periodic colour calibration validation. Manually checking each colour patch against reference LAB values across multiple imaging modes is time-consuming and inconsistent.
- **Type**: Image quality validation / colour science utility
- **Approach**: Loads TIF images from four Visia imaging modes (Standard 1/2, Cross-Polarized, Parallel-Polarized), extracts ROI pixels for each of 25 Macbeth ColorChecker patches, converts to LAB, and computes the delta against known reference LAB values.

---

## Objective

- Quantify per-colour L* deviation from the Macbeth ColorChecker standard for each Visia imaging mode.
- Produce visualisation plots that make colour drift immediately visible for camera QC sign-off.

---

## Dataset

| Field | Details |
|---|---|
| Source | Visia camera (4 TIF images per validation run) |
| Imaging modes | Standard 1, Standard 2, Cross-Polarized, Parallel-Polarized |
| ColorChecker | 24 colour patches + 1 grey patch (25 total ROIs defined by pixel coordinates) |
| Reference standard | Macbeth ColorChecker LAB reference values (hardcoded in `color_check_standard_dict`) |

---

## Methodology

1. **Image loading** — Each of the four mode-specific TIF paths is read once with `cv2.imread`.
2. **ROI masking** — `extract_roi_mask(img)` applies a spatial mask to isolate the colour chart region.
3. **Per-patch extraction** — `extract_lab(colorname, coord_tuple, masked_img)` crops each of the 25 patches using `(x, y, w, h)` coordinates from `color_chart_coord_dict` and converts the pixel values to LAB.
4. **Delta calculation** — Extracted LAB values are compared against `color_check_standard_dict` reference tuples; deviation is stored in `gold_std_delta_dict`.
5. **Visualisation** — Three script variants produce different plot styles:
   - `main_logging.py` — subplot per colour with L* deviation across modes
   - `main_multiPlots_v1.py` — multi-plot variant
   - `main_simple.py` — single-figure simplified output

---

## Code Structure

```
Visia_ColorChart_Validation/
└── source/
    ├── main_logging.py       # Subplot visualisation with per-colour deviation logging
    ├── main_multiPlots_v1.py # Multi-plot variant
    └── main_simple.py        # Simplified single-figure output
```

> All three scripts share the same `color_chart_coord_dict`, `color_check_standard_dict`, and helper functions (currently duplicated; extraction to a shared module is a planned but unimplemented improvement).

---

## Key Logic

Each script was refactored to move `cv2.imread` and `extract_roi_mask` **outside** the inner colour loop. Previously, both were called once per colour patch per image — 25× redundant reads for each image. The fix reduces disk reads from 100 to 4 per run (once per image path).

The 25-patch ROI dictionary uses pixel coordinates specific to the Visia camera's image resolution and colour chart placement — these coordinates are not portable to other camera systems without re-calibration.

---

## Results

> No fixed numeric thresholds are defined in code for pass/fail. Delta values are reported visually for human judgement.

Key outputs:
- Per-colour LAB delta plots across all four imaging modes
- `img_color_dict` dictionary populated with extracted LAB tuples per image/colour combination

---

## Limitations

- ROI pixel coordinates (`color_chart_coord_dict`) are hardcoded for Visia camera resolution — not portable to other imaging systems.
- No automated pass/fail threshold is implemented; validation is visual.
- The three scripts share ~75 lines of duplicated dictionaries and helper functions (planned for extraction to `color_chart_data.py` but not yet done).
- Image paths are hardcoded in each script; adapting to a different dataset requires editing the source.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Image processing | OpenCV (`cv2`) |
| Numerical | NumPy |
| Visualisation | matplotlib |
| Colour science | Custom LAB conversion via OpenCV |

---

## How to Run

```bash
# 1. Place Visia TIF images in data/sample_images/ with the expected filenames:
#    sample_Standard_2.tif, sample_Standard_1.tif,
#    sample_Cross-Polarized.tif, sample_Parallel-Polarized.tif

# 2. Run the desired visualisation variant
python source/main_logging.py
# or
python source/main_multiPlots_v1.py
# or
python source/main_simple.py
```

---

## Business / Practical Value

Provides a fast, repeatable, and auditable colour validation workflow for Visia cameras in clinical imaging labs — replacing manual colour chart reading with an automated per-patch delta report.

---

## Author

Jayesh Bhat · [LinkedIn] · [GitHub]
