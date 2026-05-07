"""
Per-Subject 2D Water Profile Heatmaps  --  Version 10
======================================================

KEY CHANGES vs v9
-----------------
FIX -- Preserve original scan order from the Excel file (Step 3)

  In v9, pandas groupby+unstack silently sorted the scan columns by
  x_position value, even when .sort_index(axis=1) was commented out.
  The sort is performed internally by unstack() as it builds the column
  MultiIndex.

  v10 captures the first-seen order of x_position values BEFORE the
  groupby (using pd.unique(), which is insertion-order preserving), then
  reindexes the pivot columns to that order AFTER unstack().

  Result: scan columns appear in the order they were recorded in the
  Excel file, not sorted by x_position.

  All other pipeline steps (merge, PCHIP, blur, render) are unchanged.

NOTE ON 2D vs 3D CONSISTENCY
  The 2D and 3D plots are intentionally different representations:
  - 2D (v10): x-axis = scan index 1..n (original data order), PCHIP.
    Answers: "How do depth profiles compare across scans?"
  - 3D (v7): x/y-axes = real (x_position, y_position) in µm, griddata.
    Answers: "What is the spatial water distribution on the skin?"
  No face of the 3D cube equals the 2D view because the scan positions
  are scattered in 2D space, not on a 1D line.

========================================================================
PIPELINE
========================================================================
Step 1  Load + filter (exclude==0, depth 0-40, depth cast to int)
Step 2  Merge near-duplicate x_positions (< SCAN_MERGE_THRESHOLD_UM µm)
Step 3  Pivot: group by scan_group -> (41 x n_scans) matrix,
        columns in original data order (first-seen x_position), indexed 0…n-1
Step 4  Fill partial-depth NaN cells (lateral linear interp on indices)
        Safety fill: remaining NaN -> overall mean
Step 5  Two-pass PCHIP interpolation:
          Pass A: lateral (scan index -> fine grid, per depth row)
          Pass B: depth   (raw depths -> ND_OUT, per fine column)
Step 6  Gaussian blur (sigma_x = SIGMA_X_SCANS * NX_PER_SCAN px,
                       sigma_y = SIGMA_Y_UM / DEPTH_SUBSTEP px)
Step 7  Render: x-axis ticks at each scan centre, labelled 1…n_scans
"""

import os
import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
from scipy.interpolate import PchipInterpolator, interp1d
from scipy.ndimage import gaussian_filter


