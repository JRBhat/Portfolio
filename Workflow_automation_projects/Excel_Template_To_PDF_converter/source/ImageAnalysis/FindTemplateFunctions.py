import cv2
import numpy as np
from past.utils import old_div
import pylab
from skimage.transform import AffineTransform, ProjectiveTransform
from skimage.measure import ransac
from .ResizeAndCropFunctions import cropBBoxITK


def find_template_central(image: np.ndarray, template: np.ndarray, method: str = None, cropimage: np.ndarray = None, showdata: bool = False) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int, int], np.ndarray]:
    """finds template central on image

    :param image: image
    :type image: ndarray
    :param template: template to find on image
    :type template: ndarray
    :param method: method for template matching, defaults to None
    :type method: cv.TM_SQDIFF/cv.TM_SQDIFF_NORMED/cv.TM_CCORR/cv.TM_CCORR_NORMED/ cv.TM_CCOEFF/cv.TM_CCOEFF_NORMED, optional
    :param cropimage: cropped image, defaults to None
    :type cropimage: ndarray, optional
    :param showdata: show data (pylab.show()), defaults to False
    :type showdata: bool, optional
    :return: only found template highlighted (rest of image 0), center of template, bounding box of the template, cropped template
    :rtype: tuple[ndarray, ndarray, tuple[int, int, int, int], ndarray]
    """
    assert image.dtype == template.dtype
    if method is None:
        method = cv2.TM_CCORR_NORMED
    method_value = {cv2.TM_CCORR_NORMED: [1, 3],
                    cv2.TM_SQDIFF_NORMED: [0, 2],
                    cv2.TM_CCOEFF_NORMED: [1, 3],
                    cv2.TM_CCORR: [1, 3],
                    cv2.TM_SQDIFF: [0, 2],
                    cv2.TM_CCOEFF: [1, 3]}
    (h, w) = template.shape[:2]
    value_choice = method_value[method]
    ttype = image.dtype
    if ttype.type is np.uint16:
        image = (old_div(image, 255)).astype(np.uint8)
        template = (old_div(template, 255)).astype(np.uint8)
    out = cv2.matchTemplate(image, template, method)
    range_min_mx = [out.min(), out.max()]
    range_best = cv2.matchTemplate(template, template, method)
    minMaxValues = cv2.minMaxLoc(out)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(out)
    if cropimage is None:
        cropimage = image
    bd = 0  # 100
    testImAuss, bbox_crop = cropBBoxITK(
        image, [minMaxValues[value_choice[-1]][0], minMaxValues[value_choice[-1]][1], w, h], border=bd)
    best_point = minMaxValues[value_choice[-1]]
    if abs(range_best - range_min_mx[0]) < abs(range_best - range_min_mx[1]):
        # , alpha=range_best, beta=range_min_mx[1])
        out = 1.0 - (old_div((out - range_best),
                     (range_min_mx[1] - range_best))).clip(0, 1)
    else:
        out = (
            old_div((out - range_min_mx[0]), (range_best - range_min_mx[0]))).clip(0, 1)
    out_centralised = np.zeros(image.shape[:2], dtype=out.dtype)
    out_centralised[old_div(h, 2): old_div(-h, 2) + 1,
                    old_div(w, 2): old_div(-w, 2) + 1] = out
    if showdata:
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
    return out_centralised, np.array(best_point)[::-1] + np.array([old_div(h, 2), old_div(w, 2)]), (minMaxValues[value_choice[-1]][1], (minMaxValues[value_choice[-1]][1] + h), minMaxValues[value_choice[-1]][0], minMaxValues[value_choice[-1]][0] + w), testImAuss


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
    :return: template , bounding box
    :rtype: tuple[ndarray, tuple[int, int, int, int]]
    """
    assert image.dtype == template.dtype
    (h, w) = template.shape[:2]
    method = cv2.TM_CCORR_NORMED
    value_choice = [1, 3]
    ttype = image.dtype
    ma = None
    mi = None
    if not((ttype.type is np.uint8) or (ttype.type is np.uint16)):
       # LOGGER.warning("Imagetype is not supported, do conversion!")
        ma = max(image.max(), template.max())
        mi = min(image.min(), template.min())
        image = ((image - mi) / (ma - mi) * 255).astype(np.uint8)
        template = ((template - mi) / (ma - mi) * 255).astype(np.uint8)
        if cropimage is None:
            cropimage = (image.astype(np.double) / 255.0 * (ma - mi)) + mi
    if ttype.type is np.uint16:
        image = (old_div(image, 255)).astype(np.uint8)
        template = (old_div(template, 255)).astype(np.uint8)
        if cropimage is None:
            cropimage = image
    out = cv2.normalize(cv2.matchTemplate(image, template, method))
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(out)
    minMaxValues = cv2.minMaxLoc(out)
    bd = 0  # 100
    testImAuss, bbox_crop = cropBBoxITK(cropimage, [
                                        minMaxValues[value_choice[-1]][0], minMaxValues[value_choice[-1]][1], w, h], border=bd)
    if showdata:
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


def find_template_for_ransac(image: np.ndarray, template: np.ndarray) -> tuple[np.ndarray, int, tuple[int, int, int, int]]:
    """finds  all possible template positions 

    :param image: image
    :type image: ndarray
    :param template: template to find
    :type template: ndarray
    :return: normalized template, index of maximum value normalized template bounding box
    :rtype: ndarray, tupel
    """
    assert image.dtype == template.dtype
    (h, w) = template.shape[:2]
    method = cv2.TM_CCORR_NORMED
    value_choice = [1, 3]
    ttype = image.dtype
   # if np.issubdtype(ttype, int) and not ((ttype.type is np.uint8) or (ttype.type is np.uint16)):
    # LOGGER.warning("Imagetype is integer but not uint8 or uint16!")
    if ttype.type is np.uint16:
        image = (old_div(image, 255)).astype(np.uint8)
        template = (old_div(template, 255)).astype(np.uint8)
    out = cv2.normalize(cv2.matchTemplate(image, template, method))
    minMaxValues = cv2.minMaxLoc(out)
    return out, minMaxValues[value_choice[-1]], (minMaxValues[value_choice[-1]][1], (minMaxValues[value_choice[-1]][1] + h), minMaxValues[value_choice[-1]][0], minMaxValues[value_choice[-1]][0] + w)


def find_template_contour(input_image: np.ndarray, contour_list: list[list[int, int]], find_images: list[np.ndarray], find_bbox: list[tuple[int, int, int, int]], min_size: int = 200, template_bbox: tuple[int, int, int, int] = None) -> tuple[list[tuple[int, int]], list[list[int, int]]]:
    """finds contours

    :param input_image: template image
    :type input_image: ndarray
    :param contour_list: list of contours
    :type contour_list: list[list[int,int]]
    :param find_images: images
    :type find_images: list[ndarray]
    :param find_bbox: list of bboxes (mapped to find images)
    :type find_bbox: list[tuple[int,int,int,int]]
    :param min_size: for bboxes, defaults to 200
    :type min_size: int, optional
    :param template_bbox: template bbox, defaults to None
    :type template_bbox: tuple[int,int,int,int], optional
    :return: list of contours, differenc between coordinates of contours
    :rtype: tuple[list[tuple[int,int]],list[list[int,int]]]
    """
    y = np.array([z[0] for z in contour_list])
    x = np.array([z[1] for z in contour_list])
    if template_bbox is None:
        def find_correct_bbox(input_image_shape: tuple[int, int], min_size: int, xmax: int, xmin: int) -> int:
            """finds a bbox

            :param input_image_shape: input image shape
            :type input_image_shape: tuple[int,int]
            :param min_size: minsizefor bbox
            :type min_size: int
            :param xmax: max x
            :type xmax: int
            :param xmin: min x
            :type xmin: int
            :return: max x and min x
            :rtype: int
            """
            step = 0
            while step < 10 and xmax - xmin < min_size and xmin > 0 and xmin < input_image_shape:
                diff = old_div((min_size - (xmax - xmin)), 2) + 1
                xmin = int(np.max([0, xmin - diff]))
                xmax = int(np.min([input_image_shape, xmax + diff]))
                step = step + 1
            return xmax, xmin
        xmin = int(np.max([0, x.min()]))
        xmax = int(np.min([input_image.shape[0], x.max()]))
        xmax, xmin = find_correct_bbox(
            input_image.shape[0], min_size, xmax, xmin)
        ymin = int(np.max([0, y.min()]))
        ymax = int(np.min([input_image.shape[1], y.max()]))
        ymax, ymin = find_correct_bbox(
            input_image.shape[1], min_size, ymax, ymin)
    else:
        xmin, xmax, ymin, ymax = template_bbox
    template = input_image[xmin:xmax, ymin:ymax, :]
    output = []
    diff_output = []
    for k in range(len(find_images)):
        if find_bbox[k] is None:
            find_bbox[k] = [0, 0, find_images[k].shape[1],
                            find_images[k].shape[0]]
        elif find_bbox[k] == 'auto':
            x_perc = 0.1 * find_images[k].shape[0]
            y_perc = 0.1 * find_images[k].shape[1]
            find_bbox[k] = [max(ymin - y_perc, 0), max(xmin - x_perc, 0), min(
                ymax + y_perc, find_images[k].shape[1]), min(xmax + x_perc, find_images[k].shape[0])]
        bbox = [int(xa) for xa in [max(0, find_bbox[k][1] - (xmax - xmin)), min(find_images[k].shape[0], find_bbox[k][3] + (xmax - xmin)),
                                   max(0, find_bbox[k][0] - (ymax - ymin)), min(find_images[k].shape[1], find_bbox[k][2] + (xmax - xmin))]]
        testImAuss, bbox_data = find_template(
            find_images[k][bbox[0]:bbox[1], bbox[2]:bbox[3], :], template, showdata=False)
        diff_x = - xmin + bbox_data[0] + bbox[0]
        diff_y = - ymin + bbox_data[2] + bbox[2]
        contour_x = x + diff_x
        contour_y = y + diff_y
        output.append(
            list(map(list, list(zip(contour_y.tolist(), contour_x.tolist())))))
        diff_output.append([diff_x, diff_y])
    return output, diff_output


def find_template_ransac(input_image: np.ndarray, contour_list_fg: list[list[int, int]], contour_list_bg: list[list[int, int]], find_image: np.ndarray, find_bbox: list[int, int, int, int], min_size=100) -> tuple[np.ndarray, np.ndarray]:
    """finds templates with ransac

    :param input_image: input image
    :type input_image: nd array
    :param contour_list_fg: contour list foreground
    :type contour_list_fg: list[list[int,int]]
    :param contour_list_bg: contour list background
    :type contour_list_bg: list[list[int,int]]
    :param find_image: image to search for
    :type find_image: ndarray
    :param find_bbox: bbox to search for
    :type find_bbox: list[int,int,int,int]
    :param min_size: min size, defaults to 100
    :type min_size: int, optional
    :return: distance array, found template 
    :rtype: tuple[ndarray, ndarray]
    """
    # , PiecewiseAffineTransform, AffineTransform
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
        corr_images[(y, x)] = [corr_image, best_local, diff_x, diff_y]
    # ransac
    src = np.array(contour_list_fg)
    dst = np.array(dst)
    model = ProjectiveTransform()
    model.estimate(src, dst)
    model_robust, inliers = ransac(
        (src, dst), ProjectiveTransform, min_samples=4, residual_threshold=3, max_trials=200)
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
    model_robust, inliers = ransac(
        (src, dst), ProjectiveTransform, min_samples=4, residual_threshold=3, max_trials=200)
    robust_transformed_dst = model_robust(src)
    distances = np.sqrt(((robust_transformed_dst - dst) ** 2).sum(axis=1))
    real_outliers = np.where(distances > 10)[0]
    return dst.tolist(), out_region[0]


def find_template_ransac_affine(input_image: np.ndarray, contour_list_fg: list[list[int, int]], contour_list_bg: list[list[int, int]], find_image: np.ndarray, find_bbox: tuple[int, int, int, int], min_size: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """find template in affine image, transforms image

    :param input_image: input image
    :type input_image: ndarray
    :param contour_list_fg: contour list foreground
    :type contour_list_fg: list[list[int,int]]
    :param contour_list_bg: contour list background
    :type contour_list_bg: list[list[int,int]]
    :param find_image: image to search for
    :type find_image: ndarray
    :param find_bbox: bbox to search for
    :type find_bbox: ndarray
    :param min_size: min size, defaults to 100
    :type min_size: int, optional
    :return: distance array, found template 
    :rtype: tuple[ndarray, ndarray]
    """
    # , PiecewiseAffineTransform, AffineTransform
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
        corr_images[(y, x)] = [corr_image, best_local, diff_x, diff_y]
    # ransac
    src = np.array(contour_list_fg)
    dst = np.array(dst)
    model = AffineTransform()
    model.estimate(src, dst)
    model_robust, inliers = ransac(
        (src, dst), AffineTransform, min_samples=4, residual_threshold=3, max_trials=200)
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
    model_robust, inliers = ransac(
        (src, dst), AffineTransform, min_samples=4, residual_threshold=3, max_trials=200)
    robust_transformed_dst = model_robust(src)
    distances = np.sqrt(((robust_transformed_dst - dst) ** 2).sum(axis=1))
    real_outliers = np.where(distances > 10)[0]
    return dst.tolist(), out_region[0]
