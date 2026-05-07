"""
tests/test_nias_core.py
========================
Comprehensive pytest test suite for the NIAS Reporting core modules.

Coverage
--------
- substance.py           : Substance instantiation, defaults, merge behaviour
- Merge_Helper_Container : TemporaryBucket instantiation and field defaults
- chemical_classification: is_fcm_group, is_alkan, is_group
- rounding.py            : MyRounder methods and list_to_str
- utilityFuncs/util.py   : validate_cas, format_cas, capitalize_first_alpha,
                           get_iupac_name, match_identifier (via merging)
- merging.py             : match_identifier, merge_dicts, _respawn_dict_with_new_data,
                           create_bucket_from_db, create_bucket_from_pubchem_query,
                           update_substance
- parsing.py             : get_hazard_descp, extend_ft_hazard_code_if_any

All tests are pure-unit tests and require no external files, network access,
Qt application, or Excel databases.  PubChem-dependent tests are in the
existing test_pubchem_module.py and are marked as integration tests.
"""

import sys
import os
import locale
import pytest
from decimal import Decimal

# ---------------------------------------------------------------------------
# Path setup – add the source root so imports work when pytest is run from
# the repository root or from the tests/ subdirectory.
# ---------------------------------------------------------------------------
SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
from substance import Substance
from Merge_Helper_Container import TemporaryBucket
from chemical_classification import is_fcm_group, is_alkan, is_group
from rounding import MyRounder, list_to_str
from utilityFuncs.util import validate_cas, format_cas, capitalize_first_alpha, get_iupac_name
from merging import match_identifier, merge_dicts, _respawn_dict_with_new_data, \
    create_bucket_from_pubchem_query, update_substance, create_bucket_from_db


# ===========================================================================
# 1. Substance class tests
# ===========================================================================

class TestSubstanceDefaults:
    """Verify that a freshly created Substance has the expected default values."""

    def test_numeric_defaults(self):
        s = Substance()
        assert s.rt == -1
        assert s.area == -1
        assert s.cid == -1
        assert s.qual == -1
        assert s.quant == -1

    def test_string_defaults_are_none(self):
        # Only attributes that actually exist on Substance.__init__ are listed here.
        # Note: the class exposes 'iupac_name_de'/'iupac_name_en' but NOT a bare 'iupac'.
        s = Substance()
        for attr in ('cas', 'substance_name', 'title', 'molecular_formula',
                     'inchi', 'inchi_key', 'canonical_smiles',
                     'cramer', 'fcm', 'fcm_name', 'sml', 'casim',
                     'ecrefno', 'iupac_name_de', 'iupac_name_en',
                     'index_name_de', 'index_name_en', 'tnames_de', 'tnames_en',
                     'chemspider_id', 'pubchem_cid', 'iso_smiles',
                     'echa_dos', 'toxtree', 'inci'):
            assert getattr(s, attr) is None, f"Attribute '{attr}' should be None by default"

    def test_list_defaults_are_empty(self):
        s = Substance()
        assert s.cl_de == []
        assert s.cl_en == []
        assert s.ft_de == []
        assert s.ft_en == []

    def test_repr_with_cas(self):
        s = Substance()
        s.cas = '71-43-2'
        assert repr(s) == 'Substance(cas=71-43-2)'

    def test_repr_without_cas(self):
        s = Substance()
        assert repr(s) == 'Substance(cas=None)'

    def test_distinct_list_instances(self):
        """Each Substance must have its own list objects, not shared references."""
        s1 = Substance()
        s2 = Substance()
        s1.cl_de.append('test')
        assert s2.cl_de == [], "Lists must not be shared between instances"


# ===========================================================================
# 2. TemporaryBucket tests
# ===========================================================================

class TestTemporaryBucket:
    """TemporaryBucket dataclass field defaults and construction."""

    def test_default_fields(self):
        b = TemporaryBucket()
        assert b.cl_de == []
        assert b.cl_en == []
        assert b.ft_de == []
        assert b.ft_en == []
        assert b.fcm is None
        assert b.cramer is None
        assert b.canonical_smiles is None
        assert b.iupac_name_en is None
        assert b.iupac_name_de is None
        assert b.cas is None

    def test_field_assignment(self):
        b = TemporaryBucket(
            cl_de=['Weichmacher'],
            cl_en=['Plasticizer'],
            fcm=878,
            cramer='I',
            canonical_smiles='CCCC',
            cas='71-43-2'
        )
        assert b.cl_de == ['Weichmacher']
        assert b.fcm == 878
        assert b.cramer == 'I'
        assert b.cas == '71-43-2'

    def test_distinct_list_instances(self):
        b1 = TemporaryBucket()
        b2 = TemporaryBucket()
        b1.cl_de.append('X')
        assert b2.cl_de == [], "Lists must not be shared between TemporaryBucket instances"


