import pandas as pd
import ast

def expand_lists_in_fts(cell):
    """
    If cell is a list-like string (e.g., "['item1', 'item2']") or already a list,
    return the list; otherwise, return the cell as-is.
    """
    if isinstance(cell, list):
        return cell
    if isinstance(cell, str):
        cell = cell.strip()
        # Check if the string starts with [ and ends with ]
        if cell.startswith('[') and cell.endswith(']'):
            try:
                parsed = ast.literal_eval(cell)
                if isinstance(parsed, list):
                    return parsed
            except Exception as e:
                print(f"Warning: Could not parse cell: {cell}. Error: {e}")
    return cell

# Update this path to point to your local copy of the NIAS database Excel file.
input_file = r"path\to\NIAS_DB_FILLED.xlsx"
df = pd.read_excel(input_file)

# --- Step 1: Process Classification Columns ---
# For columns CL_DE and CL_EN, if the cell is a list, join its items with newline characters.
for col in ["CL_DE", "CL_EN"]:
    if col in df.columns:
        df[col] = df[col].apply(
            lambda cell: "\n".join(expand_lists_in_fts(cell)) if isinstance(expand_lists_in_fts(cell), list) else cell
        )

# --- Step 2: Expand Rows for Footnotes ---
def expand_footnotes(row):
    """
    For a given row, if FT_DE and/or FT_EN contain lists,
    return a list of rows (as Series) where each row has one footnote item.
    If a footnote cell is not a list, it is wrapped in a one-item list.

    Ensures that if a footnote list is empty, it still returns one row.
    """
    # Process FT_DE and FT_EN using the expand_lists_in_fts function
    ft_de = expand_lists_in_fts(row["FT_DE"]) if "FT_DE" in row else row.get("FT_DE", None)
    ft_en = expand_lists_in_fts(row["FT_EN"]) if "FT_EN" in row else row.get("FT_EN", None)

    # If neither cell is a list, simply return the original row
    if not (isinstance(ft_de, list) or isinstance(ft_en, list)):
        return [row]

    # Ensure both are lists (wrap non-list values in a list)
    ft_de_list = ft_de if isinstance(ft_de, list) else [ft_de]
    ft_en_list = ft_en if isinstance(ft_en, list) else [ft_en]

    # If a list is empty, replace it with a list containing an empty string
    if len(ft_de_list) == 0:
        ft_de_list = ['']
    if len(ft_en_list) == 0:
        ft_en_list = ['']

    # Determine the number of new rows to create (using the maximum list length)
    count = max(len(ft_de_list), len(ft_en_list))

    new_rows = []
    for i in range(count):
        new_row = row.copy()
        new_row["FT_DE"] = ft_de_list[i] if i < len(ft_de_list) else ''
        new_row["FT_EN"] = ft_en_list[i] if i < len(ft_en_list) else ''
        new_rows.append(new_row)
    return new_rows

# Build a new DataFrame with expanded footnotes.
expanded_rows = []
for _, row in df.iterrows():
    expanded_rows.extend(expand_footnotes(row))

df_expanded = pd.DataFrame(expanded_rows)

# --- Step 3: Row Count Check and Save to Excel ---
original_row_count = len(df)
new_row_count = len(df_expanded)
print(f"Original number of rows: {original_row_count}")
print(f"New number of rows: {new_row_count}")

output_file = r"path\to\NIAS_DB_FILLED_output.xlsx"
df_expanded.to_excel(output_file, index=False)
print(f"Processing complete. Output saved to {output_file}")
