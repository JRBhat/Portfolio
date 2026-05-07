# 🔬 Automated Raman Spectroscopy Water Concentration Heatmap Generator

Generates publication-quality 2D and 3D heatmaps of skin water concentration from Raman spectroscopy measurements, across subjects, products, and timepoints — fully automated from a single Excel file.

---

## 🧠 Project Overview

- **Problem**: Manually plotting multi-subject, multi-product, multi-timepoint Raman spectroscopy data into consistent, publication-ready figures is time-consuming and hard to reproduce.
- **Type**: Scientific Data Visualization Pipeline
- **Approach**: PCHIP interpolation + Gaussian blur for 2D depth-vs-scan heatmaps; scattered-point `griddata` interpolation + 3D Gaussian blur for spatial tissue-block visualizations.

---

## 🎯 Objective

- Automate the generation of 2D and 3D water concentration heatmaps for each study subject from a structured Excel input.
- Produce structured quality logs alongside every pipeline run to track data gaps, clipping warnings, and scan-count anomalies.

---

## 📊 Dataset

| Field | Details |
|---|---|
| Source | Internal — Raman spectroscopy measurements from a clinical skin study |
| Size | Not clear from available documentation |
| Features | subjectID, product (_B/_C/_D), timePoint (T01/T02/T03), x_position (µm), y_position (µm), depth (0–40 µm), Water_Percent (%), exclude flag |
| Target | Water_Percent — Raman-derived skin water content, clipped to [8–75]% |

> Subject IDs are pseudonymized (S001–S004). The raw Excel file is excluded from the repository via `.gitignore`.

---

## ⚙️ Methodology

1. **Data Loading & Filtering** — Reads the Excel sheet, casts depth to int, filters out excluded rows and out-of-range depth values, logs clipping and NaN statistics.
2. **2D Pipeline** — Per subject/product/timepoint: pivots raw measurements into a (41 depths × n_scans) matrix, merges near-duplicate scan positions, fills NaNs via lateral interpolation, applies two-pass PCHIP (horizontal then vertical), and smooths with Gaussian blur before rendering.
3. **3D Pipeline** — Per subject: groups by (x, y, depth), interpolates 10 scattered scan positions to a regular 40×40 spatial grid via `scipy.griddata`, applies 3D Gaussian blur, upsamples the depth axis (41→100 px), and renders a five-face 3D tissue block.
4. **Quality Logging** — Every run produces a timestamped text log with row counts, clipping warnings, merge counts, and NaN fill summaries.

---

## 🧩 Code Structure

```
Automated_RAMAN_Wasser_concentration_plots/
├── main.py                        # CLI entry point (argparse: --input, --output, --mode)
├── heatmap_2d.py                  # 2D depth-vs-scan-index heatmap generator (v10)
├── heatmap_3d.py                  # 3D spatial tissue-block visualization (v7)
├── config.py                      # Study design constants and colormap definition
├── palette.py                     # Shared colormap builder (yellow→navy, NaN→white)
├── quality_log.py                 # Structured INFO/WARN logging with timestamped output
├── data_io.py                     # Unified Excel loading, filtering, and statistics
├── create_algorithm_slides.py     # Interactive slide deck generator (synthetic data only)
├── requirements.txt
└── README.md
```

---

## 🧠 Key Logic / Algorithm

The 2D pipeline uses two-pass PCHIP interpolation: first horizontally (20 pixels per scan position) to densify the lateral axis, then vertically (161 pixels for the 0–40 µm depth range) for smooth depth transitions. A final Gaussian blur removes interpolation artifacts without blurring the biological gradient. This approach preserves monotonicity at each pass, which is important for Raman data where sharp depth gradients are meaningful.

The 3D pipeline uses `scipy.griddata` to map 10 real scan positions (arbitrary x, y coordinates) onto a regular 40×40 spatial grid at each of 41 depth slices. A 3D Gaussian blur is applied to the resulting volume before rendering five faces of a tissue block, with actual scan positions marked as white dots on the top face.

---

## 📈 Results

> No quantitative model metrics apply — this is a visualization pipeline.

Quality metrics tracked per run:
- Row counts: total loaded, after exclusion filtering
- Water_Percent range (min / max / mean / NaN count)
- Clipping warnings: rows below 8% or above 75%
- Per-panel warnings: missing scans, merged near-duplicates, NaN fills

---

## ⚠️ Limitations

- Study design is hardcoded in `config.py`: 3 products × 3 timepoints × 10 expected scans — the pipeline needs code changes for different study layouts.
- Smoothing and interpolation parameters (`SIGMA_X_SCANS`, `SIGMA_Y_UM`, `NX_PER_SCAN`) are hardcoded in `heatmap_2d.py` rather than exposed as config constants. Future iterations will handle this.

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Data | pandas, numpy, openpyxl |
| Visualization | matplotlib |
| Interpolation | scipy (PchipInterpolator, griddata, gaussian\_filter, zoom) |
| CLI | argparse |

---

## ▶️ How to Run

```bash
# 1. Clone the repo
git clone "repo path"
cd Automated_RAMAN_Wasser_concentration_plots

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run both pipelines
python main.py --input data/your_study.xlsx --output output/ --mode both

# Or run a single mode
python main.py --input data/your_study.xlsx --output output/ --mode 2d
python main.py --input data/your_study.xlsx --output output/ --mode 3d
```

---

## 💡 Business / Practical Value

Raman spectroscopy studies generate hundreds of individual measurements per subject. Without automation, producing consistent, reproducible heatmaps across all subjects and conditions takes significant analyst time and introduces manual plotting errors. This pipeline reduces per-study visualization effort from hours to minutes, and the structured quality log makes it straightforward to catch data quality issues (missing scans, out-of-range values) before results are shared with collaborators.

---

## 👤 Author

Jayesh Bhat · [LinkedIn](https://linkedin.com/in/your-profile) · [GitHub](https://github.com/your-username)
