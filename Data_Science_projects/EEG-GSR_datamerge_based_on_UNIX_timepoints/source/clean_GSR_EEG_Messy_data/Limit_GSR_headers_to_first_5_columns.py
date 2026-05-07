import pandas as pd
from pathlib import Path

# ===== CONFIG =====
INPUT_DIR = Path("data/thesis_study/missing_gsr_data")     # folder with your original files
OUTPUT_DIR = Path("data/thesis_study/cleaned_excels")  # folder for cleaned files
OUTPUT_DIR.mkdir(exist_ok=True)

EXPECTED_COLUMNS = [
    "Shimmer_A5C7_TimestampSync_Unix_CAL",
    "Shimmer_A5C7_GSR_Range_CAL",
    "Shimmer_A5C7_GSR_Skin_Conductance_CAL",
    "Shimmer_A5C7_GSR_Skin_Resistance_CAL",
    "Shimmer_A5C7_PPG_A13_CAL"
]

for file in INPUT_DIR.glob("*.csv"):
    print(f"\nProcessing: {file.name}")

    try:
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # First line is: "sep=\t"
        sep_line = lines[0]

        # Header & units (tab separated)
        headers = lines[1].strip().split("\t")
        units = lines[2].strip().split("\t")

        # Keep only first 5 columns
        headers_5 = headers[:5]
        units_5 = units[:5]

        # Check headers match expected
        if headers_5 != EXPECTED_COLUMNS:
            print("❌ Column mismatch:")
            print("Found:   ", headers_5)
            print("Expected:", EXPECTED_COLUMNS)
            continue

        new_lines = []
        new_lines.append(sep_line)
        new_lines.append("\t".join(headers_5) + "\n")
        new_lines.append("\t".join(units_5) + "\n")

        # Process data rows
        for line in lines[3:]:
            values = line.strip().split("\t")[:5]
            new_lines.append("\t".join(values) + "\n")

        # Save with same name in output folder
        output_path = OUTPUT_DIR / file.name

        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print(f"✅ Saved: {output_path}")

    except Exception as e:
        print(f"⚠️ Error in {file.name}: {e}")
