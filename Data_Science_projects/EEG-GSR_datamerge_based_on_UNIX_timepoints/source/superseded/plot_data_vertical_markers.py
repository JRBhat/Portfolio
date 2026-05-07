import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
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


# def plot_variable(ax, y_col, title, df_markers, df_plot, palette):
#     sns.lineplot(
#         data=df_plot,
#         x='timestamp',
#         y=y_col,
#         hue='marker_label',
#         palette=palette,
#         ax=ax,
#         linewidth=1,
#         legend=False
#     )
#     annotate_and_mark(ax, y_col, df_markers)
#     ax.set_title(title)
#     ax.set_ylabel(y_col)
#     ax.set_xlabel('Timestamp')
#     # Mark singleton segments explicitly
#     for lbl, grp in df_plot.groupby('marker_label'):
#         if lbl in palette and len(grp) <= 1:
#             ax.scatter(grp['timestamp'], grp[y_col], color=palette[lbl], s=50, zorder=5)
#     annotate_and_mark(ax, y_col, df_markers)
#     ax.set_title(title)
#     ax.set_ylabel(y_col)
#     ax.set_xlabel('Timestamp')


def plot_variable_single(fig, ax, y_col, title, df_markers, df_plot, palette):
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
    # Mark singleton segments explicitly
    for lbl, grp in df_plot.groupby('marker_label'):
        if lbl in palette and len(grp) <= 1:
            ax.scatter(grp['timestamp'], grp[y_col], color=palette[lbl], s=50, zorder=5)
    annotate_and_mark(ax, y_col, df_markers)
    ax.set_title(title)
    ax.set_ylabel(y_col)
    ax.set_xlabel('Timestamp')

def generate_plots(merged_file_path, window_duration_mins, downsample):

    # Configuration
    # marker_values = [1, 2, 3, 4]
    marker_values = [1, 2, 3, 4, 5, 6]
    subj_name = os.path.basename(os.path.dirname(merged_file_path))
    png_path = os.path.join(os.path.dirname(merged_file_path), f'time_series_plot_{subj_name}_minimal_mrmwd2.png')
    # svg_path = os.path.join(os.path.dirname(merged_file_path), f'time_series_plot_{subj_name}_minimal_mrmwd2.svg')
    base_dir = os.path.dirname(merged_file_path)
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
    print("Unique markers in df:", sorted(df['marker'].unique()))
    # Variables to plot and file-naming\    
    variables = [
        ('BPM', 'BPM over Time'),
        ('Skin_conductance_uS', 'Skin Conductance (uS)')
    ]
    # Sliding window and downsampling
    window_duration = pd.Timedelta(minutes=window_duration_mins)
    # downsample = 100
    segments = []

    for m in marker_values:
        for _, mr in df[df['marker'] == m].iterrows():
            start, end = mr['timestamp'], mr['timestamp'] + window_duration
            win = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)].copy()
            win['marker_label'] = f'M{m}'

            only_m = win[win['marker'] == m]
            others = win[win['marker'] != m].iloc[::downsample]

            combined = pd.concat([only_m, others]).sort_values('timestamp')
            print(f"Marker {m}: {len(combined)} rows")
            segments.append({'marker': m, 'data': combined})

    # Build plot DataFrame
    df_plot = pd.concat([s['data'] for s in segments]).sort_values('timestamp')

    # Replace any marker not in 1–6 (including 0,8,9,NaN) with NaN
    df_plot['marker'] = df_plot['marker'].where(df_plot['marker'].isin(marker_values), np.nan)

    # Print only the markers 1–6 for display
    display_markers = sorted(df_plot['marker'].dropna().unique())
    print("Markers in df_plot (display):", display_markers)

    # Prepare markers for annotation
    df_markers = df_plot[df_plot['marker'].isin(marker_values)]
    print("Markers in df_markers:", sorted(df_markers['marker'].unique()))

    # Palette and plotting
    palette = {f'M{k}': c for k, c in zip(marker_values, ['blue','green','orange','purple','cyan','grey'])}
    fig, axs = plt.subplots(1, 2, figsize=(15,5), sharex=True)
    fig.suptitle('Time Series (5 Min After Markers)')

    # plot_variable(axs[0], 'BPM', 'BPM over Time', df_markers, df_plot, palette)
    # plot_variable(axs[1], 'Skin_conductance_uS', 'Skin Conductance (uS)', df_markers, df_plot, palette)

    # # Manual legend: only M1–M6
    # handles, labels = axs[0].get_legend_handles_labels()
    # valid = [(h, l) for h, l in zip(handles, labels) if l in palette]
    # if valid:
    #     hs, ls = zip(*valid)
    #     fig.legend(hs, ls, loc='upper right', title='Marker Zones')

    # # Format time axis and save
    # for ax in axs:
    #     ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    # plt.tight_layout(rect=[0,0,0.95,0.95])
    # plt.savefig(png_path, dpi=300)
    # plt.savefig(svg_path)
    # plt.close(fig)


    for y_col, title in variables:
        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle(f'{title} (5 Min After Markers)', fontsize=18)
        plot_variable_single(fig, ax, y_col, title, df_markers, df_plot, palette)
        # manual legend
        handles, labels = ax.get_legend_handles_labels()
        valid = [(h, l) for h, l in zip(handles, labels) if l in palette]
        if valid:
            hs, ls = zip(*valid)
            fig.legend(hs, ls, loc='upper right', title='Marker Zones', fontsize=12)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.tight_layout(rect=[0,0,0.95,0.95])
        # save
        png = os.path.join(base_dir, f'{y_col}_{subj_name}.png')
        svg = os.path.join(base_dir, f'{y_col}_{subj_name}.svg')
        plt.savefig(png, dpi=300)
        plt.savefig(svg)
        plt.close(fig)
    # Cache segments
    with open(segment_pkl_path, 'wb') as f:
        pickle.dump(segments, f)

    return segments

if __name__ == '__main__':
    generate_plots(r"path/to/your/merged.xlsx")
