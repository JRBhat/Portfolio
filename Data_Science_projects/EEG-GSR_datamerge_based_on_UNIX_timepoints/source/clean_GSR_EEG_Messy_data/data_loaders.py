import pandas as pd
import numpy as np


def load_eeg_easy_file(file_path):
    """
    Load EEG .easy file (TSV), skip first row.
    Uses the last column as UNIX timestamps.
    """
    # Use error_bad_lines=False / on_bad_lines='skip' (newer pandas)
    df = pd.read_csv(file_path, sep="\t", header=None, skiprows=1, engine="python",
                     on_bad_lines='skip')  # skip malformed rows

    # Ensure there is at least one column
    if df.shape[1] < 1:
        raise ValueError(f"No valid columns found in {file_path}")

    ts = df.iloc[:, -1].astype(float).values
    return np.sort(ts)



import pandas as pd
import numpy as np

def read_shimmer_file(file_path):
    """
    Reads a Shimmer GSR file and returns only the timestamp column as a NumPy array.
    Handles both 'sep=' lines and decimal point formatting.
    """
    # Open file and read first line to detect separator
    with open(file_path, 'r') as f:
        first_line = f.readline().strip()
        second_line = f.readline().strip()  # usually units
    
    # Detect separator
    if first_line.startswith("sep="):
        sep = first_line.split('=')[1]
    elif ';' in first_line:
        sep = ';'
    else:
        sep = '\t'
    
    # Read the file as strings (no header)
    df = pd.read_csv(file_path, sep=sep, engine='python', header=None, dtype=str, skiprows=3)
    
    # Keep only the first column (timestamps)
    ts_col = df.iloc[:, 0]
    
    # Convert to float (replace commas if any)
    ts_col = ts_col.str.replace(',', '.', regex=False).astype(float)
    
    # Return as NumPy array
    return ts_col.to_numpy()

# def read_shimmer_file(file_path):
#     """
#     Reads a Shimmer GSR sensor data file (two formats):
#     - Format 1: semicolon-separated, decimal comma
#     - Format 2: tab-separated, optional "sep=" header, decimal point
    
#     Returns:
#         ts_array: NumPy array of float timestamps
#     """
#     # Open file and read first two lines
#     with open(file_path, 'r') as f:
#         first_line = f.readline().strip()
#         second_line = f.readline().strip()
    
#     # Detect format
#     if first_line.startswith("sep="):
#         sep = first_line.split('=')[1]
#         decimal_comma = False
#     elif ';' in first_line:
#         sep = ';'
#         decimal_comma = True
#     else:
#         sep = '\t'
#         decimal_comma = False
    
#     # Read file into DataFrame without skipping rows
#     df = pd.read_csv(file_path, sep=sep, engine='python', header=None, dtype=str)
    
#     # Replace comma with dot if needed
#     if decimal_comma:
#         df = df.applymap(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
    
#     # Keep only numeric rows (skip headers/units)
#     df_numeric = df[pd.to_numeric(df.iloc[:, 0], errors='coerce').notna()]
    
#     # Convert first column to float
#     ts_array = df_numeric.iloc[:, 0].astype(float).to_numpy()
    
#     return ts_array