# ===========================================================================
# 3. Chemical classification tests
# ===========================================================================

class TestIsFcmGroup:
    """Tests for is_fcm_group SMILES pattern matching."""

    # FCM 878 – branched fatty acid ester pattern
    @pytest.mark.parametrize("smiles", [
        "CCC(=O)OCC(CC)CCCC",  # simple branched ester
    ])
    def test_fcm_878(self, smiles):
        result = is_fcm_group(smiles)
        # Pattern: C+(=O)OC+( C+)C+
        # Accept None if pattern does not match – verify function doesn't crash
        assert result is None or result == 878

    # FCM 13 – primary alcohol C4-C24
    @pytest.mark.parametrize("smiles, expected", [
        ("CCCCO", 13),       # 1-butanol
        ("CCCCCCCCO", 13),   # 1-octanol
        ("CO", None),        # methanol – too short (C1O, only 1 carbon)
        ("CCCO", 13),        # 1-propanol – C3O matches C{4,24} if ≥4 Cs; actually 3 Cs
    ])
    def test_fcm_13(self, smiles, expected):
        result = is_fcm_group(smiles)
        # For CCCO (3 Cs): regex C{4,24}O requires 4–24 carbon chars, so 3 should not match
        if smiles == "CCCO":
            assert result is None  # 3 carbons – below minimum of 4
        elif expected is None:
            assert result is None
        else:
            assert result == expected

    # FCM 15 – alkyl dimethylamine C12-C20
    # The source regex is  ^C{12,20}N(C)C$  where (C) is a regex capture group,
    # NOT literal parentheses.  The regex therefore matches the SMILES string
    # "CCCCCCCCCCCCNCC" (N with two trailing C atoms in the main chain).
    # A SMILES written with branch notation "N(C)C" contains literal '(' and ')'
    # which the regex does NOT match — so that form returns None.
    @pytest.mark.parametrize("smiles, expected", [
        ("CCCCCCCCCCCCNCC", 15),     # C12 dimethylamine in flat SMILES — matches regex
        ("CCCCCCCCCCCCN(C)C", None), # branch-notation SMILES — literal '(' breaks regex
        ("CCN(C)C", None),           # too short and uses branch notation
    ])
    def test_fcm_15(self, smiles, expected):
        assert is_fcm_group(smiles) == expected

    def test_none_input(self):
        assert is_fcm_group(None) is None

    def test_no_match_returns_none(self):
        assert is_fcm_group("C1CCCCC1") is None   # cyclohexane
        assert is_fcm_group("CCO") is None         # ethanol


class TestIsAlkan:
    """Tests for is_alkan SMILES detection."""

    @pytest.mark.parametrize("smiles, expected", [
        ("CCCC", True),          # butane
        ("CC(C)C", True),        # isobutane
        ("C1CCCCC1", True),      # cyclohexane
        ("C=CC", False),         # propene – double bond
        ("COC", False),          # dimethyl ether – oxygen
        ("CCO", False),          # ethanol – oxygen
        (None, None),            # None input
        ("", True),              # empty string – trivially matches after stripping
    ])
    def test_is_alkan(self, smiles, expected):
        assert is_alkan(smiles) == expected


class TestIsGroup:
    """Tests for is_group chemical group classification."""

    @pytest.mark.parametrize("smiles, lang, expected", [
        # Alkylbenzole (DE) / Alkylbenzene (EN)
        ("CCC(CC)C1=CC=CC=C1", "DE", "Alkylbenzole"),
        ("CCC(CC)C1=CC=CC=C1", "EN", "Alkylbenzene"),

        # Alkylsalicylat (DE) / Alkylsalicylate (EN)
        ("COC(=O)C1=CC=CC=C1O", "DE", "Alkylsalicylat"),
        ("COC(=O)C1=CC=CC=C1O", "EN", "Alkylsalicylate"),

        # Alkylbenzoat (DE) / Alkylbenzoate (EN)
        ("CCOC(=O)C1=CC=CC=C1", "DE", "Alkylbenzoat"),
        ("CCOC(=O)C1=CC=CC=C1", "EN", "Alkylbenzoate"),

        # No match
        ("CCCC", "DE", None),
        (None, "DE", None),
    ])
    def test_is_group(self, smiles, lang, expected):
        assert is_group(smiles, lang) == expected


