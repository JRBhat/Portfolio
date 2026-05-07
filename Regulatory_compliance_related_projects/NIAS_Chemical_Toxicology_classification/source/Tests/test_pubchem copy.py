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
    """Query PubChem using an identifier (CAS, IUPAC, name or SMILES)."""
    identifier = identifier.strip()
    qtype = query_type.lower()
    # Determine namespace for first lookup
    if qtype in ["cas", "iupac", "name"]:
        namespace = "name"
    elif qtype == "smiles":
        namespace = "smiles"
    else:
        raise ValueError("Invalid query_type. Use 'cas', 'iupac', 'name', or 'smiles'.")

    # Step 1: resolve to CID
    cid_url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{namespace}/{identifier}/cids/JSON"
    )
    try:
        general_logger.debug(f"Resolving CID with URL: {cid_url}")
        resp_cid = requests.get(cid_url, verify=True)
        resp_cid.raise_for_status()
        cid_data = resp_cid.json()
        cids = cid_data.get("IdentifierList", {}).get("CID", [])
        if not cids:
            general_logger.error(f"No CIDs found for {identifier}")
            return None
        cid = cids[0]

        # Step 2: fetch properties using new API property names
        prop_url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/"
            "property/ConnectivitySMILES,IUPACName,MolecularFormula/JSON"
        )
        general_logger.debug(f"Querying properties with URL: {prop_url}")
        resp_prop = requests.get(prop_url, verify=True)
        resp_prop.raise_for_status()
        prop_data = resp_prop.json()

        props = prop_data.get("PropertyTable", {}).get("Properties", [{}])[0]
        result = {
            "Identifier": identifier,
            "CID": cid,
            "SMILES": props.get("ConnectivitySMILES"),
            "IUPAC": props.get("IUPACName"),
            "MolecularFormula": props.get("MolecularFormula"),
            "CAS": None
        }

        # Fetch synonyms (including CAS) via CID
        syn_url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
        )
        general_logger.debug(f"Querying synonyms with URL: {syn_url}")
        resp_syn = requests.get(syn_url, verify=True)
        resp_syn.raise_for_status()
        syn_data = resp_syn.json()

        synonyms = syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
        cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
        for syn in synonyms:
            if cas_pattern.match(syn):
                result["CAS"] = syn
                break

        return result

    except requests.RequestException as e:
        general_logger.error(f"PubChem request failed: {e}")
    except Exception as e:
        general_logger.exception(f"Unexpected error: {e}")
    return None


# Example usage
test_ids = ["58-08-2", "50-78-2", "64-17-5", "7732-18-5", "glucose", "C(C(=O)O)N"]
for ident in test_ids:
    res = query_pubchem(ident, query_type="cas" if re.match(r'^\d', ident) else "name")
    print(res)
