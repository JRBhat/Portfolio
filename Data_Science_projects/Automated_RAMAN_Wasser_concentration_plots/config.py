"""
Study-design and visual-style constants shared by the 2D, 3D, and slide
pipelines.

These constants encode the following study assumptions:
- 3 product codes (B, C, D) × 3 time-points (T01 BL, T02 D01_1h, T03 D01_4h)
- 10 scans expected per panel
- Depth grid runs from 0 to 40 µm at 1 µm resolution (41 integer levels)
- Colour scale spans 8–75 % water, using a custom 6-node yellow-to-navy map
"""

# -- Colour scale -----------------------------------------------------------
VMIN = 8
VMAX = 75

# -- Custom colour map nodes and colours ------------------------------------
CMAP_NODES = [0.00, 0.18, 0.38, 0.58, 0.78, 1.00]
CMAP_COLORS = ["#FFFF00", "#CC9900", "#4CAF50", "#40E0D0", "#1E90FF", "#00008B"]

# -- Figure layout ----------------------------------------------------------
ROWS = [("_B", "Code B"), ("_C", "Code C"), ("_D", "Code D")]
COLS = [("T01", "BL"), ("T02", "D01_1h"), ("T03", "D01_4h")]

# -- Expected scan count per panel ------------------------------------------
EXPECTED_SCANS_PER_PANEL = 10

# -- Depth grid -------------------------------------------------------------
DEPTH_MIN_UM = 0
DEPTH_MAX_UM = 40
N_DEPTH_LEVELS = 41
