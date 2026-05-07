import pandas as pd
import re

def extract_hazard_codes(text):
    if pd.isna(text):
        return "-"
    codes = re.findall(r"H\d{2,3}[a-zA-Z]*:", text)
    return (", ".join(codes) if codes else "-").replace(":", "")

def merge_codes(row, eng_col_code, ger_col_code):
    codes_eng = row[eng_col_code]
    codes_ger = row[ger_col_code]

    # Create a list of codes, ignoring "-" which means no codes found.
    codes = []
    if codes_eng != "-" and codes_eng:
        codes.extend(codes_eng.split(", "))
    if codes_ger != "-" and codes_ger:
        codes.extend(codes_ger.split(", "))

    return ", ".join(codes) if codes else "-"


def process_excel(input_file, output_file, eng_col, ger_col):
    # Load Excel file
    df = pd.read_excel(input_file, engine='openpyxl')

    # Extract hazard codes
    eng_codes_col = f"{eng_col} Codes"
    ger_codes_col = f"{ger_col} Codes"
    df[eng_codes_col] = df[eng_col].apply(extract_hazard_codes)
    df[ger_codes_col] = df[ger_col].apply(extract_hazard_codes)

    # Merge the English and German hazard codes into one column
    df["Hazard codes"] = df.apply(lambda row: merge_codes(row, eng_codes_col, ger_codes_col), axis=1)

    # Save to a new Excel file
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"Processed file saved as: {output_file}")


def main():
    # Update these paths to point to your local input and output files.
    input_file = r"path\to\NIAS_DB_FILLED_updated_duplicates_removed.xlsx"   # Change this to your actual file name
    output_file = r"path\to\NIAS_DB_FILLED_updated_parsedHazards.xlsx"
    english_column = "FT_EN"  # Change this to your actual column name
    german_column = "FT_DE"    # Change this to your actual column name

    process_excel(input_file, output_file, english_column, german_column)

if __name__ == "__main__":
    main()
