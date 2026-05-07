import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the Excel file into a DataFrame.
df = pd.read_excel("data/thesis_study/subject_002/merged_highlighted.xlsx")

# Convert the timestamp column to datetime objects.
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Set the downsampling factor for non-marker rows.
downsampling_factor = 350

# Separate marker rows (markers 1, 2, 3, and 4) to preserve them.
df_markers = df[df['marker'].isin([1, 2, 3, 4])]
df_non_markers = df[~df['marker'].isin([1, 2, 3, 4])]

# Downsample the non-marker rows.
df_non_markers_downsampled = df_non_markers.iloc[::downsampling_factor, :]

# Combine the downsampled non-marker rows with the marker rows.
df_plot = pd.concat([df_non_markers_downsampled, df_markers]).sort_values('timestamp')

# Create a figure with 4 subplots (2 rows x 2 columns)
fig, axs = plt.subplots(2, 2, figsize=(15, 10), sharex=True)
fig.suptitle('Time Series Plots with Marker Annotations and Values', fontsize=16)

def annotate_and_mark(ax, y_col, df_marker):
    """
    Annotates the axes with marker values.
    
    Parameters:
    - ax: the matplotlib axes to annotate.
    - y_col: the column name in the DataFrame corresponding to the y-axis values.
    - df_marker: DataFrame containing marker rows.
    """
    
    # Annotate marker points with marker number and corresponding value.
    for _, row in df_marker.iterrows():
        text = f"Marker {row['marker']}\n{y_col}: {row[y_col]:.2f}"
        ax.annotate(text,
                    xy=(row['timestamp'], row[y_col]),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=9, color='red', bbox=dict(boxstyle="round,pad=0.3", edgecolor="red", facecolor="white"))
    # Highlight marker points on the plot using a distinct scatter marker.
    ax.scatter(df_marker['timestamp'], df_marker[y_col], color='red', marker='D', s=50, zorder=5)

# Plot 1: timestamp vs BPM
sns.lineplot(x='timestamp', y='BPM', data=df_plot, marker="o", markerfacecolor="orange", markeredgewidth=0.5, markeredgecolor="orange", markersize=0.2, linewidth=1, ax=axs[0, 0])
annotate_and_mark(axs[0, 0], 'BPM', df_markers)
axs[0, 0].set_title('Timestamp vs BPM')
axs[0, 0].set_xlabel('Timestamp')
axs[0, 0].set_ylabel('BPM')

# Plot 2: timestamp vs Skin_conductance_uS
sns.lineplot(x='timestamp', y='Skin_conductance_uS', data=df_plot, marker="o", markerfacecolor="orange", markeredgewidth=0.5, markeredgecolor="orange", markersize=0.2, linewidth=1, ax=axs[0, 1])
annotate_and_mark(axs[0, 1], 'Skin_conductance_uS', df_markers)
axs[0, 1].set_title('Timestamp vs Skin_conductance_uS')
axs[0, 1].set_xlabel('Timestamp')
axs[0, 1].set_ylabel('Skin_conductance_uS')

# Plot 0.2: timestamp vs Skin_resistence_kOhms
sns.lineplot(x='timestamp', y='Skin_resistence_kOhms', data=df_plot, marker="o", markerfacecolor="orange", markeredgewidth=0.5, markeredgecolor="orange",markersize=0.2, linewidth=1, ax=axs[1, 0])
annotate_and_mark(axs[1, 0], 'Skin_resistence_kOhms', df_markers)
axs[1, 0].set_title('Timestamp vs Skin_resistence_kOhms')
axs[1, 0].set_xlabel('Timestamp')
axs[1, 0].set_ylabel('Skin_resistence_kOhms')

# Plot 4: timestamp vs PPG_mV
sns.lineplot(x='timestamp', y='PPG_mV', data=df_plot, marker="o", markerfacecolor="orange", markeredgewidth=0.5, markeredgecolor="orange",markersize=0.2,  linewidth=1, ax=axs[1, 1])
annotate_and_mark(axs[1, 1], 'PPG_mV', df_markers)
axs[1, 1].set_title('Timestamp vs PPG_mV')
axs[1, 1].set_xlabel('Timestamp')
axs[1, 1].set_ylabel('PPG_mV')

# Optionally add legends to each subplot
for ax in axs.flat:
    ax.legend()

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()
