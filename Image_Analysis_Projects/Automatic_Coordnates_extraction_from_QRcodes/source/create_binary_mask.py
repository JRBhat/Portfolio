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
                cv2.circle(mask, (x, y), radius, (255), thickness=-1)  # 255 for white (1 in binary)

    return mask

def main():
    # Example usage
    json_file_path = "data/scans/test_good/S700F99T99REG.ptx"  # Path to your JSON file
    image_path = "data/scans/test_good/S700F99T99REG.tiff"  # Path to your image file

    binary_mask = create_circle_mask(json_file_path, image_path, MASK_CIRCLE_IDS)

    # Save or display the mask
    cv2.imwrite(os.path.join(os.path.dirname(image_path), os.path.basename(image_path).replace(".tiff", "_binary.tiff")), binary_mask)
    # cv2.imshow('Mask', binary_mask)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