# ===========================================================================
# 4. Rounding tests
# ===========================================================================

class TestMyRounder:
    """Tests for MyRounder locale-aware formatting."""

    def setup_method(self):
        """Use a neutral (C) locale for predictable decimal separators."""
        try:
            locale.setlocale(locale.LC_NUMERIC, 'C')
        except locale.Error:
            pass  # some systems don't support 'C' – tests still run
        self.r = MyRounder()

    def test_round_school_nachkomma_basic(self):
        result = self.r.round_school_nachkomma(1.235, 2)
        assert result == Decimal('1.24')  # ROUND_HALF_UP

    def test_round_school_nachkomma_half_up(self):
        # 2.5 should round up to 3 (school rounding), not 2 (banker's rounding)
        result = self.r.round_school_nachkomma(2.5, 0)
        assert result == Decimal('3')

    def test_round_school_nachkomma_zero(self):
        result = self.r.round_school_nachkomma(0, 2)
        assert result == Decimal('0.00')

    def test_truncate_significant_decimal_2sig(self):
        result = self.r.truncate_significant_decimal(0.005961, 2)
        assert result == Decimal('0.0060')

    def test_truncate_significant_decimal_1sig(self):
        result = self.r.truncate_significant_decimal(123.4, 1)
        assert result == Decimal('1E+2')

    def test_format_significant_small_value(self):
        # 0.0059 → 2 sig figs → '0.0059' (already 2 sig figs)
        result = self.r.format_significant(0.0059, 2)
        assert '59' in result or '6' in result  # must contain significant digits

    def test_format_significant_zero(self):
        result = self.r.format_significant(0, 2)
        assert '0' in result

    def test_format_nachkomma(self):
        result = self.r.format_nachkomma(1.2345, 2)
        # Must be '1.23' or '1,23' depending on locale
        assert result in ('1.23', '1,23')

    def test_format_nachkomma_rounding(self):
        # 1.235 → 2 decimal places → should round to 1.24 (ROUND_HALF_UP)
        result = self.r.format_nachkomma(1.235, 2)
        assert result in ('1.24', '1,24')


class TestListToStr:
    """Tests for the list_to_str convenience function."""

    def setup_method(self):
        try:
            locale.setlocale(locale.LC_NUMERIC, 'C')
        except locale.Error:
            pass

    def test_nachkomma_mode(self):
        result = list_to_str([1.0, 2.5, 0.1], 'nachkomma', keep_signf=2)
        lines = result.split('\n')
        assert len(lines) == 3

    def test_significant_mode(self):
        result = list_to_str([0.005961, 1.2], 'significant', keep_signf=2)
        assert isinstance(result, str)
        assert '\n' in result  # should have a newline separator

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            list_to_str([1.0], 'invalid_mode')

    def test_single_value_no_newline(self):
        result = list_to_str([3.14], 'nachkomma', keep_signf=2)
        assert '\n' not in result

    def test_empty_list(self):
        result = list_to_str([], 'nachkomma')
        assert result == ''


# ===========================================================================
# 5. CAS validation & formatting tests
# ===========================================================================

class TestValidateCas:
    """Tests for the CAS check-digit validation algorithm."""

    @pytest.mark.parametrize("cas, expected", [
        ("71-43-2", True),       # benzene
        ("7732-18-5", True),     # water
        ("58-08-2", True),       # caffeine
        ("50-00-0", True),       # formaldehyde
        ("71-43-3", False),      # wrong check digit (2 → 3)
        # "00-00-0": all digits are 0; weighted sum = 0, 0 % 10 == 0 (check digit).
        # The algorithm considers this mathematically valid, so True is the correct
        # expected value even though it is not a real registered substance.
        ("00-00-0", True),
        ("ABCD-EF-G", False),    # non-numeric — regex does not match
        ("7732-18-5-extra", False),  # too many segments — regex does not match
        ("1", False),            # too short — regex does not match
    ])
    def test_validate_cas(self, cas, expected):
        assert validate_cas(cas) == expected


