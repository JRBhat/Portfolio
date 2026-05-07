"""Pipeline orchestrator for QR-code-based scan registration and mask generation.

Orchestrates QR detection -> registration -> mask generation. Reads input
scans from ``PATH`` and writes outputs to ``BAD_PATH`` (insufficient QR
corner detections), ``INV_PATH`` (inverted scans), and ``OUTPATH``
(generated binary/overlay masks).
"""
import os
from detect_qrcode import detect_qrcodes_from_skewed_image
from scan_registration import registration_step
import logging
import shutil
from create_binary_mask_overlay import generate_masks
import re

# Path to skewed scanned images folder
PATH = "data/scans/"

"""DUMMY PTX, USUALLY EMPTY BUT NECESSARY TO BE PASSED"""
DUMMY_PTX_PATH = "data/reference/dummy.ptx"

"""ALWAYS ENSURE THIS RESEMBLES THE GOLDEN STANDARD. THE PROGRAM USES THESE COORDINATES TO BE WHAT'S CONSIDERED PERFECTLY ORIENTED"""
REF_PTX_PATH = "data/reference/S000F00T00VAL.ptx"

SUBJECT_ID_PATTERN = re.compile(r"S[0-9]{3}")
CANONICAL_SKEWED_SUFFIX = "F01T01SKW.tif"


def move_files(img_path, bad_path):
    """Move the four-file group (image + ptx, both SKW and REG variants) for `img_path` into `bad_path`. Missing files are skipped silently."""

    img_reg_path =img_path.replace("SKW", "REG")
    ptx_path = img_path.replace(".tif", ".ptx")
    ptx_reg_path = ptx_path.replace("SKW", "REG")

    for p in [img_path, img_reg_path, ptx_path, ptx_reg_path]:
        try:
            shutil.move(p, os.path.join(bad_path, os.path.basename(p)))
            logging.debug(f"{p} successfully moved to bad output folder")
        except FileNotFoundError:
            continue

def main(test=False):
    """End-to-end pipeline entry point. When `test=True`, intermediate visualisations and verbose registration output are enabled."""

    LOGPATH = os.path.join(PATH, "app.log")
    BAD_PATH = os.path.join(PATH, "bad") # path which detects coordinates but < 4 coordinates (not all detected)
    INV_PATH = os.path.join(PATH, "inverted") # collects inverted images (if any)
    OUTPATH = os.path.join(PATH, "output")
    
    # initialize logging object and configure it
    logging.basicConfig(
        filename=LOGPATH,
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
        level=logging.DEBUG)
    
    # Reads all skewed images from the folder that contains all the skewed scanned images by looping over it
    for filename in os.listdir(PATH):
        if filename.endswith(".tif"):
            subject_id = filename.split(".")[0]
            if SUBJECT_ID_PATTERN.match(subject_id):
                new_filename = subject_id + CANONICAL_SKEWED_SUFFIX
                os.rename(os.path.join(PATH, filename), os.path.join(PATH, new_filename))
                filename = new_filename
                skwd_img_path = os.path.join(PATH, filename) # SKW.tif
                # detect qr code from each image and create corresponding ptx and update the coords
                status, new_skwd_img_path = detect_qrcodes_from_skewed_image(skwd_img_path, DUMMY_PTX_PATH, test=test)
                skwd_img_path = new_skwd_img_path
                filename = os.path.basename(new_skwd_img_path)
                if status == 0:
                    # register the skewed image and save new REG image, also copy the ORG.ptx to create a new REG.ptx
                    skwd_ptx_path = skwd_img_path.replace(".tif", ".ptx") # SKW.ptx
                    reg_img_save_path = skwd_img_path.replace("SKW", "REG")
                    registration_step(REF_PTX_PATH, skwd_ptx_path, skwd_img_path, reg_img_save_path, print_reg_details=test)
                    logging.debug(f"{filename} successfully registered")

                elif status == 1:
                    if not os.path.isdir(INV_PATH):
                        os.makedirs(INV_PATH, exist_ok=True)
                    move_files(os.path.join(PATH, filename), INV_PATH)
                    logging.warning(f"Inverted image {filename} detected. Skipping for now. Check log file later to make ammends..")
                    continue
                else:
                    if not os.path.isdir(BAD_PATH):
                        os.makedirs(BAD_PATH, exist_ok=True)
                    move_files(os.path.join(PATH, filename), BAD_PATH)
                    logging.error(f"{filename} coordinates < 4")
                    continue

    for filename in os.listdir(PATH):
        if filename.endswith(".tif") and "SKW" in filename:
            generate_masks(os.path.join(PATH, filename), OUTPATH)
            logging.info(f"generating the masks for {filename}")
            logging.debug(f"masks for {filename} successfully generated")
if __name__ == "__main__":
    main(test=False)


