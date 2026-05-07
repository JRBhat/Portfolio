from typing import Callable
import cv2
import numpy as np
import logging
from skimage.measure import ransac
from skimage.transform import SimilarityTransform
from past.utils import old_div

from . import Util
# import because older versions of ImageLibary explicit imported ImageClass from OverloadedFunctions
from .ImageClasses import ImageClass
from .FindTemplateFunctions import find_template_contour
from .ResizeAndCropFunctions import cropBBoxITK
from . import IMAGEANALYSIS_LOGGER


def __svndata__():
    """
    | $Author: ndrews $
    | $Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $
    | $Rev: 13366 $
    | $URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/OverloadedFunctions.py $
    | $Id: OverloadedFunctions.py 13366 2022-08-05 13:06:26Z ndrews $
    """
    # only for documentation purpose
    return {
        'author': "$Author: ndrews $".replace('$', '').replace('Author:', '').strip(),
        'date': "$Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $".replace('$', '').replace('Date:', '').strip(),
        'rev': "$Rev: 13366 $".replace('$', '').replace('Rev:', '').strip(),
        'id': "$Id: OverloadedFunctions.py 13366 2022-08-05 13:06:26Z ndrews $".replace('$', '').replace('Id:', '').strip(),
        'url': "$URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/OverloadedFunctions.py $".replace('$', '').replace('URL:', '').strip()
    }



def find_template(image: np.ndarray, template: np.ndarray, cropimage: np.ndarray = None, showdata: bool = False) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """find a template in a image

    :param image: image to search in
    :type image: ndarray
    :param template: template to search for
    :type template: ndarray
    :param cropimage: cropped image, defaults to None
    :type cropimage: ndarray, optional
    :param showdata: show data (pylab.show()), defaults to False
    :type showdata: bool, optional
    :return: template , bounding box of found template
    :rtype: ndarray, tuple[int,int,int,int]
    """
    assert image.dtype == template.dtype
    (h, w) = template.shape[:2]
    method = cv2.TM_CCORR_NORMED
    value_choice = [1, 3]
    ttype = image.dtype
    if np.issubdtype(ttype, int) and not ((ttype.type is np.uint8) or (ttype.type is np.uint16)):
        IMAGEANALYSIS_LOGGER.warning("Imagetype is integer but not uint8 or uint16!")
    if ttype.type is np.uint16:
        image = Util.convert_uint16_to_uint8(image)
        template = Util.convert_uint16_to_uint8(template)
    out = cv2.normalize(cv2.matchTemplate(image, template, method))
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(out)
    minMaxValues = cv2.minMaxLoc(out)
    if cropimage is None:
        cropimage = image
    bd = 0  # 100
    testImAuss, bbox_crop = cropBBoxITK(
        image, [minMaxValues[value_choice[-1]][0], minMaxValues[value_choice[-1]][1], w, h], border=bd)
    if showdata:
        import pylab
        pylab.subplot(222)
        imgplot = pylab.imshow(out)
        imgplot.set_interpolation('nearest')
        pylab.scatter(maxLoc[0], maxLoc[1], c='r', s=40)
        pylab.scatter(minLoc[0], minLoc[1], c='g', s=40)
        pylab.subplot(221)
        imgplot = pylab.imshow(image)
        imgplot.set_interpolation('nearest')
        pylab.scatter(maxLoc[0], maxLoc[1], c='r', s=40)
        pylab.scatter(minLoc[0], minLoc[1], c='g', s=40)
        pylab.subplot(223)
        imgplot = pylab.imshow(template)
        imgplot.set_interpolation('nearest')
        pylab.subplot(224)
        imgplot = pylab.imshow(testImAuss)
        imgplot.set_interpolation('nearest')
        pylab.show()
    return testImAuss, (minMaxValues[value_choice[-1]][1], (minMaxValues[value_choice[-1]][1] + h), minMaxValues[value_choice[-1]][0], minMaxValues[value_choice[-1]][0] + w)


