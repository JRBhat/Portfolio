import os
import cv2
import shutil
import numpy as np







def crop_center(img, cropx, cropy):
    y, x, _ = img.shape
    startx = x // 2 - (cropx // 2)
    starty = y // 2 - (cropy // 2)
    return img[starty:starty + cropy, startx:startx + cropx, :]


def move_files(fn, inpath, outdir):
    shutil.move(os.path.join(inpath, fn), os.path.join(outdir, fn))
    raw_fn = fn.replace(".JPG", ".CR2").replace(".jpg", ".cr2")
    shutil.move(os.path.join(inpath, raw_fn), os.path.join(outdir, raw_fn))

def is_white(measured_val, w_thresh):
    return all([measured_val[0].mean() >= w_thresh, measured_val[1].mean() >= w_thresh, measured_val[2].mean() >= w_thresh])

def is_black(measured_val, blk_thresh):
    return all([measured_val[0].mean() <= blk_thresh, measured_val[1].mean() <= blk_thresh, measured_val[2].mean() <= blk_thresh])

def main():

    os.makedirs(OUT_DIR_W, exist_ok=True)
    os.makedirs(OUT_DIR_BLK, exist_ok=True)
    white_list = []
    # loop over list of fnms
    for fn in os.listdir(INPATH):
        if fn.endswith(".jpg") or fn.endswith(".JPG"):

            # read image into an array using opencv
            img = cv2.imread(os.path.join(INPATH, fn), cv2.IMREAD_COLOR)
            img_crop = crop_center(img, CROP_BOX_SIZE_IN_PX, CROP_BOX_SIZE_IN_PX)
            img_lab = cv2.cvtColor(img_crop, cv2.COLOR_BGR2LAB) # changes RGB to LAB color space
            # condition: get centre of image array
            print(fn, img_lab[0].mean(), img_lab[1].mean(), img_lab[2].mean())
            if is_white(img_lab, W_THRESH):
                white_list.append((fn, (img_lab[0].mean(), img_lab[1].mean(), img_lab[2].mean())))
                move_files(fn, INPATH, OUT_DIR_W)
            elif is_black(img_lab, BLK_THRESH):
                move_files(fn, INPATH, OUT_DIR_BLK)

    with open(os.path.join(OUT_DIR_W, "group_whites.log"), "a+") as wfile:
        for entry in white_list:
            wfile.writelines(str(entry) + "\n")

if __name__ == "__main__":
    
    INPATH = os.environ.get("STUDY_PATH", "data/study/device/session")
    OUT_DIR_W = os.path.join(INPATH, "all_whites")
    OUT_DIR_BLK = os.path.join(INPATH, "all_blacks")
    CROP_BOX_SIZE_IN_PX = 1000
    W_THRESH = 160
    BLK_THRESH = 90
    
    
    timepoints = ["T02", "T03", "T04", "T05", "T06", "T07"]
    for t in timepoints:
        TMP_PATH = INPATH
        INPATH = os.path.join(INPATH, t)
        main()
        INPATH = TMP_PATH
