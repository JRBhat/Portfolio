import pandas as pd
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt

def calculate_bpm_from_ppg(df):
    """Process the PPG signal and compute BPM using peak detection and a rolling window approach."""
    
    # --- Correction Start ---
    # If the timestamp column is datetime, convert it to numeric (milliseconds)
    if pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = df["timestamp"].astype(np.int64) / 1e6  
        print("Converted datetime timestamps to numeric (ms).")
    # --- Correction End ---
    
    # Ensure timestamps are numeric (should now be in milliseconds)
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    
    # Save the base timestamp (first timestamp) as a datetime for later conversion
    base_timestamp = pd.to_datetime(df["timestamp"].iloc[0], unit="ms")  # --- Correction
    
    # Convert time differences from ms to seconds (relative time)
    time = (df["timestamp"] - df["timestamp"].iloc[0]) / 1000  # Now in seconds
    
    # Extract PPG signal
    ppg_signal = df["PPG_mV"]
    
    # Determine sampling frequency (Hz)
    dt = np.diff(time)
    fs = 1 / np.mean(dt)
    print("Sampling frequency (fs):", fs)
    
    # Desired cutoff frequencies in Hz
    desired_lowcut, desired_highcut = 0.5, 5
    nyquist = fs / 2.0
    if nyquist <= desired_lowcut:
        raise ValueError(f"Sampling frequency too low. Nyquist ({nyquist} Hz) must be greater than lowcut ({desired_lowcut} Hz).")
    
    # Normalize the cutoff frequencies
    low = desired_lowcut / nyquist
    high = desired_highcut / nyquist

    # Adjust if necessary to be safely within (0, 1)
    if low <= 0:
        low = 0.01  # minimal normalized frequency
        print("Adjusted normalized low cutoff to 0.01")
    if high >= 1:
        high = 0.99  # maximal normalized frequency
        print("Adjusted normalized high cutoff to 0.99")
    if high <= low:
        raise ValueError("Normalized high cutoff must be greater than normalized low cutoff.")
    
    print("Normalized low cutoff:", low, "Normalized high cutoff:", high)
    
    # Apply a bandpass filter with the adjusted cutoffs
    b, a = signal.butter(3, [low, high], btype='band')
    ppg_filtered = signal.filtfilt(b, a, ppg_signal)

    # Smooth the signal with a moving average filter
    window_size = int(fs * 0.5)
    if window_size < 1:
        window_size = 1  # Correction: Ensure window_size is at least 1
    ppg_smoothed = np.convolve(ppg_filtered, np.ones(window_size) / window_size, mode='same')

    # Peak detection using an adaptive threshold (75th percentile)
    percentile_value = np.percentile(ppg_smoothed, 75)
    peaks, _ = signal.find_peaks(ppg_smoothed, height=percentile_value, distance=int(fs * 0.5))
    
    if len(peaks) == 0:
        print("No peaks detected in PPG signal.")
        return pd.DataFrame(columns=["timestamp", "BPM"])
    
    # Extract peak times (relative time in seconds)
    peak_times = time.iloc[peaks]

    # Compute BPM using a rolling 10-second window
    window_length = 10  
    bpm_values = []
    bpm_times = []

    for i in range(1, len(peak_times)):
        recent_peaks = peak_times[peak_times > (peak_times.iloc[i] - window_length)]
        if len(recent_peaks) > 1:
            ibi = np.diff(recent_peaks)  # Inter-beat intervals in seconds
            avg_ibi = np.mean(ibi)
            bpm = 60 / avg_ibi  # Convert to BPM
            bpm_values.append(bpm)
            bpm_times.append(peak_times.iloc[i])
    
    # Convert the relative peak times (in seconds) back to absolute datetime
    # --- Correction Start ---
    bpm_times = [base_timestamp + pd.to_timedelta(t, unit='s') for t in bpm_times]
    # --- Correction End ---
    
    # Convert BPM results into a DataFrame
    bpm_df = pd.DataFrame({
        "timestamp": bpm_times,
        "BPM": bpm_values
    })
    
    return bpm_df


def merge_device_datasets(d1path, d2path):
    """Merge EEG and GSR datasets, replacing PPG_mV with BPM values."""
    
    # Load EEG dataset (expected to contain timepoint and EEG values)
    d1 = pd.read_excel(d1path)  
    
    # Load GSR dataset, adjusting headers
    d2 = pd.read_csv(d2path, header=None, skiprows=3, sep="\t", usecols=[0,1,2,3,4])  

    # Set proper column headers
    d1.columns = ['ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'ch8', 'X', 'Y', 'Z', 'marker', 'timestamp']
    new_headers = ['timestamp', 'GSR_range', 'Skin_conductance_uS', 'Skin_resistence_kOhms', 'PPG_mV']
    d2.columns = new_headers
    
    # Convert timestamps from Unix milliseconds to datetime for merging purposes
    d1["timestamp"] = pd.to_datetime(d1["timestamp"], unit="ms")
    d2["timestamp"] = pd.to_datetime(d2["timestamp"], unit="ms")
    
    # Sort data by timestamp
    d1 = d1.sort_values("timestamp")
    d2 = d2.sort_values("timestamp")
    
    # Create a copy of d2 for BPM calculation with numeric timestamps (in ms)
    d2_for_bpm = d2.copy()
    # Convert d2_for_bpm timestamps back to numeric (ms) for BPM calculation
    d2_for_bpm["timestamp"] = d2_for_bpm["timestamp"].astype(np.int64) // 10**6  # Correction: integer division to get ms
    
    # Sort d2_for_bpm by timestamp (numeric)
    d2_for_bpm = d2_for_bpm.sort_values("timestamp")
    
    # Compute BPM from PPG signal using the copy with numeric timestamps
    bpm_df = calculate_bpm_from_ppg(d2_for_bpm)

    # Merge EEG and GSR datasets using an outer join
    merged_outer = pd.merge(d1, d2, on="timestamp", how="outer", sort=True)

    # Merge BPM results, replacing PPG_mV with BPM using a nearest match (tolerance 100ms)
    merged_final = pd.merge_asof(
        merged_outer, bpm_df, on="timestamp", direction="nearest", tolerance=pd.Timedelta("100ms")
    )

    # Replace PPG_mV column with BPM values
    merged_final["PPG_mV"] = merged_final["BPM"]
    merged_final.drop(columns=["BPM"], inplace=True)  # Remove redundant BPM column

    # Save final dataset
    output_path = r"H:\merged_all_v1.csv"
    merged_final.to_csv(output_path, index=False)
    print(f"Merged dataset saved as '{output_path}'.")

def main():
    eeg_path = "data/eeg_export/sample_eeg_main.xlsx"
    gsr_path = "data/eeg_export/eeg_study_Session23_Shimmer_A5C7_Calibrated_PC.csv"
    merge_device_datasets(eeg_path, gsr_path)

if __name__ == "__main__":
    main()