def find_template_for_ransac(image: np.ndarray, template: np.ndarray, mode: str = cv2.TM_SQDIFF_NORMED, best_value_choice: list[int] = [0, 2]) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """do opencv template matching
    :param image: image to search
    :type image: numpy.array(uint8 or uint16)
    :param template: template image
    :type template: numpy.array(uint8 or uint16)
    :param mode: opencv template mode (see opencv docu)
    :type mode: str
    :param best_value_choice: [0,2] for minimisation metrc, [1,3] otherwise (see cv2.minmaxLoc)
    :type best_value_choice: list[int,int]
    :return: metric image in float, bounding box of found template
    :rtype: tuple[np.ndarray,tuple[int,int,int,int]]
    """
    assert(image.dtype == template.dtype)
    (h, w) = template.shape[:2]
    method = mode
    value_choice = best_value_choice
    ttype = image.dtype
    if np.issubdtype(ttype, int) and not ((ttype.type is np.uint8) or (ttype.type is np.uint16)):
        IMAGEANALYSIS_LOGGER.warning("Imagetype is integer but not uint8 or uint16!")
    if ttype.type is np.uint16:
        image = Util.convert_uint16_to_uint8(image)
        template = Util.convert_uint16_to_uint8(template)
    # cv2.TM_SQDIFF)) # or CV_TM_CCORR_NORMED))
    out = cv2.matchTemplate(image, template, method)
    range_min_mx = [out.min(), out.max()]
    range_best = cv2.matchTemplate(template, template, method)
    minMaxValues = cv2.minMaxLoc(out)
    if abs(range_best - range_min_mx[0]) < abs(range_best - range_min_mx[1]):
        # , alpha=range_best, beta=range_min_mx[1])
        out = 1.0 - (old_div((out - range_best),
                     (range_min_mx[1] - range_best))).clip(0, 1)
    else:
        # cv2.normalize(out, alpha=range_min_mx[0], beta=range_best)
        out = (
            old_div((out - range_min_mx[0]), (range_best - range_min_mx[0]))).clip(0, 1)
    return out, minMaxValues[value_choice[-1]], (minMaxValues[value_choice[-1]][1], (minMaxValues[value_choice[-1]][1] + h), minMaxValues[value_choice[-1]][0], minMaxValues[value_choice[-1]][0] + w)


