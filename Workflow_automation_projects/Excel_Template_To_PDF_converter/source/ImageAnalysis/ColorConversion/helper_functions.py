"""
Helper functions for ColorConversion functions
"""
import os
import subprocess
from io import BytesIO
import cv2
import numpy as np
from PIL import Image, ImageCms
from . import COLORCONVERSION_LOGGER

__version__ = "$Revision: 13366 $"


def __svndata__():
    """
    | $Author: ndrews $
    | $Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $
    | $Rev: 13366 $
    | $URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ColorConversion/helper_functions.py $
    | $Id: helper_functions.py 13366 2022-08-05 13:06:26Z ndrews $
    """
    # only for documentation purpose
    return {
        'author': "$Author: ndrews $".replace('$', '').replace('Author:', '').strip(),
        'date': "$Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $".replace('$', '').replace('Date:', '').strip(),
        'rev': "$Rev: 13366 $".replace('$', '').replace('Rev:', '').strip(),
        'id': "$Id: helper_functions.py 13366 2022-08-05 13:06:26Z ndrews $".replace('$', '').replace('Id:', '').strip(),
        'url': "$URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ColorConversion/helper_functions.py $".replace('$', '').replace('URL:', '').strip()
    }


def get_colorprofile(filename: str) -> tuple[str, str, int]:
    """get the colorprofile

    :param filename: file path
    :type filename: str
    :raises NotImplemented: if image shape is to big ( must <= 3)
    :return: (colorspace definition, color mode ,bpp)
    :rtype: tuple[str, str, int
    """
    pil_image = Image.open(filename)
    cv2_image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    bits = {'uint8': 8, 'uint16': 16, 'uint32': 32}[cv2_image.dtype.name]
    if len(cv2_image.shape) == 3:
        bpp = bits * cv2_image.shape[2]
    elif len(cv2_image.shape) == 2:
        bpp = bits
    else:
        raise NotImplementedError("Image shape > 3")
    return __get_colorprofile_freeimage(pil_image) + (bpp,)


def mode_to_bpp(mode: str) -> int:
    """returns bpp of given mode

    :param mode: mode to get bpp
    :type mode: str
    :return: bpp
    :rtype: int
    """
    return {'1': 1, 'L': 8, 'P': 8, "I;16L": 16, "I;16": 16, 'RGB': 24, 'RGBA': 32, 'CMYK': 32, 'YCbCr': 24, 'I': 32, 'F': 32}[mode]


def __get_colorprofile_freeimage(pil_image: Image) -> tuple[str, str]:
    """gets colorprofile with freeimage

    :param image: Pil image
    :type image: PIL.Image
    :return: (color definition, mode)
    :rtype: tuple[str, str]
    """
    bpp = mode_to_bpp(pil_image.mode)
    try:
        icc = pil_image.info.get('icc_profile')
        bytes_object = BytesIO(icc)
        colorspace_name = ImageCms.ImageCmsProfile(
            bytes_object).profile.profile_description
    except Exception:
        colorspace_name = 'srgb'
    if colorspace_name is None:
        COLORCONVERSION_LOGGER.warning(
            "Colorspace name is None, Image couldn't be read")
    colorspace_definitions = {u'Adobe RGB (1998)': 'adobe',
                              u'sRGB IEC61966-2.1': 'srgb',
                              u"RT_sRGB gamma sRGB(IEC61966 equivalent)": 'srgb',
                              u'Hasselblad RGB': 'hasselrgb',
                              u'RTv4_sRGB': 'srgb',
                              u'RTv2_sRGB': 'srgb',
                              'srgb': 'srgb',
                              u'EPSON  Gray - Gamma 2.2': 'srgb'
                              }
    try:
        colorspace_name_real = colorspace_definitions[colorspace_name]
    except KeyError as exc:
        if 'srgb'.upper() in colorspace_name.upper():
            COLORCONVERSION_LOGGER.warning("Colorspace " + colorspace_name +
                                           " not found; using fallback srgb")
            colorspace_name_real = 'srgb'
        else:
            raise exc
    return colorspace_name_real, pil_image.mode


