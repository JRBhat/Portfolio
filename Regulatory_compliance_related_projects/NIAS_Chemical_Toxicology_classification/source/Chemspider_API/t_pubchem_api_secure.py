import requests
import re


# def query_pubchem(cas_or_name):
#     """
#     Queries the PubChem API for substance information.
    
#     Args:
#         cas_or_name (str): CAS number or chemical name.
    
#     Returns:
#         dict: A dictionary containing substance properties or None if not found.
#     """
#     cas_or_name = cas_or_name.lstrip('0')
#     base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/"
#     properties = "MolecularFormula,MolecularWeight,Title,IUPACName,InChIKey,InChI,CanonicalSMILES/JSON"
#     url = base_url.format(cas_or_name) + properties
    
#     try:
#         response = requests.get(url, verify=certifi.where())
#         response.raise_for_status()
#         data = json.loads(response.text)
#     except (requests.RequestException, json.JSONDecodeError) as e:
#         print(f"Error fetching data for {cas_or_name}: {e}")
#         return None
    
#     try:
#         properties = data["PropertyTable"]["Properties"][0]
#         return {
#             "CID": properties["CID"],
#             "MolecularFormula": properties["MolecularFormula"],
#             "MolecularWeight": properties["MolecularWeight"],
#             "CanonicalSMILES": properties["CanonicalSMILES"],
#             "InChI": properties["InChI"],
#             "InChIKey": properties["InChIKey"],
#             "IUPACName": properties["IUPACName"],
#             "Title": properties["Title"]
#         }
#     except (KeyError, IndexError):
#         print(f"Failed to extract data for {cas_or_name}")
#         return None
    
    
def query_pubchem(identifier, query_type="cas"):
    """Query PubChem using an identifier (CAS, IUPAC, or SMILES) to retrieve
    canonical properties and CAS number (from synonyms).

    For CAS, IUPAC, or name searches, the 'name' endpoint is used.
    For SMILES, the 'smiles' endpoint is used.
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
    
    # URL to fetch canonical properties (note that 'CAS' is not available here)
    prop_url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{}/{}/"
                "property/CanonicalSMILES,IUPACName,MolecularFormula/JSON").format(input_type, identifier)
    
    try:
        response = requests.get(prop_url, verify=True)
        response.raise_for_status()
        data = response.json()
        
        properties = data.get("PropertyTable", {}).get("Properties", [])
        if not properties:
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

        # Access synonyms from the response; structure may vary so we default to an empty list if not found.
        synonyms = syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
        
        # Use a regular expression to identify a valid CAS number format:
        cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
        for syn in synonyms:
            if cas_pattern.match(syn):
                result["CAS"] = syn
                break
        
        return result
    except requests.RequestException as e:
        print(f"PubChem query failed for {identifier}: {e}")
    
    return None


    # base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{}/{}/property/CAS,CanonicalSMILES,IUPACName,MolecularFormula/JSON"
    
    # if query_type == "cas" or query_type == "iupac":
    #     url = base_url.format("name", identifier)
    # elif query_type == "smiles":
    #     url = base_url.format("smiles", identifier)
    
    # try:
    #     response = requests.get(url, verify=True)
    #     response.raise_for_status()
    #     data = response.json()
        
    #     properties = data.get("PropertyTable", {}).get("Properties", [])
    #     if properties:
    #         return {
    #             "CAS": identifier if query_type == "cas" else None,
    #             "SMILES": properties[0].get("CanonicalSMILES"),
    #             "IUPAC": properties[0].get("IUPACName")
    #         }
    # except requests.RequestException as e:
    #     print(f"PubChem query failed for {identifier}: {e}")
    # return None


if __name__ == "__main__":
    smiles = input("Enter smiles: ")
    result = query_pubchem(smiles, query_type="smiles")
    print("Result:", result)
