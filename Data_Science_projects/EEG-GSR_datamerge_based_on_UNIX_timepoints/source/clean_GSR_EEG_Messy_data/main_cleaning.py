"""
Wrapper script to run all three EEG–GSR matching versions
with a single input folder, and compare performance.
"""

import time
from pathlib import Path

# Import the three versions
# Assume the previous version scripts are in the same folder or installed as modules
# For this example, let's assume you saved them as version_A.py, version_B.py, version_C.py

from version_C import match_files_version_C


def run_all_versions(input_folder):
    """
    Run Version A, B, and C on the same input folder, 
    measure execution time, and return results.
    """

    input_folder = Path(input_folder)
    results_summary = {}

    # print(f"Running Version A (Fastest Range-Based) on {input_folder}...")
    # start_time = time.time()
    # df_a = match_files_version_A(input_folder)
    # t_a = time.time() - start_time
    # results_summary['Version_A'] = {'time_sec': t_a, 'matches': len(df_a)}
    # print(f"Version A done in {t_a:.2f} seconds, {len(df_a)} matches found.\n")

    # print(f"Running Version B (Sample-Level Interpolation) on {input_folder}...")
    # start_time = time.time()
    # df_b = match_files_version_B(input_folder)
    # t_b = time.time() - start_time
    # results_summary['Version_B'] = {'time_sec': t_b, 'matches': len(df_b)}
    # print(f"Version B done in {t_b:.2f} seconds, {len(df_b)} matches found.\n")

    print(f"Running Version C (Continuous High-Precision) on {input_folder}...")
    start_time = time.time()
    df_c = match_files_version_C(input_folder)
    t_c = time.time() - start_time
    results_summary['Version_C'] = {'time_sec': t_c, 'matches': len(df_c)}
    print(f"Version C done in {t_c:.2f} seconds, {len(df_c)} matches found.\n")

    print("Performance Summary:")
    for ver, info in results_summary.items():
        print(f"{ver}: Time = {info['time_sec']:.2f} sec, Matches = {info['matches']}")

    return df_c, results_summary
    # return df_b, df_c, results_summary
    


if __name__ == "__main__":
    # Example usage: pass your input folder path here
    input_folder = "data/thesis_study/mixed_data_working"
    run_all_versions(input_folder)
