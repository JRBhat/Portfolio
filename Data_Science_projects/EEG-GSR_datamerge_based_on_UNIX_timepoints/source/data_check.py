"""
Pre-flight diagnostic script for EEG and GSR data quality.

Scans ``ROOT_FOLDER`` for subject sub-directories, loads EEG ``.easy`` files
and Shimmer GSR ``.csv`` files, then:

- Plots discrete EEG marker timelines per subject and saves a grid PNG to
  ``OUTPUT_FOLDER``.
- Checks Area ``.txt`` files for missing / malformed values and saves heatmap
  PNGs when issues are found.
- Computes continuous EEG–Shimmer timestamp overlap and temporal drift for
  each subject pair, saving a summary grid PNG to ``ROOT_FOLDER``.

All output files (PNGs, CSV summaries) are written to ``OUTPUT_FOLDER``.
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import logging
from math import ceil

# -------------------------------
# Logging setup
# -------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# -------------------------------
# Path constants
# -------------------------------
VALIDATION_FOLDER = "data/thesis_study/05-Final--validation"

# -------------------------------
# Output folder (all plots saved here)
# -------------------------------
OUTPUT_FOLDER = VALIDATION_FOLDER
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Colour map for EEG marker scatter plots.
MARKER_COLORS = {0: 'lightgray', 1: 'red', 2: 'blue', 3: 'green', 4: 'orange'}

# -------------------------------
# Data loader functions
# -------------------------------
def load_eeg_easy_file(file_path):
    """Load EEG .easy file, auto-detect marker and timestamp columns."""
    try:
        df = pd.read_csv(file_path, sep="\t", header=None, skiprows=1, engine="python", on_bad_lines='skip')
        if df.shape[1] < 2:
            raise ValueError(f"No valid columns found in {file_path}")

        # Detect timestamp column: numeric, large, monotonically increasing
        timestamp_col = None
        for col in df.columns:
            vals = pd.to_numeric(df[col], errors='coerce')
            if vals.notna().sum() < 2:
                continue
            if (vals > 1e9).all() and vals.is_monotonic_increasing:
                timestamp_col = col
                break
        if timestamp_col is None:
            raise ValueError(f"No timestamp column detected in {file_path}")

        # Detect marker column: single digits 0-4 with NaNs
        marker_col = None
        for col in df.columns:
            if col == timestamp_col:
                continue
            vals = df[col].dropna().unique()
            if all(str(v).isdigit() and int(v) in range(5) for v in vals):
                marker_col = col
                break
        if marker_col is None:
            raise ValueError(f"No marker column detected in {file_path}")

        timestamps = pd.to_numeric(df[timestamp_col], errors='coerce').to_numpy()
        markers = df[marker_col].fillna(0).astype(int).to_numpy()
        return timestamps, markers
    except Exception as e:
        logging.error(f"EEG file load error: {file_path} -> {e}")
        return None, None


def read_shimmer_file(file_path):
    """Read Shimmer file, auto-detect timestamp column."""
    try:
        with open(file_path, 'r') as f:
            first_line = f.readline().strip()
            _ = f.readline().strip()
        sep = first_line.split('=')[1] if first_line.startswith("sep=") else (';' if ';' in first_line else '\t')

        df = pd.read_csv(file_path, sep=sep, engine='python', header=None, dtype=str, skiprows=3)
        numeric_cols = {}
        for col in df.columns:
            try:
                vals = pd.to_numeric(df[col].str.replace(',', '.', regex=False), errors='coerce')
                numeric_cols[col] = vals
            except (ValueError, TypeError):
                continue

        ts_col = None
        for col, vals in numeric_cols.items():
            vals = vals.dropna()
            if len(vals) < 2:
                continue
            if (vals > 1e9).all() and vals.is_monotonic_increasing:
                ts_col = col
                break

        if ts_col is None:
            ts_col = list(numeric_cols.keys())[0]

        return numeric_cols[ts_col].to_numpy()
    except Exception as e:
        logging.error(f"Shimmer file load error: {file_path} -> {e}")
        return None


def load_area_file(file_path):
    """Load Area file."""
    try:
        df = pd.read_csv(file_path, sep="\t", engine="python")
        return df
    except Exception as e:
        logging.error(f"Area file load error: {file_path} -> {e}")
        return None

# -------------------------------
# Continuous overlap functions
# -------------------------------
def continuous_overlap(eeg_ts, gsr_ts, resolution=10000):
    """Create continuous overlap timeline for EEG and GSR timestamps."""
    t_start = min(eeg_ts[0], gsr_ts[0])
    t_end = max(eeg_ts[-1], gsr_ts[-1])
    vt = np.linspace(t_start, t_end, resolution)
    eeg_interp = np.interp(vt, eeg_ts, np.ones_like(eeg_ts), left=0, right=0)
    gsr_interp = np.interp(vt, gsr_ts, np.ones_like(gsr_ts), left=0, right=0)
    eeg_mask = eeg_interp > 0
    gsr_mask = gsr_interp > 0
    both = eeg_mask & gsr_mask
    pct = both.sum() / resolution
    return pct, vt, eeg_mask, gsr_mask

def plot_continuous(vt, eeg_mask, gsr_mask, ax, subj):
    """Plot continuous timeline overlap on existing axis."""
    ax.fill_between(vt, 0, eeg_mask.astype(int), alpha=0.4, label="EEG coverage")
    ax.fill_between(vt, 0, gsr_mask.astype(int), alpha=0.4, label="GSR coverage")
    ax.set_title(subj, fontsize=10)
    ax.set_yticks([])
    ax.set_xlabel("Unix Time", fontsize=8)
    ax.set_ylabel("Overlap", fontsize=8)
    ax.legend(fontsize=6)

# -------------------------------
# Root folder and subjects
# -------------------------------
ROOT_FOLDER = VALIDATION_FOLDER
subjects = [f for f in os.listdir(ROOT_FOLDER) if os.path.isdir(os.path.join(ROOT_FOLDER, f))]
logging.info(f"Found subjects: {subjects}")

eeg_results, area_results, shimmer_results = {}, {}, {}

# -------------------------------
# Load data from all subfolders
# -------------------------------
for subj in subjects:
    subj_folder = os.path.join(ROOT_FOLDER, subj)
    files = os.listdir(subj_folder)
    eeg_file = next((f for f in files if f.endswith(".easy")), None)
    area_file = next((f for f in files if f.endswith(".txt")), None)
    shimmer_file = next((f for f in files if f.endswith(".csv")), None)

    if eeg_file:
        ts, markers = load_eeg_easy_file(os.path.join(subj_folder, eeg_file))
        if ts is not None:
            eeg_results[subj] = (ts, markers)
    if area_file:
        area_results[subj] = load_area_file(os.path.join(subj_folder, area_file))
    if shimmer_file:
        shimmer_results[subj] = read_shimmer_file(os.path.join(subj_folder, shimmer_file))



# -------------------------------
# EEG marker plots (discrete)
# -------------------------------
n = len(eeg_results)
if n > 0:
    cols = ceil(np.sqrt(n))
    rows = ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3 * rows))
    axes = axes.flatten()

    for i, (subj, (ts, markers)) in enumerate(eeg_results.items()):
        for m in np.unique(markers):
            mask = markers == m
            axes[i].scatter(ts[mask], markers[mask], c=MARKER_COLORS[m], s=15, label=f'Marker {m}')
        axes[i].set_title(subj)
        axes[i].set_ylabel("Markers")
        axes[i].set_ylim(-0.5, 4.5)
        axes[i].legend(loc='upper right', fontsize=8)
    for j in range(i+1, len(axes)):
        axes[j].axis('off')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FOLDER, "EEG_markers_grid_discrete.png"), dpi=300)
    plt.close(fig)
    logging.info("✅ EEG markers plotted successfully.")


# -------------------------------
# Area file analysis (only if issues)
# -------------------------------
for subj, df in area_results.items():
    if df is None:
        logging.warning(f"[{subj}] Area file was not loaded correctly – skipping.")
        continue
    missing_map = df.isna() | df.isin(["?"])
    missing_count = missing_map.sum().sum()
    if missing_count == 0:
        logging.info(f"[{subj}] Area file is clean ✅ – no plot generated.")
        continue

    logging.warning(f"[{subj}] Area file contains {missing_count} missing or '?' values ❌")
    summary_table = pd.DataFrame({"Column": df.columns, "Missing_Count": (df.isna() | df.isin(["?"])).sum().values})
    summary_file = os.path.join(OUTPUT_FOLDER, f"Area_missing_summary_{subj}.csv")
    summary_table.to_csv(summary_file, index=False)
    plt.figure(figsize=(min(15, len(df.columns)), 5))
    sns.heatmap(missing_map, cbar=False, linewidths=0.2)
    plt.title(f"Missing / Weird Values Heatmap: {subj}")
    heatmap_file = os.path.join(OUTPUT_FOLDER, f"Area_missing_heatmap_{subj}.png")
    plt.tight_layout()
    plt.savefig(heatmap_file, dpi=300)
    plt.close()
    logging.info(f"[{subj}] Heatmap saved: {heatmap_file}")

logging.info("✅ Area file analysis completed.")



# -------------------------------
# Continuous EEG vs Shimmer Overlap + Drift Detection
# -------------------------------

def find_unix_column(df):
    """Return index of the column with UNIX timestamps (large numbers, strictly increasing)."""
    for col in df.columns:
        try:
            col_vals = pd.to_numeric(df[col], errors='coerce').dropna()
            if col_vals.empty:
                continue
            # UNIX timestamps usually > 1e9
            if col_vals.min() > 1e9 and col_vals.is_monotonic_increasing:
                return col
        except Exception:
            continue
    return None

def compute_drift(eeg_ts, gsr_ts):
    """Memory-efficient drift calculation: nearest neighbor differences."""
    eeg_ts = np.sort(eeg_ts)
    gsr_ts = np.sort(gsr_ts)
    idx = np.searchsorted(gsr_ts, eeg_ts)
    nearest_diff = np.empty_like(eeg_ts)
    for i, (e_val, j) in enumerate(zip(eeg_ts, idx)):
        if j == 0:
            nearest_diff[i] = abs(gsr_ts[0] - e_val)
        elif j == len(gsr_ts):
            nearest_diff[i] = abs(gsr_ts[-1] - e_val)
        else:
            nearest_diff[i] = min(abs(gsr_ts[j] - e_val), abs(gsr_ts[j-1] - e_val))
    return nearest_diff

# Prepare grid
valid_subjects = [s for s in subjects if s in eeg_results and s in shimmer_results]
if valid_subjects:
    n = len(valid_subjects)
    cols = ceil(np.sqrt(n))
    rows = ceil(n / cols)
    fig = plt.figure(figsize=(4*cols, 3*rows))
    gs = gridspec.GridSpec(rows, cols, figure=fig)

    for i, subj in enumerate(valid_subjects):
        eeg_ts, _ = eeg_results[subj]
        shimmer_ts = shimmer_results[subj]

        # Continuous overlap
        pct, vt, eeg_mask, gsr_mask = continuous_overlap(eeg_ts, shimmer_ts)

        # Drift
        nearest_diff = compute_drift(eeg_ts, shimmer_ts)
        drift_median = np.median(nearest_diff)
        drift_max = np.max(nearest_diff)

        ax = fig.add_subplot(gs[i])
        ax.fill_between(vt, 0, eeg_mask.astype(int), alpha=0.4, label="EEG coverage")
        ax.fill_between(vt, 0, gsr_mask.astype(int), alpha=0.4, label="Shimmer coverage")
        ax.set_title(f"{subj}\nOverlap: {pct*100:.1f}%, \nMedian drift: {drift_median:.3f}s, \nMax drift: {drift_max:.3f}s")
        ax.set_yticks([])
        ax.set_xlabel("Unix Time")
        ax.legend(fontsize=7)

    for j in range(i+1, rows*cols):
        fig.add_subplot(gs[j]).axis("off")

    plt.suptitle("EEG vs Shimmer Continuous Overlap & Drift per Subject", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    conv_path = os.path.join(ROOT_FOLDER, "EEG_Shimmer_continuous_overlap_grid.png")
    plt.savefig(conv_path, dpi=300)
    plt.close(fig)
    logging.info(f"✅ Continuous EEG–Shimmer overlap + drift grid saved -> {conv_path}")
else:
    logging.warning("No subjects with both EEG and Shimmer data for continuous overlap.")
