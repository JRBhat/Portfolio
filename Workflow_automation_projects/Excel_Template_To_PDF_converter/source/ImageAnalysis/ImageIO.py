from PIL import Image
import numpy as np
import os
import imageio
import cv2

from . import IMAGEANALYSIS_LOGGER


def __svndata__():
    """
    | $Author: ndrews $
    | $Date: 2022-09-08 13:50:33 +0200 (Do., 08. Sep 2022) $
    | $Rev: 13397 $
    | $URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ImageIO.py $
    | $Id: ImageIO.py 13397 2022-09-08 11:50:33Z ndrews $
    """
    # only for documentation purpose
    return {
        'author': "$Author: ndrews $".replace('$', '').replace('Author:', '').strip(),
        'date': "$Date: 2022-09-08 13:50:33 +0200 (Do., 08. Sep 2022) $".replace('$', '').replace('Date:', '').strip(),
        'rev': "$Rev: 13397 $".replace('$', '').replace('Rev:', '').strip(),
        'id': "$Id: ImageIO.py 13397 2022-09-08 11:50:33Z ndrews $".replace('$', '').replace('Id:', '').strip(),
        'url': "$URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ImageIO.py $".replace('$', '').replace('URL:', '').strip()
    }


READ_IMAGES = {}

def readRGBImage(filename: str, keep: bool = False) -> np.ndarray:
    """Reads image and converts to RGB

    :param filename: file to convert
    :type filename: str
    :param keep: keep file, defaults to False
    :type keep: bool, optional
    :return: image
    :rtype: ndarray
    """
    img = readImage(filename, keep)
    if len(img.shape) == 2:
        return np.dstack([img, img, img])
    else:
        return img


def readImage(filename: str, keep: bool = False) -> np.ndarray:
    """reades an image as numpy array

    :param filename: image location
    :type filename: string
    :param keep: keep image, defaults to False
    :type keep: bool, optional
    :raises IOError: File not found/error while reading
    :return: image as array
    :rtype: Numpy Array
    """
    if keep:
        global READ_IMAGES
        if filename in READ_IMAGES:
            return READ_IMAGES[filename]
    if not os.path.exists(filename):
        IMAGEANALYSIS_LOGGER.error("Could not read File '%s', File does not exist" %
                     filename)  # log error
        raise IOError
    try:
        im = imageio.imread(filename)
        IMAGEANALYSIS_LOGGER.info("Read Image %s using 'freeimage'" % filename)
    except:
        try:
            im = Image.open(filename)
            IMAGEANALYSIS_LOGGER.info("Read Image %s using 'pil'" % filename)
        except:
            try:
                frames = imageio.mimread(filename)
                im = frames[len(frames)//2]
                IMAGEANALYSIS_LOGGER.info(
                    "Read a video and took image at position " + str(len(frames)//2) + "   %s using 'imageio.mimread'" % filename)
            except Exception as inst:
                IMAGEANALYSIS_LOGGER.error("Could not read File '%s', Exception: %s" %
                             (filename, inst))  # log error
                raise
    return np.array(im)


def readGrayscaleImage(filename: str, keep: bool = False) -> np.ndarray:
    """ Reads image and converts to grayscale (weighted colors)

    :param filename: file to convert
    :type filename: str
    :param keep: keep image, defaults to False
    :type keep: bool, optional
    :return: image in grayscale
    :rtype: ndarray
    """
    return rgb_to_gray_image(readImage(filename, keep).astype(np.float32))


def rgb_to_gray_image(img: np.ndarray) -> np.ndarray:
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


def writeImage(data: np.ndarray, filename: str) -> np.ndarray:
    """write an image

    :param data: data to write in RGB colorspace
    :type data: ndarray
    :param filename: location to save image
    :type filename: string
    :return: filename or false if fails
    :rtype: string or false
    """
    if data.max() > 255:
        try:
            if data.dtype is np.dtype("uint16") and filename.split(".")[-1] != "tif":
                raise ValueError(
                    "Can't write other imagetypes than tif as uint16!")
            imageio.imsave(filename, data)
            IMAGEANALYSIS_LOGGER.info("Write Image %s using 'imageio'" % filename)
        except Exception as inst:
            IMAGEANALYSIS_LOGGER.error("Could not write File '%s', Exception: %s" %
                         (filename, inst))  # log error
            raise
        return filename
    else:
        try:
            try:

                #high memory usage; try imageio first?
                # cv writes in BGR so convert image first from RGB to BGR
                if cv2.imwrite(filename, cv2.cvtColor(data, cv2.COLOR_RGB2BGR)):
                    IMAGEANALYSIS_LOGGER.info(f"Wrote Image {filename} using 'openCV'")
                else:
                    raise ValueError()
            except:
                try:
                    Image.fromarray(data).save(filename)
                    IMAGEANALYSIS_LOGGER.info(f"Wrote Image {filename} using 'pil'")
                except:
                    try:
                        imageio.imsave(filename, data)
                        IMAGEANALYSIS_LOGGER.info(
                            f"wrote Image {filename} using 'imageio.imsave'")
                    except:
                        raise
        except Exception as inst:
            IMAGEANALYSIS_LOGGER.error(f"Could not write File '{filename}', Exception: {inst}")
            raise
        return filename
