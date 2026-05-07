"""
merging.py
==========
Integrates substance data from the laboratory Excel file with entries in the
NIAS substance database, and enriches substances with information retrieved
from the PubChem REST API when needed.

Key responsibilities
--------------------
- **merge_db_and_excel_substances** – primary merge function that walks every
  substance from the lab Excel file and, in priority order, attempts to:
  1. Apply database values directly (CAS found in DB).
  2. Remap via the ``ALL_BAD_CAS`` mapping (invalid/mismatched CAS numbers).
  3. Record a minimal entry for manual follow-up if no resolution is possible.

- **fill_missing_data_by_queries** – for substances not found in the DB, iterates
  over multiple identifier types (CAS, name, IUPAC, SMILES) using a rotating
  :class:`collections.deque` and calls PubChem until all three fields (CAS, IUPAC,
  SMILES) are resolved or all combinations are exhausted.

- **match_identifier** – classifies a free-text string as 'cas', 'smiles',
  'iupac', or 'unknown' so that the correct PubChem endpoint is called.

Logging
-------
All errors are written to both ``cas_merge_errors.log`` (file) and the console
via the root logger configured at module level.
"""

import json
import logging
import re
import pandas as pd
from merge_helper_container import TemporaryBucket
from utilityFuncs.util import query_pubchem , validate_cas
from collections import deque, Counter

logger = logging.getLogger(__name__)

def log_error(context, cas=None, name=None, exception=None, extra=None):
    """
    Log an error with context, CAS, substance name, and optional exception or extra info.
    """
    cas_info = f"CAS: {cas}" if cas else "CAS: N/A"
    name_info = f"Name: {name}" if name else "Name: N/A"
    extra_info = f" | {extra}" if extra else ""
    err_msg = f"[{context}] {cas_info}, {name_info}{extra_info}"
    if exception:
        logger.error(f"{err_msg} | Exception: {str(exception)}")
    else:
        logger.error(err_msg)


def create_bucket_from_db(db_sub, cas):
    """
    Create a TemporaryBucket populated from a database entry.
    Validates and casts FCM if present.
    """
    bucket = TemporaryBucket(
        cl_de=db_sub.cl_de,
        cl_en=db_sub.cl_en,
        ft_de=db_sub.ft_de,
        ft_en=db_sub.ft_en,
        iupac_name_en=db_sub.iupac_name_en,
        iupac_name_de=db_sub.iupac_name_de,
        cramer=db_sub.cramer,
        canonical_smiles=db_sub.canonical_smiles,
        cas=cas
    )
    # Try converting FCM to int if it's a non-trivial number
    try:
        if db_sub.fcm and len(str(db_sub.fcm)) > 1:
            bucket.fcm = int(db_sub.fcm)
    except Exception:
        log_error("create_bucket_from_db", cas=cas, extra="invalid fcm format")
    return bucket


def create_bucket_from_pubchem_query(iupac_en, iupac_de, smiles, cas):
    """
    Create a TemporaryBucket using external query results (ChemSpider/PubChem).
    """
    return TemporaryBucket(
        iupac_name_en=iupac_en,
        iupac_name_de=iupac_de,
        canonical_smiles=smiles,
        cas=cas
    )


def update_substance(s, bucket):
    """
    Apply the values from a TemporaryBucket to the substance object.
    Strips leading zeros from CAS.
    """
    s.cl_de = bucket.cl_de
    s.cl_en = bucket.cl_en
    s.ft_de = bucket.ft_de
    s.ft_en = bucket.ft_en
    s.iupac_name_en = bucket.iupac_name_en
    s.iupac_name_de = bucket.iupac_name_de
    s.fcm = bucket.fcm
    s.cramer = bucket.cramer
    s.canonical_smiles = bucket.canonical_smiles
    s.cas = bucket.cas.lstrip('0')  # Normalize CAS format

    
