"""Scan registration helpers.

Estimates a similarity transform between reference and skewed PTX coordinates
and rewrites the skewed PTX with transformed coordinates.  The registration is
coordinate-only: the pixel image is not warped.  If fewer than 3 coordinate
pairs are available the functions return ``(None, None)`` and log an error.
"""
import json
import numpy as np
from skimage import io, transform
import shutil
import logging
from detect_qrcode import read_ptx_file, write_ptx_file, extract_coordinates

# PTX schema id constants (mirrors detect_qrcode.py)
PTX_ID_QRCODES = 1
PTX_ID_TOP_CIRCLES = 2
PTX_ID_BOTTOM_CIRCLES = 3


def register_image(reference_ptx, skewed_ptx, skewed_image_path):
    """Estimate a similarity transform from reference to skewed QR-code coordinates.

    Reads both PTX files, extracts QR-code and circle coordinates, and fits a
    ``skimage.transform.SimilarityTransform`` using the QR-code corner pairs.
    The transform is then applied to all three coordinate sets.

    :param reference_ptx: Path to the reference (golden-standard) PTX file.
    :param skewed_ptx: Path to the skewed scan PTX file.
    :param skewed_image_path: Path to the skewed scan image (used only for logging).
    :returns: ``(transformed_coords_dict, similarity_transform)`` where
        *transformed_coords_dict* maps ``"ptx_id1/2/3"`` to transformed
        coordinate arrays, or ``(None, None)`` when registration fails.
    """
    # Read PTX files
    ref_data = read_ptx_file(reference_ptx)
    skewed_data = read_ptx_file(skewed_ptx)

    # Extract coordinates
    ref_coords_dict = extract_coordinates(ref_data)
    skewed_coords_dict = extract_coordinates(skewed_data)

    # Ensure we have at least 3 pairs of coordinates
    try:
        assert len(ref_coords_dict) >= 3 and len(skewed_coords_dict) >= 3, "Expected at least 3 pairs of coordinates"
    except AssertionError:
        logging.error(f"{skewed_image_path} Fails.\n\n Expected at least 3 pairs of coordinates")
        transformed_coords, similarity_transform = None, None
        return transformed_coords, similarity_transform
    # Compute the similarity transform
    try:
        similarity_transform = transform.SimilarityTransform()
        # Estimate the transformation function from src:org ref qrcode to dst: skw qrcode coordinate
        similarity_transform.estimate(ref_coords_dict["qrcoords"], skewed_coords_dict["qrcoords"])

    except ValueError:
        logging.error(f"{skewed_image_path} fails\n due to coords dimension mismatch")
        transformed_coords, similarity_transform = None, None
        return transformed_coords, similarity_transform

    # Get the transformed coordinates
    transformed_qrcodes = similarity_transform(ref_coords_dict["qrcoords"])
    transformed_top_circles = similarity_transform(ref_coords_dict["top_circles"])
    transformed_bottom_circles = similarity_transform(ref_coords_dict["bottom_circles"])

    transformation_dict={}
    transformation_dict["ptx_id1"] = transformed_qrcodes
    transformation_dict["ptx_id2"] = transformed_top_circles
    transformation_dict["ptx_id3"] = transformed_bottom_circles

    return transformation_dict, similarity_transform


def registration_step(reference_ptx, skewed_ptx, skewed_image_path, registered_img_savepath, print_reg_details=False):
    """Run the full registration pipeline for one scan.

    Calls :func:`register_image` to obtain transformed coordinates, then
    calls :func:`create_final_ptx` to overwrite the skewed PTX in-place.
    If registration fails (``transformed_coords_dict is None``), logs an error
    and returns without writing any file.

    :param reference_ptx: Path to the reference PTX.
    :param skewed_ptx: Path to the skewed PTX (will be overwritten on success).
    :param skewed_image_path: Path to the skewed scan image.
    :param registered_img_savepath: Reserved for future image-warp output (unused).
    :param print_reg_details: When ``True``, enables verbose debug logging.
    """
    transformed_coords_dict, transformation_matrix = register_image(reference_ptx, skewed_ptx, skewed_image_path)

    # (registration-by-warp implementation removed; see git history)

    if transformed_coords_dict is None:
        logging.error(f"Skipping {skewed_image_path}: registration failed")
        return

    create_final_ptx(skewed_ptx, transformed_coords_dict)

def create_final_ptx(skewed_ptx_path, transformed_coords_dict):
    """Overwrite *skewed_ptx_path* with transformed coordinates.

    Copies the original PTX to a ``*_BCKP.ptx`` backup, then rewrites the
    original with the coordinates from *transformed_coords_dict*.

    :param skewed_ptx_path: Path to the skewed PTX file (modified in-place).
    :param transformed_coords_dict: Dict with keys ``"ptx_id1"``, ``"ptx_id2"``,
        ``"ptx_id3"`` mapping to numpy arrays of transformed coordinates.
    :returns: The path to the (overwritten) PTX file.
    """
    src_path = skewed_ptx_path
    dest_path = skewed_ptx_path.replace("SKW", "SKW_BCKP")
    shutil.copy(src_path, dest_path)

    data = read_ptx_file(skewed_ptx_path)

    for item in data:
        if item["id"] == PTX_ID_QRCODES:
            item["contour"] = transformed_coords_dict["ptx_id1"].tolist()
        elif item["id"] == PTX_ID_TOP_CIRCLES:
            item["contour"] = transformed_coords_dict["ptx_id2"].tolist()
        elif item["id"] == PTX_ID_BOTTOM_CIRCLES:
            item["contour"] = transformed_coords_dict["ptx_id3"].tolist()

    with open(skewed_ptx_path, "w") as fptx:
        json.dump(data, fptx, indent=4)

    return skewed_ptx_path

def main():
    # Usage example
    reference_ptx = "data/reference/S998F99T99ORG.ptx"
    skewed_ptx = "data/scans/S987F99T99SKW.ptx"
    skewed_image_path = "data/scans/S901F01T01SKW.tif"
    registered_img_savepath = "output/S901F01T01REG.tif"

    registration_step(reference_ptx, skewed_ptx, skewed_image_path, registered_img_savepath, print_reg_details=True)


if __name__ == "__main__":
    main()
