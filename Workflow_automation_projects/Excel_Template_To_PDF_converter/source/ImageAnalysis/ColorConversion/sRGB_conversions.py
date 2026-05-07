import numpy as np
from numba import njit
from . import helper_functions
from . import XYZ_conversions
from . import rgb_conversions

# inverse of XYZTosRGBArray
sRGB_to_XYZ_array = np.array([[0.41239557, 0.21258622, 0.01929721],
                              [0.3575834, 0.7151703, 0.11918385],
                              [0.18049261, 0.07220048, 0.95049703]]).astype(np.float32)


def sRGB_to_norm_sRGB(image: np.ndarray) -> np.ndarray:
    """"converts sRGB to norm sRGB by removing gamma, return norm sRGB 0-1, uint8

    :param image: sRGB image  to convert
    :type image: ndarray
    :return: norm sRGB image
    :rtype: ndarray
    """
    srgb_image = image.copy()
    srgb_image = helper_functions.convert_0_to_1(srgb_image)
    srgb_image = sRGB_remove_gamma(srgb_image).clip(0, 1)
    return srgb_image


def sRGB_to_hsv(image: np.ndarray) -> np.ndarray:
    """converts an array from sRGB to HSV colorspace

    :param image: image to convert 
    :type image: ndarray
    :return: array in HSV colorspace
    :rtype: ndarray
    """
    hsv_image = image.copy()
    hsv_image = helper_functions.convert_0_to_1(hsv_image)
    hsv_image = sRGB_remove_gamma(hsv_image).clip(0, 1)
    return rgb_conversions.convert_RGB_to_HSV(hsv_image)


def sRGB_to_xyz(image_numpy: np.ndarray) -> np.ndarray:
    """converts an array from sRGB colorspace to XYZ

    :param image_numpy: image to convert
    :type image_numpy: ndarray
    :return: converted array
    :rtype: ndarray
    """
    xyz_image = image_numpy.copy()
    xyz_image = helper_functions.convert_0_to_1(xyz_image)
    xyz_image = sRGB_remove_gamma(xyz_image).clip(0, 1)
    return __sRGB_to_xyz_mat_mult(xyz_image)


def sRGB_to_lab(image_numpy: np.ndarray) -> np.ndarray:
    """converts an array from sRGB to CIELAB colorspace

    :param image_numpy: image in 0-1 to convert
    :type image_numpy: ndarray
    :return: converted array
    :rtype: ndarray
    """
    # transform to xyz (copy, remove gamma)
    lab_image = sRGB_to_xyz(image_numpy)
    # convert to lab
    return XYZ_conversions.xyz_to_lab(lab_image)


def sRGB_to_adobe(image_numpy: np.ndarray) -> np.ndarray:
    """converts an array from sRGB to AdobeRGB

    :param image_numpy: image in 0-1 to convert
    :type image_numpy: ndarray
    :return: converted array
    :rtype: ndarray
    """
    # transform to xyz (copy, remove gamma)
    xyz = sRGB_to_xyz(image_numpy)
    # convert to adobe rgb
    return XYZ_conversions.xyz_to_adobeRGB(xyz)


@njit(fastmath=True)
def sRGB_add_gamma(image: np.ndarray) -> np.ndarray:
    """adds gamma to sRGB image, njit boosted

    :param image: image in 0-1
    :type image: ndarray
    :return: image with gamma
    :rtype: ndarray
    """
    x_out = np.zeros_like(image)
    for indexes, data in np.ndenumerate(image):
        if data <= 0.0031308:
            x_out[indexes] = data * 12.92
        if data > 0.0031308:
            x_out[indexes] = (1 + 0.055) * \
                np.power(np.float32(image[indexes]), 1.0 / 2.4) - 0.055
    return x_out


@njit(fastmath=True)
def sRGB_remove_gamma(image: np.ndarray) -> np.ndarray:
    """removes gamma from sRGB image, njit boosted

    :param image: image in 0-1
    :type image: ndarray
    :return: image without gamma
    :rtype: ndarray
    """
    x_out = np.zeros_like(image)
    for indexes, data in np.ndenumerate(image):
        if data <= 0.04045:
            x_out[indexes] = data / 12.92
        if data > 0.04045:
            x_out[indexes] = np.power(
                np.float32(image[indexes] + 0.055) / 1.055, 2.4)
    return x_out


@njit(fastmath=True)
def __sRGB_to_xyz_mat_mult(image: np.ndarray) -> np.ndarray:
    """converts sRGB to XYZ format, njit boosted

    :param image: image in 0-1 to convert
    :type image: ndarray
    :return: converted image
    :rtype: ndarray
    """
    image_shape = image.shape
    image = image.reshape(image_shape[0] * image_shape[1], 3)
    return image.astype(np.float32).dot(sRGB_to_XYZ_array).reshape((image_shape[0], image_shape[1], 3))
