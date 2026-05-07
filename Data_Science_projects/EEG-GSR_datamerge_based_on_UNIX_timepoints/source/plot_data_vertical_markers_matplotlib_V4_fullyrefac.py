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
        self.file_path = file_path # Excel file path    
        self.cache_path = os.path.join(os.path.dirname(file_path), 'df_temp.pkl') # Cache file path

    # load data with caching
    def load(self) -> pd.DataFrame:
        # Load DataFrame from cache if exists, else from Excel and cache it
        if os.path.exists(self.cache_path):
            with open(self.cache_path, 'rb') as f:
                df = pickle.load(f)
        else:
            df = pd.read_excel(self.file_path)
            with open(self.cache_path, 'wb') as f:
                pickle.dump(df, f)
        df['timestamp'] = pd.to_datetime(df['timestamp']) # Ensure timestamp is datetime before returning df
        return df


class Segmenter:
    """Segments DataFrame into marker windows with optional downsampling."""
    def __init__(self, window_mins: int, downsample: int):
        # for windowing due to pd.Timedelta usage, it needs to be in minutes,
        # without this it does not work properly because of numpy datetime64 compatibility
        self.window_duration = pd.Timedelta(minutes=window_mins) 
        self.downsample = downsample # downsample factor for non-marker rows - keeps every nth row 
        # applied to rows not matching markers so that marker rows are always kept

    def segment(self, df: pd.DataFrame, marker_values: List[int]) -> List[Dict]:
        """Vectorized segmentation without nested loops."""
        if df.empty or not marker_values:
            return []

        # Filter only marker rows we care about
        markers_df = df[df['marker'].isin(marker_values)].copy()

        # Create empty list to store segments
        segments = []

        # Process each marker type separately
        for m in marker_values:
            marker_times = markers_df.loc[markers_df['marker'] == m, 'timestamp']

            # Create windows for all timestamps of this marker
            start_times = marker_times.values
            end_times = start_times + np.timedelta64(self.window_duration, 's')

            # Boolean mask for all rows that fall into any marker window
            mask = np.zeros(len(df), dtype=bool)
            for start, end in zip(start_times, end_times):
                mask |= (df['timestamp'].values >= start) & (df['timestamp'].values <= end)

            df_window = df.loc[mask].copy()
            df_window['marker_label'] = f'T{m}'

            # Ensure full marker points included, downsample others
            only_m = df_window[df_window['marker'] == m]
            others = df_window[df_window['marker'] != m].iloc[::self.downsample]
            combined = pd.concat([only_m, others]).sort_values('timestamp')

            segments.append({'marker': m, 'data': combined})

        return segments


class Plotter:
    """Handles plotting time series with marker annotations."""
    def __init__(self, palette: Dict[str, str]):
        self.palette = palette

    def annotate_markers(self, ax: plt.Axes, df_markers: pd.DataFrame):
        """Vectorized marker annotation."""
        if df_markers.empty:
            return

        ax.vlines(
            x=df_markers['timestamp'],
            ymin=ax.get_ylim()[0],
            ymax=ax.get_ylim()[1],
            colors='red',
            linestyles='--',
            linewidth=1,
            zorder=4
        )

        x_coords = df_markers['timestamp'].values
        y_coord = ax.get_ylim()[1]
        labels = [f"M{int(m)}" for m in df_markers['marker']]

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
    marker_values: List[int] | None = None,
) -> List[Dict]:
    """
    Load a merged EEG-GSR Excel file, segment it into per-marker windows, and
    produce per-variable time-series PNGs.

    Caching:
        If a ``segments.pkl`` file exists in the same directory as
        ``merged_file_path``, the function returns the cached segments
        immediately without reprocessing.  Delete the file to force a
        full recompute.

    Palette:
        All marker labels currently share the colour ``'black'`` (with
        ``'cyan'`` and ``'grey'`` for labels beyond the first four). The
        palette is built as ``{f'T{k}': colour for k in marker_values}``.

    Output PNGs:
        One PNG per variable in ``[('BPM', …), ('Skin_conductance_uS', …)]``,
        named ``<variable>_<subject_name>_matplotlib.png`` and saved next to
        ``merged_file_path``.

    Parameters:
        merged_file_path: Absolute path to the merged ``.xlsx`` workbook.
        window_duration_mins: Duration of each marker window in minutes.
        downsample_size: Keep every *n*-th non-marker row to reduce plot density.
        marker_values: List of integer marker codes to segment on.
            Defaults to ``[1, 2, 3]`` if ``None``.

    Returns:
        List of segment dicts, each with keys ``'marker'`` (int) and
        ``'data'`` (DataFrame).
    """
    if marker_values is None:
        marker_values = [1, 2, 3]

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
    # palette = {f'T{k}': c for k, c in zip(marker_values, ['blue','green','orange','purple','cyan','grey'])}
    palette = {f'T{k}': c for k, c in zip(marker_values, ['black','black','black','black','cyan','grey'])}
    
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
