"""QR-code detection and PTX read/write helpers.

This module provides three groups of functionality:

* **Image preprocessing** -- grayscale conversion, Gaussian blur, Otsu
  thresholding and morphological hole filling, used to make the QR codes
  pop out from the surrounding scan background.
* **Contour-based QR localisation** -- finds external contours of the
  preprocessed binary image, filters them by area and side length to
  identify the four QR-code corners, then decodes their payloads with
  ``pyzbar``.
* **PTX read/write helpers** -- read/write the JSON-based ``.ptx``
  files that store contour coordinates for QR codes (id 1) and the top
  and bottom circle markers (ids 2 and 3) used downstream by the
  registration step.
"""


import cv2
from pyzbar.pyzbar import decode
import json
import numpy as np
import os
import shutil
import logging

# QR contour filtering thresholds (pixels)
QR_MIN_AREA_PX = 25_000
QR_SIDE_MIN_PX = 150
QR_SIDE_MAX_PX = 300
INVERTED_QR_WIDTH_THRESHOLD = 200

# PTX schema id constants
PTX_ID_QRCODES = 1
PTX_ID_TOP_CIRCLES = 2
PTX_ID_BOTTOM_CIRCLES = 3

# Number of retries for hole-filling when fewer than 4 QR corners are detected
FILL_HOLES_RETRY_COUNT = 6


def preprocess_image(img_path, testing=False):
    """ Load imgae, grayscale, Gaussian blur, Otsu's threshold"""
    image = cv2.imread(img_path)
    original = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7,7), 0) # A Gaussian blur is applied to reduce noise and detail.
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1] # A binary threshold is applied using Otsu's method to binarize the image.
    closed = fill_holes(thresh)
    if testing:
        cv2.imwrite(f'ROI_Test.png', closed)
        cv2.imshow('ROI', closed)
        cv2.waitKey()
    return original, closed, image

def fill_holes(thresh):
    """ Defines a kernel and apply morphological closing: This helps to close small holes in the foreground objects."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    closed_img = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=5)
    return closed_img

def get_qr_code_coords(closed_img, image, original, padding=55, testing=False):
    """ Gets QR code coordinates"""
    contours = cv2.findContours(closed_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) #Find contours: Contours are the boundaries of objects detected in the binary image.
    contours = contours[0] if len(contours) == 2 else contours[1]

    # Iterate through each contour and filter them based on shape, area, and aspect ratio to identify potential QR code regions.
    count = 0

    final_coords = []
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
        x,y, w, h = get_padded_bbox(approx, padding)
        logging.debug("%s %s %s %s", x, y, w, h)
        area = cv2.contourArea(contour)
        logging.debug("%s", area)
        cv2.rectangle(image, (x, y), (x + w, y + h), (36,255,12), 3)
        ROI = image[y:y+h, x:x+w]
        # print(len(approx), area, ar)
        if testing:
            try:
                cv2.imshow('ROI',ROI)
                cv2.waitKey()
            except cv2.error:
                logging.debug("cv2.imshow failed for ROI")

        if area > QR_MIN_AREA_PX and QR_SIDE_MIN_PX < w < QR_SIDE_MAX_PX and QR_SIDE_MIN_PX < h < QR_SIDE_MAX_PX: # get only qr codes
            cv2.rectangle(image, (x, y), (x + w, y + h), (36,255,12), 3)
            ROI = image[y:y+h, x:x+w]
            # print(len(approx), area, ar)
            data = decode(original[y:y+h, x:x+w])
            if len(data) == 0:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
                test_img = cv2.morphologyEx(original, cv2.MORPH_CLOSE, kernel, iterations=1)
                if testing:
                    cv2.imshow('ROI',test_img[y:y+h, x:x+w])
                    cv2.waitKey()
                data = decode(test_img[y:y+h, x:x+w])

            logging.debug("%s", str(data[0][0])[1:].replace("'", ""))
            # print(x, y, w, h)
            final_coords.append({"sum": x+y, "x":x, "y": y,"width": w, "height": h, "data": str(data[0][0])[1:].replace("'", "")})

            # saves the detected ROIs - for testing purposes
            if testing:
                cv2.imwrite(f'ROI_{count}.png', ROI)
                count += 1

    # sorts the sum of coordinates to ensure that the points are well positioned
    if len(final_coords) == 4:
        return sorted(final_coords, key= lambda x : x["sum"])
    else:
        logging.error("Coords mismatch <4")
        return sorted(final_coords, key= lambda x : x["sum"])

def get_padded_bbox(approx, padding):
    """Expands the bounding box of the detected QR code region to ensure it fully encompasses the QR code, and then save the region."""
    x,y,w,h = cv2.boundingRect(approx)
    x = x - padding
    y = y - padding
    w = w + 2*padding
    h = h + 2*padding
    return x, y, w, h

# PTX file schema:
#   id == 1  -> QR-code corner coordinates (list of [x, y] centre points)
#   id == 2  -> top circle markers (list of [x, y] with a parallel 'radius' list)
#   id == 3  -> bottom circle markers (list of [x, y] with a parallel 'radius' list)
# Each entry has 'contour' (list of [x, y]) and an optional 'radius' list.

def update_ptx_with_new_coords(coords_list, path, dummy_ptx_path):
    """Updates the contour key with values corressponding to the coordinates of the detected QR codes"""

    data = read_ptx_file(dummy_ptx_path)
    fn = os.path.basename(path)
    new_path = dummy_ptx_path.replace("dummy", fn.replace(".tif", ""))
    skw_ptx_path = write_ptx_file(new_path, coords_list, data)
    new_loc_skw_ptx = os.path.join(os.path.dirname(path), os.path.basename(skw_ptx_path))
    shutil.move(skw_ptx_path, new_loc_skw_ptx)

def write_ptx_file(new_file_path, coords_list, data):
    """writes the values to the corresponding key in the ptx"""
    for item in data:
        if item["id"] == PTX_ID_QRCODES:
            item["contour"] = [[ele["x"]+ele["width"]//2, ele["y"]+ele["height"]//2] for ele in coords_list]

    with open(new_file_path, "w") as fptx:
        json.dump(data, fptx, indent=4)
    return new_file_path

def read_ptx_file(file_path):
    """Extracts the data from the ptx file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def extract_coordinates(data):
    """Extracts the coordinates from the data from the ptx"""
    arr_dict = {}
    for item in data:
        if item['id'] == PTX_ID_QRCODES:
            arr_dict["qrcoords"] = np.array(item['contour'])
        elif item["id"] == PTX_ID_TOP_CIRCLES:
            arr_dict["top_circles"] = np.array(item['contour'])
        elif item["id"] == PTX_ID_BOTTOM_CIRCLES:
            arr_dict["bottom_circles"] = np.array(item['contour'])
        else:
            unknown_id = item["id"]
            raise ValueError(f"No object with id == {unknown_id} found in the PTX file")
    return arr_dict

