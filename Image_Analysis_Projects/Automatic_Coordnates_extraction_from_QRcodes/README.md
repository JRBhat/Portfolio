# 📐 Automated QR Code-Based Scan Registration & Coordinate Extraction

Detects QR codes in scanned dermatology assessment sheets, registers skewed images against a golden-standard reference using a similarity transform, and generates binary circle masks for downstream skin irritation analysis.

---

## 🧠 Project Overview

- **Problem**: Scanned D-Squame assessment sheets arrive at arbitrary orientations and positions. Manual coordinate extraction for 56 subjects × 4 body areas × 3 timepoints is impractical and error-prone.
- **Type**: Computer Vision / Image Processing Pipeline
- **Approach**: Contour-based QR localization (OpenCV morphology + pyzbar decoding) → similarity transform registration (scikit-image) → circle mask generation for downstream measurement.

---

## 🎯 Objective

- Automatically locate and decode QR codes on scanned sheets to identify subjects.
- Register each skewed scan to a golden-standard reference image, correcting for rotation and scale.
- Generate binary circle masks that define the exact measurement regions for skin irritation quantification.

---

## 📊 Dataset

| Field | Details |
|---|---|
| Source | Internal — 600 DPI TIF scans of D-Squame skin assessment sheets |
| Size | 56 subjects × 4 body areas × 3 timepoints (D-Squame skin irritation study) |
| Features | Scanned sheet images (`.tif`), PTX JSON coordinate files, golden-standard reference PTX |
| Target | Not applicable — pipeline outputs registered images and circle coordinate masks |

> All scan files are excluded from the repository via `.gitignore`. Subject IDs follow the pseudonymized format `S###F##T##`.

---

## ⚙️ Methodology

1. **Input Preparation** — Renames `.tif` scans to canonical format (`S###F01T01SKW.tif`); routes inverted or low-quality scans to a `bad/` directory.
2. **QR Detection** — Converts to grayscale → Gaussian blur → Otsu threshold → morphological hole-filling → contour filtering by area/size → pyzbar decode. Returns 4 corner coordinates per QR code.
3. **Similarity Transform Registration** — Estimates a 4-DOF similarity transform (translation, rotation, uniform scale) from the 4 QR corner correspondences between the golden-standard PTX and the skewed scan. Applies the same transform to the circle marker coordinates.
4. **Mask Generation** — Reads transformed circle coordinates from the PTX file; draws filled circles on a blank canvas. Produces three output TIFs: binary mask, semi-transparent overlay, and overlay with green circle outlines.

---

## 🧩 Code Structure

```
Automatic_Coordnates_extraction_from_QRcodes/
└── source/
    ├── main.py                              # Pipeline orchestrator
    ├── detect_qrcode.py                     # QR detection, PTX read/write helpers
    ├── scan_registration.py                 # Similarity transform estimation & application
    ├── create_binary_mask_overlay.py        # Binary mask and overlay generation
    ├── generate_qrcode.py                   # QR code generation for booklet templates
    ├── create_docs_with_qrcodes.py          # Word document generation with QR codes
    ├── Dsquame_final_analysis.py            # Downstream skin irritation analysis
    └── tests/
        └── test_dsquame_v1.py               # Pytest suite with synthetic fixtures
```

---

## 🧠 Key Logic / Algorithm

The registration step is the core of the pipeline. Four QR corner coordinates detected in a skewed scan are matched against the corresponding four corners in the golden-standard PTX file. `skimage.transform.SimilarityTransform` fits a rigid transform (no shear, uniform scale) to these correspondences. The same transform is then applied to the circle marker coordinates — this is what spatially aligns all measurement spots to the reference geometry, enabling valid cross-scan comparisons.

The PTX file format (a JSON list with typed `id` fields — `1` for QR corners, `2` for top circles, `3` for bottom circles) acts as the contract between pipeline stages, keeping coordinate data separate from image files.

---

## 📈 Results

> This is a pipeline tool — no model accuracy metrics apply.

Operational outputs per subject:
- `*_REG.tif` — registered (aligned) scan image
- `*_binary.tif` — binary circle mask
- `*_overlay.tif` — semi-transparent mask overlay on original image
- `*_overlay_w_circ.tif` — overlay with green circle outlines
- Updated PTX with registered coordinates (original backed up as `*_SKW_BCKP.ptx`)
- `data/scans/app.log` — full pipeline execution log

---

## ⚠️ Limitations

- Subject count and body area count are hardcoded; adapting to different study designs requires code changes.
- `create_docs_with_qrcodes.py` uses `subprocess` with `shell=True` for Windows ZIP operations — not portable to Linux/macOS.
- QR detection retry loop in `detect_qrcode.py` runs 6 identical morphological iterations — may be slow on large image batches.

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Image Processing | OpenCV (cv2), scikit-image |
| QR Code | pyzbar (decode), qrcode (generate) |
| Data | numpy, json |
| Documents | xml.etree.ElementTree, subprocess |
| Parallelism | joblib (downstream analysis only) |
| Testing | pytest |

---

## ▶️ How to Run

```bash
# 1. Clone the repo
git clone "repo_address"
cd Automatic_Coordnates_extraction_from_QRcodes

# 2. Install dependencies (no requirements.txt — install manually)
pip install opencv-python pyzbar qrcode scikit-image numpy

# 3. Place scanned TIF files in data/scans/
# 4. Ensure reference PTX is at data/reference/S000F00T00VAL.ptx

# 5. Run the pipeline
python code/source/main.py

# 6. Run tests (unit tests only, no internal_library needed)
pytest code/source/tests/test_dsquame_v1.py -v -m "not integration"
```

---

## 💡 Business / Practical Value

D-Squame studies require precise, reproducible measurement of skin barrier disruption at specific anatomical locations. Without automated registration, every scanned sheet would need manual coordinate entry — an analyst-hours bottleneck that also introduces inter-operator variability. This pipeline processes a full study batch unattended, and the PTX audit trail makes it straightforward to inspect or re-run individual registrations if a scan is flagged as problematic.

---

## 👤 Author

Jayesh Bhat · [LinkedIn](https://linkedin.com/in/your-profile) · [GitHub](https://github.com/your-username)
