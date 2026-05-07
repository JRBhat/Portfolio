"""
Per-subject statistics aggregation for EEG-GSR studies.

This module provides two aggregation functions, one for each study design:

- :func:`generate_statistics_clinical` — six-timepoint longitudinal protocol.
  Parameters:
    - ``segments``: list of dicts, each with keys ``'marker'`` (int) and
      ``'data'`` (DataFrame containing at least ``'BPM'`` and
      ``'Skin_conductance_uS'`` columns).
    - ``ffa_output``: dict mapping FAA key strings (e.g. ``'FAA_baseline'``)
      to float values, as returned by :func:`calculate_FFA.compute_faa`.
    - ``merged_file_path``: absolute path to the merged Excel file; used to
      derive the subject name and output directory.
    - ``variables``: list of column names to aggregate (currently unused
      inside the function body but kept for API compatibility).

- :func:`generate_statistics_masterarbeit` — four-timepoint pre/application/
  CPT/post protocol.
  Parameters:
    - ``segments``: same shape as above.
    - ``ffa_output``: dict with keys ``'FAA_pre'`` and ``'FAA_post'``.
    - ``merged_file_path``: same as above.
"""
import logging
import os
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def generate_statistics_clinical(segments, ffa_output, merged_file_path, variables):
    # ----- Compute statistics and save to Excel -----
    subj_name = os.path.basename(os.path.dirname(merged_file_path))
    stat_file_name = f'statistics_{os.path.basename(os.path.dirname(merged_file_path))}_{subj_name}.xlsx'
    # Save statistics to Excel
    excel_path = os.path.join(os.path.dirname(merged_file_path), stat_file_name)
    if not os.path.exists(excel_path):
        stats_rows = []
        
        faa_headers = ['FAA_baseline', 'FAA_applk', 'FAA_5min', 'FAA_10min', 'FAA_15min', 'FAA_20min']
        marker_translations = ['Baseline', '2 min after application', '5min after application', '10min after application', '15min after application', '20min after application']
        for n, seg in enumerate(segments, start=1):
            df_win = seg['data']

            # for var in variables:
            stats_rows.append({
                'Timepoint': marker_translations[n-1],
                'BPM': df_win['BPM'].median(),
                'Skin_conductance_uS': df_win['Skin_conductance_uS'].median(),
                'FAA': ffa_output.get(faa_headers[n-1], np.nan),
            })

                    
        stats_df = pd.DataFrame(stats_rows)

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)

        logger.info("Stats generated and saved successfully to %s", stat_file_name)
    else:
        logger.info("Stats path %s already exists. Exiting.", excel_path)

def generate_statistics_masterarbeit(segments, ffa_output, merged_file_path):
    # ----- Compute statistics and save to Excel -----
    subj_name = os.path.basename(os.path.dirname(merged_file_path))
    stat_file_name = f'statistics_{os.path.basename(os.path.dirname(merged_file_path))}_{subj_name}.xlsx'
    # Save statistics to Excel
    excel_path = os.path.join(os.path.dirname(merged_file_path), stat_file_name)
    if not os.path.exists(excel_path):
        stats_rows = []

        faa_headers = ['FAA_pre', '-', '-', 'FAA_post']
        marker_translations = ['Pre (Trigger 1)', 'Application (Trigger 3)', 'CPT (Trigger 4)', 'Post (Trigger 2)']
        for n, seg in enumerate(segments, start=1):
            df_win = seg['data']

            # for var in variables:
            stats_rows.append({
                'Timepoint': marker_translations[n-1],
                'BPM': df_win['BPM'].median(),
                'Skin_conductance_uS': df_win['Skin_conductance_uS'].median(),
                'FAA': ffa_output.get(faa_headers[n-1], np.nan),
            })

                    
        stats_df = pd.DataFrame(stats_rows)

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)

        logger.info("Stats generated and saved successfully to %s", stat_file_name)
    else:
        logger.info("Stats path %s already exists. Exiting.", excel_path)

if __name__ == "__main__":
    # TODO: broken __main__ block removed (imported from non-existent 'super' package).
    # See refactoring_report.md for details.
    pass