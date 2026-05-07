import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)


def generate_final_collated_stat_file(base_dir, numeric_columns):

    # --- PROCESS ---
    all_rows = []

    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)

        # Only process directories like "01_C", "01_R", etc.
        if not os.path.isdir(folder_path):
            continue
        if "_" not in folder or not folder[:2].isdigit():
            continue

        subject_id = folder

        # Locate statistics file
        stats_file = None
        for f in os.listdir(folder_path):
            if f.lower().startswith("statistics_") and f.lower().endswith(".xlsx"):
                stats_file = os.path.join(folder_path, f)
                break

        if stats_file is None:
            logger.warning("No statistics file found in %s", folder)
            continue

        # Read Excel
        df = pd.read_excel(stats_file)

        # Replace commas with dots for numeric columns + convert to float
        for col in numeric_columns:
            if col in df.columns:
                df[col] = (df[col].astype(str)
                                    .str.replace(",", ".")
                                    .replace("nan", None)
                                    .astype(float))

        # Add subject ID
        df["Subj_id"] = subject_id

        all_rows.append(df)

    # Combine all subjects
    if not all_rows:
        raise RuntimeError("No valid statistics files found!")

    final_df = pd.concat(all_rows, ignore_index=True)

    # Reorder columns
    cols = ["Subj_id", "timepoint", "BPM", "Skin_conductance_uS", "FAA"]
    final_df = final_df[cols]
    OUTPUT_FILE = os.path.join(base_dir, "final_statistics.xlsx")
    
    # Save output
    final_df.to_excel(OUTPUT_FILE, index=False)

    logger.info("Done! Final file written to: %s", OUTPUT_FILE)


if __name__ == "__main__":
    
    
    # --- CONFIG ---
    BASE_DIR = "data/thesis_study/test"   # <-- change this


    # Which columns should be converted
    NUM_COLS = ["BPM", "Skin_conductance_uS", "FAA"]
    generate_final_collated_stat_file(BASE_DIR, NUM_COLS)
    