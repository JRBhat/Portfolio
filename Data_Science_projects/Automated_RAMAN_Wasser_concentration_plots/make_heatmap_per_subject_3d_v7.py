"""
Per-Subject 3D Water Profile Heatmaps  --  Version 7
=====================================================

KEY CHANGE vs v6
----------------
Previous versions used x_position as the only lateral axis and built an
artificial thin-slab Y dimension with Y_THICK=0.25.  This was wrong:
the 10 scan positions per panel are scattered in 2D space with real
(x_position, y_position) coordinates.

v7 uses both x_position and y_position as the two spatial horizontal
axes of the 3D box, and depth as the vertical axis.  The result is a
true spatial tissue block:

    x-axis  → x_position [µm]   (left-right on skin)
    y-axis  → y_position [µm]   (front-back on skin)
    z-axis  → depth      [µm]   (into skin, 0 at surface, 40 at bottom)
    colour  → Water_Percent

Because the 10 scan positions are scattered (not on a regular grid), the
data is interpolated to a regular NX_GRID × NY_GRID spatial grid at each
depth level using scipy.interpolate.griddata:
  - Within the convex hull of the 10 scan positions: linear interpolation.
  - Outside the convex hull: nearest-neighbour extrapolation.
The result is a smooth, fully solid 3D block with no white gaps.

The 5 visible faces of the box are:
  - Top    (depth=0):          spatial water map at the skin surface
  - Front  (y=y_grid[0]):      depth cross-section at minimum y
  - Back   (y=y_grid[-1]):     depth cross-section at maximum y
  - Left   (x=x_grid[0]):      depth cross-section at minimum x
  - Right  (x=x_grid[-1]):     depth cross-section at maximum x

White dots on the top face mark the actual scan positions.

========================================================================
PIPELINE
========================================================================
Step 1  Load + filter (exclude==0, depth 0-40, depth cast to int)
Step 2  Group by (x_position, y_position, depth) -> mean Water_Percent
Step 3  For each depth level (0-40):
          griddata (linear) within convex hull +
          griddata (nearest) outside -> solid NX_GRID x NY_GRID slice
Step 4  Stack 41 slices -> volume (41, NY_GRID, NX_GRID)
        Clip to [VMIN, VMAX]
Step 5  3-D Gaussian blur (sigma_depth, sigma_y, sigma_x)
Step 6  Upsample depth axis: 41 -> ND_OUT pixels (bicubic zoom)
Step 7  Draw 5-face 3D box; mark scan positions on top face
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
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter, zoom as ndimage_zoom

def make_3d_heatmap(input_path, output_dir):
    # -- Colour scale -------------------------------------------------------
    VMIN = 8
    VMAX = 75

    # -- Custom colour map --------------------------------------------------
    CMAP_NODES  = [0.00, 0.18, 0.38, 0.58, 0.78, 1.00]
    CMAP_COLORS = ["#FFFF00", "#CC9900", "#4CAF50", "#40E0D0", "#1E90FF", "#00008B"]

    # -- Spatial grid resolution -------------------------------------------
    # The 10 scattered scan positions are interpolated onto a regular grid.
    NX_GRID = 40    # pixels in x_position direction
    NY_GRID = 40    # pixels in y_position direction

    # Padding around the convex hull of scan positions, as fraction of span.
    # Ensures the box has some border beyond the outermost scans.
    XY_PAD_FRAC = 0.15

    # -- Depth output resolution -------------------------------------------
    ND_OUT = 100    # depth pixels in final render (upsampled from 41)

    # -- Smoothing ----------------------------------------------------------
    # Applied to the 3D volume before face extraction.
    SIGMA_XY_FRAC = 0.08   # lateral blur = this fraction of NX_GRID / NY_GRID
    SIGMA_D_PX    = 2.0    # depth blur in raw depth pixels (1 px = 1 µm here)

    # -- 3D view angle ------------------------------------------------------
    ELEV = 28
    AZIM = -55

    # -- Warning thresholds -------------------------------------------------
    EXPECTED_SCANS_PER_PANEL = 10
    MIN_SCANS_WARN           = 4

    # -- Figure layout ------------------------------------------------------
    # ROWS = [("_A", "Code A"), ("_B", "Code B"), ("_C", "Code C"), ("_D", "Code D")]
    ROWS = [("_B", "Code B"), ("_C", "Code C"), ("_D", "Code D")]
    COLS = [("T01", "BL"), ("T02", "D01_1h"), ("T03", "D01_4h")]


    # ======================================================================
    # SECTION 2 -- COLOUR MAP
    # ======================================================================

    cmap = LinearSegmentedColormap.from_list(
        "water_cmap", list(zip(CMAP_NODES, CMAP_COLORS)), N=512
    )
    norm = mcolors.Normalize(vmin=VMIN, vmax=VMAX)


    # ======================================================================
    # SECTION 3 -- QUALITY LOGGER
    # ======================================================================

    class QualityLog:
        def __init__(self, out_dir):
            ts          = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.path   = os.path.join(out_dir, f"data_quality_log_3D_v7_{ts}.txt")
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
                "  DATA QUALITY LOG  --  3D Water Profile Heatmap Script  (v7)",
                f"  Generated : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"  Script    : {os.path.basename(__file__)}",
                f"  Input     : {input_path}",
                "  NOTE      : v7 uses actual (x_position, y_position) as the two",
                "              spatial axes.  Scattered scan data is interpolated",
                "              to a regular NX_GRID x NY_GRID grid via griddata.",
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

    df = df_raw[
        (df_raw["exclude"] == 0) &
        (df_raw["depth"].between(0, 40))
    ].copy()

    n_excl   = (df_raw["exclude"] == 1).sum()
    pct_excl = 100.0 * n_excl / len(df_raw)
    log.global_info(
        f"After exclude==0 + depth 0-40: {len(df):,} rows used "
        f"({n_excl:,} excluded, {pct_excl:.1f}%)"
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

    log.header("SCAN POSITIONS PER PANEL  (x, y in µm)")
    subjects = sorted(df["subjectID"].unique())
    for subj in subjects:
        log.note(f"\n  Subject {subj}:")
        for prod, plabel in ROWS:
            for tp, tlabel in COLS:
                s = df[
                    (df["subjectID"] == subj) &
                    (df["product"]   == prod) &
                    (df["timePoint"] == tp)
                ]
                if len(s) == 0:
                    log.warn(subj, prod, tp, "No data.")
                    continue
                xy = s[["x_position", "y_position"]].drop_duplicates()
                n  = len(xy)
                x_span = xy["x_position"].max() - xy["x_position"].min()
                y_span = xy["y_position"].max() - xy["y_position"].min()
                if n < EXPECTED_SCANS_PER_PANEL:
                    log.warn(subj, prod, tp,
                            f"Only {n} scan(s) (expected {EXPECTED_SCANS_PER_PANEL}). "
                            f"x_span={x_span:.0f}um, y_span={y_span:.0f}um")
                else:
                    log.info(
                        f"  [{subj} {prod} {tp}]  {n} scans, "
                        f"x_span={x_span:.0f}um, y_span={y_span:.0f}um"
                    )

    log.header("RENDERING BEGINS")


    # ======================================================================
    # SECTION 5 -- PIPELINE FUNCTION
    # ======================================================================

    def build_volume(subj, product, timepoint, log, panel_warnings):
        """
        Interpolate scattered scan data onto a regular 3D grid.

        Each of the 10 (x, y) scan positions provides a depth profile
        (Water_Percent at depths 0-40).  For each depth level, the 10
        scattered values are interpolated to a NX_GRID x NY_GRID regular
        grid using scipy griddata.

        Returns
        -------
        vol_nd   : ndarray (ND_OUT, NY_GRID, NX_GRID)  -- upsampled volume
        x_grid   : 1-D array (NX_GRID,)  -- x_position values of grid columns
        y_grid   : 1-D array (NY_GRID,)  -- y_position values of grid rows
        scan_xy  : ndarray (n_scans, 2)  -- actual (x, y) scan positions
        n_scans  : int
        """

        # -- Step 1: Subset ------------------------------------------------
        sub = df[
            (df["subjectID"] == subj) &
            (df["product"]   == product) &
            (df["timePoint"] == timepoint)
        ]
        if len(sub) == 0:
            panel_warnings.append("No data -- flat mid-range fallback.")
            fallback = np.full((ND_OUT, NY_GRID, NX_GRID), (VMIN + VMAX) / 2.0)
            x_g = np.linspace(0, 1, NX_GRID)
            y_g = np.linspace(0, 1, NY_GRID)
            return fallback, x_g, y_g, np.zeros((0, 2)), 0

        # -- Step 2: Group by scan position and depth ----------------------
        grp = (
            sub.groupby(["x_position", "y_position", "depth"])["Water_Percent"]
            .mean()
            .reset_index()
        )

        scan_xy = grp[["x_position", "y_position"]].drop_duplicates().values
        n_scans = len(scan_xy)

        if n_scans < EXPECTED_SCANS_PER_PANEL:
            panel_warnings.append(
                f"Only {n_scans} scan(s) (expected {EXPECTED_SCANS_PER_PANEL})."
            )

        n_clip_lo = int((sub["Water_Percent"] < VMIN).sum())
        n_clip_hi = int((sub["Water_Percent"] > VMAX).sum())
        if n_clip_lo:
            panel_warnings.append(f"{n_clip_lo} values < VMIN={VMIN}% clipped.")
        if n_clip_hi:
            panel_warnings.append(f"{n_clip_hi} values > VMAX={VMAX}% clipped.")

        # -- Step 3: Build regular spatial grid with padding ---------------
        x_min, x_max = scan_xy[:, 0].min(), scan_xy[:, 0].max()
        y_min, y_max = scan_xy[:, 1].min(), scan_xy[:, 1].max()

        x_span = max(x_max - x_min, 1.0)
        y_span = max(y_max - y_min, 1.0)
        x_pad  = x_span * XY_PAD_FRAC
        y_pad  = y_span * XY_PAD_FRAC

        x_grid = np.linspace(x_min - x_pad, x_max + x_pad, NX_GRID)
        y_grid = np.linspace(y_min - y_pad, y_max + y_pad, NY_GRID)
        gx, gy = np.meshgrid(x_grid, y_grid)          # (NY_GRID, NX_GRID)
        grid_pts = np.column_stack([gx.ravel(), gy.ravel()])  # (NY_GRID*NX_GRID, 2)

        log.info(
            f"  [{subj} {product} {timepoint}]  {n_scans} scans, "
            f"grid x=[{x_grid[0]:.0f}…{x_grid[-1]:.0f}]um "
            f"y=[{y_grid[0]:.0f}…{y_grid[-1]:.0f}]um"
        )

        # -- Step 4: Interpolate each depth slice --------------------------
        vol = np.full((41, NY_GRID, NX_GRID), np.nan)

        for d in range(0, 41):
            d_data = grp[grp["depth"] == d]
            if len(d_data) == 0:
                continue

            pts  = d_data[["x_position", "y_position"]].values   # (n_pts, 2)
            vals = d_data["Water_Percent"].values                  # (n_pts,)

            if len(pts) < 3:
                # Not enough points for triangulation -- use nearest only
                z = griddata(pts, vals, grid_pts, method="nearest")
            else:
                # Linear within convex hull, nearest outside
                z_lin  = griddata(pts, vals, grid_pts, method="linear")
                z_near = griddata(pts, vals, grid_pts, method="nearest")
                z = np.where(np.isnan(z_lin), z_near, z_lin)

            vol[d] = z.reshape(NY_GRID, NX_GRID)

        # Fill any remaining NaN depth slices with overall mean
        n_nan_slices = int(np.isnan(vol).any(axis=(1, 2)).sum())
        if n_nan_slices:
            panel_warnings.append(
                f"{n_nan_slices} depth slice(s) had NaN after griddata; "
                f"filled with panel mean."
            )
            overall_mean = float(np.nanmean(vol)) if not np.all(np.isnan(vol)) else VMIN
            vol = np.where(np.isnan(vol), overall_mean, vol)

        vol = np.clip(vol, VMIN, VMAX)

        # -- Step 5: 3-D Gaussian blur -------------------------------------
        sigma_x = SIGMA_XY_FRAC * NX_GRID
        sigma_y = SIGMA_XY_FRAC * NY_GRID
        sigma_d = SIGMA_D_PX

        vol = np.clip(
            gaussian_filter(vol, sigma=[sigma_d, sigma_y, sigma_x]),
            VMIN, VMAX
        )

        # -- Step 6: Upsample depth axis to ND_OUT -------------------------
        zoom_d = ND_OUT / 41.0
        vol_nd = np.clip(
            ndimage_zoom(vol, (zoom_d, 1.0, 1.0), order=3),
            VMIN, VMAX
        )

        return vol_nd, x_grid, y_grid, scan_xy, n_scans


    # ======================================================================
    # SECTION 6 -- DRAW ONE 3D BOX
    # ======================================================================

    def draw_box(ax, vol, x_grid, y_grid, scan_xy, n_scans):
        """
        Draw a 5-face 3D box coloured by Water_Percent.

        Axes are in real µm units:
        x = x_position, y = y_position, z = depth (0 at top, 40 at bottom)
        """
        nd, ny, nx = vol.shape
        D1d = np.linspace(0, 40, nd)
        surface_kwargs  = dict(shade=False, linewidth=0, antialiased=False)

        def rgba(data_2d):
            return cmap(norm(np.clip(data_2d, VMIN, VMAX)))

        # Meshgrids for each face
        Gx, Gy   = np.meshgrid(x_grid, y_grid)         # (ny, nx)
        Gx_d, Gd = np.meshgrid(x_grid, D1d)            # (nd, nx)
        Gy_d, Gd2= np.meshgrid(y_grid, D1d)            # (nd, ny)

        # Top face: depth=0, full xy extent
        top_data = vol[0]                                           # (ny, nx)
        ax.plot_surface(Gx, Gy, np.zeros_like(Gx),
                        facecolors=rgba(top_data), **surface_kwargs)

        # Front face: y=y_grid[0], all x, all depth
        front_data = vol[:, 0, :]                                   # (nd, nx)
        ax.plot_surface(Gx_d, np.full_like(Gx_d, y_grid[0]), Gd,
                        facecolors=rgba(front_data), **surface_kwargs)

        # Back face: y=y_grid[-1]
        back_data = vol[:, -1, :]                                   # (nd, nx)
        ax.plot_surface(Gx_d, np.full_like(Gx_d, y_grid[-1]), Gd,
                        facecolors=rgba(back_data), **surface_kwargs)

        # Left face: x=x_grid[0], all y, all depth
        left_data = vol[:, :, 0]                                    # (nd, ny)
        ax.plot_surface(np.full_like(Gy_d, x_grid[0]), Gy_d, Gd2,
                        facecolors=rgba(left_data), **surface_kwargs)

        # Right face: x=x_grid[-1]
        right_data = vol[:, :, -1]                                  # (nd, ny)
        ax.plot_surface(np.full_like(Gy_d, x_grid[-1]), Gy_d, Gd2,
                        facecolors=rgba(right_data), **surface_kwargs)

        # Scan position markers on top face
        for idx, (xp, yp) in enumerate(scan_xy, start=1):
            ax.scatter(xp, yp, 0, s=25, c="white",
                    edgecolors="#2255aa", linewidths=0.8,
                    zorder=10, depthshade=False)
            ax.text(xp, yp, -1.5, str(idx),
                    ha="center", va="center", fontsize=4,
                    color="#2255aa", fontweight="bold", zorder=11)

        # Axis formatting
        ax.set_xlim(x_grid[0], x_grid[-1])
        ax.set_ylim(y_grid[0], y_grid[-1])
        ax.set_zlim(40, 0)
        ax.set_zticks(np.arange(0, 41, 10))
        ax.set_zticklabels([str(v) for v in np.arange(0, 41, 10)], fontsize=5)
        ax.set_zlabel("depth [µm]", fontsize=6, labelpad=2)
        ax.set_xlabel("x [µm]", fontsize=5, labelpad=1)
        ax.set_ylabel("y [µm]", fontsize=5, labelpad=1)
        ax.tick_params(axis="x", labelsize=4)
        ax.tick_params(axis="y", labelsize=4)

        for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
            pane.fill = False
            pane.set_edgecolor("#cccccc")

        ax.view_init(elev=ELEV, azim=AZIM)

        if n_scans < MIN_SCANS_WARN:
            ax.text2D(
                0.50, 0.12,
                f"sparse data  (n={n_scans})",
                transform=ax.transAxes,
                fontsize=6, color="red", fontweight="bold",
                ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="red",
                        alpha=0.75, lw=0.8),
            )


    # ======================================================================
    # SECTION 7 -- GENERATE ONE FIGURE PER SUBJECT
    # ======================================================================

    n_rows = len(ROWS)
    n_cols = len(COLS)
    all_panel_warnings = []

    for subj in subjects:
        log.note(f"\n  ----- Subject {subj} -----")

        fig = plt.figure(figsize=(16, 5 * n_rows))
        fig.patch.set_facecolor("white")

        subj_warnings = 0

        for i, (prod_code, prod_label) in enumerate(ROWS):
            for j, (tp_code, tp_label) in enumerate(COLS):

                panel_idx      = i * n_cols + j + 1
                ax             = fig.add_subplot(n_rows, n_cols, panel_idx, projection="3d")
                panel_warnings = []

                vol, x_grid, y_grid, scan_xy, n_scans = build_volume(
                    subj, prod_code, tp_code, log, panel_warnings
                )
                draw_box(ax, vol, x_grid, y_grid, scan_xy, n_scans)

                for w_msg in panel_warnings:
                    log.warn(subj, prod_code, tp_code, w_msg)
                    subj_warnings += 1
                if panel_warnings:
                    all_panel_warnings.append((subj, prod_code, tp_code, panel_warnings))

                if i == 0:
                    ax.set_title(tp_label, fontsize=9, fontweight="bold", pad=3)
                if j == 0:
                    ax.text2D(-0.10, 0.5, prod_label,
                            transform=ax.transAxes,
                            fontsize=9, fontweight="bold",
                            va="center", ha="center", rotation=90)

                print(f"    {prod_label} {tp_label} done", flush=True)

        cbar_ax = fig.add_axes([0.93, 0.12, 0.016, 0.76])
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, cax=cbar_ax)
        cbar.ax.invert_yaxis()
        cbar.set_label("% Water", fontsize=10, labelpad=6)
        cbar.ax.tick_params(labelsize=8)

        fig.suptitle(
            f"3D Water Profile -- {subj}  "
            f"(axes: x/y = scan position [µm], z = depth [µm])",
            fontsize=12, fontweight="bold", y=0.99
        )

        plt.subplots_adjust(left=0.05, right=0.91, top=0.95, bottom=0.02,
                            wspace=0.05, hspace=0.05)

        out_path = os.path.join(output_dir, f"{subj}_3d.png")
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
        f"({panels_warned} had quality warnings)"
    )
    if all_panel_warnings:
        log.note("\n  Panels with warnings:")
        for subj, prod, tp, msgs in all_panel_warnings:
            log.note(f"    {subj} {prod} {tp}:")
            for m in msgs:
                log.note(f"      - {m}")

    log.header("v7 DESIGN NOTES")
    log.note("  x-axis = x_position [µm], y-axis = y_position [µm].")
    log.note("  Scattered scan data interpolated to NX_GRID x NY_GRID grid")
    log.note("  via scipy.interpolate.griddata (linear within convex hull,")
    log.note("  nearest-neighbour outside).  No white gaps.")
    log.note("  Dots on top face = actual scan (x, y) positions, numbered.")
    log.note(f"  Grid: {NX_GRID} x {NY_GRID}, depth: {ND_OUT} px, padding: {XY_PAD_FRAC*100:.0f}%")

    log.write()
    print("All subjects done.")


if __name__ == "__main__":
    
# ======================================================================
# SECTION 1 -- CONFIGURATION
# ======================================================================

    input_path = "data/raman_water_data.xlsx"
    output_dir = "output/"
    make_3d_heatmap(input_path, output_dir)