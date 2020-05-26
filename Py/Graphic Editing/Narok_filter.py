"""
File: Narok_filter.py
----------------
This program implements a Narok image filter.
"""

from simpleimage import SimpleImage

DEFAULT_FILE = 'images/quad.jpg'
THRESHOLD = 0.6

def main():
    # Get file and load image
    filename = get_file()
    image = SimpleImage(filename)

    # Show the image before the transform
    image.show()

    # Apply the filter

    for pixel in image:
        pixel_average = (pixel.red + pixel.blue + pixel.green) // 3
        if pixel_average > (255 * THRESHOLD):
            pixel.red = pixel_average
            pixel.blue = pixel_average
            pixel.green = pixel_average
    # Show the image after the transform
    image.show()


def get_file():
    # Read image file path from user, or use the default file
    filename = input('Enter image file (or press enter for default): ')
    if filename == '':
        filename = DEFAULT_FILE
    return filename


if __name__ == '__main__':
    main()