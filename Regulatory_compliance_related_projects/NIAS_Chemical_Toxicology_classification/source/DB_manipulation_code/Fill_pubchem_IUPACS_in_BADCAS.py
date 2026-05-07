import os
import pandas as pd
import time
import logging
from pathlib import Path
import shutil
from utilityFuncs.util import query_pubchem  # Ensure this is the correct import path for your utility function    
# Make sure your query_pubchem function is importable / defined in the same file/context.
# from your_module import query_pubchem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pubchem_updater")

# CONFIG: change these paths/names if needed
workbook_path = Path(os.environ.get("BADCAS_WORKBOOK_PATH", "data/ZDB_main/ALLBADCAS_merged.xlsx"))   # <-- change if your file has another name
sheet_name = "PUBCHEM_IUPAC_EN"                # <-- change if sheet name differs
backup_suffix = ".backup.xlsx"
sleep_between_requests = 0.2  # seconds (reduce hammering on PubChem)

def find_col(df, target):
    """Find a column name in df ignoring case; return original column name or None."""
    lookup = {c.lower(): c for c in df.columns}
    return lookup.get(target.lower())

def is_empty_cell(val):
    """Return True if cell is empty (NaN, None, or only whitespace)."""
    if pd.isna(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False

def update_iupac_en_in_sheet(workbook_path: Path, sheet_name: str):
    if not workbook_path.exists():
        raise FileNotFoundError(f"{workbook_path} does not exist")

    # backup original file
    backup_path = workbook_path.with_name(workbook_path.stem + backup_suffix)
    shutil.copy2(workbook_path, backup_path)
    logger.info(f"Backup of workbook saved to: {backup_path}")

    # read sheet as strings to avoid dtype surprises
    df = pd.read_excel(workbook_path, sheet_name=sheet_name, dtype=str)

    # find columns (case-insensitive)
    trivial_col = find_col(df, "Trivial_Name")
    iupac_col = find_col(df, "IUPAC_EN")
    if trivial_col is None:
        raise KeyError("Could not find 'Trivial_Name' column in the sheet.")
    if iupac_col is None:
        # option: create the column if missing
        logger.warning("IUPAC_EN column missing — creating it.")
        iupac_col = "IUPAC_EN"
        df[iupac_col] = ""

    n_rows = len(df)
    updated = 0
    skipped_no_name = 0
    failed = 0
    already_present = 0

    for idx, row in df.iterrows():
        trivial = row.get(trivial_col)
        if is_empty_cell(trivial):
            skipped_no_name += 1
            continue

        current_iupac = row.get(iupac_col)
        if not is_empty_cell(current_iupac):
            already_present += 1
            continue

        # call query_pubchem with query_type='name'
        try:
            # query_pubchem must be in scope
            result = query_pubchem(trivial, query_type="name", text_changed=None)
        except Exception as e:
            logger.exception(f"Query failed for '{trivial}': {e}")
            failed += 1
            # small pause before continuing
            time.sleep(sleep_between_requests)
            continue

        # If result is falsy (None or empty), skip
        if not result:
            logger.info(f"No result for '{trivial}'")
            failed += 1
            time.sleep(sleep_between_requests)
            continue

        # Look for possible IUPAC name keys (function returns "IUPAC" but we check a couple possibilities)
        found_iupac = result.get("IUPAC") or result.get("IUPACName") or result.get("IUPAC_Name")
        if found_iupac:
            df.at[idx, iupac_col] = found_iupac
            updated += 1
            logger.info(f"Updated row {idx}: Trivial='{trivial}' -> IUPAC_EN='{found_iupac}'")
        else:
            logger.info(f"Result for '{trivial}' contained no IUPAC name in returned data.")
            skipped_no_name += 1

        time.sleep(sleep_between_requests)

    # write updated sheet back to workbook, replacing only the sheet
    # requires pandas >= 1.4 for if_sheet_exists='replace'
    with pd.ExcelWriter(workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    logger.info("Write complete.")
    logger.info(
        f"Summary: rows={n_rows}, updated={updated}, already_present={already_present}, "
        f"skipped_no_name={skipped_no_name}, failed={failed}"
    )
    return {
        "rows": n_rows,
        "updated": updated,
        "already_present": already_present,
        "skipped_no_name": skipped_no_name,
        "failed": failed,
        "backup_path": str(backup_path)
    }

if __name__ == "__main__":
    summary = update_iupac_en_in_sheet(workbook_path, sheet_name)
    print("Done. Summary:", summary)
