"""
missing_substances_and_bad_cas_handling.py
==========================================
Handles substances whose CAS numbers are absent from, or mismatched with, the
NIAS substance database.

Overview
--------
Every run of the reporting pipeline may encounter substances that the laboratory
Excel file lists but the DB does not contain.  This module:

1. **Identifies missing substances** – iterates the list of lab substances and
   separates those whose (normalised) CAS is not in ``db_substances``.

2. **Queries PubChem** – calls :func:`~merging.fill_missing_data_by_queries` for
   each missing substance to attempt to retrieve a confirmed CAS, IUPAC name, and
   SMILES string from the PubChem REST API.

3. **Classifies the outcome** into one of five scenarios:

   +--------------------------------------------------+----------------------+
   | Scenario                                         | Destination sheet    |
   +==================================================+======================+
   | Invalid LAB_CAS, no PubChem hit                  | BAD_CAS_HANDLING     |
   | Invalid LAB_CAS, valid PubChem CAS found         | BAD_CAS_HANDLING     |
   | Valid LAB_CAS == PubChem CAS (exact match)       | READY_TO_MERGE_DB    |
   | Valid LAB_CAS ≠ PubChem CAS (mismatch)           | BAD_CAS_HANDLING     |
   | Valid LAB_CAS, no PubChem CAS returned           | BAD_CAS_HANDLING     |
   +--------------------------------------------------+----------------------+

4. **Writes output files**:
   - Updates the ``ALL_BAD_CAS`` sheet inside the NIAS DB Excel file.
   - Writes a timestamped debug Excel file (``missing_YYYYMMDD_HHMMSS.xlsx``)
     with three sheets: ``MISSING``, ``BAD_CAS_HANDLING``, and
     ``(FOR_USER)READY_TO_MERGE_DB``.

5. **Returns** the pre-existing ``ALL_BAD_CAS`` dictionary so the main merge step
   can remap mismatched CAS numbers.

Custom CAS Keys
---------------
When no valid PubChem CAS can be obtained, a synthetic wrapper key is generated:
- ``#<LAB_CAS>#<n>`` – for entirely invalid CAS numbers.
- ``&<LAB_CAS>#<n>`` – for valid LAB_CAS with no PubChem confirmation.

These keys are used as placeholders in the DB until a curator manually resolves them.
"""

import re
import os
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from merging import fill_missing_data_by_queries
from datetime import datetime
from utilityFuncs.util import validate_cas
import sys
import time

