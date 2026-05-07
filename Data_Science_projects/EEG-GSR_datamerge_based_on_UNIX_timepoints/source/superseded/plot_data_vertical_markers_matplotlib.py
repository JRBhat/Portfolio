import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib.dates as mdates
import pickle
import numpy as np


def annotate_and_mark(ax, y_col, df_markers):
    for _, row in df_markers.iterrows():
        text = f"M{int(row['marker'])}"
        ax.axvline(x=row['timestamp'], color='red', linestyle='--', linewidth=1, zorder=4)
        ax.annotate(
            text,
            xy=(row['timestamp'], ax.get_ylim()[1]),
            xytext=(5, -2),
            textcoords='offset points',
            fontsize=6,
            color='red',
            bbox=dict(boxstyle="round", edgecolor="red", facecolor="white"),
            rotation=0,
            ha='left', va='top'
        )


def plot_with_matplotlib(ax, y_col, title, df_markers, df_plot, palette):
    # Plot each marker zone separately
    for label, color in palette.items():
        grp = df_plot[df_plot['marker_label'] == label]
        if not grp.empty:
            ax.plot(grp['timestamp'], grp[y_col], label=label, color=color, linewidth=1, zorder=2)
            # Scatter singleton points explicitly
            if len(grp) <= 1:
                ax.scatter(grp['timestamp'], grp[y_col], color=color, s=50, zorder=3)
    annotate_and_mark(ax, y_col, df_markers)
    ax.set_title(title)
    ax.set_ylabel(y_col)
    ax.set_xlabel('Timestamp')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))


def generate_plots(merged_file_path, window_duration_mins, downsample_size, marker_values):
    
    subj_name = os.path.basename(os.path.dirname(merged_file_path))
    base_dir = os.path.dirname(merged_file_path)
    seg_path = os.path.join(base_dir, 'segments.pkl')

    df_temp_path = os.path.join(os.path.dirname(merged_file_path),'df_temp.pkl')
    variables = [
        ('BPM', 'BPM over Time'),
        ('Skin_conductance_uS', 'Skin Conductance (uS)')
    ]
    if not os.path.exists(seg_path):
        # Load the Excel data
        if not os.path.exists(df_temp_path):
            df = pd.read_excel(merged_file_path)
            with open(df_temp_path, 'wb') as dfpk:
                pickle.dump(df, dfpk)
        else:
            with open(df_temp_path, 'rb') as dfpk:
                df = pickle.load(dfpk)
                


            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        window_duration = pd.Timedelta(minutes=window_duration_mins)
        downsample = downsample_size
        segments = []
        for m in marker_values:
            for _, mr in df[df['marker'] == m].iterrows():
                start, end = mr['timestamp'], mr['timestamp'] + window_duration
                win = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)].copy()
                win['marker_label'] = f'T{m}'
                only_m = win[win['marker'] == m]
                others = win[win['marker'] != m].iloc[::downsample]
                combined = pd.concat([only_m, others]).sort_values('timestamp')
                segments.append({'marker': m, 'data': combined})
        with open(seg_path, 'wb') as f:
            pickle.dump(segments, f)

        # Build DataFrames
        df_plot = pd.concat([s['data'] for s in segments]).sort_values('timestamp')
        df_plot['marker'] = df_plot['marker'].where(df_plot['marker'].isin(marker_values), np.nan)
        df_plot['marker_label'] = df_plot['marker_label']  # ensure column exists
        df_markers = df_plot[df_plot['marker'].isin(marker_values)]

        # Palette mapping
        palette = {f'T{k}': c for k, c in zip(marker_values, ['blue','green','orange','purple','cyan','grey'])}

        # Create separate matplotlib figures
        for y_col, title in variables:
            fig, ax = plt.subplots(figsize=(20, 8))
            fig.suptitle(f'{title}', fontsize=18)

            plot_with_matplotlib(ax, y_col, title, df_markers, df_plot, palette)

            # Manual legend
            ax.legend(title='Trigger Zones', fontsize=12)
            plt.tight_layout(rect=[0, 0, 0.95, 0.95])

            # Save
            png = os.path.join(base_dir, f'{y_col}_{subj_name}_matplotlib.png')
            svg = os.path.join(base_dir, f'{y_col}_{subj_name}_matplotlib.svg')
            plt.savefig(png, dpi=300)
            plt.savefig(svg)
            plt.close(fig)
            
        # Cache segments
        with open(seg_path, 'wb') as f:
            pickle.dump(segments, f)
        return segments
    
        # Load or compute segments
    else:
        with open(seg_path, 'rb') as f:
            segments = pickle.load(f)
            return segments
        
if __name__ == '__main__':
    generate_plots(r"path/to/your/merged.xlsx")
