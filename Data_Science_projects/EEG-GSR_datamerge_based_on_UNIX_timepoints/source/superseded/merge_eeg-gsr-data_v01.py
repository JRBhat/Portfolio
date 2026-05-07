## code that converts timepoints (e.g. format : 174099899433 based on a Unix-like or epoch-based timestamp system) into milliseconds

import pandas as pd


def merge_device_datasets(d1path, d2path):
    # # Load datasets
    d1 = pd.read_excel(d1path)  # Expected columns: timepoint, value1
    d2 = pd.read_csv(d2path, header=None, skiprows=3, sep="\t", usecols=[0,1,2,3,4])  # Expected columns: timepoint, value2

    
    new_headers = ['timestamp', 'GSR_range', 'Skin_conductance_uS', 'Skin_resistence_kOhms', 'PPG_mV']  # Adjust based on the number of columns left
    d1.columns =  ['ch1', 'ch2', 'ch3','ch4', 'ch5', 'ch6','ch7', 'ch8', 'X', 'Y', 'Z', 'marker', 'timestamp']
    d2.columns = new_headers
    # Convert unix based timepoint from milliseconds to datetime and sort
    d1["timestamp"] = pd.to_datetime(d1["timestamp"], unit="ms")
    d2["timestamp"] = pd.to_datetime(d2["timestamp"], unit="ms")

    d1 = d1.sort_values("timestamp")
    d2 = d2.sort_values("timestamp")

    # Option 1: Merge using an outer join and then interpolate missing values
    merged_outer = pd.merge(d1, d2, on="timestamp", how="outer", sort=True)
    # merged_outer.interpolate(method="ffill", inplace=True) # use linear or forward fill - choose forward fill becasue the GSR value hardly changes during the short EEG sampling rates
    # merged_outer.iloc[:, 1:] = merged_outer.iloc[:, 1:].interpolate(method="linear")

    # Option 2: Merge using merge_asof for tolerance-based nearest matching
    # This method is ideal if you expect the timestamps to be near but not exactly equal.
    # merged_asof = pd.merge_asof(
    #     d1, d2, on="timestamp", direction="nearest", tolerance=pd.Timedelta("100ms")
    # )

    # Save the merged datasets if needed
    merged_outer.to_csv(r"H:\merged_outer.csv", index=False)
    # merged_asof.to_csv(r"output\merged_asof.csv", index=False)
    print("Merged datasets saved as 'merged_outer.csv' and 'merged_asof.csv'.")


def main():
    eeg = "data/eeg_export/sample_eeg_main.xlsx"
    gsr = "data/eeg_export/eeg_study_Session23_Shimmer_A5C7_Calibrated_PC.csv"

    merge_device_datasets(eeg, gsr)
    
if __name__ == "__main__":
    main()
    # from datetime import datetime
    # timestamp_ms = 174099899433
    # dt = datetime.fromtimestamp(datetime.timezone.utc)(timestamp_ms / 1000)
    # print(dt)  # Output: 2025-06-02 15:43:14 UTC