def find_template_transform(input_image: np.ndarray, contour_list_fg: list[tuple[int, int]], contour_list_bg: list[tuple[int, int]], find_image: np.ndarray, find_bbox: tuple[int, int, int, int], min_size: int = 200, contours_to_move: list[tuple[int, int]] = None) -> tuple[list[list[tuple[int, int]]], list[tuple[int, int]], list[list[tuple[int, int]]]]:
    """finds templates

    :param input_image: input image
    :type input_image: ndarray
    :param contour_list_fg: contour list foreground
    :type contour_list_fg: list[tuple[int,int]]
    :param contour_list_bg: contour list background
    :type contour_list_bg: list[tuple[int,int]]
    :param find_image: image to search for
    :type find_image: ndarray
    :param find_bbox: bbox to search for
    :type find_bbox: tuple[int,int,int,int]
    :param min_size: min size, defaults to 100
    :type min_size: int, optional
    :param contours_to_move: list of coordinates to transform according to 'best-fit-transform', defaults to None
    :type contours_to_move: list[tuple[int,int]], optional
    :return: distance array, found contours, moved contours 
    :rtype: tuple[list[list[tuple[int,int]]], list[tuple[int,int]], list[list[tuple[int,int]]]]
    """
    out_region, cc = find_template_contour(input_image, contour_list_bg, [find_image], [
                                           find_bbox], min_size=min_size, template_bbox=None)
    dst = []
    corr_images = {}
    for (y, x) in contour_list_fg:
        xmin = int(np.max([0, x - old_div(min_size, 2)]))
        xmax = int(np.min([input_image.shape[0], x + old_div(min_size, 2)]))
        ymin = int(np.max([0, y - old_div(min_size, 2)]))
        ymax = int(np.min([input_image.shape[1], y + old_div(min_size, 2)]))
        template = input_image[xmin:xmax, ymin:ymax, :]
        if find_bbox is None:
            find_bbox_loc = [0, 0, find_image.shape[1], find_image.shape[0]]
        elif find_bbox == 'auto':
            x_perc = 0.1 * find_image.shape[0]
            y_perc = 0.1 * find_image.shape[1]
            find_bbox_loc = [max(ymin - y_perc, 0), max(xmin - x_perc, 0), min(
                ymax + y_perc, find_image.shape[1]), min(xmax + x_perc, find_image.shape[0])]
        bbox = [int(xa) for xa in [max(0, find_bbox_loc[1] - (xmax - xmin)), min(find_image.shape[0], find_bbox_loc[3] + (xmax - xmin)),
                                   max(0, find_bbox_loc[0] - (ymax - ymin)), min(find_image.shape[1], find_bbox_loc[2] + (xmax - xmin))]]
        corr_image, best_local, bbox_data = find_template_for_ransac(
            find_image[bbox[0]:bbox[1], bbox[2]:bbox[3], :], template)
        diff_x = - xmin + bbox_data[0] + bbox[0]
        diff_y = - ymin + bbox_data[2] + bbox[2]
        contour_x = x + diff_x
        contour_y = y + diff_y
        dst.append([contour_y, contour_x])
        corr_images[(y, x)] = [corr_image, best_local,
                               diff_x, diff_y, template]
    # ransac
    src = np.array(contour_list_fg)
    dst = np.array(dst)
    transform = SimilarityTransform  # ProjectiveTransform
    model = transform()
    model.estimate(src, dst)
    robust_transformed_dst = model(src)
    distances = np.sqrt(((robust_transformed_dst - dst) ** 2).sum(axis=1))
    real_outliers = np.where(distances > 10)[0]
    value_choice = [0, 2]  # see find_template_for_ransac
    if len(real_outliers) > 0:
        for k in real_outliers:
            new_coord = robust_transformed_dst[k, :]
            diff_best_coord = dst[k, :] - new_coord
            x_local = corr_images[tuple(
                contour_list_fg[k])][1][0] + (new_coord[0] - dst[k, 0])
            y_local = corr_images[tuple(
                contour_list_fg[k])][1][1] + (new_coord[1] - dst[k, 1])
            im = corr_images[tuple(contour_list_fg[k])][0]
            y_local_range = [max(y_local - 150, 0),
                             min(y_local + 150, im.shape[0])]
            x_local_range = [max(x_local - 150, 0),
                             min(x_local + 150, im.shape[1])]
            minMaxValues = cv2.minMaxLoc(
                im[y_local_range[0]:y_local_range[1], x_local_range[0]:x_local_range[1]])
            dst[k, :] = [new_coord[1] + (x_local_range[0] - x_local) + minMaxValues[value_choice[-1]]
                         [1], new_coord[0] + (y_local_range[0] - y_local) + minMaxValues[value_choice[-1]][0]]
    model_robust_nn, inliers = ransac(
        (src, dst), transform, min_samples=4, residual_threshold=3, max_trials=200)
    out_contours = None
    model_nn = transform()
    model_nn.estimate(src, dst)
    if contours_to_move:
        out_contours = [(model_robust_nn(src_c)).tolist()
                        for src_c in contours_to_move]
    return dst.tolist(), out_region[0], out_contours


