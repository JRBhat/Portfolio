#import modules needed for logger creation
from distutils import extension
import os
import os.path
import inspect
import logging
import re
from datetime import datetime

import sys

#import further modules
from ImageAnalysis import Util as Ut
# from pias.ImageAnalysis.OverloadedFunctions import ImageClass
import numpy as np
import scipy.ndimage    
import scipy.interpolate
import skimage.util
import cv2
from scipy import stats
import copy
from ImageAnalysis import ImageIO as Io

# reg_exp_grp = r"(S[0-9]{3})(F[0-9]{2})(T[0-9]{2})USR220229"
# reg_exp_full = r"S[0-9]{3}F[0-9]{2}T[0-9]{2}USR220229"
reg_exp_full = r"[0-9]{2}_D[0-9]{2}_[A-Za-z ]*_STD45"

# def print_2_file(content):
#     # variable_name = f'{content=}'.split('=')[0] # trick to print variable name and content
#     with open(os.path.join(output_directory,'log_'+now.strftime("%m-%d-%Y-%H-%M-%S")+'.txt'), 'a+') as f:
#         print(content, file=f)

def main():

    """ main function """
    # INPATH = r"data\raw\front" #TESTPATH
    INPATH = r"data\raw"   # Set this to your local input directory
    OUTPATH = r"data\processed\run3_results"  # Set this to your local output directory
    # CONTOUR_NAME = "under-eye-left"# eye-lower-right = id 15, eye-lower-left = id 14, #  "all key points" contour = id 0; ## "full_face"contour = id 18 
    CONTOUR_NAME_LIST = ["under-eye-right", "eye-right"]#["under-eye-left", "eye-left"]#["under-eye-left", "eye-left", "under-eye-right", "eye-right"] #
    FIXED_POINT_NAME = "Front_face_nose_center_point" # by trial and error # TODO: Front: left27/29right ; Side: rightface17/15leftface
    EXTND_SIDE_BY_PXLS = [0]
    SIDE = "Right"
    # fixed_key_points_botheyes = [25, 26, 27, 28, 29,30,31,32] # for avg fixed point of contour
    fixed_key_points = [15, 16, 17, 18] # right and left side face eye contours

    contour_name_indx_dict = {
        "key-points" : 0, 
        "full-upper" : 1, 
        "mid-face" : 2,
        "full-cheek-left" : 3, "full-cheek-right" : 4, 
        "cheek-left" : 5,"cheek-right" : 6,
        "pore" : 7,
        "crows-feet-left" : 8,  "crows-feet-right" : 9,
        "forehead" : 10, 
        "periorbital-left" : 11, "periorbital-right" : 12,
        "glabellar" : 13,
        "under-eye-left" : 14, "under-eye-right" : 15,
        "nasolabial-left" : 16, "nasolabial-right" : 17,
        "full-face" : 18,
        "brow-left" : 19, "brow-right" : 20,
        "eye-left" : 21, "eye-right" : 22,
        "mouth" : 24,
        "pore_pd_left" : 25, "pore_pd_right" : 26,
    }

    fixed_point_descp = {
        "Front_face_right_eye_innermost" : 27,
        "Front_face_left_eye_innermost" : 29,
        "Front_face_left_eyebrow_innermost" : 16,
        "Front_face_right_eyebrow_innermost" : 17,
        "Front_face_nose_center_point": 23,
        "Front_face_chin_center_point": 6,

        "Left_face_left_eye_innermost": 17,
        "Right_face_right_eye_innermost": 15,
    } # Note: key points numbering changes for front view and left/right view so indices might be same

    # contour_idx = contour_name_indx_dict[CONTOUR_NAME]
    fixed_key_point = fixed_point_descp[FIXED_POINT_NAME]
    
    contour_list = [contour_name_indx_dict[name] for name in CONTOUR_NAME_LIST]

    # for fx_pnt in range(1):#range(0, 46):
    now = datetime.now()
    # output_directory = os.path.join("\\".join(INPATH.split("\\")[:-1]), f'output_{SIDE}_Custom_{fixed_key_point}_('+now.strftime("%H-%M-%S")+")")
    fixed_name_short = "".join([word[0].upper() for word in FIXED_POINT_NAME.split("_")])
    contour_name_short = "".join([word[0].upper() for contourname in CONTOUR_NAME_LIST for word in contourname.split("-")])
    output_directory = os.path.join(OUTPATH, f'output_{contour_name_short}_{fixed_name_short}-{fixed_key_point}_('+now.strftime("%H-%M-%S")+")")

    Ut.createDirectory(output_directory)
    # padding
    # print_2_file(f'{dists=}')
    current_imlist = {"Images":{},"PointFiles":{}} # dictcontaining two dicts: Images and PointFiles

    # just read in the image filenames and create ptx files by replacing the extension
    for filename in os.listdir(INPATH):
        # extract the filename
        if filename.endswith(".jpg") and SIDE in filename and re.match(reg_exp_full, filename):# or "F02" in filename):
            re_matched = re.search(reg_exp_full, filename).group(0)
            filepath_reconst = os.path.join(INPATH, re_matched+".jpg") 
            ptx_reconst = os.path.join(INPATH, re_matched+".ptx")

            # create corressponding dicts to store filepaths and ptx paths
            current_imlist["Images"][re_matched] = filepath_reconst
            current_imlist["PointFiles"][re_matched] = ptx_reconst
            # dict created: contains Images and Pointfiles as keys, with values corressponding to the corresponding paths to those files

    bbox_ges = []

    for key in current_imlist['Images'].keys(): # iterate over each image 
        # imagefile = current_imlist['Images'][key] # gets filename

        try:
            ptx_name = current_imlist['PointFiles'][key] # gets ptx filename
            ptx_data = Ut.read_ptx_file(ptx_name) # gets ptx coordinate data

            all_keypoint_coordinates = np.array(sum([ptx_data[idx]['contour'][:] for idx in contour_list], [])) # all coordinates for contour of interest
            # all_keypoint_coordinates = np.array(ptx_data[contour_idx]['contour'][:]) # all coordinates for contour of interest

            real_fixed_point = (np.array(ptx_data[0]['contour'])[fixed_key_points, :]).mean(axis=0) # select fixed key point as reference to all other points

            # stack all 
            bbox_diff_1 = all_keypoint_coordinates - real_fixed_point # move all contours to a starting key point position

            # get optimal bounding box coordinates "bbox_ges(amt)"
            if SIDE in ptx_name and (SIDE == "Front" or SIDE == "Right"): # right side F01
                bbox_ges.append([bbox_diff_1[:,0].min(), 
                                bbox_diff_1[:,1].min(), 
                                bbox_diff_1[:,0].max(), 
                                bbox_diff_1[:,1].max()])

            elif SIDE in ptx_name and SIDE == "Left": # left side f02
                bbox_ges.append([-bbox_diff_1[:,0].max(), 
                                  bbox_diff_1[:,1].min(), 
                                 -bbox_diff_1[:,0].min(), 
                                  bbox_diff_1[:,1].max()])

        except Exception as inst:
            print(inst)

    #testtest bbox_x0 = np.array([-200, -200, 200, 200])

    bbox_x0 = np.array(bbox_ges).min(axis=0)#
    bbox_x0[2:] = np.array(bbox_ges)[:,2:].max(axis=0)

    # print_2_file(f'{bbox_x0=}')
    current_imlist = {"Images":{},"PointFiles":{}} # dictcontaining two dicts: Images and PointFiles

    # just read in the image filenames and create ptx files by replacing the extension
    # input_directory = input_directory_1
    for filename in os.listdir(INPATH):
        # extract the filename
        if filename.endswith(".jpg") and SIDE in filename and re.match(reg_exp_full, filename): #("F01" in filename or "F02" in filename):
            re_matched = re.search(reg_exp_full, filename).group(0)
            filepath_reconst = os.path.join(INPATH, re_matched+".jpg") 
            ptx_reconst = os.path.join(INPATH, re_matched+".ptx")
            current_imlist["Images"][re_matched] = filepath_reconst
            current_imlist["PointFiles"][re_matched] = ptx_reconst
        #print(f'{current_imlist=}')

    for _,key in enumerate(current_imlist['Images'].keys()):
        imagefile_2 = current_imlist['Images'][key]
        imdata = Io.readRGBImage(imagefile_2)
        imdata[:500, :, : ] = 0

        try:
            ptx_name = current_imlist['PointFiles'][key]
            ptx_data = Ut.read_ptx_file(ptx_name)
        except Exception as inst:
            print(inst)

        if SIDE in ptx_name  and (SIDE == "Front" or SIDE == "Right"):
            bbox_x0_2 = copy.deepcopy(bbox_x0)

        elif SIDE in ptx_name and SIDE == "Left" :
            bbox_x0_2 = copy.deepcopy(bbox_x0)
            bbox_x0_2[0] = -bbox_x0[2]
            bbox_x0_2[2] = -bbox_x0[0]

        for dist in EXTND_SIDE_BY_PXLS:
            real_fixed_point = (np.array(ptx_data[0]['contour'])[fixed_key_points, :]).mean(axis=0)#np.array(ptx_data[0]['contour'][fixed_key_point])

            bbox_diff_2 = [(bbox_x0_2[0] + real_fixed_point[0]-dist).astype(int), 
                                (bbox_x0_2[1] + real_fixed_point[1]-dist).astype(int), 
                                (bbox_x0_2[2] + real_fixed_point[0]+dist).astype(int), 
                                (bbox_x0_2[3] + real_fixed_point[1]+dist).astype(int)]

            # print_2_file(f'{bbox_diff_2=}')

            if min(bbox_diff_2)<0 or  bbox_diff_2[3]>=imdata.shape[0] or bbox_diff_2[2]>=imdata.shape[1]:
                pdxx=0
                if bbox_diff_2[0] <0 :
                    pdxx = abs(bbox_diff_2[0])
                if bbox_diff_2[1] <0 :
                    pdxx = max([pdxx,abs(bbox_diff_2[1])])

                pdxx = max([pdxx,bbox_diff_2[3]+1 - imdata.shape[0], bbox_diff_2[2] - imdata.shape[1]+1])
                # # print_2_file(f'{pdxx=}')
                
                imxx = np.pad(imdata, ((pdxx,pdxx),(pdxx,pdxx),(0,0)), mode='edge')
                #?????????????? Io.writeImage(imxx[slice(bbox_diff_2[0][1+pdxx], bbox_diff_2[1][1]+pdxx), slice(bbox_diff_2[0][0]+pdxx, bbox_diff_2[1][0]+pdxx)] , Ut.create_filename_from_basefile(imagefile, directory=output_directory, file_ext=".png"))
                Io.writeImage(imxx[slice(bbox_diff_2[1]+pdxx, bbox_diff_2[3]+pdxx), 
                                    slice(bbox_diff_2[0]+pdxx, bbox_diff_2[2]+pdxx)], 
                                                    Ut.create_filename_from_basefile(imagefile_2, directory=output_directory, file_ext=".tif"))
            else:

                Io.writeImage(imdata[slice(bbox_diff_2[1], bbox_diff_2[3]), 
                                    slice(bbox_diff_2[0], bbox_diff_2[2])] ,
                                                    Ut.create_filename_from_basefile(imagefile_2, directory=output_directory, file_ext=".tif"))
            # print_2_file(f'{imdata[slice(bbox_diff_2[1], bbox_diff_2[3]), slice(bbox_diff_2[0], bbox_diff_2[2])]=}')
    return 0
    # print(f"loop for {fx_pnt} finished")
    
if __name__ == "__main__":
    main()
    input("Press Enter to continue...")
