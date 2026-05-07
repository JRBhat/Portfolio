import requests
import json
import time
import certifi
import logging 

# def query_chemspider(cas):
#     """
#     Queries ChemSpider for the IUPAC name using a CAS number.
    
#     Args:
#         cas (str): The CAS number of the substance.
    
#     Returns:
#         dict: A dictionary containing 'iupac_name_en' and 'iupac_name_de', or None if not found.
#     """
#     cas = cas.lstrip('0')
#     user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0'
#     url = f'https://www.chemspider.com/api/search?value={cas}&orderBy=ReferenceCounts.DatasourceCount&orderDirection=descending'
    
#     try:
#         r = requests.get(url, headers={"User-Agent": user_agent}, verify=certifi.where())
#         r.raise_for_status()
#         response = json.loads(r.text)
#     except (requests.RequestException, json.JSONDecodeError) as e:
#         print(f'Error fetching data for CAS {cas}: {e}')
#         return None
    
#     time.sleep(1)
    
#     iupac_de = None
#     iupac_en = None
#     try:
#         for synonym in response['Records'][0]['Synonyms']:
#             if synonym['Language'] == 'de':
#                 iupac_de = synonym['Name']
#             elif synonym['Language'] == 'en':
#                 if 'ACD/IUPAC Name' in synonym['Flags'] and synonym['Status'] == 'Approved':
#                     iupac_en = synonym['Name']
        
#         return {'iupac_name_de': iupac_de, 'iupac_name_en': iupac_en}
#     except (KeyError, IndexError):
#         print(f'Failed to extract IUPAC name for CAS {cas}')
#         return None

#TODO: Q: Why does searching for 2,4-Bis(2-methyl-2-propanyl)phenol' in chemspider return 2,4-Di-t-butylphenol'? are they the same? CAn I use the SMILES code from this substance?

def query_chemspider(identifier, query_type="cas"):
    """Query ChemSpider for CAS, IUPAC, or SMILES based on input type."""
    user_agent = 'Mozilla/5.0'
    base_url = "https://www.chemspider.com/api/search?value={}"
    
    url = base_url.format(identifier)
    
    try:
        response = requests.get(url, headers={"User-Agent": user_agent}, verify=True)
        response.raise_for_status()
        data = response.json()
        
        if "Records" in data and data["Records"]:
            record = data["Records"][0]
            
            cas = record.get("Cas")
            smiles = record.get("StructuralIdentifiers", {}).get("Smiles")
            iupac = record.get("IUPACName")
            
            return {"CAS": cas, "SMILES": smiles, "IUPAC": iupac}
        
    except requests.RequestException as e:
        print(f"ChemSpider query failed for {identifier}: {e}")
    return None

if __name__ == "__main__":
    cas_number = input("Enter CAS number: ")
    result = query_chemspider(cas_number)
    print("Result:", result)