def find_template_ransac(input_image: np.ndarray, contour_list_fg: list[tuple[int, int]], contour_list_bg: list[tuple[int, int]], find_image: np.ndarray, find_bbox: tuple[int, int, int, int], min_size: int = 200, contours_to_move: list[tuple[int, int]] = None, transform: Callable = SimilarityTransform) -> tuple[list[list[tuple[int, int]]], list[tuple[int, int]]]:
    """finds templates with ransac

    :param input_image: input image
    :type input_image: ndarray
    :param contour_list_fg: contour list foreground
    :type contour_list_fg: list of tupel
    :param contour_list_bg: contour list background
    :type contour_list_bg: list of tupel
    :param find_image: image to search for
    :type find_image: ndarray
    :param find_bbox: bbox to search for
    :type find_bbox: ndarray
    :param min_size: min size, defaults to 100
    :type min_size: int, optional
    :param contours_to_move: list of coordinates to transform according to 'best-fit-transform', defaults to None
    :type contours_to_move: list of list of [x,y](None), optional
    :param transform: transformation type, defaults to SimilarityTransform
    :type transform: skimage.Transform, optional
    :return: distance array, list of contours 
    :rtype: tuple[list[list[tuple[int, int]]], list[tuple[int, int]]]
    """
    out_region, _ = find_template_contour(input_image, contour_list_bg, [find_image], [
                                          find_bbox], min_size=min_size, template_bbox=None)
    dst = []
    corr_images = {}
    for (y, x) in contour_list_fg:
        xmin = int(np.max([0, x - old_div(min_size, 2)]))
        xmax = int(np.min([input_image.shape[0], x + old_div(min_size, 2)]))
        ymin = int(np.max([0, y - old_div(min_size, 2)]))
        ymax = int(np.min([input_image.shape[1], y + old_div(min_size, 2)]))
        template = input_image[xmin:xmax, ymin:ymax, :]
        if find_bbox is None:
            find_bbox = [0, 0, find_image.shape[1], find_image.shape[0]]
        elif find_bbox == 'auto':
            x_perc = 0.1 * find_image.shape[0]
            y_perc = 0.1 * find_image.shape[1]
            find_bbox = [max(ymin - y_perc, 0), max(xmin - x_perc, 0), min(
                ymax + y_perc, find_image.shape[1]), min(xmax + x_perc, find_image.shape[0])]
        bbox = [int(xa) for xa in [max(0, find_bbox[1] - (xmax - xmin)), min(find_image.shape[0], find_bbox[3] + (xmax - xmin)),
                                   max(0, find_bbox[0] - (ymax - ymin)), min(find_image.shape[1], find_bbox[2] + (xmax - xmin))]]
        corr_image, best_local, bbox_data = find_template_for_ransac(
            find_image[bbox[0]:bbox[1], bbox[2]:bbox[3], :], template)
        diff_x = - xmin + bbox_data[0] + bbox[0]
        diff_y = - ymin + bbox_data[2] + bbox[2]
        contour_x = x + diff_x
        contour_y = y + diff_y
        dst.append([contour_y, contour_x])
        corr_images[(y, x)] = [corr_image, best_local,
                               diff_x, diff_y, template]
    # ransac
    src = np.array(contour_list_fg)
    dst = np.array(dst)
    model = transform()
    model.estimate(src, dst)
    model_robust, inliers = ransac_transform(
        (src, dst), transform, min_samples=4, residual_threshold=3, max_trials=2000)  # max_trials=2000)
    robust_transformed_dst = model_robust(src)
    distances = np.sqrt(((robust_transformed_dst - dst) ** 2).sum(axis=1))
    real_outliers = np.where(distances > 10)[0]
    value_choice = [1, 3]  # see find_template_for_ransac
    if len(real_outliers) > 0:
        for k in real_outliers:
            new_coord = robust_transformed_dst[k, :]
            diff_best_coord = dst[k, :] - new_coord
            x_local = corr_images[tuple(
                contour_list_fg[k])][1][0] + (new_coord[0] - dst[k, 0])
            y_local = corr_images[tuple(
                contour_list_fg[k])][1][1] + (new_coord[1] - dst[k, 1])
            im = corr_images[tuple(contour_list_fg[k])][0]
            y_local_range = [max(y_local - 150, 0),
                             min(y_local + 150, im.shape[0])]
            x_local_range = [max(x_local - 150, 0),
                             min(x_local + 150, im.shape[1])]
            minMaxValues = cv2.minMaxLoc(
                im[y_local_range[0]:y_local_range[1], x_local_range[0]:x_local_range[1]])
            dst[k, :] = [new_coord[0] + (y_local_range[0] - y_local) + minMaxValues[value_choice[-1]]
                         [0], new_coord[1] + (x_local_range[0] - x_local) + minMaxValues[value_choice[-1]][1]]
    return dst.tolist(), out_region[0]


