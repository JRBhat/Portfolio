import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.dates as mdates
import pickle
import numpy as np

def annotate_and_mark(ax, y_col, df_marker):
    for _, row in df_marker.iterrows():
        text = f"M{int(row['marker'])}"#: {row[y_col]:.2f}"
        ax.axvline(x=row['timestamp'], color='red', linestyle='--', linewidth=1, zorder=4)
        ax.annotate(text,
                    xy=(row['timestamp'], ax.get_ylim()[1]),
                    xytext=(5,-2),
                    textcoords='offset points',
                    fontsize=6, color='red',
                    bbox=dict(boxstyle="round", edgecolor="red", facecolor="white"),
                    rotation=0,
                    ha='left', va='top')

    # ax.scatter(df_marker['timestamp'], df_marker[y_col], color='red', marker='D', s=50, zorder=5)

# def mark_extreme_points(ax, y_col):
#     for seg in segments:
#         df_win = seg['data']
#         m = seg['marker']
#         # find extreme points
#         max_row = df_win.loc[df_win[y_col].idxmax()]
#         min_row = df_win.loc[df_win[y_col].idxmin()]
#         for extreme, row in [('max', max_row), ('min', min_row)]:
#             label = f"{extreme.capitalize()}: {row[y_col]:.2f}"
#             color = 'black' if extreme == 'max' else 'grey'
#             marker_sym = 'o' if extreme == 'max' else 's'
#             ax.annotate(label,
#                         xy=(row['timestamp'], row[y_col]),
#                         xytext=(5, -10 if extreme == 'max' else 10),
#                         textcoords='offset points',
#                         fontsize=9, color=color,
#                         bbox=dict(boxstyle="round", edgecolor=color, facecolor="white"))
#             ax.plot(row['timestamp'], row[y_col], marker=marker_sym, color=color, markersize=6, zorder=6)

def plot_variable(ax, y_col, title, df_markers, df_plot, palette):
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
    # mark_extreme_points(ax, y_col)
    ax.set_title(title)
    ax.set_ylabel(y_col)
    ax.set_xlabel('Timestamp')
    
    
