import numpy as np
from numba import njit


@njit(fastmath=True)
def rgb_to_gray_image(img: np.ndarray) -> np.ndarray:
    """transforms rgb to gray image

    :param img: image in 0-1
    :type img: ndarray
    :return: image in gray
    :rtype: ndarray
    """
    intype = img.dtype
    img = img.astype(np.float32)
    new_img = None
    if len(img.shape) == 3:
        new_img = img.astype(np.float32)
        new_img = (0.21 * new_img[:, :, 0] + 0.72 *
                   new_img[:, :, 1] + 0.07 * new_img[:, :, 2])
    # if else needed for numba
    if new_img is not None:
        img = new_img
    return new_img


@njit(fastmath=True)
def convert_RGB_to_HSV(image_array: np.ndarray) -> np.ndarray:
    """converts an image from RGB to HSV colorspace, expects 0-1 values

    :param image_array: image in in 0-1
    :type image_array: ndarray
    :return: image in HSV colorspace
    :rtype: ndarray
    """
    new_image = np.zeros_like(image_array)
    # iterate over each pixel
    for index in np.ndindex(image_array.shape[:2]):
        c_min = np.min(image_array[index])
        c_max = np.max(image_array[index])
        delta = c_max - c_min  # chroma
        if delta != 0:
            # get R/G/B
            r_value = image_array[index][0]
            g_value = image_array[index][1]
            b_value = image_array[index][2]
            # calc and set H Value
            if c_max == r_value:
                new_image[index][0] = np.mod(
                    60 * (g_value - b_value) / delta, 360)
            elif c_max == g_value:
                new_image[index][0] = 60 * (b_value - r_value) / delta + 120
            elif c_max == b_value:
                new_image[index][0] = 60 * (r_value - g_value) / delta + 240
        # calc and set V value
        new_image[index][2] = c_max
        # calc and set S value
        if c_max != 0:
            new_image[index][1] = delta / c_max
    return new_image
