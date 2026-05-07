import os
import pandas as pd
import numpy as np
import re

# Define CAS validation function
def validate_cas(cas):
    """Validate a CAS number using its check digit."""
    cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
    if cas_pattern.match(str(cas)):
        positions = np.arange(9, -1, -1)
        ziffern = np.array(list(f"{int(''.join(cas.split('-'))):010d}"), dtype=int)
        betrag = positions[:-1] * ziffern[:-1]
        return int(np.sum(betrag) % 10) == ziffern[-1]
    return False

# Load Excel file
df = pd.read_excel(os.environ.get("BEFUND_CAS_FILE_PATH", "data/ZDB_main/Befunde_CAS_NIAS.xlsx"))

# Validate CAS numbers and filter invalid ones
df['CAS_valid'] = df['CAS'].apply(validate_cas)
bad_cas_df = df[~df['CAS_valid']].drop(columns='CAS_valid')

# Save bad CAS entries to new Excel file
bad_cas_df.to_excel('bad_Cas.xlsx', index=False)

print(f"Found {len(bad_cas_df)} invalid CAS entries. Saved to 'bad_Cas.xlsx'.")
