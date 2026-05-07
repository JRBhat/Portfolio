import os
import pandas as pd
import requests
import json
import time
import certifi
import logging
import re

# ----------------------------
# Logger Setup
# ----------------------------

# Formatter for all loggers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# General error logger (for CAS-based queries and other errors)
general_logger = logging.getLogger('general_errors')
general_logger.setLevel(logging.ERROR)
# File handler for general errors: failed_queries.log (overwrite each run)
gen_file_handler = logging.FileHandler('failed_queries.log', mode='w')
gen_file_handler.setFormatter(formatter)
general_logger.addHandler(gen_file_handler)
# Console handler: prints errors to the console
gen_console_handler = logging.StreamHandler()
gen_console_handler.setFormatter(formatter)
general_logger.addHandler(gen_console_handler)

# Logger for successful fallbacks (when IUPAC search returns a value)
fallback_success_logger = logging.getLogger("fallback_success")
fallback_success_logger.setLevel(logging.INFO)
fs_handler = logging.FileHandler("fallback_success.log", mode='w')
fs_handler.setFormatter(formatter)
fallback_success_logger.addHandler(fs_handler)

# Logger for failed fallbacks (when IUPAC search still fails)
fallback_failure_logger = logging.getLogger("fallback_failure")
fallback_failure_logger.setLevel(logging.ERROR)
ff_handler = logging.FileHandler("fallback_failure.log", mode='w')
ff_handler.setFormatter(formatter)
fallback_failure_logger.addHandler(ff_handler)

# ----------------------------
# API Query Functions
# ----------------------------
import requests

def query_chemspider(identifier):
    """Query ChemSpider for CAS, IUPAC, SMILES, and German name based on input type."""
    user_agent = 'Mozilla/5.0'
    base_url = "https://www.chemspider.com/api/search?value={}"
    url = base_url.format(identifier)
    
    try:
        response = requests.get(url, headers={"User-Agent": user_agent}, verify=True)
        response.raise_for_status()
        data = response.json()
        
        if "Records" in data and data["Records"]:
            record = data["Records"][0]
            title = record.get("Title")
            cas = record.get("Cas")
            smiles = record.get("StructuralIdentifiers", {}).get("Smiles")
            iupac = record.get("IUPACName")

            # Extract German name
            german_name = None
            synonyms = record.get("Synonyms", [])
            for synonym in synonyms:
                if synonym.get("Language") == "de":
                    german_name = synonym.get("Name")
                    break  # Stop at the first German name found

            return {"Identifier": identifier, "Title": title,"CAS": cas, "SMILES": smiles, "IUPAC": iupac, "German Name": german_name}
        else:
            general_logger.error(f"ChemSpider: No records found for identifier: {identifier}")
    except requests.RequestException as e:
        general_logger.error(f"ChemSpider query failed for identifier {identifier}: {e}")
    return None

def query_pubchem(identifier, query_type="cas"):
    """Query PubChem using an identifier (CAS, IUPAC, or SMILES) to retrieve
    canonical properties and CAS number (from synonyms).
    """
    # Clean the identifier string
    identifier = identifier.strip()
    
    # Determine which endpoint to use
    if query_type.lower() in ["cas", "iupac", "name"]:
        input_type = "name"
    elif query_type.lower() == "smiles":
        input_type = "smiles"
    else:
        raise ValueError("Invalid query_type. Use 'cas', 'iupac', or 'smiles'.")
    
    # URL to fetch canonical properties
    prop_url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{}/{}/"
                "property/CanonicalSMILES,IUPACName,MolecularFormula/JSON").format(input_type, identifier)
    
    try:
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
            "CAS": None  # Will update after checking synonyms
        }
        
        # Query synonyms to try and extract the CAS number
        syn_url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{}/{}/synonyms/JSON").format(input_type, identifier)
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
    
    return None

