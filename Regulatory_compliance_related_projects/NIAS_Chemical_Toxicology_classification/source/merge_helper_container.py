"""
Merge_Helper_Container
======================
Defines :class:`TemporaryBucket`, a lightweight dataclass used as an
intermediate staging object during the substance-merging pipeline.

When a substance from the laboratory Excel file is matched against the NIAS
database (or an external PubChem query), its enriched fields are first collected
into a ``TemporaryBucket`` before being written back to the ``Substance`` object.
This two-step approach avoids partially-overwriting substance data if a lookup
fails mid-way.

Typical lifecycle
-----------------
1. ``create_bucket_from_db()``  or  ``create_bucket_from_pubchem_query()`` in
   ``merging.py`` populate a bucket.
2. ``update_substance(s, bucket)`` copies every bucket field onto the target
   ``Substance`` instance.
"""

from dataclasses import dataclass, field
from typing import Union


@dataclass
class TemporaryBucket:
    """
    Staging container that holds enriched substance fields during the merge pipeline.

    All fields mirror counterparts on :class:`~substance.Substance` but are kept
    separate so that a failed or partial lookup never corrupts the original object.

    Attributes:
        cl_de (list): German classification strings for the substance.
        cl_en (list): English classification strings for the substance.
        ft_de (list): German functional-type footnotes (e.g. "Weichmacher").
        ft_en (list): English functional-type footnotes (e.g. "Plasticizer").
        fcm (int | str | None): EU Food Contact Material number.
            Stored as ``int`` when valid, ``str`` or ``None`` otherwise.
        cramer (str | None): Cramer toxicological class ('I', 'II', or 'III').
        canonical_smiles (str | None): Canonical SMILES string from the DB or PubChem.
        iupac_name_en (str | None): IUPAC systematic name in English.
        iupac_name_de (str | None): IUPAC systematic name in German.
        cas (str | None): Normalised CAS number (leading zeros stripped).
    """

    cl_de : list = field(default_factory=list)
    cl_en : list = field(default_factory=list)
    ft_de : list = field(default_factory=list)
    ft_en : list = field(default_factory=list)
    fcm : Union[int, str] = None
    cramer : str = None
    canonical_smiles: str = None
    iupac_name_en : str = None
    iupac_name_de : str = None
    cas: str = None