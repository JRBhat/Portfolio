import logging
import os
import re
from datetime import datetime
import numpy as np
from ImageAnalysis import Util as Ut
from ImageAnalysis import ImageIO as Io

# Constants
FILENAME_PATTERN = r"S[0-9]{3}F[0-9]{2}T[0-9]{2}STUDYID*"  # Replace STUDYID with your study's filename suffix
CROP_PADDING = 100 # px to pad around bbox
# CROP_RESOLUTION: (width, height) in pixels. Set to None to auto-calculate.
# Example: CROP_RESOLUTION = (512, 512) or CROP_RESOLUTION = (800, 600)
CROP_RESOLUTION = (1000, 1000)  # User-provided resolution (width, height) or None for auto-calculation
ORDERING = ["right_lower", "right_upper", "left_lower", "left_upper"]
# Reference dictionary mapping order names to (filename prefix, contour ID)
REF_DICT = {"right_lower": ["F01", 0], "right_upper": ["F01", 1],
            "left_lower": ["F02", 2], "left_upper": ["F02", 3]
            }


def setup_directories(order):
    input_dir = r"data\raw\conv_cleaned"  # Set this to your local input directory
    output_base = r"data\processed\pias_cropped"  # Set this to your local output directory
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = os.path.join(output_base, f"{order}_{ts}")
    Ut.createDirectory(out_dir)
    return input_dir, out_dir


def get_files(directory, order):
    images, pts = {}, {}
    prefix, cid = REF_DICT[order]
    for fn in os.listdir(directory):
        if fn.endswith('.TIF') and prefix in fn:
            m = re.search(FILENAME_PATTERN, fn)
            if not m:
                continue
            base = m.group(0)
            images[base] = os.path.join(directory, f"{base}.TIF")
            pts[base] = os.path.join(directory, f"{base}.ptx")
    return {'Images': images, 'PointFiles': pts}, cid


def calculate_bbox(ptx_file, contour_id):
    data = Ut.read_ptx_file(ptx_file)
    pts = np.array(data[contour_id]['contour'])
    xmin, ymin = pts[:, 0].min(), pts[:, 1].min()
    xmax, ymax = pts[:, 0].max(), pts[:, 1].max()
    return xmin, ymin, xmax, ymax


def compute_global_params(point_files, contour_id):
    """
    Returns:
      centers: dict mapping base → (cx, cy)
      final_w, final_h: int, the crop width/height
    
    If CROP_RESOLUTION is set, uses the user-provided resolution.
    Otherwise, calculates based on the max width/height of all bboxes + padding.
    """
    centers = {}
    widths = []
    heights = []

    for base, f in point_files.items():
        try:
            xmin, ymin, xmax, ymax = calculate_bbox(f, contour_id)
        except Exception as e:
            logging.warning("Error reading %s: %s", f, e)
            continue

        w_i = xmax - xmin
        h_i = ymax - ymin
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2

        centers[base] = (cx, cy)
        widths.append(w_i)
        heights.append(h_i)

    if not centers:
        raise ValueError("No valid .ptx files found – check your filenames/pattern.")

    # Use user-provided resolution if set, otherwise auto-calculate
    if CROP_RESOLUTION is not None:
        final_w, final_h = CROP_RESOLUTION
        print(f"Using enforced crop resolution: {final_w}x{final_h}")
    else:
        final_w = int(max(widths) + 2 * CROP_PADDING)
        final_h = int(max(heights) + 2 * CROP_PADDING)
        print(f"Using auto-calculated crop resolution: {final_w}x{final_h}")
    
    return centers, final_w, final_h


def crop_and_save(image, cx, cy, w, h, out_path):
    H, W = image.shape[:2]
    left = int(np.floor(cx - w / 2))
    top = int(np.floor(cy - h / 2))
    right = left + w
    bottom = top + h

    # Compute in-bounds crop region
    crop_left = max(left, 0)
    crop_top = max(top, 0)
    crop_right = min(right, W)
    crop_bottom = min(bottom, H)

    # Crop the in-bounds region
    crop = image[crop_top:crop_bottom, crop_left:crop_right]

    # Calculate padding amounts
    pad_top = crop_top - top
    pad_bottom = bottom - crop_bottom
    pad_left = crop_left - left
    pad_right = right - crop_right

    # Pad as needed
    crop_padded = np.pad(
        crop,
        pad_width=((pad_top, pad_bottom), (pad_left, pad_right), (0, 0)),
        mode='edge'
    )

    # Sanity check: ensure final shape is exactly (h, w)
    assert crop_padded.shape[0] == h and crop_padded.shape[1] == w, \
        f"Padding mismatch: got {crop_padded.shape}, expected {(h, w)}"

    Io.writeImage(crop_padded, out_path)


def process(files, centers, final_w, final_h, out_dir):
    for base, img_path in files['Images'].items():
        if base not in centers:
            print(f"Skipping {base!r}: no center computed.")
            continue
        cx, cy = centers[base]
        img = Io.readRGBImage(img_path)
        out = Ut.create_filename_from_basefile(
            img_path,
            directory=out_dir,
            file_ext=f"_crop_{final_w}x{final_h}.TIF"
        )
        crop_and_save(img, cx, cy, final_w, final_h, out)


def main():
    
    for order in ORDERING:
        inp, outp = setup_directories(order)
        files, cid = get_files(inp, order)
        centers, fw, fh = compute_global_params(files['PointFiles'], cid)
        process(files, centers, fw, fh, outp)


if __name__ == '__main__':
    main()
