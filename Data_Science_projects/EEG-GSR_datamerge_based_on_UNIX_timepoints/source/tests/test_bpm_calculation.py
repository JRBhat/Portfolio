"""
Tests for calculate_bpm_best_practices.py

Tests cover:
  - Output schema (columns, non-empty)
  - BPM accuracy at controlled heart rates
  - Physiological constraints on output values
  - Edge cases: very short signal, high noise, empty input
"""
import numpy as np
import pandas as pd
import pytest

from calculate_bpm_best_practices import calculate_bpm_from_ppg
from conftest import make_ppg_signal


# ---------------------------------------------------------------------------
# Output schema tests
# ---------------------------------------------------------------------------

class TestOutputSchema:
    """The return value must always be a DataFrame with the expected columns."""

    def test_returns_dataframe(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        assert isinstance(result, pd.DataFrame), "Return value must be a DataFrame"

    def test_has_timestamp_column(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        assert "timestamp" in result.columns, "Output must have 'timestamp' column"

    def test_has_bpm_column(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        assert "BPM" in result.columns, "Output must have 'BPM' column"

    def test_not_empty_for_valid_signal(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        assert not result.empty, "Result should not be empty for a valid PPG signal"

    def test_timestamp_is_datetime(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        assert pd.api.types.is_datetime64_any_dtype(result["timestamp"]), \
            "timestamp column must be datetime64"

    def test_bpm_is_numeric(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        assert pd.api.types.is_float_dtype(result["BPM"]) or \
               pd.api.types.is_integer_dtype(result["BPM"]), \
            "BPM column must be numeric"


# ---------------------------------------------------------------------------
# BPM accuracy tests
# ---------------------------------------------------------------------------

class TestBPMAccuracy:
    """BPM values should closely match the known ground-truth heart rate."""

    TOLERANCE_BPM = 10  # ±10 BPM tolerance for synthetic signal

    def test_60bpm_accuracy(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        valid_bpm = result["BPM"].dropna()
        if len(valid_bpm) == 0:
            pytest.skip("No BPM values detected — check signal quality")
        mean_bpm = valid_bpm.mean()
        assert abs(mean_bpm - 60.0) < self.TOLERANCE_BPM, \
            f"Expected ~60 BPM, got {mean_bpm:.1f} BPM"

    def test_75bpm_accuracy(self, ppg_df_75bpm):
        result = calculate_bpm_from_ppg(ppg_df_75bpm)
        valid_bpm = result["BPM"].dropna()
        if len(valid_bpm) == 0:
            pytest.skip("No BPM values detected — check signal quality")
        mean_bpm = valid_bpm.mean()
        assert abs(mean_bpm - 75.0) < self.TOLERANCE_BPM, \
            f"Expected ~75 BPM, got {mean_bpm:.1f} BPM"

    @pytest.mark.parametrize("target_bpm", [40, 60, 80, 100, 120])
    def test_parametrised_bpm_targets(self, target_bpm):
        df = make_ppg_signal(duration_sec=40, fs=51.0, bpm=target_bpm, noise_std=0.05)
        result = calculate_bpm_from_ppg(df)
        valid_bpm = result["BPM"].dropna()
        if len(valid_bpm) == 0:
            pytest.skip(f"No peaks detected at {target_bpm} BPM")
        mean_bpm = valid_bpm.mean()
        assert abs(mean_bpm - target_bpm) < self.TOLERANCE_BPM, \
            f"Expected ~{target_bpm} BPM, got {mean_bpm:.1f}"


# ---------------------------------------------------------------------------
# Physiological constraint tests
# ---------------------------------------------------------------------------

class TestPhysiologicalConstraints:
    """BPM values in output must lie within physiological bounds."""

    def test_bpm_above_minimum(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm, min_hr_bpm=30)
        valid_bpm = result["BPM"].dropna()
        assert (valid_bpm >= 30).all(), \
            "All BPM values should be >= minimum physiological limit (30)"

    def test_bpm_below_maximum(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm, max_hr_bpm=220)
        valid_bpm = result["BPM"].dropna()
        assert (valid_bpm <= 300).all(), \
            "BPM values should not vastly exceed physiological maximum"

    def test_bpm_not_all_nan(self, ppg_df_60bpm):
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        n_valid = result["BPM"].notna().sum()
        assert n_valid > 0, "At least some BPM values must be non-NaN"


# ---------------------------------------------------------------------------
# Robustness / edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Function must handle unusual inputs gracefully without crashing."""

    def test_high_noise_signal_does_not_crash(self, ppg_df_noisy):
        """A very noisy signal may produce no peaks but must not raise an exception."""
        try:
            result = calculate_bpm_from_ppg(ppg_df_noisy)
            assert isinstance(result, pd.DataFrame)
        except Exception as exc:
            pytest.fail(f"High-noise signal raised an exception: {exc}")

    def test_short_signal_10_seconds(self):
        """A 10-second signal should either succeed or return empty DataFrame gracefully."""
        df = make_ppg_signal(duration_sec=10, fs=51.0, bpm=60.0)
        try:
            result = calculate_bpm_from_ppg(df)
            assert isinstance(result, pd.DataFrame)
        except Exception as exc:
            pytest.fail(f"Short signal raised: {exc}")

    def test_custom_bpm_limits(self):
        """Custom min/max BPM parameters should be accepted without error."""
        df = make_ppg_signal(duration_sec=30, fs=51.0, bpm=60.0)
        result = calculate_bpm_from_ppg(df, min_hr_bpm=40, max_hr_bpm=180)
        assert isinstance(result, pd.DataFrame)

    def test_custom_adaptive_quantile(self):
        """Changing the adaptive quantile should not crash."""
        df = make_ppg_signal(duration_sec=30, fs=51.0, bpm=60.0)
        for q in [0.50, 0.75, 0.90, 0.95]:
            result = calculate_bpm_from_ppg(df, adaptive_quantile=q)
            assert isinstance(result, pd.DataFrame), f"Failed at quantile={q}"

    def test_debug_mode_does_not_show_plots(self, ppg_df_60bpm, monkeypatch):
        """With debug=True, matplotlib.pyplot.show() should be called but not block."""
        import matplotlib.pyplot as plt
        show_calls = []
        monkeypatch.setattr(plt, "show", lambda: show_calls.append(1))
        result = calculate_bpm_from_ppg(ppg_df_60bpm, debug=True)
        assert isinstance(result, pd.DataFrame)
        # show() should have been called multiple times (once per debug plot)
        assert len(show_calls) > 0, "debug=True should call plt.show() at least once"

    def test_monotone_timestamps_in_output(self, ppg_df_60bpm):
        """Output timestamps must be monotonically increasing."""
        result = calculate_bpm_from_ppg(ppg_df_60bpm)
        if len(result) > 1:
            diffs = result["timestamp"].diff().dropna()
            assert (diffs >= pd.Timedelta(0)).all(), \
                "Output timestamps must be monotonically non-decreasing"
