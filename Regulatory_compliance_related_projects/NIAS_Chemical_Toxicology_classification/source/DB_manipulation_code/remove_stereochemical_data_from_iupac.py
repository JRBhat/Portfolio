import pandas as pd
import re

# Define a regex pattern that matches the stereochemical prefix at the beginning.
# This pattern will:
# - Optionally match a leading dash and spaces.
# - Optionally match an opening square bracket.
# - Match an opening parenthesis.
# - Match any characters except a closing parenthesis.
# - Match the closing parenthesis.
# - Optionally match a hyphen.
# - Optionally match a closing square bracket.
# - Remove any extra whitespace at the start.
pattern = re.compile(r'^-?\s*(?:\[\s*)?\([^)]+\)-?(?:\])?\s*')

def remove_stereo(name):
    """Removes stereochemical information from the start of a name."""
    if pd.isnull(name):
        return name
    return re.sub(pattern, '', name)

# Update this path to point to your local input file.
df = pd.read_excel(r"path\to\output_ALL_with_stereo_clean.xlsx")

# Create new columns to store the original names
df['Substance_EN_original'] = df['Substance_EN']
df['Substance_DE_original'] = df['Substance_DE']

# Remove stereochemical prefixes from the substance name columns
df['Substance_EN'] = df['Substance_EN'].apply(remove_stereo)
df['Substance_DE'] = df['Substance_DE'].apply(remove_stereo)

# Save the cleaned DataFrame to a new Excel file
df.to_excel(r"path\to\output_ALL_stereo_removed_clean.xlsx", index=False)

print("Stereochemical information removed and new file saved.")
