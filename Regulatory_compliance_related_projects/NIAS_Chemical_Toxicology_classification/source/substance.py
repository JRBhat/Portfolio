from dataclasses import dataclass, field


@dataclass(repr=False)
class Substance:
    """
    A class to represent a chemical substance and its associated metadata.

    Attributes:
        rt (float): Retention time of the substance in a chromatographic analysis. Default is -1.
        area (float): Peak area of the substance in a chromatogram. Default is -1.
        substance_name (str): Name of the substance. Default is None.
        cid (int): Compound ID from a database or experiment. Default is -1.
        qual (float): Qualitative result or score for the substance. Default is -1.
        quant (float): Quantitative result or score for the substance. Default is -1.
        cas (str): CAS (Chemical Abstracts Service) number for the substance. Default is None.
        title (str): Title or name of the substance. Default is None.
        molecular_formula (str): Molecular formula of the substance. Default is None.
        molecular_weight (float): Molecular weight of the substance. Default is None.
        iupac_name_de / iupac_name_en: German and English IUPAC names.
        inchi (str): InChI (International Chemical Identifier) string of the substance. Default is None.
        inchi_key (str): InChI Key of the substance. Default is None.
        canonical_smiles (str): Canonical SMILES (Simplified Molecular Input Line Entry System) representation. Default is None.
        cramer (str): Cramer classification for toxicological assessment. Default is None.
        fcm (str): Food Contact Material (FCM) identifier. Default is None.
        fcm_name (str): Name of the FCM category or group. Default is None.
        sml (float): Specific Migration Limit (SML) for the substance. Default is None.
        casim (str): Alternative CAS-like identifier. Default is None.
        ecrefno (str): European Chemicals Reference number. Default is None.
        iupac_name_de (str): German IUPAC name of the substance. Default is None.
        iupac_name_en (str): English IUPAC name of the substance. Default is None.
        index_name_de (str): German index name of the substance. Default is None.
        index_name_en (str): English index name of the substance. Default is None.
        tnames_de (str): German trivial names for the substance. Default is None.
        tnames_en (str): English trivial names for the substance. Default is None.
        chemspider_id (int): ChemSpider ID for the substance. Default is None.
        pubchem_cid (int): PubChem CID for the substance. Default is None.
        iso_smiles (str): Isomeric SMILES string. Default is None.
        echa_dos (str): European Chemicals Agency (ECHA) dossier number. Default is None.
        cl_de (list): List of German classifications. Default is an empty list.
        cl_en (list): List of English classifications. Default is an empty list.
        ft_de (list): List of German functional types. Default is an empty list.
        ft_en (list): List of English functional types. Default is an empty list.
        toxtree (str): Toxicological classification based on Toxtree software. Default is None.
        inci (str): International Nomenclature of Cosmetic Ingredients (INCI) name. Default is None.
    """

    # Analytical data
    rt: float = -1
    area: float = -1
    substance_name: str | None = None
    cid: int = -1
    qual: float = -1
    quant: float = -1

    # Chemical identifiers
    cas: str | None = None
    title: str | None = None
    molecular_formula: str | None = None
    molecular_weight: float | None = None
    inchi: str | None = None
    inchi_key: str | None = None
    canonical_smiles: str | None = None

    # Regulatory data
    cramer: str | None = None
    fcm: str | None = None
    fcm_name: str | None = None
    sml: float | None = None

    # Additional identifiers
    casim: str | None = None
    ecrefno: str | None = None
    iupac_name_de: str | None = None
    iupac_name_en: str | None = None
    index_name_de: str | None = None
    index_name_en: str | None = None
    tnames_de: str | None = None
    tnames_en: str | None = None
    chemspider_id: int | None = None
    pubchem_cid: int | None = None
    iso_smiles: str | None = None
    echa_dos: str | None = None

    # Classification and functional types
    cl_de: list = field(default_factory=list)
    cl_en: list = field(default_factory=list)
    ft_de: list = field(default_factory=list)
    ft_en: list = field(default_factory=list)

    # Additional data
    toxtree: str | None = None
    inci: str | None = None

    def __repr__(self):
        return f'Substance(cas={self.cas})'

    def merge(self, other):
        """Merges another Substance object's attributes into this one, avoiding duplicates."""
        if not isinstance(other, Substance) or self.cas != other.cas:
            raise ValueError("Can only merge substances with the same CAS number.")

        def safe_merge(attr1, attr2):
            """Ensures both attributes are lists before merging to avoid TypeErrors."""
            if not isinstance(attr1, list):
                attr1 = [attr1] if attr1 else []
            if not isinstance(attr2, list):
                attr2 = [attr2] if attr2 else []
            return list(set(attr1 + attr2))

        self.fcm = safe_merge(self.fcm, other.fcm)
        self.inci = safe_merge(self.inci, other.inci)
        self.cl_de = safe_merge(self.cl_de, other.cl_de)
        self.ft_de = safe_merge(self.ft_de, other.ft_de)
        self.cl_en = safe_merge(self.cl_en, other.cl_en)
        self.ft_en = safe_merge(self.ft_en, other.ft_en)
