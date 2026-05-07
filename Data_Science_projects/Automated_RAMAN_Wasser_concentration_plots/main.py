"""
Entry point for the Raman water-concentration heatmap pipeline.

Drives two independent rendering pipelines:

- **2D pipeline** (``heatmap_2d``): produces per-subject PNGs where the
  x-axis is scan index (original data order) and the y-axis is depth.
- **3D pipeline** (``heatmap_3d``): produces per-subject PNGs showing a
  five-face 3D tissue block with real (x, y) scan positions and depth as
  the z-axis.

CLI options
-----------
--input   Path to the input Excel file (default: data/raman_water_data.xlsx)
--output  Directory for output PNGs and quality log (default: output/)
--mode    Which pipeline(s) to run: 2d | 3d | both (default: both)
"""

import argparse
from pathlib import Path

from heatmap_2d import make_2d_heatmap
from heatmap_3d import make_3d_heatmap

DEFAULT_INPUT = Path("data/raman_water_data.xlsx")
DEFAULT_OUTPUT = Path("output")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 2D and/or 3D Raman water-concentration heatmaps."
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Path to input Excel file (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Output directory for PNGs and quality log (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--mode", choices=["2d", "3d", "both"], default="both",
        help="Which pipeline(s) to run (default: both)"
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    if args.mode in ("2d", "both"):
        print("Making 2D heatmap...")
        make_2d_heatmap(args.input, args.output)

    if args.mode in ("3d", "both"):
        print("Making 3D heatmap...")
        make_3d_heatmap(args.input, args.output)

    print("All heatmaps generated successfully!")


if __name__ == "__main__":
    main()
