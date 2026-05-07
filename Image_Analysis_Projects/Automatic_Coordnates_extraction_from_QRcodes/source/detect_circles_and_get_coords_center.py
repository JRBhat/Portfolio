
import numpy as np
import matplotlib.pyplot as plt
from skimage import io, color, feature, transform, draw
from skimage.transform import hough_circle, hough_circle_peaks
from skimage.feature import canny
from skimage.draw import circle_perimeter
from scipy import ndimage as ndi
import cv2


def detect_circles(image, min_radius=256, max_radius=256, min_distance=999):
    # Convert to grayscale if necessary
    if image.ndim == 3:
        gray_image = color.rgb2gray(image)
    else:
        gray_image = image

    # Apply Gaussian blur to reduce noise
    blurred = ndi.gaussian_filter(gray_image, sigma=2)

    # Edge detection with lower threshold for dotted circles
    edges = feature.canny(blurred, sigma=1, low_threshold=0, high_threshold=0)

    # Dilate edges to connect nearby dots
    dilated_edges = ndi.binary_dilation(edges)
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(dilated_edges, cmap=plt.cm.gray)
    # Detect circles
    hough_radii = np.arange(min_radius, max_radius, 1)
    hough_res = transform.hough_circle(dilated_edges, hough_radii)

    # Select circles
    accums, cx, cy, radii = transform.hough_circle_peaks(hough_res, hough_radii,
                                                         total_num_peaks=24,
                                                         min_xdistance=min_distance,
                                                         min_ydistance=min_distance)
    return cx, cy, radii


def main():
    # Load the image
    image_path = "data/reference/S000F00T00VAL.tiff"
    image = io.imread(image_path)

    # Check if the image has 4 channels (RGBA) and convert to RGB if necessary
    if image.shape[-1] == 4:
        image = color.rgba2rgb(image)


    # set top 100 and bottom 100 pixels to black
    # image[:100, :] = 0
    # image[-100:, :] = 0

    # Detect circles
    cx, cy, radii = detect_circles(image)

    # Visualize results
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(image, cmap=plt.cm.gray)

    for center_y, center_x, radius in zip(cy, cx, radii):
        circy, circx = draw.circle_perimeter(center_y, center_x, radius, shape=image.shape)
        ax.plot(circx, circy, 'r-')

        # Print center coordinates
        print(f"Circle center: ({center_x}, {center_y})")

        # Add text annotation on the image
        ax.text(center_x, center_y, f'({center_x}, {center_y})',
                color='white', fontsize=8, ha='center', va='center')

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