def rename_file_to_standard_barcode(scanned_img_path, qrcode_coords_data_dict, n):
    try:
        if "Studie" in qrcode_coords_data_dict[n]["data"]:
            logging.debug("%s", qrcode_coords_data_dict[n]["data"])
            new_fn_path = scanned_img_path.replace(os.path.basename(scanned_img_path), qrcode_coords_data_dict[n]["data"][-4:]+"F01T01SKW.tif")
            try:
                os.rename(scanned_img_path, new_fn_path)
            except FileExistsError:
                logging.error("Filename already exists. Reverting to original file name")
                return scanned_img_path
            return new_fn_path
        else:
            logging.warning("Possible QR code containing Studyno was not read")
            return None
    except TypeError:
        logging.error("Possible Coordinates mismatch")
        return None

def detect_qrcodes_from_skewed_image(path, dummy_ptx_path, pad=20, test=False):

    original, thresh, image = preprocess_image(path, testing=test)

    sorted_qrcode_coords = get_qr_code_coords(thresh, image,  original, padding=pad, testing=test)
    new_path = rename_file_to_standard_barcode(path, sorted_qrcode_coords, 0)

    if new_path is None:
        for num, _ in enumerate(sorted_qrcode_coords):
            new_path = rename_file_to_standard_barcode(path, sorted_qrcode_coords, num)
            if new_path is not None:
                break

    if new_path is not None:
        path = new_path


    if len(sorted_qrcode_coords)==4 and int(sorted_qrcode_coords[0]["width"]) < INVERTED_QR_WIDTH_THRESHOLD: # threshold width of biggest QR code
        log_path = os.path.dirname(path)
        with open(os.path.join(log_path, "images_inverted.log"), "a+") as logf:
            logf.writelines(f"{path}\n")
            return 1, path

    if len(sorted_qrcode_coords)!=4:
        for _ in range(FILL_HOLES_RETRY_COUNT):
            closed_img = fill_holes(thresh)
            sorted_qrcode_coords = get_qr_code_coords(closed_img, image,  original, padding=pad, testing=test)
            if len(sorted_qrcode_coords) == 4:
                logging.debug("%s", sorted_qrcode_coords)
        return 2, path
    else:
        update_ptx_with_new_coords(sorted_qrcode_coords, path, dummy_ptx_path)
        return 0, path

def main():
    # PATH = "data/scans/S999F99T99SKW.tif"
    # DUMMY_PTX_PATH = "data/reference/dummy.ptx"
    # PAD = 5

    # detect_qrcodes_from_skewed_image(PATH, DUMMY_PTX_PATH, pad=PAD)
    pass

if __name__ == "__main__":
    main()
