from __future__ import division
import scipy.ndimage as mod
from scipy.ndimage.interpolation import rotate
import PIL.Image as Image
import numpy as np
import os
import pylab
from past.utils import old_div
import skimage.transform as skTrans
from functools import reduce

from .Util import *
from .StandardLogger import create_internal_logger
IMAGEANALYSIS_LOGGER = None
IMAGEANALYSIS_LOGGER = create_internal_logger("ImageAnalysis_logger")
try:
    IMAGEANALYSIS_LOGGER.debug(get_git_status(os.path.dirname(__file__)))
except:
    pass
from .WidthProfileOptimizerFunctions import *
from .ImageClasses import *
from .MedianFilterFunctions import *
from .MaskFunctions import *
from .ContourFunctions import *
from .LabelFunctions import *
from .ImageFilterFunctions import *
from .FindTemplateFunctions import *
from .DrawAndBlendFunctions import *
from .ColorConversion import *
from .ImageIO import *
from .ResizeAndCropFunctions import *
from . import ImageIO as Io
from .LabelFunctions import relabelMap, getLabelFormatUINT, binary_image2labelimage, renameLabels, removeLabels



def removeSmallForeground(binImage: np.ndarray, maxSize: int = 1, keepLargest: int = -1,  structure: np.ndarray = None) -> np.ndarray:
    """remove small foreground object

    :param binImage: input binary image
    :type binImage: ndarray
    :param maxSize: size upto objects removed
    :type maxSize: int(1)
    :param keepLargest: how many objects are kept at maximum (-1=all)
    :type keepLargest: int (-1)
    :param structure: structure used in label binary images, optional defaults to None
    :type structure: ndarray
    :return: relabelled images
    :rtype: ndarray
    """
    if structure is None:
        structure = mod.generate_binary_structure(2, 2)
    labelImage, ml = mod.label(binImage, structure)
    if ml == 0:
        return labelImage
    labelCount = mod.measurements.sum(
        labelImage > 0, labels=labelImage, index=list(range(1, labelImage.max() + 1)))
    if keepLargest <= 0:
        if maxSize > 1:
            posLabel = set(np.where((labelCount >= maxSize))[0] + 1)
        else:
            posLabel = set(
                np.where((labelCount >= maxSize * labelCount.max()))[0] + 1)
    else:
        max_size_n = np.sort(labelCount)[-keepLargest]
        if maxSize > 1:
            posLabel = set(
                np.where((labelCount >= max(maxSize, max_size_n)))[0] + 1)
        elif maxSize <= 0:
            posLabel = set(np.where((labelCount >= max_size_n))[0] + 1)
        else:
            posLabel = set(
                np.where((labelCount >= max(maxSize * labelCount.max(), max_size_n)))[0] + 1)

    if len(posLabel) == 1:
        return labelImage == list(posLabel)[0]
    elif len(posLabel) <= 5:
        lI = list(reduce(lambda x, y: np.logical_or(x, y), [
            labelImage == x for x in posLabel], np.zeros_like(binImage)))
        return lI
    else:
        return relabelMap(labelImage.astype(getLabelFormatUINT(labelImage.max())), posLabel) > 0
    return labelImage


def MeanSquareDiffImage(img1: str, img2: str) -> np.ndarray:
    """calculates mean square difference between images

    :param img1: first image path
    :type img1: str
    :param img2: second image path
    :type img2: str
    :return: mean square difference
    :rtype: ndarray
    """
    try:
        im1 = Image.open(img1)
    except Exception as inst:
        IMAGEANALYSIS_LOGGER.error("Could not load File '%s', Exception: %s" %
                                   (img1, inst))  # log error
        return False
    try:
        im2 = Image.open(img2)
    except Exception as inst:
        IMAGEANALYSIS_LOGGER.error("Could not load File '%s', Exception: %s" %
                                   (img2, inst))  # log error
        return False
    diff = np.max((np.array(im1).astype(float) -
                  np.array(im2).astype(float)) ** 2)
    return diff


def SimpleThreshold(filename: str, threshold: int) -> Image:
    """creates a simple treshold of an image

    :param filename: image
    :type filename: str
    :param threshold: treshold
    :type threshold: integer
    :return: image
    :rtype: Pil.Image
    """
    img = Image.open(filename).convert('L')
    if threshold > 0:
        imgN = img.point(lambda i: i >= threshold)
    else:
        imgN = img.point(lambda i: i <= -threshold)
    return imgN


