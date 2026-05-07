import pandas as pd
import sys

# Usage: python add_additional_substances_from_befund.py
# Update the file paths below to point to your local copies of the input files.
INPUT_DB_FILE = r"path\to\NIAS_ZDB.xlsx"          # Primary NIAS substance database
INPUT_BEFUND_FILE = r"path\to\Befund_CAS_NIAS.xlsx"  # File containing additional CAS entries

# Read the Excel files into DataFrames
df_file1 = pd.read_excel(INPUT_DB_FILE)
df_file2 = pd.read_excel(INPUT_BEFUND_FILE)


# Convert the 'CAS' columns to strings and remove leading zeros
df_file1['CAS'] = df_file1['CAS'].astype(str).str.lstrip('0')
df_file2['CAS'] = df_file2['CAS'].astype(str).str.lstrip('0')

# Create sets of CAS numbers for both files
file1_cas = set(df_file1['CAS'])
file2_cas = set(df_file2['CAS'])

# Identify the CAS numbers that are present in file 2 but missing in file 1
missing_cas = file2_cas - file1_cas

# If there are any missing CAS numbers, prepare new rows to append to file 1
if missing_cas:
    new_rows = []
    # For each missing CAS, retrieve the corresponding IUPAC_EN from file2
    for cas in missing_cas:
        # Get the first occurrence of IUPAC_EN for this CAS in file2 (if available)
        iupac_val = df_file2.loc[df_file2['CAS'] == cas, 'IUPAC_EN'].iloc[0] if not df_file2.loc[df_file2['CAS'] == cas, 'IUPAC_EN'].empty else None

        # Create a new row with all columns set to None by default
        new_row = {col: None for col in df_file1.columns}
        # Set the CAS and IUPAC_EN values for the new row
        new_row['CAS'] = cas
        new_row['IUPAC_EN'] = iupac_val
        new_rows.append(new_row)

    # Convert the list of new rows into a DataFrame with the same columns as file1
    df_new = pd.DataFrame(new_rows, columns=df_file1.columns)

    # Append the new rows to the original file1 DataFrame
    df_file1 = pd.concat([df_file1, df_new], ignore_index=True)

# Save the updated DataFrame to a new Excel file
df_file1.to_excel('file1_updated.xlsx', index=False)
