"""
VERSION A — FASTEST
====================

This version computes overlap purely using timestamp
range intersections:

    overlap = max(0, min(end1, end2) - max(start1, start2))

No interpolation is used. This is extremely fast and scales
well when many files exist.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import shutil

from data_loaders import load_eeg_easy_file, read_shimmer_file


# ---------------------------------------------------------------------
# Overlap computation (range-only)
# ---------------------------------------------------------------------
def compute_overlap_range(ts1, ts2):
    """
    Fastest overlap method:
    Only compares overall time ranges.

    Returns overlap duration and percentages.
    """
    start1, end1 = ts1[0], ts1[-1]
    

    start2, end2 = ts2[0], ts2[-1]

    overlap_start = max(start1, start2)
    overlap_end   = min(end1, end2)

    if overlap_end <= overlap_start:
        return (0, None, None, 0, 0)

    overlap = overlap_end - overlap_start

    pct1 = overlap / (end1 - start1)
    pct2 = overlap / (end2 - start2)

    return overlap, overlap_start, overlap_end, pct1, pct2


# ---------------------------------------------------------------------
# Plot timeline overlap
# ---------------------------------------------------------------------
def create_overlap_plot(eeg_ts, gsr_ts, overlap_start, overlap_end, out_path):
    """
    Creates a simple horizontal timeline plot showing:
        - EEG range
        - GSR range
        - Overlap range (highlighted green)
    """
    plt.figure(figsize=(10, 2))

    plt.hlines(1, eeg_ts[0], eeg_ts[-1], linewidth=8)
    plt.hlines(2, gsr_ts[0], gsr_ts[-1], linewidth=8)

    if overlap_start and overlap_end:
        plt.hlines(1.5, overlap_start, overlap_end, linewidth=8)

    plt.yticks([1, 1.5, 2], ["EEG", "Overlap", "GSR"])
    plt.xlabel("Unix Time")
    plt.title("Timeline Overlap")

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


# ---------------------------------------------------------------------
# Main matching function
# ---------------------------------------------------------------------
def match_files_version_A(input_folder, output_folder="output_A", threshold=0.05):
    """
    Matches EEG (.easy) and GSR (.csv) files based on time-range overlap.

    Creates a folder for each match:
        output_A/match_001/
            EEG_file.easy
            GSR_file.csv
            overlap.png

    Returns a DataFrame of match results.
    """
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
            print(f"Comparing {eeg_file.name} and {gsr_file.name}...")
            gsr_ts = read_shimmer_file(gsr_file)

            overlap_sec, ostart, oend, pct_eeg, pct_gsr = compute_overlap_range(
                eeg_ts, gsr_ts
            )

            if pct_eeg > threshold:
                match_id = f"match_{match_counter:03d}"
                match_path = output_folder / match_id
                match_path.mkdir(exist_ok=True)

                # Copy files
                shutil.copy(eeg_file, match_path / eeg_file.name)
                shutil.copy(gsr_file, match_path / gsr_file.name)

                # Plot
                # plot_path = match_path / "timeline_overlap.png"
                # create_overlap_plot(eeg_ts, gsr_ts, ostart, oend, plot_path)

                results.append({
                    "match_id": match_id,
                    "EEG_file": eeg_file.name,
                    "GSR_file": gsr_file.name,
                    "overlap_seconds": overlap_sec,
                    "pct_overlap_eeg": pct_eeg,
                    "pct_overlap_gsr": pct_gsr
                })

                match_counter += 1
                print(f"  --> Match found! (pct_eeg={pct_eeg:.3f})")
            else:
                print(f"  --> No match. (pct_eeg={pct_eeg:.3f})")
            print("GSR files remaining to compare:", len(gsr_files) - gsr_files.index(gsr_file) - 1)
        print("EEG files remaining to compare:", len(eeg_files) - eeg_files.index(eeg_file) - 1)
        
        
    df = pd.DataFrame(results)
    print("Saving results to CSV...")
    df.to_csv(output_folder / "results_VersionA.csv", index=False)
    return df
