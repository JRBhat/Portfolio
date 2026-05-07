import logging
import os
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

logger = logging.getLogger(__name__)


def generate_final_collated_stat_file(base_dir, out_dir, measured_variables, max_cols=5, subplot_width=5, subplot_height=4):
    all_rows = []
    bpm_images = []
    sc_images = []

    # ------------------------------
    # Collect stats and images
    # ------------------------------
    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)

        if not os.path.isdir(folder_path):
            continue
        if "_" not in folder or not folder[:2].isdigit():
            continue

        subject_id = folder

        # --- Locate statistics file ---
        stats_file = None
        for f in os.listdir(folder_path):
            if f.lower().startswith("statistics_") and f.lower().endswith(".xlsx"):
                stats_file = os.path.join(folder_path, f)
                break

        if stats_file is None:
            logger.warning("No statistics file found in %s", folder)
            continue

        # --- Locate BPM and Skin_conductance images (PNG) ---
        bpm_file = None
        sc_file = None
        for f in os.listdir(folder_path):
            if f.startswith("BPM") and f.lower().endswith(".png"):
                bpm_file = os.path.join(folder_path, f)
            if f.startswith("Skin_conductance_uS") and f.lower().endswith(".png"):
                sc_file = os.path.join(folder_path, f)

        if bpm_file:
            bpm_images.append((subject_id, bpm_file))
        if sc_file:
            sc_images.append((subject_id, sc_file))

        # --- Read Excel ---
        df = pd.read_excel(stats_file)
        for col in measured_variables:
            if col in df.columns:
                df[col] = (df[col].astype(str)
                                    .str.replace(",", ".")
                                    .replace("nan", None)
                                    .astype(float))
        df["Subj_id"] = subject_id
        all_rows.append(df)

    # ------------------------------
    # Merge Statistics
    # ------------------------------
    if not all_rows:
        raise RuntimeError("No valid statistics files found!")

    final_df = pd.concat(all_rows, ignore_index=True)
    final_df = final_df[["Subj_id", "Timepoint", "BPM", "Skin_conductance_uS", "FAA"]]

    
    final_df.to_excel(out_dir, index=False)
    logger.info("Final statistics saved: %s", out_dir)

    # ------------------------------
    # Build auto-scaled grid PNG
    # ------------------------------
    def build_grid_png(image_list, output_name):
        if len(image_list) == 0:
            logger.warning("No images found for %s, skipping.", output_name)
            return

        num_images = len(image_list)

        # Auto-adjust columns and rows
        cols = min(max_cols, math.ceil(math.sqrt(num_images)))
        rows = math.ceil(num_images / cols)

        fig, axes = plt.subplots(rows, cols, figsize=(cols*subplot_width, rows*subplot_height))

        # Flatten axes for easy iteration
        if rows == 1 and cols == 1:
            axes = [axes]
        elif rows == 1 or cols == 1:
            axes = axes.flatten()
        else:
            axes = [ax for row_ax in axes for ax in row_ax]

        # Plot each image
        for ax, (subject_id, img_path) in zip(axes, image_list):
            img = mpimg.imread(img_path)
            ax.imshow(img)
            ax.set_axis_off()
            ax.set_title(subject_id, fontsize=12)

        # Hide unused axes
        for ax in axes[len(image_list):]:
            ax.set_axis_off()

        plt.tight_layout()
        output_png = os.path.join(base_dir, output_name)
        plt.savefig(output_png, format="png", dpi=200)
        plt.close()
        logger.info("Saved grid PNG: %s", output_png)

    # ------------------------------
    # Build both grids
    # ------------------------------
    build_grid_png(bpm_images, "all_subjects_BPM_grid.png")
    build_grid_png(sc_images, "all_subjects_Skin_conductance_uS_grid.png")


if __name__ == "__main__":
    BASE_DIR = "data/thesis_study/test"  # <-- change this
    OUT_DIR = "data/thesis_study/test/final_statistics_TEST.xlsx"  # <-- change this
    NUM_COLS = ["BPM", "Skin_conductance_uS", "FAA"]
    generate_final_collated_stat_file(BASE_DIR, OUT_DIR, NUM_COLS)
