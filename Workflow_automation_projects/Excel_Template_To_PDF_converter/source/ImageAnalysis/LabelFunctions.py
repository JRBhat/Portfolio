from typing import Callable
import numpy as np
from . import ImageIO as Io
import scipy.ndimage as mod
import SimpleITK as sitk


def binary_image2labelimage(binImage: np.ndarray, autoRemove: bool = True, deleteSmallObjects: int = 0, borderSize: int = 0, foreground_mask: str = None) -> tuple[np.ndarray, list[int], set[np.ndarray], set[np.ndarray], set[np.ndarray]]:
    """label binary image, remove labels by size, mask, position (border)

    :param binImage: binary input image
    :type binImage: numpy array
    :param autoRemove: remove labels from image or return label list of them
    :type autoRemove: Boolean(True)
    :param deleteSmallObjects: size of small images to be deleted, or if value is  <1 float delete all images with are bigger than x % of biggest small image
    :type deleteSmallObjects: int(0)
    :param borderSize: size in pixel of border, nay label which is patially inside is deleted
    :type borderSize: int(0)
    :param foreground_mask: filename of binary forground mask
    :type foreground_mask: string(None)
    :return: labelled image and labels list if autoRemove is false
    :rtype: tuple[np.ndarray, list[int], set[np.ndarray], set[np.ndarray], set[np.ndarray]]
    """

    labelimage, _ = mod.label(binImage, mod.generate_binary_structure(2, 2))
    allLabels = list(range(1, labelimage.max() + 1))
    borderLabels = None
    bck_label = None
    if deleteSmallObjects > 0:
        labelCount = mod.measurements.sum(
            labelimage > 0, labels=labelimage, index=list(range(1, labelimage.max() + 1)))
        if deleteSmallObjects >= 1:
            posLabel = set(np.where((labelCount >= deleteSmallObjects))[0] + 1)
        else:
            posLabel = set(
                np.where((labelCount >= deleteSmallObjects * labelCount.max()))[0] + 1)
    else:
        posLabel = set(allLabels)
    if borderSize > 0:
        borderLabels = (set(labelimage[:borderSize, :].flatten().tolist()) | set(labelimage[-borderSize:, :].flatten().tolist())
                        | set(labelimage[:, :borderSize].flatten().tolist()) | set(labelimage[:, -borderSize:].flatten().tolist())) - set([0])
        posLabel = posLabel - borderLabels
    if foreground_mask is not None:
        background = Io.readGrayscaleImage(foreground_mask) <= 0
        bck_label = set(np.unique(labelimage[background]).tolist())
        posLabel = posLabel - bck_label
    if autoRemove:
        labelimage = relabelMap(labelimage.astype(
            getLabelFormatUINT(labelimage.max())), posLabel)
        labelimage = labelimage.astype(getLabelFormatUINT(labelimage.max()))
        return labelimage
    else:
        return labelimage, allLabels, posLabel, borderLabels, bck_label


def vectorFunc(x: int, newLabel: list[int]) -> int:
    """Helper class for curry_f

    :param x: old labels
    :type x: int
    :param newLabel: list of new labels
    :type newLabel: list of int
    :rtype: int
    """
    return newLabel[x]


def curry_relabelMap(posLabel: list[int], labeledImage: np.ndarray) -> np.ndarray:
    """Helper function to speed up relabelMap

    :param posLabel: list of labels to keep
    :type posLabel: list
    :param labeledImage: labelled image
    :type labeledImage: ndarray
    :return: numpy array
    :rtype: ndarray
    """
    posLabel = list(posLabel)
    posLabel.sort()
    newLabel = np.zeros(labeledImage.max() +
                        1).astype(getLabelFormatUINT(labeledImage.max() + 1))
    z = 1
    for x in posLabel:
        newLabel[x] = z
        z += 1

    def f_curried(x):
        return vectorFunc(x, newLabel)  # using your definition from above
    return f_curried


