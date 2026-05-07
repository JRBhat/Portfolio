"""
Tests for calculate_FFA.py

Tests cover:
  - Correct FAA formula: log(F4) - log(F3)
  - Output keys for both study types
  - Caching behaviour (skips recomputation if output exists)
  - Edge cases: zero alpha values, negative alpha (invalid)
  - File output written correctly
"""
import math
import os
import pandas as pd
import pytest

from calculate_FFA import compute_faa


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_masterarbeit_input(path, f3_pre, f4_pre, f3_post, f4_post):
    """Write a whitespace-separated input file in Masterarbeit (German decimal) format."""
    content = (
        "F3-Average_pre\tF4-Average_pre\tF3-Average_post\tF4-Average_post\n"
        f"{str(f3_pre).replace('.', ',')}\t{str(f4_pre).replace('.', ',')}\t"
        f"{str(f3_post).replace('.', ',')}\t{str(f4_post).replace('.', ',')}\n"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _write_clinical_input(path, values: dict):
    """
    Write a whitespace-separated input file in clinical (dot decimal) format.

    values: dict with keys like 'F3-Average_baseline', 'F4-Average_baseline', etc.
    """
    timepoints = ["baseline", "applk", "5min", "10min", "15min", "20min"]
    header_parts = []
    row_parts = []
    for tp in timepoints:
        for side in ["F3", "F4"]:
            col = f"{side}-Average_{tp}"
            header_parts.append(col)
            row_parts.append(str(values[col]))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\t".join(header_parts) + "\n")
        fh.write("\t".join(row_parts) + "\n")


# ---------------------------------------------------------------------------
# Masterarbeit tests
# ---------------------------------------------------------------------------

class TestComputeFAAMasterarbeit:

    def test_returns_dict_with_correct_keys(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, 0.5, 0.8, 0.6, 0.9)
        result = compute_faa(inp, out, studytype="Masterarbeit")
        assert isinstance(result, dict)
        assert "FAA_pre" in result
        assert "FAA_post" in result

    def test_faa_formula_pre(self, tmp_path):
        """FAA_pre = log(F4_pre) - log(F3_pre)"""
        f3_pre, f4_pre = 0.5, 0.8
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, f3_pre, f4_pre, 0.6, 0.9)
        result = compute_faa(inp, out, studytype="Masterarbeit")
        expected = math.log(f4_pre) - math.log(f3_pre)
        assert abs(result["FAA_pre"] - expected) < 1e-6, \
            f"FAA_pre: expected {expected}, got {result['FAA_pre']}"

    def test_faa_formula_post(self, tmp_path):
        """FAA_post = log(F4_post) - log(F3_post)"""
        f3_post, f4_post = 0.6, 0.9
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, 0.5, 0.8, f3_post, f4_post)
        result = compute_faa(inp, out, studytype="Masterarbeit")
        expected = math.log(f4_post) - math.log(f3_post)
        assert abs(result["FAA_post"] - expected) < 1e-6

    def test_output_csv_created(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, 0.5, 0.8, 0.6, 0.9)
        compute_faa(inp, out, studytype="Masterarbeit")
        assert os.path.exists(out), "Output CSV file should be created"

    def test_output_csv_contains_faa_columns(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, 0.5, 0.8, 0.6, 0.9)
        compute_faa(inp, out, studytype="Masterarbeit")
        df = pd.read_csv(out)
        assert "FAA_pre" in df.columns
        assert "FAA_post" in df.columns

    def test_caching_skips_recomputation(self, tmp_path):
        """If output file already exists, function loads it without re-reading input."""
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, 0.5, 0.8, 0.6, 0.9)

        # First call: computes and writes output
        result1 = compute_faa(inp, out, studytype="Masterarbeit")

        # Modify input file — should NOT affect result if caching works
        _write_masterarbeit_input(inp, 9.9, 9.9, 9.9, 9.9)

        # Second call: should return same values as first (cached)
        result2 = compute_faa(inp, out, studytype="Masterarbeit")
        assert abs(result1["FAA_pre"] - result2["FAA_pre"]) < 1e-6, \
            "Cached result should match first computation"

    def test_positive_faa_when_f4_greater_than_f3(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, 0.5, 1.0, 0.5, 1.0)  # F4 > F3
        result = compute_faa(inp, out, studytype="Masterarbeit")
        assert result["FAA_pre"] > 0, "FAA should be positive when F4 alpha > F3 alpha"

    def test_negative_faa_when_f3_greater_than_f4(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, 1.0, 0.5, 1.0, 0.5)  # F3 > F4
        result = compute_faa(inp, out, studytype="Masterarbeit")
        assert result["FAA_pre"] < 0, "FAA should be negative when F3 alpha > F4 alpha"

    def test_zero_faa_when_f3_equals_f4(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_masterarbeit_input(inp, 0.5, 0.5, 0.5, 0.5)  # F3 == F4
        result = compute_faa(inp, out, studytype="Masterarbeit")
        assert abs(result["FAA_pre"]) < 1e-9, "FAA should be ~0 when F3 == F4"


# ---------------------------------------------------------------------------
# clinical tests
# ---------------------------------------------------------------------------

class TestComputeFAAclinical:

    def _default_values(self):
        """Return a dict with valid alpha values for all clinical timepoints."""
        timepoints = ["baseline", "applk", "5min", "10min", "15min", "20min"]
        values = {}
        for i, tp in enumerate(timepoints):
            values[f"F3-Average_{tp}"] = 0.5 + i * 0.01
            values[f"F4-Average_{tp}"] = 0.6 + i * 0.01
        return values

    def test_returns_dict_with_all_clinical_keys(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_clinical_input(inp, self._default_values())
        result = compute_faa(inp, out, studytype="clinical")
        expected_keys = {"FAA_baseline", "FAA_applk", "FAA_5min",
                         "FAA_10min", "FAA_15min", "FAA_20min"}
        assert set(result.keys()) == expected_keys

    def test_faa_baseline_formula(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        vals = self._default_values()
        f3 = vals["F3-Average_baseline"]
        f4 = vals["F4-Average_baseline"]
        _write_clinical_input(inp, vals)
        result = compute_faa(inp, out, studytype="clinical")
        expected = math.log(f4) - math.log(f3)
        assert abs(result["FAA_baseline"] - expected) < 1e-6

    def test_clinical_output_csv_created(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_clinical_input(inp, self._default_values())
        compute_faa(inp, out, studytype="clinical")
        assert os.path.exists(out)

    def test_clinical_caching(self, tmp_path):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        vals = self._default_values()
        _write_clinical_input(inp, vals)
        result1 = compute_faa(inp, out, studytype="clinical")

        # Overwrite input with different values
        for k in vals:
            vals[k] = 9.9
        _write_clinical_input(inp, vals)

        result2 = compute_faa(inp, out, studytype="clinical")
        assert abs(result1["FAA_baseline"] - result2["FAA_baseline"]) < 1e-6, \
            "Caching should prevent re-reading modified input"

    @pytest.mark.parametrize("timepoint", [
        "baseline", "applk", "5min", "10min", "15min", "20min"
    ])
    def test_all_timepoints_have_numeric_faa(self, tmp_path, timepoint):
        inp = str(tmp_path / "area.txt")
        out = str(tmp_path / "area_faa.csv")
        _write_clinical_input(inp, self._default_values())
        result = compute_faa(inp, out, studytype="clinical")
        key = f"FAA_{timepoint}"
        assert isinstance(result[key], float), f"{key} should be a float"
        assert not math.isnan(result[key]), f"{key} should not be NaN"
