import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the Excel file into a DataFrame.
# Replace 'data.xlsx' with the path to your Excel file.
df = pd.read_excel("data/thesis_study/subject_004/merged_highlighted.xlsx")

# Convert the timestamp column to datetime objects.
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Identify rows where marker is one of [1, 2, 3, 4] for annotation.
marker_points = df[df['marker'].isin([1, 2, 3, 4])]

# Create a figure with four subplots (2 rows x 2 columns)
fig, axs = plt.subplots(2, 2, figsize=(15, 10), sharex=True)
fig.suptitle('Time Series Plots with Markers', fontsize=16)

# Plot 1: timestamp vs. BPM
sns.lineplot(x='timestamp', y='BPM', data=df, marker="o", ax=axs[0, 0])
axs[0, 0].set_title('Timestamp vs BPM')
axs[0, 0].set_xlabel('Timestamp')
axs[0, 0].set_ylabel('BPM')
for _, row in marker_points.iterrows():
    axs[0, 0].annotate(f"Marker {row['marker']}",
                       xy=(row['timestamp'], row['BPM']),
                       xytext=(5, 5),
                       textcoords='offset points',
                       fontsize=9, color='red')

# Plot 2: timestamp vs. Skin_conductance_uS
sns.lineplot(x='timestamp', y='Skin_conductance_uS', data=df, marker="o", ax=axs[0, 1])
axs[0, 1].set_title('Timestamp vs Skin_conductance_uS')
axs[0, 1].set_xlabel('Timestamp')
axs[0, 1].set_ylabel('Skin_conductance_uS')
for _, row in marker_points.iterrows():
    axs[0, 1].annotate(f"Marker {row['marker']}",
                       xy=(row['timestamp'], row['Skin_conductance_uS']),
                       xytext=(5, 5),
                       textcoords='offset points',
                       fontsize=9, color='red')

# Plot 3: timestamp vs. Skin_resistence_kOhms
sns.lineplot(x='timestamp', y='Skin_resistence_kOhms', data=df, marker="o", ax=axs[1, 0])
axs[1, 0].set_title('Timestamp vs Skin_resistence_kOhms')
axs[1, 0].set_xlabel('Timestamp')
axs[1, 0].set_ylabel('Skin_resistence_kOhms')
for _, row in marker_points.iterrows():
    axs[1, 0].annotate(f"Marker {row['marker']}",
                       xy=(row['timestamp'], row['Skin_resistence_kOhms']),
                       xytext=(5, 5),
                       textcoords='offset points',
                       fontsize=9, color='red')

# Plot 4: timestamp vs. PPG_mV
sns.lineplot(x='timestamp', y='PPG_mV', data=df, marker="o", ax=axs[1, 1])
axs[1, 1].set_title('Timestamp vs PPG_mV')
axs[1, 1].set_xlabel('Timestamp')
axs[1, 1].set_ylabel('PPG_mV')
for _, row in marker_points.iterrows():
    axs[1, 1].annotate(f"Marker {row['marker']}",
                       xy=(row['timestamp'], row['PPG_mV']),
                       xytext=(5, 5),
                       textcoords='offset points',
                       fontsize=9, color='red')

# Improve layout spacing and display the plot
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()
