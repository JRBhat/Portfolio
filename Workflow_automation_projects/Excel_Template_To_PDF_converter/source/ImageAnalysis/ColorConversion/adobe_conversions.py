from numba import njit
import numpy as np
from . import XYZ_conversions
from . import sRGB_conversions
from . import rgb_conversions
from . import helper_functions

# inverse of XYZToAdobeMatrixArray
adobe_to_XYZ_Array = np.array([[0.5767, 0.2973, 0.0270],
                               [0.1856, 0.6274, 0.0707],
                               [0.1882, 0.0753, 0.9911]], dtype=np.float32)


def adobe_to_xyz(in_data_numpy: np.ndarray) -> np.ndarray:
    """converts an array from adobe RGB to XYZ, also rescales from 0-1 and removes gamma

    :param inData_numpy: array to convert in 0-1
    :type inData_numpy: ndarray
    :param whitePointRef: standard illumination conditions, defaults to whitePointD65
    :type whitePointRef: tupel, optional
    :return: converted array
    :rtype: ndarray
    WARNING: Check before converting to adobeRGB to sRGB!!!!
    """
    xyz_image = in_data_numpy.copy()
    shape = xyz_image.shape
    xyz_image = helper_functions.convert_0_to_1(xyz_image)
    # remove gamma
    xyz_image = __adobe_gamma_remove(xyz_image).clip(0, 1)
    # reshape for matrix mult
    xyz_image = xyz_image.reshape((shape[0] * shape[1], shape[2]))
    # convert to xyz
    xyz_image = __adobe_to_xyz_matrix_mult(xyz_image)
    # reshape in original form
    return xyz_image.reshape(shape)


def adobe_to_hsv(inData_numpy: np.ndarray) -> np.ndarray:
    """converts an array from adobe RGB to HSV colorspace

    :param inData_numpy: numpy array to convert in 0-1
    :type inData_numpy: ndarray
    :return: array in HSV colorspace
    :rtype: ndarray
    WARNING: Check before converting to adobeRGB to sRGB!!!!
    """
    hsv_image = inData_numpy.copy()
    hsv_image = helper_functions.convert_0_to_1(hsv_image)
    hsv_image = __adobe_gamma_remove(hsv_image).clip(0, 1)
    return rgb_conversions.convert_RGB_to_HSV(hsv_image)


def adobe_to_norm_sRGB(in_data_numpy: np.ndarray) -> np.ndarray:
    """converts an array from adobe RGB to norm sRGB 0-1

    :param inData_numpy: image as numpy array in 0-1
    :type inData_numpy: ndarray
    :return: image in sRGB
    :rtype: ndarray
    WARNING: Check before converting to adobeRGB to sRGB!!!!
    """
    xyz = adobe_to_xyz(in_data_numpy.copy())
    return sRGB_conversions.sRGB_remove_gamma(XYZ_conversions.xyz_to_sRGB(xyz))


def adobe_to_sRGB(in_data_numpy: np.ndarray) -> np.ndarray:
    """converts an array from adobe RGB to sRGB colorspace

    :param inData_numpy: array to convert in 0-1
    :type inData_numpy: ndarray
    :param whitePointRef: standard illumination conditions, defaults to whitePointD65
    :type whitePointRef: tupel, optional
    :return: converted array
    :rtype: ndarray
    WARNING: Check before converting to adobeRGB to sRGB!!!!
    """
    # convert to norm sRGB, copy image,  removes gamma and rescales
    in_data_numpy = adobe_to_norm_sRGB(in_data_numpy)
    # add gamma
    in_data_numpy = sRGB_conversions.sRGB_add_gamma(in_data_numpy).clip(0, 1)
    return in_data_numpy


def adobe_to_lab(indata_numpy: np.ndarray) -> np.ndarray:
    """converts an array from adobe RGB to CIELAB

    :param indata_numpy: image as numpy array in 0-1
    :type indata_numpy: ndarray
    :return: array in CIELAB
    :rtype: ndarray
    WARNING: Check before converting to adobeRGB to sRGB!!!!
    """
    # removes ,copy, gamma remove and rescales here
    xyz = adobe_to_xyz(indata_numpy)
    lab_image = XYZ_conversions.xyz_to_lab(xyz)
    return lab_image


def __adobe_gamma_remove(image: np.ndarray) -> np.ndarray:
    """removes adobe gamma from image, njit boosted

    :param image: image in 0-1
    :type image: ndarray
    :return: image without gamma
    :rtype: ndarray
    WARNING: Check before converting to adobeRGB to sRGB!!!!
    """
    return np.power(image, 563/256)


@njit(fastmath=True)
def adobe_add_gamma(image: np.ndarray) -> np.ndarray:
    """adds adobe gamma to image, inverse from add remove

    :param image: image in 0-1
    :type image: ndarray
    :return: image without gamma
    :rtype: ndarray
    WARNING: Check before converting to adobeRGB to sRGB!!!!
    """
    return np.power(image, 256/563)


@njit(fastmath=True)
def __adobe_to_xyz_matrix_mult(image: np.ndarray):
    """converts adobe to XYZ, njit boosted

    :param image: image in 0-1
    :type image:  ndarray
    WARNING: Check before converting to adobeRGB to sRGB!!!!
    """
    return image.astype(np.float32).dot(adobe_to_XYZ_Array)
