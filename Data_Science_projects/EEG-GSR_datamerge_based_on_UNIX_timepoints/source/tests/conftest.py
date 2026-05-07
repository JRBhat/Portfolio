"""
Shared pytest fixtures for the EEG-GSR pipeline test suite.

All fixtures create in-memory or temporary-file synthetic datasets that
mirror the exact format expected by each production module.
"""
import os
import sys
import math
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Make the source directory importable when running pytest from project root
# or from within the tests/ subfolder.
# ---------------------------------------------------------------------------
_SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SOURCE_DIR not in sys.path:
    sys.path.insert(0, _SOURCE_DIR)


# ---------------------------------------------------------------------------
# Synthetic signal helpers
# ---------------------------------------------------------------------------

def make_ppg_signal(duration_sec: float = 30.0,
                    fs: float = 51.0,
                    bpm: float = 60.0,
                    noise_std: float = 0.05) -> pd.DataFrame:
    """
    Generate a synthetic PPG signal with clean heartbeat peaks at a fixed BPM.

    Parameters
    ----------
    duration_sec : float
        Length of the signal in seconds.
    fs : float
        Sampling frequency in Hz.
    bpm : float
        Target heart rate in beats per minute.
    noise_std : float
        Standard deviation of additive Gaussian noise.

    Returns
    -------
    pd.DataFrame with columns ['timestamp' (ms int64), 'PPG_mV' (float64)]
    """
    n_samples = int(duration_sec * fs)
    t = np.arange(n_samples) / fs  # seconds

    # Fundamental frequency of heartbeat
    f_heart = bpm / 60.0  # Hz

    # Simulate PPG as sum of harmonics (realistic waveform shape)
    ppg = (
        1.0 * np.sin(2 * np.pi * f_heart * t)
        + 0.5 * np.sin(2 * np.pi * 2 * f_heart * t)
        + 0.2 * np.sin(2 * np.pi * 3 * f_heart * t)
    )
    ppg += np.random.normal(0, noise_std, size=n_samples)

    # Timestamps as integer milliseconds starting from a Unix epoch
    base_ms = 1_700_000_000_000  # arbitrary fixed base
    timestamps_ms = base_ms + (t * 1000).astype(np.int64)

    return pd.DataFrame({"timestamp": timestamps_ms, "PPG_mV": ppg})


def make_eeg_dataframe(n_samples: int = 200,
                       fs_hz: float = 250.0,
                       with_markers: bool = True) -> pd.DataFrame:
    """
    Generate a synthetic EEG DataFrame in the merged-file column format.

    Returns
    -------
    pd.DataFrame with columns:
        ch1..ch8, X, Y, Z, marker, timestamp (datetime64), BPM, Skin_conductance_uS
    """
    base_ms = 1_700_000_000_000
    dt_ms = int(1000 / fs_hz)
    timestamps_ms = base_ms + np.arange(n_samples) * dt_ms
    timestamps_dt = pd.to_datetime(timestamps_ms, unit="ms")

    rng = np.random.default_rng(42)
    data = {col: rng.standard_normal(n_samples) for col in
            ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8",
             "X", "Y", "Z"]}
    data["timestamp"] = timestamps_dt
    data["marker"] = 0

    if with_markers:
        # Place markers at 4 evenly spaced positions
        for i, pos in enumerate([20, 60, 100, 140], start=1):
            data["marker"][pos] = i

    data["BPM"] = rng.uniform(55, 85, size=n_samples)
    data["Skin_conductance_uS"] = rng.uniform(1.5, 8.0, size=n_samples)

    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ppg_df_60bpm():
    """PPG DataFrame at exactly 60 BPM."""
    return make_ppg_signal(duration_sec=30, fs=51.0, bpm=60.0, noise_std=0.05)


@pytest.fixture
def ppg_df_75bpm():
    """PPG DataFrame at 75 BPM."""
    return make_ppg_signal(duration_sec=30, fs=51.0, bpm=75.0, noise_std=0.05)


@pytest.fixture
def ppg_df_noisy():
    """High-noise PPG — BPM detection should still succeed."""
    return make_ppg_signal(duration_sec=30, fs=51.0, bpm=60.0, noise_std=0.3)


@pytest.fixture
def eeg_df():
    """Synthetic merged EEG DataFrame with 4 markers."""
    return make_eeg_dataframe(n_samples=500, fs_hz=250.0, with_markers=True)


@pytest.fixture
def segments_clinical(eeg_df):
    """
    Synthetic segments list in the format produced by generate_plots(),
    matching the 6-timepoint clinical structure.
    """
    rng = np.random.default_rng(0)
    n_timepoints = 6
    segments = []
    chunk_size = 60  # rows per segment
    for i in range(n_timepoints):
        seg_df = pd.DataFrame({
            "BPM": rng.uniform(60, 80, chunk_size),
            "Skin_conductance_uS": rng.uniform(2.0, 6.0, chunk_size),
        })
        segments.append({"marker": i + 1, "data": seg_df})
    return segments


@pytest.fixture
def segments_masterarbeit():
    """
    Synthetic segments list for the 4-timepoint Masterarbeit structure.
    """
    rng = np.random.default_rng(1)
    n_timepoints = 4
    segments = []
    for i in range(n_timepoints):
        seg_df = pd.DataFrame({
            "BPM": rng.uniform(60, 80, 100),
            "Skin_conductance_uS": rng.uniform(2.0, 6.0, 100),
        })
        segments.append({"marker": i + 1, "data": seg_df})
    return segments


@pytest.fixture
def faa_output_clinical():
    """Synthetic FAA values for clinical study."""
    return {
        "FAA_baseline": 0.142,
        "FAA_applk": 0.198,
        "FAA_5min": 0.215,
        "FAA_10min": 0.230,
        "FAA_15min": 0.250,
        "FAA_20min": 0.270,
    }


@pytest.fixture
def faa_output_masterarbeit():
    """Synthetic FAA values for Masterarbeit study."""
    return {"FAA_pre": -0.05, "FAA_post": 0.12}


@pytest.fixture
def tmp_subject_dir(tmp_path):
    """
    Create a temporary subject directory structure:
        tmp_path/
            01_Subject/
                statistics_01_Subject_Subject.xlsx
                BPM_Subject_matplotlib.png
    """
    subj_dir = tmp_path / "01_Subject"
    subj_dir.mkdir()
    return subj_dir