def make_2d_heatmap(input_path, output_dir):
    # -- Colour scale -------------------------------------------------------
    VMIN = 8
    VMAX = 75

    # -- Custom colour map --------------------------------------------------
    CMAP_NODES  = [0.00, 0.18, 0.38, 0.58, 0.78, 1.00]
    CMAP_COLORS = ["#FFFF00", "#CC9900", "#4CAF50", "#40E0D0", "#1E90FF", "#00008B"]

    # -- Output resolution --------------------------------------------------
    DEPTH_SUBSTEP = 0.25                          # µm per depth pixel
    ND_OUT        = int(40 / DEPTH_SUBSTEP) + 1  # 161 depth pixels
    NX_PER_SCAN   = 20                            # output pixels per scan profile

    # -- Scan merging -------------------------------------------------------
    SCAN_MERGE_THRESHOLD_UM = 0 # merge x_positions closer than this

    # -- Smoothing ----------------------------------------------------------
    SIGMA_X_SCANS = 0.4   # lateral blur = this fraction of one scan width
    SIGMA_Y_UM    = 1.0   # depth blur in µm

    # -- Figure layout ------------------------------------------------------
    # ROWS = [("_A", "Code A"), ("_B", "Code B"), ("_C", "Code C"), ("_D", "Code D")]
    ROWS = [("_B", "Code B"), ("_C", "Code C"), ("_D", "Code D")]
    COLS = [("T01", "BL"),    ("T02", "D01_1h"), ("T03", "D01_4h")]

    EXPECTED_SCANS_PER_PANEL = 10


    # ======================================================================
    # SECTION 2 -- COLOUR MAP
    # ======================================================================

    cmap = LinearSegmentedColormap.from_list(
        "water_cmap", list(zip(CMAP_NODES, CMAP_COLORS)), N=512
    )
    cmap.set_bad(color="white")


    # ======================================================================
    # SECTION 3 -- QUALITY LOGGER
    # ======================================================================

    class QualityLog:
        def __init__(self, out_dir):
            ts          = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.path   = os.path.join(out_dir, f"data_quality_log_2D_v10_{ts}.txt")
            self._lines = []
            self._nwarn = 0
            self._ninfo = 0

        def _append(self, line):
            self._lines.append(line)
            print(line)

        def header(self, title):
            sep = "=" * 70
            self._append(f"\n{sep}")
            self._append(f"  {title}")
            self._append(sep)

        def info(self, msg):
            self._lines.append(f"  INFO  {msg}")
            self._ninfo += 1

        def global_info(self, msg):
            self._append(f"  INFO  {msg}")
            self._ninfo += 1

        def warn(self, subj, prod, tp, msg):
            line = f"  WARN  [{subj} {prod} {tp}]  {msg}"
            self._append(line)
            self._nwarn += 1

        def note(self, msg):
            self._append(f"  {msg}")

        def write(self):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            header_lines = [
                "=" * 70,
                "  DATA QUALITY LOG  --  2D Water Profile Heatmap Script  (v10)",
                f"  Generated : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"  Script    : {os.path.basename(__file__)}",
                f"  Input     : {input_path}",
                "  NOTE      : v10 stacks scan profiles in original data order (not sorted by x_position).",
                f"              Near-duplicate scans (< {SCAN_MERGE_THRESHOLD_UM} µm apart) are merged.",
                "              Lateral interpolation uses PCHIP (no overshoot by construction).",
                "=" * 70,
            ]
            footer_lines = [
                "",
                "=" * 70,
                f"  TOTALS:  {self._nwarn} warning(s),  {self._ninfo} info message(s)",
                "=" * 70,
            ]
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(header_lines + self._lines + footer_lines))
                fh.write("\n")
            print(f"\n  Log written -> {self.path}")
            print(f"  Total: {self._nwarn} warning(s), {self._ninfo} info message(s)\n")


    # ======================================================================
    # SECTION 4 -- DATA LOADING
    # ======================================================================

    log = QualityLog(output_dir)
    log.header("DATA LOADING")

    df_raw = pd.read_excel(input_path, sheet_name=0)
    log.global_info(f"Loaded: {df_raw.shape[0]:,} rows x {df_raw.shape[1]} columns")
    log.global_info(f"Columns: {df_raw.columns.tolist()}")

    df_raw["depth"] = df_raw["depth"].round().astype(int)

    n_neg   = (df_raw["depth"] < 0).sum()
    n_deep  = (df_raw["depth"] > 40).sum()
    if n_neg:
        log.info(f"Rows depth < 0 (filtered): {n_neg:,}")
    if n_deep:
        log.info(f"Rows depth > 40 (filtered): {n_deep:,}")

    df = df_raw[
        (df_raw["exclude"] == 0) &
        (df_raw["depth"].between(0, 40))
    ].copy()

    n_excl   = (df_raw["exclude"] == 1).sum()
    pct_excl = 100.0 * n_excl / len(df_raw)
    log.global_info(
        f"After exclude==0 + depth 0-40: {len(df):,} rows used "
        f"({n_excl:,} excluded by analyst, {pct_excl:.1f}%)"
    )

    water_pct = df["Water_Percent"]
    log.header("WATER_PERCENT RANGE")
    log.global_info(
        f"min={water_pct.min():.3f}%  max={water_pct.max():.3f}%  "
        f"mean={water_pct.mean():.2f}%  NaN={water_pct.isna().sum()}"
    )
    if (water_pct < VMIN).sum():
        log.warn("ALL", "ALL", "ALL", f"{(water_pct<VMIN).sum()} values < VMIN={VMIN}% (clipped)")
    if (water_pct > VMAX).sum():
        log.warn("ALL", "ALL", "ALL", f"{(water_pct>VMAX).sum()} values > VMAX={VMAX}% (clipped)")

    log.header("SCAN COUNT PER PANEL")
    subjects = sorted(df["subjectID"].unique())
    for prod, plabel in ROWS:
        for tp, tlabel in COLS:
            sub_p  = df[(df["product"] == prod) & (df["timePoint"] == tp)]
            counts = sub_p.groupby("subjectID")["x_position"].nunique()
            flags  = [f"{s}={n}" for s, n in counts.items() if n < EXPECTED_SCANS_PER_PANEL]
            flag_str = f"  LOW: {', '.join(flags)}" if flags else ""
            log.info(f"  {plabel} {tlabel}: {dict(counts)}{flag_str}")

    log.header("RENDERING BEGINS")


    # ======================================================================
    # SECTION 5 -- HELPER: MERGE NEAR-DUPLICATE X-POSITIONS
    # ======================================================================

    def merge_scan_positions(x_positions_sorted):
        """
        Given a sorted list of x_position values, return a dict mapping
        each original x_position to a representative group value.
        Adjacent positions within SCAN_MERGE_THRESHOLD_UM are merged.

        Returns
        -------
        x_to_rep : dict  {original_x -> representative_x}
        n_merged : int   number of positions that were collapsed into another
        """
        x_to_rep = {}
        group_rep = None
        n_merged  = 0
        for x in x_positions_sorted:
            if group_rep is None or abs(x - group_rep) >= SCAN_MERGE_THRESHOLD_UM:
                group_rep = x          # start a new group
            else:
                n_merged += 1          # this x collapses into the current group
            x_to_rep[x] = group_rep
        return x_to_rep, n_merged


    # ======================================================================
    # SECTION 6 -- PIPELINE FUNCTION
    # ======================================================================

    def build_panel_matrix(subj, product, timepoint, log, panel_warnings):
        """
        Build a smooth (ND_OUT x n_scans*NX_PER_SCAN) display matrix.

        Step 2  Near-duplicate x_positions are merged (averaged) before
                pivoting to avoid the sharp local spikes that caused
                RectBivariateSpline oscillations in v8.
        Step 5  Two-pass PCHIP: lateral (per depth row) then depth (per
                fine column).  PCHIP output is always bounded by the data
                values at the knots -- no clipping artefacts possible.

        Returns
        -------
        mat_out  : ndarray (ND_OUT, n_scans * NX_PER_SCAN)
        (0, 40)  : depth extent
        n_scans  : int  (after merging)
        """
        # -- Step 1: Subset ------------------------------------------------
        sub = df[
            (df["subjectID"] == subj) &
            (df["product"]   == product) &
            (df["timePoint"] == timepoint)
        ]
        if len(sub) == 0:
            panel_warnings.append("No data -- panel rendered as flat mid-range.")
            fallback = np.full((ND_OUT, NX_PER_SCAN), (VMIN + VMAX) / 2.0)
            return fallback, (0, 40), 0

        # -- Step 2: Merge near-duplicate x_positions ----------------------
        # pd.unique() is insertion-order preserving -- captures the order
        # scans appear in the Excel file, without sorting by x_position.
        # dropna() prevents NaN x_positions from breaking the dict lookup
        # in the reps_in_order step below (NaN dict keys are unreliable).
        xvals_all    = pd.unique(sub["x_position"].dropna())
        x_to_rep, n_merged = merge_scan_positions(xvals_all)

        if n_merged > 0:
            panel_warnings.append(
                f"{n_merged} scan position(s) merged into neighbour "
                f"(within {SCAN_MERGE_THRESHOLD_UM} µm): "
                f"original x_pos = {[round(float(x),1) for x in xvals_all]}"
            )
            sub = sub.copy()
            sub["scan_group"] = sub["x_position"].map(x_to_rep)
            group_col = "scan_group"
        else:
            group_col = "x_position"

        # -- Step 3: Pivot (depth x scan, original data order) -----------
        # unstack() sorts columns by x_position internally; we undo that
        # by reindexing to the first-seen order captured in xvals_all.
        # For the merge case, map each xvals_all entry to its representative
        # so the column order matches what unstack produced after merging.
        pivot = (
            sub.groupby([group_col, "depth"])["Water_Percent"]
            .mean()
            .unstack(level=group_col)
            .sort_index(axis=0)
            .reindex(index=range(0, 41))
        )
        # Restore original scan order: derive representative values in
        # first-seen order, then keep only those present as columns.
        reps_in_order = list(dict.fromkeys(x_to_rep[x] for x in xvals_all))
        reps_in_order = [r for r in reps_in_order if r in pivot.columns]
        pivot   = pivot[reps_in_order]
        mat_raw = pivot.to_numpy(dtype=float)   # (41, n_scans)
        xvals   = pivot.columns.values          # representative x_positions (for log)
        n_scans = mat_raw.shape[1]
        scan_idx = np.arange(n_scans, dtype=float)

        if n_scans < EXPECTED_SCANS_PER_PANEL:
            panel_warnings.append(
                f"Only {n_scans} scan(s) found (expected {EXPECTED_SCANS_PER_PANEL}) "
                f"after merging."
            )

        n_clip_lo = int((sub["Water_Percent"] < VMIN).sum())
        n_clip_hi = int((sub["Water_Percent"] > VMAX).sum())
        if n_clip_lo:
            panel_warnings.append(f"{n_clip_lo} values < VMIN={VMIN}% clipped.")
        if n_clip_hi:
            panel_warnings.append(f"{n_clip_hi} values > VMAX={VMAX}% clipped.")

        log.info(
            f"  [{subj} {product} {timepoint}]  {n_scans} scan(s) after merge, "
            f"rep x_positions: {[round(float(x),1) for x in xvals]}"
        )

        # -- Step 4: Fill partial-depth NaN cells (on scan index axis) ----
        mat_f = mat_raw.copy()
        n_incomplete = int(np.isnan(mat_f[-1, :]).sum())
        if n_incomplete:
            panel_warnings.append(
                f"{n_incomplete}/{n_scans} scan(s) don't reach depth=40 "
                f"(filled by lateral interpolation on scan index)."
            )

        for row in range(mat_f.shape[0]):
            valid = ~np.isnan(mat_f[row])
            if valid.sum() >= 2:
                f_i = interp1d(
                    scan_idx[valid], mat_f[row, valid],
                    kind="linear", bounds_error=False,
                    fill_value=(mat_f[row, valid][0], mat_f[row, valid][-1])
                )
                mat_f[row] = f_i(scan_idx)

        n_still_nan = int(np.isnan(mat_f).sum())
        if n_still_nan:
            panel_warnings.append(
                f"{n_still_nan} cell(s) still NaN after lateral fill; "
                f"replaced with overall mean."
            )
            overall_mean = float(np.nanmean(mat_f)) if not np.all(np.isnan(mat_f)) else VMIN
            mat_f = np.where(np.isnan(mat_f), overall_mean, mat_f)

        # -- Step 5a: PCHIP lateral (per depth row) ----------------------
        # For each of the 41 depth rows, interpolate from n_scans knots
        # to n_scans * NX_PER_SCAN fine columns.
        # PCHIP guarantees output bounded by [min(row), max(row)].
        x_fine   = np.linspace(0, n_scans - 1, n_scans * NX_PER_SCAN)
        mat_fine = np.empty((41, n_scans * NX_PER_SCAN), dtype=float)

        if n_scans == 1:
            # Single scan: tile across all output columns
            for d in range(41):
                mat_fine[d, :] = mat_f[d, 0]
        else:
            for d in range(41):
                pchip = PchipInterpolator(scan_idx, mat_f[d, :])
                mat_fine[d, :] = pchip(x_fine)

        # -- Step 5b: PCHIP depth (per fine column) ----------------------
        # Upsample from 41 integer depth steps to ND_OUT fine rows.
        y_raw  = np.arange(0, 41, 1.0)
        y_fine = np.linspace(0, 40, ND_OUT)
        mat_s  = np.empty((ND_OUT, n_scans * NX_PER_SCAN), dtype=float)

        for col in range(n_scans * NX_PER_SCAN):
            pchip = PchipInterpolator(y_raw, mat_fine[:, col])
            mat_s[:, col] = pchip(y_fine)

        # Safety clip (PCHIP is bounded by data; this handles any floating-
        # point edge cases and the display VMIN/VMAX limits)
        mat_s = np.clip(mat_s, VMIN, VMAX)

        # -- Step 6: Gaussian blur ----------------------------------------
        sigma_x_px = SIGMA_X_SCANS * NX_PER_SCAN
        sigma_y_px = SIGMA_Y_UM / DEPTH_SUBSTEP

        mat_out = np.clip(
            gaussian_filter(mat_s, sigma=[sigma_y_px, sigma_x_px]),
            VMIN, VMAX
        )

        return mat_out, (0, 40), n_scans


    # ======================================================================
    # SECTION 7 -- GENERATE ONE FIGURE PER SUBJECT
    # ======================================================================

    all_panel_warnings = []

    for subj in subjects:
        log.note(f"\n  ----- Subject {subj} -----")

        fig, axes = plt.subplots(
            nrows=len(ROWS), ncols=len(COLS),
            figsize=(15, 4.5 * len(ROWS)),
            gridspec_kw={"hspace": 0.35, "wspace": 0.30}
        )
        fig.patch.set_facecolor("white")

        subj_warnings = 0

        for i, (prod_code, prod_label) in enumerate(ROWS):
            for j, (tp_code, tp_label) in enumerate(COLS):

                ax             = axes[i, j]
                panel_warnings = []

                mat, (y0, y1), n_scans = build_panel_matrix(
                    subj, prod_code, tp_code, log, panel_warnings
                )

                for w_msg in panel_warnings:
                    log.warn(subj, prod_code, tp_code, w_msg)
                    subj_warnings += 1
                if panel_warnings:
                    all_panel_warnings.append((subj, prod_code, tp_code, panel_warnings))

                ax.imshow(
                    mat,
                    origin="upper",
                    extent=[0, 1, y1, y0],
                    aspect="auto",
                    cmap=cmap,
                    vmin=VMIN, vmax=VMAX,
                    interpolation="bilinear"
                )

                # Y axis: depth
                ax.set_ylim(y1, y0)
                ax.set_yticks(np.arange(0, 41, 5))
                ax.set_yticklabels([str(v) for v in np.arange(0, 41, 5)], fontsize=8)
                ax.set_ylabel("depth [µm]", fontsize=9)

                # X axis: scan number ticks centred on each scan column
                if n_scans > 0:
                    tick_pos    = [(k + 0.5) / n_scans for k in range(n_scans)]
                    tick_labels = [str(k + 1) for k in range(n_scans)]
                    ax.set_xticks(tick_pos)
                    ax.set_xticklabels(tick_labels, fontsize=7)
                else:
                    ax.set_xticks([])
                ax.set_xlabel("Scan #", fontsize=9, labelpad=2)

                if i == 0:
                    ax.set_title(tp_label, fontsize=11, fontweight="bold", pad=6)
                if j == 0:
                    ax.text(-0.28, 0.5, prod_label,
                            transform=ax.transAxes,
                            fontsize=11, fontweight="bold",
                            va="center", ha="center", rotation=90)

        # Shared colour bar
        cbar_ax = fig.add_axes([0.93, 0.12, 0.018, 0.76])
        sm = plt.cm.ScalarMappable(
            cmap=cmap, norm=mcolors.Normalize(vmin=VMIN, vmax=VMAX)
        )
        sm.set_array([])
        cbar = fig.colorbar(sm, cax=cbar_ax)
        cbar.ax.invert_yaxis()
        cbar.set_label("% Water", fontsize=10, labelpad=6)
        cbar.ax.tick_params(labelsize=8)

        fig.suptitle(
            f"2D Water Profile Heatmap -- {subj}  "
            f"(scan profiles 1–n, depth 0–40 µm)",
            fontsize=13, fontweight="bold", y=0.99
        )

        out_path = os.path.join(output_dir, f"{subj}_2d.png")
        plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        log.global_info(
            f"  {subj}: saved -> {out_path}  [{subj_warnings} warning(s)]"
        )


    # ======================================================================
    # SECTION 8 -- SUMMARY AND LOG
    # ======================================================================

    log.header("RUN SUMMARY")
    total_panels  = len(subjects) * len(ROWS) * len(COLS)
    panels_warned = len(all_panel_warnings)
    log.global_info(
        f"Total panels rendered: {total_panels}  "
        f"({panels_warned} had at least one quality warning)"
    )
    if all_panel_warnings:
        log.note("\n  Panels with warnings:")
        for subj, prod, tp, msgs in all_panel_warnings:
            log.note(f"    {subj} {prod} {tp}:")
            for m in msgs:
                log.note(f"      - {m}")

    log.header("v10 DESIGN NOTES")
    log.note("  x-axis = scan index 1…n, in original Excel data order (NOT sorted by x_position).")
    log.note(f"  Scans within {SCAN_MERGE_THRESHOLD_UM} µm of each other are merged (averaged).")
    log.note("  Lateral interpolation: PCHIP (guaranteed no overshoot beyond data range).")
    log.note("  Depth interpolation:   PCHIP (smooth upsampling 41 -> ND_OUT rows).")
    log.note("  For the spatially-correct 3D view (using actual x,y coords)")
    log.note("  see make_heatmap_per_subject_3d_v7.py.")
    log.note("  Compare with v9 outputs (_2D_v9.png) to see effect of scan reordering.")

    log.write()
    print("All subjects done.")


if __name__ == "__main__":
    input_path = "data/raman_water_data.xlsx"
    output_dir = "output/"
    make_2d_heatmap(input_path, output_dir)