def merge_db_and_excel_substances(xlsx_substances, db_substances, saved_dict_for_merging, isd):
    """
    Main function to merge substances from an Excel list and a DB mapping.
    Writes enriched results to a JSON file and logs errors.
    """

    for s in xlsx_substances:
        raw_cas = s.cas  # original CAS string (may have leading zeros)
        cas = raw_cas.lstrip('0')  # normalize by removing leading zeros

        # Skip if CAS is already in ISD or DB
        if cas in isd:
            continue
        
        try:
            if cas in db_substances:
                # Found in database: use DB values
                bucket = create_bucket_from_db(db_substances[cas], cas)
                update_substance(s, bucket)

            # elif validate_cas(cas):
            #     # Valid CAS but not in DB: Fill pubchem data atleast - rest will be later filled by DB manual fill
            #     d = fill_missing_data_by_queries(s)
            #     iupac_en, iupac_de, smiles = None, None, d["SMILES"]
            #     bucket = create_bucket_from_pubchem_query(iupac_en, iupac_de, smiles, cas)
            #     update_substance(s, bucket)
                
            elif s.cas.lstrip('0') in [v[0] for _, v in saved_dict_for_merging.items()]: 
                # CAS is in ALL_BAD_CAS: use existing values
                cas_key = [k for k, v in saved_dict_for_merging.items() if v[0] == s.cas.lstrip('0')][0]
                bucket = create_bucket_from_db(db_substances[cas_key], cas_key)
                update_substance(s, bucket)
            
            else:
                # No valid CAS or name: log and record minimal info
                log_error(
                    "INVALID_CAS_NAME_PAIR",
                    cas=cas,
                    name=s.name,
                    extra="no valid CAS or name to query"
                )

                bucket = TemporaryBucket(iupac_name_en=s.name, cas=cas)
                update_substance(s, bucket)

        except Exception as e:
            # Catch-all error handler for this record
            log_error("merge_db_and_excel_substances", cas=raw_cas, name=s.name, exception=e)


def match_identifier(identifier: str) -> str:
    PATTERN_CAS = r'^\d{2,7}-\d{2}-\d$'
    PATTERN_SMILES = r'^[A-Za-z0-9@\+\-\[\]\(\)=#\\/]+$'
    PATTERN_IUPAC = r'^[A-Za-z][A-Za-z0-9,\-()]*[A-Za-z]$'
    """
    Classify a chemical identifier as 'cas', 'smiles', 'iupac' or 'unknown'.
    """
    identifier = identifier.strip()

    # 1) CAS (e.g. 50-00-0)

    if re.fullmatch(PATTERN_CAS, identifier):
        print(f"Matched identifier: {identifier} as CAS")
        return "cas"

    # 2) SMILES
    #   a) only SMILES‐legal chars
    if re.fullmatch(PATTERN_SMILES, identifier):
        #   b) must have either a bond token or a proper ring closure digit
        has_bond = bool(re.search(r'[=#@\\/]', identifier))
        digits = Counter(re.findall(r'\d', identifier))
        has_ring = any(count == 2 for count in digits.values())
        if has_bond or has_ring:
            print(f"Matched identifier: {identifier} as smiles")
            return "smiles"
        

    # 3) IUPAC‐style name
    #    Strip any leading/trailing hyphens first, then require start+end with letter.
    name_candidate = identifier.strip('-')
    if re.fullmatch(PATTERN_IUPAC, name_candidate):
        print(f"Matched identifier: {identifier} as iupac")
        return "iupac"
    
    print(f"Unknown match for identifier: {identifier} -- reverting to  iupac")
    return "iupac"

    
def get_data_from_Pubchem_database(identifier, text_changed):
    
        
    pub = query_pubchem(identifier, match_identifier(identifier), text_changed)

    return {
        "iupac_name_en": None,
        "iupac_name_de": None,
        "pubchem-iupac": pub.get("IUPAC") if pub else None,
        "SMILES": pub.get("SMILES") if pub else None,
        "CAS": pub.get("CAS") if pub else None,
    }
    


from collections import deque

