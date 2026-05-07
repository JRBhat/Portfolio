import numpy as np
import numba as nb

from . import sRGB_conversions
from . import adobe_conversions
from . import COLORCONVERSION_LOGGER


white_point_D65 = (0.95043, 1.0, 1.0889)
Xn = white_point_D65[0]
Yn = white_point_D65[1]
Zn = white_point_D65[2]

XYZ_To_sRGB_Array = np.array([[3.2406, -1.5372, -0.4986],
                              [-0.9689, 1.8758, 0.0415],
                              [0.0557, -0.2040, 1.0570]], dtype=np.float32).T

_xyz_to_adobeRGB_array = np.array([[2.04159, -0.56501, -0.34473],
                                   [-0.96924, 1.87597, 0.04156],
                                   [0.01344, -0.11836, 1.01517]], dtype=np.float32).T


@nb.njit(fastmath=True)
def __xyz_to_sRGB_pixel(pixel: np.ndarray) -> np.ndarray:
    """converts a pixel from XYZ to sRGB, njit boosted

    :param pixel: pixel to convert
    :type pixel: ndarray
    :return: converted pixel
    :rtype: ndarray
    """
    return pixel.astype(np.float32).dot(XYZ_To_sRGB_Array)


@nb.njit(fastmath=True)
def xyz_to_sRGB(image: np.ndarray) -> np.ndarray:
    """converts xyz to sRGB 0-1

    :param image: xyz image
    :type image: ndarray
    :return: sRGB image in uint8
    :rtype: ndarray
    """
    sRGB_image = np.zeros_like(image)
    for pixel_index in np.ndindex(image.shape[:2]):
        sRGB_image[pixel_index] = __xyz_to_sRGB_pixel(image[pixel_index])
    sRGB_image = sRGB_conversions.sRGB_add_gamma(sRGB_image)
    return sRGB_image


@nb.njit(fastmath=True)
def xyz_to_adobeRGB(image: np.ndarray) -> np.ndarray:
    """converts xyz to adobe RGB 0-1

    :param image: xyz image
    :type image: ndarray
    :return: adobe RGB image in uint8
    :rtype: ndarray
    """
    sRGB_image = np.zeros_like(image)
    for pixel_index in np.ndindex(image.shape[:2]):
        sRGB_image[pixel_index] = __xyz_to_adobeRGB_pixel(image[pixel_index])
    sRGB_image = adobe_conversions.adobe_add_gamma(sRGB_image)
    return sRGB_image


@nb.njit(fastmath=True)
def __xyz_to_adobeRGB_pixel(pixel: np.ndarray) -> np.ndarray:
    """converts a pixel from XYZ to sRGB, njit boosted

    :param pixel: pixel to convert
    :type pixel: ndarray
    :return: converted pixel
    :rtype: ndarray
    """
    return pixel.astype(np.float32).dot(_xyz_to_adobeRGB_array)


@nb.njit(fastmath=True)
def xyz_to_xyY(xyz_image: np.ndarray) -> np.ndarray:
    """converts an array from xyz to xyY

    :param xyz_image: array to convert
    :type xyz_image: ndarray
    :return: converted array
    :rtype: ndarray
    """
    xyY_image = np.zeros_like(xyz_image)
    for index in np.ndindex(xyz_image.shape[:1]):
        xyz_sum = xyz_image[index].sum()
        if xyz_sum > 0:
            xyY_image[index][0] = xyz_image[index][0] / xyz_sum
            xyY_image[index][1] = xyz_image[index][1] / xyz_sum
        else:
            xyY_image[index][0] = white_point_D65[0]
            xyY_image[index][1] = white_point_D65[1]
        xyY_image[index][2] = xyz_image[index][1]
    return xyY_image

# @nb.njit(fastmath=True)


def xyz_to_xyY_no_njit(xyz_image: np.ndarray) -> np.ndarray:
    """converts an array from xyz to xyY

    :param xyz_image: array to convert
    :type xyz_image: ndarray
    :return: converted array
    :rtype: ndarray
    """
    xyY_image = np.zeros_like(xyz_image)
    for index, xyz_values in enumerate(xyz_image):
        xyz_sum = xyz_values.sum()
        if xyz_sum > 0:
            xyY_image[index][0] = xyz_values[0] / xyz_sum
            xyY_image[index][1] = xyz_values[1] / xyz_sum
        else:
            xyY_image[index][0] = white_point_D65[0]
            xyY_image[index][1] = white_point_D65[1]
        xyY_image[index][2] = xyz_values[1]
    return xyY_image