def SimpleThresholdSize(filename: str, threshold: int) -> np.ndarray:
    """creates a simple treshold size

    :param filename: image
    :type filename: str
    :param threshold: treshold
    :type threshold: int
    :return: treshold size
    :rtype: int
    """
    arr = np.array(np.asarray(SimpleThreshold(filename, threshold)))
    return old_div(arr.sum().astype(np.double), arr.size)


def get_grayscale_image(filename: str, keep: bool = False) -> np.ndarray:
    """gets the grayscale of an image

    :param filename: image location
    :type filename: String
    :param keep: keep the original file, defaults to False
    :type keep: bool, optional
    :return: gray scale as array
    :rtype: Numpy Array
    """
    if filename is None:
        return None
    if isinstance(filename, str):
        if os.path.exists(filename):
            return Io.readGrayscaleImage(filename, keep)
        else:
            return None
    elif type(filename) is np.ndarray:
        return filename
    else:
        return None


def getImageResolution(filename: str) -> tuple[float, float]:
    """gets the image resolution

    :param filename: image
    :type filename: str
    :return: image resolution
    :rtype: tuple[float, float]
    """
    im = Image.open(filename)
    return im.info['dpi']


def restoreImageResolution(filename: str, outFile: str, orgFile: str) -> None:
    """restores image resolution and saves the restored image

    :param filename: inputfile
    :type filename: str
    :param outFile: outputfile
    :type outFile: str
    :param orgFile: originalfile
    :type orgFile: str
    """
    im = Image.open(orgFile)
    dpi = im.info['dpi']
    im = Image.open(filename)
    im.save(outFile, dpi=dpi)


def morphological_binarize(imageNP, minMaxThreshold, deleteSmallObjects=0, borderSize=0, foreground_mask=None, mode='gauss', subsample=1, crop_by_foreground=False):
    """morphological binarize using hysteresis inverse thresholding (i.e. pixel is on if value is smaller than min
    threshold or value is smaller than max threshold and pixel is connected (4) to foreground
    This function uses threshold based on Gaussian assumption: threshold = Mean(image) - minMaxThreshold * STD(image)
    Uses :func:binary_image2labelimage for postprocessing

    :param imageNP: input image
    :type imageNP: ndarray
    :param minMaxThreshold: threshold on Gaussian distribution
    :type minMaxThreshold: 2-list, tuple
    :param deleteSmallObjects: size of small images to be deleted, or if value is  <1 float delete all images with are bigger than x % of biggest small image
    :type deleteSmallObjects: int(0)/float
    :param borderSize: size in pixel of border, nay label which is patially inside is deleted
    :type borderSize: int(0)
    :param foreground_mask: filename of binary forground mask
    :type foreground_mask: str(None)
    :return: labelled image and background labels
    :rtype: ndarray, list
    """
    foreground = get_grayscale_image(foreground_mask)
    if foreground is None:
        foreground = np.ones_like(imageNP).astype(np.bool_)
    else:
        foreground = foreground > 0
    if subsample > 1:
        foreground = foreground[::subsample, ::subsample]
    if mode == 'gauss':
        me = imageNP[::subsample, ::subsample][foreground].astype(
            np.double).mean()
        st = imageNP[::subsample, ::subsample][foreground].astype(
            np.double).std()
        lowThreshImage = imageNP.astype(np.double) < (
            me - minMaxThreshold[0] * st)
        highThreshImage = imageNP.astype(
            np.double) < (me - minMaxThreshold[1] * st)
    elif mode == 'fix':
        lowThreshImage = imageNP.astype(np.double) < minMaxThreshold[0]
        highThreshImage = imageNP.astype(np.double) < minMaxThreshold[1]
    elif mode == '-fix':
        lowThreshImage = imageNP.astype(np.double) > minMaxThreshold[0]
        highThreshImage = imageNP.astype(np.double) > minMaxThreshold[1]
    else:
        return 'unsupported mode'
    if crop_by_foreground and foreground_mask is not None:
        foreground[:borderSize, :] = False
        foreground[:, :borderSize] = False
        foreground[-borderSize:, :] = False
        foreground[:, -borderSize:] = False
        labelImage, allLabels, posLabel, _, _ = binary_image2labelimage(np.logical_and(
            lowThreshImage, foreground), autoRemove=False, deleteSmallObjects=deleteSmallObjects, borderSize=borderSize, foreground_mask=foreground_mask)
    else:
        labelImage, allLabels, posLabel, _, _ = binary_image2labelimage(
            lowThreshImage, autoRemove=False, deleteSmallObjects=deleteSmallObjects, borderSize=borderSize, foreground_mask=None)
    if labelImage.max() == 0:
        return labelImage, set([])
    imageMeasMax = mod.measurements.maximum(highThreshImage.astype(
        np.double), labels=labelImage, index=allLabels)
    posLabel = posLabel & set(np.where(imageMeasMax > 0)[0] + 1)
    labelImageN = relabelMap(labelImage.astype(
        getLabelFormatUINT(labelImage.max())), posLabel)
    labelImage = labelImageN.astype(getLabelFormatUINT(labelImage.max()))
    bck_label = set([])
    if foreground_mask is not None and (isinstance(foreground_mask, str) and os.path.exists(foreground_mask)):
        background = mod.morphology.binary_dilation(
            np.logical_not(foreground), iterations=2)
        bck_label = set(np.unique(labelImage[background]).tolist()) - set([0])
    return labelImage, bck_label