# ----------------------------
# Main Processing Loop
# ----------------------------
def main():
    # Load the Excel file (adjust the filename if needed)
    df = pd.read_excel(os.environ.get("NIAS_DB_PATH", "data/NIAS_ZDB.xlsx"))

    for idx, row in df.iterrows():
        cas = row["CAS"]
        
        # Check if IUPAC names or SMILES are missing (empty string or NaN)
        missing_iupac_de = pd.isna(row["IUPAC_DE"]) or row["IUPAC_DE"] == ""
        missing_iupac_en = pd.isna(row["IUPAC_EN"]) or row["IUPAC_EN"] == ""
        missing_smiles   = pd.isna(row["SMILES"]) or row["SMILES"] == ""
        
        # --------- IUPAC Query Section ----------
        if missing_iupac_de or missing_iupac_en:
            # First try querying using the CAS number
            result_cs = query_chemspider(cas, query_type="cas")
            
            # If CAS query fails, attempt fallback using IUPAC name if available
            if not result_cs:
                alt_identifier = None
                if pd.notna(row["IUPAC_EN"]) and row["IUPAC_EN"] != "":
                    alt_identifier = row["IUPAC_EN"]
                elif pd.notna(row["IUPAC_DE"]) and row["IUPAC_DE"] != "":
                    alt_identifier = row["IUPAC_DE"]
                
                if alt_identifier:
                    general_logger.error(f"ChemSpider: CAS query failed for {cas}, trying fallback IUPAC search with: {alt_identifier}")
                    result_cs = query_chemspider(alt_identifier, query_type="iupac")
                    if result_cs and result_cs.get("IUPAC"):
                        fallback_success_logger.info(f"Fallback search using IUPAC identifier '{alt_identifier}' succeeded for original CAS {cas}.")
                    else:
                        fallback_failure_logger.error(f"Fallback search using IUPAC identifier '{alt_identifier}' failed for original CAS {cas}.")
            
            if result_cs:
                iupac_value = result_cs.get("IUPAC")
                if iupac_value:
                    if missing_iupac_de:
                        df.at[idx, "IUPAC_DE"] = iupac_value
                    if missing_iupac_en:
                        df.at[idx, "IUPAC_EN"] = iupac_value
                else:
                    general_logger.error(f"ChemSpider: IUPAC name not found for identifier: {cas}")
                # Optionally update SMILES from ChemSpider if missing
                if missing_smiles and result_cs.get("SMILES"):
                    df.at[idx, "SMILES"] = result_cs.get("SMILES")
            else:
                general_logger.error(f"ChemSpider: Failed to retrieve data for identifier: {cas}")
            
            time.sleep(1)  # Pause between API calls

        # --------- SMILES Query Section ----------
        if missing_smiles:
            result_pc = query_pubchem(cas, query_type="cas")
            if not result_pc:
                # If PubChem query with CAS fails, attempt fallback using IUPAC name if available
                alt_identifier = None
                if pd.notna(row["IUPAC_EN"]) and row["IUPAC_EN"] != "":
                    alt_identifier = row["IUPAC_EN"]
                elif pd.notna(row["IUPAC_DE"]) and row["IUPAC_DE"] != "":
                    alt_identifier = row["IUPAC_DE"]
                
                if alt_identifier:
                    general_logger.error(f"PubChem: CAS query failed for {cas}, trying fallback IUPAC search with: {alt_identifier}")
                    result_pc = query_pubchem(alt_identifier, query_type="iupac")
                    if result_pc and result_pc.get("SMILES"):
                        fallback_success_logger.info(f"Fallback search using IUPAC identifier '{alt_identifier}' succeeded for original CAS {cas} in PubChem.")
                    else:
                        fallback_failure_logger.error(f"Fallback search using IUPAC identifier '{alt_identifier}' failed for original CAS {cas} in PubChem.")
            
            if result_pc:
                smiles_value = result_pc.get("SMILES")
                if smiles_value:
                    df.at[idx, "SMILES"] = smiles_value
                else:
                    general_logger.error(f"PubChem: SMILES not found for identifier: {cas}")
            else:
                general_logger.error(f"PubChem: Failed to retrieve data for identifier: {cas}")
            
            time.sleep(1)

    # ----------------------------
    # Save Updated File
    # ----------------------------

    df.to_excel("updated_file.xlsx", index=False)
    print("Update complete. New file saved as 'updated_file.xlsx'.")
    print("Please check 'failed_queries.log', 'fallback_success.log', and 'fallback_failure.log' for details.")

    # >>> string = "%07d"%354236
    # >>> list(string)

if __name__ == '__main__':
    cas = "220766-68-7"
    smiles = "CC(C)(C)c1ccc(O)c(C(C)(C)C)c1"
    iupac = "2,4-Bis(2-methyl-2-propanyl)phenol"
    
    # pubchem to retrieve cas given iupac or iupac given cas, or cas+iupac given smiles
    print(query_pubchem(cas, "cas"))
    # print(query_pubchem(smiles, "smiles"))
    # print(query_pubchem(iupac, "iupac")) # no german iupac names
    
    print("................\n\n")
    
    # chem spider gets smiles and german name given iupac_en or cas
    print(query_chemspider(cas))
    # print(query_chemspider(smiles))
    # print(query_chemspider(iupac))