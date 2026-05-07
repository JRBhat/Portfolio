"""
chemical_classification.py
===========================
SMILES-pattern-based chemical structure classifier used during the FCM grouping
and Cramer classification stages of the NIAS reporting pipeline.

All three public functions accept a SMILES string and return either an integer
FCM group number, a boolean, or a chemical-group name string.  They rely
exclusively on regular-expression matching against the *canonical* (non-isomeric,
non-stereo) SMILES produced by PubChem or the NIAS database.

Functions
---------
is_fcm_group(smiles)
    Returns the EU FCM group number (9, 13, 15, 878, or 879) if the SMILES
    matches a known pattern; otherwise ``None``.  Used in ``exports.py``
    when a substance has no explicit FCM number assigned.

is_alkan(smiles)
    Returns ``True`` when the SMILES represents a pure hydrocarbon (alkane or
    cycloalkane), ``False`` for any heteroatom or double bond, and ``None``
    for ``None`` input.  Alkanes receive special treatment in Table A3.

is_group(smiles, language)
    Classifies the molecule into a named chemical group
    (Alkylbenzole/Alkylbenzene, Alkylsalicylat/Alkylsalicylate,
    Alkylbenzoat/Alkylbenzoate) for Cramer classification overrides.
    Returns a localised string or ``None``.

Pattern approach
----------------
All patterns match against the *full* SMILES string (``re.match`` anchored at
start, patterns end with ``$``).  Only simple, linear or lightly branched
structures are covered; ring-closed or complex molecules that happen to contain
a matching sub-string are excluded by the end-anchor.
"""

import re


def is_fcm_group(smiles):
    """
    Determines the FCM group of a molecule based on its SMILES representation.

    Args:
        smiles (str): A string representing a chemical structure in SMILES format.

    Returns:
        int | None: The FCM group number if a match is found, otherwise None.
        
    """
    if smiles is None:
        return None

    m = re.match(r'^C+\(=O\)OC+\(C+\)C+$', smiles)
    if m:
        return 878

    m = re.match(r'^C+OC\(=O\)C+\(?C+\)?C+$', smiles)
    if m:
        return 879

    m = re.match(r'^C+\(=O\)OC+$', smiles)
    if m:
        return 879

    m = re.match(r'^C{4,24}O$', smiles)
    if m:
        return 13
    m = re.match(r'^C{12,20}N(C)C$', smiles)
    if m:
        return 15
    return None

def is_alkan(smiles: str) -> bool | None: 
    """
    Determines if the given SMILES string represents an alkane molecule.

    An alkane is a hydrocarbon composed entirely of carbon (C) and hydrogen (H), 
    with single bonds only and no branching beyond C atoms. This function checks 
    for the presence of characters other than `C` (carbon) and ignores branching 
    (`(`, `)`) and ring-closing notation (`1`).

    Args:
        smiles (str): A string representing a molecule in SMILES format. 
                    If None is provided, the function returns None.

    Returns:
        bool | None: 
            - True if the SMILES string represents an alkane.
            - False if it contains other atoms or non-alkane structures.
            - None if the input is None.

    Examples:
        >>> is_alkan("CCCC")
        True  # Represents butane (an alkane)
        
        >>> is_alkan("CC(C)C")
        True  # Represents isobutane (an alkane with branching)

        >>> is_alkan("C1CCCCC1")
        True  # Represents cyclohexane (ring-based alkane)

        >>> is_alkan("C=CC")
        False  # Contains a double bond (not an alkane)

        >>> is_alkan("COC")
        False  # Contains an oxygen atom (not an alkane)

        >>> is_alkan(None)
        None  # Invalid input
    """
    if smiles is None:
        return None

    # Remove characters that are part of standard alkane SMILES
    smiles_r = smiles.replace('C', '').replace('(', '').replace(')', '').replace('1', '')

    # Check if the resulting string is empty
    if len(smiles_r) == 0:
        return True  # The molecule is an alkane
    else:
        return False  # The molecule contains other elements or bonds

def is_group(smiles, language):
    """
    Classifies a molecule into a specific chemical group based on its SMILES representation.

    Args:
        smiles (str): A string representing a molecule in SMILES format. 
                    If None is provided, the function returns None.

    Returns:
        str | None: The name of the chemical group if the SMILES string matches a pattern,
                    otherwise None.

    Matching Patterns:
        - 'Alkylbenzole': Matches molecules with an alkyl group attached to a benzene ring.
        Example: `CC(C)C1=CC=CC=C1`.
        
        - 'Alkylsalicylate': Matches molecules with an alkoxy group (CO) attached to a benzene 
        ring with hydroxyl (OH) and carbonyl (C=O) groups.
        Example: `COC(=O)C1=CC=CC=C1O`.
        
        - 'Alkylbenzoate': Matches molecules with an alkyl group (optionally branched) attached 
        to a benzoate structure.
        Example: `CCOC(=O)C1=CC=CC=C1`.
    """
    if smiles is None:
        return None

    m = re.match(r'^C+\(C+\)C1=CC=CC=C1$', smiles)
    if m:
        if language == 'DE':
            return 'Alkylbenzole'
        elif language == 'EN':
            return 'Alkylbenzene'
        
    m = re.match(r'^C+OC\(=O\)C1=CC=CC=C1O$', smiles)
    if m:
        if language == 'DE':
            return 'Alkylsalicylat'
        elif language == 'EN':
            return 'Alkylsalicylate'


    m = re.match(r'^(C+(\(C+\))?C*)OC\(=O\)C1=CC=CC=C1$', smiles)
    
    if m:
        if language == 'DE':
            return 'Alkylbenzoat'
        elif language == 'EN':
            return 'Alkylbenzoate'

    return None
