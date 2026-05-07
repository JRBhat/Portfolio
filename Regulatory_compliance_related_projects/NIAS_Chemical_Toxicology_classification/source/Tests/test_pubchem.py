import requests
import re
import logging

# Setup logger
general_logger = logging.getLogger("PubChemLogger")
general_logger.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add handler to logger
if not general_logger.handlers:
    general_logger.addHandler(console_handler)

def query_pubchem(identifier, query_type="cas"):
    """Query PubChem using an identifier (CAS, IUPAC, or SMILES)."""
    identifier = identifier.strip()
    if query_type.lower() in ["cas", "iupac", "name"]:
        input_type = "name"
    elif query_type.lower() == "smiles":
        input_type = "smiles"
    else:
        raise ValueError("Invalid query_type. Use 'cas', 'iupac', or 'smiles'.")
    
    prop_url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{input_type}/{identifier}/"
        "property/CanonicalSMILES,IUPACName,MolecularFormula/JSON"
    )
    try:
        general_logger.debug(f"Querying PubChem properties with URL: {prop_url}")
        response = requests.get(prop_url, verify=True)
        response.raise_for_status()
        data = response.json()
        
        properties = data.get("PropertyTable", {}).get("Properties", [])
        if not properties:
            general_logger.error(f"PubChem: No properties found for identifier: {identifier}")
            return None
        
        result = {
            "Identifier": identifier,
            "SMILES": properties[0].get("CanonicalSMILES"),
            "IUPAC": properties[0].get("IUPACName"),
            "MolecularFormula": properties[0].get("MolecularFormula"),
            "CAS": None
        }
        
        syn_url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{input_type}/{identifier}/synonyms/JSON"
        )
        general_logger.debug(f"Querying PubChem synonyms with URL: {syn_url}")
        syn_response = requests.get(syn_url, verify=True)
        syn_response.raise_for_status()
        syn_data = syn_response.json()
        
        synonyms = syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
        cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
        for syn in synonyms:
            if cas_pattern.match(syn):
                result["CAS"] = syn
                break
        
        return result

    except requests.RequestException as e:
        general_logger.error(f"PubChem query failed for identifier {identifier}: {e}")
    except Exception as e:
        general_logger.exception(f"Unexpected error for identifier {identifier}: {e}")
    return None


# Test cases
test_cases = [
    ("58-08-2",    "cas"),      # caffeine
    ("50-78-2",    "cas"),      # aspirin
    ("64-17-5",    "cas"),      # ethanol
    ("7732-18-5",  "cas"),      # water
    ("67-56-1",    "cas"),      # methanol
    ("71-43-2",    "cas"),      # benzene
    ("75-07-0",    "cas"),      # acetaldehyde
    ("7782-44-7",  "cas"),      # oxygen
    ("7440-44-0",  "cas"),      # carbon
    ("7440-50-8",  "cas"),      # copper
    ("glucose",              "name"),
    ("acetone",              "name"),
    ("2‑Propanol",           "iupac"),
    ("sucrose",              "name"),
    ("2‑Methylpropane",      "iupac"),
    ("ethyl acetate",        "name"),
    ("formaldehyde",         "name"),
    ("acetic acid",          "name"),
    ("benzene",              "name"),
    ("2‑Chloroethanol",      "iupac"),
    ("C(C(=O)O)N",           "smiles"),  # glycine
    ("CC(=O)O",              "smiles"),  # acetic acid
    ("C1CCCCC1",             "smiles"),  # cyclohexane
    ("C(CO)O",               "smiles"),  # ethylene glycol
    ("CCO",                  "smiles"),  # ethanol
    ("C#N",                  "smiles"),  # hydrogen cyanide
    ("O=C=O",                "smiles"),  # carbon dioxide
    ("CC(=O)NC1=CC=CC=C1",   "smiles"),  # acetanilide
    ("CCC(=O)OCC",           "smiles"),  # ethyl propionate
    ("C1=CC=CC=C1O",         "smiles"),  # phenol
]

for ident, qtype in test_cases:
    if qtype == "smiles":
        ident = ident.replace("=", "%3")
    res = query_pubchem(ident, query_type=qtype)
    print(f"\nLookup {ident!r} ({qtype}):")
    if res:
        for k, v in res.items():
            print(f"  {k:15s}: {v}")
    else:
        print("  → No data returned or error")
