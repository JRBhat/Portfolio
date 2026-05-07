import pandas as pd

# Update this path to point to your local copy of the COSING Ingredients/Fragrance Inventory Excel file.
# The file can be downloaded from the EU COSING database portal.
input_file = r"path\to\COSING_Ingredients_Fragrance_Inventory.xlsx"  # Change this to your actual file
df = pd.read_excel(input_file)

# Extract and process the "Function" column
unique_values = set()
if "Function" in df.columns:
    for values in df["Function"].dropna():
        unique_values.update(values.split(", "))

# Convert to DataFrame and save as an Excel file
output_df = pd.DataFrame({"Unique Functions": sorted(unique_values)})
output_file = r"path\to\COSING_List_of_functions.xlsx"
output_df.to_excel(output_file, index=False)

print(f"Unique values saved to {output_file}")
