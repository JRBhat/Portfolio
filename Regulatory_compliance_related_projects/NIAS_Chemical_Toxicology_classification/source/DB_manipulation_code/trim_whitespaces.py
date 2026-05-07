import pandas as pd

def trim_excel_spaces(input_file, output_file):
    # Read the Excel file
    df = pd.read_excel(input_file, dtype=str)  # Read all data as strings to preserve formatting

    # Trim spaces from all non-empty cells
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # Save the cleaned data to a new Excel file
    df.to_excel(output_file, index=False)

# Update these paths to point to your local input and output files.
input_file = r"path\to\NIAS_ZDB_cleaned.xlsx"   # Change this to your actual input file
output_file = r"path\to\NIAS_ZDB_cleaned_output.xlsx"  # Change this to your desired output file
trim_excel_spaces(input_file, output_file)


# TODO: stereochemie raus nehmen - REGEX([0-9,()])