def convert_0_to_1(img_as_np: np.ndarray) -> np.ndarray:
    """converts from 0-max(img_as_np.dtype) to 0-1

    :param img_as_np: data to convert
    :type img_as_np: ndarray
    :param data_type: data type of new array if None old datatype is used, defaults to None
    :type data_type: str or np.datatype, optional
    :return: img_as_np in range 0-1
    :rtype: ndarray
    """
    ttype = img_as_np.dtype
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
        if img_as_np.max() == 1:
            COLORCONVERSION_LOGGER.warning("Image is binary")
        if not((ttype.type is np.uint8) or (ttype.type is np.uint16)):
            COLORCONVERSION_LOGGER.warning("Type of image is: " + str(ttype.type) +
                                           " may lead to wrong 0-1 conversion")
        img_as_np = (img_as_np.astype(float) /
                     np.iinfo(ttype).max).clip(0, 1)
    if np.any((img_as_np < 0) | (img_as_np > 1)):
        raise ValueError(
            "Values are not between 0-1 after rescaling, image type could be float!")
    return img_as_np


def convert_0_to_255(img_as_np: np.ndarray, data_type: str = "uint8") -> np.ndarray:
    """converts image from 0-1 to 0-max(data_type)

    :param img_as_np: image as numpy array
    :type img_as_np: ndarray
    :param data_type: data type of new array must be uint8 or uint16 is used, defaults to uint8
    :type data_type: str or np.datatype, optional
    :return: returns the image as 0-255 and with the new datatype
    :rtype: ndarray
    """
    # check if subtype float
    if np.issubdtype(img_as_np.dtype, float):
        if (img_as_np > 1).any():
            raise ValueError(
                "Some values are > 1, please clip image before rescaling")
        if (img_as_np < 0).any():
            raise ValueError("Negativ image values are not allowed")
        if data_type == "uint8":
            return convert_to_uint8(img_as_np)
        if data_type == "uint16":
            return convert_to_uint16(img_as_np)
        else:
            raise ValueError(
                "Only conversions to uint8/uint16 are implemented")
    else:
        raise ValueError(
            "Array type %s should not be converted to 0-255" % str(img_as_np.dtype))


def convert_to_uint8(img_as_np: np.ndarray) -> np.ndarray:
    """converts images from 0-1 to uint8 0-255

    :param img_as_np: image as numpy array
    :type img_as_np: ndarray
    :return: image in uint8 0-255
    :rtype: ndarray
    """
    return (img_as_np.clip(0, 1) * np.iinfo(np.uint8).max).round().clip(0, np.iinfo(np.uint8).max).astype(np.uint8)


def convert_to_uint16(img_as_np: np.ndarray) -> np.ndarray:
    """converts images from 0-1 to uint16 0-max(uint16)

    :param img_as_np: image as numpy array
    :type img_as_np: ndarray
    :return: image in uint8 0-255
    :rtype: ndarray
    """
    return (img_as_np.clip(0, 1) * np.iinfo(np.uint16).max).round().clip(0, np.iinfo(np.uint16).max).astype(np.uint16)


def set_colorspace_to_icc(file_path: str, icc_profile_path: str, exiftool_path: str = None) -> None:
    """sets a profile to image

    :param file_path: file path to image to set adobe profile
    :type img_as_np: str
    :param icc_profile_path: absolute path to the icc profile to use for conversion
    :type icc_profile_path: str
    :param exiftool_path: absolute path to the exiftool.exe, defaults to None
    :type exiftool_path: str, optional
    """
    if exiftool_path is None:
        exiftool_path = os.path.join(os.path.dirname(__file__), "exiftool.exe")
    # escape paths to deal with spaces in paths
    subprocess.call("\"%s\" \"-icc_profile<=\"%s\"\" -overwrite_original \"%s\"" %
                    (exiftool_path, icc_profile_path, file_path))


def set_adobe_icc_profile_to_file(file_path: str) -> None:
    """converts an image as numpy array (0-1 or 0-255) to adobe colorspace via .icc file

    :param file_path: path to the file to set icc profile for
    :type file_path: str
    """
    icc_path = os.path.join(os.path.dirname(__file__),
                            "icc_profiles", "AdobeRGB1998.icc")
    set_colorspace_to_icc(file_path, icc_path)
