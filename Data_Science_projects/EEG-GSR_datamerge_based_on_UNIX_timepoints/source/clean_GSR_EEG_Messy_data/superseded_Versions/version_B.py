"""
VERSION B — SAMPLE-LEVEL INTERPOLATION
======================================

More precise than Version A.
Measures overlap based on actual samples after interpolation.
"""

import os
import numpy as np
import pandas as pd
import shutil
import matplotlib.pyplot as plt
from pathlib import Path


from data_loaders import load_eeg_easy_file, read_shimmer_file

# ---------------- SAMPLE-LEVEL OVERLAP ----------------
def compute_overlap_interpolated(eeg_ts, gsr_ts):
    """
    Interpolates EEG timestamps to GSR domain and determines
    how many interpolated EEG times lie inside the GSR range.
    """

    g_start, g_end = gsr_ts[0], gsr_ts[-1]

    # Map EEG time indices to GSR sampling timeline
    eeg_interp = np.interp(
        np.linspace(0, len(eeg_ts)-1, len(gsr_ts)),
        np.arange(len(eeg_ts)),
        eeg_ts
    )

    inside = (eeg_interp >= g_start) & (eeg_interp <= g_end)
    pct = inside.sum() / len(eeg_interp)

    return pct, eeg_interp


# ---------------- PLOT ----------------
def create_overlap_plot(eeg_ts, gsr_ts, out_path):
    plt.figure(figsize=(10, 3))
    plt.scatter(eeg_ts, np.zeros_like(eeg_ts), s=1, label="EEG timestamps")
    plt.scatter(gsr_ts, np.ones_like(gsr_ts), s=1, label="GSR timestamps")

    plt.yticks([])
    plt.legend()
    plt.xlabel("Unix Time")
    plt.title("Sample-Level Timeline Comparison")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


# ---------------- MAIN ----------------
def match_files_version_B(input_folder, output_folder="output_B", threshold=0.05):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(exist_ok=True)

    eeg_files = list(input_folder.glob("*.easy"))
    gsr_files = list(input_folder.glob("*.csv"))

    results = []
    match_counter = 1

    for eeg_file in eeg_files:
        eeg_ts = load_eeg_easy_file(eeg_file)

        for gsr_file in gsr_files:
            gsr_ts = read_shimmer_file(gsr_file)

            pct, interp_ts = compute_overlap_interpolated(eeg_ts, gsr_ts)

            if pct > threshold:
                match_id = f"match_{match_counter:03d}"
                match_path = output_folder / match_id
                match_path.mkdir(exist_ok=True)

                shutil.copy(eeg_file, match_path / eeg_file.name)
                shutil.copy(gsr_file, match_path / gsr_file.name)

                # create_overlap_plot(eeg_ts, gsr_ts, match_path / "timeline_plot.png")

                results.append({
                    "match_id": match_id,
                    "EEG_file": eeg_file.name,
                    "GSR_file": gsr_file.name,
                    "pct_sample_overlap": pct
                })

                match_counter += 1

    df = pd.DataFrame(results)
    df.to_csv(output_folder / "results_VersionB.csv", index=False)
    return df
