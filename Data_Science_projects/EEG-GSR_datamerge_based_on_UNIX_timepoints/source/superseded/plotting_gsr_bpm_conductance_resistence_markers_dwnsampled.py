import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the Excel file into a DataFrame.
df = pd.read_excel("data/thesis_study/subject_002/merged_highlighted.xlsx")

# Convert the timestamp column to datetime objects.
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Set the downsampling factor: change this based on your preferences.
downsampling_factor = 20

# Separate out the marker rows to ensure they are preserved.
df_markers = df[df['marker'].isin([1, 2, 3, 4])]
df_non_markers = df[~df['marker'].isin([1, 2, 3, 4])]

# Downsample only the non-marker rows.
df_non_markers_downsampled = df_non_markers.iloc[::downsampling_factor, :]

# Combine the preserved marker rows with the downsampled non-marker rows.
df_plot = pd.concat([df_non_markers_downsampled, df_markers]).sort_values('timestamp')

# Create a figure with four subplots (2 rows x 2 columns)
fig, axs = plt.subplots(2, 2, figsize=(15, 10), sharex=True)
fig.suptitle('Time Series Plots with Marker Annotations', fontsize=16)

# Function to add marker annotations and extra visual markers on the lines.
def annotate_and_mark(ax, x, y, df_marker, label):
    # Annotate marker points
    for _, row in df_marker.iterrows():
        ax.annotate(f"Marker {row['marker']}",
                    xy=(row['timestamp'], row[y]),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=9, color='red')
    # Visually mark the marker points on the plot (e.g., with a different marker style).
    ax.scatter(df_marker['timestamp'], df_marker[y], color='red', 
               marker='D', s=50, label='Marker points')

# Plot 1: timestamp vs. BPM
sns.lineplot(x='timestamp', y='BPM', data=df_plot, marker="o", markersize=3, linewidth=1, ax=axs[0, 0])
annotate_and_mark(axs[0, 0], 'timestamp', 'BPM', df_markers, 'BPM')
axs[0, 0].set_title('Timestamp vs BPM')
axs[0, 0].set_xlabel('Timestamp')
axs[0, 0].set_ylabel('BPM')

# Plot 2: timestamp vs. Skin_conductance_uS
sns.lineplot(x='timestamp', y='Skin_conductance_uS', data=df_plot, marker="o", markersize=3, linewidth=1, ax=axs[0, 1])
annotate_and_mark(axs[0, 1], 'timestamp', 'Skin_conductance_uS', df_markers, 'Skin_conductance_uS')
axs[0, 1].set_title('Timestamp vs Skin_conductance_uS')
axs[0, 1].set_xlabel('Timestamp')
axs[0, 1].set_ylabel('Skin_conductance_uS')

# Plot 3: timestamp vs. Skin_resistence_kOhms
sns.lineplot(x='timestamp', y='Skin_resistence_kOhms', data=df_plot, marker="o", markersize=3, linewidth=1, ax=axs[1, 0])
annotate_and_mark(axs[1, 0], 'timestamp', 'Skin_resistence_kOhms', df_markers, 'Skin_resistence_kOhms')
axs[1, 0].set_title('Timestamp vs Skin_resistence_kOhms')
axs[1, 0].set_xlabel('Timestamp')
axs[1, 0].set_ylabel('Skin_resistence_kOhms')

# Plot 4: timestamp vs. PPG_mV
sns.lineplot(x='timestamp', y='PPG_mV', data=df_plot, marker="o", markersize=3, linewidth=1, ax=axs[1, 1])
annotate_and_mark(axs[1, 1], 'timestamp', 'PPG_mV', df_markers, 'PPG_mV')
axs[1, 1].set_title('Timestamp vs PPG_mV')
axs[1, 1].set_xlabel('Timestamp')
axs[1, 1].set_ylabel('PPG_mV')

# Adjust layout spacing and add a legend to each subplot.
for ax in axs.flat:
    ax.legend()

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()
