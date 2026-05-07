import pandas as pd
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
import os

# --- Load data from CSV file ---
dfpath = "data/thesis_study/ppg_validation/eeg_study_Session14_Shimmer_A5C7_Calibrated_PC.csv"
df = pd.read_csv(
    dfpath,
    header=None,
    skiprows=3,
    sep="\t",
    usecols=[0, 1, 2, 3, 4]
)

# --- Assign proper column names ---
df.columns = [
    'timestamp',
    'GSR_range',
    'Skin_conductance_uS',
    'Skin_resistance_kOhms',
    'PPG_mV'
]

# --- Time conversion (Shimmer timestamps in ms since epoch) ---
raw_ts = pd.to_numeric(df['timestamp'], errors='coerce')
df['timestamp'] = pd.to_datetime(raw_ts, unit='ms')  # no change here

base_timestamp = df['timestamp'].iloc[0]
time = (df['timestamp'] - base_timestamp).dt.total_seconds()

df['timestamp_ms'] = (df['timestamp'] - pd.Timestamp('1970-01-01'))\
                       .dt.total_seconds() * 1000

ppg_signal = df['PPG_mV']

# --- Preprocessing: Bandpass filter (0.5–5 Hz) ---
fs = 1.0 / np.mean(np.diff(time))
print(f"Sampling rate: {fs:.2f} Hz")

lowcut, highcut = 0.5, 5.0
nyq = fs / 2.0
if highcut >= nyq:
    highcut = nyq * 0.99
if lowcut <= 0:
    lowcut = nyq * 0.01

low = lowcut / nyq
high = highcut / nyq
b, a = signal.butter(3, [low, high], btype='band')
ppg_filtered = signal.filtfilt(b, a, ppg_signal)

# --- Smoothing: moving average (0.5 s window) ---
window_size = max(1, int(fs * 0.5))
ppg_smoothed = np.convolve(ppg_filtered,
                           np.ones(window_size) / window_size,
                           mode='same')

# --- PEAK DETECTION (ADJUSTED THRESHOLD) ---
min_distance = int(fs * 0.5)
threshold = np.percentile(ppg_smoothed, 50)  # ← FIXED: lower from 75 to 50 percentile
peaks, props = signal.find_peaks(
    ppg_smoothed,
    height=threshold,
    distance=min_distance
)
peak_times = time.iloc[peaks]

# --- ROLLING 10-SECOND BPM (COUNT-BASED) ---
window_length = 10
bpm_values = []
bpm_times = []

for t in peak_times:
    recent = peak_times[(peak_times > t - window_length) & (peak_times <= t)]
    count = len(recent)
    if count > 1:
        bpm = count * (60.0 / window_length)     # ← FIXED: count × (60/10) instead of avg IBI
        bpm_values.append(bpm)
        bpm_times.append(t)

# --- Plotting ---
plt.figure(figsize=(12, 8))

plt.subplot(2, 1, 1)
plt.plot(time, ppg_signal,        label='Raw PPG', alpha=0.5)
plt.plot(time, ppg_smoothed,      label='Filtered & Smoothed', linewidth=1.5)
plt.scatter(peak_times, ppg_smoothed[peaks],
            color='red', label='Peaks')
plt.xlabel('Time (s)')
plt.ylabel('PPG (mV)')
plt.title('PPG Signal with Detected Peaks')
plt.legend()

plt.subplot(2, 1, 2)
plt.plot(bpm_times, bpm_values, marker='o', linestyle='-')
plt.xlabel('Time (s)')
plt.ylabel('BPM')
plt.title('Estimated BPM Over Time')

plt.tight_layout()
plt.show()

# --- Final BPM & Save ---
if bpm_values:
    print(f"Final Estimated BPM: {np.mean(bpm_values):.2f}")
else:
    print("No BPM readings; adjust parameters.")

results_df = pd.DataFrame({
    'Time (s)': bpm_times,
    'BPM':     bpm_values
})
subj_name = os.path.basename(os.path.dirname(dfpath))
out_fname = f"bpm_results_{subj_name}.xlsx"
results_df.to_excel(os.path.join(os.path.dirname(dfpath), out_fname),
                    index=False)
print(f"Results saved to {out_fname}")
