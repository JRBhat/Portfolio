import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import welch, butter, filtfilt, find_peaks, freqz

def diagnose_ppg(
    df,
    time_col='timestamp',
    signal_col='PPG_mV',
    lowcut=0.5,             # Hz
    highcut=5.0,            # Hz
    smoothing_win_s=0.5,    # seconds
    peak_percentile=75,     # for height threshold
    min_rr_s=0.5            # minimum expected RR interval in seconds
):
    # --- 1) Compute relative time & sampling stats
    # if your timestamps are datetime, convert first:
    if pd.api.types.is_datetime64_any_dtype(df[time_col]):
        df = df.copy()
        df[time_col] = df[time_col].astype(np.int64) / 1e6
    t = (df[time_col] - df[time_col].iloc[0]) / 1000.0  # seconds
    dt = np.diff(t)
    fs = 1.0 / np.mean(dt)
    print(f"Sampling frequency: {fs:.2f} Hz")
    print(f"Δt: mean={dt.mean():.4f}s, median={np.median(dt):.4f}s, std={dt.std():.4f}s, min={dt.min():.4f}s, max={dt.max():.4f}s")
    
    # --- 2) Power spectral density of raw signal
    f, Pxx = welch(df[signal_col], fs, nperseg=min(len(df), 1024))
    
    # --- 3) Filter design & freq response
    nyq = fs / 2.0
    low_n = lowcut / nyq
    high_n = highcut / nyq
    b, a = butter(3, [low_n, high_n], btype='band')
    w, h = freqz(b, a, worN=8000)
    freq_resp = (w / np.pi) * nyq
    
    # --- 4) Smooth + peak detect
    win_samps = max(1, int(smoothing_win_s * fs))
    smoothed = np.convolve(filtfilt(b, a, df[signal_col]),
                           np.ones(win_samps)/win_samps,
                           mode='same')
    min_dist_samps = int(min_rr_s * fs)
    peaks, _ = find_peaks(smoothed,
                          height=np.percentile(smoothed, peak_percentile),
                          distance=min_dist_samps)
    
    # --- 5) Plot everything
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    
    # (a) Δt histogram
    axs[0,0].hist(dt, bins=50)
    axs[0,0].set_title("Sampling Interval Δt Distribution")
    axs[0,0].set_xlabel("Δt (s)")
    
    # (b) PSD
    axs[0,1].semilogy(f, Pxx)
    axs[0,1].axvline(lowcut, color='r', ls='--', label='lowcut')
    axs[0,1].axvline(highcut, color='r', ls='--', label='highcut')
    axs[0,1].set_title("Power Spectral Density")
    axs[0,1].set_xlabel("Frequency (Hz)")
    axs[0,1].legend()
    
    # (c) Filter frequency response
    axs[1,0].plot(freq_resp, np.abs(h))
    axs[1,0].set_title("Bandpass Filter Response")
    axs[1,0].set_xlabel("Frequency (Hz)")
    
    # (d) Smoothed signal + detected peaks
    axs[1,1].plot(t, smoothed, label='Smoothed PPG')
    axs[1,1].plot(t[peaks], smoothed[peaks], 'ro', label='Peaks')
    axs[1,1].set_title("Smoothed PPG with Detected Peaks")
    axs[1,1].set_xlabel("Time (s)")
    axs[1,1].legend()
    
    plt.tight_layout()
    plt.show()
    
    # --- 6) Print key parameter summary
    print(f"\nNyquist frequency: {nyq:.2f} Hz")
    print(f"Normalized cutoffs: low={low_n:.3f}, high={high_n:.3f}")
    print(f"Smoothing window: {smoothing_win_s}s → {win_samps} samples")
    print(f"Min peak distance: {min_rr_s}s → {min_dist_samps} samples")
    print(f"Peak‐height percentile: {peak_percentile} → height threshold = {np.percentile(smoothed, peak_percentile):.3f}")

# # Usage example:
# df = pd.read_csv("your_file.csv", parse_dates=["timestamp"])  # or however you load it
# diagnose_ppg(df, time_col="timestamp", signal_col="PPG_mV")
