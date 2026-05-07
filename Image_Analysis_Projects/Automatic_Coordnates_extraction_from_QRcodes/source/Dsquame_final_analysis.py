#SIT_dsquame_test

import os
import os.path
import inspect
import logging
import sys

# from internal_library import internal_library_LOGGER
import internal_library.ImageAnalysis as ImageAnalysis
from internal_library.ImageAnalysis.StandardLogger import create_standard_logger
from internal_library.ImageAnalysis.OverloadedFunctions import ImageClass
from internal_library.ImageAnalysis.MaskFunctions import create_mask_from_circles_ndim, create_mask_from_circles
from internal_library.ImageAnalysis import readGrayscaleImage, writeImage, winpath_to_posixpath
from internal_library.ImageAnalysis import Util
from internal_library.algorithms.algorithm_helper_functions import internal_library_get_converted_image, save_user_params
import numpy as np
from joblib import Parallel, parallel_backend, delayed
import pylab    
import skimage
import cv2
import time

OUTPUTPATH = "output/sit_analysis"
""" :param OUTPUTPATH: output path
    :type OUTPUTPATH: string (directory)"""

LOGGER_NAME = os.path.splitext(os.path.split(inspect.getfile(\
    inspect.currentframe()))[1])[0]
""" :param LOGGER_NAME: name of logger, used inside log file and as logfilename
    :type LOGGER_NAME: string """

#setup standard logger
LOGGER = create_standard_logger(LOGGER_NAME, os.path.join(OUTPUTPATH, \
    LOGGER_NAME + ".log"), create_newfile=True)
LOGGER.setLevel(logging.DEBUG)



BASEPATH = "data/"
PTX_PATH = "data/"
InputFileParseMask = "S(?P<subj_int>[0-9]*)F(?P<side_int>[0-9]{2})T(?P<time_int>[0-9]{2})", 
InputFileParameters = [
    "subj_int", 
        "side_int", 
        "time_int"
]


