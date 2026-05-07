import pytest

from utilityFuncs.util import query_pubchem

@pytest.mark.parametrize("identifier, query_type, expected_smiles, expected_formula", [
    # Formaldehyde: CAS lookup
    ("50-00-0", "cas", "C=O", "CH2O"),
    # Cyclohexane: SMILES lookup
    ("C1CCCCC1", "smiles", "C1CCCCC1", "C6H12"),
    # Water: name lookup
    ("water", "name", "O", "H2O"),
])
def test_query_pubchem_basic(identifier, query_type, expected_smiles, expected_formula):
    """
    Basic integration tests against the PubChem API.
    Checks that query_pubchem returns expected SMILES and formula.
    """
    result = query_pubchem(identifier, query_type=query_type)
    
    # The call should return a dictionary with the core keys
    assert isinstance(result, dict)
    for key in ("Identifier", "CID", "SMILES", "IUPAC", "MolecularFormula"):  
        assert key in result, f"Missing key {key} in result"

    # Check the SMILES and formula match expected values
    assert result["SMILES"] == expected_smiles
    assert result["MolecularFormula"] == expected_formula


def test_invalid_query_type():
    """
    Passing an invalid query_type should raise a ValueError.
    """
    with pytest.raises(ValueError):
        query_pubchem("1234-56-7", query_type="invalid")


def test_nonexistent_identifier():
    """
    A nonexistent identifier should return None (no data).
    """
    # Assuming this random string won't match any compound
    result = query_pubchem("ZZZZZZZZ", query_type="name")
    assert result is None