def ransac_transform(xxx_todo_changeme, transform, weight=None, min_samples=3, max_samples=0, distances_eps=1e-5, residual_threshold=3, max_trials=200):
    """find best fit transform between numbered corrdinate points
    :param src_full: source points coordinates
    :type (src_full: list of [x,y]
    :param dst_full: destination points coordinates
    :type dst_full: list of [x,y]
    :param transform: transform to use see skimage.Transform
    :type transform: skimage.Transform
    :param weight: list of weights how to "pick" subset /(randomised)
    :type weight: list(None)
    :param min_samples: minimum number of points to randomly pick
    :type min_samples: int(3)
    :param max_samples: maximum number of points to randomly pick
    :type max_samples: type(0=all)
    :param distances_eps: stop if movement < distances_eps
    :type distances_eps: float(1e-5)
    :param residual_threshold: count ouliers if distance larger than residual_threshold
    :type residual_threshold: float(3)
    :param max_trials: maximum number of runs
    :type max_trials: int(200)
    :return: best tramnsformation model, outliers
    :rtype: skimage.Transform, list
    """
    (src_full, dst_full) = xxx_todo_changeme
    data_len = max(src_full.shape)
    if weight is None:
        weight = np.ones((data_len,))
    else:
        weight = np.copy(weight)
    weight = old_div(weight, weight.sum())
    if max_samples <= 0:
        max_samples = data_len
    max_samples = min(max_samples, (weight > 0).sum())
    min_dist = np.inf
    best_choice = None
    for run in range(max_trials):
        random_choice_r = np.random.randint(min_samples, max_samples + 1)
        random_choice = np.random.choice(
            data_len, size=random_choice_r, replace=False, p=weight)
        model = transform()
        model.estimate(src_full[random_choice], dst_full[random_choice])
        transformed_dst = model(src_full)
        distances = np.sqrt(((transformed_dst - dst_full) ** 2).sum(axis=1))
        real_outliers = np.where(distances > residual_threshold)[0]
        dist = np.mean(distances)
        if dist < min_dist:
            best_choice = np.copy(random_choice)
            min_dist = dist
        if min(real_outliers.shape) == 0 and dist <= distances_eps:
            break
    best_model = transform()
    best_model.estimate(src_full[best_choice], dst_full[best_choice])
    transformed_dst = best_model(src_full)
    distances = np.sqrt(((transformed_dst - dst_full) ** 2).sum(axis=1))
    real_inliers = np.where(distances <= residual_threshold)[0]
    return best_model, real_inliers


