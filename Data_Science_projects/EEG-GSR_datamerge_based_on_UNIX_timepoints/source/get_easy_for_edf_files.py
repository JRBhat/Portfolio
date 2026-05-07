"""
EDF-to-EASY file pairing by 14-digit timestamp prefix.

Scans ``edf_folder`` for ``.edf`` files whose names start with a 14-digit
timestamp (e.g. ``20250523093747_…``), then looks up a matching ``.easy``
file in ``easy_folder`` whose name starts with the same timestamp.  Matched
pairs are copied to ``output_folder``.

Usage::

    python get_easy_for_edf_files.py
"""
import os
import re
import shutil

# --------- CONFIGURATION ---------
edf_folder = "data/thesis_study/EEG_raw"        # Folder containing .edf files
easy_folder = "data/thesis_study/NIC"      # Folder containing .easy files
output_folder = "data/thesis_study/EEG_raw_out"  # Folder to copy matched files into


if __name__ == "__main__":
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Regex pattern to extract the timestamp at the beginning
    pattern = re.compile(r"^(\d{14})_.*\.edf$", re.IGNORECASE)

    # Get list of .easy files for faster lookup
    easy_files = {os.path.splitext(f)[0].split('_')[0]: f for f in os.listdir(easy_folder) if f.lower().endswith('.easy')}

    # Iterate over .edf files
    for edf_file in os.listdir(edf_folder):
        match = pattern.match(edf_file)
        if match:
            timestamp_part = match.group(1)
            if timestamp_part in easy_files:
                # Found a matching .easy file
                edf_path = os.path.join(edf_folder, edf_file)
                easy_path = os.path.join(easy_folder, easy_files[timestamp_part])

                # Copy both files to the output folder
                shutil.copy(edf_path, os.path.join(output_folder, edf_file))
                shutil.copy(easy_path, os.path.join(output_folder, easy_files[timestamp_part]))
                print(f"Copied: {edf_file} and {easy_files[timestamp_part]}")
        else:
            print(f"No timestamp match for: {edf_file}")

    print("Done.")
