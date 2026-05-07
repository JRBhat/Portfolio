"""
pyzbar-based barcode detector for single images.

What it does: reads a JPG/PNG, applies a grayscale mask (MASK_LOWER–MASK_UPPER),
decodes the first barcode found, draws a bounding box, and saves debug artifacts.

Inputs:  path (str) — filesystem path to the image.
Outputs: barcode data as a byte string, or None if undetected.
         Debug images written to DEBUG_OUTPUT_DIR (default: "bin/").

Key constants: MASK_LOWER, MASK_UPPER, BBOX_PAD, BBOX_COLOR, BBOX_THICKNESS,
               DEBUG_OUTPUT_DIR.
"""

# Importing required libraries
import cv2
from pyzbar.pyzbar import decode
import numpy as np
import os
from typing import Optional

MASK_LOWER: int = 170
MASK_UPPER: int = 255
BBOX_PAD: int = 10
BBOX_COLOR: tuple = (255, 0, 0)  # BGR
BBOX_THICKNESS: int = 5
DEBUG_OUTPUT_DIR: str = "bin"


def _save_debug_artifacts(path: str, mask, img) -> None:
    """Write the binary mask and annotated image to DEBUG_OUTPUT_DIR."""
    image_filename = os.path.basename(path)
    cv2.imwrite(os.path.join(DEBUG_OUTPUT_DIR, image_filename + "_masked.png"), mask)
    cv2.imwrite(os.path.join(DEBUG_OUTPUT_DIR, image_filename + "_detected.png"), img)


def read_barcode(path: str) -> Optional[str]:
    """
    Reads and decodes a barcode from an image at the specified path.

    Args:
    - path (str): The file path of the image to process.

    Returns:
    - str or None: The decoded barcode data if detected, otherwise None.
    """

    os.makedirs(DEBUG_OUTPUT_DIR, exist_ok=True)

    # Read the image as a NumPy array
    img = cv2.imread(path)

    # Convert the image to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Create a binary mask with pixel values in the range MASK_LOWER to MASK_UPPER
    mask = cv2.inRange(gray, MASK_LOWER, MASK_UPPER)

    # Decode the barcode from the masked image
    detected_barcodes = decode(mask)

    # Check if barcodes are detected
    if not detected_barcodes:
        print("Barcode Not Detected or your barcode is blank/corrupted!")
        return None
    # Process each detected barcode
    for barcode in detected_barcodes:
        # Get the bounding box of the barcode
        (x, y, w, h) = barcode.rect

        # Draw a rectangle around the detected barcode
        cv2.rectangle(
            img,
            (x - BBOX_PAD, y - BBOX_PAD),
            (x + w + BBOX_PAD, y + h + BBOX_PAD),
            BBOX_COLOR,
            BBOX_THICKNESS,
        )

        # Save the masked and detected images in the `bin` directory
        _save_debug_artifacts(path, mask, img)

        # If the barcode data is not empty, print and return it
        if barcode.data != "":
            print(barcode.data)
            return barcode.data

if __name__ == "__main__":
    # Define the path to a sample image
    path_to_image = "data/sample_image.JPG"

    # Call the read_barcode function with the sample image path
    read_barcode(path_to_image)