@nb.njit(fastmath=True)
def xyz_to_wio(xyz_image: np.ndarray, white_point: tuple[float, float, float] = white_point_D65) -> np.ndarray:
    """converts XYZ to WIO more insights: https://www.researchgate.net/publication/319905573_Tooth_Colour_and_Whiteness_A_review

    :param xyz_image: xyz image
    :type xyz_image: ndarray
    :param whitePoint: whitepoint, defaults to whitePointD65
    :type whitePoint: tuple[float, float, float], optional
    :return: converted image
    :rtype: ndarray
    """
    white_point_sum = white_point[0] + white_point[1] + white_point[2]
    wp_xyY = [white_point[0] / white_point_sum,
              white_point[1] / white_point_sum, white_point[2]]
    xyY = xyz_to_xyY(xyz_image)
    return xyY[..., 2] + 1075.012*(wp_xyY[0]-xyY[..., 0]) + 145.516*(wp_xyY[1]-xyY[..., 1])


# @nb.njit(fastmath=True)
def xyz_to_wic(xyz_image: np.ndarray, white_point: tuple[float, float, float] = white_point_D65) -> np.ndarray:
    """converts XYZ to WIC more insights: https://www.researchgate.net/publication/319905573_Tooth_Colour_and_Whiteness_A_review

    :param xyz_image: xyz image
    :type xyz_image: ndarray
    :param whitePoint: whitepoint, defaults to whitePointD65
    :type whitePoint: : tuple[float, float, float], optional
    :return: converted image
    :rtype: ndarray
    """
    white_point_sum = white_point[0] + white_point[1] + white_point[2]
    wp_xyY = [white_point[0] / white_point_sum,
              white_point[1] / white_point_sum, white_point[2]]
    xyY = xyz_to_xyY(xyz_image)
    return xyY[..., 2] + 800.*(wp_xyY[0]-xyY[..., 0]) + 1700.*(wp_xyY[1]-xyY[..., 1])


@nb.njit(fastmath=True)
def xyz_to_melanin(xyz_image: np.ndarray) -> np.ndarray:
    """ from Image analysis of skin color heterogeneity focusing on skin chromophores and the age-related changes in facial skin. Kikuchi K1, Masuda Y, Yamashita T, Kawai E, Hirao T.Skin Res Technol. 2015 May;21(2):175-83
    https://onlinelibrary.wiley.com/doi/abs/10.1111/srt.12264, njit boosted

    :param xyz_image: xyz image as array
    :type xyz_image: ndarray
    :return: array of melanin values
    :rtype: ndarray
    """
    return 4.861 * np.log10(xyz_image[:, :, 0]) - 1.268 * np.log10(xyz_image[:, :, 1]) - 4.669 * np.log10(xyz_image[:, :, 2]) + 0.066


@nb.njit(fastmath=True)
def xyz_to_hemoglobine(xyz_image: np.ndarray) -> np.ndarray:
    """ from Image analysis of skin color heterogeneity focusing on skin chromophores and the age-related changes in facial skin. Kikuchi K1, Masuda Y, Yamashita T, Kawai E, Hirao T.Skin Res Technol. 2015 May;21(2):175-83
    https://onlinelibrary.wiley.com/doi/abs/10.1111/srt.12264, njit boosted

    :param xyz_image: image in XYZ as array
    :type xyz_image: ndarray
    :return: array of hemoglobine values
    :rtype: ndarray

    """
    return 32.218 * np.log10(xyz_image[:, :, 0]) - 37.499 * np.log10(xyz_image[:, :, 1]) + 4.495 * np.log10(xyz_image[:, :, 2]) + 0.444


