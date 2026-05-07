"""
VERSION C — CONTINUOUS HIGH-PRECISION TIMELINE
===============================================

Creates a high-resolution continuous timeline (virtual grid) and
interpolates both EEG and GSR timestamps to determine continuous overlap.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import shutil

from data_loaders import load_eeg_easy_file, read_shimmer_file


def continuous_overlap(eeg_ts, gsr_ts, resolution=10000):
    """
    Creates a virtual timeline from min to max of combined timelines.

    interpolation:
        virtual_eeg[t] = True if EEG has data around this moment
        virtual_gsr[t] = True if GSR has data around this moment
    """
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


def plot_continuous(vt, eeg_mask, gsr_mask, out_path):
    plt.figure(figsize=(10, 2))
    plt.fill_between(vt, 0, eeg_mask.astype(int), alpha=0.4, label="EEG coverage")
    plt.fill_between(vt, 0, gsr_mask.astype(int), alpha=0.4, label="GSR coverage")
    plt.title("Continuous Timeline Overlap")
    plt.xlabel("Unix Time")
    plt.yticks([])
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def match_files_version_C(input_folder, output_folder="output_C2", threshold=0.05):
    input_folder = Path(input_folder)
    output_folder = Path(input_folder/ output_folder)
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

            pct, vt, emask, gmask = continuous_overlap(eeg_ts, gsr_ts)

            if pct > threshold:
                match_id = f"match_{match_counter:03d}"
                match_path = output_folder / match_id
                match_path.mkdir(exist_ok=True)

                shutil.copy(eeg_file, match_path / eeg_file.name)
                shutil.copy(gsr_file, match_path / gsr_file.name)

                plot_continuous(vt, emask, gmask, match_path / f"continuous_overlap{match_id}.png")

                results.append({
                    "match_id": match_id,
                    "EEG_file": eeg_file.name,
                    "GSR_file": gsr_file.name,
                    "pct_continuous_overlap": pct
                })

                match_counter += 1

                print(f"  --> Match found! (pct_eeg={pct:.3f})")
            else:
                print(f"  --> No match. (pct_eeg={pct:.3f})")
            print("GSR files remaining to compare:", len(gsr_files) - gsr_files.index(gsr_file) - 1)
        print("EEG files remaining to compare:", len(eeg_files) - eeg_files.index(eeg_file) - 1)
        
    df = pd.DataFrame(results)
    df.to_csv(output_folder / "results_VersionC.csv", index=False)
    return df
