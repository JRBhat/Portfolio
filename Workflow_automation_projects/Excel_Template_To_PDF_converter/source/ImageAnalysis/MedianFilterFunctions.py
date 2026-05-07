import cv2
import numpy as np
from .ImageIO import readGrayscaleImage
import skimage
from skimage.morphology import square
from skimage.filters import rank
from past.utils import old_div


def medianFilterNormalize(filename: str, medianRadius: int, subSampleFact: int = 1, outfile: str = None) -> np.ndarray:
    """median filters a image

    :param filename: image or filename of image
    :type filename: str/ndarray
    :param medianRadius: radius of median filter
    :type medianRadius: int
    :param subSampleFact: do subsampling first to speed up (window size), defaults to 1
    :type subSampleFact: int, optional
    :param outfile: outfile, defaults to None
    :type outfile: string, optional
    :return: normalized image
    :rtype: ndarray
    """
    try:
        grey_full = filename
        grey_full = ((grey_full - grey_full.min()) /
                     (grey_full.max() - grey_full.min()) * 255).astype(np.uint8)
    except Exception:
        grey_full = readGrayscaleImage(filename)
        grey_full = ((grey_full - grey_full.min()) /
                     (grey_full.max() - grey_full.min()) * 255).astype(np.uint8)
    grey_small = cv2.resize(grey_full, (0, 0), fx=1./subSampleFact,
                            fy=1./subSampleFact, interpolation=cv2.INTER_NEAREST)
    im3 = (cv2.medianBlur(cv2.copyMakeBorder(grey_small, medianRadius + 1, medianRadius + 1, medianRadius + 1, medianRadius + 1,
           cv2.BORDER_REFLECT), medianRadius * 2 + 1))[medianRadius + 1: -(medianRadius + 1), medianRadius + 1: -(medianRadius + 1)]
    im4 = cv2.resize(
        im3, (grey_full.shape[1], grey_full.shape[0]), interpolation=cv2.INTER_NEAREST)
    imNN = (grey_full.astype(np.int32) - im4.astype(np.int32)
            ).clip(0, 255).astype(np.uint8)
    if outfile is not None:
        cv2.imwrite(outfile, imNN)
    return imNN


def medianFilterNormalizeImage(image: np.ndarray, medianRadius: int, subSampleFact: int = 1, outfile: str = None) -> tuple[np.ndarray, np.ndarray]:
    """shading correction via median filter

    :param image: input image
    :type image: ndarray
    :param medianRadius: radius of median filter
    :type medianRadius: int
    :param subSampleFact: do subsampling first to speed up (window size)
    :type subSampleFact: int(1)
    :param outfile: write
    :type outfile: type(None)
    :return: median image, resized image
    :rtype: tuple[np.ndarray,np.ndarray]
    """
    grey_full = image
    grey_full = ((grey_full - grey_full.min()) /
                 (grey_full.max() - grey_full.min()) * 255).astype(np.uint8)
    grey_small = cv2.resize(grey_full, (0, 0), fx=1./subSampleFact,
                            fy=1. / subSampleFact, interpolation=cv2.INTER_NEAREST)
    im3 = (cv2.medianBlur(cv2.copyMakeBorder(grey_small, medianRadius + 1, medianRadius + 1, medianRadius + 1, medianRadius + 1,
           cv2.BORDER_REFLECT), medianRadius * 2 + 1))[medianRadius + 1: -(medianRadius + 1), medianRadius + 1: -(medianRadius + 1)]
    im4 = cv2.resize(
        im3, (grey_full.shape[1], grey_full.shape[0]), interpolation=cv2.INTER_LINEAR)
    imNN = (grey_full.astype(np.int32) - im4.astype(np.int32))
    if outfile is not None:
        cv2.imwrite(outfile, imNN.clip(0, 255).astype(np.uint8))
    return imNN, im4


