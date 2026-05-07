"""
Tests for generate_stats.py

Tests cover:
  - generate_statistics_clinical: output file created, correct columns, correct timepoints
  - generate_statistics_Masterarbeit: output file created, correct timepoints
  - Median values are computed correctly
  - FAA values are attached correctly
  - Idempotency (skips if output exists)
  - Missing FAA keys result in NaN (not a crash)
"""
import math
import os
import numpy as np
import pandas as pd
import pytest

from generate_stats import generate_statistics_clinical, generate_statistics_Masterarbeit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_subject_path(tmp_path, subject_folder="01_Subject"):
    """
    Create a fake subject directory and return a fake merged file path
    whose parent directory basename can be used as the subject identifier.
    """
    subj_dir = tmp_path / subject_folder
    subj_dir.mkdir(exist_ok=True)
    # The functions derive subject name from merged_file_path.split("\\")[-2]
    # On Windows this works naturally; on Linux we simulate with a path string.
    merged_path = str(subj_dir / "merged_highlighted_Subject_bpmcorrected.xlsx")
    return merged_path, str(subj_dir)


def _make_segments(n: int, bpm_median: float = 70.0, sc_median: float = 4.0):
    """Create n synthetic segments with predictable medians."""
    segments = []
    for _ in range(n):
        # 100-row window where the median is exactly bpm_median / sc_median
        bpm_values = [bpm_median] * 100
        sc_values = [sc_median] * 100
        seg_df = pd.DataFrame({
            "BPM": bpm_values,
            "Skin_conductance_uS": sc_values,
        })
        segments.append({"marker": 1, "data": seg_df})
    return segments


# ---------------------------------------------------------------------------
# clinical statistics tests
# ---------------------------------------------------------------------------

