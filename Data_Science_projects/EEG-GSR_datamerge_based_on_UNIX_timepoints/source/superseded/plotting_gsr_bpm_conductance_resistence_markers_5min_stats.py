import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
df = pd.read_excel("data/thesis_study/subject_004/merged_highlighted.xlsx")
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Configuration
marker_values = [1, 2, 3, 4]
window_duration = pd.Timedelta(minutes=5)
downsampling_factor = 350

# For storing segments and their stats
segments = []
stats = []

for marker_val in marker_values:
    marker_rows = df[df['marker'] == marker_val]
    for _, marker_row in marker_rows.iterrows():
        start_time = marker_row['timestamp']
        end_time = start_time + window_duration
        window_df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)].copy()
        window_df['marker_label'] = f'Marker {marker_val}'
        
        # Separate out marker row(s)
        marker_only = window_df[window_df['marker'] == marker_val]
        non_marker_part = window_df[window_df['marker'] != marker_val]
        
        # Downsample non-marker rows
        non_marker_downsampled = non_marker_part.iloc[::downsampling_factor, :]
        combined = pd.concat([marker_only, non_marker_downsampled])
        segments.append(combined)

        # Compute summary stats for the window
        stats.append({
            'marker': marker_val,
            'label': f'Marker {marker_val}',
            'start_time': start_time,
            'end_time': end_time,
            'BPM': {
                'mean': window_df['BPM'].mean(),
                'min': window_df['BPM'].min(),
                'max': window_df['BPM'].max(),
                'std': window_df['BPM'].std()
            },
            'Skin_conductance_uS': {
                'mean': window_df['Skin_conductance_uS'].mean(),
                'min': window_df['Skin_conductance_uS'].min(),
                'max': window_df['Skin_conductance_uS'].max(),
                'std': window_df['Skin_conductance_uS'].std()
            },
            'Skin_resistence_kOhms': {
                'mean': window_df['Skin_resistence_kOhms'].mean(),
                'min': window_df['Skin_resistence_kOhms'].min(),
                'max': window_df['Skin_resistence_kOhms'].max(),
                'std': window_df['Skin_resistence_kOhms'].std()
            },
            'PPG_mV': {
                'mean': window_df['PPG_mV'].mean(),
                'min': window_df['PPG_mV'].min(),
                'max': window_df['PPG_mV'].max(),
                'std': window_df['PPG_mV'].std()
            }
        })

# Combine all data for plotting
df_plot = pd.concat(segments).drop_duplicates().sort_values('timestamp')
df_markers = df_plot[df_plot['marker'].isin(marker_values)]
stats_df = pd.DataFrame(stats)

# Color palette
palette = {
    'Marker 1': 'blue',
    'Marker 2': 'green',
    'Marker 3': 'orange',
    'Marker 4': 'purple'
}

# Plot setup
fig, axs = plt.subplots(2, 2, figsize=(15, 10), sharex=True)
fig.suptitle('Time Series (5 min after marker) with Stats', fontsize=16)

def annotate_and_mark(ax, y_col, df_marker):
    for _, row in df_marker.iterrows():
        text = f"Marker {row['marker']}\n{y_col}: {row[y_col]:.2f}"
        ax.annotate(text,
                    xy=(row['timestamp'], row[y_col]),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=9, color='red',
                    bbox=dict(boxstyle="round", edgecolor="red", facecolor="white"))
    ax.scatter(df_marker['timestamp'], df_marker[y_col], color='red', marker='D', s=50, zorder=5)

def plot_variable(ax, y_col, title):
    # Plot time series lines per marker zone
    sns.lineplot(
        data=df_plot,
        x='timestamp',
        y=y_col,
        hue='marker_label',
        palette=palette,
        ax=ax,
        linewidth=1,
        legend=False
    )
    
    # Plot marker annotations
    annotate_and_mark(ax, y_col, df_markers)

    # Plot stats lines
    for i, row in stats_df.iterrows():
        label = row['label']
        mean = row[y_col]['mean']
        std = row[y_col]['std']
        min_val = row[y_col]['min']
        max_val = row[y_col]['max']

        color = palette[label]

        # Mean line
        ax.axhline(mean, linestyle='--', color=color, linewidth=1, label=f'{label} Mean')
        # Mean ± Std
        ax.axhline(mean + std, linestyle=':', color=color, linewidth=0.8, label=f'{label} ± Std')
        ax.axhline(mean - std, linestyle=':', color=color, linewidth=0.8)
        # Min/Max lines
        ax.axhline(min_val, linestyle='-', color=color, alpha=0.2, label=f'{label} Min')
        ax.axhline(max_val, linestyle='-', color=color, alpha=0.2, label=f'{label} Max')

    ax.set_title(title)
    ax.set_ylabel(y_col)
    ax.set_xlabel('Timestamp')

# Generate plots
plot_variable(axs[0, 0], 'BPM', 'Timestamp vs BPM')
plot_variable(axs[0, 1], 'Skin_conductance_uS', 'Timestamp vs Skin Conductance (uS)')
plot_variable(axs[1, 0], 'Skin_resistence_kOhms', 'Timestamp vs Skin Resistance (kOhms)')
plot_variable(axs[1, 1], 'PPG_mV', 'Timestamp vs PPG (mV)')

# Add a global legend
handles, labels = axs[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc='upper right', bbox_to_anchor=(0.99, 0.95), title='Marker Zones + Stats')

plt.tight_layout(rect=[0, 0, 0.98, 0.94])
plt.show()
