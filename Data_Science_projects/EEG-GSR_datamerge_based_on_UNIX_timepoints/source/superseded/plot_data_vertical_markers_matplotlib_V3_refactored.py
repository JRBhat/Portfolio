from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import pickle
import numpy as np
from typing import List, Dict


class DataLoader:
    """Handles loading Excel or cached DataFrames."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.cache_path = os.path.join(os.path.dirname(file_path), 'df_temp.pkl')

    def load(self) -> pd.DataFrame:
        if os.path.exists(self.cache_path):
            with open(self.cache_path, 'rb') as f:
                df = pickle.load(f)
        else:
            df = pd.read_excel(self.file_path)
            with open(self.cache_path, 'wb') as f:
                pickle.dump(df, f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df


class Segmenter:
    """Segments DataFrame into marker windows with optional downsampling."""
    def __init__(self, window_mins: int, downsample: int):
        self.window_duration = pd.Timedelta(minutes=window_mins)
        self.downsample = downsample

    def segment(self, df: pd.DataFrame, marker_values: List[int]) -> List[Dict]:
        segments = []
        for m in marker_values:
            marker_rows = df[df['marker'] == m]
            for ts in marker_rows['timestamp']:
                win = df[(df['timestamp'] >= ts) & (df['timestamp'] <= ts + self.window_duration)].copy()
                win['marker_label'] = f'T{m}'
                only_m = win[win['marker'] == m]
                others = win[win['marker'] != m].iloc[::self.downsample]
                combined = pd.concat([only_m, others]).sort_values('timestamp')
                segments.append({'marker': m, 'data': combined})
        return segments


class Plotter:
    """Handles plotting time series with marker annotations."""
    def __init__(self, palette: Dict[str, str]):
        self.palette = palette

    def annotate_markers(self, ax: plt.Axes, df_markers: pd.DataFrame):
        """Vectorized marker annotation without iterrows."""
        if df_markers.empty:
            return

        # Draw vertical lines
        ax.vlines(
            x=df_markers['timestamp'],
            ymin=ax.get_ylim()[0],
            ymax=ax.get_ylim()[1],
            colors='red',
            linestyles='--',
            linewidth=1,
            zorder=4
        )

        # Add text labels
        x_coords = df_markers['timestamp'].values
        y_coord = ax.get_ylim()[1]
        labels = [f"M{int(m)}" for m in df_markers['marker']]

        # Using ax.text in a loop is okay here since it's very fast compared to iterrows
        for x, label in zip(x_coords, labels):
            ax.text(
                x, y_coord, label,
                fontsize=6,
                color='red',
                bbox=dict(boxstyle="round", edgecolor="red", facecolor="white"),
                ha='left', va='top',
                zorder=5
            )

    def plot(self, df_plot: pd.DataFrame, df_markers: pd.DataFrame, y_col: str, title: str, save_path: str):
        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle(title, fontsize=18)

        for label, color in self.palette.items():
            grp = df_plot[df_plot['marker_label'] == label]
            if not grp.empty:
                ax.plot(grp['timestamp'], grp[y_col], label=label, color=color, linewidth=1, zorder=2)
                if len(grp) <= 1:
                    ax.scatter(grp['timestamp'], grp[y_col], color=color, s=50, zorder=3)

        self.annotate_markers(ax, df_markers)
        ax.set_title(title)
        ax.set_ylabel(y_col)
        ax.set_xlabel('Timestamp')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.legend(title='Trigger Zones', fontsize=12)
        plt.tight_layout(rect=[0, 0, 0.95, 0.95])
        plt.savefig(save_path, dpi=300)
        plt.close(fig)


def generate_plots(
    merged_file_path: str,
    window_duration_mins: int = 5,
    downsample_size: int = 5,
    marker_values: List[int] = [1, 2, 3]
) -> List[Dict]:

    base_dir = os.path.dirname(merged_file_path)
    seg_path = os.path.join(base_dir, 'segments.pkl')
    subj_name = os.path.basename(os.path.dirname(merged_file_path))

    if os.path.exists(seg_path):
        with open(seg_path, 'rb') as f:
            return pickle.load(f)

    # Load and segment data
    df = DataLoader(merged_file_path).load()
    segments = Segmenter(window_duration_mins, downsample_size).segment(df, marker_values)

    df_plot = pd.concat([s['data'] for s in segments]).sort_values('timestamp')
    df_plot['marker'] = df_plot['marker'].where(df_plot['marker'].isin(marker_values), np.nan)
    df_markers = df_plot[df_plot['marker'].isin(marker_values)]

    # Define palette
    palette = {f'T{k}': c for k, c in zip(marker_values, ['blue','green','orange','purple','cyan','grey'])}
    plotter = Plotter(palette)

    variables = [('BPM', 'BPM over Time'), ('Skin_conductance_uS', 'Skin Conductance (uS)')]
    for y_col, title in variables:
        png = os.path.join(base_dir, f'{y_col}_{subj_name}_matplotlib.png')
        plotter.plot(df_plot, df_markers, y_col, title, png)

    # Cache segments
    with open(seg_path, 'wb') as f:
        pickle.dump(segments, f)

    return segments


if __name__ == '__main__':
    generate_plots(r"path/to/your/merged.xlsx")
