import os
import tempfile
import numpy as np
import pandas as pd
import pytest
import scipy.signal as signal

# Suppose your code is contained in a module named `ppg_processing`
# from ppg_processing import calculate_bpm_from_ppg, merge_device_datasets

# For this example, we'll assume the functions are defined in the current namespace.
# Replace the following two imports with your module’s import:
from super.merge_eeg_gsr_bpm_interpolated_highlighted_v2 import calculate_bpm_from_ppg, merge_device_datasets


def create_synthetic_ppg(duration=20, fs=100, peak_amplitude=10):
    """
    Create synthetic PPG data with clear peaks at 1-second intervals.
    The peaks are generated as impulse-like spikes.
    """
    t = np.linspace(0, duration, int(duration * fs))
    ppg_signal = np.zeros_like(t)
    # Insert an impulse at every whole second (except at t=0)
    for sec in range(1, int(duration)):
        idx = int(sec * fs)
        if idx < len(ppg_signal):
            ppg_signal[idx] = peak_amplitude
    # Add a little random noise
    ppg_signal += np.random.normal(0, 0.5, size=ppg_signal.shape)
    return t, ppg_signal


def test_calculate_bpm_from_ppg():
    """
    Test the BPM calculation on synthetic PPG data.
    We expect peaks at 1-second intervals, so the BPM should be around 60.
    """
    fs = 100  # samples per second
    duration = 20  # seconds
    t, ppg = create_synthetic_ppg(duration, fs)
    
    # Create a DataFrame with a 'timestamp' column in ms and a 'PPG_mV' column
    df = pd.DataFrame({
        "timestamp": (t * 1000).astype(np.int64),  # convert seconds to milliseconds
        "PPG_mV": ppg
    })
    
    bpm_df = calculate_bpm_from_ppg(df)
    
    # Ensure the resulting BPM DataFrame is not empty.
    assert not bpm_df.empty, "BPM DataFrame should not be empty when peaks are present."
    
    # Check that the computed BPM values are near 60 (with a tolerance)
    assert (bpm_df["BPM"] > 50).all() and (bpm_df["BPM"] < 70).all(), (
        "BPM values should be in the range of 50-70 for a 1-second IBI (~60 BPM)."
    )


def test_merge_device_datasets(tmp_path, monkeypatch):
    """
    Test merging of EEG and GSR/PPG datasets.
    We create synthetic EEG and GSR datasets, write them to temporary files,
    and then run merge_device_datasets. We intercept file writes to verify output.
    """
    # --- Create synthetic EEG data ---
    num_samples = 50
    # Create timestamps (simulate every 200 ms)
    timestamps = pd.to_datetime(np.arange(num_samples) * 200, unit="ms")
    eeg_data = pd.DataFrame({
        "ch1": np.random.rand(num_samples),
        "ch2": np.random.rand(num_samples),
        "ch3": np.random.rand(num_samples),
        "ch4": np.random.rand(num_samples),
        "ch5": np.random.rand(num_samples),
        "ch6": np.random.rand(num_samples),
        "ch7": np.random.rand(num_samples),
        "ch8": np.random.rand(num_samples),
        "X": np.random.rand(num_samples),
        "Y": np.random.rand(num_samples),
        "Z": np.random.rand(num_samples),
        "marker": np.random.randint(0, 2, size=num_samples),
        # Save timestamp as numeric (ms) for EEG dataset, but later converted to datetime in the function
        "timestamp": (timestamps.astype(np.int64) // 10**6)
    })
    
    eeg_file = tmp_path / "eeg_data.xlsx"
    eeg_data.to_excel(eeg_file, index=False)
    
    # --- Create synthetic GSR/PPG data ---
    # For the GSR CSV, we simulate the file with a header block to skip.
    t, ppg = create_synthetic_ppg(duration=10, fs=50)  # shorter duration, lower sampling rate for testing
    gsr_data = pd.DataFrame({
        0: (t * 1000).astype(np.int64),  # timestamp (ms)
        1: np.random.rand(len(t)),        # GSR_range
        2: np.random.rand(len(t)),        # Skin_conductance_uS
        3: np.random.rand(len(t)),        # Skin_resistence_kOhms
        4: ppg                         # PPG_mV
    })
    
    gsr_file = tmp_path / "gsr_data.csv"
    # Write dummy header lines then append the data without a header
    with open(gsr_file, "w") as f:
        f.write("Dummy header line 1\n")
        f.write("Dummy header line 2\n")
        f.write("Dummy header line 3\n")
    # Append the data as tab-separated values
    gsr_data.to_csv(gsr_file, sep="\t", header=False, index=False, mode="a")
    
    # --- Monkey-patch pandas DataFrame to_excel and to_csv methods ---
    # We want to capture the output file paths instead of writing to the hard-coded locations.
    outputs = {}
    
    def fake_to_excel(self, excel_path, index=True):
        outputs["excel"] = excel_path
        # You might also choose to verify the contents by writing to a temporary location if needed.
        
    def fake_to_csv(self, csv_path, index=True):
        outputs["csv"] = csv_path
        # Similarly, you can capture and inspect the DataFrame if desired.
    
    monkeypatch.setattr(pd.DataFrame, "to_excel", fake_to_excel)
    monkeypatch.setattr(pd.DataFrame, "to_csv", fake_to_csv)
    
    # --- Run the merge function ---
    # Since merge_device_datasets expects file path strings, convert Path objects.
    merge_device_datasets(str(eeg_file), str(gsr_file))
    
    # Verify that our fake file outputs were called.
    assert "excel" in outputs, "Expected Excel output was not generated."
    assert "csv" in outputs, "Expected CSV output was not generated."
    
    # Optionally, you could load the merged data from the fake outputs if you had written them to temporary files.
    # Here, we simply check that the output file path strings exist.
    for key in ("excel", "csv"):
        assert outputs[key] is not None and isinstance(outputs[key], str), f"{key} output should be a valid file path."


if __name__ == "__main__":
    pytest.main([__file__])
