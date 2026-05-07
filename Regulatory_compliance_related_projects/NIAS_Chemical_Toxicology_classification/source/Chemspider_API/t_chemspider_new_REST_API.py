from chemspipy import ChemSpider, Compound
from dotenv import load_dotenv
import os



from typing import Optional, Dict, Any

# Load ChemSpider API key from environment variable.
# Set RSC_CHEMSPIDER_API_KEY in your environment or a .env file before running.
load_dotenv()  # Loads from a .env file in the current working directory if present
API_KEY = os.getenv("RSC_CHEMSPIDER_API_KEY")
# Initialize once at module level
_cs = ChemSpider(API_KEY)

def query_chemspider(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Query ChemSpider via ChemSpiPy for CAS, IUPAC, SMILES, and English & German names.
    Returns a dict or None on error / not found.
    """
    identifier = identifier.strip()
    try:
        # 1) Fetch the Compound object
        if identifier.isdigit():
            # direct lookup by CSID
            comp: Compound = _cs.get_compound(int(identifier))
        else:
            # search by name/SMILES/InChI/etc.
            results = _cs.search(identifier)
            comp = next(results, None)
            if comp is None:
                return None

        # 2) Extract the desired properties
        # Note: chemspipy Compound attributes:
        #   comp.csid, comp.cas, comp.smiles, comp.iupac_name, comp.common_name, comp.synonyms
        cas     = comp.cas
        smiles  = comp.smiles or comp.canonical_smiles
        iupac   = comp.iupac_name
        english = comp.common_name

        # 3) Find a German synonym if available
        german = None
        # ChemSpiPy's .synonyms is a flat list of strings, so we do a simple language filter:
        for syn in comp.synonyms:
            # crude check: german names often contain umlauts or 'ß'
            if any(ch in syn for ch in ("ä","ö","ü","ß")):
                german = syn
                break

        return {
            "Identifier": identifier,
            "CSID":       comp.csid,
            "CAS":        cas,
            "SMILES":     smiles,
            "IUPAC":      iupac,
            "English":    english,
            "German":     german
        }

    except Exception as e:
        # you might want to log e or reraise a more specific exception
        print(f"ChemSpider query failed: {e}")
        return None