def morphological_binarize_segm(imageNP, minMaxThreshold, deleteSmallObjects=0, borderSize=0, foreground_mask=None, mode='gauss', subsample=1, crop_by_foreground=False):
    """morphological binarize using hysteresis inverse thresholding

    :param imageNP: input image
    :type imageNP: ndarray
    :param minMaxThreshold: threshold on Gaussian distribution
    :type minMaxThreshold: 2-list, tuple
    :param deleteSmallObjects: size of small images to be deleted, or if value is  <1 float delete all images with are bigger than x % of biggest small image
    :type deleteSmallObjects: int(0)
    :param borderSize: size in pixel of border, nay label which is patially inside is deleted
    :type borderSize: int(0)
    :param foreground_mask: filename of binary forground mask
    :type foreground_mask: str(None)
    :return: labelled image
    :rtype: ndarray
    """
    return morphological_binarize(imageNP, minMaxThreshold, deleteSmallObjects, borderSize, foreground_mask, mode, subsample, crop_by_foreground)[0]


def secure_rotation(imLabelCut: np.ndarray, angle: float, mode='nearest') -> np.ndarray:
    """rotates an image

    :param imLabelCut: image to rotate
    :type imLabelCut: ndarray
    :param angle: angle
    :type angle: float
    :param mode: mode, defaults to 'nearest'
    :type mode: str, optional
    :return: The rotated array of image.
    :rtype: ndarray
    """
    orgType = imLabelCut.dtype
    if imLabelCut.max() <= 255 and imLabelCut.min() >= 0:
        return rotate(imLabelCut.astype(np.uint8), angle * 180 / np.pi, mode=mode).astype(orgType)
    else:
        labelsOrg = np.unique(imLabelCut)
        if len(labelsOrg) > 255:
            IMAGEANALYSIS_LOGGER.critical(
                "secureRotation(imLabelCut, angle, mode)")
            sys.exit(-1)
        renameLabelsList = [[x, idx] for idx, x in enumerate(labelsOrg)]
        renameLabelsInvList = [[idx, x] for idx, x in enumerate(labelsOrg)]
        imToRot = renameLabels(imLabelCut.copy(), renameLabelsList)
        imRot = rotate(imToRot.astype(np.uint8),
                       angle * 180 / np.pi, mode=mode).astype(orgType)
        imreturn = renameLabels(imRot, renameLabelsInvList)
        return imreturn


def _vec2d_dist(p1, p2):
    """distance between to 2d vectors

    :param p1: vector 1
    :type p1: tupel
    :param p2: vector 2
    :type p2: tupel
    :return: distance 
    :rtype: float
    """
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2


def _vec2d_sub(p1, p2):
    """subtraction between two 2d vectors

    :param p1: vector 1
    :type p1: tupel
    :param p2: vector 2
    :type p2: tupel
    :return: difference
    :rtype: float
    """
    return (p1[0] - p2[0], p1[1] - p2[1])


def _vec2d_mult(p1, p2):
    """multiplication between two 2d vectors

    :param p1: vector 1
    :type p1: tupel
    :param p2: vector 2
    :type p2: tupel
    :return: product
    :rtype: [type]
    """
    return p1[0] * p2[0] + p1[1] * p2[1]