def fill_missing_data_by_queries(s, text_changed):
    """
    Attempts to resolve missing chemical data for a substance via iterative PubChem queries.

    The function tries to fill three fields – CAS number, IUPAC name, and SMILES –
    by querying PubChem with whatever identifiers are already available on the substance
    object.  It uses a rotating :class:`~collections.deque` to cycle through four
    identifier slots in different orders so that every plausible combination is tried
    before giving up.

    Resolution order on first pass:
        1. CAS (if ``s.cas`` passes :func:`~utilityFuncs.util.validate_cas`)
        2. Substance name  (``s.name``)
        3. PubChem IUPAC name (populated by a previous successful query)
        4. SMILES           (populated by a previous successful query)

    The deque is rotated on each outer iteration, so subsequent passes start from a
    different identifier, maximising the chance of a hit.

    Args:
        s: A :class:`~substance.Substance` instance with at minimum ``s.cas`` and
           ``s.name`` set.
        text_changed (Signal): Qt signal (or any callable accepting a ``str``) used to
            stream progress messages to the GUI log area.

    Returns:
        dict: A dictionary with keys ``'pubchem-iupac'``, ``'SMILES'``, ``'CAS'``.
              Each value is the resolved string, or ``None`` if unresolved.
    """
    data_dict = {
        "pubchem-iupac": None,
        "SMILES": None,
        "CAS": None,
    }
    
    # If CAS valid, query it first
    
    cas = s.cas.lstrip("0")
    if validate_cas(cas):
        result_dict = get_data_from_Pubchem_database(cas, text_changed)
        print(f"CAS: {cas}")
        text_changed.emit(f"CAS: {cas}")
        data_dict = merge_dicts(data_dict, result_dict, text_changed)

    # Identifiers priority list
    identifier_order = [4, 1, 2, 3]

    # Get mapping of identifier numbers to actual identifiers
    func_map_dict = _respawn_dict_with_new_data(s, data_dict)

    # Iterate over each rotated version of identifier_order
    identifiers_deque = deque(identifier_order)
    for _ in range(len(identifiers_deque)):
        identifiers_deque.rotate(-1)
        
        for nr in identifiers_deque:
            identifier = func_map_dict.get(nr)
            if identifier:
                print(f"Querying identifier: {identifier} (type {nr})")
                text_changed.emit(f"Querying identifier: {identifier} (type {nr})")
                result_dict = get_data_from_Pubchem_database(identifier, text_changed)
                data_dict = merge_dicts(data_dict, result_dict, text_changed)
                
                # Print intermediate state
                print(f"After querying {identifier}: {data_dict}")
                text_changed.emit(f"After querying {identifier}: {data_dict}")
                if all(value is not None for value in data_dict.values()):
                    return data_dict  # Return early if all data found

    print(f"Final data_dict: {data_dict}")
    text_changed.emit(f"Final data_dict: {data_dict}")
    
    return data_dict


def _respawn_dict_with_new_data(s, data_dict):
    """
    Rebuilds the identifier lookup map after each PubChem query round.

    Maps integer slots (1–4) to the most up-to-date identifier values so that
    ``fill_missing_data_by_queries`` always queries using the freshest data.

    Slot assignments:
        1 → substance trivial name (``s.name``)
        2 → PubChem IUPAC (from a previous query result)
        3 → SMILES (from a previous query result)
        4 → CAS number (from a previous query result)

    Args:
        s: A :class:`~substance.Substance` instance.
        data_dict (dict): Current state of resolved fields.

    Returns:
        dict: Mapping of ``{int: str | None}`` for use in the deque rotation loop.
    """
    return {
        1: s.name,
        2: data_dict.get("pubchem-iupac"),
        3: data_dict.get("SMILES"),
        4: data_dict.get("CAS")
    }

def merge_dicts(data_dict, result_dict, text_changed):
    """
    Merges a PubChem query result into the running data dictionary without overwriting
    values that are already resolved.

    For each key shared between ``data_dict`` and ``result_dict``, keeps the existing
    value in ``data_dict`` if it is not ``None``; otherwise adopts the value from
    ``result_dict``.  This ensures that data accumulated across multiple queries is
    never lost.

    Args:
        data_dict (dict): Current accumulator of resolved fields
            (keys: ``'pubchem-iupac'``, ``'SMILES'``, ``'CAS'``).
        result_dict (dict): Result returned by a single PubChem query.
        text_changed: Unused in this function but kept for signature consistency
            with the surrounding pipeline (future use).

    Returns:
        dict: Updated accumulator preserving all previously resolved values.
    """
    return {
        key: data_dict[key] if data_dict[key] is not None else result_dict[key]
        for key in data_dict.keys()
    }
        
# === Example calls ===
if __name__ == "__main__":

# === Highlights of changes ===
# • Always resolve CID via /cids endpoint, since property endpoint no longer accepts xref/rn, smiles, or name directly.
# • Properties fetched via cid/{CID}/property.
# • Synonyms fetched via cid/{CID}/synonyms for consistent CAS extraction.

    tests = [
        # CAS lookups
        ("58-08-2", "cas"),        # caffeine
        ("7732-18-5", "cas"),      # water

        # Name/IUPAC lookups
        ("aspirin", "name"),
        ("2‑Propanol", "iupac"),   # isopropanol
        ("acetone", "name"),

        # SMILES lookups
        ("C1CCCCC1", "smiles"),    # cyclohexane
        ("C(C(=O)O)N", "smiles"),   # glycine
        ("CCO", "smiles"),         # ethanol
    ]

    for ident, qtype in tests:
        
        print(f"\n>> {ident!r} ({qtype}):")
        
        result = query_pubchem(ident, query_type=qtype)
        if result:

            print(f"  SMILES:          {result['SMILES']}")
            print(f"  IUPAC Name:      {result['IUPAC']}")
            print(f"  MolecularForm.:  {result['MolecularFormula']}")
            print(f"  CAS RN (if any): {result['CAS']}")
        else:
            print("  → Lookup failed or no data returned")