def generate_plots(merged_file_path):
    
    # Configuration
    # marker_values = [1, 2, 3, 4]
    marker_values = [1, 2, 3, 4, 5, 6]
    subj_name = os.path.basename(os.path.dirname(merged_file_path))
    png_path = os.path.join(os.path.dirname(merged_file_path), f'time_series_plot_{subj_name}_minimal_mrmwd2.png')
    svg_path = os.path.join(os.path.dirname(merged_file_path), f'time_series_plot_{subj_name}_minimal_mrmwd2.svg')
    segment_pkl_path = os.path.join(os.path.dirname(merged_file_path), 'segments.pkl')
    df_temp_path = os.path.join(os.path.dirname(merged_file_path),'df_temp.pkl')
    if not os.path.exists(png_path) and not os.path.exists(segment_pkl_path):
        # Load the Excel data
        if not os.path.exists(df_temp_path):
            df = pd.read_excel(merged_file_path)
            with open(df_temp_path, 'wb') as dfpk:
                pickle.dump(df, dfpk)
        else:
            with open(df_temp_path, 'rb') as dfpk:
                df = pickle.load(dfpk)
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print("All unique markers in df:", df['marker'].unique())


        
        window_duration = pd.Timedelta(minutes=5)
        downsampling_factor = 100  # adjust as needed

        # Store filtered segments with metadata
        segments = []  # list of dicts: {'marker': int, 'data': DataFrame}

        for marker_val in marker_values:
            # if marker_val == 3:
            #     window_duration = pd.Timedelta(minutes=3)
            # elif marker_val == 4:
            #     window_duration = pd.Timedelta(minutes=2)
            
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
                if not marker_only.empty:
                    combined = pd.concat([marker_only, non_marker_downsampled]).sort_values('timestamp')
                    print(f"Marker {marker_val}: {len(combined)} rows in window")
                    segments.append({'marker': marker_val, 'data': combined})
                else:
                    print(f"Warning: Marker {marker_val} has no matching rows in window.")
                # # Combine
                # combined = pd.concat([marker_only, non_marker_downsampled]).sort_values('timestamp')
                
                # segments.append({'marker': marker_val, 'data': combined})

        # Prepare DataFrame for plotting by concatenating all segments
        df_plot = pd.concat([seg['data'] for seg in segments]).sort_values('timestamp')
        print("Markers in df_plot:", df_plot['marker'].unique())
        df_plot['marker'] = df_plot['marker'].replace(0, np.nan)
        all_markers = df_plot['marker'].unique()
        # remove 0 for the sake of display:
        df_markers = sorted(m for m in all_markers if m != 0)
        print("Markers in df_plot:", df_markers)
        
        # Extract markers for annotation (all marker rows)
        # df_markers = df_plot[df_plot['marker'].isin(marker_values)]
        # print("Markers in df_markers:", df_markers['marker'].unique())
        
        # Colors for each marker zone
        # palette = {'M1': 'blue', 'M2': 'green', 'M3': 'orange', 'M4': 'purple'}
        palette = {'M1': 'blue', 'M2': 'green', 'M3': 'orange', 'M4': 'purple', 'M5': 'cyan', 'M6': 'grey'}
        # Create subplots
        fig, axs = plt.subplots(1, 2, figsize=(15, 5), sharex=True)
        fig.suptitle('Time Series (5 Min After Markers) with Color-Coded Zones', fontsize=16)

        # Plot each variable
        plot_variable(axs[0], 'BPM', 'Timestamp vs BPM', df_markers, df_plot, palette)
        plot_variable(axs[1], 'Skin_conductance_uS', 'Timestamp vs Skin Conductance (uS)', df_markers, df_plot, palette)
        axs[1].set_ylabel('Skin conductance (uS)')
        # plot_variable(axs[1, 0], 'Skin_resistence_kOhms', 'Timestamp vs Skin Resistance (kOhms)')
        # plot_variable(axs[1, 1], 'PPG_mV', 'Timestamp vs PPG (mV)')

        # # 1. Grab all handles & labels (there will be one line for each hue group you actually drew)
        # handles, labels = axs[0].get_legend_handles_labels()

        # # 2. Filter out any entries you don't want (e.g. 'M0')
        # valid = [(h, lbl) for h, lbl in zip(handles, labels) if lbl in palette.keys()]
        # if valid:
        #     handles_filt, labels_filt = zip(*valid)
        # else:
        #     handles_filt, labels_filt = [], []

        # # 3. Draw a manual legend from just the M1–M6 lines
        # fig.legend(
        #     handles_filt,
        #     labels_filt,
        #     loc='upper right',
        #     title='Marker Zones'
        # )
        # Shared legend
        handles, labels = axs[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='upper right', title='Marker Zones')


        for ax in axs:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

        plt.tight_layout(rect=[0, 0, 0.98, 0.96])
        
        plt.savefig(png_path, dpi=300)
        plt.savefig(svg_path)
        plt.close(fig)
        print(f"Plotting successful for {subj_name}")
        
        with open(segment_pkl_path, 'wb') as f:
            pickle.dump(segments, f)
        return segments
    
    else:
        print(f"{png_path} and {svg_path} and {segment_pkl_path} already exist.")
        print("Skipping plot and proceeding to stats calc...")
        with open(segment_pkl_path, 'rb') as f:
            segments = pickle.load(f)
        return segments
        
if __name__ == "__main__":
    # paths = ["data/thesis_study/subject_005/merged_highlighted_subject_005_bpmcorrected.xlsx",
    #          "data/thesis_study/subject_002/merged_highlighted_subject_002_bpmcorrected.xlsx",
    #          "data/thesis_study/subject_003/merged_highlighted_subject_003_bpmcorrected.xlsx",
    #          "data/thesis_study/subject_004/merged_highlighted_subject_004_bpmcorrected.xlsx"
    # ]
    # for path in paths:
    #     _ = generate_plots(path)
    generate_plots("data/eeg_study/subject_001/merged_highlighted_subject_001_bpmcorrected_markers_corrected.xlsx")