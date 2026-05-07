import os
import cv2

CROP_Y = 500
CROP_X = 1030
CROP_HEIGHT = 2840
CROP_WIDTH = 3700
INPUT_PATH = r"data\raw\TIF"
MASK_PATH = r"data\masks\mask_1.tif"


def main():
    output_path = os.path.join(INPUT_PATH, "out")
    if not os.path.exists(output_path):
        os.mkdir(output_path)

    cropped_path = os.path.join(output_path, "cropped")
    if not os.path.exists(cropped_path):
        os.mkdir(cropped_path)

    mask_img = cv2.imread(str(MASK_PATH), 0)

    for filename in os.listdir(INPUT_PATH):
        if filename.endswith(".tif"):
            img = cv2.imread(os.path.join(INPUT_PATH, filename))
            res = cv2.bitwise_and(img, img, mask=mask_img)
            crop = res[CROP_Y:CROP_Y + CROP_HEIGHT, CROP_X:CROP_X + CROP_WIDTH]
            stem = os.path.splitext(filename)[0]
            cv2.imwrite(os.path.join(output_path, f"{stem}_masked.tif"), res)
            cv2.imwrite(os.path.join(cropped_path, f"{stem}_masked_cropped.tif"), crop)


if __name__ == "__main__":
    main()
