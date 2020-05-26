"""
File: TrimcropExplained.py
----------------
Takes an image. Generate a new image with a specified portion of the image trimmed off.
"""


# The line below imports SimpleImage for use here
# Its depends on the Pillow package being installed
from simpleimage import SimpleImage


def trim_crop_image(filename, trim_size):
    image = SimpleImage(filename)
    width = image.width
    height = image.height

    canvas_width = width - (2*trim_size)
    canvas_height = height - (2*trim_size)
    trimmed = SimpleImage.blank(canvas_width, canvas_height)

    for y in range(trim_size, height - trim_size):
        for x in range(trim_size, width - trim_size):
            pixel = image.get_pixel(x, y)
            trimmed.set_pixel(x - trim_size, y - trim_size, pixel)
    return trimmed

def main():
    """
    This program tests your highlight_fires function by displaying
    the original image of a fire as well as the resulting image
    from your highlight_fires function.
    """
    original = SimpleImage('images/simba-sq.jpg')
    original.show()
    trimmed_image = trim_crop_image('images/simba-sq.jpg', 30)
    trimmed_image.show()


if __name__ == '__main__':
    main()
