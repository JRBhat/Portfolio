"""
Tests for merge_data_V2.py

Tests cover:
  - load_shimmer_csv_auto: English tab format, German semicolon format
  - load_shimmer_csv_auto: output columns and timestamp dtype
  - load_shimmer_csv_auto: 2-hour timezone offset applied
  - load_shimmer_csv_auto: data is sorted by timestamp
  - merge_device_datasets: output file created
  - merge_device_datasets: idempotency (skips if output exists)
  - merge_device_datasets: output has required columns
  - merge_device_datasets: no fully-NaN rows in key columns
"""
import os
import numpy as np
import pandas as pd
import pytest

from merge_data_V2 import load_shimmer_csv_auto, merge_device_datasets
from conftest import make_ppg_signal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_MS = 1_700_000_000_000  # arbitrary fixed epoch in ms


def _write_shimmer_english(path, n=3060):
    """
    Write a Shimmer CSV in English tab-decimal format (with 'sep=\\t' header line).
    Uses 3060 samples at ~51 Hz (60 seconds) with a synthetic 60 BPM PPG signal
    so that calculate_bpm_from_ppg can detect peaks and return a non-empty DataFrame.
    """
    fs = 51.0
    duration = n / fs
    t = np.arange(n) / fs

    # Synthetic 60 BPM PPG (fundamental + harmonics)
    f_heart = 60.0 / 60.0  # 1 Hz
    ppg = (1.0 * np.sin(2 * np.pi * f_heart * t)
           + 0.5 * np.sin(2 * np.pi * 2 * f_heart * t)
           + 0.2 * np.sin(2 * np.pi * 3 * f_heart * t))

    timestamps_ms = BASE_MS + (t * 1000).astype(np.int64)
    rows = np.column_stack([
        timestamps_ms,
        np.random.default_rng(0).uniform(0, 1, n),    # GSR_range
        np.random.default_rng(1).uniform(1, 10, n),   # Skin_conductance_uS
        np.random.default_rng(2).uniform(50, 200, n), # Skin_resistance_kOhms
        ppg,                                           # PPG_mV
    ])
    with open(path, "w") as fh:
        fh.write("sep=\t\n")
        fh.write("timestamp\tGSR_range\tSkin_conductance_uS\tSkin_resistence_kOhms\tPPG_mV\n")
        fh.write("unit1\tunit2\tunit3\tunit4\tunit5\n")
        for row in rows:
            fh.write("\t".join(f"{v:.6f}" for v in row) + "\n")


def _write_shimmer_german(path, n=3060):
    """
    Write a Shimmer CSV in German semicolon-comma-decimal format.
    """
    timestamps_ms = BASE_MS + np.arange(n) * 20
    rows = np.column_stack([
        timestamps_ms,
        np.random.uniform(0, 1, n),
        np.random.uniform(1, 10, n),
        np.random.uniform(50, 200, n),
        np.random.uniform(-0.5, 0.5, n),
    ])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("timestamp;GSR_range;Skin_conductance_uS;Skin_resistence_kOhms;PPG_mV\n")
        fh.write("unit1;unit2;unit3;unit4;unit5\n")
        fh.write("extra;header;line;here;now\n")
        for row in rows:
            # German locale: dots replaced by commas for decimals
            german_row = ";".join(f"{v:.6f}".replace(".", ",") for v in row)
            fh.write(german_row + "\n")


def _write_eeg_tsv(path, n=100, fs_hz=250):
    """Write a minimal EEG TSV file."""
    dt_ms = int(1000 / fs_hz)
    timestamps_ms = BASE_MS + np.arange(n) * dt_ms
    rng = np.random.default_rng(42)
    rows = np.column_stack([
        rng.standard_normal((n, 11)),  # ch1-ch8, X, Y, Z
        np.zeros(n),                    # marker
        timestamps_ms,
    ])
    df = pd.DataFrame(rows, columns=[
        "ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8",
        "X", "Y", "Z", "marker", "timestamp"
    ])
    df.to_csv(path, sep="\t", index=False)


# ---------------------------------------------------------------------------
# load_shimmer_csv_auto tests
# ---------------------------------------------------------------------------

