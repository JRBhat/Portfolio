"""
Algorithm Slide Generator
=========================
Produces PPT-style PNG slides explaining each step of the 2D (v9) and
3D (v7) Raman water-concentration heatmap pipelines.

Output folder: output_slides/
"""

import sys
import io
# Force UTF-8 output so special characters in print() don't crash on cp1252 terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter
from pathlib import Path
from config import VMIN, VMAX, CMAP_NODES, CMAP_COLORS
from palette import build_water_cmap

OUT_DIR = "output_slides/"
Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

# ── shared colour map (matches production scripts) ─────────────────────────
CMAP = build_water_cmap()

# ── slide style ────────────────────────────────────────────────────────────
SLIDE_W, SLIDE_H = 13.33, 7.5           # 16:9 inches
BG       = "#FFFFFF"
ACCENT   = "#1565C0"          # dark blue header band
ACCENT2  = "#0277BD"          # lighter accent
STEP_CLR = "#E3F2FD"          # very light blue for step boxes
TEXT_CLR = "#212121"
SUB_CLR  = "#455A64"

def save_slide(fig, name):
    path = Path(OUT_DIR) / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  saved -> {path}")

def base_fig(title, subtitle="", step_tag=""):
    """Create a slide canvas with header band and title."""
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), facecolor=BG)

    # Header band
    ax_hdr = fig.add_axes([0, 0.87, 1, 0.13])
    ax_hdr.set_facecolor(ACCENT)
    ax_hdr.axis("off")
    if step_tag:
        ax_hdr.text(0.015, 0.62, step_tag, color="#90CAF9", fontsize=12,
                    fontweight="bold", va="center", transform=ax_hdr.transAxes)
    ax_hdr.text(0.015, 0.28, title, color="white", fontsize=20,
                fontweight="bold", va="center", transform=ax_hdr.transAxes)
    if subtitle:
        ax_hdr.text(0.985, 0.28, subtitle, color="#B0BEC5", fontsize=11,
                    va="center", ha="right", transform=ax_hdr.transAxes,
                    style="italic")
    return fig


def bullet_box(ax, lines, x=0.02, y=0.90, dy=0.17, fontsize=11):
    """Draw bullet-point lines on an axes."""
    for i, line in enumerate(lines):
        ax.text(x, y - i * dy, line, transform=ax.transAxes,
                fontsize=fontsize, va="top", color=TEXT_CLR,
                wrap=True)

# ═══════════════════════════════════════════════════════════════════════════
#  SYNTHETIC DATA
# ═══════════════════════════════════════════════════════════════════════════

rng = np.random.default_rng(42)

N_SCANS = 8
DEPTHS  = np.arange(0, 41)   # 41 integer depths

# Simulated raw panel matrix: (41, 8)  with realistic gradients
raw_mat = np.zeros((41, N_SCANS))
for s in range(N_SCANS):
    base    = 30 + rng.uniform(-8, 8)
    surface = 55 + rng.uniform(-5, 5)
    raw_mat[:, s] = surface * np.exp(-DEPTHS / 15) + base * (1 - np.exp(-DEPTHS / 15))
    raw_mat[:, s] += rng.normal(0, 1.5, 41)

# Introduce one cluster of near-duplicate scans (scans 2 and 3)
raw_mat_dup = raw_mat.copy()
raw_mat_dup[:, 2] = raw_mat_dup[:, 1] + rng.normal(0, 0.5, 41)   # near-duplicate

# Introduce a few NaN cells
raw_mat_nan = raw_mat.copy()
raw_mat_nan[35:, 5] = np.nan
raw_mat_nan[38:, 7] = np.nan

x_positions = np.array([-380, -360, -358, -340, -310, -280, -250, -220], dtype=float)
# scans 1 and 2 are near-duplicates (20µm apart → below 10µm after merge example)

# After merge
x_merged = np.array([-380, -359, -340, -310, -280, -250, -220], dtype=float)
N_MERGED  = 7