def ramerdouglas(line, dist):
    """Does Ramer-Douglas-Peucker simplification of a line with `dist`
    threshold.`line` is a list-of-tuples, where each tuple is a 2D coordinate
    Usage is like so:
    myline = [(0.0, 0.0), (1.0, 2.0), (2.0, 1.0)]
    simplified = (myline, dist = 1.0)

    :param line: list-of-tuples, where each tuple is a 2D coordinate
    :type line: list of tuples
    :param dist: distance
    :type dist: float
    :return: [begin, end]
    :rtype: list
    """
    if len(line) < 3:
        return line
    begin, end = line[0], line[-1]
    distSq = []
    for curr in line[1:-1]:
        tmp = (_vec2d_dist(begin, curr) - old_div(_vec2d_mult(_vec2d_sub(end,
               begin), _vec2d_sub(curr, begin)) ** 2, _vec2d_dist(begin, end)))
        distSq.append(tmp)
    maxdist = max(distSq)
    if maxdist < dist ** 2:
        return [begin, end]
    pos = distSq.index(maxdist)
    return ramerdouglas(line[:pos + 2], dist) + ramerdouglas(line[pos + 1:], dist)[1:]


def colorize_label_image(np_array):
    """colorizes an image

    :param np_array: image
    :type np_array: ndarray
    :return: colorized image
    :rtype: ndarray
    """
    im = colorize_image(np_array)
    im[:, :, 0][np_array == 0] = 0
    im[:, :, 1][np_array == 0] = 0
    im[:, :, 2][np_array == 0] = 0
    return im


def colorize_image(np_array, ma_in=None, mi_in=None):
    """colormaps the image with the colormap "jet" using pylab.

    :param np_array: np_array to colormap
    :type np_array: ndarray
    :param ma_in: max colorrange, defaults to None
    :type ma_in: int, optional
    :param mi_in: minimum colorrange, defaults to None
    :type mi_in: int, optional
    :return: colormapped image in uint8 
    :rtype: ndarray
    """
    np_array = np_array.astype(np.double)
    if mi_in is not None:
        mi = mi_in
    else:
        mi = np_array.min()
    if ma_in is not None:
        ma = ma_in
    else:
        ma = np_array.max()
    if mi == ma:
        im = pylab.cm.jet(np.zeros_like(np_array), bytes=True)
    else:
        im = pylab.cm.jet(old_div((np_array - mi), (ma - mi)), bytes=True)
    return im


def gaussian_pyramid(image, level, scale=2, enlarge_full=False):
    """creates a gaussian pyramid with the image

    :param image: image
    :type image: ndarray
    :param level: max layer
    :type level: int
    :param scale: downscale factor, defaults to 2
    :type scale: float, optional
    :param enlarge_full: enlarge image, defaults to False
    :type enlarge_full: bool, optional
    :return: gaussian pyramid
    :rtype: ndarray
    """
    in_type = image.dtype
    image = image.astype(np.double)
    mi = image.min()
    ma = image.max()
    out_im = [(x * (ma - mi) + mi).astype(in_type) for x in skTrans.pyramid_gaussian(
        (old_div((image.astype(np.double) - mi), (ma - mi))), max_layer=level, downscale=scale)]
    if enlarge_full:
        base_np_im = np.zeros_like(out_im[0])

        def pad_funct(im):
            out = np.copy(base_np_im)
            if len(im.shape) == 2:
                out[:im.shape[0], :im.shape[1]] = im
            else:
                out[:im.shape[0], :im.shape[1]][:] = im.flatten()
            return out
        out_im = list(map(pad_funct, out_im))
    return out_im


def fill_background_holes(labelImage, border=2):
    """fills labelled background holes

    :param labelImage: labelled image
    :type labelImage: Image
    :param border: border, defaults to 2
    :type border: int, optional
    :return: image with filled background and removed labels
    :rtype: ndarray 
    """
    labelimage, ml = mod.label(labelImage == 0)
    bck_label = (set(labelimage[:border, :].flatten()) | set(labelimage[-border:, :].flatten()) | set(
        labelimage[:, :border].flatten()) | set(labelimage[:, -border:].flatten())) - set([0])
    remove_label = set(labelimage.flatten()) - bck_label - set([0])
    return np.logical_not(removeLabels(labelimage, remove_label))