def find_template_ransac_weighted(input_image_list, contour_list_fg_list, find_image, find_bbox, min_size=200, contours_to_move=None, transform_model=SimilarityTransform):
    """do weighted template matching of in all templates in input_image_list:
        "Track all points in contour_list_fg_list, apply "best" transformation and refit points for outliers
    :param input_image_list: templates
    :type input_image_list: list of numpy.array
    :param contour_list_fg_list: list of centre coordinates of templates to track
    :type contour_list_fg_list: list of [x,y]
    :param find_image: image to search
    :type find_image: numpy.array
    :param find_bbox: set ROI where to track
    :type find_bbox: value(None: full image, 'auto' same as input coordinate bounding box, [x0,y0, width, height])
    :param min_size: minimal size of templates
    :type min_size: int(200)
    :param contours_to_move: list of coordinates to transform according to 'best-fit-transform'
    :type contours_to_move: list of list of [x,y](None)
    :return: transformed point set, [], transformed contours_to_move
    :rtype: list of [x,y], ,list of list of [x,y]
    """
    cv2_template_modes = [['sqdiff', cv2.TM_SQDIFF_NORMED, [0, 2]], [
        'ccorr', cv2.TM_CCORR_NORMED, [1, 3]], ['CCOEFF', cv2.TM_CCOEFF_NORMED, [1, 3]]]
    # currently used metrics with min/max value information
    dst_full = []
    src_full = []
    dst = []
    src = []
    weight = []
    data_src = []
    weight_full = []
    corr_images = {}
    for idx, (input_image, contour_list_fg) in enumerate(zip(input_image_list, contour_list_fg_list)):
        # track single point
        for p_idx, (y, x) in enumerate(contour_list_fg):
            # define region
            xmin = int(np.max([0, x - old_div(min_size, 2)]))
            xmax = int(
                np.min([input_image.shape[0], x + old_div(min_size, 2)]))
            ymin = int(np.max([0, y - old_div(min_size, 2)]))
            ymax = int(
                np.min([input_image.shape[1], y + old_div(min_size, 2)]))
            template = input_image[xmin:xmax, ymin:ymax, :]
            if find_bbox is None:
                find_bbox = [0, 0, find_image.shape[1], find_image.shape[0]]
            elif find_bbox == 'auto':
                x_perc = 0.1 * find_image.shape[0]
                y_perc = 0.1 * find_image.shape[1]
                find_bbox = [max(ymin - y_perc, 0), max(xmin - x_perc, 0), min(
                    ymax + y_perc, find_image.shape[1]), min(xmax + x_perc, find_image.shape[0])]
            bbox = [int(xa) for xa in [max(0, find_bbox[1] - (xmax - xmin)), min(find_image.shape[0], find_bbox[3] + (xmax - xmin)),
                                       max(0, find_bbox[0] - (ymax - ymin)), min(find_image.shape[1], find_bbox[2] + (xmax - xmin))]]
            src_local = dict()
            dst_local = dict()
            corr_im = []
            best_local_set = set([])
            # track using all metrics
            for t_mode in cv2_template_modes:
                corr_image, best_local, bbox_data = find_template_for_ransac(
                    find_image[bbox[0]:bbox[1], bbox[2]:bbox[3], :], template, mode=t_mode[1], best_value_choice=t_mode[2])
                diff_x = - xmin + bbox_data[0] + bbox[0]
                diff_y = - ymin + bbox_data[2] + bbox[2]
                contour_x = x + diff_x
                contour_y = y + diff_y
                dst_full.append([contour_y, contour_x])
                src_full.append(contour_list_fg_list[0][p_idx])
                weight_full.append(corr_image[best_local[::-1]])
                data_src.append((idx, t_mode[0], p_idx))
                corr_images[(idx, t_mode[0], p_idx)] = [
                    corr_image, best_local, diff_x, diff_y, template]
                corr_im.append(corr_image)
                src_local[best_local] = contour_list_fg_list[0][p_idx]
                dst_local[best_local] = [contour_y, contour_x]
            # average all "correlation" images per metric
            corr_im = np.mean(corr_im, axis=0)
            for best_local in src_local:
                src.append(src_local[best_local])
                dst.append(dst_local[best_local])
                weight.append(corr_im[best_local[::-1]])
    src = np.array(src)
    dst = np.array(dst)
    src_full = np.array(src_full)
    dst_full = np.array(dst_full)
    weight = np.array(weight).astype(float)
    weight_full = np.array(weight_full).astype(float)
    # define Transform mpodel to use
    transform = transform_model
    model = transform()
    model.estimate(src, dst)
    model_robust, inliers = ransac_transform((src, dst), transform, weight=old_div(weight, weight.sum(
    )), min_samples=max(old_div(max(dst.shape), 6), 4), residual_threshold=3, max_trials=200)
    robust_transformed_dst = model_robust(src_full)
    distances = np.sqrt(((robust_transformed_dst - dst_full) ** 2).sum(axis=1))
    real_outliers = np.where(distances > 10)[0]
    value_choice = [1, 3]  # see find_template_for_ransac
    if len(real_outliers) > 0:
        # for all outliers find good point close to "best-fit" transformed
        # point
        for k in real_outliers:
            new_coord = robust_transformed_dst[k, :]
            diff_best_coord = dst_full[k, :] - new_coord
            x_local = corr_images[data_src[k]][1][0] + \
                (new_coord[0] - dst_full[k, 0])
            y_local = corr_images[data_src[k]][1][1] + \
                (new_coord[1] - dst_full[k, 1])
            im = corr_images[data_src[k]][0]
            y_local_range = [max(y_local - 150, 0),
                             min(y_local + 150, im.shape[0])]
            x_local_range = [max(x_local - 150, 0),
                             min(x_local + 150, im.shape[1])]
            minMaxValues = cv2.minMaxLoc(
                im[y_local_range[0]:y_local_range[1], x_local_range[0]:x_local_range[1]])
            dst_full[k, :] = [new_coord[0] + (y_local_range[0] - y_local) + minMaxValues[value_choice[-1]]
                              [0], new_coord[1] + (x_local_range[0] - x_local) + minMaxValues[value_choice[-1]][1]]
        model_robust, inliers = ransac_transform((src_full, dst_full), transform, weight=old_div(
            weight_full, weight_full.sum()), min_samples=max(old_div(max(dst.shape), 6), 4), residual_threshold=3, max_trials=200)
    out_contours = None
    if contours_to_move:
        out_contours = [(model_robust(src_c)) for src_c in contours_to_move]
    robust_transformed_dst = model_robust(contour_list_fg_list[0])
    quality = 0
    return robust_transformed_dst, [], out_contours


def relabelMap(labelledImage:np.ndarray, posLabel:list[tuple[int,int]]) -> np.ndarray:
    """relabel labelled image , only keep posLabels and relabel them into 1...n

    :param labelledImage: labelled image
    :type labelledImage: ndarray
    :param posLabel: list of labels to keep
    :type posLabel: list[tuple[int,int]]
    :rtype: ndarray
    """
    labeledSITKNew = np.zeros_like(labelledImage)
    for k, v in zip(posLabel, list(range(1, len(posLabel) + 1))):
        labeledSITKNew[labelledImage == k] = v
    return labeledSITKNew
