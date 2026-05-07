import cv2
import sys
import numpy as np
from past.utils import old_div
from .LabelFunctions import removeLabels

def cv2_findContours(*args, **kwargs):
    """Finds contours

    :raises Exception: cv2 version not found
    :return: contours, hierarchy
    :rtype: ArrayOfArrays, Array
    """
    (major, _, _) = cv2.__version__.split(".")
    if major == '3':
        _, contours, hierarchy = cv2.findContours(*args, **kwargs)
    elif major == '2':
        contours, hierarchy = cv2.findContours(*args, **kwargs)
    else:
        raise Exception
    return contours, hierarchy

def contourMeasurementsCV(labeledSITK: np.ndarray, pos_set:set=None, neg_set:set=None):
    """gets contour measurements

    :param labeledSITK: labeled image
    :type labeledSITK: ndarray
    :param pos_set: label of interests, defaults to None
    :type pos_set: set, optional
    :param neg_set: not interested labels, defaults to None
    :type neg_set: set, optional
    :return: shapeData, additional informations
    :rtype: ndarray, dict
    """
    if pos_set is not None and neg_set is None:
        neg_set = set(range(1, labeledSITK.max() + 1)) - pos_set
    elif pos_set is None and neg_set is not None:
        pass
    elif pos_set is None and neg_set is None:
        pos_set = set(range(1, labeledSITK.max() + 1))
        neg_set = set([])
    else:
        #LOGGER.critical("poas_set and neg_set given")
        sys.exit(-1)

    def getContourMeasurements(cs: np.ndarray) -> tuple[np.ndarray, dict]:
        """gets measurements of countour

        :param cs: contour
        :type cs: Array
        :return: shapedata, additional informations
        :rtype: tuple[ndarray, dict]
        """
        cs = cs.astype(np.float32)
        boundingRect = cv2.boundingRect(cs)
        contourArea = cv2.contourArea(cs)
        fittedRect = cv2.minAreaRect(cs)
        fittedCircle = cv2.minEnclosingCircle(cs)
        length = np.array(fittedRect[1]).max()
        width = np.array(fittedRect[1]).min()
        circArea = fittedCircle[1] ** 2 * np.pi
        if width == 0:
            width = 0.001
        if contourArea == 0:
            contourArea = 0.001
        return [length, width, old_div(length, width), contourArea, length * width, circArea, length * width / contourArea, old_div(circArea, contourArea), fittedRect[0][0], fittedRect[0][1],
                fittedRect[1][0], fittedRect[1][1], fittedRect[2], boundingRect[0], boundingRect[1], boundingRect[2], boundingRect[3]]
    
    outDict = {'labelIndex': 0, 'lenIndex': 1, 'widthIndex': 2, 'length/widthIndex': 3, 'areaIndex': 4, 'boxAreaIndex': 5, 'circArea': 6, 'length*width/contourArea': 7, 'circArea/contourArea': 8, 'fittedRectCentreIndex': [9, 10],
               'fittedRectSizeIndex': [11, 12], 'fittedRectAngleIndex': 13, 'boundingBoxIndex': [14, 15, 16, 17]}
    cs, _ = cv2_findContours((removeLabels(np.copy(labeledSITK), neg_set) > 0).astype(
        np.uint8), mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)
    cs = [x.astype(np.float32) for x in cs]
    shapeData = np.array(list(map(getContourMeasurements, cs)))
    good_data_1 = np.logical_and(shapeData[:, 1] > 0, shapeData[:, 2] > 0)
    shapeData = shapeData[good_data_1, :]  # border labels are weird...
    shapeData = np.append(np.zeros((shapeData.shape[0], 1)), shapeData, 1)
    newLabel = 1
    setlabels = set([])
    for idx, css in enumerate([c for iidx, c in enumerate(cs) if good_data_1[iidx]]):
        labelImageCV = np.zeros_like(labeledSITK)
        cv2.drawContours(labelImageCV, [np.array(
            [x[0].astype(np.int32) for x in css])], 0, color=1, thickness=-1)
        if labelImageCV.sum() <= 5:
            continue
        meetLabel = set(np.unique(labelImageCV * labeledSITK))
        meetLabel.add(0)
        meetLabel.remove(0)
        if len(meetLabel) > 1:
            meetLabel = np.array(list(meetLabel))
            sz = [(labelImageCV * labeledSITK == x).sum() for x in meetLabel]
            meLabel = meetLabel[np.array(sz).argmax()]
        else:
            meLabel = meetLabel.pop()
        shapeData[idx, 0] = meLabel
        setlabels.add(meLabel)
        newLabel += 1
    shapeData = shapeData[shapeData[:, 0] > 0]
    return shapeData, outDict