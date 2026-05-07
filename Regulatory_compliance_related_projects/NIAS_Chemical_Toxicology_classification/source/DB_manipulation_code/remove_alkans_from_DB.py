import pandas as pd


def is_alkan(smiles: str) -> bool | None:
    """
    Determines if the given SMILES string represents an alkane molecule.
    """
    if smiles is None:
        return None

    # Remove characters that are part of standard alkane SMILES
    smiles_r = smiles.replace('C', '').replace('(', '').replace(')', '').replace('1', '')

    # Check if the resulting string is empty
    return len(smiles_r) == 0

def highlight_alkanes(input_file, output_file):
    # Read the Excel file
    df = pd.read_excel(input_file, dtype=str)

    # Apply alkane check only for non-empty SMILES codes
    if "SMILES" in df.columns:
        df["Is_Alkane"] = df["SMILES"].apply(lambda x: is_alkan(x) if pd.notna(x) and x.strip() != "" else None)
        df["Highlight"] = df["Is_Alkane"].map(lambda x: "background-color: yellow" if x else "")

    # Save the highlighted file
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        highlight_format = workbook.add_format({'bg_color': 'yellow'})
        for row in range(1, len(df) + 1):
            if df.loc[row - 1, "Is_Alkane"]:
                worksheet.set_row(row, None, highlight_format)

# Update these paths to point to your local input and output files.
input_file = r"path\to\NIAS_ZDB_cleaned.xlsx"   # Change this to your actual input file
output_file = r"path\to\NIAS_ZDB_alkanes_removed.xlsx"  # Change this to your desired output file

highlight_alkanes(input_file, output_file)
