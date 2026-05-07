# 🏷️ Barcode-Based Image Pair Renamer

Detects barcodes in scanned Canon JPEG images using computer vision and automatically renames both the JPG and CR2 raw file pairs using the decoded barcode as a filename prefix.

---

## 🧠 Project Overview

- **Problem**: Manually renaming large batches of scanned images is slow and error-prone — especially in lab settings where one barcode label physically covers multiple consecutive shots.
- **Type**: Computer Vision / Automation Tool
- **Approach**: Grayscale threshold masking to isolate the barcode region, pyzbar decoding, and a carry-forward rule to handle consecutive images under the same label.

---

## 🎯 Objective

- Automatically decode barcodes from scanned JPG images and rename both the JPG and its paired CR2 raw file with the barcode value as a prefix.
- Handle the common lab case where one barcode label corresponds to several consecutive images (carry-forward).

---

## 📊 Dataset

| Field | Details |
|---|---|
| Source | Internal — scanned Canon camera images from a clinical/lab study |
| Size | Not clear from available documentation |
| Features | Paired `.JPG` (preview) and `.CR2` (raw) files per scan |
| Target | Not applicable — this is an automation tool, not an ML project |

> No sample images are included. Input paths have been sanitized from the original clinical study directory structure.

---

## ⚙️ Methodology

1. **Image Loading** — Reads all `.JPG` files from `data/images/` via OpenCV.
2. **Barcode Detection** — Converts to grayscale, applies a threshold mask (pixel range 170–255) to isolate the barcode region, then decodes with `pyzbar`.
3. **Carry-Forward Rule** — When no barcode is detected in an image, the most recently decoded barcode is reused for that image pair.
4. **File Renaming** — Renames both `.JPG` and `.CR2` files with the barcode value as a prefix.
5. **Output Move** — Moves successfully renamed pairs to `data/images/out/`.

---

## 🧩 Code Structure

```
Barcode_reader_and_Image_Renamer/
└── source/
    ├── __init__.py
    ├── rename_imgs_with_barcodes.py          # Main pipeline — orchestrates the full workflow
    ├── barcode_reader_simple_refactored.py   # Production barcode decoder
    ├── barcode_reader.py                     # Exploratory reference (Sobel gradient method)
    └── barcode_reader_simple_old.py          # Legacy version (retained for reference)
├── requirements.txt
└── .gitignore
```

---

## 🧠 Key Logic / Algorithm

The carry-forward rule is the non-obvious piece: in practice, one physical barcode label is placed over several consecutive scanned samples. Rather than requiring a barcode in every image, the pipeline records the last successfully decoded barcode in a list and reuses it for the next image if detection fails. This matches the physical lab setup and avoids manual intervention for runs of unlabeled shots.

Barcode detection applies a grayscale threshold (pixels in [170, 255]) to create a binary mask before passing it to pyzbar. This helps isolate the barcode from background noise in scanned images, which tend to have uneven illumination.

---

## 📈 Results

> This is an automation tool — no ML metrics apply.

Outputs per run:
- Renamed `<barcode>*.JPG` and `<barcode>*.CR2` pairs moved to `data/images/out/`
- Debug artifacts per image: annotated bounding-box image and binary mask saved to `bin/`

---

## ⚠️ Limitations

- Expects every `.JPG` to have a matching `.CR2` in the same directory; raises `FileNotFoundError` if the raw file is missing.
- `barcode_reader.py` (the exploratory Sobel method) contains a magic number tied to one specific test image and is not used in the production pipeline.
- Threshold values (`MASK_LOWER = 170`, `MASK_UPPER = 255`) are hardcoded and may need tuning for different scanner/lighting setups.
- No CSV or log output tracking which barcode was assigned to which file.

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Image Processing | OpenCV (cv2), numpy, imutils |
| Barcode Decoding | pyzbar |
| Standard Library | os, shutil, typing |

---

## ▶️ How to Run

```bash
# 1. Clone the repo
git clone "repo address"
cd Barcode_reader_and_Image_Renamer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Place input images in data/images/ (JPG + CR2 pairs)

# 4. Run the pipeline
python -m source.rename_imgs_with_barcodes
```

Renamed output will appear in `data/images/out/`. Debug images (bounding boxes and masks) are saved to `bin/`.

---

## 💡 Business / Practical Value

In lab settings where hundreds of images are scanned per session, manual renaming to match barcode labels is a tedious, error-prone task. This tool processes a full image directory unattended in seconds, handles edge cases like missed barcode reads via the carry-forward rule, and saves debug artifacts so any detection failure can be reviewed visually — cutting post-scan prep time significantly.

---

## 👤 Author

Jayesh Bhat · [LinkedIn](https://linkedin.com/in/your-profile) · [GitHub](https://github.com/your-username)
