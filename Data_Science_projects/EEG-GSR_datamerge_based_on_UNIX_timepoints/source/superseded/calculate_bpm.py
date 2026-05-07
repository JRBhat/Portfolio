import pandas as pd
import numpy as np
import scipy.signal as signal


def calculate_bpm_from_ppg(df):
    """Process the PPG signal and compute BPM using peak detection and a rolling window approach."""
    # diagnose_ppg(df)
    
    # ————— FIXED TIME CONVERSION —————
    # Shimmer timestamps are in ms since epoch → parse accordingly
    raw_ts = pd.to_numeric(df["timestamp"], errors="coerce")                  # ← FIXED
    df["timestamp"] = pd.to_datetime(raw_ts, unit="ms")                       # ← FIXED
    
    base_timestamp = df["timestamp"].iloc[0]
    time = (df["timestamp"] - base_timestamp).dt.total_seconds()               # ← FIXED
    # ————————————————————————————————————
    
    # Extract PPG
    ppg_signal = df["PPG_mV"]
    
    # Sampling rate
    fs = 1.0 / np.mean(np.diff(time))
    # print("Sampling frequency (fs):", fs)
    
    # Bandpass filter 0.5–5 Hz
    lowcut, highcut = 0.5, 5.0
    nyq = fs / 2.0
    if highcut >= nyq:
        highcut = nyq * 0.99
    if lowcut <= 0:
        lowcut = nyq * 0.01
    low  = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(3, [low, high], btype='band')
    ppg_filtered = signal.filtfilt(b, a, ppg_signal)
    
    # Smooth (0.5 s MA)
    window_size = max(1, int(fs * 0.5))
    ppg_smoothed = np.convolve(ppg_filtered,
                               np.ones(window_size) / window_size,
                               mode='same')
    
    # ————— FIXED PEAK DETECTION THRESHOLD —————
    # Lower from 75th to 50th percentile so fewer beats are missed
    threshold = np.percentile(ppg_smoothed, 50)                              # ← FIXED
    peaks, _ = signal.find_peaks(ppg_smoothed,
                                 height=threshold,
                                 distance=int(fs * 0.5))
    if len(peaks) == 0:
        print("No peaks detected in PPG signal.")
        return pd.DataFrame(columns=["timestamp", "BPM"])
    peak_times = time[peaks]
    # ————————————————————————————————————
    
    # ————— FIXED BPM CALCULATION (COUNT-BASED) —————
    window_length = 10  # seconds
    bpm_values = []
    bpm_times  = []
    
    for t in peak_times:
        recent = peak_times[(peak_times > t - window_length) & (peak_times <= t)]
        count = len(recent)
        if count > 1:
            bpm = count * (60.0 / window_length)                               # ← FIXED
            bpm_values.append(bpm)
            bpm_times.append(t)
    # ————————————————————————————————————
    
    # Convert back to timestamps
    bpm_timestamps = [base_timestamp + pd.to_timedelta(t, unit="s") 
                      for t in bpm_times]
    
    return pd.DataFrame({
        "timestamp": bpm_timestamps,
        "BPM":       bpm_values
    })



if __name__ == "__main__":
    
    d2path = "data/eeg_study/subject_001/eeg_study_Session23_Shimmer_A5C7_Calibrated_PC.csv"
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