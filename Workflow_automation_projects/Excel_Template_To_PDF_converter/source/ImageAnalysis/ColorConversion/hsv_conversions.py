import numpy as np
from numba import njit
from . import sRGB_conversions


def hsv_to_sRGB(image_array: np.ndarray) -> np.ndarray:
    """converts from hsv to sRGB 0-1

    :param image_array: hsv image in 0-1
    :type image_array: ndarray
    :return: sRGB image with gamma
    :rtype: ndarray
    """
    sRGB_image = image_array.copy()
    sRGB_image = __hsv_to_rgb(sRGB_image)
    # add gamma
    sRGB_image = sRGB_conversions.sRGB_add_gamma(sRGB_image).clip(0, 1)
    return sRGB_image


@njit(fastmath=True)
def __hsv_to_rgb(image_array: np.ndarray) -> np.ndarray:
    """converts from hsv to rgb 0-1

    :param image_array: image as hsv in 0-1
    :type image_array: ndarray
    :return: image as rgb
    :rtype: ndarray
    """
    for index in np.ndindex(image_array.shape[:2]):
        # HSV from 0 to 360 degree
        H = image_array[index][0]
        S = image_array[index][1]
        V = image_array[index][2]
        C = V * S
        X = C * (1 - np.absolute((H/60) % 2 - 1))
        m = V - C
        pre_r_g_b = (None, None, None)
        if 0 <= H < 60:
            pre_r_g_b = (C, X, 0)
        elif 60 <= H < 120:
            pre_r_g_b = (X, C, 0)
        elif 120 <= H < 180:
            pre_r_g_b = (0, C, X)
        elif 180 <= H < 240:
            pre_r_g_b = (0, X, C)
        elif 240 <= H < 300:
            pre_r_g_b = (X, 0, C)
        elif 300 <= H < 360:
            pre_r_g_b = (C, 0, X)
        else:
            raise ValueError("H out of range should be 0-360")
        # r value
        image_array[index][0] = (pre_r_g_b[0] + m)
        # g  value
        image_array[index][1] = (pre_r_g_b[1] + m)
        # b value
        image_array[index][2] = (pre_r_g_b[2] + m)
    return image_array
