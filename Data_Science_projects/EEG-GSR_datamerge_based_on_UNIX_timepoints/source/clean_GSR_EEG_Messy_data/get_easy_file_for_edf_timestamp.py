import os
import re
from openpyxl import Workbook

def extract_timestamp(filename: str) -> str | None:
    """Extract timestamp from filename like: 20250523093747_01d2_main.edf"""
    match = re.match(r"(\d{14})_", filename)
    if match:
        return match.group(1)
    return None


def find_matching_easy_files(edf_folder: str, search_folder: str, output_excel: str):
    """
    1. Read all .edf files from `edf_folder`
    2. Extract timestamps
    3. Search for .easy files in `search_folder` and subfolders
    4. Only match .easy files with same timestamp
    5. Save results to Excel
    """

    print(f"\n📂 EDF folder: {edf_folder}")
    print(f"🔍 Search folder for .easy files: {search_folder}\n")

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "EDF & EASY Matches"
    ws.append(["EDF File Name", "EDF Full Path", "Timestamp", "EASY File Name", "EASY Full Path"])

    # Step 1: Read all EDF files
    edf_files = []
    for file in os.listdir(edf_folder):
        if file.lower().endswith(".edf"):
            edf_path = os.path.join(edf_folder, file)
            edf_files.append(edf_path)
            print(f"✅ Found EDF: {edf_path}")

    if not edf_files:
        print("❌ No EDF files found in input folder.")
        return

    print(f"\n📁 Total EDF files found: {len(edf_files)}")

    # Step 2: Process each EDF
    for edf_path in edf_files:
        edf_filename = os.path.basename(edf_path)
        print("\n" + "="*70)
        print(f"📄 Processing: {edf_filename}")

        timestamp = extract_timestamp(edf_filename)
        if not timestamp:
            print("⚠️ Could not extract timestamp — skipping.")
            ws.append([edf_filename, edf_path, "NO TIMESTAMP", "SKIPPED", "SKIPPED"])
            continue

        print(f"🕒 Extracted timestamp: {timestamp}")

        # Step 3: Search for matching .easy files
        matches = []
        for root, _, files in os.walk(search_folder):
            for file in files:
                if file.lower().endswith(".easy") and timestamp in file:
                    full_path = os.path.join(root, file)
                    matches.append(full_path)
                    print(f"🎯 Match found: {full_path}")

        # Step 4: Write to Excel
        if matches:
            for match_path in matches:
                ws.append([edf_filename, edf_path, timestamp, os.path.basename(match_path), match_path])
            print(f"✅ Total .easy matches found: {len(matches)}")
        else:
            ws.append([edf_filename, edf_path, timestamp, "NO MATCH", "NO MATCH"])
            print("❌ No matching .easy files found.")

    # Save Excel
    wb.save(output_excel)
    print(f"\n📊 Excel results saved at: {output_excel}")
    print("\n✅ Done scanning all EDF files.")


# -------------------------
# USAGE
# -------------------------
edf_input_folder = "data/thesis_study/mixed_data"       # folder containing only EDF files
search_folder = "data/thesis_study/raw_gsr_eeg"             # folder to search recursively for .easy
output_excel_file = "data/thesis_study/mixed_data/edf_easy_results.xlsx"

find_matching_easy_files(edf_input_folder, search_folder, output_excel_file)
