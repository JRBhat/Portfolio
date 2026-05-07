import logging
import pandas as pd
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Remap specific marker codes before sequential renumbering.
# Markers 2 and 3 are relabelled to 8 and 9 to distinguish them from
# the 1-7 range used by the sequential renumber step.
MARKER_REMAP = {2: 8, 3: 9}


def extract_and_serialize_marker_ones(file_path):
    """
    Correct marker codes in a merged EEG-GSR Excel file and write the result
    to a new ``*_markers_corrected.xlsx`` file beside the original.

    Processing steps:

    1. **Remap** markers 2 → 8 and 3 → 9 (using :data:`MARKER_REMAP`) so that
       they are not accidentally renumbered in the next step.
    2. **Sequential renumber** all remaining markers in the range 1–7 (excluding
       the just-remapped 8/9 codes) with serial integers starting at 1, in
       row order.

    Side-effect:
        Writes ``<file_path without .xlsx>_markers_corrected.xlsx``.

    Returns:
        str: Path to the newly written (or pre-existing) corrected file.
    """
    outpath = file_path.replace(".xlsx", "_markers_corrected.xlsx")
    if not os.path.exists(outpath):
        # Determine file type and load accordingly
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format. Use CSV or Excel.")

        # Ensure required columns exist
        if "marker" not in df.columns or "timestamp" not in df.columns:
            raise ValueError("File must contain 'Markers' and 'Timepoint' columns.")

        # Step 1: Vectorised remap using MARKER_REMAP constant
        for src, dst in MARKER_REMAP.items():
            df.loc[df["marker"] == src, "marker"] = dst

        # Step 2: Sequential renumber of markers 1-7 (8/9 already excluded above)
        num = 1
        for i in df.index:
            marker = df.at[i, "marker"]
            try:
                marker_int = int(marker)
                if marker_int != 0 and 1 <= marker_int <= 7:
                    df.at[i, "marker"] = num
                    num += 1
            except (ValueError, TypeError):
                continue

        df.to_excel(outpath, index=False)
        logger.info("Updated Excel file saved to: %s", outpath)
        return outpath
    else:
        logger.info("%s already exists.", outpath)
        logger.info("Skipping extraction and serialization and proceeding to plotting calculation...")
        return outpath

def main():
    input_file = "data/eeg_study/subject_001/merged_highlighted_subject_001_bpmcorrected.xlsx"
    out_path = extract_and_serialize_marker_ones(input_file)

if __name__ == "__main__":
    main()
