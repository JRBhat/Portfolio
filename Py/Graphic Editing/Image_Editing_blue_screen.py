"""
File: bluescreen.py
----------------
Not part of the assignment. This was a lecture demo!
This is a fun algorithm to implement. It is not in the
assignment, but feel free to implement it as an extension.
Put the smaller foreground picture into the background.
Do not include any pixels that are sufficiently blue.
"""

from simpleimage import SimpleImage #imports SimpleImage module from simpleimage library instead of 'Simpleimage.SimpleImage()'

INTENSITY_THRESHOLD = 1.6

def main():
    foreground = SimpleImage('images/tiefighter.jpg')
    foreground.show()
    background = SimpleImage('images/quad.jpg')
    background.show()
    image_replaced = bluescreen('images/tiefighter.jpg', 'images/quad.jpg')
    image_replaced.show()

def bluescreen(front_file, back_file):
    image = SimpleImage(front_file)
    back = SimpleImage(back_file)
    for pixel in image:
        average = (pixel.red + pixel.green + pixel.blue) // 3
        #See if this pixel is sufficiently blue
        if pixel.blue >= average * INTENSITY_THRESHOLD:#Checks if pixel is mostly blue i.e. if blue value is more than 1.6 times the average intensity of that pixels
            x = pixel.x
                        #if so, then owerwrite the original image's pixel with the
                        #coressponding pixel from the background image
            y = pixel.y
            image.set_pixel(x, y, back.get_pixel(x,y))
    return image

if __name__ == '__main__':
    main()