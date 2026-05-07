"""
Data loading and filtering for the Raman water-concentration pipelines.

Provides ``load_and_filter``, which reads the Excel input, casts the
depth column to integer, applies the standard exclusion and depth-range
filters, and emits structured log messages via a ``QualityLog`` instance.
"""

import pandas as pd
from pathlib import Path
from config import VMIN, VMAX, DEPTH_MIN_UM, DEPTH_MAX_UM


def load_and_filter(path: Path, log) -> pd.DataFrame:
    """
    Load the Raman Excel file and apply standard pre-processing filters.

    Steps performed:
    1. Read the first sheet of the Excel file.
    2. Round and cast the ``depth`` column to ``int``.
    3. Filter to rows where ``exclude == 0`` and
       ``depth`` is in [DEPTH_MIN_UM, DEPTH_MAX_UM].
    4. Log load statistics, row counts, and Water_Percent range via *log*.

    Parameters
    ----------
    path : Path
        Path to the input Excel file.
    log : QualityLog
        Quality logger used to emit INFO and WARN messages.

    Returns
    -------
    pd.DataFrame
        Filtered copy of the input data ready for panel processing.
    """
    df_raw = pd.read_excel(path, sheet_name=0)
    log.global_info(f"Loaded: {df_raw.shape[0]:,} rows x {df_raw.shape[1]} columns")
    log.global_info(f"Columns: {df_raw.columns.tolist()}")

    df_raw["depth"] = df_raw["depth"].round().astype(int)

    n_neg  = (df_raw["depth"] < DEPTH_MIN_UM).sum()
    n_deep = (df_raw["depth"] > DEPTH_MAX_UM).sum()
    if n_neg:
        log.info(f"Rows depth < {DEPTH_MIN_UM} (filtered): {n_neg:,}")
    if n_deep:
        log.info(f"Rows depth > {DEPTH_MAX_UM} (filtered): {n_deep:,}")

    df = df_raw[
        (df_raw["exclude"] == 0) &
        (df_raw["depth"].between(DEPTH_MIN_UM, DEPTH_MAX_UM))
    ].copy()

    n_excl   = (df_raw["exclude"] == 1).sum()
    pct_excl = 100.0 * n_excl / len(df_raw)
    log.global_info(
        f"After exclude==0 + depth {DEPTH_MIN_UM}-{DEPTH_MAX_UM}: {len(df):,} rows used "
        f"({n_excl:,} excluded by analyst, {pct_excl:.1f}%)"
    )

    water_pct = df["Water_Percent"]
    log.header("WATER_PERCENT RANGE")
    log.global_info(
        f"min={water_pct.min():.3f}%  max={water_pct.max():.3f}%  "
        f"mean={water_pct.mean():.2f}%  NaN={water_pct.isna().sum()}"
    )
    if (water_pct < VMIN).sum():
        log.warn("ALL", "ALL", "ALL", f"{(water_pct < VMIN).sum()} values < VMIN={VMIN}% (clipped)")
    if (water_pct > VMAX).sum():
        log.warn("ALL", "ALL", "ALL", f"{(water_pct > VMAX).sum()} values > VMAX={VMAX}% (clipped)")

    return df
