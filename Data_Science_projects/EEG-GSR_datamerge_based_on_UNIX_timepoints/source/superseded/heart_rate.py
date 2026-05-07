import pandas as pd
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
import os


# Load data from CSV file (adjust filename/path as needed)
dfpath = "data/thesis_study/subject_002/subject_002_Session6_Shimmer_A5C7_Calibrated_PC.csv"
df = pd.read_csv(dfpath, header=None, skiprows=3, sep="\t", usecols=[0,1,2,3,4])  # Expected columns: timepoint, value2
    
new_headers = ['timestamp', 'GSR_range', 'Skin_conductance_uS', 'Skin_resistence_kOhms', 'PPG_mV']  # Adjust based on the number of columns left
df.columns = new_headers
# # Convert the timestamp column from string to numeric (float)
# df["timestamp"] = pd.to_numeric(df["timestamp"], errors='coerce')

# # Convert timestamps from Unix ms to seconds relative to the first timestamp
# time = (df["timestamp"] - df["timestamp"].iloc[0]) / 1000


#————— FIXED TIME CONVERSION —————
# 1) Force timestamp into datetime64 (if not already)
df["timestamp"] = pd.to_datetime(df["timestamp"])                         # ← FIXED
# 2) Save the base timestamp for later
base_timestamp = df["timestamp"].iloc[0]                                  # ← FIXED
# 3) Build a "time" vector in true seconds
time = (df["timestamp"] - base_timestamp).dt.total_seconds()              # ← FIXED
# ————————————————————————————————————

# If you still need numeric timestamps for something else, you can get them via:
df["timestamp_ms"] = (df["timestamp"] - pd.Timestamp("1970-01-01")) \
                          .dt.total_seconds() * 1000
                          
# Extract the PPG signal (in mV)
ppg_signal = df["PPG_mV"]

# ---------------------------
# Preprocessing: Bandpass Filter (0.5–5 Hz) to focus on heart rate frequencies
fs = 1 / np.mean(np.diff(time))  # Sampling frequency in Hz
lowcut, highcut = 0.2, 5  # Frequency range for heart rate

# Create a Butterworth bandpass filter
b, a = signal.butter(3, [lowcut / (fs / 2), highcut / (fs / 2)], btype='band')
ppg_filtered = signal.filtfilt(b, a, ppg_signal)

# ---------------------------
# Smoothing: Apply a moving average filter to reduce noise (0.5 second window)
window_size = int(fs * 0.5)
ppg_smoothed = np.convolve(ppg_filtered, np.ones(window_size) / window_size, mode='same')

# ---------------------------
# Peak Detection: Adaptive thresholding based on the 75th percentile of the smoothed signal
peaks, properties = signal.find_peaks(ppg_smoothed, height=np.percentile(ppg_smoothed, 75), distance=int(fs * 0.5))

# Extract the times corresponding to the detected peaks
peak_times = time.iloc[peaks]

# ---------------------------
# Rolling Window BPM Calculation (using the last 10 seconds of data)
window_length = 10  # seconds
bpm_values = []
bpm_times = []

for i in range(1, len(peak_times)):
    # Consider peaks in the last 10 seconds relative to the current peak
    recent_peaks = peak_times[peak_times > (peak_times.iloc[i] - window_length)]
    if len(recent_peaks) > 1:
        ibi = np.diff(recent_peaks)  # Inter-beat intervals in seconds
        avg_ibi = np.mean(ibi)
        bpm = 60 / avg_ibi  # Convert average interval to BPM
        bpm_values.append(bpm)
        bpm_times.append(peak_times.iloc[i])

# ---------------------------
# Plotting the results
plt.figure(figsize=(12, 8))

# Plot the PPG signal and detected peaks
plt.subplot(2, 1, 1)
plt.plot(df["timestamp_ms"], ppg_signal, label="Raw PPG Signal", alpha=0.5)
plt.plot(df["timestamp_ms"], ppg_smoothed, label="Filtered & Smoothed PPG", linewidth=1.5)
plt.scatter(peak_times, ppg_smoothed[peaks], color='red', label="Detected Peaks")
plt.xlabel("Time (s)")
plt.ylabel("PPG Signal (mV)")
plt.title("PPG Signal with Detected Peaks")
plt.legend()

# Plot the BPM over time
plt.subplot(2, 1, 2)
plt.plot(bpm_times, bpm_values, marker='o', linestyle='-', color='blue', label="BPM")
plt.xlabel("Time (s)")
plt.ylabel("BPM")
plt.title("Estimated BPM Over Time")
plt.legend()

plt.tight_layout()
plt.show()

# Print the final BPM estimate (mean of rolling window BPM values)
if bpm_values:
    print(f"Final Estimated BPM: {np.mean(bpm_values):.2f}")
else:
    print("No valid BPM readings detected. Try adjusting the detection parameters.")


# ---------------------------
# Save the BPM results and timepoints to an Excel file
results_df = pd.DataFrame({
    "Time (s)": bpm_times,
    "BPM": bpm_values
})
subj_name = dfpath.split("\\")[-2]
dfpath_folder = "\\".join(dfpath.split("\\")[:-1])
results_df.to_excel(os.path.join(dfpath_folder, f"bpm_results_{subj_name}.xlsx"), index=False)
print(f"BPM results saved to 'bpm_results{subj_name}.xlsx'")