"""
Visia Macbeth Colour Chart Validator — subplot visualization.
Validates LAB colour accuracy of Visia camera captures against Macbeth ColorChecker
reference values. Plots per-colour L* deviation across all image capture modes.
"""
import os
import cv2
import numpy as np
import pprint
import matplotlib.pyplot as plt



# Path
path_std2 = r"data/sample_images/sample_Standard_2.tif"
path_std1 = r"data/sample_images/sample_Standard_1.tif"
path_xpol = r"data/sample_images/sample_Cross-Polarized.tif"
path_ppol = r"data/sample_images/sample_Parallel-Polarized.tif"

paths = [path_std2, path_std1, path_xpol, path_ppol]
# loop over all images in path and save the image name


##### specify ROI mask dimensions and apply mask over image
# Define the ROI coordinates (x,y,w,h)
color_chart_coord_dict = {
"dark_skin"     : (712, 4960, 80, 80),    
"light_skin"    : (842, 4960, 80, 80),	    
"blue_sky"      : (972, 4960, 80, 80), 
"foliage"       : (1102, 4960, 80, 80),	        
"blue_flower"	: (1232, 4960, 80, 80),    
"bluish_green"  : (1362, 4960, 80, 80),	
"orange"        : (2270, 4960, 80, 80),	        
"purplish_blue": (2400, 4960, 80, 80),
"moderate_red"  : (2530, 4960, 80, 80),	
"purple"        : (2660, 4960, 80, 80),	        
"yellow_green"  : (2790, 4960, 80, 80),	
"orange_yellow" : (2920, 4960, 80, 80),	
"blue"          : (710, 5090, 80, 80),	        
"green"         : (840, 5090, 80, 80),	        
"red"	        : (970, 5090, 80, 80),            
"yellow"        : (1100, 5090, 80, 80),        
"magenta"	    : (1230, 5090, 80, 80),
"cyan"          : (1360, 5090, 80, 80),
"white"         : (1492, 4960, 80, 80),	        
"neutral_8"     : (1622, 4960, 80, 80),	    
"neutral_6.5"   : (1752, 4960, 80, 80),	    
"neutral_5"     : (1882, 4960, 80, 80),	    
"neutral_3.5"   : (2009, 4960, 80, 80),
"black"         : (2140, 4960, 80, 80),
"long_grey_patch": (330, 5235, 3035, 50)
}	

color_check_standard_dict = {
"dark_skin": (38, 12, 14),
"light_skin":(66, 13, 17),
"blue_sky":(51, 0, -22),
"foliage":(43, -17, 22),
"blue_flower":(56, 13, -25),
"bluish_green" :(72, -31, 1),
"orange" :(62, 28, 58),
"purplish_blue"	:(41, 18, -43),
"moderate_red" :(52, 43, 15),
"purple" :(31, 26, -23),
"yellow_green" :(72, -28, 59),
"orange_yellow" :(72, 12, 67),
"blue" :(30, 27, -51),
"green":(55, -41, 34),
"red":(41, 51, 26),
"yellow" :(81, -4, 79),
"magenta" :(52, 49, -16),
"cyan" :(52, 22, 27),
"white" : (96, 0, 0),
"neutral_8" :(81, 0, 0),
"neutral_6.5" :(67, 0, 0),
"neutral_5" :(52, 0, 0),
"neutral_3.5" :(36, 0, 0),
"black" : (20, 0, 0),
"long_grey_patch" : (0, 0, 0)
}

macbeth_color_dict = {
"dark_skin":   "saddlebrown",
"light_skin":  "peachpuff",
"blue_sky":  "skyblue",
"foliage":  "forestgreen",
"blue_flower":  "mediumpurple",
"bluish_green" :  "mediumturquoise",
"orange" :  "orange",
"purplish_blue"	:  "slateblue",
"moderate_red" :  "palevioletred",
"purple" :  "rebeccapurple",
"yellow_green" :  "yellowgreen",
"orange_yellow" :  "goldenrod",
"blue" :  "navy",
"green":  "limegreen",
"red":  "darkred",
"yellow" :  "yellow",
"magenta" :  "mediumvioletred",
"cyan" :  "darkcyan",
"white" :   "lime",
"neutral_8" : "darkgray", 
"neutral_6.5" :  "gray",
"neutral_5" :  "dimgray",
"neutral_3.5" :  "lightslategray",
"black" :   "black",
"long_grey_patch" :  "lightsteelblue", 
}

def extract_roi_mask(img):

    # Define the ROI coordinates (x,y,w,h)
    x, y, w, h = 250, 4900, 3240, 470

    # Create a mask of zeros with the same size as the image
    mask = np.zeros_like(img)

    # Draw a white rectangle on the mask at the ROI coordinates
    cv2.rectangle(mask, (x,y), (x+w,y+h), (255,255,255), -1)

    # Apply the mask to the image
    masked_img = cv2.bitwise_and(img, mask)

    return masked_img


def draw_rect(masked_img, color_tuple):

    # Draw a neon coloured rectangle on the mask at the ROI coordinates
    x, y, w, h = color_tuple

    cv2.rectangle(masked_img, (x,y), (x+w,y+h), (253,32,171), -1)


def extract_lab(colorname, color_tuple, masked_img):
    x, y, w, h = color_tuple

    # Extract the ROI from the image
    roi = masked_img[y:y+h, x:x+w]

    # Convert the ROI to LAB color space
    lab_roi = cv2.cvtColor(roi.astype("float32")/255, cv2.COLOR_BGR2LAB)

    # Calculate the mean LAB values for the ROI
    L_mean, A_mean, B_mean = cv2.mean(lab_roi)[:3]

    # Print the mean LAB values
    # print("{} ---------- L*: {:.2f}, a*: {:.2f}, b*: {:.2f}".format(colorname, L_mean, A_mean, B_mean))
    
    return L_mean, A_mean, B_mean


def main():
    gold_std_delta_dict = {}
    img_color_dict = {}
    fig, axs = plt.subplots(nrows=len(color_check_standard_dict.keys()), ncols=1)
    for path in paths:
        Img = cv2.imread(path)
        MaskedImg = extract_roi_mask(Img)
        count = 0
        for k, v in color_check_standard_dict.items():
            Lab_tup = extract_lab(k, color_chart_coord_dict[k], MaskedImg)
            img_color_dict[k] = Lab_tup
            gold_std_delta_dict[k] = tuple(map(lambda a, b: round(a - b, 2), Lab_tup, color_check_standard_dict[k]))

            axs[count].axhline(y=v[0], color=macbeth_color_dict[k], linestyle="solid", linewidth=1) # type: ignore
            axs[count].plot(os.path.basename(path), img_color_dict[k][0], "o", markersize=2, color=macbeth_color_dict[k]) # type: ignore
            axs[count].set_ylabel(k, rotation="horizontal", fontsize="xx-small", horizontalalignment="right") # type: ignore
            axs[count].tick_params(axis="x", labelrotation=90, labelsize="xx-small") # type: ignore
            count += 1
        print()
        print(path)
        pprint.pprint(gold_std_delta_dict)
    plt.show()

if __name__ == "__main__":
    main()