import numpy as np
import pandas as pd
import scipy.signal as signal
import matplotlib.pyplot as plt


def calculate_bpm_from_ppg(df,
                           window_length_sec=10,
                           smoothing_sec=0.2,
                           min_hr_bpm=30,
                           max_hr_bpm=220,
                           adaptive_quantile=0.90,
                           debug=False):
    """
    Improved PPG-to-BPM calculation with best practices and debug plots:
      1. Uniform resampling if needed
      2. Zero-phase bandpass filtering (0.5–10 Hz)
      3. Short moving-average smoothing (e.g. 200 ms)
      4. Adaptive thresholding via rolling quantile (e.g. 90th percentile)
      5. Peak detection with min/max HR distance
      6. Instantaneous HR from inter-beat intervals and smoothed HR via sliding window count

    Returns two DataFrames:
      - ib_df: instantaneous BPM at each inter-beat interval time
      - bpm_df: window-count BPM at specified window_length_sec
    """
    # 1. Time conversion
    df = df.copy()
    raw_ts = pd.to_numeric(df['timestamp'], errors='coerce')
    df['timestamp'] = pd.to_datetime(raw_ts, unit='ms')
    base_ts = df['timestamp'].iloc[0]
    df['time_s'] = (df['timestamp'] - base_ts).dt.total_seconds()

    t_orig = df['time_s'].values
    ppg_orig = df['PPG_mV'].values
    
    # Plot raw PPG signal
    if debug:
        plt.figure(figsize=(10, 3))
        plt.plot(t_orig, ppg_orig, label='Raw PPG')
        plt.xlabel('Time (s)'); plt.ylabel('PPG (mV)')
        plt.title('Raw PPG Signal'); plt.legend(); plt.tight_layout(); plt.show()

    # 2. Uniform resampling (optional)
    dt = np.diff(t_orig)
    fs = 1.0 / np.median(dt)
    uniform_t = np.arange(0, t_orig[-1], 1/fs)
    ppg = np.interp(uniform_t, t_orig, ppg_orig)
    
    if debug:
        plt.figure(figsize=(10, 3))
        plt.plot(uniform_t, ppg, label='Resampled PPG')
        plt.xlabel('Time (s)'); plt.ylabel('PPG (mV)')
        plt.title(f'Resampled to {fs:.1f} Hz'); plt.legend(); plt.tight_layout(); plt.show()

    # 3. Bandpass filter (0.5–10 Hz) with zero-phase
    lowcut, highcut = 0.5, 10.0
    nyq = fs / 2.0
    low = lowcut / nyq
    high = min(highcut, nyq*0.99) / nyq
    b, a = signal.butter(4, [low, high], btype='band')
    ppg_filt = signal.filtfilt(b, a, ppg)
    
    if debug:
        plt.figure(figsize=(10, 3))
        plt.plot(uniform_t, ppg_filt, label='Filtered PPG', color='orange')
        plt.xlabel('Time (s)'); plt.ylabel('PPG (mV)')
        plt.title('Bandpass Filtered (0.5–10 Hz)'); plt.legend(); plt.tight_layout(); plt.show()

    # 4. Short moving-average smoothing
    smooth_win = max(1, int(fs * smoothing_sec))
    ppg_smooth = np.convolve(ppg_filt, np.ones(smooth_win)/smooth_win, mode='same')
    
    if debug:
        plt.figure(figsize=(10, 3))
        plt.plot(uniform_t, ppg_smooth, label=f'Smoothed ({smoothing_sec}s MA)', color='green')
        plt.xlabel('Time (s)'); plt.ylabel('PPG (mV)')
        plt.title('Smoothed PPG'); plt.legend(); plt.tight_layout(); plt.show()

    # 5. Adaptive threshold: rolling quantile
    ppg_series = pd.Series(ppg_smooth, index=uniform_t)
    roll_win = int(window_length_sec * fs)
    threshold_series = ppg_series.rolling(roll_win, center=True, min_periods=1).quantile(adaptive_quantile)

    if debug:
        plt.figure(figsize=(10, 3))
        plt.plot(uniform_t, ppg_smooth, label='Smoothed PPG', color='green')
        plt.plot(uniform_t, threshold_series, label=f'{adaptive_quantile*100:.0f}th percentile threshold', linestyle='--')
        plt.xlabel('Time (s)'); plt.ylabel('PPG (mV)')
        plt.title('Adaptive Thresholding'); plt.legend(); plt.tight_layout(); plt.show()

    # 6. Peak detection with physiological refractory limits
    min_dist_s = 60.0 / max_hr_bpm
    peaks, _ = signal.find_peaks(ppg_smooth, distance=min_dist_s*fs)
    valid = ppg_smooth[peaks] > threshold_series.values[peaks]
    peaks = peaks[valid]
    peak_times = uniform_t[peaks]
    
    if debug:
        plt.figure(figsize=(10, 3))
        plt.plot(uniform_t, ppg_smooth, label='Smoothed PPG', color='green')
        plt.plot(peak_times, ppg_smooth[peaks], 'ro', label='Detected Peaks')
        plt.xlabel('Time (s)'); plt.ylabel('PPG (mV)')
        plt.title('Peak Detection'); plt.legend(); plt.tight_layout(); plt.show()

    peak_timestamps = [base_ts + pd.to_timedelta(t, unit='s') for t in peak_times]

    # Instantaneous HR (IBI-based)
    ibi = np.diff(peak_times)
    hr_inst = 60.0 / ibi
    inst_times = peak_times[1:]
    inst_timestamps = [base_ts + pd.to_timedelta(t, unit='s') for t in inst_times]
    ib_df = pd.DataFrame({'timestamp': inst_timestamps, 'BPM': hr_inst})

    if debug and not ib_df.empty:
        plt.figure(figsize=(10, 3))
        plt.plot(ib_df['timestamp'], ib_df['BPM'], marker='o', linestyle='-')
        plt.xlabel('Time'); plt.ylabel('BPM')
        plt.title('Instantaneous Heart Rate'); plt.tight_layout(); plt.show()
        plt.figure(figsize=(10, 3))
        plt.plot(inst_times, ib_df['BPM'], marker='o', linestyle='-')
        plt.xlabel('Time'); plt.ylabel('BPM')
        plt.title('Instantaneous Heart Rate'); plt.tight_layout(); plt.show()

    # Windowed count HR
    bpm_vals, bpm_times = [], []
    for t in peak_times:
        count = np.sum((peak_times > t - window_length_sec) & (peak_times <= t))
        if count > 1:
            bpm_vals.append(count * (60.0 / window_length_sec))
            bpm_times.append(t)
    bpm_timestamps = [base_ts + pd.to_timedelta(t, unit='s') for t in bpm_times]
    bpm_df = pd.DataFrame({'timestamp': bpm_timestamps, 'BPM': bpm_vals})

    if debug and not bpm_df.empty:
        plt.figure(figsize=(10, 3))
        plt.plot(bpm_df['timestamp'], bpm_df['BPM'], marker='o', linestyle='-')
        plt.xlabel('Time'); plt.ylabel('BPM')
        plt.title(f'Windowed ({window_length_sec}s) Heart Rate'); plt.tight_layout(); plt.show()
        plt.figure(figsize=(10, 3))
        plt.plot(bpm_times, bpm_df['BPM'], marker='o', linestyle='-')
        plt.xlabel('Time'); plt.ylabel('BPM')
        plt.title(f'Windowed ({window_length_sec}s) Heart Rate'); plt.tight_layout(); plt.show()

    return ib_df, bpm_df

if __name__ == "__main__":
    
    d2path = "data/eeg_study/subject_002/eeg_study_Session25_Shimmer_A5C7_Calibrated_PC.csv"
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
    ib_df, bpm_df = calculate_bpm_from_ppg(d2_for_bpm, debug=True)