def medianFilterNormalizeFloat(image: np.ndarray, medianRadius: int, subSampleFact: int = 1, outfile: str = None) -> tuple[np.ndarray, np.ndarray]:
    grey_full = image.astype(np.double)
    mi = grey_full.min()
    ma = grey_full.max()
    grey_full = ((grey_full - mi) / (ma - mi) * 255).astype(np.uint8)
    grey_small = cv2.resize(grey_full, (0, 0), fx=1./subSampleFact,
                            fy=1./subSampleFact, interpolation=cv2.INTER_NEAREST)
    im3 = (cv2.medianBlur(cv2.copyMakeBorder(grey_small, medianRadius + 1, medianRadius + 1, medianRadius + 1, medianRadius + 1,
           cv2.BORDER_REFLECT), medianRadius * 2 + 1))[medianRadius + 1: -(medianRadius + 1), medianRadius + 1: -(medianRadius + 1)]
    im4 = (cv2.resize(im3, (grey_full.shape[1], grey_full.shape[0]),
           interpolation=cv2.INTER_LINEAR)).astype(np.double)
    imNN = ((grey_full.astype(np.double) -
            im4.astype(np.double)) / 255.0 * (ma - mi))
    if outfile is not None:
        cv2.imwrite(outfile.clip(0, 255).astype(np.uint8), imNN)
    return imNN, (im4.astype(np.double) / 255.0 * (ma - mi)) + mi


def medianFilterImage(image: np.ndarray, medianRadius: int, subSampleFact: int = 1) -> np.ndarray:
    grey_full = image
    mi = grey_full.min()
    ma = grey_full.max()
    grey_full = ((grey_full - grey_full.min()) /
                 (grey_full.max() - grey_full.min()) * 255).astype(np.uint8)
    grey_small = cv2.resize(grey_full, (0, 0), fx=old_div(
        1., subSampleFact), fy=old_div(1., subSampleFact), interpolation=cv2.INTER_NEAREST)
    im3 = (cv2.medianBlur(cv2.copyMakeBorder(grey_small, medianRadius + 1, medianRadius + 1, medianRadius + 1, medianRadius + 1,
           cv2.BORDER_REFLECT), medianRadius * 2 + 1))[medianRadius + 1: -(medianRadius + 1), medianRadius + 1: -(medianRadius + 1)]
    im4 = cv2.resize(
        im3, (grey_full.shape[1], grey_full.shape[0]), interpolation=cv2.INTER_CUBIC)
    return (im4.astype(np.double) / 255 * (ma - mi)) + mi


def medianFilterImageD(image: np.ndarray, medianRadius: int = 2, subSampleFact: int = 1) -> np.ndarray:
    grey_full = image
    grey_small = cv2.resize(grey_full, (0, 0), fx=old_div(
        1., subSampleFact), fy=old_div(1., subSampleFact), interpolation=cv2.INTER_CUBIC)
    im3 = (cv2.medianBlur(cv2.copyMakeBorder(grey_small.astype(np.float32), medianRadius + 1, medianRadius + 1, medianRadius + 1,
           medianRadius + 1, cv2.BORDER_REFLECT), medianRadius * 2 + 1))[medianRadius + 1: -(medianRadius + 1), medianRadius + 1: -(medianRadius + 1)]
    im4 = cv2.resize(
        im3, (grey_full.shape[1], grey_full.shape[0]), interpolation=cv2.INTER_CUBIC)
    return im4


def medianFilterImageS(image: np.ndarray, medianRadius: int, subSampleFact: int = 1) -> np.ndarray:
    grey_full = image
    grey_small = cv2.resize(grey_full, (0, 0), fx=old_div(
        1., subSampleFact), fy=old_div(1., subSampleFact), interpolation=cv2.INTER_CUBIC)
    mi = grey_small.min()
    ma = grey_small.max()
    im = np.round((grey_small-mi)/(ma-mi)*((2**10)-1)).astype(np.uint16)
    im3 = skimage.filters.rank.median(cv2.copyMakeBorder(im, medianRadius + 1, medianRadius + 1,
                                      medianRadius + 1, medianRadius + 1, cv2.BORDER_REFLECT), skimage.morphology.disk(medianRadius))

    im4 = cv2.resize((im3.astype(np.double) / ((2**10)-1) * (ma - mi)) + mi,
                     (grey_full.shape[1], grey_full.shape[0]), interpolation=cv2.INTER_CUBIC)
    return im4


def skimage_median(image: np.ndarray, radius: int) -> np.ndarray:
    """Return local median of an image.

    :param image: image
    :type image: ndarray
    :param radius: [description]
    :type radius: int
    :return: image with median filter
    :rtype: ndarray
    """
    mi = image.min()
    ma = image.max()
    im_adj = ((image.astype(np.double) - mi) / (ma - mi)
              * ((2 ** 12) - 1)).astype(np.uint16)
    return rank.median(im_adj, square(radius)).astype(np.double) / ((2 ** 12) - 1) * (ma - mi) + mi
