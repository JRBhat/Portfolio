# 🧠 EEG-GSR Biosignal Merge & Analysis Pipeline

Merges EEG and GSR/PPG recordings from two independent devices on UNIX timestamps, computes heart rate and frontal alpha asymmetry, segments around event markers, and generates per-subject statistics reports and visualizations.

---

## 🧠 Project Overview

- **Problem**: EEG (NIC/Enobio) and GSR (Shimmer Consensys) devices record independently with no hardware sync — temporal alignment must be done programmatically by matching UNIX millisecond timestamps across two heterogeneous file formats.
- **Type**: Biosignal Processing Pipeline / Data Engineering
- **Approach**: UNIX-timestamp outer join → PPG-to-BPM via Butterworth bandpass + adaptive peak detection → Frontal Alpha Asymmetry from EEG alpha band powers → marker-based signal segmentation → per-subject median statistics.

---

## 🎯 Objective

- Produce a single, time-aligned dataset per subject combining EEG channels, GSR, and BPM, with imputed values highlighted in the output Excel for transparency.
- Support two study protocols (MASTERARBEIT and CLINICAL) with separate segmentation windows and timepoint definitions.

---

## 📊 Dataset

| Field | Details |
|---|---|
| Source | Internal — EEG recordings (NIC/Enobio device, `.easy`/`.tsv`) + GSR recordings (Shimmer Consensys, `.csv`) |
| Size | Not clear from available documentation |
| Features | EEG: 8 channels (ch1–ch8), 3-axis accelerometer, marker, UNIX-ms timestamp. GSR: skin conductance (µS), skin resistance (kΩ), PPG (mV), UNIX-ms timestamp |
| Target | Not applicable — pipeline computes BPM, FAA, and statistics as outputs |

> All raw data files are excluded from the repository via `.gitignore`. Subject identifiers and file paths have been fully anonymized.

---

## ⚙️ Methodology

1. **Discovery & Format Handling** — Finds `.easy` EEG files and `.csv` GSR files per subject; auto-detects English (tab-sep, dot-decimal) vs. German (semicolon-sep, comma-decimal) CSV format.
2. **Temporal Merge** — Converts UNIX-ms timestamps to datetime (CEST offset); outer joins EEG and GSR on timestamp; linearly interpolates EEG and BPM gaps; forward-fills GSR columns. Imputed cells are highlighted yellow in the Excel output.
3. **BPM Computation** — Applies a 0.5–10 Hz Butterworth bandpass to the PPG signal, then adaptive thresholding + peak detection to locate heartbeats; computes BPM from inter-beat intervals.
4. **Frontal Alpha Asymmetry (FAA)** — Reads per-subject EEG alpha band power text files; computes FAA = log(F4) − log(F3) for each timepoint.
5. **Marker Correction** — Remaps and renumbers event markers sequentially to ensure consistent downstream indexing.
6. **Segmentation & Plotting** — Segments the merged signal around each event marker into fixed windows (1-min for CLINICAL, 10-min for MASTERARBEIT); generates per-variable PNG plots with red marker annotations.
7. **Statistics & Final Report** — Computes per-subject median BPM, skin conductance, and FAA per timepoint; collates across subjects into a single Excel + composite PNG montage.

---

## 🧩 Code Structure

