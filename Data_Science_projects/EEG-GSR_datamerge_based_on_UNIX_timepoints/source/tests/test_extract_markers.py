"""
Tests for extract_markers.py

Tests cover:
  - Marker remapping: 2 → 8, 3 → 9
  - Marker serialization: remaining 1–7 become sequential 1, 2, 3, ...
  - Idempotency: output file reused if it already exists
  - Edge cases: no markers, only 0 markers, mixed marker types
  - Output file is valid Excel with required columns
"""
import os
import pandas as pd
import pytest

from extract_markers import extract_and_serialize_marker_ones


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_marker_xlsx(tmp_path, markers: list, filename="merged.xlsx") -> str:
    """Create a minimal Excel file with 'marker' and 'timestamp' columns."""
    n = len(markers)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="4ms"),
        "marker": markers,
        "ch1": range(n),  # extra column to verify it passes through
    })
    path = str(tmp_path / filename)
    df.to_excel(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Remapping tests (2 → 8, 3 → 9)
# ---------------------------------------------------------------------------

class TestMarkerRemapping:

    def test_marker_2_remapped_to_8(self, tmp_path):
        path = _make_marker_xlsx(tmp_path, [0, 2, 0, 1])
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        assert 8 in df["marker"].values, "Marker 2 should be remapped to 8"

    def test_marker_3_remapped_to_9(self, tmp_path):
        path = _make_marker_xlsx(tmp_path, [0, 3, 0, 1])
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        assert 9 in df["marker"].values, "Marker 3 should be remapped to 9"

    def test_original_2_not_present_after_remap(self, tmp_path):
        path = _make_marker_xlsx(tmp_path, [2, 2, 1])
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        non_zero = df["marker"][df["marker"] != 0]
        assert 2 not in non_zero.values, "Original marker 2 should not remain after remapping"

    def test_original_3_not_present_after_remap(self, tmp_path):
        path = _make_marker_xlsx(tmp_path, [3, 1, 3])
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        non_zero = df["marker"][df["marker"] != 0]
        assert 3 not in non_zero.values, "Original marker 3 should not remain after remapping"


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------

class TestMarkerSerialization:

    def test_six_markers_serialized_1_to_6(self, tmp_path):
        """clinical-typical case: 6 marker-1 events become 1,2,3,4,5,6."""
        # 6 marker-1 events interspersed with zeros
        markers = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        path = _make_marker_xlsx(tmp_path, markers)
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        serialized = sorted(df["marker"][df["marker"] > 0].values)
        assert serialized == [1, 2, 3, 4, 5, 6], \
            f"Expected [1,2,3,4,5,6], got {serialized}"

    def test_single_marker_becomes_1(self, tmp_path):
        path = _make_marker_xlsx(tmp_path, [0, 1, 0])
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        serialized = df["marker"][df["marker"] > 0].values
        assert list(serialized) == [1]

    def test_four_markers_serialized(self, tmp_path):
        """Masterarbeit-typical: 4 markers become 1,2,3,4."""
        markers = [1, 0, 1, 0, 1, 0, 1]
        path = _make_marker_xlsx(tmp_path, markers)
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        serialized = sorted(df["marker"][df["marker"] > 0].values)
        assert serialized == [1, 2, 3, 4]

    def test_remapped_markers_not_serialized(self, tmp_path):
        """Markers 2 and 3 become 8 and 9, not serialized to 1+."""
        markers = [2, 1, 3, 1]  # two remapped, two serialized
        path = _make_marker_xlsx(tmp_path, markers)
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        # Should have 8, 9 for the remapped markers and 1, 2 for the serialized
        marker_vals = set(df["marker"][df["marker"] != 0].values)
        assert 8 in marker_vals
        assert 9 in marker_vals
        assert 1 in marker_vals
        assert 2 in marker_vals

    def test_serialization_order_is_temporal(self, tmp_path):
        """Serialized numbers should follow temporal order of appearance."""
        markers = [0, 1, 0, 0, 1, 0, 1]
        path = _make_marker_xlsx(tmp_path, markers)
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        serial_vals = df["marker"][df["marker"] > 0].tolist()
        # Should be [1, 2, 3] in order
        assert serial_vals == sorted(serial_vals), \
            "Serialized markers must increase chronologically"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_all_zero_markers(self, tmp_path):
        """File with only zero markers should produce unchanged output."""
        path = _make_marker_xlsx(tmp_path, [0, 0, 0, 0])
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        assert (df["marker"] == 0).all(), "All-zero markers should remain zero"

    def test_output_file_is_valid_excel(self, tmp_path):
        path = _make_marker_xlsx(tmp_path, [1, 2, 3])
        out = extract_and_serialize_marker_ones(path)
        assert out.endswith(".xlsx"), "Output must be an Excel file"
        df = pd.read_excel(out)
        assert "marker" in df.columns
        assert "timestamp" in df.columns

    def test_extra_columns_preserved(self, tmp_path):
        """Non-marker columns in the file must pass through unchanged."""
        path = _make_marker_xlsx(tmp_path, [1, 0, 1])
        out = extract_and_serialize_marker_ones(path)
        df = pd.read_excel(out)
        assert "ch1" in df.columns, "Extra columns should be preserved in output"

    def test_output_row_count_unchanged(self, tmp_path):
        """The number of rows must not change during marker processing."""
        markers = [0, 1, 2, 3, 0, 1, 0]
        path = _make_marker_xlsx(tmp_path, markers)
        out = extract_and_serialize_marker_ones(path)
        df_in = pd.read_excel(path)
        df_out = pd.read_excel(out)
        assert len(df_in) == len(df_out), "Row count must be preserved"


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------

class TestIdempotency:

    def test_output_reused_if_exists(self, tmp_path):
        """If _markers_corrected.xlsx already exists, it is returned without reprocessing."""
        path = _make_marker_xlsx(tmp_path, [1, 1, 1])
        out1 = extract_and_serialize_marker_ones(path)
        assert os.path.exists(out1)

        # Call again — should return same path without re-processing
        out2 = extract_and_serialize_marker_ones(path)
        assert out1 == out2, "Same output path should be returned on second call"

    def test_output_path_naming_convention(self, tmp_path):
        """Output filename follows the _markers_corrected suffix convention."""
        path = _make_marker_xlsx(tmp_path, [1])
        out = extract_and_serialize_marker_ones(path)
        assert "_markers_corrected.xlsx" in out, \
            "Output filename must contain '_markers_corrected'"
