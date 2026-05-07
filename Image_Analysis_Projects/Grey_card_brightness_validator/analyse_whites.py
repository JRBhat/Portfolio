import os
import cv2
import numpy as np
import exifread
import sys
from pathlib import Path
from matplotlib import pyplot as plt
from ImageAnalysis.ColorConversion.sRGB_conversions import sRGB_to_lab
def crop_center(img, cropx, cropy):
    y, x, _ = img.shape
    startx = x // 2 - (cropx // 2)
    starty = y // 2 - (cropy // 2)
    return img[starty:starty + cropy, startx:startx + cropx, :]

def get_original_time_from_exif(filename, main_study_path):
    """
    Retrieve original "image taken" timestamp from the file metadata/exif

        :param filename: filename string literal
        :type filename: str
        :param main_study_path: path to root study folder
        :type main_study_path: str
        :return: timestamp
        :rtype: str ('%Y:%m:%d %H:%M:%S')
        """   

    timestamp = None
    abs_path_to_image = os.path.join(main_study_path, filename)

    # read creation time from metadata using exifread
    with open(abs_path_to_image, 'rb') as f:
        tags = exifread.process_file(f)
    for tag in tags.keys():
        if tag == 'Image DateTime':
            timestamp = str(tags[tag])
            break
    if timestamp is not None:
        return timestamp
    else:
        print(f"Time not found in EXIF metadata for {filename} Exiting")
        sys.exit()

def get_time_sorted_filelist_from_basepath(main_study_path, file_ext):
    """
    get a list of filenames and times, sorted according to their timestamps

        :param main_study_path: path to root study folder
        :type main_study_path: str
        :param file_ext: image extension to be detected ; .jpg is default
        :type file_ext: str
        :return: time sorted list with (filenames and timestamp) tuple
        :rtype: list
    """ 
    
    file_list = []
    for entry in main_study_path.iterdir():
        # for each path element; check if it is a file or not; if True then create a separate list with only these files
        if entry.is_file() and entry.suffix==file_ext:
            file_list.append((entry.name, get_original_time_from_exif(entry.name, main_study_path)))
    # sort the files according to their timestamps
    file_list_sorted = sorted(file_list, key=lambda x: x[1])
    return file_list_sorted

def main() -> None:
    path = Path(os.environ.get("STUDY_PATH", "data/study/device/session/all_whites"))

    white_list = []
    for fn in os.listdir(path):
        if fn.endswith(".jpg"):
            img = cv2.imread(os.path.join(path, fn))
            img_crop = crop_center(img, 500, 500)
            img_rgb = cv2.cvtColor(img_crop, cv2.COLOR_BGR2RGB)
            img_lab = sRGB_to_lab(img_rgb)
            white_list.append((fn, (np.mean([x[0][0] for x in img_lab]), np.mean([x[0][1] for x in img_lab]), np.mean([x[0][2] for x in img_lab]))))

    timepoint_list = get_time_sorted_filelist_from_basepath(path, ".jpg")

    list_to_plot = []
    for fn, time in timepoint_list:
        tup = list(filter(lambda x: fn in x[0], white_list))
        list_to_plot.append((fn, time, tup))

    x_axis_range = []
    y1_axis_range = []

    for item in list_to_plot:
        x_axis_range.append(str(item[0]) + "_" + str(item[1]))
        y1_axis_range.append(item[2][0][1][0])

    plt.plot(x_axis_range, y1_axis_range)
    plt.xticks(rotation=90)
    plt.show()

    with open(os.path.join(path, "plot_log.txt"), "w") as wfile:
        for entry in list_to_plot:
            wfile.writelines(str(entry) + "\n")


if __name__ == "__main__":
    main()