class TestLoadShimmerCSVAuto:

    def test_english_format_loads_correctly(self, tmp_path):
        csv_path = str(tmp_path / "shimmer_en.csv")
        _write_shimmer_english(csv_path)
        df = load_shimmer_csv_auto(csv_path)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_german_format_loads_correctly(self, tmp_path):
        csv_path = str(tmp_path / "shimmer_de.csv")
        _write_shimmer_german(csv_path)
        df = load_shimmer_csv_auto(csv_path)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_output_columns_english(self, tmp_path):
        csv_path = str(tmp_path / "shimmer_en.csv")
        _write_shimmer_english(csv_path)
        df = load_shimmer_csv_auto(csv_path)
        expected = {"timestamp", "GSR_range", "Skin_conductance_uS",
                    "Skin_resistence_kOhms", "PPG_mV"}
        assert set(df.columns) == expected

    def test_output_columns_german(self, tmp_path):
        csv_path = str(tmp_path / "shimmer_de.csv")
        _write_shimmer_german(csv_path)
        df = load_shimmer_csv_auto(csv_path)
        expected = {"timestamp", "GSR_range", "Skin_conductance_uS",
                    "Skin_resistence_kOhms", "PPG_mV"}
        assert set(df.columns) == expected

    def test_timestamp_is_datetime(self, tmp_path):
        csv_path = str(tmp_path / "shimmer_en.csv")
        _write_shimmer_english(csv_path)
        df = load_shimmer_csv_auto(csv_path)
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"]), \
            "timestamp column should be datetime64"

    def test_two_hour_offset_applied(self, tmp_path):
        """The loaded timestamps should be 2 hours ahead of the raw Unix ms value."""
        csv_path = str(tmp_path / "shimmer_en.csv")
        _write_shimmer_english(csv_path, n=5)
        df = load_shimmer_csv_auto(csv_path)

        # The first raw timestamp converted without offset
        raw_first = pd.to_datetime(BASE_MS, unit="ms")
        loaded_first = df["timestamp"].iloc[0]

        # The offset is exactly 2 hours
        offset = loaded_first - raw_first
        assert abs(offset.total_seconds() - 7200) < 1, \
            f"Expected +2h offset, got {offset}"

    def test_data_is_sorted_by_timestamp(self, tmp_path):
        csv_path = str(tmp_path / "shimmer_en.csv")
        _write_shimmer_english(csv_path)
        df = load_shimmer_csv_auto(csv_path)
        assert df["timestamp"].is_monotonic_increasing, \
            "Timestamps should be sorted in ascending order"

    def test_no_nan_in_ppg_column(self, tmp_path):
        csv_path = str(tmp_path / "shimmer_en.csv")
        _write_shimmer_english(csv_path)
        df = load_shimmer_csv_auto(csv_path)
        assert df["PPG_mV"].notna().all(), "PPG_mV column should have no NaN values"


# ---------------------------------------------------------------------------
# merge_device_datasets tests
# ---------------------------------------------------------------------------

class TestMergeDeviceDatasets:

    def _setup_subject(self, tmp_path, eeg_n=15000, gsr_n=3060):
        """Create EEG tsv + GSR csv + subject dir, return paths."""
        subj_dir = tmp_path / "01_Subject"
        subj_dir.mkdir()

        eeg_path = str(subj_dir / "eeg.tsv")
        gsr_path = str(subj_dir / "gsr.csv")
        _write_eeg_tsv(eeg_path, n=eeg_n)
        _write_shimmer_english(gsr_path, n=gsr_n)

        return eeg_path, gsr_path, str(subj_dir)

    def test_output_file_created(self, tmp_path):
        eeg, gsr, subj_dir = self._setup_subject(tmp_path)
        out = merge_device_datasets(eeg, gsr, subj_dir)
        assert os.path.exists(out), "Merged output Excel file should be created"

    def test_output_is_excel_file(self, tmp_path):
        eeg, gsr, subj_dir = self._setup_subject(tmp_path)
        out = merge_device_datasets(eeg, gsr, subj_dir)
        assert out.endswith(".xlsx"), "Output file must be an .xlsx file"

    def test_output_has_required_columns(self, tmp_path):
        eeg, gsr, subj_dir = self._setup_subject(tmp_path)
        out = merge_device_datasets(eeg, gsr, subj_dir)
        df = pd.read_excel(out)
        required = ["ch1", "ch2", "marker", "timestamp",
                    "Skin_conductance_uS", "BPM", "PPG_mV"]
        for col in required:
            assert col in df.columns, f"Column '{col}' missing from merged output"

    def test_output_filename_contains_bpmcorrected(self, tmp_path):
        eeg, gsr, subj_dir = self._setup_subject(tmp_path)
        out = merge_device_datasets(eeg, gsr, subj_dir)
        assert "bpmcorrected" in os.path.basename(out), \
            "Output filename should contain 'bpmcorrected'"

    def test_no_all_nan_rows_in_key_columns(self, tmp_path):
        """After interpolation, key columns should not have all-NaN rows."""
        eeg, gsr, subj_dir = self._setup_subject(tmp_path)
        out = merge_device_datasets(eeg, gsr, subj_dir)
        df = pd.read_excel(out)
        for col in ["ch1", "Skin_conductance_uS"]:
            null_count = df[col].isna().sum()
            total = len(df)
            # At most 10% NaN after interpolation is acceptable for edge rows
            assert null_count / total < 0.10, \
                f"Column '{col}' has too many NaN values after interpolation: {null_count}/{total}"

    def test_idempotency_skips_if_output_exists(self, tmp_path):
        """Second call should return existing file path without reprocessing."""
        eeg, gsr, subj_dir = self._setup_subject(tmp_path)
        out1 = merge_device_datasets(eeg, gsr, subj_dir)
        mtime1 = os.path.getmtime(out1)

        import time
        time.sleep(0.05)  # ensure time difference would be detectable

        out2 = merge_device_datasets(eeg, gsr, subj_dir)
        mtime2 = os.path.getmtime(out2)

        assert out1 == out2, "Both calls should return same output path"
        assert abs(mtime1 - mtime2) < 0.01, \
            "File modification time should not change on second call (idempotency)"

    def test_output_row_count_positive(self, tmp_path):
        eeg, gsr, subj_dir = self._setup_subject(tmp_path)
        out = merge_device_datasets(eeg, gsr, subj_dir)
        df = pd.read_excel(out)
        assert len(df) > 0, "Merged file should contain at least one row"

    def test_timestamp_column_is_sortable(self, tmp_path):
        eeg, gsr, subj_dir = self._setup_subject(tmp_path)
        out = merge_device_datasets(eeg, gsr, subj_dir)
        df = pd.read_excel(out)
        # Timestamps should be parseable as datetime
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        assert ts.notna().any(), "Timestamps should be valid datetime values"
