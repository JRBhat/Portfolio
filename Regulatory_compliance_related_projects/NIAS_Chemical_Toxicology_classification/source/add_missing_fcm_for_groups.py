import pandas as pd
import re

def is_fcm_group(smiles):
    if smiles is None:
        return None

    m = re.match(r'^C+\(=O\)OC+\(C+\)C+$', smiles)
    if m:
        return 878

    m = re.match(r'^C+OC\(=O\)C+\(?C+\)?C+$', smiles)
    if m:
        return 879

    m = re.match(r'^C+\(=O\)OC+$', smiles)
    if m:
        return 879

    m = re.match(r'^C{4,24}O$', smiles)
    if m:
        return 13

    m = re.match(r'^C{12,20}N(C)C$', smiles)
    if m:
        return 15

    return None

def update_fcm_column(file_path, output_file):
    df = pd.read_excel(file_path)

    if 'SMILES' not in df.columns or 'FCM' not in df.columns:
        raise ValueError("Excel file must contain 'SMILES' and 'FCM' columns")

    for index, row in df.iterrows():
        if pd.isna(row['FCM']):  # Update only if FCM column is empty
            fcm_value = is_fcm_group(str(row['SMILES']))
            if fcm_value is not None:
                df.at[index, 'FCM'] = str(fcm_value)

    df.to_excel(output_file, index=False)
    print(f"Updated file saved as: {output_file}")

# Update these paths to point to your local input and output files.
update_fcm_column(r"path\to\NIAS_ZDB_stereo_removed.xlsx",
                  r"path\to\NIAS_ZDB_fcms_added.xlsx")