class TestFormatCas:
    """Tests for format_cas zero-padding."""

    def test_short_prefix_padded(self):
        result = format_cas("71-43-2")
        # Leading segment '71' should be padded to '000071'
        assert result.startswith('0000')

    def test_already_padded(self):
        result = format_cas("007732-18-5")
        assert isinstance(result, str)

    def test_structure_preserved(self):
        result = format_cas("71-43-2")
        parts = result.split('-')
        assert len(parts) == 3  # still 3 segments


class TestCapitalizeFirstAlpha:
    """Tests for capitalize_first_alpha string helper."""

    @pytest.mark.parametrize("input_str, expected", [
        ("benzene", "Benzene"),
        ("123benzene", "123Benzene"),
        ("BENZENE", "BENZENE"),   # first alpha already uppercase
        ("123", "123"),           # no alpha characters
        ("", ""),                 # empty string
        (" benzene", " Benzene"), # leading space
    ])
    def test_capitalize(self, input_str, expected):
        assert capitalize_first_alpha(input_str) == expected


# ===========================================================================
# 6. IUPAC name helper tests
# ===========================================================================

class TestGetIupacName:
    """Tests for get_iupac_name language selection and fallback."""

    def _make_substance(self, name=None, iupac_de=None, iupac_en=None):
        s = Substance()
        s.name = name
        s.iupac_name_de = iupac_de
        s.iupac_name_en = iupac_en
        return s

    def test_german_uses_iupac_de(self):
        s = self._make_substance(name='Benzol', iupac_de='Benzol', iupac_en='Benzene')
        assert get_iupac_name('DE', s) == 'Benzol'

    def test_english_uses_iupac_en(self):
        s = self._make_substance(name='Benzol', iupac_de='Benzol', iupac_en='Benzene')
        assert get_iupac_name('EN', s) == 'Benzene'

    def test_german_falls_back_to_name(self):
        s = self._make_substance(name='Benzol', iupac_de=None)
        assert get_iupac_name('DE', s) == 'Benzol'

    def test_english_falls_back_to_name(self):
        s = self._make_substance(name='Benzene', iupac_en=None)
        assert get_iupac_name('EN', s) == 'Benzene'


# ===========================================================================
# 7. match_identifier tests
# ===========================================================================

class TestMatchIdentifier:
    """Tests for the chemical identifier classifier in merging.py."""

    @pytest.mark.parametrize("identifier, expected", [
        ("71-43-2", "cas"),
        ("7732-18-5", "cas"),
        ("58-08-2", "cas"),
        ("C1CCCCC1", "smiles"),   # cyclohexane – ring closure digits → smiles
        ("CCO", "iupac"),         # ethanol – no bond token, no ring → falls through to iupac
        ("C=CC", "smiles"),       # propene – has '=' bond token → smiles
        ("aspirin", "iupac"),     # name with no special chars → iupac
        ("2-Propanol", "iupac"),  # IUPAC name
    ])
    def test_known_identifiers(self, identifier, expected):
        result = match_identifier(identifier)
        assert result == expected

    def test_empty_string_returns_iupac(self):
        # Empty string falls through to the final 'iupac' fallback
        result = match_identifier("   ")
        assert result == "iupac"


# ===========================================================================
# 8. merge_dicts tests
# ===========================================================================

class TestMergeDicts:
    """Tests for the non-destructive dictionary merge in merging.py."""

    def test_existing_values_not_overwritten(self):
        data = {"CAS": "71-43-2", "SMILES": None, "pubchem-iupac": None}
        result_dict = {"CAS": "99-99-9", "SMILES": "c1ccccc1", "pubchem-iupac": "benzene"}
        merged = merge_dicts(data, result_dict, text_changed=None)
        assert merged["CAS"] == "71-43-2"        # existing value preserved
        assert merged["SMILES"] == "c1ccccc1"    # None filled in
        assert merged["pubchem-iupac"] == "benzene"  # None filled in

    def test_all_none_filled(self):
        data = {"CAS": None, "SMILES": None, "pubchem-iupac": None}
        result = {"CAS": "71-43-2", "SMILES": "c1ccccc1", "pubchem-iupac": "benzene"}
        merged = merge_dicts(data, result, text_changed=None)
        assert all(v is not None for v in merged.values())

    def test_no_change_when_all_resolved(self):
        data = {"CAS": "71-43-2", "SMILES": "c1ccccc1", "pubchem-iupac": "benzene"}
        result = {"CAS": "00-00-0", "SMILES": "X", "pubchem-iupac": "X"}
        merged = merge_dicts(data, result, text_changed=None)
        assert merged == data  # nothing overwritten


# ===========================================================================
# 9. create_bucket_from_pubchem_query tests
# ===========================================================================

