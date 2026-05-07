import numpy as np
import pandas as pd
from scipy import signal
import matplotlib.pyplot as plt
import seaborn as sns

def calculate_bpm_from_ppg(df, debug=False):
    """Process the PPG signal and compute BPM using peak detection and a rolling window approach."""
    sns.set(style="whitegrid")

    # ————— FIXED TIME CONVERSION —————
    raw_ts = pd.to_numeric(df["timestamp"], errors="coerce")
    df["timestamp"] = pd.to_datetime(raw_ts, unit="ms")
    
    base_timestamp = df["timestamp"].iloc[0]
    time = (df["timestamp"] - base_timestamp).dt.total_seconds()
    
    # ————— Raw PPG signal —————
    ppg_signal = df["PPG_mV"]
    if debug:
        plt.figure(figsize=(12, 4))
        plt.plot(time, ppg_signal, label="Raw PPG")
        plt.xlabel("Time (s)")
        plt.ylabel("PPG (mV)")
        plt.title("Raw PPG Signal")
        plt.legend()
        plt.show()
    
    # ————— Bandpass filter —————
    fs = 1.0 / np.mean(np.diff(time))
    lowcut, highcut = 0.5, 5.0
    nyq = fs / 2.0
    highcut = min(highcut, nyq * 0.99)
    lowcut = max(lowcut, nyq * 0.01)
    low, high = lowcut / nyq, highcut / nyq
    b, a = signal.butter(3, [low, high], btype='band')
    ppg_filtered = signal.filtfilt(b, a, ppg_signal)
    if debug:
        plt.figure(figsize=(12, 4))
        plt.plot(time, ppg_filtered, label="Filtered PPG", color='orange')
        plt.xlabel("Time (s)")
        plt.ylabel("Filtered PPG (mV)")
        plt.title("Bandpass-Filtered PPG (0.5-5 Hz)")
        plt.legend()
        plt.show()

    # ————— Smoothing —————
    window_size = max(1, int(fs * 0.5))
    ppg_smoothed = np.convolve(ppg_filtered, np.ones(window_size) / window_size, mode='same')
    if debug:
        plt.figure(figsize=(12, 4))
        plt.plot(time, ppg_smoothed, label="Smoothed PPG", color='green')
        plt.xlabel("Time (s)")
        plt.ylabel("Smoothed PPG (mV)")
        plt.title("Smoothed PPG (0.5s Moving Average)")
        plt.legend()
        plt.show()

    # ————— Peak Detection —————
    threshold = np.percentile(ppg_smoothed, 50)
    peaks, _ = signal.find_peaks(ppg_smoothed, height=threshold, distance=int(fs * 0.5))
    if debug:
        plt.figure(figsize=(12, 4))
        plt.plot(time, ppg_smoothed, label="Smoothed PPG", color='green')
        plt.plot(time[peaks], ppg_smoothed[peaks], "ro", label="Detected Peaks")
        plt.axhline(threshold, color='gray', linestyle='--', label='50th percentile')
        plt.xlabel("Time (s)")
        plt.ylabel("PPG")
        plt.title("Peak Detection")
        plt.legend()
        plt.show()
    
    if len(peaks) == 0:
        print("No peaks detected in PPG signal.")
        return pd.DataFrame(columns=["timestamp", "BPM"])
    
    peak_times = time[peaks]

    # ————— BPM Calculation —————
    window_length = 10  # seconds
    bpm_values = []
    bpm_times  = []

    for t in peak_times:
        recent = peak_times[(peak_times > t - window_length) & (peak_times <= t)]
        count = len(recent)
        if count > 1:
            bpm = count * (60.0 / window_length)
            bpm_values.append(bpm)
            bpm_times.append(t)

    bpm_timestamps = [base_timestamp + pd.to_timedelta(t, unit="s") for t in bpm_times]

    bpm_df = pd.DataFrame({
        "timestamp": bpm_timestamps,
        "BPM":       bpm_values
    })

    if debug and not bpm_df.empty:
        plt.figure(figsize=(12, 4))
        plt.plot(bpm_df["timestamp"], bpm_df["BPM"], marker='o', linestyle='-')
        plt.xlabel("Timestamp")
        plt.ylabel("BPM")
        plt.title("Estimated Heart Rate Over Time")
        plt.grid(True)
        plt.show()

    return bpm_df


if __name__ == "__main__":
    
    d2path = "data/eeg_study/subject_003/eeg_study_Session26_Shimmer_A5C7_Calibrated_PC.csv"
    # Load GSR dataset, adjusting headers
    d2 = pd.read_csv(d2path, header=None, skiprows=3, sep="\t", usecols=[0,1,2,3,4])  

    # Set proper column headers
    new_headers = ['timestamp', 'GSR_range', 'Skin_conductance_uS', 'Skin_resistence_kOhms', 'PPG_mV']
    d2.columns = new_headers
    
    # Convert timestamps from Unix milliseconds to datetime for merging purposes
    d2["timestamp"] = pd.to_datetime(d2["timestamp"], unit="ms") + pd.Timedelta(hours=1)
    
    # Sort data by timestamp
    d2 = d2.sort_values("timestamp")
    
    # Create a copy of d2 for BPM calculation with numeric timestamps (in ms)
    d2_for_bpm = d2.copy()
    # Convert d2_for_bpm timestamps back to numeric (ms) for BPM calculation
    d2_for_bpm["timestamp"] = d2_for_bpm["timestamp"].astype(np.int64) // 10**6  # --- Correction: integer division to get ms
    
    # Sort d2_for_bpm by timestamp (numeric)
    d2_for_bpm = d2_for_bpm.sort_values("timestamp")
    
    # Compute BPM from PPG signal using the copy with numeric timestamps
    bpm_df = calculate_bpm_from_ppg(d2_for_bpm)