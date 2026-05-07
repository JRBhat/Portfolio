"""
Custom colour map for Raman water-concentration heatmaps.

Provides ``build_water_cmap``, which constructs the shared yellow-to-navy
``LinearSegmentedColormap`` used by the 2D, 3D, and slide pipelines.
NaN cells are rendered as white.
"""

from matplotlib.colors import LinearSegmentedColormap
from config import CMAP_NODES, CMAP_COLORS


def build_water_cmap(n: int = 512) -> LinearSegmentedColormap:
    """
    Build the shared water-concentration colour map.

    Parameters
    ----------
    n : int, optional
        Number of colour levels (default 512).

    Returns
    -------
    LinearSegmentedColormap
        A 6-node map running from yellow (dry) through green, turquoise,
        sky-blue to dark navy (wet).  NaN cells are set to white.
    """
    cmap = LinearSegmentedColormap.from_list(
        "water_cmap", list(zip(CMAP_NODES, CMAP_COLORS)), N=n
    )
    cmap.set_bad(color="white")
    return cmap
