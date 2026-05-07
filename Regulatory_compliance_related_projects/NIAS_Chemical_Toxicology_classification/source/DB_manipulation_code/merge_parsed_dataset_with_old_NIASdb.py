import pandas as pd

# --- Configuration ---
# Update the file names and sheet names if necessary
file_sheet1 = r"path\to\NIAS_DB_FILLED_output.xlsx"   # File for Sheet 1
file_sheet2 = r"path\to\output_ALL.xlsx"               # File for Sheet 2

sheet1_name = "DB_data"         # Sheet name in file_sheet1
sheet2_name = "Doc_data"             # Sheet name in file_sheet2

# --- Read Excel Sheets ---
df1 = pd.read_excel(file_sheet1, sheet_name=sheet1_name)
df2 = pd.read_excel(file_sheet2, sheet_name=sheet2_name)

# Ensure the common key column is treated as string (in case of leading zeros, etc.)
df1["CAS"] = df1["CAS"].astype(str)
df2["cas"] = df2["cas"].astype(str)

# --- Process Each Row from Sheet 2 ---
# We will iterate through df2 (Output_ALL) and update or add rows in df1 (NIAS_DB_FILLED)
for _, row in df2.iterrows():
    cas = row["cas"]
    language = str(row["language"]).strip().upper()  # Normalize language (EN or DE)
    if str(row["ft_text"]) != 'nan':
        ft_list = eval(row["ft_text"])# throws out a list
    else:
        ft_list = [str(row["ft_text"])]
    cramer_val = row["cramer"]
    name_val = row["substance_name"]  # This name will go to IUPAC_EN or IUPAC_DE if a new row is needed
    ttype = row["template_type"]
    path = row["path"]
    classification = row["classification"]


    # Identify rows in df1 that match the cas number
    for ft in ft_list:
        matching = df1["CAS"] == cas

        if matching.any():
            # If matching cas number found in df1, update the corresponding FT and Creamer fields.
            if language == "EN":
                # Update FT_EN only if it's empty (NaN or an empty string)
                condition = matching & (df1["FT_EN"].isna() | (df1["FT_EN"] == "") | (df1["FT_EN"] == "[]"))
                if condition.any():
                    # update the first instance
                    df1.loc[condition, "FT_EN"] = ft
                    df1.loc[condition, "FT_DE"] = ""
                    # Update the Creamer column (applied to all matching rows)
                    df1.loc[matching, "Cramer"] = cramer_val
                    df1.loc[matching, "CL_EN"] = classification
                    df1.loc[matching, "CL_DE"] = ""
                    df1.loc[matching, "Language"] = language
                    df1.loc[matching, "TypeFlag"] = ttype
                    df1.loc[matching, "Path"] = path

                else:
                    # --- Add line: Copy the last matching row, update FT_EN and append as a new row ---
                    last_index = df1[matching].tail(1).index[0]
                    new_row = df1.loc[last_index].copy()
                    new_row["FT_EN"] = ft
                    new_row["FT_DE"] = ""
                    new_row["Cramer"] = cramer_val
                    new_row["CL_EN"] = classification
                    new_row["CL_DE"] = ""
                    new_row["Language"] = language
                    new_row["TypeFlag"] = ttype
                    new_row["Path"] = path
                    df1 = pd.concat([df1, pd.DataFrame([new_row])], ignore_index=True)

            elif language == "DE":
                # Update FT_DE if empty
                condition = matching & (df1["FT_DE"].isna() | (df1["FT_DE"] == "") | (df1["FT_DE"] == "[]"))
                if condition.any():
                    df1.loc[condition, "FT_DE"] = ft
                    df1.loc[condition, "FT_EN"] = ""
                    df1.loc[matching, "Cramer"] = cramer_val
                    df1.loc[matching, "CL_DE"] = classification
                    df1.loc[matching, "CL_EN"] = ""
                    df1.loc[matching, "Language"] = language
                    df1.loc[matching, "TypeFlag"] = ttype
                    df1.loc[matching, "Path"] = path

                else:
                    # If FT_DE is already filled in all matching rows, you could add a similar "copy row" logic here.
                    last_index = df1[matching].tail(1).index[0]
                    new_row = df1.loc[last_index].copy()
                    new_row["FT_DE"] = ft
                    new_row["FT_EN"] = ""
                    new_row["Cramer"] = cramer_val
                    new_row["CL_DE"] = classification
                    new_row["CL_EN"] = ""
                    new_row["Language"] = language
                    new_row["TypeFlag"] = ttype
                    new_row["Path"] = path
                    df1 = pd.concat([df1, pd.DataFrame([new_row])], ignore_index=True)
            # (Optionally, you could also update IUPAC_EN/DE for existing rows if desired.)
        else:
            # If the cas number does not exist in df1, create a new row.
            cas = "-" if "$" in cas else cas
            new_row = {"CAS": cas, "Cramer": cramer_val}

            if language == "EN":
                new_row["FT_EN"] = ft
                new_row["IUPAC_EN"] = name_val
                # Initialize the DE fields as empty
                new_row["FT_DE"] = ""
                new_row["IUPAC_DE"] = ""
                new_row["CL_DE"] = classification
                new_row["Language"] = language
                new_row["TypeFlag"] = ttype
                new_row["Path"] = path
            elif language == "DE":
                new_row["FT_DE"] = ft
                new_row["IUPAC_DE"] = name_val
                new_row["CL_EN"] = classification
                new_row["FT_EN"] = ""
                new_row["IUPAC_EN"] = ""
                new_row["Language"] = language
                new_row["TypeFlag"] = ttype
                new_row["Path"] = path
            else:
                # In case language is neither EN nor DE, you might choose to skip or log a warning.
                print(f"Warning: Language '{language}' not recognized for cas number {cas}. Skipping row.")
                continue

            # Append the new row to df1.
            df1 = pd.concat([df1, pd.DataFrame([new_row])], ignore_index=True)

# --- Write Updated DataFrame to a New Excel File ---
output_file = "NIAS_DB_FILLED_updated.xlsx"
df1.to_excel(output_file, index=False)
print(f"Updated data written to {output_file}")
