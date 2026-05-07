
# test_set: "data/test/skin_imager_raw_renamer_test/sample"

# expected folder structure
# study_folder
    # ├───conv_cleaned
    # └───raw_cleaned

import os
import re
import json
import shutil
import logging as log
import sys
import pickle

def main():
    
    mapping_dict = {}

    extn = ""
    
    for root, _, filenames in os.walk(PATH):
        for fn in filenames:
            
            if fn.endswith(".tif"):
                extn = ".tif"
                img_id = re.search(CONV_FN_REGX, fn).group(5)
                print(img_id)
                print(os.path.join(root, fn))
                mapping_dict[img_id] = {"exported_img_path": os.path.join(root, fn), "raw_image_path": ""}
            
            if fn.endswith(".jpg"):
                extn = ".jpg"
                img_id = re.search(CONV_FN_REGX, fn).group(5)
                print(img_id)
                print(os.path.join(root, fn))
                mapping_dict[img_id] = {"exported_img_path": os.path.join(root, fn), "raw_image_path": ""}

            if extn == "":
                sys.exit(1)
                
            elif fn.endswith(".cr2"):
                raw_id = re.search(RAW_FN_REGX, fn).group(4)
                print(raw_id)
                print(os.path.join(root, fn))
                if raw_id in mapping_dict.keys():
                    mapping_dict[raw_id]["raw_image_path"] = os.path.join(root, fn)
                else:
                    print(f"missing raw id: {raw_id} ")
                    sys.exit(1)

    with open(os.path.join(PICKLE_PATH), "wb") as f:
        for k,v in mapping_dict.items():
            print(f"{k}:{v} \n\n")
            pickle.dump(mapping_dict, f)
            
    raw_directory = ""
    for _, v in mapping_dict.items():
        old_raw_file_name = v.get("raw_image_path").split("\\")[-1] # only raw file name
        new_raw_filename = v.get("exported_img_path").split("\\")[-1].replace(extn, ".cr2") 
        
        path_with_old_raw_file = v.get("raw_image_path")
        path_with_renamed_file = v.get("raw_image_path").replace(old_raw_file_name, new_raw_filename)
        
        try:
            os.rename(path_with_old_raw_file, path_with_renamed_file)
        except Exception as Argument:
            with open(os.path.join(PATH, "renaming_errors.log"), "a+") as fl:
                fl.write(str(Argument))
            
        # move files to main raw parent folder; outside subj folders
        if raw_directory == "":    
            raw_directory = ("\\").join(path_with_renamed_file.split("\\")[:-2]) # remove subject folders from raw directory
            print(raw_directory)
        try:
            shutil.move(path_with_renamed_file, os.path.join(raw_directory, path_with_renamed_file.split("\\")[-1]))
        except Exception as Argument:
            with open(os.path.join(PATH, "moving_errors.log"), "a+") as flm:
                flm.write(str(Argument))


def reverse_renaming_raw_files(log_path, raw_path):
    
    with open(log_path, "rb") as picklef:
        orig_dict = pickle.load(picklef)
    
    rawList = os.listdir(raw_path)
    for k in orig_dict.keys():
        try:
            img_val = list(filter(lambda x: k in x and ".cr2" in x, rawList))
            if len(img_val) > 0:
                current_fn = orig_dict[k]["exported_img_path"].split("\\")[-1].replace(".tif", ".cr2").replace(".jpg", ".cr2")
                raw_path_with_subjdir = "\\".join(orig_dict[k]["raw_image_path"].split("\\")[:-1])
                raw_path_without_subjdir =  "\\".join(raw_path_with_subjdir.split("\\")[:-1])
                current_loc =  os.path.join(raw_path_without_subjdir, current_fn)
                desired_loc = os.path.join(raw_path_with_subjdir, current_fn)
                
                shutil.move(current_loc, desired_loc)
                current_fn = desired_loc
                orig_raw_fn = orig_dict[k]["raw_image_path"].split("\\")[-1]
                desired_fn = os.path.join(raw_path_with_subjdir, orig_raw_fn)
                os.rename(current_fn, desired_fn)
            
        except (AttributeError,IndexError) as err:
            print(err)
            sys.exit(1)
            
    print("File reconstruction of all files to original naming scheme...without errors ")
    del_flag = input("Delete Json log file?(y/n)")
    if del_flag == "y":
        os.remove(log_path)
                
if __name__ == "__main__":
    # path with raw_cleaned folder and conv_cleaned folder(with correct names)
    PATH = os.environ.get("STUDY_PATH", "data/study/final_export")
    
    # exported images pattern
    # example: "02_t3_Front View_Cross-Polarized_20231205093235917_ 001.tif"
    CONV_FN_REGX = r"([0-9]*)_([A-Za-z0-9 ]*)_([A-Za-z ]*)_([0-9A-Za-z\- ]*)_([0-9]*)"#_ ([0-9]*)"
    
    # raw images pattern
    # raw file example: "02, 26344  (20231205092816876) 20231205093141093.cr2"
    RAW_FN_REGX = r"([0-9]*), ([0-9]*)  ([0-9\(\)]*) ([0-9]*)"
    
    PICKLE_PATH = os.path.join(PATH, "mapping.pickle")
    RAW_PATH = os.path.join(PATH, "raw_cleaned")
    
    main()
    #reverse_renaming_raw_files(PICKLE_PATH, RAW_PATH)