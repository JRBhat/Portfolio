# test data path
# data/test/face_camera_renamer_test/XX.XXXX-XX
# log file: "data/test/face_camera_renamer_test/XX.XXXX-XX_LOG_RenamedFiles.json"

import re
import os
import json
import sys
import time

class filenameError(Exception):
    pass


def rename_colorface_files(actual_path, studyID):
    
    file_ext = ".jpg"
    #rgx_mask = r"([0-9]*)_([A-Za-z0-9]*)_([a-zA-Z ]*)_([a-zA-Z0-9 ]*)"
    rgx_mask = r"([0-9]*)_([a-zA-Z ]*)_([A-Za-z0-9]*)_([a-zA-Z0-9 ]*)"
   
    # visia_naming_order_dict = {
    #     "subjectno" : 1,
    #     "timepoint" : 2,
    #     "side" : 3,
    #     "light" : 4
    # }
    
    colorface_naming_order_dict = {
        "subjectno" : 1,
        "timepoint" : 3,
        "side" : 2,
        "light" : 4
    }
    
    side_list= []
    rgx = re.compile(rgx_mask)

    log_path = os.path.join(actual_path, f"{studyID}_LOG_VisiaRenamedFiles.json")

    # sides_dict = {"Right View": "F01",
    #                   "Front View": "F02", 
    #                   "Left View": "F03",
    #                   "Right Face" : "F01",
    #                   "Front Face" : "F02",
    #                   "Left Face" : "F03"}

    times_dict = {
        "Baseline":"T01",
        "D01": "T02",
        "D15": "T03",
        "D57": "T04"
        }
    
    # assoicates an abbreviated string to the lighting modes
    # light_dict = {"Standard 1":"STD1", 
    #             "Standard 2":"STD2", 
    #             "UV-NF":"UVNF",
    #             "UV-F":"UVFF",
    #             "Cross-Polarized": "XPOL", 
    #             "Parallel-Polarized":"PPOL",
    #             "CP": "XPOL",
    #             "PP": "PPOL",
    #             "No Filters" : "NOFL",
    #             "STD45": "SD45",
    #             "STD60": "SD60",
    #             }

    log_dict = {}

    for fn in os.listdir(actual_path):
    
        if fn.endswith(file_ext):
            
            #subject numbering
            try:
                orig_subj_num = re.search(rgx, fn).group(colorface_naming_order_dict["subjectno"])
            except:
                raise filenameError(f"check Subj of {fn} for mask {rgx_mask}")
            
            if len(orig_subj_num) == 3:
                subjHead = "S" + orig_subj_num
            elif len(orig_subj_num) == 2:
                subjHead = "S0" + orig_subj_num
            elif len(orig_subj_num) == 1:
                subjHead = "S00" + orig_subj_num
                
            # timepoint numbering
            try:
                timeHead = times_dict[re.search(rgx, fn).group(colorface_naming_order_dict["timepoint"])]
            except:
                raise filenameError(f"check timep of {fn} for mask {rgx_mask}")  
            
            # side numbering              
            # try:
            #     sideHead = sides_dict[re.search(rgx, fn).group(colorface_naming_order_dict["side"])]
            # except:
            #     raise filenameError(f"check sideid of {fn} for mask {rgx_mask}")
            
            # light numbering                
            # try:
            #     lightHead = light_dict[re.search(rgx, fn).group(colorface_naming_order_dict["light"])]
            # except:
            #     raise filenameError(f"check light id of {fn} for mask {rgx_mask}")                

            # new filename
            new_fn = subjHead + "F01" +timeHead + "CLF" +"--"+fn #+"_"+idHead 
            print(new_fn)
            # log all changes to a tuple and save it in a dict
            log_dict[new_fn] = fn
      
    #rename - code kept outside first loop ; renaming occurs only if the dict is properly written without errors
    print("No errors found during the dictionary creation process.... Now renaming")
    print("Please Wait until program ENDS...")
    time.sleep(3)
    for new_fn, fn in log_dict.items():
        os.rename(os.path.join(actual_path, fn), os.path.join(actual_path, new_fn))

    # dump dict to dict for logging
    with open(log_path, "w") as logJson:
        json.dump(log_dict, logJson)

    print("Renaming finished; changes stored in json log file")

def reverse_renaming(json_log_file_path, raw_path, file_ext):
    with open(json_log_file_path, "r") as jsonF:
        orig_dict = json.load(jsonF)
    
    rawList = os.listdir(raw_path)
    for k in orig_dict.keys():
        try:
            mod_fn = list(filter(lambda x: k == x and file_ext in x, rawList))
            orig_name = orig_dict[mod_fn[0]]
            print(orig_name)
            os.rename(os.path.join(raw_path, mod_fn[0]), os.path.join(raw_path, orig_name))
        except (AttributeError,IndexError) as err:
            print(err)
            sys.exit(1)
    print("File reconstruction of all files to original naming scheme...without errors ")
    del_flag = input("Delete Json log file?(y/n)")
    if del_flag == "y":
        os.remove(json_log_file_path)


def main():

    PATH = os.environ.get("STUDY_PATH", "data/study/analysis")
    STUDY_ID = os.environ.get("STUDY_ID", "XX.XXXX-XX")
    # REGX_PATTERN_WITH_GROUPING = r"([0-9]{2})*"
    FILE_EXT = ".jpg"
    LOG_PATH = os.path.join(PATH, f"{STUDY_ID}_LOG_VisiaRenamedFiles.json")

    rename_colorface_files(PATH, STUDY_ID)
    
    # uncomment for reversing renaming
    #reverse_renaming(LOG_PATH, PATH, FILE_EXT)
    
if __name__ == "__main__":
    main()