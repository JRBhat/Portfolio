"""
File: border.py
----------------
Takes an image. Generate a new image with a specified pixels thickness border around it.
"""

# The line below imports SimpleImage for use here
# Its depends on the Pillow package being installed
from simpleimage import SimpleImage


def set_border(filename, border_size):
    image = SimpleImage(filename)
    width = image.width
    height = image.height

    canvas_width = width + (2*border_size)
    canvas_height = height + (2*border_size)
    bordered = SimpleImage.blank(canvas_width, canvas_height)

    for y in range(canvas_height):
        for x in range(canvas_width):
            canv_pixel = bordered.get_pixel(x, y)
            #pink border
            canv_pixel.red = 240
            canv_pixel.blue = 150
            canv_pixel.green = 150
            '''
            For a black border
            canv_pixel.red = 0
            canv_pixel.blue = 0
            canv_pixel.green = 0
            '''
            bordered.set_pixel(x, y, canv_pixel)

    for y in range(height):
        for x in range(width):
            pixel = image.get_pixel(x,y)
            bordered.set_pixel(x+border_size, y+border_size, pixel)
    return bordered


def main():
    """
    This program tests your set_border() function by displaying
    the original image  as well as the resulting bordered image
    from your set_border() function.
    """
    original = SimpleImage('images/simba-sq.jpg')
    original.show()
    bordered_image = set_border('images/simba-sq.jpg', 30)
    bordered_image.show()


if __name__ == '__main__':
    main()
