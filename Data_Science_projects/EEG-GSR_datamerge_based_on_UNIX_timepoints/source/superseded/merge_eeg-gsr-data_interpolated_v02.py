import pandas as pd

def merge_device_datasets(d1path, d2path):
    # Load datasets
    d1 = pd.read_excel(d1path)  # Expected columns: timepoint, value1, etc.
    d2 = pd.read_csv(d2path, header=None, skiprows=3, sep="\t", usecols=[0,1,2,3,4])  # Expected columns: timepoint, value2, etc.
    
    # Set proper column headers
    d1.columns = ['ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'ch8', 'X', 'Y', 'Z', 'marker', 'timestamp']
    new_headers = ['timestamp', 'GSR_range', 'Skin_conductance_uS', 'Skin_resistence_kOhms', 'PPG_mV']
    d2.columns = new_headers
    
    # Convert Unix-based timepoints (in milliseconds) to datetime and sort
    d1["timestamp"] = pd.to_datetime(d1["timestamp"], unit="ms")
    d2["timestamp"] = pd.to_datetime(d2["timestamp"], unit="ms")
    d1 = d1.sort_values("timestamp")
    d2 = d2.sort_values("timestamp")
    
    # Merge the datasets using an outer join to preserve all timestamps
    merged_outer = pd.merge(d1, d2, on="timestamp", how="outer", sort=True)
    
    # Ensure the merged dataset is sorted by timestamp
    merged_outer.sort_values("timestamp", inplace=True)
    
    # Define columns by type
    eeg_cols = ['ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'ch8', 'X', 'Y', 'Z']
    gsr_cols = ['GSR_range', 'Skin_conductance_uS', 'Skin_resistence_kOhms']
    ppg_col = 'PPG_mV'
    
    # Fill missing values:
    # - For EEG channels and PPG data, use linear interpolation since these signals change quickly.
    merged_outer[eeg_cols] = merged_outer[eeg_cols].interpolate(method="linear")
    merged_outer[ppg_col] = merged_outer[ppg_col].interpolate(method="linear")
    
    # - For GSR values, forward-fill is often appropriate since these values change gradually.
    merged_outer[gsr_cols] = merged_outer[gsr_cols].fillna(method="ffill")
    
    # Optional: For any remaining NaNs at the beginning, you can also backfill.
    merged_outer.fillna(method="bfill", inplace=True)
    
    # Save the merged dataset if needed
    merged_outer.to_csv(r"H:\merged_outer.csv", index=False)
    print("Merged dataset saved as 'merged_outer.csv'.")

def main():
    eeg = "data/eeg_export/sample_eeg_main.xlsx"
    gsr = "data/eeg_export/eeg_study_Session23_Shimmer_A5C7_Calibrated_PC.csv"
    merge_device_datasets(eeg, gsr)
    
if __name__ == "__main__":
    main()