def main():
    """ main function """
    OUTPUT_VAL = os.path.join(OUTPUTPATH, 'validation')
    #OUTPUT_FFACE = os.path.join(OUTPUTPATH, 'full_fit')
    Util.createDirectory(OUTPUT_VAL)
    #Util.createDirectory(OUTPUT_FFACE)
    mb_ges = []
    parameters = Util.read_ptx_file("data/SIT_QRcode.json")
    contour_names_bef = parameters[u'ContourTypes']
    contour_names_dict = dict([(x['name'], x['id']-1) for x in contour_names_bef])
    study_data = Util.check_study_data(BASEPATH, "*.tif", InputFileParseMask, InputFileParameters,2, search_depth=0 , key_remove_list=[])

    CIRCLE_REFERENCE_RADIUS_PX = 256
    CIRCLE_EFFECTIVE_RADIUS_PX = 232
    reduce_circ_border_diameter = (CIRCLE_REFERENCE_RADIUS_PX - CIRCLE_EFFECTIVE_RADIUS_PX) * 2
    #original size: 256pixel ~ 10mm
    #600 dpi 1inch=25.4mm, 10mm=600/25.4*10 1dot= 25.4/600 mm, d.h 10mm = 10*600/25.4 = 236 22mm d-squame = 259 pixel
    #80& = 19.7mm ->232px radius
    rename_parts= {(31,1):None,(101,0):None,(111,0):None }# {(1,1):None,(2,0):None,(2,1):2, (31,1):None}
    if True:
        err_data = []
        gray_data = {}
        gray_mean = {}


        for st_data in study_data:
            image_T1 = st_data
            
            ptx_data_T1 = Util.read_ptx_file(Util.create_filename_from_basefile(image_T1[-1], file_ext=".ptx"))
            im1 = ImageClass(image_T1[-1])

            for idx, fn in enumerate(['Proband_top', 'Proband_lower']):
                subj=st_data[0]+idx
                if (st_data[0],idx) in rename_parts:
                    if rename_parts[(st_data[0],idx)] is None:
                        continue
                    else:
                        subj=rename_parts[(st_data[0],idx)]
                mask_all_spots = create_mask_from_circles_ndim(im1.shape, ptx_data_T1[contour_names_dict[fn]]['contour'], [x*2-reduce_circ_border_diameter for x in ptx_data_T1[contour_names_dict[fn]]['radius']])
                # gr_mean = []
                # gr_std = []
                # gr_data = []

                gr_mean = np.zeros((4,3))
                for spot_index in range(mask_all_spots.shape[-1]):
                    areal = (spot_index // 3)
                    timep = (spot_index%3)
                    y = ptx_data_T1[contour_names_dict['Proband_top']]['contour'][spot_index][0]
                    x = ptx_data_T1[contour_names_dict['Proband_top']]['contour'][spot_index][1]
                    r = ptx_data_T1[contour_names_dict['Proband_top']]['radius'][spot_index]+20
                    # crop = (slice(int(x-r), int(x+r)), slice(int(y-r), int(y+r)))
                    # fig, ((ax1, ax2), (ax3, ax4)) = pylab.subplots(2,2)
                    # ax1.imshow(im1.np_data[crop])
                    # ax2.imshow(ttt[:,:,id][crop])
                    # ax3.imshow((im1.np_data*ttt[:,:,id])[crop])
                    # fig.show()
                    
                    data = im1.np_data[mask_all_spots[:,:,spot_index]>0]
                    gr_mean[areal, timep] = np.mean(data)
                    # gr_mean.append(np.mean(data))
                    # gr_std.append(np.std(data))
                    # gr_data.append(data)
                    gray_data[(subj, areal, timep)] = data
                gray_mean[subj] = gr_mean

                # input("Press Enter to continue...")
                                                
            print(1)
            Util.backupFile(os.path.join(OUTPUTPATH, "data.dat"))
            Util.writeData([study_data, gray_data, gray_mean], os.path.join(OUTPUTPATH, "data.dat"))
            # ptx_data_T2 = Util.read_ptx_file(Util.create_filename_from_basefile(image_T2[-1], file_ext=".ptx"))
            # ptx_data_T1_new = Util.read_ptx_file(Util.create_filename_from_basefile(image_T2[-1], file_ext=".ptx")) #Take copy of T2 to have same points
        # return

    if True:
        [study_data, gray_data, gray_mean] = Util.readData(os.path.join(OUTPUTPATH, "data.dat"))    

        combined_gray_mean=np.dstack([gray_mean[subj] for subj in gray_mean.keys()])

        dark_view_thresh = np.mean(combined_gray_mean[:,0,:10])
        white_view_thresh = np.mean(combined_gray_mean[:,1:2,:10]) # np.percentile(xx[:,0,:10], 99) # np.mean(xx[:,1:2,:10])


        for dummy_perc in [1,2,3,4,5,10]:
            OUTPUT_VAL = os.path.join(OUTPUTPATH, 'validation_p%02d'%dummy_perc)
            #OUTPUT_FFACE = os.path.join(OUTPUTPATH, 'full_fit')
            Util.createDirectory(OUTPUT_VAL)
            perc = [np.percentile(gray_data[key], dummy_perc) for key in gray_data.keys() if (key[2] in [1,2]) ]
            dark_threshold = np.mean(perc[:(4*2*5)]) # first 5 subjects all areas & timepoints


            if True:
                err_data = []
                thresh_data = {}
                thresh_stat_data = {}


                for st_data in study_data:
                    image_T1 = st_data
                    
                    ptx_data_T1 = Util.read_ptx_file(Util.create_filename_from_basefile(image_T1[-1], file_ext=".ptx"))
                    im1 = ImageClass(image_T1[-1])

                    for idx, fn in enumerate(['Proband_top', 'Proband_lower']):
                        subj=st_data[0]+idx
                        if (st_data[0],idx) in rename_parts:
                            if rename_parts[(st_data[0],idx)] is None:
                                continue
                            else:
                                subj=rename_parts[(st_data[0],idx)]

                        mask_all_spots = create_mask_from_circles_ndim(im1.shape, ptx_data_T1[contour_names_dict[fn]]['contour'], [x*2-reduce_circ_border_diameter for x in ptx_data_T1[contour_names_dict[fn]]['radius']])
                        mask_all_spots_2D = np.max(mask_all_spots, axis=-1)
                        # gr_mean = []
                        # gr_std = []
                        # gr_data = []
                        
                        writeImage(((mask_all_spots_2D>0)*255).astype(np.uint8), os.path.join(OUTPUT_VAL, "S%03d_mask.png"%subj))
                        thresholded_image = np.logical_and(mask_all_spots_2D>0, im1.np_data < dark_threshold)
                        writeImage((thresholded_image*255).astype(np.uint8), os.path.join(OUTPUT_VAL, "S%03d_thresh.png"%subj))

                        out_val_im = np.repeat(np.clip(np.round(np.copy(im1.np_data)*255),0,255)[:, :, np.newaxis], 3, axis=2).astype(np.uint8)
                        out_val_im[:,:,1][thresholded_image] = 0
                        out_val_im[:,:,2][thresholded_image] = 0
                        out_val_im[:,:,0][thresholded_image] = 255
                        writeImage(out_val_im, os.path.join(OUTPUT_VAL, "S%03d_val_auto.png"%subj))

                        scaled = np.clip(np.round( ((np.copy(im1.np_data)-dark_view_thresh) / (white_view_thresh-dark_view_thresh))*255),0,255).astype(np.uint8)
                        out_val_im = np.repeat(scaled[:, :, np.newaxis], 3, axis=2)
                        writeImage(out_val_im, os.path.join(OUTPUT_VAL, "S%03d_scaled.png"%subj))
                        out_val_im[:,:,1][thresholded_image] = 0
                        out_val_im[:,:,2][thresholded_image] = 0
                        out_val_im[:,:,0][thresholded_image] = 255
                        writeImage(out_val_im, os.path.join(OUTPUT_VAL, "S%03d_scaled_val_auto.jpg"%subj))

                        for spot_index in range(mask_all_spots.shape[-1]):
                            areal = (spot_index // 3)
                            timep = (spot_index%3)
                            # y = ptx_data_T1[contour_names_dict['Proband_top']]['contour'][id][0]
                            # x = ptx_data_T1[contour_names_dict['Proband_top']]['contour'][id][1]
                            # r = ptx_data_T1[contour_names_dict['Proband_top']]['radius'][id]+20
                            # crop = (slice(int(x-r), int(x+r)), slice(int(y-r), int(y+r)))
                            # fig, ((ax1, ax2), (ax3, ax4)) = pylab.subplots(2,2)
                            # ax1.imshow(im1.np_data[crop])
                            # ax2.imshow(ttt[:,:,id][crop])
                            # ax3.imshow((im1.np_data*ttt[:,:,id])[crop])
                            # fig.show()
                            
                            data = im1.np_data[mask_all_spots[:,:,spot_index]>0] < dark_threshold


                            # gr_mean.append(np.mean(data))
                            # gr_std.append(np.std(data))
                            # gr_data.append(data)
                            thresh_data[(subj, areal, timep)] = data
                            thresh_stat_data[(subj, areal, timep)] = {'percentage':np.mean(data), 'count':np.sum(data), 'ROIsize': mask_all_spots[:,:,spot_index].sum(), 'st_data_intern':st_data, 'val_img':os.path.join(OUTPUT_VAL, "S%03d_val_auto.png"%subj), 'contour_name':fn, 'reduce_circ_border':reduce_circ_border_diameter, 'threshold_perc':dummy_perc, 'used_threshold':dark_threshold}
                        # thresh_mean[subj] = gr_mean

                        # input("Press Enter to continue...")
                                                        
                    print(1)
                    Util.backupFile(os.path.join(OUTPUTPATH, "data_th_p%02d.dat"%dummy_perc))
                    Util.writeData([study_data, thresh_data, thresh_stat_data], os.path.join(OUTPUTPATH, "data_th_p%02d.dat"%dummy_perc))
                    # ptx_data_T2 = Util.read_ptx_file(Util.create_filename_from_basefile(image_T2[-1], file_ext=".ptx"))
                    # ptx_data_T1_new = Util.read_ptx_file(Util.create_filename_from_basefile(image_T2[-1], file_ext=".ptx")) #Take copy of T2 to have same points
            

            out_stat_data = {} #data_dictionary['header'] = ['subj', 'time1', 'view', 'light','region', "Test", "Test_long", "Measurement", "Value", "Unit"]
            out_stat_data['header'] = ['subj', 'areal', 'timep', 'Test',"Test_long", "Value", "Unit",'org_img', 'val_img','contour_name', 'used_threshold', 'threshold_perc', 'reduce_circ_border' ]
            test_names = {'percentage':'percentage of covered area', 'count':'count of dark pixels in ROI', 'ROIsize': 'pixels in roi'}
            unit_names = {'percentage':'0-1', 'count':'#', 'ROIsize': '#'}
            out_data = []
            for subj_data, data_c in thresh_stat_data.items():
                for test_key, long_test_name in test_names.items():
                    out_data.append( [str(subj_data[0]), str(subj_data[1]+1), str(subj_data[2]+1)]
                                + [test_key, long_test_name, str(data_c[test_key]), unit_names[test_key], str(data_c['st_data_intern'][-1])]
                                + [str(data_c[loc_key]) for loc_key in out_stat_data['header'][8:]])

            out_stat_data['data'] = out_data
            Util.export_for_stat_format(out_stat_data, os.path.join(OUTPUTPATH, "data_th_p%02d.tsv"%dummy_perc))

    if True:
        for dummy_perc in [1,2,3,4,5,10]:
            OUTPUT_VAL = os.path.join(OUTPUTPATH, 'validation_p%02d'%dummy_perc)
            # [study_data, thresh_data, thresh_stat_data] = Util.readData(os.path.join(OUTPUTPATH, "data_th_p%02d.dat"%dummy_perc))

            [study_data, thresh_data, thresh_stat_data_dirty] = Util.readData(os.path.join(OUTPUTPATH, "data_th_p%02d.dat"%dummy_perc))
            
            thresh_stat_data = {}
            # #2 extra ->102
            thresh_stat_data[(2,2,2)] = thresh_stat_data_dirty[(2,3,1)]
            thresh_stat_data[(2,3,1)] = thresh_stat_data_dirty[(102,3,1)]
            thresh_stat_data[(2,3,2)] = thresh_stat_data_dirty[(102,3,2)]
            # #12 extra ->112
            thresh_stat_data[(12,2,2)] = thresh_stat_data_dirty[(112,2,2)]
            # thresh_stat_data[(2,2,2)] = thresh_stat_data_dirty[(36,2,2)]

            # #9 -> image S109
            # #22 -> image S32
            # #24 -> image S099 unten
            # for areal in range(4):
            #     for timep in range(3):
            #         thresh_stat_data[(9,areal,timep)] = thresh_stat_data_dirty[(109,areal,timep)]
            #         thresh_stat_data[(22,areal,timep)] = thresh_stat_data_dirty[(32,areal,timep)]
            #         thresh_stat_data[(24,areal,timep)] = thresh_stat_data_dirty[(99,areal,timep)]
                    
            

            # thresh_stat_data[(20,3,1)] = thresh_stat_data_dirty[(20,2,2)]
            # thresh_stat_data[(20,2,2)] = thresh_stat_data_dirty[(20,3,1)]


            # thresh_stat_data[(21,3,1)] = thresh_stat_data_dirty[(22,0,1)]


            data_to_check = {}
            for subj_data, data_c in thresh_stat_data_dirty.items():
                
                if (subj_data[0]<=31) and (subj_data not in thresh_stat_data):
                    thresh_stat_data[subj_data] = data_c
                else:
                    data_to_check[subj_data] = data_c


            LOGGER.debug("manually changed: subj, areal, timepoint")
            print("manually changed: subj, areal, timepoint")
            for subj_data in data_to_check.keys():
                print([str(subj_data[0]), str(subj_data[1]+1), str(subj_data[2]+1)])
                LOGGER.debug([str(subj_data[0]), str(subj_data[1]+1), str(subj_data[2]+1)])
                    # ptx_data_T2 = Util.read_ptx_file(Util.create_filename_from_basefile(image_T2[-1], file_ext=".ptx"))
                    # ptx_data_T1_new = Util.read_ptx_file(Util.create_filename_from_basefile(image_T2[-1], file_ext=".ptx")) #Take copy of T2 to have same points
            print("manually changed: subj, areal, timepoint") 
            areanames = ["links unten", "links oben", "rechts unten", "rechts oben"]
            timepnames = ["t0", "3.strip", "6.strip"]
            for subj_data in data_to_check.keys():
                print([str(subj_data[0]), areanames[subj_data[1]], timepnames[subj_data[2]]])
                LOGGER.debug([str(subj_data[0]), areanames[subj_data[1]], timepnames[subj_data[2]]])

            out_stat_data = {} #data_dictionary['header'] = ['subj', 'time1', 'view', 'light','region', "Test", "Test_long", "Measurement", "Value", "Unit"]
            out_stat_data['header'] = ['subj', 'areal', 'timep', 'areal_name', 'timepoint_name','Test',"Test_long", "Value", "Unit",'org_img', 'val_img','contour_name', 'used_threshold', 'threshold_perc', 'reduce_circ_border' ]
            test_names = {'percentage':'percentage of covered area', 'count':'count of dark pixels in ROI', 'ROIsize': 'pixels in roi'}
            unit_names = {'percentage':'0-1', 'count':'#', 'ROIsize': '#'}
            out_data = []
            for subj_data, data_c in thresh_stat_data.items():
                for test_key, long_test_name in test_names.items():
                    out_data.append( [str(subj_data[0]), str(subj_data[1]+1), str(subj_data[2]+1), areanames[subj_data[1]], timepnames[subj_data[2]]]
                                + [test_key, long_test_name, str(data_c[test_key]), unit_names[test_key], str(data_c['st_data_intern'][-1])]
                                + [str(data_c[loc_key]) for loc_key in out_stat_data['header'][10:]])

            out_stat_data['data'] = out_data
            Util.export_for_stat_format(out_stat_data, os.path.join(OUTPUTPATH, "data_cleaned_th_p%02d.tsv"%dummy_perc))



if __name__ == "__main__":
    main()
    input("Press Enter to continue...")