class TestGenerateStatisticsclinical:

    def test_output_file_created(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(6)
        faa = {
            "FAA_baseline": 0.1, "FAA_applk": 0.2, "FAA_5min": 0.3,
            "FAA_10min": 0.4, "FAA_15min": 0.5, "FAA_20min": 0.6,
        }
        generate_statistics_clinical(segments, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])
        expected_dir = os.path.dirname(merged_path)
        excel_files = [f for f in os.listdir(expected_dir) if f.startswith("statistics_") and f.endswith(".xlsx")]
        assert len(excel_files) == 1, "Exactly one statistics Excel file should be created"

    def test_output_has_correct_columns(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(6)
        faa = {k: 0.0 for k in ["FAA_baseline", "FAA_applk", "FAA_5min", "FAA_10min", "FAA_15min", "FAA_20min"]}
        generate_statistics_clinical(segments, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        for col in ["Timepoint", "BPM", "Skin_conductance_uS", "FAA"]:
            assert col in df.columns, f"Column '{col}' missing from statistics output"

    def test_output_has_six_rows(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(6)
        faa = {k: 0.0 for k in ["FAA_baseline", "FAA_applk", "FAA_5min", "FAA_10min", "FAA_15min", "FAA_20min"]}
        generate_statistics_clinical(segments, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        assert len(df) == 6, f"Expected 6 rows (one per timepoint), got {len(df)}"

    def test_timepoint_labels_are_correct(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(6)
        faa = {k: 0.0 for k in ["FAA_baseline", "FAA_applk", "FAA_5min", "FAA_10min", "FAA_15min", "FAA_20min"]}
        generate_statistics_clinical(segments, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        timepoints = df["Timepoint"].tolist()
        assert timepoints[0] == "Baseline"
        assert "application" in timepoints[1].lower()
        assert "5min" in timepoints[2].lower()

    def test_bpm_median_is_correct(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(6, bpm_median=72.5)
        faa = {k: 0.0 for k in ["FAA_baseline", "FAA_applk", "FAA_5min", "FAA_10min", "FAA_15min", "FAA_20min"]}
        generate_statistics_clinical(segments, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        assert all(abs(df["BPM"] - 72.5) < 0.01), "Median BPM values should be 72.5"

    def test_faa_values_attached_correctly(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(6)
        faa = {
            "FAA_baseline": 0.10, "FAA_applk": 0.20, "FAA_5min": 0.30,
            "FAA_10min": 0.40, "FAA_15min": 0.50, "FAA_20min": 0.60,
        }
        generate_statistics_clinical(segments, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        assert abs(df["FAA"].iloc[0] - 0.10) < 1e-6, "FAA_baseline should be 0.10"
        assert abs(df["FAA"].iloc[5] - 0.60) < 1e-6, "FAA_20min should be 0.60"

    def test_missing_faa_key_produces_nan(self, tmp_path):
        """If a FAA key is not in faa_output, the FAA cell should be NaN."""
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(6)
        faa = {}  # Empty dict: all FAA values will be NaN
        generate_statistics_clinical(segments, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        assert df["FAA"].isna().all(), "Missing FAA keys should produce NaN values"

    def test_idempotency(self, tmp_path):
        """Second call should skip generation if output already exists."""
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(6, bpm_median=70.0)
        faa = {k: 0.0 for k in ["FAA_baseline", "FAA_applk", "FAA_5min", "FAA_10min", "FAA_15min", "FAA_20min"]}

        generate_statistics_clinical(segments, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])

        # Change BPM to verify caching (second call should not overwrite)
        segments2 = _make_segments(6, bpm_median=99.0)
        generate_statistics_clinical(segments2, faa, merged_path, variables=["BPM", "Skin_conductance_uS"])

        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        # Should still be 70.0 from first call
        assert all(abs(df["BPM"] - 70.0) < 0.01), \
            "Second call should not overwrite existing statistics file"


# ---------------------------------------------------------------------------
# Masterarbeit statistics tests
# ---------------------------------------------------------------------------

class TestGenerateStatisticsMasterarbeit:

    def test_output_file_created(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(4)
        faa = {"FAA_pre": -0.05, "FAA_post": 0.12}
        generate_statistics_Masterarbeit(segments, faa, merged_path)
        excel_files = [f for f in os.listdir(os.path.dirname(merged_path))
                       if f.startswith("statistics_") and f.endswith(".xlsx")]
        assert len(excel_files) == 1

    def test_output_has_four_rows(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(4)
        faa = {"FAA_pre": -0.05, "FAA_post": 0.12}
        generate_statistics_Masterarbeit(segments, faa, merged_path)
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        assert len(df) == 4

    def test_masterarbeit_timepoint_labels(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(4)
        faa = {"FAA_pre": -0.05, "FAA_post": 0.12}
        generate_statistics_Masterarbeit(segments, faa, merged_path)
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        timepoints = df["Timepoint"].tolist()
        assert "Pre" in timepoints[0]
        assert "Post" in timepoints[3]

    def test_faa_pre_attached_to_first_segment(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(4)
        faa = {"FAA_pre": -0.05, "FAA_post": 0.12}
        generate_statistics_Masterarbeit(segments, faa, merged_path)
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        assert abs(df["FAA"].iloc[0] - (-0.05)) < 1e-6, "FAA_pre should be in first row"

    def test_faa_post_attached_to_last_segment(self, tmp_path):
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(4)
        faa = {"FAA_pre": -0.05, "FAA_post": 0.12}
        generate_statistics_Masterarbeit(segments, faa, merged_path)
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        assert abs(df["FAA"].iloc[3] - 0.12) < 1e-6, "FAA_post should be in last row"

    def test_middle_segments_have_nan_faa(self, tmp_path):
        """Segments 2 and 3 (Application, CPT) have no FAA → should be NaN."""
        merged_path, _ = _make_subject_path(tmp_path)
        segments = _make_segments(4)
        faa = {"FAA_pre": -0.05, "FAA_post": 0.12}
        generate_statistics_Masterarbeit(segments, faa, merged_path)
        excel_file = [f for f in os.listdir(os.path.dirname(merged_path)) if f.startswith("statistics_")][0]
        df = pd.read_excel(os.path.join(os.path.dirname(merged_path), excel_file))
        assert math.isnan(df["FAA"].iloc[1]), "Row 2 (Application) should have NaN FAA"
        assert math.isnan(df["FAA"].iloc[2]), "Row 3 (CPT) should have NaN FAA"
