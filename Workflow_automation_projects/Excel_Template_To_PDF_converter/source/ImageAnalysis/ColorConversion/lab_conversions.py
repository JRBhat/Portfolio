import numpy as np
import numba as nb
from . import XYZ_conversions


@nb.njit(fastmath=True)
def lab_to_xyz(image: np.ndarray) -> np.ndarray:
    """converts lab to xyz

    :param image: lab image in 0-1
    :type image: ndarray
    :return: image in xyz
    :rtype: ndarray
    """
    xyz_image = np.zeros_like(image)
    for index in np.ndindex(image.shape[:2]):
        constant = (image[index][0] + 16)/116
        # calc and set x
        xyz_image[index][0] = XYZ_conversions.Xn * \
            __lab_to_xyz_f_function(constant + image[index][1]/500)
        # calc and set y
        xyz_image[index][1] = XYZ_conversions.Yn * \
            __lab_to_xyz_f_function(constant)
        # calc and set z
        xyz_image[index][2] = XYZ_conversions.Zn * \
            __lab_to_xyz_f_function(constant - image[index][2]/200)
    return xyz_image


@nb.njit(fastmath=True)
def lab_to_srgb(image: np.ndarray) -> np.ndarray:
    """converts lab to srgb 0-1 via xyz

    :param image: lab image 0-1 to convert to srgb
    :type image: ndarray
    :return: image in sRGB
    :rtype: ndarray
    """
    return XYZ_conversions.xyz_to_sRGB(lab_to_xyz(image))


@nb.njit(fastmath=True)
def __lab_to_xyz_f_function(t_value: float) -> float:
    """function needed to calc xyz values

    :param t_value: value
    :type t_value: float
    :return: modified number
    :rtype: float
    """
    delta = 6 / 29
    if t_value > delta:
        return t_value ** 3
    return 3 * delta ** 2 * (t_value - 4/29)
