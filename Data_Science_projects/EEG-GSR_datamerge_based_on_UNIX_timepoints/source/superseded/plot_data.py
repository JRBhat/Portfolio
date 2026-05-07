import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os


def generate_plots(merged_file_path):
    
    # Load the Excel data
    df = pd.read_excel(merged_file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Configuration
    marker_values = [1, 2, 3, 4]
    window_duration = pd.Timedelta(minutes=5)
    downsampling_factor = 350  # adjust as needed

    # Store filtered segments with metadata
    segments = []  # list of dicts: {'marker': int, 'data': DataFrame}

    for marker_val in marker_values:
        marker_rows = df[df['marker'] == marker_val]
        for _, marker_row in marker_rows.iterrows():
            start_time = marker_row['timestamp']
            end_time = start_time + window_duration
            window_df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)].copy()
            window_df['marker_label'] = f'M{marker_val}'

            # Separate marker row(s) to preserve them
            marker_only = window_df[window_df['marker'] == marker_val]
            non_marker_part = window_df[window_df['marker'] != marker_val]

            # Downsample the non-marker part
            non_marker_downsampled = non_marker_part.iloc[::downsampling_factor, :]

            # Combine
            combined = pd.concat([marker_only, non_marker_downsampled]).sort_values('timestamp')
            segments.append({'marker': marker_val, 'data': combined})

    # Prepare DataFrame for plotting by concatenating all segments
    df_plot = pd.concat([seg['data'] for seg in segments]).sort_values('timestamp')

    # Extract markers for annotation (all marker rows)
    df_markers = df_plot[df_plot['marker'].isin(marker_values)]

    # Colors for each marker zone
    palette = {'M1': 'blue', 'M2': 'green', 'M3': 'orange', 'M4': 'purple'}

    # Create subplots
    fig, axs = plt.subplots(1, 2, figsize=(15, 5), sharex=True)
    fig.suptitle('Time Series (5 Min After Markers) with Color-Coded Zones', fontsize=16)

    def annotate_and_mark(ax, y_col, df_marker):
        for _, row in df_marker.iterrows():
            text = f"M{int(row['marker'])}"#: {row[y_col]:.2f}"
            ax.annotate(text,
                        xy=(row['timestamp'], row[y_col]),
                        xytext=(5, 5),
                        textcoords='offset points',
                        fontsize=5, color='red',
                        bbox=dict(boxstyle="round", edgecolor="red", facecolor="white"))
        ax.scatter(df_marker['timestamp'], df_marker[y_col], color='red', marker='D', s=50, zorder=5)

    def mark_extreme_points(ax, y_col):
        for seg in segments:
            df_win = seg['data']
            m = seg['marker']
            # find extreme points
            max_row = df_win.loc[df_win[y_col].idxmax()]
            min_row = df_win.loc[df_win[y_col].idxmin()]
            for extreme, row in [('max', max_row), ('min', min_row)]:
                label = f"{extreme.capitalize()}: {row[y_col]:.2f}"
                color = 'black' if extreme == 'max' else 'grey'
                marker_sym = 'o' if extreme == 'max' else 's'
                ax.annotate(label,
                            xy=(row['timestamp'], row[y_col]),
                            xytext=(5, -10 if extreme == 'max' else 10),
                            textcoords='offset points',
                            fontsize=9, color=color,
                            bbox=dict(boxstyle="round", edgecolor=color, facecolor="white"))
                ax.plot(row['timestamp'], row[y_col], marker=marker_sym, color=color, markersize=6, zorder=6)

    def plot_variable(ax, y_col, title):
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
        annotate_and_mark(ax, y_col, df_markers)
        mark_extreme_points(ax, y_col)
        ax.set_title(title)
        ax.set_ylabel(y_col)
        ax.set_xlabel('Timestamp')

    # Plot each variable
    plot_variable(axs[0], 'BPM', 'Timestamp vs BPM')
    plot_variable(axs[1], 'Skin_conductance_uS', 'Timestamp vs Skin Conductance (uS)')
    # plot_variable(axs[1, 0], 'Skin_resistence_kOhms', 'Timestamp vs Skin Resistance (kOhms)')
    # plot_variable(axs[1, 1], 'PPG_mV', 'Timestamp vs PPG (mV)')

    # Shared legend
    handles, labels = axs[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right', title='Marker Zones')

    plt.tight_layout(rect=[0, 0, 0.98, 0.96])
    subj_name = os.path.basename(os.path.dirname(merged_file_path))
    plt.savefig(os.path.join(os.path.dirname(merged_file_path), f'time_series_plot_{subj_name}_minimal.png'), dpi=300)
    plt.savefig(os.path.join(os.path.dirname(merged_file_path), f'time_series_plot_{subj_name}_minimal.svg'))
    plt.close(fig)
    print(f"Plotting successful for {subj_name}")
    return segments
    