# Simulated merged matrix
raw_mat_m = np.zeros((41, N_MERGED))
for s in range(N_MERGED):
    base    = 30 + rng.uniform(-8, 8)
    surface = 55 + rng.uniform(-5, 5)
    raw_mat_m[:, s] = surface * np.exp(-DEPTHS / 15) + base * (1 - np.exp(-DEPTHS / 15))
    raw_mat_m[:, s] += rng.normal(0, 1.5, 41)


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 0 – 2D Overview
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_overview():
    fig = base_fig("2D Heatmap Pipeline  (v9) — Overview",
                   "Raman Water Concentration", "ALGORITHM  |  2D")

    ax = fig.add_axes([0.02, 0.04, 0.96, 0.82])
    ax.set_facecolor(BG)
    ax.axis("off")

    steps = [
        ("1", "Load & Filter",        "Remove excluded rows\nDepth 0 – 40 µm"),
        ("2", "Merge Duplicates",      "Average scans < 10 µm apart"),
        ("3", "Pivot Matrix",          "Build (41 depth × n scans)\nraw data matrix"),
        ("4", "Fill NaN",              "Linear interpolation on\nscan-index axis"),
        ("5", "PCHIP Lateral",         "Pass A: upsample each depth row\n(scan index → fine grid)"),
        ("6", "PCHIP Depth",           "Pass B: upsample each column\n(41 raw → 161 fine rows)"),
        ("7", "Gaussian Blur",         "Smooth σ lateral & σ depth"),
        ("8", "Render Heatmap",        "x = Scan #, y = depth [µm]\nColour = % water"),
    ]

    n = len(steps)
    box_w = 0.105
    box_h = 0.55
    gap   = 0.015
    total = n * box_w + (n - 1) * gap
    x0    = (1 - total) / 2

    for k, (num, title, desc) in enumerate(steps):
        x = x0 + k * (box_w + gap)
        y = 0.18

        # Box
        fancy = mpatches.FancyBboxPatch(
            (x, y), box_w, box_h,
            boxstyle="round,pad=0.01",
            linewidth=1.5, edgecolor=ACCENT2,
            facecolor=STEP_CLR, transform=ax.transAxes, clip_on=False
        )
        ax.add_patch(fancy)

        # Step number badge
        circ = plt.Circle((x + box_w / 2, y + box_h + 0.04), 0.03,
                           color=ACCENT, transform=ax.transAxes, clip_on=False)
        ax.add_patch(circ)
        ax.text(x + box_w / 2, y + box_h + 0.04, num,
                transform=ax.transAxes, fontsize=10, color="white",
                ha="center", va="center", fontweight="bold")

        ax.text(x + box_w / 2, y + box_h - 0.04, title,
                transform=ax.transAxes, fontsize=8.5, color=ACCENT,
                ha="center", va="top", fontweight="bold")
        ax.text(x + box_w / 2, y + box_h - 0.14, desc,
                transform=ax.transAxes, fontsize=7.5, color=SUB_CLR,
                ha="center", va="top", multialignment="center")

        # Arrow
        if k < n - 1:
            ax.annotate("", xy=(x + box_w + gap, y + box_h / 2 + 0.18),
                        xytext=(x + box_w, y + box_h / 2 + 0.18),
                        xycoords="axes fraction", textcoords="axes fraction",
                        arrowprops=dict(arrowstyle="->", color=ACCENT2, lw=1.5))

    ax.text(0.5, 0.07,
            "Output: one PNG per subject  ·  3 products (B, C, D)  ×  3 time-points (BL, 1 h, 4 h)  ·  colour scale 8–75 % water",
            transform=ax.transAxes, fontsize=9, ha="center", color=SUB_CLR)

    save_slide(fig, "2D_00_overview.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2D-1 – Load & Filter
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_step1():
    fig = base_fig("Step 1 — Load & Filter",
                   "2D Pipeline  (v9)", "STEP 1 / 8")

    # Left: description panel
    ax_txt = fig.add_axes([0.02, 0.06, 0.40, 0.78])
    ax_txt.set_facecolor(STEP_CLR)
    ax_txt.axis("off")
    for spine in ax_txt.spines.values():
        spine.set_visible(False)

    lines = [
        "Input",
        "  Excel file: one sheet, ~80 000 rows",
        "",
        "Filters applied",
        "  ✔  exclude == 0   (analyst-approved rows only)",
        "  ✔  depth 0 – 40 µm  (stratum corneum)",
        "  ✔  depth rounded to integer",
        "",
        "Key columns kept",
        "  subjectID  ·  product  ·  timePoint",
        "  x_position  ·  depth  ·  Water_Percent",
        "",
        "Result",
        "  Clean DataFrame used by all downstream steps",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") and not ln.startswith("✔") else "normal"
        color  = ACCENT if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.95 - i * 0.065, ln,
                    transform=ax_txt.transAxes, fontsize=9.5,
                    va="top", color=color, fontweight=weight)

    # Right: schematic table before/after
    ax_r = fig.add_axes([0.46, 0.06, 0.52, 0.78])
    ax_r.axis("off")

    # Before table header
    ax_r.text(0.15, 0.97, "Raw Excel  (sample rows)", fontsize=10,
              fontweight="bold", color=ACCENT, transform=ax_r.transAxes, va="top")

    headers = ["subjectID", "exclude", "depth", "Water_%"]
    col_x   = [0.00, 0.28, 0.50, 0.70]
    rows_data = [
        ["S001", "0", "5.2", "48.3"],
        ["S001", "1", "6.0", "44.1"],    # excluded
        ["S001", "0", "45.0", "20.1"],   # depth > 40
        ["S001", "0", "10.0", "42.7"],
        ["S001", "0", "15.0", "38.2"],
    ]
    excl_rows = {1, 2}

    row_y = 0.87
    for hi, hdr in enumerate(headers):
        ax_r.text(col_x[hi], row_y, hdr, transform=ax_r.transAxes,
                  fontsize=8.5, fontweight="bold", color=ACCENT, va="top")
    row_y -= 0.07

    for ri, rd in enumerate(rows_data):
        clr = "#FFCDD2" if ri in excl_rows else "#E8F5E9"
        rect = mpatches.FancyBboxPatch(
            (-0.01, row_y - 0.045), 0.96, 0.06,
            boxstyle="square,pad=0.005", linewidth=0,
            facecolor=clr, transform=ax_r.transAxes, clip_on=False
        )
        ax_r.add_patch(rect)
        for ci, val in enumerate(rd):
            ax_r.text(col_x[ci], row_y, val, transform=ax_r.transAxes,
                      fontsize=8.5, va="top",
                      color=("#B71C1C" if ri in excl_rows else TEXT_CLR))
        if ri == 1:
            ax_r.text(0.88, row_y, "✗ excluded", transform=ax_r.transAxes,
                      fontsize=7.5, color="#B71C1C", va="top")
        if ri == 2:
            ax_r.text(0.88, row_y, "✗ depth>40", transform=ax_r.transAxes,
                      fontsize=7.5, color="#B71C1C", va="top")
        row_y -= 0.07

    ax_r.annotate("", xy=(0.45, 0.38), xytext=(0.45, 0.28),
                  xycoords="axes fraction", textcoords="axes fraction",
                  arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=2))
    ax_r.text(0.45, 0.24, "After filtering", transform=ax_r.transAxes,
              fontsize=9, ha="center", color=ACCENT, fontweight="bold")
    ax_r.text(0.45, 0.16, "Only rows with  exclude = 0\nand  depth ∈ [0, 40]  are kept",
              transform=ax_r.transAxes, fontsize=9, ha="center", color=TEXT_CLR)

    save_slide(fig, "2D_01_load_filter.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2D-2 – Merge Near-Duplicate Scans
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_step2():
    fig = base_fig("Step 2 — Merge Near-Duplicate Scan Positions",
                   "2D Pipeline  (v9)", "STEP 2 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor(STEP_CLR)
    ax_txt.axis("off")

    lines = [
        "Problem",
        "  Some panels have scans taken at almost",
        "  the same skin spot (as little as 1 µm apart).",
        "  In a uniform scan-index matrix these form",
        "  sharp data spikes → spline oscillation.",
        "",
        "Fix — Scan Merge  (threshold = 10 µm)",
        "  Sort scan positions by x_position.",
        "  Any adjacent pair closer than 10 µm",
        "  → averaged into one representative scan.",
        "",
        "Effect",
        "  Reduces n from 10 to as few as 7 scans",
        "  Eliminates the data spike at the source",
        "  Logged for transparency",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = ACCENT if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.062, ln,
                    transform=ax_txt.transAxes, fontsize=9.2,
                    va="top", color=color, fontweight=weight)

    # Right: before/after scan position visualisation
    ax_r = fig.add_axes([0.44, 0.12, 0.54, 0.70])
    ax_r.set_facecolor(BG)

    x_before = np.array([-380, -360, -357, -340, -310, -280, -250, -220])
    x_after  = np.array([-380, -358.5, -340, -310, -280, -250, -220])

    y_before = np.zeros_like(x_before)
    y_after  = np.zeros_like(x_after)

    ax_r.scatter(x_before, y_before + 1, s=80, c="#1565C0", zorder=5, label="Original scans")
    ax_r.scatter(x_after, y_after, s=100, c="#E53935", marker="D", zorder=5,
                 label="After merge")

    # Highlight the merged pair
    ax_r.annotate("", xy=(-358.5, 0.15), xytext=(-380, 0.85),
                  arrowprops=dict(arrowstyle="-", color="#E53935", lw=1, linestyle="dashed"))
    ax_r.annotate("", xy=(-358.5, 0.15), xytext=(-360, 0.85),
                  arrowprops=dict(arrowstyle="-", color="#E53935", lw=1, linestyle="dashed"))
    ax_r.annotate("", xy=(-358.5, 0.15), xytext=(-357, 0.85),
                  arrowprops=dict(arrowstyle="-", color="#E53935", lw=1, linestyle="dashed"))

    ax_r.text(-369, 1.12, "3 scans within\n10 µm window", fontsize=8,
              ha="center", color="#1565C0")
    ax_r.text(-358.5, -0.22, "averaged\ninto one", fontsize=8,
              ha="center", color="#E53935")

    for xi, x in enumerate(x_before):
        ax_r.text(x, 1.22, f"S{xi+1}", fontsize=7.5, ha="center", color="#1565C0")
    for xi, x in enumerate(x_after):
        ax_r.text(x, -0.42, f"S{xi+1}", fontsize=7.5, ha="center", color="#E53935")

    ax_r.text(-300, 1.22, "BEFORE  (8 raw scans)", fontsize=9,
              color="#1565C0", fontweight="bold")
    ax_r.text(-300, -0.42, "AFTER  (7 merged scans)", fontsize=9,
              color="#E53935", fontweight="bold")

    ax_r.set_xlim(-400, -200)
    ax_r.set_ylim(-0.7, 1.6)
    ax_r.set_xlabel("x_position  [µm]", fontsize=9)
    ax_r.set_yticks([])
    ax_r.spines["top"].set_visible(False)
    ax_r.spines["right"].set_visible(False)
    ax_r.spines["left"].set_visible(False)
    ax_r.set_title("Scan position consolidation", fontsize=10,
                   fontweight="bold", color=ACCENT)

    save_slide(fig, "2D_02_merge_duplicates.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2D-3 – Pivot Matrix
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_step3():
    fig = base_fig("Step 3 — Pivot: Build Raw Data Matrix",
                   "2D Pipeline  (v9)", "STEP 3 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor(STEP_CLR)
    ax_txt.axis("off")

    lines = [
        "Goal",
        "  Convert the long-format DataFrame into",
        "  a 2D matrix ready for interpolation.",
        "",
        "How",
        "  Group by (scan_group, depth)",
        "  → average Water_Percent",
        "  Pivot: rows = depth (0–40), cols = scans",
        "  Sort columns left → right by x_position",
        "",
        "Result",
        "  Shape: (41 depths  ×  n scans)",
        "  Each cell = measured % water",
        "  Some cells may be NaN if a scan",
        "  didn't reach all depths",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = ACCENT if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.062, ln,
                    transform=ax_txt.transAxes, fontsize=9.2,
                    va="top", color=color, fontweight=weight)

    # Right: show the pivot matrix as a heatmap
    ax_r = fig.add_axes([0.44, 0.10, 0.50, 0.74])
    show = raw_mat_m.copy()
    # Add some NaN to illustrate
    show[36:, 5] = np.nan
    im = ax_r.imshow(show, aspect="auto", cmap=CMAP, vmin=VMIN, vmax=VMAX,
                     origin="upper", interpolation="none")
    ax_r.set_xlabel("Scan index (sorted by x_position)", fontsize=9)
    ax_r.set_ylabel("Depth [µm]", fontsize=9)
    ax_r.set_xticks(range(N_MERGED))
    ax_r.set_xticklabels([f"S{i+1}" for i in range(N_MERGED)], fontsize=8)
    ytk = list(range(0, 41, 10))
    ax_r.set_yticks(ytk)
    ax_r.set_yticklabels([str(v) for v in ytk], fontsize=8)
    ax_r.set_title("Raw pivot matrix  (41 × 7 example)", fontsize=10,
                   fontweight="bold", color=ACCENT)

    # Highlight NaN region
    ax_r.text(5, 38, "NaN\n(scan didn't\nreach 40 µm)", fontsize=7.5,
              ha="center", va="center", color="#B71C1C",
              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#B71C1C", alpha=0.85))

    cb = plt.colorbar(im, ax=ax_r, fraction=0.04, pad=0.03)
    cb.set_label("% Water", fontsize=8)
    cb.ax.invert_yaxis()

    save_slide(fig, "2D_03_pivot_matrix.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2D-4 – Fill NaN
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_step4():
    fig = base_fig("Step 4 — Fill Missing Values  (NaN)",
                   "2D Pipeline  (v9)", "STEP 4 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor(STEP_CLR)
    ax_txt.axis("off")

    lines = [
        "Why NaN occurs",
        "  Some scans don't cover every depth.",
        "  The pivot step leaves empty cells.",
        "",
        "Primary fill",
        "  For each depth row, linearly interpolate",
        "  across scan indices using valid neighbours.",
        "  Boundary values are held constant.",
        "",
        "Safety fill",
        "  Any remaining NaN (e.g., an entire row",
        "  is missing) → replaced with panel mean.",
        "",
        "Result",
        "  No NaN in the matrix after this step.",
        "  PCHIP in Step 5 requires complete data.",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = ACCENT if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.062, ln,
                    transform=ax_txt.transAxes, fontsize=9.2,
                    va="top", color=color, fontweight=weight)

    # Right: before / after NaN fill
    mat_before = raw_mat_m.copy()
    mat_before[36:, 5] = np.nan

    mat_after = mat_before.copy()
    for row in range(mat_after.shape[0]):
        valid = ~np.isnan(mat_after[row])
        if valid.sum() >= 2:
            from scipy.interpolate import interp1d
            xi = np.arange(N_MERGED, dtype=float)
            f  = interp1d(xi[valid], mat_after[row, valid], kind="linear",
                          bounds_error=False,
                          fill_value=(mat_after[row, valid][0], mat_after[row, valid][-1]))
            mat_after[row] = f(xi)
    mat_after = np.where(np.isnan(mat_after), np.nanmean(mat_after), mat_after)

    ax_l = fig.add_axes([0.44, 0.10, 0.25, 0.74])
    im = ax_l.imshow(mat_before, aspect="auto", cmap=CMAP, vmin=VMIN, vmax=VMAX,
                     origin="upper", interpolation="none")
    ax_l.set_title("Before fill", fontsize=9, fontweight="bold", color=ACCENT)
    ax_l.set_xlabel("Scan #", fontsize=8)
    ax_l.set_ylabel("Depth [µm]", fontsize=8)
    ax_l.set_xticks(range(N_MERGED))
    ax_l.set_xticklabels([str(i+1) for i in range(N_MERGED)], fontsize=7)
    ytk = list(range(0, 41, 10))
    ax_l.set_yticks(ytk)
    ax_l.set_yticklabels([str(v) for v in ytk], fontsize=7)

    ax_rr = fig.add_axes([0.73, 0.10, 0.25, 0.74])
    ax_rr.imshow(mat_after, aspect="auto", cmap=CMAP, vmin=VMIN, vmax=VMAX,
                 origin="upper", interpolation="none")
    ax_rr.set_title("After fill", fontsize=9, fontweight="bold", color="#2E7D32")
    ax_rr.set_xlabel("Scan #", fontsize=8)
    ax_rr.set_yticks(ytk)
    ax_rr.set_yticklabels([str(v) for v in ytk], fontsize=7)
    ax_rr.set_xticks(range(N_MERGED))
    ax_rr.set_xticklabels([str(i+1) for i in range(N_MERGED)], fontsize=7)

    # Arrow between the two
    fig.text(0.695, 0.50, "→", fontsize=28, color=ACCENT, ha="center", va="center")

    save_slide(fig, "2D_04_fill_nan.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2D-5 – PCHIP Lateral
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_step5():
    fig = base_fig("Step 5 — PCHIP Interpolation  Pass A: Lateral",
                   "2D Pipeline  (v9)", "STEP 5 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor(STEP_CLR)
    ax_txt.axis("off")

    lines = [
        "Goal",
        "  Upsample each depth row from n_scans",
        "  knots → n_scans × 20  fine columns.",
        "",
        "Method — PCHIP",
        "  Piecewise Cubic Hermite Interpolating",
        "  Polynomial.  Key property:",
        "  output is always bounded by the",
        "  data values at the knots.",
        "  → No oscillation, no impossible",
        "  negative-% or 800%-% artefacts.",
        "",
        "Why not a spline?",
        "  v8 used RectBivariateSpline → produced",
        "  extreme oscillations (−763 % to +836 %)",
        "  on panels with clustered scans.",
        "  PCHIP eliminates this by design.",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = ACCENT if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.062, ln,
                    transform=ax_txt.transAxes, fontsize=9.0,
                    va="top", color=color, fontweight=weight)

    # Right: 1D PCHIP vs spline comparison for a single row
    ax_r = fig.add_axes([0.44, 0.12, 0.53, 0.72])

    x_knots = np.arange(N_MERGED, dtype=float)
    row_data = raw_mat_m[10, :]          # pick depth = 10 µm
    x_fine   = np.linspace(0, N_MERGED - 1, N_MERGED * 20)

    pchip_fn = PchipInterpolator(x_knots, row_data)
    y_pchip  = pchip_fn(x_fine)

    # Simulate spline oscillation (artificial)
    row_data_spike = row_data.copy()
    row_data_spike[1] += 25   # simulate the near-duplicate spike effect
    from scipy.interpolate import CubicSpline
    cs = CubicSpline(x_knots, row_data_spike)
    y_spline = cs(x_fine)

    ax_r.plot(x_fine, y_spline, color="#B71C1C", lw=1.5, linestyle="--",
              label="Cubic spline (with spike data) — oscillation!")
    ax_r.plot(x_fine, y_pchip, color="#1565C0", lw=2,
              label="PCHIP — bounded, no oscillation")
    ax_r.scatter(x_knots, row_data, color="#1565C0", s=55, zorder=5,
                 label="Data knots")

    ax_r.axhline(VMIN, color="#888", ls=":", lw=1, label=f"VMIN={VMIN}%")
    ax_r.axhline(VMAX, color="#888", ls=":", lw=1, label=f"VMAX={VMAX}%")
    ax_r.fill_between(x_fine, VMIN, VMAX, alpha=0.07, color="green",
                      label="Valid range")

    ax_r.set_xlabel("Scan index (fine)", fontsize=9)
    ax_r.set_ylabel("Water_Percent  [%]", fontsize=9)
    ax_r.set_title("Single depth row  (depth = 10 µm)", fontsize=10,
                   fontweight="bold", color=ACCENT)
    ax_r.legend(fontsize=7.5, loc="upper right")
    ax_r.grid(True, alpha=0.3)

    save_slide(fig, "2D_05_pchip_lateral.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2D-6 – PCHIP Depth
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_step6():
    fig = base_fig("Step 6 — PCHIP Interpolation  Pass B: Depth",
                   "2D Pipeline  (v9)", "STEP 6 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor(STEP_CLR)
    ax_txt.axis("off")

    lines = [
        "Goal",
        "  Upsample depth axis from 41 integer",
        "  steps → 161 fine rows  (0.25 µm each).",
        "",
        "Method — PCHIP  (same as Pass A)",
        "  For each fine column produced in Pass A,",
        "  apply PCHIP along the depth axis.",
        "",
        "Two-pass result",
        "  Matrix shape after both passes:",
        "  161 rows  ×  (n_scans × 20) columns",
        "",
        "Both passes are independent",
        "  Decouples lateral and depth interpolation.",
        "  More numerically stable than a single",
        "  bivariate interpolation.",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = ACCENT if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.062, ln,
                    transform=ax_txt.transAxes, fontsize=9.2,
                    va="top", color=color, fontweight=weight)

    # Right: before / after on depth axis
    ax_l = fig.add_axes([0.44, 0.10, 0.22, 0.74])
    ax_rr = fig.add_axes([0.73, 0.10, 0.25, 0.74])

    # Before: 41-row matrix (lateral already fine from pass A, show compressed)
    col = 0
    mat_A_col = raw_mat_m[:, col]   # single column, 41 depths (proxy for pass A result)
    d_raw  = np.arange(0, 41)
    d_fine = np.linspace(0, 40, 161)
    pchip_d = PchipInterpolator(d_raw, mat_A_col)
    mat_A_fine_col = pchip_d(d_fine)

    ax_l.barh(d_raw, mat_A_col, color=CMAP((mat_A_col - VMIN)/(VMAX - VMIN)),
              height=0.85, left=0)
    ax_l.set_ylim(40.5, -0.5)
    ax_l.set_xlabel("Water %", fontsize=8)
    ax_l.set_ylabel("Depth [µm]", fontsize=8)
    ax_l.set_title("Before Pass B\n(41 depth steps)", fontsize=9,
                   fontweight="bold", color=ACCENT)
    ax_l.tick_params(labelsize=7)

    ax_rr.barh(d_fine, mat_A_fine_col,
               color=CMAP((np.clip(mat_A_fine_col, VMIN, VMAX) - VMIN)/(VMAX - VMIN)),
               height=0.4, left=0)
    ax_rr.set_ylim(40.5, -0.5)
    ax_rr.set_xlabel("Water %", fontsize=8)
    ax_rr.set_title("After Pass B\n(161 depth steps)", fontsize=9,
                    fontweight="bold", color="#2E7D32")
    ax_rr.tick_params(labelsize=7)

    fig.text(0.695, 0.50, "→", fontsize=28, color=ACCENT, ha="center", va="center")

    save_slide(fig, "2D_06_pchip_depth.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2D-7 – Gaussian Blur
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_step7():
    fig = base_fig("Step 7 — Gaussian Smoothing",
                   "2D Pipeline  (v9)", "STEP 7 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor(STEP_CLR)
    ax_txt.axis("off")

    lines = [
        "Purpose",
        "  Remove residual pixel-level noise and",
        "  create visually smooth transitions.",
        "",
        "Parameters",
        "  σ lateral = 0.4 × 20 px = 8 px",
        "    (40 % of one scan-profile width)",
        "  σ depth = 1.0 µm / 0.25 µm·px⁻¹ = 4 px",
        "",
        "Implementation",
        "  scipy.ndimage.gaussian_filter",
        "  Applied to the full fine matrix.",
        "  Output clipped back to [8, 75 %].",
        "",
        "Effect",
        "  Reduces inter-scan boundary sharpness.",
        "  Does not shift colours—only blurs.",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = ACCENT if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.062, ln,
                    transform=ax_txt.transAxes, fontsize=9.2,
                    va="top", color=color, fontweight=weight)

    # Build synthetic fine matrix
    x_fine = np.linspace(0, N_MERGED - 1, N_MERGED * 20)
    mat_fine = np.empty((41, N_MERGED * 20))
    for d in range(41):
        pchip = PchipInterpolator(np.arange(N_MERGED, dtype=float), raw_mat_m[d, :])
        mat_fine[d, :] = pchip(x_fine)
    mat_fine = np.clip(mat_fine, VMIN, VMAX)
    mat_blurred = np.clip(gaussian_filter(mat_fine, sigma=[4, 8]), VMIN, VMAX)

    ax_l = fig.add_axes([0.44, 0.10, 0.25, 0.74])
    ax_l.imshow(mat_fine, aspect="auto", cmap=CMAP, vmin=VMIN, vmax=VMAX,
                origin="upper", interpolation="bilinear")
    ax_l.set_title("Before blur", fontsize=9, fontweight="bold", color=ACCENT)
    ax_l.set_xlabel("Fine column index", fontsize=8)
    ax_l.set_ylabel("Depth [µm]", fontsize=8)
    ytk = list(range(0, 41, 10))
    ax_l.set_yticks(ytk)
    ax_l.set_yticklabels([str(v) for v in ytk], fontsize=7)
    ax_l.tick_params(axis="x", labelsize=7)

    ax_r = fig.add_axes([0.73, 0.10, 0.25, 0.74])
    ax_r.imshow(mat_blurred, aspect="auto", cmap=CMAP, vmin=VMIN, vmax=VMAX,
                origin="upper", interpolation="bilinear")
    ax_r.set_title("After blur", fontsize=9, fontweight="bold", color="#2E7D32")
    ax_r.set_xlabel("Fine column index", fontsize=8)
    ax_r.set_yticks(ytk)
    ax_r.set_yticklabels([str(v) for v in ytk], fontsize=7)
    ax_r.tick_params(axis="x", labelsize=7)

    fig.text(0.695, 0.50, "→", fontsize=28, color=ACCENT, ha="center", va="center")

    save_slide(fig, "2D_07_gaussian_blur.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2D-8 – Final Render
# ═══════════════════════════════════════════════════════════════════════════

def slide_2d_step8():
    fig = base_fig("Step 8 — Render Final 2D Heatmap",
                   "2D Pipeline  (v9)", "STEP 8 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.30, 0.78])
    ax_txt.set_facecolor(STEP_CLR)
    ax_txt.axis("off")

    lines = [
        "Layout",
        "  3 rows (products B, C, D)",
        "  3 columns (BL, 1h, 4h)",
        "  → 9 panels per subject",
        "",
        "Axes",
        "  x = Scan number (1 … n)",
        "    sorted left→right by x_position",
        "  y = Depth into skin (0–40 µm)",
        "    0 = surface, 40 = deep SC",
        "",
        "Colour scale",
        "  Yellow → dry  (8 %)",
        "  Dark navy → wet  (75 %)",
        "  Inverted colourbar for intuition",
        "",
        "Output",
        "  300 dpi PNG, one per subject",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = ACCENT if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.058, ln,
                    transform=ax_txt.transAxes, fontsize=9.0,
                    va="top", color=color, fontweight=weight)

    # Build the final display matrix
    x_fine = np.linspace(0, N_MERGED - 1, N_MERGED * 20)
    mat_fine = np.empty((41, N_MERGED * 20))
    for d in range(41):
        pchip = PchipInterpolator(np.arange(N_MERGED, dtype=float), raw_mat_m[d, :])
        mat_fine[d, :] = pchip(x_fine)
    mat_fine = np.clip(mat_fine, VMIN, VMAX)
    mat_blurred = np.clip(gaussian_filter(mat_fine, sigma=[4, 8]), VMIN, VMAX)

    ax_r = fig.add_axes([0.36, 0.10, 0.54, 0.78])
    im = ax_r.imshow(mat_blurred, origin="upper",
                     extent=[0, 1, 40, 0],
                     aspect="auto", cmap=CMAP, vmin=VMIN, vmax=VMAX,
                     interpolation="bilinear")
    tick_pos = [(k + 0.5) / N_MERGED for k in range(N_MERGED)]
    ax_r.set_xticks(tick_pos)
    ax_r.set_xticklabels([str(k+1) for k in range(N_MERGED)], fontsize=9)
    ax_r.set_xlabel("Scan #", fontsize=10)
    ax_r.set_ylabel("Depth [µm]", fontsize=10)
    ytk = list(range(0, 41, 5))
    ax_r.set_yticks(ytk)
    ax_r.set_yticklabels([str(v) for v in ytk], fontsize=8)
    ax_r.set_title("Example panel  (subject / product / time-point)",
                   fontsize=10, fontweight="bold", color=ACCENT)

    cb = plt.colorbar(im, ax=ax_r, fraction=0.035, pad=0.03)
    cb.ax.invert_yaxis()
    cb.set_label("% Water", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    save_slide(fig, "2D_08_render.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 0 – 3D Overview
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_overview():
    fig = base_fig("3D Heatmap Pipeline  (v7) — Overview",
                   "Raman Water Concentration", "ALGORITHM  |  3D")

    ax = fig.add_axes([0.02, 0.04, 0.96, 0.82])
    ax.set_facecolor(BG)
    ax.axis("off")

    steps = [
        ("1", "Load & Filter",         "Same as 2D:\nexclude==0, depth 0–40"),
        ("2", "Group by\n(x,y, depth)", "Average Water_Percent\nat each scan+depth"),
        ("3", "Build Spatial\nGrid",    "Regular 40×40 µm grid\nwith 15% padding"),
        ("4", "griddata\nInterp.",      "Linear inside hull\n+ nearest outside"),
        ("5", "Stack Slices\n→ Volume", "41 depth slices →\n3D array"),
        ("6", "3D Gaussian\nBlur",      "Smooth volume\nσ_xy and σ_depth"),
        ("7", "Upsample\nDepth",        "41 → 100 px\nbicubic zoom"),
        ("8", "Draw 5-Face\n3D Box",    "x/y = real µm\nz = depth"),
    ]

    n = len(steps)
    box_w = 0.105
    box_h = 0.58
    gap   = 0.015
    total = n * box_w + (n - 1) * gap
    x0    = (1 - total) / 2

    for k, (num, title, desc) in enumerate(steps):
        x = x0 + k * (box_w + gap)
        y = 0.15

        fancy = mpatches.FancyBboxPatch(
            (x, y), box_w, box_h,
            boxstyle="round,pad=0.01",
            linewidth=1.5, edgecolor="#00838F",
            facecolor="#E0F7FA", transform=ax.transAxes, clip_on=False
        )
        ax.add_patch(fancy)

        circ = plt.Circle((x + box_w / 2, y + box_h + 0.04), 0.03,
                          color="#00838F", transform=ax.transAxes, clip_on=False)
        ax.add_patch(circ)
        ax.text(x + box_w / 2, y + box_h + 0.04, num,
                transform=ax.transAxes, fontsize=10, color="white",
                ha="center", va="center", fontweight="bold")

        ax.text(x + box_w / 2, y + box_h - 0.05, title,
                transform=ax.transAxes, fontsize=8.0, color="#00838F",
                ha="center", va="top", fontweight="bold", multialignment="center")
        ax.text(x + box_w / 2, y + box_h - 0.22, desc,
                transform=ax.transAxes, fontsize=7.5, color=SUB_CLR,
                ha="center", va="top", multialignment="center")

        if k < n - 1:
            ax.annotate("", xy=(x + box_w + gap, y + box_h / 2 + 0.15),
                        xytext=(x + box_w, y + box_h / 2 + 0.15),
                        xycoords="axes fraction", textcoords="axes fraction",
                        arrowprops=dict(arrowstyle="->", color="#00838F", lw=1.5))

    ax.text(0.5, 0.06,
            "Output: one PNG per subject  ·  true spatial (x,y,depth) 3D block  ·  white dots = actual scan positions  ·  same colour scale as 2D",
            transform=ax.transAxes, fontsize=9, ha="center", color=SUB_CLR)

    save_slide(fig, "3D_00_overview.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3D-1 – Load & Filter  (brief, same logic as 2D)
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_step1():
    fig = base_fig("Step 1 — Load & Filter  (same as 2D)",
                   "3D Pipeline  (v7)", "STEP 1 / 8")

    ax = fig.add_axes([0.04, 0.06, 0.92, 0.78])
    ax.set_facecolor(BG)
    ax.axis("off")

    ax.text(0.5, 0.92, "Identical filtering to the 2D pipeline",
            transform=ax.transAxes, fontsize=14, ha="center",
            color=ACCENT, fontweight="bold")

    criteria = [
        ("exclude == 0", "Only analyst-approved rows"),
        ("depth ∈ [0, 40]", "Stratum corneum range"),
        ("depth → integer", "Round float depth values"),
    ]

    for i, (crit, desc) in enumerate(criteria):
        bx = 0.10 + i * 0.30
        by = 0.45
        rect = mpatches.FancyBboxPatch(
            (bx, by), 0.25, 0.25,
            boxstyle="round,pad=0.02",
            linewidth=1.5, edgecolor="#00838F",
            facecolor="#E0F7FA", transform=ax.transAxes, clip_on=False
        )
        ax.add_patch(rect)
        ax.text(bx + 0.125, by + 0.165, crit,
                transform=ax.transAxes, fontsize=11,
                ha="center", va="top", color="#00838F", fontweight="bold")
        ax.text(bx + 0.125, by + 0.085, desc,
                transform=ax.transAxes, fontsize=9.5,
                ha="center", va="top", color=TEXT_CLR)

    ax.text(0.5, 0.28, "Key difference vs 2D:",
            transform=ax.transAxes, fontsize=11, ha="center",
            color=ACCENT, fontweight="bold")
    ax.text(0.5, 0.18,
            "3D also uses  y_position  (the second spatial axis).\n"
            "No scan-merge step — every scan's (x, y) position is kept for spatial interpolation.",
            transform=ax.transAxes, fontsize=10.5, ha="center",
            color=TEXT_CLR, va="top")

    save_slide(fig, "3D_01_load_filter.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3D-2 – Group by (x,y,depth)
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_step2():
    fig = base_fig("Step 2 — Group by (x_position, y_position, depth)",
                   "3D Pipeline  (v7)", "STEP 2 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor("#E0F7FA")
    ax_txt.axis("off")

    lines = [
        "Purpose",
        "  Aggregate replicate measurements at",
        "  the same scan location and depth.",
        "",
        "Operation",
        "  group_by([x_position, y_position, depth])",
        "  → mean(Water_Percent)",
        "",
        "Result",
        "  Each unique (x, y, depth) triplet",
        "  has exactly one Water_Percent value.",
        "",
        "Scan positions extracted",
        "  Unique (x, y) pairs = the n scan",
        "  locations measured on the skin.",
        "  These are the input points for griddata.",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = "#00838F" if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.062, ln,
                    transform=ax_txt.transAxes, fontsize=9.2,
                    va="top", color=color, fontweight=weight)

    # Right: scatter of scan positions in 2D
    ax_r = fig.add_axes([0.44, 0.10, 0.52, 0.74])
    rng2 = np.random.default_rng(7)
    x_scans = rng2.uniform(-400, -200, 10)
    y_scans = rng2.uniform(100, 300, 10)

    ax_r.scatter(x_scans, y_scans, s=120, c="#00838F", zorder=5)
    for i, (xs, ys) in enumerate(zip(x_scans, y_scans)):
        ax_r.annotate(f"Scan {i+1}\n(x={xs:.0f}, y={ys:.0f})",
                      (xs, ys), textcoords="offset points",
                      xytext=(8, 5), fontsize=6.5, color=SUB_CLR)

    ax_r.set_xlabel("x_position  [µm]  (left–right on skin)", fontsize=9)
    ax_r.set_ylabel("y_position  [µm]  (front–back on skin)", fontsize=9)
    ax_r.set_title("Scattered scan positions in 2D space\n"
                   "(each carries a full depth profile 0–40 µm)",
                   fontsize=9.5, fontweight="bold", color="#00838F")
    ax_r.grid(True, alpha=0.3)
    ax_r.set_facecolor("#F9FBE7")

    save_slide(fig, "3D_02_group_positions.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3D-3 – Build Spatial Grid
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_step3():
    fig = base_fig("Step 3 — Build Regular Spatial Grid  (40 × 40)",
                   "3D Pipeline  (v7)", "STEP 3 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor("#E0F7FA")
    ax_txt.axis("off")

    lines = [
        "Problem",
        "  The 10 scan positions are scattered,",
        "  not on a regular grid.",
        "  Rendering requires a regular array.",
        "",
        "Solution",
        "  Compute bounding box of scan positions.",
        "  Add 15 % padding on each side.",
        "  Create 40 × 40 equally-spaced grid.",
        "",
        "Grid created",
        "  x_grid: 40 points spanning x_min–x_max",
        "  y_grid: 40 points spanning y_min–y_max",
        "  meshgrid(x_grid, y_grid) →",
        "  1600 query points for interpolation",
    ]
    for i, ln in enumerate(lines):
        weight = "bold" if ln and not ln.startswith(" ") else "normal"
        color  = "#00838F" if weight == "bold" else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.062, ln,
                    transform=ax_txt.transAxes, fontsize=9.2,
                    va="top", color=color, fontweight=weight)

    ax_r = fig.add_axes([0.44, 0.10, 0.52, 0.74])
    rng2 = np.random.default_rng(7)
    x_scans = rng2.uniform(-380, -220, 10)
    y_scans = rng2.uniform(120, 280, 10)
    x_pad = (x_scans.max() - x_scans.min()) * 0.15
    y_pad = (y_scans.max() - y_scans.min()) * 0.15
    xg = np.linspace(x_scans.min() - x_pad, x_scans.max() + x_pad, 10)
    yg = np.linspace(y_scans.min() - y_pad, y_scans.max() + y_pad, 10)
    Xg, Yg = np.meshgrid(xg, yg)

    ax_r.scatter(Xg, Yg, s=15, c="#B0BEC5", marker="s", zorder=2,
                 label="Regular grid points (40×40)")
    ax_r.scatter(x_scans, y_scans, s=120, c="#E53935", zorder=5, marker="o",
                 label="Actual scan positions")

    bbox_x = [x_scans.min(), x_scans.max(), x_scans.max(), x_scans.min(), x_scans.min()]
    bbox_y = [y_scans.min(), y_scans.min(), y_scans.max(), y_scans.max(), y_scans.min()]
    ax_r.plot(bbox_x, bbox_y, "r--", lw=1, label="Data bounding box")

    pad_x = [xg[0], xg[-1], xg[-1], xg[0], xg[0]]
    pad_y = [yg[0], yg[0], yg[-1], yg[-1], yg[0]]
    ax_r.plot(pad_x, pad_y, color="#00838F", lw=2, label="Grid with 15% padding")

    ax_r.set_xlabel("x_position  [µm]", fontsize=9)
    ax_r.set_ylabel("y_position  [µm]", fontsize=9)
    ax_r.set_title("Scan positions  +  regular interpolation grid",
                   fontsize=9.5, fontweight="bold", color="#00838F")
    ax_r.legend(fontsize=7.5)
    ax_r.grid(True, alpha=0.2)

    save_slide(fig, "3D_03_spatial_grid.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3D-4 – griddata Interpolation
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_step4():
    fig = base_fig("Step 4 — griddata Interpolation  (per depth slice)",
                   "3D Pipeline  (v7)", "STEP 4 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor("#E0F7FA")
    ax_txt.axis("off")

    lines = [
        "For each depth level  (0, 1, 2 … 40 µm)",
        "",
        "  Input: ~10 scattered (x,y) points",
        "  each with a Water_Percent value",
        "",
        "  Linear interpolation",
        "    Inside the convex hull of scan pts",
        "    → smooth gradient between scans",
        "",
        "  Nearest-neighbour extrapolation",
        "    Outside the convex hull",
        "    → no white gaps at grid edges",
        "",
        "  Combined: solid 40×40 slice",
        "    No NaN, no white holes",
        "",
        "  Repeated for all 41 depth levels",
    ]
    for i, ln in enumerate(lines):
        bold = ln and not ln.startswith(" ")
        color = "#00838F" if bold else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.060, ln,
                    transform=ax_txt.transAxes, fontsize=9.0,
                    va="top", color=color,
                    fontweight="bold" if bold else "normal")

    # Right: show one interpolated depth slice
    from scipy.interpolate import griddata as gd
    rng2 = np.random.default_rng(7)
    x_s = rng2.uniform(-380, -220, 10)
    y_s = rng2.uniform(120, 280, 10)
    vals = 40 + 15 * np.sin(x_s / 80) + 10 * np.cos(y_s / 60) + rng2.normal(0, 2, 10)
    x_pad = (x_s.max() - x_s.min()) * 0.15
    y_pad = (y_s.max() - y_s.min()) * 0.15
    xg = np.linspace(x_s.min() - x_pad, x_s.max() + x_pad, 40)
    yg = np.linspace(y_s.min() - y_pad, y_s.max() + y_pad, 40)
    Xg, Yg = np.meshgrid(xg, yg)
    gpts = np.column_stack([Xg.ravel(), Yg.ravel()])
    pts  = np.column_stack([x_s, y_s])
    z_lin  = gd(pts, vals, gpts, method="linear")
    z_near = gd(pts, vals, gpts, method="nearest")
    z_comb = np.where(np.isnan(z_lin), z_near, z_lin).reshape(40, 40)

    ax_r = fig.add_axes([0.44, 0.10, 0.52, 0.74])
    im = ax_r.imshow(z_comb, origin="lower",
                     extent=[xg[0], xg[-1], yg[0], yg[-1]],
                     aspect="auto", cmap=CMAP, vmin=VMIN, vmax=VMAX,
                     interpolation="bilinear")
    ax_r.scatter(x_s, y_s, s=80, c="white", edgecolors="#1565C0",
                 linewidths=1.2, zorder=5, label="Scan positions")
    ax_r.set_xlabel("x_position  [µm]", fontsize=9)
    ax_r.set_ylabel("y_position  [µm]", fontsize=9)
    ax_r.set_title("One interpolated depth slice  (e.g., depth = 5 µm)",
                   fontsize=9.5, fontweight="bold", color="#00838F")
    ax_r.legend(fontsize=8)
    cb = plt.colorbar(im, ax=ax_r, fraction=0.04, pad=0.03)
    cb.set_label("% Water", fontsize=8)
    cb.ax.invert_yaxis()

    save_slide(fig, "3D_04_griddata.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3D-5 – Stack → Volume
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_step5():
    fig = base_fig("Step 5 — Stack 41 Slices into a 3D Volume",
                   "3D Pipeline  (v7)", "STEP 5 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.38, 0.78])
    ax_txt.set_facecolor("#E0F7FA")
    ax_txt.axis("off")

    lines = [
        "Each depth level (0 – 40 µm)",
        "  is now a complete 40×40 spatial map.",
        "",
        "Stack all 41 slices",
        "  vol[ depth, y_grid, x_grid ]",
        "  Shape: (41, 40, 40)",
        "",
        "Clip to colour range",
        "  vol = clip(vol, 8%, 75%)",
        "",
        "Now a full 3D tissue block",
        "  x/y = skin surface position [µm]",
        "  depth = into stratum corneum [µm]",
        "  value = % water at that voxel",
    ]
    for i, ln in enumerate(lines):
        bold = ln and not ln.startswith(" ")
        color = "#00838F" if bold else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.065, ln,
                    transform=ax_txt.transAxes, fontsize=9.5,
                    va="top", color=color,
                    fontweight="bold" if bold else "normal")

    # Right: stacked slices diagram
    ax_r = fig.add_axes([0.43, 0.08, 0.54, 0.78])
    ax_r.axis("off")

    n_shown = 6
    offsets = np.linspace(0, 0.55, n_shown)
    depths_shown = [0, 8, 16, 24, 32, 40]

    for k in range(n_shown - 1, -1, -1):
        ox = offsets[k] * 0.35
        oy = offsets[k] * 0.28
        w, h = 0.38, 0.25

        # Colour block
        cval = 0.15 + k * 0.14
        face_color = CMAP(cval)
        rect = mpatches.FancyBboxPatch(
            (0.15 + ox, 0.08 + oy), w, h,
            boxstyle="square,pad=0.005",
            linewidth=1, edgecolor="#00838F",
            facecolor=face_color, alpha=0.85,
            transform=ax_r.transAxes, clip_on=False
        )
        ax_r.add_patch(rect)
        ax_r.text(0.15 + ox + w + 0.02, 0.08 + oy + h / 2,
                  f"depth = {depths_shown[k]} µm",
                  transform=ax_r.transAxes, fontsize=8,
                  va="center", color="#00838F")

    ax_r.text(0.50, 0.94, "vol  [41, 40, 40]",
              transform=ax_r.transAxes, fontsize=12,
              ha="center", va="top", color="#00838F", fontweight="bold")
    ax_r.text(0.50, 0.86, "← stacked in depth order →",
              transform=ax_r.transAxes, fontsize=9,
              ha="center", va="top", color=SUB_CLR)

    save_slide(fig, "3D_05_stack_volume.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3D-6 – 3D Gaussian Blur
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_step6():
    fig = base_fig("Step 6 — 3D Gaussian Blur",
                   "3D Pipeline  (v7)", "STEP 6 / 8")

    ax = fig.add_axes([0.04, 0.06, 0.92, 0.78])
    ax.set_facecolor(BG)
    ax.axis("off")

    ax.text(0.5, 0.96,
            "scipy.ndimage.gaussian_filter applied to the full 3D volume",
            transform=ax.transAxes, fontsize=11, ha="center", color=TEXT_CLR,
            va="top")

    params = [
        ("σ lateral  (x and y)", "0.08 × 40 = 3.2 pixels",
         "Gentle spatial smoothing\nacross the skin surface"),
        ("σ depth", "2.0 pixels  (≈ 2 µm)",
         "Smooth depth transitions\nwithin the tissue block"),
        ("Boundary handling", "Reflect  (default)",
         "No edge artefacts"),
    ]

    for i, (param, value, effect) in enumerate(params):
        bx = 0.05 + i * 0.32
        by = 0.45

        rect = mpatches.FancyBboxPatch(
            (bx, by), 0.28, 0.38,
            boxstyle="round,pad=0.02",
            linewidth=1.5, edgecolor="#00838F",
            facecolor="#E0F7FA", transform=ax.transAxes, clip_on=False
        )
        ax.add_patch(rect)
        ax.text(bx + 0.14, by + 0.35, param,
                transform=ax.transAxes, fontsize=10,
                ha="center", va="top", color="#00838F", fontweight="bold")
        ax.text(bx + 0.14, by + 0.25, value,
                transform=ax.transAxes, fontsize=9.5,
                ha="center", va="top", color=TEXT_CLR, fontweight="bold")
        ax.text(bx + 0.14, by + 0.13, effect,
                transform=ax.transAxes, fontsize=9,
                ha="center", va="top", color=SUB_CLR, multialignment="center")

    ax.text(0.5, 0.35, "Output clipped back to [8, 75 %] after blurring.",
            transform=ax.transAxes, fontsize=10, ha="center", color=TEXT_CLR)
    ax.text(0.5, 0.22, "Purpose: create a naturally smooth 3D tissue appearance —\n"
            "artefacts from the griddata interpolation are softened.",
            transform=ax.transAxes, fontsize=10, ha="center", color=SUB_CLR,
            va="top", multialignment="center")

    save_slide(fig, "3D_06_gaussian_blur.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3D-7 – Upsample Depth
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_step7():
    fig = base_fig("Step 7 — Upsample Depth Axis  (41 → 100 pixels)",
                   "3D Pipeline  (v7)", "STEP 7 / 8")

    ax = fig.add_axes([0.04, 0.06, 0.92, 0.78])
    ax.set_facecolor(BG)
    ax.axis("off")

    ax.text(0.5, 0.96, "scipy.ndimage.zoom  —  bicubic interpolation along depth only",
            transform=ax.transAxes, fontsize=11, ha="center", color=TEXT_CLR, va="top")

    # Diagram: before/after
    for side, label, nx, ny, color in [
        (0.08, "Before:  (41, 40, 40)", 40, 41, "#78909C"),
        (0.55, "After:  (100, 40, 40)",  40, 100, "#00838F"),
    ]:
        rect = mpatches.FancyBboxPatch(
            (side, 0.25), 0.35, 0.55,
            boxstyle="round,pad=0.02",
            linewidth=2, edgecolor=color,
            facecolor="#E0F7FA", transform=ax.transAxes, clip_on=False
        )
        ax.add_patch(rect)
        ax.text(side + 0.175, 0.76, label,
                transform=ax.transAxes, fontsize=11,
                ha="center", va="top", color=color, fontweight="bold")
        ax.text(side + 0.175, 0.66, f"Depth axis: {ny} pixels",
                transform=ax.transAxes, fontsize=10,
                ha="center", va="top", color=TEXT_CLR)
        ax.text(side + 0.175, 0.55, f"x/y axes: {nx} pixels each\n(unchanged)",
                transform=ax.transAxes, fontsize=9.5,
                ha="center", va="top", color=SUB_CLR, multialignment="center")
        ax.text(side + 0.175, 0.38,
                "0.975 µm per depth pixel" if ny == 41 else "0.40 µm per depth pixel",
                transform=ax.transAxes, fontsize=9,
                ha="center", va="top", color=TEXT_CLR)

    ax.annotate("", xy=(0.52, 0.52), xytext=(0.46, 0.52),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=2.5))

    ax.text(0.5, 0.16,
            "Zoom factor = 100 / 41 ≈ 2.44  ·  order=3 (bicubic)  ·  only depth axis scaled\n"
            "Purpose: produces smoother face surfaces on the rendered 3D box.",
            transform=ax.transAxes, fontsize=10, ha="center", color=SUB_CLR,
            va="top", multialignment="center")

    save_slide(fig, "3D_07_upsample_depth.png")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3D-8 – Draw 5-Face 3D Box
# ═══════════════════════════════════════════════════════════════════════════

def slide_3d_step8():
    fig = base_fig("Step 8 — Render 5-Face 3D Box",
                   "3D Pipeline  (v7)", "STEP 8 / 8")

    ax_txt = fig.add_axes([0.02, 0.06, 0.36, 0.78])
    ax_txt.set_facecolor("#E0F7FA")
    ax_txt.axis("off")

    lines = [
        "Five visible faces rendered",
        "  Top    depth = 0 µm  (skin surface)",
        "  Front  y = y_min  (anterior slice)",
        "  Back   y = y_max  (posterior slice)",
        "  Left   x = x_min  (medial slice)",
        "  Right  x = x_max  (lateral slice)",
        "",
        "Axes (real µm units)",
        "  x = x_position  (left–right on skin)",
        "  y = y_position  (front–back on skin)",
        "  z = depth  (0 at top, 40 at bottom)",
        "",
        "White dots on top face",
        "  Mark the actual 10 scan positions.",
        "  Numbered for reference.",
        "",
        "Same colour map as 2D",
        "  Direct colour comparison possible.",
    ]
    for i, ln in enumerate(lines):
        bold = ln and not ln.startswith(" ")
        color = "#00838F" if bold else TEXT_CLR
        ax_txt.text(0.04, 0.97 - i * 0.058, ln,
                    transform=ax_txt.transAxes, fontsize=9.0,
                    va="top", color=color,
                    fontweight="bold" if bold else "normal")

    # Right: actual 3D box using synthetic data
    from scipy.interpolate import griddata as gd
    rng2 = np.random.default_rng(7)
    x_scans = rng2.uniform(-380, -220, 10)
    y_scans = rng2.uniform(120, 280, 10)
    pts = np.column_stack([x_scans, y_scans])

    x_pad = (x_scans.max() - x_scans.min()) * 0.15
    y_pad = (y_scans.max() - y_scans.min()) * 0.15
    xg = np.linspace(x_scans.min() - x_pad, x_scans.max() + x_pad, 20)
    yg = np.linspace(y_scans.min() - y_pad, y_scans.max() + y_pad, 20)
    Xg, Yg = np.meshgrid(xg, yg)
    gpts = np.column_stack([Xg.ravel(), Yg.ravel()])

    n_depths = 20
    vol = np.zeros((n_depths, 20, 20))
    d_arr = np.linspace(0, 40, n_depths)
    for di, depth in enumerate(d_arr):
        decay = np.exp(-depth / 15)
        vals = (55 * decay + 30 * (1 - decay)
                + 8 * np.sin(x_scans / 80) + rng2.normal(0, 1, 10))
        z_lin  = gd(pts, vals, gpts, method="linear")
        z_near = gd(pts, vals, gpts, method="nearest")
        z = np.where(np.isnan(z_lin), z_near, z_lin).reshape(20, 20)
        vol[di] = np.clip(gaussian_filter(z, sigma=1), VMIN, VMAX)

    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    from matplotlib import cm as mpl_cm
    import matplotlib.colors as mcolors

    norm_3d = mcolors.Normalize(vmin=VMIN, vmax=VMAX)

    ax_r = fig.add_axes([0.40, 0.04, 0.58, 0.88], projection="3d")

    D1d = np.linspace(0, 40, n_depths)
    kw  = dict(shade=False, linewidth=0, antialiased=False)

    def rgba(d2):
        return CMAP(norm_3d(np.clip(d2, VMIN, VMAX)))

    GX, GY = np.meshgrid(xg, yg)
    GX_d, GD   = np.meshgrid(xg, D1d)
    GY_d, GD2  = np.meshgrid(yg, D1d)

    ax_r.plot_surface(GX, GY, np.zeros_like(GX),
                      facecolors=rgba(vol[0]), **kw)
    ax_r.plot_surface(GX_d, np.full_like(GX_d, yg[0]),  GD,
                      facecolors=rgba(vol[:, 0, :]), **kw)
    ax_r.plot_surface(GX_d, np.full_like(GX_d, yg[-1]), GD,
                      facecolors=rgba(vol[:, -1, :]), **kw)
    ax_r.plot_surface(np.full_like(GY_d, xg[0]),  GY_d, GD2,
                      facecolors=rgba(vol[:, :, 0]), **kw)
    ax_r.plot_surface(np.full_like(GY_d, xg[-1]), GY_d, GD2,
                      facecolors=rgba(vol[:, :, -1]), **kw)

    for xs, ys in zip(x_scans, y_scans):
        ax_r.scatter(xs, ys, 0, s=20, c="white",
                     edgecolors="#1565C0", linewidths=0.8,
                     zorder=10, depthshade=False)

    ax_r.set_xlim(xg[0], xg[-1])
    ax_r.set_ylim(yg[0], yg[-1])
    ax_r.set_zlim(40, 0)
    ax_r.set_xlabel("x [µm]", fontsize=7, labelpad=1)
    ax_r.set_ylabel("y [µm]", fontsize=7, labelpad=1)
    ax_r.set_zlabel("depth [µm]", fontsize=7, labelpad=2)
    ax_r.view_init(elev=28, azim=-55)
    for pane in [ax_r.xaxis.pane, ax_r.yaxis.pane, ax_r.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor("#cccccc")
    ax_r.set_title("Rendered 3D box\n(white dots = scan positions)",
                   fontsize=9.5, fontweight="bold", color="#00838F")

    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=norm_3d)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax_r, fraction=0.025, pad=0.04, shrink=0.7)
    cb.ax.invert_yaxis()
    cb.set_label("% Water", fontsize=8)

    save_slide(fig, "3D_08_render.png")


# ═══════════════════════════════════════════════════════════════════════════
#  STAKEHOLDER EMAIL  (plain text file)
# ═══════════════════════════════════════════════════════════════════════════

def write_email():
    email = """\
Subject: Automated Raman Water Concentration Heatmaps – How the Analysis Works

Dear [Stakeholder name],

I wanted to briefly walk you through how our automated Raman water
concentration analysis works and what the output images represent.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT WE MEASURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Raman spectroscopy measures water concentration (%) in the outer skin
layer (stratum corneum, 0–40 µm deep).  Up to 10 scan positions per
subject are collected at three time-points (baseline, 1 h, 4 h after
product application) for three products (B, C, D).


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2D HEATMAP  —  "How do depth profiles compare across scans?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Filter  →  keep only quality-approved rows, depth 0–40 µm.
2. Merge   →  if two scan positions are closer than 10 µm they are
              averaged into one (prevents mathematical artefacts).
3. Matrix  →  arrange data as a table: rows = depth, columns = scans.
4. Fill    →  any missing cells are filled by interpolating neighbours.
5. Smooth  →  PCHIP spline upsamples the matrix to a fine pixel grid.
              (PCHIP is stable by design; it cannot produce impossible
              values such as negative or >100 % water.)
6. Blur    →  a gentle Gaussian blur softens pixel boundaries.
7. Render  →  x-axis = scan number 1…n, y-axis = depth.
              Colour scale: yellow = dry (8 %), dark navy = wet (75 %).


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3D HEATMAP  —  "Where on the skin surface is water highest?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Filter  →  same quality filter as 2D.
2. Positions →  each scan has real (x, y) coordinates on the skin
              (in µm), giving a true spatial layout.
3. Grid    →  a regular 40 × 40 spatial grid is placed over the scan
              area (with a 15 % border beyond the outermost scans).
4. Interpolate →  for each depth level, the ~10 scattered values are
              interpolated onto the full grid using 'griddata':
              linear interpolation within the scanned area, nearest-
              neighbour at the edges – no white gaps.
5. Volume  →  41 interpolated slices are stacked into a 3D data block.
6. Smooth  →  3D Gaussian blur for a natural appearance.
7. Upsample → depth axis refined from 41 to 100 pixels.
8. Render  →  a five-face 3D box.  White dots on the top face mark the
              actual scan positions.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY POINTS FOR INTERPRETATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• The 2D and 3D images answer different questions and will look
  different – this is intentional, not an error.
• Both use the identical colour scale (yellow = dry, navy = wet) so
  you can compare water levels directly across views.
• Quality flags are logged automatically (sparse data, merged scans,
  etc.) and do not affect subjects without data issues.
• One PNG is generated per subject, containing all 9 panels
  (3 products × 3 time-points) in a single page.

Please feel free to reach out with any questions.

Best regards,
[Your name]
"""
    path = Path(OUT_DIR) / "stakeholder_email.txt"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(email)
    print(f"  saved -> {path}")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n=== Generating 2D algorithm slides ===")
    slide_2d_overview()
    slide_2d_step1()
    slide_2d_step2()
    slide_2d_step3()
    slide_2d_step4()
    slide_2d_step5()
    slide_2d_step6()
    slide_2d_step7()
    slide_2d_step8()

    print("\n=== Generating 3D algorithm slides ===")
    slide_3d_overview()
    slide_3d_step1()
    slide_3d_step2()
    slide_3d_step3()
    slide_3d_step4()
    slide_3d_step5()
    slide_3d_step6()
    slide_3d_step7()
    slide_3d_step8()

    print("\n=== Writing stakeholder email ===")
    write_email()

    print(f"\nAll done.  Output folder: {OUT_DIR}")
