import os
import pandas as pd
import requests
import time
import re
import logging

# Load the Excel file
file_path = os.environ.get("INVALID_CAS_FILE_PATH", "data/ZDB_main/ALL_INVALID_CAS.xlsx")
df = pd.read_excel(file_path, sheet_name="BAD_CAS_MERGE_CLEAN")

# ----------------------------
# Logger Setup
# ----------------------------
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

general_logger = logging.getLogger('general_errors')
general_logger.setLevel(logging.DEBUG)  # Set to DEBUG if you want full trace, or ERROR for production
gen_file_handler = logging.FileHandler('errors.log', mode='w')
gen_file_handler.setFormatter(formatter)
general_logger.addHandler(gen_file_handler)
gen_console_handler = logging.StreamHandler()
gen_console_handler.setFormatter(formatter)
general_logger.addHandler(gen_console_handler)

# ----------------------------
# PubChem Query Function
# ----------------------------
def query_pubchem(identifier, query_type="iupac"):
    """Query PubChem using an IUPAC name and return SMILES and CAS."""
    identifier = identifier.strip()
    
    if query_type.lower() in ["cas", "iupac", "name"]:
        input_type = "name"
    elif query_type.lower() == "smiles":
        input_type = "smiles"
    else:
        raise ValueError("Invalid query_type. Use 'cas', 'iupac', or 'smiles'.")
    
    cid_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{input_type}/{requests.utils.quote(identifier)}/cids/JSON"
    try:
        cid_response = requests.get(cid_url, timeout=10)
        cid_response.raise_for_status()
        cid_data = cid_response.json()
        cids = cid_data.get("IdentifierList", {}).get("CID", [])
        if not cids:
            general_logger.warning(f"No CID found for identifier: {identifier}")
            return None
        cid = cids[0]

        # Fetch properties
        prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/ConnectivitySMILES,IUPACName,MolecularFormula/JSON"
        prop_response = requests.get(prop_url, timeout=10)
        prop_response.raise_for_status()
        prop_data = prop_response.json()
        props = prop_data.get("PropertyTable", {}).get("Properties", [])
        if not props:
            general_logger.warning(f"No properties found for CID: {cid}")
            return None

        result = {
            "Identifier": identifier,
            "SMILES": props[0].get("ConnectivitySMILES"),
            "IUPAC": props[0].get("IUPACName"),
            "MolecularFormula": props[0].get("MolecularFormula"),
            "CAS": None
        }

        # Fetch synonyms to find CAS
        syn_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
        syn_response = requests.get(syn_url, timeout=10)
        syn_response.raise_for_status()
        syn_data = syn_response.json()

        synonyms = syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
        cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
        for syn in synonyms:
            if cas_pattern.match(syn):
                result["CAS"] = syn
                break
        print(f"Found CAS: {result['CAS']} for identifier: {identifier}")
        return result

    except requests.RequestException as e:
        general_logger.error(f"PubChem query failed for identifier {identifier}: {e}")
    except Exception as e:
        general_logger.exception(f"Unexpected error for identifier {identifier}: {e}")
    
    return None

# ----------------------------
# Build Results
# ----------------------------
output_rows = []
for _, row in df.iterrows():
    iupac_en = row.get("IUPAC_EN", "")
    lab_cas = row.get("INVALID_CAS", "")
    trivial_name = row.get("Trivial_Name", "") if "Trivial_Name" in row else ""

    if pd.isna(iupac_en) or not iupac_en.strip():
        output_rows.append([f"#{lab_cas}#1", lab_cas, trivial_name, None, "", "", iupac_en, "", "", "", "", "", "", "", "", ""])
        continue

    print(f"Querying PubChem for: {iupac_en}")
    result = query_pubchem(iupac_en)

    smiles = result["SMILES"] if result else None
    pub_cas = result["CAS"] if result and result["CAS"] else ""

    if pub_cas:
        cas_key = pub_cas
    else:
        cas_key = f"#{lab_cas}#1"

    output_rows.append([
        cas_key,          # CAS_KEY
        lab_cas,          # LAB_CAS
        trivial_name,     # Trivial_Name
        smiles,           # PUB_SMILES
        pub_cas,          # PUB_CAS (new column)
        "",               # IUPAC_DE
        iupac_en,         # IUPAC_EN
        "", "", "", "", "", "", "", "", ""  # All other columns blank
    ])

    time.sleep(0.2)

# ----------------------------
# Create DataFrame with Target Structure
# ----------------------------
columns = [
    "CAS_KEY", "LAB_CAS", "Trivial_Name", "PUB_SMILES", "PUB_CAS",
    "IUPAC_DE", "IUPAC_EN", "Cramer", "FCM", "FT_EN", "FT_DE",
    "FT_HZ", "CL_DE", "CL_EN", "TypeFlag_CL", "USER_REMARKS"
]
final_df = pd.DataFrame(output_rows, columns=columns)

# ----------------------------
# Save to Excel
# ----------------------------
output_file = "BAD_CAS_PUBCHEM_RESULTS.xlsx"
final_df.to_excel(output_file, index=False)
print(f"\n✅ Saved results to {output_file}")