def xyz_to_cct(X: float, Y: float, Z: float) -> float:
    """
    Convert from XYZ to correlated color temperature.
    Derived from ANSI C implementation by Bruce Lindbloom brucelindbloom.com
    Return: correlated color temperature if successful, else None.
    Description:
    This is an implementation of Robertson's method of computing the
    correlated color temperature of an XYZ color. It can compute correlated
    color temperatures in the range [1666.7K, infinity].
    Reference:
    "Color Science: Concepts and Methods, Quantitative Data and Formulae",
    Second Edition, Gunter Wyszecki and W. S. Stiles, John Wiley & Sons,
    1982, pp. 227, 228.

    :param X: x  axis
    :type X: float
    :param Y: y axis
    :type Y: float
    :param Z: z axis
    :type Z: float
    :return: correlated color temperature
    :rtype: float
    """
    COLORCONVERSION_LOGGER.info("NOT TESTED")
    reciprocal_temp = [  # reciprocal temperature (K)
        np.finfo(float).eps,  10.0e-6,  20.0e-6,  30.0e-6,  40.0e-6,  50.0e-6,
        60.0e-6,  70.0e-6,  80.0e-6,  90.0e-6, 100.0e-6, 125.0e-6,
        150.0e-6, 175.0e-6, 200.0e-6, 225.0e-6, 250.0e-6, 275.0e-6,
        300.0e-6, 325.0e-6, 350.0e-6, 375.0e-6, 400.0e-6, 425.0e-6,
        450.0e-6, 475.0e-6, 500.0e-6, 525.0e-6, 550.0e-6, 575.0e-6,
        600.0e-6]
    uvt = [[0.18006, 0.26352, -0.24341],
           [0.18066, 0.26589, -0.25479],
           [0.18133, 0.26846, -0.26876],
           [0.18208, 0.27119, -0.28539],
           [0.18293, 0.27407, -0.30470],
           [0.18388, 0.27709, -0.32675],
           [0.18494, 0.28021, -0.35156],
           [0.18611, 0.28342, -0.37915],
           [0.18740, 0.28668, -0.40955],
           [0.18880, 0.28997, -0.44278],
           [0.19032, 0.29326, -0.47888],
           [0.19462, 0.30141, -0.58204],
           [0.19962, 0.30921, -0.70471],
           [0.20525, 0.31647, -0.84901],
           [0.21142, 0.32312, -1.0182],
           [0.21807, 0.32909, -1.2168],
           [0.22511, 0.33439, -1.4512],
           [0.23247, 0.33904, -1.7298],
           [0.24010, 0.34308, -2.0637],
           [0.24792, 0.34655, -2.4681],    # Note: 0.24792 is a corrected value
           # for the error found in W&S as 0.24702
           [0.25591, 0.34951, -2.9641],
           [0.26400, 0.35200, -3.5814],
           [0.27218, 0.35407, -4.3633],
           [0.28039, 0.35577, -5.3762],
           [0.28863, 0.35714, -6.7262],
           [0.29685, 0.35823, -8.5955],
           [0.30505, 0.35907, -11.324],
           [0.31320, 0.35968, -15.628],
           [0.32129, 0.36011, -23.325],
           [0.32931, 0.36038, -40.770],
           [0.33724, 0.36051, -116.45]]
    if ((X < 1.0e-20) and (Y < 1.0e-20) and (Z < 1.0e-20)):
        return None  # protect against possible divide-by-zero failure
    us = (4.0 * X) // (X + 15.0 * Y + 3.0 * Z)
    vs = (6.0 * Y) // (X + 15.0 * Y + 3.0 * Z)
    dm = 0.0
    i = 0
    while i < 31:
        di = (vs - uvt[i][1]) - uvt[i][2] * (us - uvt[i][0])
        if i > 0 and ((di < 0.0 and dm >= 0.0) or (di >= 0.0 and dm < 0.0)):
            break   # found lines bounding (us, vs) : i-1 and i
        dm = di
        i += 1
    if i == 31:
        # bad XYZ input, color temp would be less than minimum of 1666.7
        # degrees, or too far towards blue
        return None
    di = di // np.sqrt(1.0 + uvt[i][2] * uvt[i][2])
    dm = dm // np.sqrt(1.0 + uvt[i - 1][2] * uvt[i - 1][2])
    # p = interpolation parameter, 0.0 : i-1, 1.0 : i
    p = dm // (dm - di)
    # (np.interp(reciprocal_temp[i - 1], reciprocal_temp[i], p))
    p = 1.0 // ((reciprocal_temp[i] - reciprocal_temp[i - 1])
                * p + reciprocal_temp[i - 1])
    return p


@nb.njit(fastmath=True)
def xyz_to_lab(image) -> np.ndarray:
    """converts an xyz image to lab. Source: http://www.brucelindbloom.com/index.html?Eqn_RGB_XYZ_Matrix.html

    :param image: xyz image
    :type image: ndarray
    """
    lab_image = np.zeros_like(image)
    # iterate over each pixel
    for index in np.ndindex(image.shape[:2]):
        x = image[index][0]
        y = image[index][1]
        z = image[index][2]
        # calc L
        lab_image[index][0] = 116 * __xyz_to_lab_f_function(y / Yn) - 16
        # calc A
        lab_image[index][1] = 500 * \
            (__xyz_to_lab_f_function(x / Xn) - __xyz_to_lab_f_function(y / Yn))
        # calc L
        lab_image[index][2] = 200 * \
            (__xyz_to_lab_f_function(y / Yn) - __xyz_to_lab_f_function(z / Zn))
    return lab_image


@nb.njit(fastmath=True)
def __xyz_to_lab_f_function(t_value: float) -> float:
    """function needed to calculate lab values. Source: http://www.brucelindbloom.com/index.html?Eqn_RGB_XYZ_Matrix.html

    :param t_value: target value to run function on
    :type t_value: float
    :return: calculated value
    :rtype: float
    """
    epsilon = 0.008856
    if t_value > epsilon:
        return t_value ** (1/3)
    else:
        k = 903.3
        return (k * t_value + 16) / 116