def save_new_substances_separately(
    xlsx_substance, db_substances, isd_cas_numbers, db_filepath, debug_path, text_changed, find_missing=True
):
    """
    Identifies substances missing from the DB, enriches them via PubChem, classifies
    each CAS-number situation, and persists results to Excel.

    This is the single entry point for the "missing & bad CAS" stage of the pipeline.
    It is always called before :func:`~merging.merge_db_and_excel_substances` so that
    the returned ``saved_dict_for_merging`` can be used to remap bad CAS numbers during
    the merge step.

    Parameters
    ----------
    xlsx_substance : list of Substance
        All substances parsed from the laboratory Excel "Auswertung" sheet that
        have a CAS value (identified substances).
    db_substances : dict
        Dictionary mapping normalised CAS strings to :class:`~substance.Substance`
        objects loaded from the NIAS database.
    isd_cas_numbers : list or set
        CAS numbers belonging to the Inclusion Set of Derivatives (ISD).  These are
        already expected to migrate and are excluded from the missing-substance check.
    db_filepath : str
        Absolute path to the NIAS database Excel file.  The ``ALL_BAD_CAS`` sheet
        inside this file is read and updated in-place.
    debug_path : str
        Directory where the timestamped debug Excel file is written.
    text_changed : Signal
        Qt signal (or any ``str``-accepting callable) used to stream progress messages
        to the GUI log area.
    find_missing : bool, optional
        When ``False`` the PubChem enrichment step is skipped entirely and the function
        returns the existing ``ALL_BAD_CAS`` mapping directly.  Useful for dry-runs or
        when the missing file has already been generated.  Default is ``True``.

    Returns
    -------
    dict
        The *pre-existing* ``ALL_BAD_CAS`` mapping
        ``{CAS_KEY: (LAB_CAS, Trivial_Name)}``.  The caller (``Reporting.run()``)
        passes this to :func:`~merging.merge_db_and_excel_substances` so that
        substances with known bad/mismatched CAS numbers can be resolved to a
        correct DB entry.

    Side Effects
    ------------
    - Reads ``ALL_BAD_CAS`` sheet from ``db_filepath``.
    - Overwrites ``ALL_BAD_CAS`` sheet in ``db_filepath`` with merged/updated rows.
    - Writes ``missing_<timestamp>.xlsx`` to ``debug_path``.
    - May call ``sys.exit(1)`` if a ``PermissionError`` prevents file writes (the
      files are likely open in Excel).
    """
    
    if not find_missing:
        text_changed.emit("Skipping missing substances handling as per user request.")

        df_all_bad = pd.read_excel(db_filepath, sheet_name="ALL_BAD_CAS", dtype=str)
        ALL_BAD_CAS_dict = {
            row.CAS_KEY: (row.LAB_CAS, row.Trivial_Name)
            for row in df_all_bad.itertuples()
        }
        return ALL_BAD_CAS_dict.copy()
    
    text_changed.emit("Starting to find missing substances...")
    # 1) Build the MISSING sheet
    records, seen = [], set()
    for s in xlsx_substance:
        lab = s.cas.lstrip('0')
        if lab not in db_substances and lab not in isd_cas_numbers:
            d = fill_missing_data_by_queries(s, text_changed) # retrieves data from PubChem
            rec = {
                "PUB_CAS": d["CAS"],
                "PUB_IUPAC": d["pubchem-iupac"],
                "LAB_CAS": lab,
                "Trivial_Name": s.name,
                "PUB_SMILES": d["SMILES"]
            }
            key = tuple(rec.items()) # create a unique key for the record
            if key not in seen:
                seen.add(key) # avoid duplicates
                records.append(rec)
    
    # Create a DataFrame for missing substances
    df_missing = pd.DataFrame(records)
    for col in ["IUPAC_DE","IUPAC_EN","Cramer","FCM",
                "FT_EN","FT_DE","FT_HZ","CL_DE","CL_EN","TypeFlag_CL"]:
        df_missing[col] = None

    # 2) Load existing ALL_BAD_CAS into dict
    df_all_bad = pd.read_excel(db_filepath, sheet_name="ALL_BAD_CAS", dtype=str)
    ALL_BAD_CAS_dict = {
        row.CAS_KEY: (row.LAB_CAS, row.Trivial_Name)
        for row in df_all_bad.itertuples()
    }
    saved_existing_dict_for_merging = ALL_BAD_CAS_dict.copy()
    
    # *** CHANGED: build a normalized key set once for membership checks
    # reason: CAS keys in the sheet may have different leading-zero formatting than keys produced earlier
    ALL_BAD_CAS_dict_normlzd = {str(k).lstrip('0') for k in ALL_BAD_CAS_dict.keys()}  # *** CHANGED ***
    
    bad_entries, ready_entries = [], []
    wrap_counters = {}

    # Define a function to push ready entries
    def push_ready(cas_key, lab, trivial, smiles, remarks=None):
        ready_entries.append({
            "CAS_KEY": cas_key,
            "LAB_CAS": lab,
            "Trivial_Name": trivial,
            "PUB_SMILES": smiles,
            **{c: None for c in ["IUPAC_DE","IUPAC_EN","Cramer","FCM",
                                 "FT_EN","FT_DE","FT_HZ","CL_DE","CL_EN","TypeFlag_CL"]},
            "USER_REMARKS": remarks
        })

    # 3) First pass: classify missing rows 
    # Iterate over the rows in df_missing
    for row in df_missing.itertuples(index=False): # use index=False to avoid adding an index column
        lab = row.LAB_CAS
        pub = (row._asdict().get("PUB_CAS") or "").lstrip('0') # normalize PUB_CAS
        triv = row.Trivial_Name
        smiles = row._asdict().get("PUB_SMILES", "")
        valid = validate_cas(lab)

        if not valid and not pub:
            # wrap invalid/no-PUB case # e.g. 1000132-07-5 (LAB_CAS) --> #1000132-07-5#1 (CUSTOM CAS) as CAS_KEY
            n = wrap_counters.get(lab, 1)
            key = f"#{lab}#{n}" # CUSTOM CAS 
            wrap_counters[lab] = n + 1
            bad_entries.append({  
                "CAS_KEY": key,
                "LAB_CAS": lab,
                "Trivial_Name": triv,
                "KICK_OUT": "",
                "REMARKS": "wrap invalid/no-PUB case"
            }) # adding to BAD_CAS_HANDLING
            continue
        
        if not valid and pub:
            # invalid LAB_CAS but valid PUB_CAS -> treat as bad but use valid PUB_CAS as CAS_Key
            # e.g. 	1000340-22-7 (LAB_CAS) --> 70682-72-3 (PUB_CAS) as CAS_KEY
            bad_entries.append({  
                "CAS_KEY": pub,
                "LAB_CAS": lab,
                "Trivial_Name": triv,
                "KICK_OUT": "",
                "REMARKS": "invalid LAB_CAS but valid PUB_CAS -> treat as bad but use valid PUB_CAS as CAS_Key"
            }) # adding to BAD_CAS_HANDLING
            continue
        
        if valid and pub and lab == pub:
            # exact match → ready (70682-72-3 (LAB_CAS) = 70682-72-3 (PUB_CAS) as CAS_KEY
            remarks = "exact match of LAB_CAS and PUB_CAS, but not in ALL_BAD_CAS and not in db_substances"
            push_ready(pub, lab, triv, smiles, remarks)
            continue

        if valid and pub and lab != pub:
            # Mismatch LAB_CAS vs PUB_CAS → treat as bad but use valid PUB_CAS as CAS_Key 
            # e.g. 1560-89-0 (LAB_CAS) -> 72123-30-9 (PUB_CAS) as CAS_KEY	
            bad_entries.append({
                "CAS_KEY": pub,
                "LAB_CAS": lab,
                "Trivial_Name": triv,
                "KICK_OUT": "",
                "REMARKS": "Mismatch LAB_CAS vs PUB_CAS → treat as bad but use valid PUB_CAS as CAS_Key"
            })  # adding to BAD_CAS_HANDLING
            continue

        if valid and not pub:
            # valid CAS but missing PUB-CAS → bad
            n = wrap_counters.get(lab, 1)
            key = f"&{lab}#{n}" # CUSTOM CAS 
            wrap_counters[lab] = n + 1
            bad_entries.append({
                "CAS_KEY": key,
                "LAB_CAS": lab,
                "Trivial_Name": triv,
                "KICK_OUT": "",
                "REMARKS": "valid CAS but missing PUB-CAS → bad"
            })  # adding to BAD_CAS_HANDLING
            continue

        else:
            # if we reach here, it means there is an unexpected case
            n = wrap_counters.get(lab, 1)
            key = f"#{lab}#{n}" # CUSTOM CAS 
            wrap_counters[lab] = n + 1
            text_changed.emit(f"Unexpected case for LAB_CAS {lab} with PUB_CAS {pub}. Please check the data.")
            bad_entries.append({
                "CAS_KEY": key,
                "LAB_CAS": lab,
                "Trivial_Name": triv,
                "KICK_OUT": "",
                "REMARKS": "Unexpected case"
            })

    # 4) Second pass: enforce kick-outs and promotions
    final_bad = []
    for e in bad_entries:
        cas_key = e["CAS_KEY"].lstrip('0')
        lab = e["LAB_CAS"].lstrip('0')
        triv = e["Trivial_Name"]
        
        # Check if the CAS_KEY is already in ALL_BAD_CAS_dict_normlzd or db_substances
        if cas_key:
            
            if cas_key in db_substances:
                e["KICK_OUT"] = "x"
                e["REMARKS"] = "CAS_KEY already exists in NIAS_Substance sheet"
                final_bad.append(e)
                continue

            elif not cas_key.startswith("#") and not cas_key.startswith("&") and cas_key not in db_substances:
                # If the CAS_KEY is not wrapped and not in db_substances, treat as ready
                e["REMARKS"] = "CAS_KEY not added yet to NIAS_Substance sheet"
                push_ready(
                    cas_key, lab, triv,
                    df_missing.loc[df_missing.LAB_CAS == lab, "PUB_SMILES"].iat[0],
                    remarks=e["REMARKS"]
                )
                final_bad.append(e)
            
            elif cas_key.startswith("&") and cas_key not in db_substances:
                e["REMARKS"] = "VALID CAS but missing PUB-CAS → Not yet added to NIAS_Substance sheet; SMILES obtained from Trivial_Name"
                push_ready(
                    cas_key, lab, triv,
                    df_missing.loc[df_missing.LAB_CAS == lab, "PUB_SMILES"].iat[0],
                    remarks=e["REMARKS"]
                )
                final_bad.append(e)
            elif cas_key.startswith("#") and cas_key not in db_substances:
                e["REMARKS"] = "CUSTOM_CAS_KEY not yet added to NIAS_Substance sheet"
                push_ready(
                    cas_key, lab, triv,
                    df_missing.loc[df_missing.LAB_CAS == lab, "PUB_SMILES"].iat[0],
                    remarks=e["REMARKS"]
                )
                final_bad.append(e)
                
            elif cas_key not in ALL_BAD_CAS_dict_normlzd:
                final_bad.append(e)  # Remove from bad_entries if already in ALL_BAD_CAS_dict_normlzd
                

                
            elif cas_key not in ALL_BAD_CAS_dict_normlzd:
                final_bad.append(e)  # Remove from bad_entries if already in ALL_BAD_CAS_dict_normlzd
        else:
            # If CAS_KEY is empty, treat as ready
            e["REMARKS"] = "CAS_KEY is empty, Needs manual review"
            push_ready(
                lab, lab, triv,
                df_missing.loc[df_missing.LAB_CAS == lab, "PUB_SMILES"].iat[0],
                remarks=e["REMARKS"]
            )
            final_bad.append(e)
            
            
    # 5) Overwrite ALL_BAD_CAS sheet with updated dict
    df_all_bad_updated = pd.DataFrame([
        {"CAS_KEY": e["CAS_KEY"], "LAB_CAS": e["LAB_CAS"], "Trivial_Name": e["Trivial_Name"], "REMARKS": e["REMARKS"]}
        for e in final_bad
    ])
    
    
    # Merge on CAS_KEY, keeping all rows from df_all_bad_updated
    try:
        merged_df = pd.concat([df_all_bad_updated, df_all_bad], ignore_index=True)
        merged_df = merged_df.drop_duplicates(['CAS_KEY', "LAB_CAS"], keep='last')
        
    except KeyError:
        # If CAS_KEY is not in df_all_bad, just use df_all_bad_updated
        merged_df = df_all_bad_updated
        merged_df = merged_df.drop_duplicates(['CAS_KEY', "LAB_CAS"], keep='last')
        
    # Save the updated ALL_BAD_CAS sheet to the database
    try:    
        with pd.ExcelWriter(db_filepath, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            merged_df.to_excel(writer, sheet_name="ALL_BAD_CAS", index=False)
    except PermissionError as e:
        text_changed.emit(f"PermissionError: Cannot write to {db_filepath}. Please close the file and try again.")
        print(f"❌ PermissionError: Cannot write to {db_filepath}. Please close the file and try again.")
        text_changed.emit(f"Exiting in 5 sec due to PermissionError.")
        time.sleep(5)  # Give user time to read the message
        sys.exit(1)
    # 6) Write debug sheets
    # Generate a timestamp for the file name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = os.path.join(debug_path, f"missing_{timestamp}.xlsx")

    try:
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df_missing.to_excel(writer, sheet_name="MISSING", index=False)
            pd.DataFrame(bad_entries).to_excel(writer, sheet_name="BAD_CAS_HANDLING", index=False)
            pd.DataFrame(ready_entries).to_excel(
                writer, sheet_name="(FOR_USER)READY_TO_MERGE_DB", index=False
            )
        text_changed.emit(f"✅ Missing File written to {out}; ALL_BAD_CAS in {db_filepath}")
        print(f"✅ Missing File written to {out}; ALL_BAD_CAS in {db_filepath}")
    except PermissionError as e:
        text_changed.emit(f"PermissionError: Cannot write to {out}. Please close the file and try again.")
        print(f"❌ PermissionError: Cannot write to {out}. Please close the file and try again.")
        text_changed.emit(f" Exiting in 5 sec due to PermissionError.")
        time.sleep(5)  # Give user time to read the message
        sys.exit(1)
    
    return saved_existing_dict_for_merging