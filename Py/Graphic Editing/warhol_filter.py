"""
This program generates the Warhol effect based on the original image.
"""

from simpleimage import SimpleImage

N_ROWS = 2
N_COLS = 3
PATCH_SIZE = 222
WIDTH = N_COLS * PATCH_SIZE
HEIGHT = N_ROWS * PATCH_SIZE
PATCH_NAME = 'images/simba-sq.jpg'

def main():
    '''
    Program takes in an image and passes it into the make_recolored_patch() function, which in turn recolors the original
    by tweaking the RGB values of each pixel according to the values specified as arguments.
    The function then returns the recolored image places it into the canvas.This is repeated six times until the canvas is
    populated with six images with different filters according to the warhol effect.
    '''
    final_image = SimpleImage.blank(WIDTH, HEIGHT)
    # This is an example which should generate a pinkish patch / Patch location: top-left
    patch_1 = make_recolored_patch(1.5, 0, 1.5)
    for y in range(patch_1.height):
        for x in range(patch_1.width):
            pix = patch_1.get_pixel(x, y)
            final_image.set_pixel(x, y, pix)

    patch_2 = make_recolored_patch(1.2, 0.3, 0.5) #Patch location: top-center
    for y in range(patch_2.height):
        for x in range(patch_2.width):
            pix = patch_2.get_pixel(x, y)
            final_image.set_pixel(x + patch_2.width, y, pix)

    patch_3 = make_recolored_patch(0, 2, 0.1)#Patch location: top-right
    for y in range(patch_3.height):
        for x in range(patch_3.width):
            pix = patch_3.get_pixel(x, y)
            final_image.set_pixel(x + 2*patch_3.width, y, pix)

    patch_4 = make_recolored_patch(1.1, 0, 3)#Patch location: bottom-left
    for y in range(patch_4.height):
        for x in range(patch_4.width):
            pix = patch_4.get_pixel(x, y)
            final_image.set_pixel(x, y + patch_4.height, pix)

    patch_5 = make_recolored_patch(1.5, 2, 0)#Patch location: bottom-center
    for y in range(patch_5.height):
        for x in range(patch_5.width):
            pix = patch_5.get_pixel(x, y)
            final_image.set_pixel(x + patch_5.width, y + patch_5.height, pix)

    patch_6 = make_recolored_patch(1, 0.1, 0)#Patch location: bottom-right
    for y in range(patch_6.height):
        for x in range(patch_6.width):
            pix = patch_6.get_pixel(x, y)
            final_image.set_pixel(x + 2*patch_6.width, y + patch_6.height, pix)

    final_image.show()

def make_recolored_patch(red_scale, green_scale, blue_scale):
    '''
    Implement this function to make a patch for the Warhol Filter. It
    loads the patch image and recolors it.
    :param red_scale: A number to multiply each pixels' red component by
    :param green_scale: A number to multiply each pixels' green component by
    :param blue_scale: A number to multiply each pixels' blue component by
    :return: the newly generated patch
    '''
    patch = SimpleImage(PATCH_NAME)
    for pixel in patch:
        R = pixel.red
        G = pixel.green
        B = pixel.blue
        pixel.red = R * red_scale
        pixel.green = G * green_scale
        pixel.blue = B * blue_scale
    return patch

if __name__ == '__main__':
    main()