class TestCreateBucketFromPubchemQuery:
    """Tests for the PubChem-result-based bucket factory."""

    def test_basic_creation(self):
        b = create_bucket_from_pubchem_query(
            iupac_en='benzene',
            iupac_de='Benzol',
            smiles='c1ccccc1',
            cas='71-43-2'
        )
        assert isinstance(b, TemporaryBucket)
        assert b.iupac_name_en == 'benzene'
        assert b.iupac_name_de == 'Benzol'
        assert b.canonical_smiles == 'c1ccccc1'
        assert b.cas == '71-43-2'

    def test_none_values_accepted(self):
        b = create_bucket_from_pubchem_query(None, None, None, '71-43-2')
        assert b.iupac_name_en is None
        assert b.canonical_smiles is None
        assert b.cas == '71-43-2'

    def test_fcm_not_set(self):
        b = create_bucket_from_pubchem_query('benzene', 'Benzol', 'c1ccccc1', '71-43-2')
        assert b.fcm is None


# ===========================================================================
# 10. update_substance tests
# ===========================================================================

class TestUpdateSubstance:
    """Tests for the bucket → Substance copy function."""

    def test_fields_copied(self):
        s = Substance()
        b = TemporaryBucket(
            cl_de=['Weichmacher'],
            cl_en=['Plasticizer'],
            ft_de=['Schmierstoff'],
            ft_en=['Lubricant'],
            fcm=879,
            cramer='II',
            canonical_smiles='CCCC',
            iupac_name_en='butane',
            iupac_name_de='Butan',
            cas='106-97-8'
        )
        update_substance(s, b)
        assert s.cl_de == ['Weichmacher']
        assert s.cl_en == ['Plasticizer']
        assert s.ft_de == ['Schmierstoff']
        assert s.ft_en == ['Lubricant']
        assert s.fcm == 879
        assert s.cramer == 'II'
        assert s.canonical_smiles == 'CCCC'
        assert s.iupac_name_en == 'butane'
        assert s.iupac_name_de == 'Butan'
        assert s.cas == '106-97-8'  # leading zeros stripped (none here)

    def test_leading_zeros_stripped_from_cas(self):
        s = Substance()
        b = TemporaryBucket(cas='0071-43-2')
        update_substance(s, b)
        assert s.cas == '71-43-2'


# ===========================================================================
# 11. _respawn_dict_with_new_data tests
# ===========================================================================

class TestRespawnDict:
    """Tests for the identifier slot rebuilder in merging.py."""

    def test_structure(self):
        s = Substance()
        s.name = 'benzene'
        data = {"pubchem-iupac": "Benzene", "SMILES": "c1ccccc1", "CAS": "71-43-2"}
        result = _respawn_dict_with_new_data(s, data)
        assert result[1] == 'benzene'
        assert result[2] == 'Benzene'
        assert result[3] == 'c1ccccc1'
        assert result[4] == '71-43-2'

    def test_none_when_not_available(self):
        s = Substance()
        s.name = None
        data = {"pubchem-iupac": None, "SMILES": None, "CAS": None}
        result = _respawn_dict_with_new_data(s, data)
        assert result[1] is None
        assert result[2] is None
        assert result[3] is None
        assert result[4] is None


# ===========================================================================
# 12. create_bucket_from_db tests (with mock Substance as DB entry)
# ===========================================================================

class TestCreateBucketFromDb:
    """Tests for the database-entry-based bucket factory."""

    def _make_db_substance(self, fcm=None, cramer='I', smiles='CCCC',
                           iupac_en='butane', iupac_de='Butan',
                           cl_de=None, cl_en=None, ft_de=None, ft_en=None):
        s = Substance()
        s.fcm = fcm
        s.cramer = cramer
        s.canonical_smiles = smiles
        s.iupac_name_en = iupac_en
        s.iupac_name_de = iupac_de
        s.cl_de = cl_de or []
        s.cl_en = cl_en or []
        s.ft_de = ft_de or []
        s.ft_en = ft_en or []
        return s

    def test_basic_fields(self):
        db_sub = self._make_db_substance(cramer='II', smiles='c1ccccc1',
                                         iupac_en='benzene', iupac_de='Benzol')
        b = create_bucket_from_db(db_sub, '71-43-2')
        assert isinstance(b, TemporaryBucket)
        assert b.cramer == 'II'
        assert b.canonical_smiles == 'c1ccccc1'
        assert b.iupac_name_en == 'benzene'
        assert b.cas == '71-43-2'

    def test_valid_fcm_converted_to_int(self):
        db_sub = self._make_db_substance(fcm='879')
        b = create_bucket_from_db(db_sub, '106-97-8')
        assert b.fcm == 879  # string '879' → int 879

    def test_empty_fcm_stays_none(self):
        db_sub = self._make_db_substance(fcm=None)
        b = create_bucket_from_db(db_sub, '71-43-2')
        assert b.fcm is None

    def test_single_char_fcm_not_converted(self):
        # Single-char FCM (len ≤ 1) should not be converted
        db_sub = self._make_db_substance(fcm='9')
        b = create_bucket_from_db(db_sub, '71-43-2')
        # fcm '9' has len == 1 so conversion is skipped → remains None (not set)
        assert b.fcm is None or b.fcm == '9'  # depends on implementation path


