import os
import pandas as pd

# Define the paths to the two folders
folder1 = "data/eeg_study/stats/finalise_temp"
folder2 = "data/eeg_study/stats/finalise_comp"

# List Excel files in each folder and extract numeric IDs
files1 = {int(os.path.splitext(f)[0].split("_")[-1]): os.path.join(folder1, f)
          for f in os.listdir(folder1) if f.split("_")[-1].replace(".xlsx", "").isdigit()}

files2 = {int(os.path.splitext(f)[0].split("_")[-1]): os.path.join(folder2, f)
          for f in os.listdir(folder2) if f.split("_")[-1].replace(".xlsx", "").isdigit()}

# Get common patient IDs
common_ids = sorted(set(files1.keys()) & set(files2.keys()))

# Compare files
for pid in common_ids:
    print(f"\nComparing Patient ID {pid}:")
    df1 = pd.read_excel(files1[pid])
    df2 = pd.read_excel(files2[pid])
    
    # Ensure both dataframes have the same shape
    if df1.shape != df2.shape:
        print("  ❌ Files have different shapes")
        continue

    # Optional: Ensure same column order and labels
    if not df1.columns.equals(df2.columns):
        print("  ❌ Files have different columns")
        continue
    # Keep only numeric columns
    numeric_cols = df1.select_dtypes(include='number').columns

    # Subtract only numeric columns
    diff = df2[numeric_cols].subtract(df1[numeric_cols])

    if diff.abs().sum().sum() == 0:
        print("  ✅ No differences found")
    else:
        print("  ⚠️ Differences found:")
        print(diff)
