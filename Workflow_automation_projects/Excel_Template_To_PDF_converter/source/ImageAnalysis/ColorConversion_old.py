# $Id: ColorConversion_old.py 13366 2022-08-05 13:06:26Z ndrews $
"""
Color Conversion definitions and functions
"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from builtins import input
from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div
from PIL import Image, ImageCms
import cv2
import io
import sys
from numba import njit
import numpy
from . import ImageIO as Io
from .cuda import convertToLab
from colormath.color_objects import sRGBColor, XYZColor, AdobeRGBColor, LabColor, HSVColor, xyYColor
from colormath.color_objects import sRGBColor as RGBColor #RGBColor got removed
from colormath.color_conversions import convert_color
import math

__version__ = "$Revision: 13366 $"


def __svndata__():
    """
    | $Author: ndrews $
    | $Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $
    | $Rev: 13366 $
    | $URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ColorConversion_old.py $
    | $Id: ColorConversion_old.py 13366 2022-08-05 13:06:26Z ndrews $
    """
    #only for documentation purpose
    return {
            'author': "$Author: ndrews $".replace('$', '').replace('Author:', '').strip(),
            'date': "$Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $".replace('$', '').replace('Date:', '').strip(),
            'rev': "$Rev: 13366 $".replace('$', '').replace('Rev:', '').strip(),
            'id': "$Id: ColorConversion_old.py 13366 2022-08-05 13:06:26Z ndrews $".replace('$', '').replace('Id:', '').strip(),
            'url': "$URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ColorConversion_old.py $".replace('$', '').replace('URL:', '').strip()
            }

import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
LOGGER.debug("Importing %s, Vs: %s" % (__name__, __svndata__()['id']))

def __imports__():
    """
    Additional imports

    | colormath.color_objects=1.0.8
    | matplotlib.pyplot=1.1.0
    | numpy=1.7.1
    | pycuda(autoinit,compiler,driver,elementwise,gpuarray)=2012.1
    | skimage.io=0.8.2
    | Util=Revision: 5510
    """
    #only for documentation purpose
    pass

import numpy as np
import skimage.io
import os.path

"""
Global Color definition
"""
Xn = 0.95
Yn = 1.0
Zn = 1.09
XYZTosRGBMatrix = np.matrix([[3.2406, -1.5372, -0.4986],[-0.9689, 1.8758, 0.0415],[0.0557, -0.2040, 1.0570]], np.float32).T
XYZToAdobeMatrix = np.matrix([[2.04159, -0.56501, -0.34473],[-0.96924, 1.87597, 0.04156],[0.01344, -0.11836, 1.01517]],np.float32).T
whitePointD65 = (0.95043, 1.0, 1.0889)


def get_colorprofile(filename):
    """get the colorprofile

    :param filename: file path
    :type filename: str
    :raises NotImplemented: if image shape is to big ( must <= 3)
    :return: colorspace definition, color mode ,bpp
    :rtype: tuple
    """
    cc = Image.open(filename)
    cv2_image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    bits = {'uint8': 8, 'uint16': 16, 'uint32': 32}[cv2_image.dtype.name]
    if len(cv2_image.shape) == 3:
        bpp = bits * cv2_image.shape[2]
    elif len(cv2_image.shape) == 2:
        bpp = bits
    else:
        raise NotImplemented("Image shape > 3")
    return get_colorprofile_freeimage(cc) + (bpp,)

def mode_to_bpp(mode):
    """returns bpp of given mode

    :param mode: mode to get bpp
    :type mode: str
    :return: bpp
    :rtype: int
    """
    return {'1':1, 'L':8, 'P':8,"I;16L": 16,"I;16": 16, 'RGB':24, 'RGBA':32, 'CMYK':32, 'YCbCr':24, 'I':32, 'F':32}[mode]

def get_colorprofile_freeimage(cc):
    """gets colorprofile with freeimage

    :param cc: Pil image
    :type cc: Pil image
    :return: color definition and mode
    :rtype: tuple
    """
    bpp = mode_to_bpp(cc.mode)
    try:
        icc = cc.info.get('icc_profile')
        f = io.BytesIO(icc)
        colorspace_name = ImageCms.ImageCmsProfile(f).profile.profile_description
    except Exception:
        colorspace_name = 'srgb'
    if colorspace_name is None:
        LOGGER.warning("Colorspace name is None, Image couldn´t be read")
    colorspace_definitions = {u'Adobe RGB (1998)': 'adobe',
                              u'sRGB IEC61966-2.1': 'srgb',
                              u"RT_sRGB gamma sRGB(IEC61966 equivalent)": 'srgb',
                              u'Hasselblad RGB': 'hasselrgb',
                              u'RTv4_sRGB': 'srgb',
                              u'RTv2_sRGB': 'srgb',
                              'srgb': 'srgb'
                              }
    try:
        colorspace_name_real = colorspace_definitions[colorspace_name]
    except KeyError as exc:
        if 'srgb'.upper() in colorspace_name.upper():
            colorspace_name_real = 'srgb'
        else:
            raise exc
    return colorspace_name_real , cc.mode 



def XYZ2CCT(X, Y, Z):
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
    rt = [# reciprocal temperature (K)
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
        return None # protect against possible divide-by-zero failure
    us = old_div((4.0 * X), (X + 15.0 * Y + 3.0 * Z))
    vs = old_div((6.0 * Y), (X + 15.0 * Y + 3.0 * Z))
    dm = 0.0
    i = 0
    while i < 31:
        di = (vs - uvt[i][1]) - uvt[i][2] * (us - uvt[i][0])
        if i > 0 and ((di < 0.0 and dm >= 0.0) or (di >= 0.0 and dm < 0.0)):
            break   # found lines bounding (us, vs) : i-1 and i
        dm = di
        i += 1
    if (i == 31):
        # bad XYZ input, color temp would be less than minimum of 1666.7
        # degrees, or too far towards blue
        return None
    di = old_div(di, np.sqrt(1.0 + uvt[i][2] * uvt[i][2]))
    dm = old_div(dm, np.sqrt(1.0 + uvt[i - 1][2] * uvt[i - 1][2]))
    p = old_div(dm, (dm - di))  # p = interpolation parameter, 0.0 : i-1, 1.0 : i
    p = 1.0 / (numpy.interp(rt[i - 1], rt[i], p))
    return p

def sRGBgamma(im):
    """applies sRGB gamma (<12.92 linear, pow 2.4)  to image 

    :param im: image
    :type im: MxNx3 numpy array
    :return: image with sRGB gamma
    :rtype: MxNx3 numpy array
    """
    sh = im.shape
    im = im.reshape(sh[0] * sh[1] * sh[2])
    step = 100000
    ll = [0]
    ll.extend(list(range(step,sh[0] * sh[1] * sh[2],step)))
    ll.append(sh[0] * sh[1] * sh[2] + 1)
    for z in range(1,len(ll)):
        tt = im[ll[z - 1]:ll[z]] <= 0.0031308
        np.putmask(im[ll[z - 1]:ll[z]],tt,12.92 * im[ll[z - 1]:ll[z]])
        np.putmask(im[ll[z - 1]:ll[z]],~tt,(1 + 0.055) * np.power(im[ll[z - 1]:ll[z]],1.0 / 2.4) - 0.055)
    im = im.reshape(sh)
    return im


def remSrgbgamma(x):
    """removes sRGB gamma

    :param x: pixel value r/g/b
    :type x: float
    :return: pixel value without gamma
    :rtype: float
    """
    if (x <= 0.0031308):
        return 12.92 * x
    else:
        return (1 + 0.055) * np.power(x,1.0 / 2.4) - 0.055

def matmul(A, B, C):
    """function returns the matrix product of two 2D arrays.

    :param A: first array
    :type A: 2d array
    :param B: second array
    :type B: 2d array
    :param C: array to store matrix product in
    :type C: 2d array
    """
    m, n = A.shape
    n, p = B.shape
    for i in range(m):
        for j in range(p):
            C[i, j] = 0
            for k in range(n):
                C[i, j] += A[i, k] * B[k, j]

def ImageMult(A, B, C):
    """multiplies 3d matrix A with 2d matrix B values and stores values in 2

    :param A: matrix A
    :type A: 3d ndarray
    :param B: matrix B
    :type B: 2d ndarray
    :param C: values stored in C
    :type C: 3d ndarray
    """
    l, m, n = A.shape
    n, p = B.shape
    for ii in range(l):
        for i in range(m):
            for j in range(p):
                C[ii, i, j] = 0
                for k in range(n):
                    C[ii, i, j] += A[ii, i, k] * B[k, j]

def sRGBToXYZImage(im):
    """converts sRGB to XYZ format

    :param im: image to convert
    :type im: ndarray
    :return: converted image
    :rtype: ndarray
    """
    sh = im.shape
    im = im.reshape(sh[0] * sh[1],3)
    im = im * XYZTosRGBMatrix.I
    im = np.array(im).reshape(sh[0],sh[1],3)
    return im

def XYZTosRGBPixel(x):
    """converts a pixel from XYZ to sRGB

    :param x: pixel to convert
    :type x: ndarray
    :return: converted pixel
    :rtype: ndarray
    """
    return np.matrix(x) * XYZTosRGBMatrix

def rgb_to_gray_image(img):
    """transforms rgb to gray image

    :param img: image
    :type img: ndarray
    :return: image in rgb
    :rtype: ndarray
    """
    intype = img.dtype
    if len(img.shape) == 3:
        img = img.astype(np.float32)
        return (0.21 * img[:, :, 0] + 0.72 * img[:, :, 1] + 0.07 * img[:, :, 2]).astype(intype)
    else:
        return img

def convertGrayToRGB(infile, outFile, rescale=False):
    """converts gray to RGB

    :param infile: Image
    :type infile: Image
    :param outFile: converted image
    :type outFile: Image
    :param rescale: rescale, defaults to False
    :type rescale: bool, optional
    """
    try:
        print(infile.shape)
        im = infile
    except:
        im = Io.readGrayscaleImage(infile)
    if len(im.shape) == 2:
        imRGB = np.dstack((im, im, im))
        if rescale:
            Io.writeImage((imRGB.astype(np.double) / im.max()
                       * 255).astype(np.uint8), outFile)
        else:
            if np.iinfo(im.dtype).max > 255:
                Io.writeImage((old_div(imRGB, 256)).astype(np.uint8), outFile)
            else:
                Io.writeImage(imRGB.astype(np.uint8), outFile)
    elif len(im.shape) == 3:
        if rescale:
            Io.writeImage((im.astype(np.double) / im.max()
                       * 255).astype(np.uint8), outFile)
        else:
            if np.iinfo(im.dtype).max > 255:
                Io.writeImage((old_div(im, 256)).astype(np.uint8), outFile)
            else:
                Io.writeImage(im.astype(np.uint8), outFile)

def XYZTosRGBImage(im,outfilename8,outfilenameGamma8,outfilename16,outfilenameGamma16):
    """converts an image from XYZ to sRGB (requires user input to perform) stores data in 8 bit and 16 bit

    :param im: image to convert
    :type im: ndarray
    :param outfilename8: path where to store 8 bit image  
    :type outfilename8: str
    :param outfilenameGamma8: 8bit image with gamma
    :type outfilenameGamma8: str
    :param outfilename16: path where to store 16 bit image
    :type outfilename16: str
    :param outfilenameGamma16: path where to store 16 bit image with gamma
    :type outfilenameGamma16: str
    """
    LOGGER.error("to check")
    input("Press Enter to continue...")
    sh = im.shape
    im = np.matrix(im.reshape(sh[0] * sh[1],3))
    im = np.array(im * XYZTosRGBMatrix * im)
    im = im.reshape(sh[0],sh[1],3)
    im = im.clip(0,1)
    print(im.max(),im.min())
    skimage.io.imsave(outfilename8,(im * 255.0).astype(np.uint8))
    skimage.io.imsave(outfilename16,(im * 65535.0).astype(np.uint8))
    im = sRGBgamma(im)
    skimage.io.imsave(outfilenameGamma8,(im * 255.0).astype(np.uint8))
    skimage.io.imsave(outfilenameGamma16,(im * 65535.0).astype(np.uint16))

@njit
def labSqrt(x):
    """ calculates the lab square

    :param x: l/a/b value
    :type x: ndarray
    :return: lab square
    :rtype: float
    """
    if (x < 0.008856):
        return (24389.0 / 27.0 * x + 16.0) / 116.0
    else:
        return np.power(float(x),1.0 / 3.0)

@njit
def XYZToLAB(xyz):
    """converts an array from xyz to CIELAB colorspace

    :param xyz: xyz format
    :type xyz: ndarray
    :return: CIELAB colorspace
    :rtype: ndarray
    """
    lab = xyz.copy() 
    y = labSqrt(xyz[1]/ Yn)    
    lab[0] = 116.0 * y - 16.0 
    lab[1] = 500 * (labSqrt(xyz[0] / Xn) - y)
    lab[2] = 200 * (y - labSqrt(xyz[2]/ Zn))
    return lab

@njit
def XYZToLabImage(im,outfilename=""):
    """converts an array from xyz to CIELAB colorspace

    :param im: image to convert
    :type im: ndarray
    :param outfilename: unused variable, defaults to ""
    :type outfilename: str, optional
    :return: image in CIELAB colorspace
    :rtype: ndarray
    """
    sh = im.shape
    im = im.reshape(sh[0] * sh[1],3)
    for idx in range(im.shape[0]):
        x = im[idx,:]
        data_out = XYZToLAB(x)
        im[idx,:] = data_out
    im = im.reshape(sh[0],sh[1],3)
    return im


def sRGBToHSVNP(inData_numpy):
    """converts an array from sRGB to HSV colorspace

    :param inData_numpy: numpy array to convert
    :type inData_numpy: ndarray
    :return: array in HSV colorspace
    :rtype: ndarray
    """
    shape = inData_numpy.shape
    ttype = inData_numpy.dtype
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
        inData_numpy = old_div(inData_numpy.astype(np.float32), np.iinfo(ttype).max)
    sz = inData_numpy.shape[0] * inData_numpy.shape[1]
    outData = convert_RGB_to_HSV((inData_numpy.clip(0,1) * 255))
    return outData.reshape(shape)

def adobeRGBToHSVNP(inData_numpy):
    """converts an array from adobe RGB to HSV colorspace

    :param inData_numpy: numpy array to convert
    :type inData_numpy: ndarray
    :return: array in HSV colorspace
    :rtype: ndarray
    """
    shape = inData_numpy.shape
    ttype = inData_numpy.dtype
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
        inData_numpy = old_div(inData_numpy.astype(np.float32), np.iinfo(ttype).max)
    sz = inData_numpy.shape[0] * inData_numpy.shape[1]
    outData = convert_RGB_to_HSV((inData_numpy.clip(0,1) * 255).astype(np.uint8))
    return outData

def convert_RGB_to_HSV(a):
    """converts an array from RGB to HSV colorspace

    :param a: array to convert
    :type a: ndarray
    :return: array in HSV colorspace
    :rtype: ndarray
    """
    R, G, B = a.T
    m = numpy.min(a,2).T
    M = numpy.max(a,2).T
    C = M - m #chroma
    Cmsk = C != 0
    # Hue
    H = numpy.zeros(R.shape, int)
    mask = (M == R) & Cmsk
    H[mask] = numpy.mod(60 * (G - B) / C, 360)[mask]
    mask = (M == G) & Cmsk
    H[mask] = (60 * (B - R) / C + 120)[mask]
    mask = (M == B) & Cmsk
    H[mask] = (60 * (R - G) / C + 240)[mask]
    H = H.astype(float)
    H *= 255
    H /= 360 # if you prefer, leave as 0-360, but don't convert to uint8
    # Value
    V = M
    # Saturation
    S = numpy.zeros(R.shape, int)
    S[Cmsk] = (old_div((255 * C), V))[Cmsk]
    return np.dstack([H.T,S.T,V.T])

@njit
def adobeGammaRemoveNP(x):
    """removes adobe gamma from image

    :param x: image
    :type x: ndarray
    :return: image without gamma
    :rtype: ndarray
    """
    return np.power(x.astype(float), 2.0 + 51.0 / 256.0)

@njit
def adobe_to_xyz(indata_numpy):
    """converts an array from adobe RGB to xyz

    :param indata_numpy: array to convert
    :type indata_numpy: ndarray
    :return: array in xyz
    :rtype: ndarray
    """
    ttype = indata_numpy.dtype
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
        indata_numpy = indata_numpy.astype(np.float32)/ np.iinfo(ttype).max
    sh = indata_numpy.shape
    indata_numpy = indata_numpy.reshape(sh[0] * sh[1], 3)
    indata_numpy = adobeGammaRemoveNP(indata_numpy) * XYZToAdobeMatrix.I
    indata_numpy = np.array(indata_numpy).reshape(sh[0],sh[1],3)
    return indata_numpy

@njit
def adobe_to_lab(indata_numpy):
    """converts an array from adobe RGB to CIELAB

    :param indata_numpy: 
    :type indata_numpy: ndarray
    :return: array in CIELAB
    :rtype: ndarray
    """
    indata_numpy = adobe_to_xyz(indata_numpy)
    labdata = XYZToLabImage(indata_numpy)
    return labdata

def srgbGammaRemoveNP(x):
    """removes gamma from sRGB image

    :param x: image
    :type x: ndarray
    :return: image without gamma
    :rtype: ndarray
    """
    x_out = np.zeros_like(x)
    x_out[x <= 0.04045] = x[x <= 0.04045] / 12.92
    x_out[x > 0.04045] = np.power(((x[x > 0.04045] + 0.055) / 1.055).astype(float),2.4)
    return x_out

@njit
def srgbGammaNP(x):
    """adds gamma to sRGB image

    :param x: image
    :type x: ndarray
    :return: image with gamma
    :rtype: ndarray
    """
    x_out = np.zeros_like(x)
    x_out[x <= 0.0031308] = x[x <= 0.0031308] * 12.92
    x_out[x > 0.0031308] = (1 + 0.055) * np.power(x[x > 0.0031308].astype(float),1.0 / 2.4) - 0.055
    return x_out


def sRGBToXYZNP(inData_numpy):
    """converts an array from sRGB colorspace to XYZ

    :param inData_numpy: array to convert
    :type inData_numpy: ndarray
    :return: converted array
    :rtype: ndarray
    """
    shape = inData_numpy.shape
    ttype = inData_numpy.dtype
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16): #TODO njit issubdtype problem
        inData_numpy = inData_numpy.astype(np.float32) / np.iinfo(ttype).max
    sz = inData_numpy.shape[0] * inData_numpy.shape[1]
    inData_numpy = srgbGammaNP(inData_numpy)
    outData = sRGBToXYZImage(inData_numpy)
    return outData 

def inter_XYZ_to_lab(np_image):
    """converts an array from XYZ to CIELAB colorspace

    :param np_image: array to convert
    :type np_image: ndarray
    :return: converted array
    :rtype: ndarray
    """
    in_shape = np_image.shape
    if len(in_shape) == 3:
        np_image = np_image.reshape([in_shape[0] * in_shape[1],3])
    out_array = [XYZColor(np_image[idx,0], np_image[idx,1], np_image[idx,2], illuminant='D65').convert_to('lab', illuminant='D65').get_value_tuple() for idx in range(np_image.shape[0])]
    return np.array(out_array).reshape(in_shape)

def inter_XYZ_to_srgb(np_image):
    """converts an array from XYZ to sRGB

    :param np_image: array to convert
    :type np_image: ndarray
    :return: converted array in sRGB colorspace
    :rtype: ndarray
    """
    in_shape = np_image.shape
    if len(in_shape) == 3:
        np_image = np_image.reshape([in_shape[0] * in_shape[1],3])
    out_array = [XYZColor(np_image[idx,0], np_image[idx,1], np_image[idx,2], illuminant='D65').convert_to('RGB', target_rgb='srgb', illuminant='D65').get_value_tuple() for idx in range(np_image.shape[0])]
    return np.array(out_array).reshape(in_shape)

def inter_srgb_to_xyz(np_image):
    """converts an array from sRGB colorspace to XYZ

    :param np_image: array to convert
    :type np_image: ndarray
    :return: converted array
    :rtype: ndarray
    """
    in_shape = np_image.shape
    if len(in_shape) == 3:
        np_image = np_image.reshape([in_shape[0] * in_shape[1],3])
    out_array = [RGBColor(np_image[idx,0], np_image[idx,1], np_image[idx,2], illuminant='D65').convert_to('xyz', illuminant='D65').get_value_tuple() for idx in range(np_image.shape[0])]
    return np.array(out_array).reshape(in_shape)


def test_colorconversion():
    """tests XYZ to CIELAB/sRGB/ and sRGB to XYZ
    """
    testdata = np.abs(np.random.rand(10,10,3))
    testdata = old_div(testdata, testdata.max())
    test2 = XYZToLabImage(np.copy(testdata))
    good_data = inter_XYZ_to_lab(np.copy(testdata))
    good_data_2 = colormath_conversion_image(np.copy(testdata), 'xyz','lab')
    np.abs((good_data - test2)).max()
    test_srgb_image = inter_XYZ_to_srgb(np.copy(testdata))
    test_srgb_image_2 = colormath_conversion_image(np.copy(testdata), 'xyz','srgb')
    test_srgb_xyz = inter_srgb_to_xyz(np.copy(test_srgb_image))
    conv = convertToLab()
    test_srgb_xyz_own = conv.sRGBToXYZ(np.copy(test_srgb_image).astype(np.uint8))
    #lab
    im = np.copy(test_srgb_xyz)
    sh = im.shape
    im = np.matrix(im.reshape(sh[0] * sh[1],3)).transpose()
    im = np.array(XYZTosRGBMatrix * im).transpose()
    im = srgbGammaNP(im) * 255
    im = im.reshape(sh[0],sh[1],3)
    im = im.clip(0,255)
    print(im.max(),im.min())
    test_out_xyz = sRGBToXYZNP(np.copy(test_srgb_image.astype(np.uint8)))

def sRGBToLabNP(inData_numpy):
    """converts an array from sRGB to CIELAB colorspace

    :param inData_numpy: array to convert
    :type inData_numpy: ndarray
    :return: converted array 
    :rtype: ndarray
    """
    shape = inData_numpy.shape
    ttype = inData_numpy.dtype
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
        inData_numpy = old_div(inData_numpy.astype(np.float32), np.iinfo(ttype).max)
    sz = inData_numpy.shape[0] * inData_numpy.shape[1]
    inData_numpy = srgbGammaRemoveNP(inData_numpy)
    outData = sRGBToXYZImage(inData_numpy)
    labdata = XYZToLabImage(outData)
    return labdata


@njit
def adobeTosRGBNP(inData_numpy, whitePointRef=None):
    """converts an array from adobe RGB to sRGB colorspace

    :param inData_numpy: array to convert
    :type inData_numpy: ndarray
    :param whitePointRef: standard illumination conditions, defaults to whitePointD65 
    :type whitePointRef: tupel, optional
    :return: converted array
    :rtype: ndarray
    """
    if whitePointRef is None:
        whitePointRef = whitePointD65
    shape = inData_numpy.shape
    ttype = inData_numpy.dtype
    if np.issubdtype(ttype, int) and not ((ttype.type is np.uint8) or (ttype.type is np.uint16)): #TODO issubdtype njit problem
        print("Imagetype is integer but not uint8 or uint16!")
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
        inData_numpy = inData_numpy.astype(np.double)/ np.iinfo(ttype).max
    sz = inData_numpy.shape[0] * inData_numpy.shape[1]
    inData_numpy = inData_numpy.reshape(shape[0] * shape[1], shape[2])#TODO reshape njit problem
    inData_numpy = adobeGammaRemoveNP(inData_numpy)
    inData_numpy = ((np.matrix(inData_numpy) * XYZToAdobeMatrix.I) * XYZTosRGBMatrix)
    inData_numpy = srgbGammaNP(np.array(inData_numpy))
    return inData_numpy.reshape(shape)

def adobeToXYZNP(inData_numpy, whitePointRef=None):
    """converts an array from adobe RGB to XYZ

    :param inData_numpy: array to convert
    :type inData_numpy: ndarray
    :param whitePointRef: standard illumination conditions, defaults to whitePointD65
    :type whitePointRef: tupel, optional
    :return: converted array
    :rtype: ndarray
    """
    if whitePointRef is None:
        whitePointRef = whitePointD65
    shape = inData_numpy.shape
    ttype = inData_numpy.dtype
    if np.issubdtype(ttype, int) and not ((ttype.type is np.uint8) or (ttype.type is np.uint16)): #TODO njit issubdtype
        LOGGER.warning("Imagetype is integer but not uint8 or uint16!")
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
        inData_numpy = inData_numpy.astype(np.double) / np.iinfo(ttype).max
    sz = inData_numpy.shape[0] * inData_numpy.shape[1]
    inData_numpy = inData_numpy.reshape(shape[0] * shape[1], shape[2]) #TODO njit reshape problem (nur 1 arg erlaubt)
    inData_numpy = adobeGammaRemoveNP(inData_numpy)
    inData_numpy = ((np.matrix(inData_numpy) * XYZToAdobeMatrix.I) * XYZTosRGBMatrix)
    return np.array(inData_numpy).reshape(shape)


def adobeToNormSRGBNP(inData_numpy, whitePointRef=None):
    """converts an array from adobe RGB to sRGB

    :param inData_numpy: [description]
    :type inData_numpy: [type]
    :param whitePointRef: [description], defaults to None
    :type whitePointRef: [type], optional
    :return: [description]
    :rtype: [type]
    """
    if whitePointRef is None:
        whitePointRef = whitePointD65
    shape = inData_numpy.shape
    ttype = inData_numpy.dtype
    if np.issubdtype(ttype, int) and not ((ttype.type is np.uint8) or (ttype.type is np.uint16)):
        LOGGER.warning("Imagetype is integer but not uint8 or uint16!")
    if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
        inData_numpy = old_div(inData_numpy.astype(np.double), np.iinfo(ttype).max)
    sz = inData_numpy.shape[0] * inData_numpy.shape[1]
    inData_numpy = inData_numpy.reshape(shape[0] * shape[1], shape[2])
    inData_numpy = adobeGammaRemoveNP(inData_numpy)
    inData_numpy = ((np.matrix(inData_numpy) * XYZToAdobeMatrix.I) * XYZTosRGBMatrix)
    return inData_numpy.reshape(shape)

def colorscience_conversion_image(np_image, color_from, color_to, mask=None, illuminant='D65'):
    """color conversion using colormath library

    :param np_image: image to convert
    :type np_image: ndarray
    :param color_from: 
    :type color_from: type
    :param color_to: 
    :type color_to: type
    :param illuminant: 
    :type illuminant: type('D65')
    :return: 
    :rtype: 
    """
    in_shape = np_image.shape
    format_dict = {'srgb': [sRGBColor , {'rgb_type':'srgb'}, ['RGB'], {'target_rgb':'srgb'}],
                   'adobe': [AdobeRGBColor , {'rgb_type':'adobe_rgb'}, ['RGB'], {'target_rgb':'adobe_rgb'}],
                   'xyz':[XYZColor, {}, ['xyz'], {}],
                   'lab':[LabColor, {}, ['lab'], {}],
                   'xyy':[xyYColor, {}, ['xyy'], {}],
                   'hsv':[HSVColor, {}, ['hsv'], {}]}
    if len(in_shape) == 3:
        np_image = np_image.reshape([in_shape[0] * in_shape[1],3])
    if mask is not None:
        if mask.shape != np_image.shape:
            mask = mask.reshape([in_shape[0] * in_shape[1]])
            if mask.shape[0] != np_image.shape[0]:
                LOGGER.error("Wrong mask shape")
        np_image = np_image[mask]
    input_keyw = format_dict[color_from][1]
    input_keyw['illuminant'] = illuminant
    # output_keyw = format_dict[color_to][3]
    output_keyw = dict()
    output_keyw['target_illuminant'] = illuminant
    if format_dict[color_from][0] == format_dict[color_to][0]:
        out_list = [format_dict[color_from][0](np_image[idx,0], np_image[idx,1], np_image[idx,2], **input_keyw).convert_to('XYZ').convert_to(*format_dict[color_to][2], **output_keyw).get_value_tuple() for idx in range(np_image.shape[0])]
    else:
        
        out_list = [convert_color(format_dict[color_from][0](np_image[idx,0], np_image[idx,1], np_image[idx,2], **input_keyw), format_dict[color_to][0], **output_keyw).get_value_tuple() for idx in range(np_image.shape[0])]
    if mask is not None:
        out_array = np.zeros(in_shape)
        for idx in range(3):
            out_a = np.zeros(np.prod(in_shape[:-1]))
            out_a[mask] = out_list[idx]
            out_array[:,:,idx] = out_a.reshape(in_shape[:-1])
        return out_array.reshape(in_shape)
    else:
        return np.array(out_list).reshape(in_shape)

def colormath_conversion_image(np_image, color_from, color_to, mask=None, illuminant='D65'):
    """color conversion using colormath library

    :param np_image: image to convert
    :type np_image: ndarray
    :param color_from: 
    :type color_from: type
    :param color_to: 
    :type color_to: type
    :param illuminant: 
    :type illuminant: type('D65')
    :return: 
    :rtype: 
    """
    in_shape = np_image.shape
    format_dict = {'srgb': [sRGBColor , {'rgb_type':'srgb'}, ['RGB'], {'target_rgb':'srgb'}],
                   'adobe': [AdobeRGBColor , {'rgb_type':'adobe_rgb'}, ['RGB'], {'target_rgb':'adobe_rgb'}],
                   'xyz':[XYZColor, {}, ['xyz'], {}],
                   'lab':[LabColor, {}, ['lab'], {}],
                   'xyy':[xyYColor, {}, ['xyy'], {}],
                   'hsv':[HSVColor, {}, ['hsv'], {}]}
    if len(in_shape) == 3:
        np_image = np_image.reshape([in_shape[0] * in_shape[1],3])
    if mask is not None:
        if mask.shape != np_image.shape:
            mask = mask.reshape([in_shape[0] * in_shape[1]])
            if mask.shape[0] != np_image.shape[0]:
                LOGGER.error("Wrong mask shape")
        np_image = np_image[mask]
    input_keyw = format_dict[color_from][1]
    input_keyw['illuminant'] = illuminant
    # output_keyw = format_dict[color_to][3]
    output_keyw = dict()
    output_keyw['target_illuminant'] = illuminant
    if format_dict[color_from][0] == format_dict[color_to][0]:
        out_list = [format_dict[color_from][0](np_image[idx,0], np_image[idx,1], np_image[idx,2], **input_keyw).convert_to('XYZ').convert_to(*format_dict[color_to][2], **output_keyw).get_value_tuple() for idx in range(np_image.shape[0])]
    else:
        
        out_list = [convert_color(format_dict[color_from][0](np_image[idx,0], np_image[idx,1], np_image[idx,2], **input_keyw), format_dict[color_to][0], **output_keyw).get_value_tuple() for idx in range(np_image.shape[0])]
    if mask is not None:
        out_array = np.zeros(in_shape)
        for idx in range(3):
            out_a = np.zeros(np.prod(in_shape[:-1]))
            out_a[mask] = out_list[idx]
            out_array[:,:,idx] = out_a.reshape(in_shape[:-1])
        return out_array.reshape(in_shape)
    else:
        return np.array(out_list).reshape(in_shape)

def XYZToMelanin(xyz_image):
    """ from Image analysis of skin color heterogeneity focusing on skin chromophores and the age-related changes in facial skin. Kikuchi K1, Masuda Y, Yamashita T, Kawai E, Hirao T.Skin Res Technol. 2015 May;21(2):175-83
    https://onlinelibrary.wiley.com/doi/abs/10.1111/srt.12264

    :param xyz_image: xyz image as array
    :type xyz_image: ndarray
    :return: array of melanin values 
    :rtype: ndarray
    """
    return 4.861 * np.log10(xyz_image[:,:,0]) - 1.268 * np.log10(xyz_image[:,:,1]) - 4.669 * np.log10(xyz_image[:,:,2]) + 0.066

def XYZToHemoglobine(xyz_image):
    """ from Image analysis of skin color heterogeneity focusing on skin chromophores and the age-related changes in facial skin. Kikuchi K1, Masuda Y, Yamashita T, Kawai E, Hirao T.Skin Res Technol. 2015 May;21(2):175-83
    https://onlinelibrary.wiley.com/doi/abs/10.1111/srt.12264

    :param xyz_image: image in XYZ as array
    :type xyz_image: ndarray
    :return: array of hemoglobine values
    :rtype: ndarray

    """
    return 32.218 * np.log10(xyz_image[:,:,0]) - 37.499 * np.log10(xyz_image[:,:,1]) + 4.495 * np.log10(xyz_image[:,:,2]) + 0.444

def XYZToxyY(xyz_image, whitePoint=whitePointD65):
    """converts an array from xyz to xyY

    :param xyz_image: array to convert
    :type xyz_image: ndarray
    :param whitePoint: [description], defaults to whitePointD65
    :type whitePoint: [type], optional
    :return: converted array
    :rtype: ndarray
    """
    xmap = np.logical_and(np.logical_and(xyz_image[...,0]==0, xyz_image[...,1]==0), xyz_image[...,2]==0)
    xmapn =np.logical_not(xmap) 
    out_im = np.copy(xyz_image)
    out_im[xmapn,0] =  old_div(xyz_image[xmapn,0],(xyz_image.sum(axis=-1)[xmapn]))
    out_im[xmapn,1] =  old_div(xyz_image[xmapn,1],(xyz_image.sum(axis=-1)[xmapn]))
    out_im[xmap,0] = old_div(whitePoint[0],sum(whitePoint))
    out_im[xmap,1] = old_div(whitePoint[1],sum(whitePoint))
    out_im[xmap,2] = whitePoint[2]
    return out_im

def XYZToWIO(xyz_image, whitePoint=whitePointD65):
    """converts XYZ to WIO more insights: https://www.researchgate.net/publication/319905573_Tooth_Colour_and_Whiteness_A_review

    :param xyz_image: xyz image
    :type xyz_image: ndarray
    :param whitePoint: whitepoint, defaults to whitePointD65
    :type whitePoint: tupel, optional
    :return: converted image
    :rtype: ndarray
    """
    wp_xyY = [old_div(whitePoint[0],sum(whitePoint)), old_div(whitePoint[1],sum(whitePoint)), whitePoint[2]]
    xyY = XYZToxyY(xyz_image, whitePoint)
    return xyY[...,2] + 1075.012*(wp_xyY[0]-xyY[...,0]) +145.516*(wp_xyY[1]-xyY[...,1])

def XYZToWIC(xyz_image, whitePoint=whitePointD65):
    """converts XYZ to WIC more insights: https://www.researchgate.net/publication/319905573_Tooth_Colour_and_Whiteness_A_review

    :param xyz_image: xyz image
    :type xyz_image: ndarray
    :param whitePoint: whitepoint, defaults to whitePointD65
    :type whitePoint: tupel, optional
    :return: converted image
    :rtype: ndarray
    """
    wp_xyY = [old_div(whitePoint[0],sum(whitePoint)), old_div(whitePoint[1],sum(whitePoint)), whitePoint[2]]
    xyY = XYZToxyY(xyz_image, whitePoint)
    return xyY[...,2] + 800.*(wp_xyY[0]-xyY[...,0]) +1700.*(wp_xyY[1]-xyY[...,1])


class color_conversion(object):
    """class for color conversions
    """
    calc_mode = 'best'
    converter = None
    def to_test(self, input, color_mode):
        if self.converter is None:
            self.converter = convertToLab()
        return self.converter.norm_sRGBToXYZ(input)# sRGBTonormSRGB(input)

    def to_lab(self, input, color_mode):
        if self.calc_mode == 'best' or self.calc_mode == 'cuda':
            try:
                if self.converter is None:
                    self.converter = convertToLab()
                if color_mode == 'adobe':
                    return self.converter.adobeRGBToLab(input)
                elif color_mode == 'srgb':
                    return self.converter.sRGBToLab(input)
                else:
                    LOGGER.critical("No supported color")
            except:
                LOGGER.warning("Cuda not working")
                sys.exit(-1)
        if color_mode == 'adobe':
            return adobe_to_lab(input)
        elif color_mode == 'srgb':
            return sRGBToLabNP(input)
        else:
            LOGGER.critical("No supported color")
        sys.exit(-1)