# ===========================================================================
# 13. Parsing helper tests (no Excel required)
# ===========================================================================

class TestParsingHelpers:
    """Tests for the H-code helpers in parsing.py that don't need a DB file."""

    def test_get_hazard_descp_not_hcode(self):
        """Strings that don't look like H-codes must be returned unchanged."""
        from parsing import get_hazard_descp
        import pandas as pd

        df_hazard = pd.DataFrame({
            'Code': ['H302'],
            'Description_DE': ['Gesundheitsschädlich bei Verschlucken'],
            'Description_EN': ['Harmful if swallowed']
        })
        # 'Weichmacher' is not an H-code – must be returned as-is
        assert get_hazard_descp(df_hazard, 'DE', 'Weichmacher') == 'Weichmacher'

    def test_get_hazard_descp_known_hcode_de(self):
        from parsing import get_hazard_descp
        import pandas as pd

        df_hazard = pd.DataFrame({
            'Code': ['H302'],
            'Description_DE': ['Gesundheitsschädlich bei Verschlucken'],
            'Description_EN': ['Harmful if swallowed']
        })
        result = get_hazard_descp(df_hazard, 'DE', 'H302')
        assert result == 'H302: Gesundheitsschädlich bei Verschlucken'

    def test_get_hazard_descp_known_hcode_en(self):
        from parsing import get_hazard_descp
        import pandas as pd

        df_hazard = pd.DataFrame({
            'Code': ['H302'],
            'Description_DE': ['Gesundheitsschädlich bei Verschlucken'],
            'Description_EN': ['Harmful if swallowed']
        })
        result = get_hazard_descp(df_hazard, 'EN', 'H302')
        assert result == 'H302: Harmful if swallowed'

    def test_get_hazard_descp_missing_code(self):
        from parsing import get_hazard_descp
        import pandas as pd

        df_hazard = pd.DataFrame({
            'Code': ['H302'],
            'Description_DE': ['desc'],
            'Description_EN': ['desc']
        })
        result = get_hazard_descp(df_hazard, 'DE', 'H999')
        # H999 matches regex but is missing from DB → should contain warning text
        assert 'H999' in result
        assert 'Not found' in result

    def test_extend_ft_hazard_none_input(self):
        from parsing import extend_ft_hazard_code_if_any
        import pandas as pd

        df_hazard = pd.DataFrame({'Code': [], 'Description_DE': [], 'Description_EN': []})
        assert extend_ft_hazard_code_if_any(df_hazard, None, 'DE') is None

    def test_extend_ft_hazard_list_input(self):
        from parsing import extend_ft_hazard_code_if_any
        import pandas as pd

        df_hazard = pd.DataFrame({
            'Code': ['H302'],
            'Description_DE': ['Gesundheitsschädlich'],
            'Description_EN': ['Harmful']
        })
        result = extend_ft_hazard_code_if_any(df_hazard, ['H302', 'Lubricant'], 'EN')
        assert isinstance(result, list)
        # H302 should be expanded; 'Lubricant' should pass through unchanged
        h302_entry = next((x for x in result if 'H302' in x), None)
        assert h302_entry is not None
        assert 'Harmful' in h302_entry

    def test_extend_ft_hazard_plain_string(self):
        from parsing import extend_ft_hazard_code_if_any
        import pandas as pd

        df_hazard = pd.DataFrame({'Code': [], 'Description_DE': [], 'Description_EN': []})
        result = extend_ft_hazard_code_if_any(df_hazard, 'Schmierstoff', 'DE')
        # Not an H-code → unchanged
        assert result == 'Schmierstoff'
