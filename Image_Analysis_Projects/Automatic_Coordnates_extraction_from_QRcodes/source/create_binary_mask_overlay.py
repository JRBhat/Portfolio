"""Binary mask and overlay generation from circle contour PTX data.

Reads circle contours (ids 2 and 3) from the PTX file paired with each scan
image and emits three output ``.tif`` files per image:

* ``*_binary.tif``        -- binary mask where each circle region is white
* ``*_overlay.tif``       -- semi-transparent blend of original + mask
* ``*_overlay_w_circ.tif``-- overlay with green circle outlines drawn on top
"""
import cv2
import numpy as np
import json
import os

# IDs of the circle entries in the PTX file used for mask generation
MASK_CIRCLE_IDS = [2, 3]

def create_circle_mask(json_file_path, image_path, circle_ids):
    # Load the image to get its dimensions
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Image not found or unable to read the image file.")
    image_height, image_width = image.shape[:2]

    # Load the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Create a blank binary mask with the same dimensions as the image
    mask = np.zeros((image_height, image_width), dtype=np.uint8)

    # Process each circle entry based on the provided IDs
    for entry in data:
        if entry['id'] in circle_ids:
            radii = entry['radius']
            contours = entry['contour']

            # Draw circles on the mask
            for (x, y), radius in zip(contours, radii):
                cv2.circle(mask, (int(x), int(y)), radius, (255), thickness=-1)  # 255 for white (1 in binary)

    return mask

def overlay_mask_on_image(image, mask):
    """Blend *mask* semi-transparently over *image* and return the result.

    :param image: Original BGR image as a numpy array.
    :param mask: Single-channel binary mask (same spatial size as *image*).
    :returns: BGR overlay image (70 % original, 30 % mask).
    """
    # Convert the mask to a 3-channel image
    mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    # Create a semi-transparent overlay
    overlay = cv2.addWeighted(image, 0.7, mask_colored, 0.3, 0)

    return overlay

def draw_circles_on_image(image, json_file_path, circle_ids):
    """Draw green circle outlines on *image* for each entry matching *circle_ids*.

    :param image: BGR image to draw on (modified in-place).
    :param json_file_path: Path to the PTX/JSON file with circle contours.
    :param circle_ids: List of PTX id values to include.
    :returns: The modified *image*.
    """
    # Load the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Draw circles directly on the image
    for entry in data:
        if entry['id'] in circle_ids:
            radii = entry['radius']
            contours = entry['contour']

            for (x, y), radius in zip(contours, radii):
                cv2.circle(image, (int(x), int(y)), radius, (0, 255, 0), thickness=2)  # Green circles

    return image


def generate_masks(image_path, outpath):
    """Generate binary, overlay, and overlay-with-circles outputs for *image_path*.

    Reads the matching PTX file (same path, ``.tif`` -> ``.ptx``), creates a
    circle mask using :data:`MASK_CIRCLE_IDS`, and writes three ``.tif`` files
    into *outpath*.

    :param image_path: Path to the registered scan (``.tif``).
    :param outpath: Directory where the three output images will be saved.
    """
    os.makedirs(outpath, exist_ok=True)

    json_file_path = image_path.replace(".tif", ".ptx")

    # Load the original image
    original_image = cv2.imread(image_path)

    # Create the binary mask
    binary_mask = create_circle_mask(json_file_path, image_path, MASK_CIRCLE_IDS)

    # Save the binary mask
    cv2.imwrite(os.path.join(outpath, os.path.basename(image_path).replace(".tif", "_binary.tif")), binary_mask)


    # Create an overlay with the mask
    overlay_image = overlay_mask_on_image(original_image.copy(), binary_mask)

    # Save the overlay image
    cv2.imwrite(os.path.join(outpath, os.path.basename(image_path).replace(".tif", "_overlay.tif")), overlay_image)

    # Draw circles on the original image
    image_with_circles = draw_circles_on_image(overlay_image, json_file_path, MASK_CIRCLE_IDS)

    # Save the image with circles
    cv2.imwrite(os.path.join(outpath, os.path.basename(image_path).replace(".tif", "_overlay_w_circ.tif")), image_with_circles)


if __name__ == "__main__":

    # Example usage
    image_path = "data/scans/test_good/S700F99T99REG.tif"  # Path to your image file
    outputPath = os.path.join(os.path.dirname(image_path), "out")
    os.makedirs(outputPath, exist_ok=True)
    # TESTING
    generate_masks(image_path, outputPath)
