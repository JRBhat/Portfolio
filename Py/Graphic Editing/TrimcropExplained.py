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
    width = image.width#222
    height = image.height#222

    canvas_width = width - (2*trim_size)#222-60 = 162
    canvas_height = height - (2*trim_size)#162
    trimmed = SimpleImage.blank(canvas_width, canvas_height)#162*162

    for y in range(trim_size, height - trim_size):#(30, 192)
        for x in range(trim_size, width - trim_size):#(30, 192)
                pixel = image.get_pixel(x, y)#(30,30) (31, 30) (191,30)...(30,31) (32, 31) (191,31)...(30, 191) (32, 191) (191,191)
                trimmed.set_pixel(x - trim_size, y - trim_size, pixel)#(0,0) (1, 0) (161, 0)...(0,1) (1, 1) (161, 1)...(0,161) (1, 161) (161, 161)
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