```
EEG-GSR_datamerge_based_on_UNIX_timepoints/
└── source/
    ├── main.py                                                      # Orchestrator — subject discovery and stage dispatch
    ├── merge_data_V2.py                                             # EEG+GSR temporal merge, BPM injection, Excel highlighting
    ├── calculate_bpm_best_practices.py                              # PPG → BPM via bandpass filter + peak detection
    ├── calculate_FFA.py                                             # Frontal Alpha Asymmetry computation
    ├── extract_markers.py                                           # Marker remapping and renumbering
    ├── plot_data_vertical_markers_matplotlib_V4_fullyrefac.py       # OO segmentation and plotting (DataLoader/Segmenter/Plotter)
    ├── generate_stats.py                                            # Per-subject median statistics
    ├── generate_final_report_and_image.py                          # Cross-subject collation + composite PNG
    ├── data_check.py                                                # Pre-flight diagnostic (EEG/GSR overlap, drift)
    ├── clean_GSR_EEG_Messy_data/                                    # Sub-pipeline for disorganized raw recordings
    ├── tests/
    │   ├── conftest.py                                              # Synthetic fixtures (PPG, EEG, segments, FAA)
    │   ├── test_bpm_calculation.py
    │   ├── test_merge_data.py
    │   ├── test_extract_markers.py
    │   ├── test_faa_calculation.py
    │   ├── test_generate_stats.py
    │   ├── test_generate_final_report.py
    │   └── test_prepare_data.py
    └── superseded/                                                   # Historical script versions (gitignored)
```

---

## 🧠 Key Logic / Algorithm

BPM is computed entirely from the PPG waveform without any wearable-specific SDK. A zero-phase Butterworth bandpass (0.5–10 Hz) removes baseline drift and high-frequency noise; adaptive thresholding then finds peaks robust to amplitude variations across subjects. Inter-beat intervals are converted to instantaneous BPM and resampled to align with the EEG timestamp grid.

Frontal Alpha Asymmetry (FAA = log(F4) − log(F3)) is a well-established EEG correlate of emotional valence and approach-withdrawal motivation. The pipeline computes this per timepoint from pre-computed alpha band power files, making it straightforward to compare emotional states across conditions.

---

## 📈 Results

> No aggregate study results are included in this repository — it contains the pipeline, not the study findings.

Per-subject outputs:
- `merged_highlighted_{subject}_bpmcorrected.xlsx` — time-aligned dataset with yellow-highlighted imputed cells
- PNG plots per signal per subject (BPM, skin conductance, EEG channels, with event marker lines)
- `statistics_{subject}.xlsx` — median BPM, skin conductance, FAA per timepoint

Study-level outputs:
- Consolidated Excel workbook across all subjects
- Grid PNG montage of all subject plots

---

## ⚠️ Limitations

- **Known FAA bug**: Clinical study FAA dispatch uses a string mismatch (`"clinical"` vs `"clinical_study"`) — clinical FAA results are silently skipped.
- **Timezone inconsistency**: Merge module applies +2h (CEST) offset; BPM module applies +1h — undocumented and may cause subtle misalignment near DST transitions.
- **No `requirements.txt`**: Dependencies must be installed manually.
- **Version suffixes in filenames** (`_V2`, `_V4_fullyrefac`) are a naming artifact from iterative development; the files are the current production versions.
- `data_check.py` and some cleaning modules execute code at module import (top-level scripts) — import-time side effects.

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Data | pandas, numpy, openpyxl |
| Signal Processing | scipy (Butterworth filter, peak detection) |
| Visualization | matplotlib |
| Testing | pytest |
| Standard Library | os, pathlib, enum, argparse, pickle, logging |

---

## ▶️ How to Run

```bash
# 1. Clone the repo
git clone "repo address"
cd EEG-GSR_datamerge_based_on_UNIX_timepoints

# 2. Install dependencies (no requirements.txt — install manually)
pip install pandas numpy scipy matplotlib openpyxl

# 3. Configure the study folder path in source/main.py (MAIN_DIR constant)

# 4. Run the pipeline
python source/main.py

# 5. Run tests
pytest source/tests/ -v
```

---

## 💡 Business / Practical Value

Combining EEG and physiological signals from different devices is a common bottleneck in academic biosignal research — each device uses its own clock and file format, making manual alignment error-prone. This pipeline handles the full merge and processing chain automatically, producing consistently formatted outputs for all subjects. The yellow-highlighted imputation cells in the Excel output give analysts immediate visibility into data quality without needing to re-run diagnostics.

---

## 👤 Author

Jayesh Bhat · [LinkedIn](https://linkedin.com/in/your-profile) · [GitHub](https://github.com/your-username)
