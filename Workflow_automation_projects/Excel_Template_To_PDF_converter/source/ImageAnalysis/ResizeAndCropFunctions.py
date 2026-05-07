import cv2
import numpy as np
from skimage import transform
from past.utils import old_div


def resize_to_fit_bewertunsmonitor(im_out: np.ndarray, x: int = 2560.0, y: int = 1600.0, enlarge: bool = False) -> np.ndarray:
    """resizes tge image to fit the bewertungsmonnitor

    :param im_out: image to resize
    :type im_out: ndarray
    :param x: x width to fit, defaults to 2560.0
    :type x: float, optional
    :param y: y width to fit, defaults to 1600.0
    :type y: float, optional
    :param enlarge: enlarge image, defaults to False
    :type enlarge: bool, optional
    :return: the resized image
    :rtype: ndarray
    """

    resize_factor = min(
        float(x) / float(im_out.shape[1]), float(y) / float(im_out.shape[0]))
    if resize_factor < 1 or enlarge:
        im_out = transform.resize(im_out, (round(
            resize_factor * im_out.shape[0]), round(resize_factor * im_out.shape[1])))
    return im_out


def resize(image: np.ndarray, width: int = None, height: int = None, inter: int = cv2.INTER_AREA) -> np.ndarray:
    """resizes an image

    :param image: image to resize
    :type image: ndarray
    :param width: resize width, defaults to None
    :type width: integer, optional
    :param height: resize height, defaults to None
    :type height: integer, optional
    :param inter: how to calculate pixel values (cv2.INTER_NEAREST,cv2.INTER_LINEAR,cv2.INTER_AREA,cv2.INTER_CUBIC,cv2.INTER_LANCZOS4), defaults to cv2.INTER_AREA
    :type inter: int
    :return: resized image
    :rtype: ndarray
    """

    dim = None
    # initialize the dimensions of the image to be resized and
    # grab the image size
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv2.resize(image, dim, interpolation=inter)

    # return the resized image
    return resized


def cropBBox(image: np.ndarray, bbox: tuple[int, int, int, int], border: int = 0, additional_crops: tuple[int, int, int, int] = None) -> np.ndarray:
    """crop image to bounding box (PIL/NUMPY)

    :param image: image
    :type image: ndarray
    :param bbox: bounding box
    :type bbox: tuple[int,int,int,int]
    :param border: add pixel border , defaults to 0
    :type border: int, optional
    :return: cropped image
    :rtype: ndarray
    """
    bbox = np.array(bbox) + [-border, -border, border, border]
    bbox[:2] = np.maximum(bbox[:2], [0, 0])
    bbox[2:] = np.minimum(bbox[2:], image.shape[:2][::-1])
    if additional_crops is not None:
        out_dat = []
        for dat in additional_crops:
            if len(dat.shape) == 2:
                out_dat.append(dat[bbox[1]: bbox[3], bbox[0]:bbox[2]])
            elif len(dat.shape) == 3:
                out_dat.append(dat[bbox[1]: bbox[3], bbox[0]:bbox[2], :])
        if len(image.shape) == 2:
            return image[bbox[1]: bbox[3], bbox[0]:bbox[2]], bbox, out_dat
        elif len(image.shape) == 3:
            return image[bbox[1]: bbox[3], bbox[0]:bbox[2], :], bbox, out_dat
    else:
        if len(image.shape) == 2:
            return image[bbox[1]: bbox[3], bbox[0]:bbox[2]]
        elif len(image.shape) == 3:
            return image[bbox[1]: bbox[3], bbox[0]:bbox[2], :]


def cropBBoxITK(image: np.ndarray, bbox: tuple[int, int, int, int], border: int = 0, square: bool = False) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """crop image to bounding box (ITK)

    :param image: image to crop to bbox
    :type image: ndarray
    :param bbox: bounding box [idx, idx, size, size]
    :type bbox: tuple[int,int,int,int]
    :param border: add pixel border, defaults to 0
    :type border: int, optional
    :param square: enlarge to have square region, defaults to False
    :type square: bool, optional
    :return: cropped image,bounding box
    :rtype: tuple[ndarray, tuple[int,int,int,int]]
    """
    idx = np.array(bbox)[:2]
    size = np.array(bbox)[2:]
    if square:
        newSize = np.array([size.max(), size.max()])
        diffSize = newSize - size
        idx -= old_div(diffSize, 2)
        size = newSize
    idx -= [border, border]
    size += 2 * np.array([border, border])
    bbox = np.array([idx, idx + size]).flatten()
    bbox[:2] = np.maximum(bbox[:2], [0, 0])
    bbox[2:] = np.minimum(bbox[2:], image.shape[:2][::-1])
    if len(image.shape) == 2:
        return image[bbox[1]: bbox[3], bbox[0]:bbox[2]], bbox
    elif len(image.shape) == 3:
        return image[bbox[1]: bbox[3], bbox[0]:bbox[2], :], bbox