def getLabelFormatUINT(maxvalue: int) -> np.dtype:
    """gets the right datatype depent on objects

    :param maxvalue: number of objects
    :type maxvalue: integer
    :return: datatype
    :rtype: dtype
    """
    if maxvalue < 255:
        workType = np.uint8
    elif maxvalue < ((2 ** 16) - 1):
        workType = np.uint16
    elif maxvalue < (2 ** 32) - 1:
        workType = np.uint32
    else:
        workType = np.uint64
    return workType


def relabelMap(labelledImage: np.ndarray, posLabel: list[tuple[int, int]]) -> np.ndarray:
    """relabel labelled image , only keep posLabels and relabel them into 1...n

    :param labelledImage: labelled image
    :type labelledImage: ndarray
    :param posLabel: list of labels to keep
    :type posLabel: list[tuple[int,int]]
    :return: image
    :rtype: ndarray
    """
    sitk_im = sitk.GetImageFromArray(np.copy(labelledImage))
    rest = set(range(0, labelledImage.max() + 1)) - set(posLabel)
    chlab = dict(list(zip(list(map(int, posLabel)), list(
        range(1, len(posLabel) + 1)))) + list(zip(rest, [0] * len(rest))))
    test = sitk.ChangeLabelImageFilter()
    test.SetChangeMap(chlab)
    labeledSITKNew = sitk.GetArrayFromImage(test.Execute(sitk_im))
    return labeledSITKNew


def curry_renameLabels(posLabel: list[tuple[int, int]], labeledImage: np.ndarray) -> Callable:
    """Helper function to speed up relabelMap

    :param posLabel: list of labels to keep
    :type posLabel: list[tuple[int,int]]
    :param labeledImage: labelled image
    :type labeledImage: ndarray
    :return: function
    :rtype: Callable
    """
    maxValue = np.maximum(labeledImage.max() + 1,
                          np.array([x[0] for x in posLabel]).max() + 1)
    newLabel = np.cumsum(np.ones(maxValue).astype(
        getLabelFormatUINT(labeledImage.max() + 1))) - 1  # [0..n]
    for x in posLabel:
        newLabel[x[0]] = x[1]

    def f_curried(x):
        return vectorFunc(x, newLabel)  # using your definition from above
    return f_curried


def renameLabels(labelledImage: np.ndarray, labelList: list[tuple[str, str]]) -> np.ndarray:
    """relabel labelled image , only keep posLabels and relabel them into 1...n

    :param labelledImage: labelled image
    :type labelledImage: ndarray
    :param labelList:  list of tuple of labelrename (oldLabel, newLabel)
    :type labelList: list[tuple[str,str]]
    :return:  labeld image
    :rtype: ndarray
    """
    labeledSITKOld = labelledImage.copy()
    for k, v in labelList:
        labelledImage[labeledSITKOld == k] = v
    return labelledImage


def curry_removeLabels(negLabel: list[str], labeledImage: np.ndarray):
    """Helper function to speed up relabelMap

    :param negLabel: list of labels to keep
    :type negLabel: list
    :param labeledImage: labelled image
    :type labeledImage: ndarray
    :return: image
    :rtype: ndarray
    """
    newLabel = np.cumsum(np.ones(labeledImage.max(
    ) + 1).astype(getLabelFormatUINT(labeledImage.max() + 1))) - 1  # [0..n]
    newLabel[np.array(list(negLabel))] = 0

    def f_curried(x):
        return vectorFunc(x, newLabel)  # using your definition from above
    return f_curried


def removeLabels(labelledImage: np.ndarray, labelList: list[str]):
    """remove labels

    :param labelledImage: labelled image
    :type labelledImage: ndarray of dtype uint
    :param labelList: list labels to remove
    :type posLabel: list (tuple(2,uint))
    :rtype: numpy array (uint)
    """
    if not labelList:
        return labelledImage
    labeledSITKOld = labelledImage.copy()
    for k in labelList:
        labelledImage[labeledSITKOld == k] = 0
    return labelledImage
