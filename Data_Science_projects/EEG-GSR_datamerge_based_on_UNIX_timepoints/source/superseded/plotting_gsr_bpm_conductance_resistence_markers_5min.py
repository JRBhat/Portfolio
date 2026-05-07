import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os


def generate_stats_and_plots(merged_file_path):
    # Load the Excel data
    df = pd.read_excel(merged_file_path)#"data/thesis_study/subject_005/merged_highlighted_subject_005_bpmcorrected.xlsx")
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Configuration
    marker_values = [1, 2, 3, 4]
    window_duration = pd.Timedelta(minutes=5)
    downsampling_factor = 350 # adjust as needed

    # Store filtered segments and metadata
    segments = []
    extreme_points = []  # stores max and min
    
    
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
            
            # Combine and store
            combined = pd.concat([marker_only, non_marker_downsampled])
            segments.append(combined)

    # Combine all marker-based segments
    df_plot = pd.concat(segments).sort_values('timestamp')

    # Extract markers for annotation
    df_markers = df_plot[df_plot['marker'].isin(marker_values)]

    # Set color palette for different markers
    palette = {
        'M1': 'blue',
        'M2': 'green',
        'M3': 'orange',
        'M4': 'purple'
    }

    # Create subplots
    fig, axs = plt.subplots(2, 2, figsize=(15, 10), sharex=True)
    fig.suptitle('Time Series (5 Min After Markers) with Color-Coded Zones', fontsize=16)

    def annotate_and_mark(ax, y_col, df_marker):
        for _, row in df_marker.iterrows():
            text = f"M{row['marker']}: {row[y_col]:.2f}"
            ax.annotate(text,
                        xy=(row['timestamp'], row[y_col]),
                        xytext=(5, 5),
                        textcoords='offset points',
                        fontsize=9, color='red', 
                        bbox=dict(boxstyle="round", edgecolor="red", facecolor="white"))
        ax.scatter(df_marker['timestamp'], df_marker[y_col], color='red', marker='D', s=50, zorder=5)
        
        
    def mark_extreme_points(ax, y_col):
        var_points = [p for p in extreme_points if p['var'] == y_col]
        for pt in var_points:
            label = f"{pt['extreme'].capitalize()}: {pt[y_col]:.2f}"
            color = 'blue' if pt['extreme'] == 'max' else 'green'
            marker = 'o' if pt['extreme'] == 'max' else 's'
            ax.annotate(label,
                        xy=(pt['timestamp'], pt[y_col]),
                        xytext=(5, -10 if pt['extreme'] == 'max' else 10),
                        textcoords='offset points',
                        fontsize=9, color=color,
                        bbox=dict(boxstyle="round", edgecolor=color, facecolor="white"))
            ax.plot(pt['timestamp'], pt[y_col], marker=marker, color=color, markersize=6, zorder=6)


    # Plot function using color-coded marker segments
    def plot_variable(ax, y_col, title):
        sns.lineplot(
            data=df_plot,
            x='timestamp',
            y=y_col,
            hue='marker_label',
            palette=palette,
            ax=ax,
            linewidth=1,
            legend=False  # we'll add a global legend later
        )
        annotate_and_mark(ax, y_col, df_markers)
        mark_extreme_points(ax, y_col)  #  <-- for extremes
        ax.set_title(title)
        ax.set_ylabel(y_col)
        ax.set_xlabel('Timestamp')

    # Generate plots
    plot_variable(axs[0, 0], 'BPM', 'Timestamp vs BPM')
    plot_variable(axs[0, 1], 'Skin_conductance_uS', 'Timestamp vs Skin Conductance (uS)')
    plot_variable(axs[1, 0], 'Skin_resistence_kOhms', 'Timestamp vs Skin Resistance (kOhms)')
    plot_variable(axs[1, 1], 'PPG_mV', 'Timestamp vs PPG (mV)')

    # Shared legend
    handles, labels = axs[0, 0].get_legend_handles_labels()

    fig.legend(handles, labels, loc='upper right', title='Marker Zones')

    plt.tight_layout(rect=[0, 0, 0.98, 0.96])
    # Final layout adjustments
    plt.tight_layout(rect=[0, 0, 0.98, 0.96])
    #plt.show()
    subj_name = merged_file_path.split("\\")[-2]
    main_path = "\\".join(merged_file_path.split("\\")[:-1])
    # Save the figure instead of showing it
    plt.savefig(os.path.join(main_path, f'time_series_plot_{subj_name}.png'), dpi=300)  # You can change the filename and DPI as needed
    plt.savefig(os.path.join(main_path, f'time_series_plot_{subj_name}.svg'))  # Example for svg

    # Optional: Close the figure to free memory if not needed anymore
    plt.close(fig)
    return segments
    