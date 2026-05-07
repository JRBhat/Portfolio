import pandas as pd
import os

# Update this path to point to the directory containing your Excel files.
path = r"path\to\your\nias_data_directory"

df1 = pd.read_excel(os.path.join(path, "NIAS_ZDB.xlsx"), sheet_name="Main")
df2 = pd.read_excel(os.path.join(path, "NIAS_ZDB.xlsx"), sheet_name="Zusammenfuehren")

print("Columns in df1 but not in df2:", set(df1.columns) - set(df2.columns))
print("Columns in df2 but not in df1:", set(df2.columns) - set(df1.columns))

df1 = df1.sort_index(axis=1)  # Sort columns alphabetically
df2 = df2.sort_index(axis=1)

df1 = df1[df2.columns]  # Reorder df1 columns to match df2

common_cols = df1.columns.intersection(df2.columns)
df1 = df1[common_cols]
df2 = df2[common_cols]

print("Indexes in df1 but not in df2:", set(df1.index) - set(df2.index))
print("Indexes in df2 but not in df1:", set(df2.index) - set(df1.index))


df1 = df1.sort_index()
df2 = df2.sort_index()


df1 = df1.reset_index(drop=True)
df2 = df2.reset_index(drop=True)
# Find differences
diff = df1.compare(df2)

# Save differences to a new Excel file
diff.to_excel(os.path.join(path, "diff_output.xlsx"))

print("Comparison done. Check 'diff_output.xlsx'")

# If you want to check if the DataFrames are fully identical:
if df1.equals(df2):
    print("DataFrames are identical")
else:
    print("DataFrames are different")
