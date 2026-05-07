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

#region old colorface renamer function
# def rename_colorface_files(path, regx, file_ext, logpath):
#     log_dict = {}

#     for fn in os.listdir(path):
#         if fn.endswith(file_ext):
#             subjid = re.search(regx, fn).group(1)
            
#             if len(subjid) > 2: # if more than 99 subjects
#                 barcode = "S" + subjid
#             else:
#                 barcode = "S0" + subjid
            
#             if "Left" in fn:
#                 barcode += "F03"
#                 if "Baseline" in fn:
#                     barcode += "T01CLF"
#                 elif "D01" in fn:
#                     barcode += "T02CLF"
#                 elif "D15" in fn:
#                     barcode += "T03CLF"
#                 elif "D57" in fn:
#                     barcode += "T04CLF"
                    
#             if "Front" in fn:
#                 barcode += "F02"
#                 if "Baseline" in fn:
#                     barcode += "T01CLF"
#                 elif "D01" in fn:
#                     barcode += "T02CLF"
#                 elif "D15" in fn:
#                     barcode += "T03CLF"
#                 elif "D57" in fn:
#                     barcode += "T04CLF"
                
#             elif "Right" in fn:
#                 barcode += "F01"
#                 if "Baseline" in fn:
#                     barcode += "T01CLF"
#                 elif "D01" in fn:
#                     barcode += "T02CLF"
#                 elif "D15" in fn:
#                     barcode += "T03CLF"
#                 elif "D57" in fn:
#                     barcode += "T04CLF"
                    
#             new_fn = barcode + "--" + fn
#             log_dict[new_fn] = fn

#     print(log_dict)

#     for new_fn, fn in log_dict.items():
#         os.rename(os.path.join(path, fn), os.path.join(path, new_fn))

#     # dump dict to dict for logging
#     with open(logpath, "w") as logJson:
#         json.dump(log_dict, logJson)
#endregion


def rename_colorface_files(actual_path, studyID):
    
    file_ext = ".jpg"
    rgx_mask = r"([0-9]*)_([A-Za-z0-9]*)_([a-zA-Z ]*)_([a-zA-Z0-9 ]*)"
   
   
    visia_naming_order_dict = {
        "subjectno" : 1,
        "timepoint" : 2,
        "side" : 3,
        "light" : 4
    }
    
    colorface_naming_order_dict = {
        "subjectno" : 1,
        "timepoint" : 2,
        "side" : 3,
        "light" : 4
    }
    
    side_list= []
    rgx = re.compile(rgx_mask)

    log_path = os.path.join(actual_path, f"{studyID}_LOG_VisiaRenamedFiles.json")

    # for fn in os.listdir(actual_path):
    #     if fn.endswith(file_ext):    
    #         try:
    #             side_list.append(re.search(rgx, fn).group(3))
    #         except:
    #             raise filenameError(f"Check side id again for {fn} with mask {rgx_mask}")
                
    # side_list = set(side_list)
    # associates a side number to the side names # visia only has 3 views
    
    sides_dict = {"Right View": "F01",
                      "Front View": "F02", 
                      "Left View": "F03",
                      "Right Face" : "F01",
                      "Front Face" : "F02",
                      "Left Face" : "F03"}

    # sides_counter_list = ["F01", "F02", "F03"]


    # sorted_key = [(x , sides_key_dict[x]) for x in side_list]
    # sorted_side_keys = sorted(sorted_key, key= lambda x: x[1])

    # side_dict = {}
    # for n, ele in enumerate(sorted_side_keys):
    #     side_dict[ele[0]] = sides_counter_list[n]
    
    times_dict = {
        "Baseline":"T01",
        "D01": "T02",
        "D15": "T03",
        "D57": "T04"
        }
    
    # time_counter_list = ["T01", "T02", "T03", "T04"]
    
    # assoicates an abbreviated string to the lighting modes
    light_dict = {"Standard 1":"STD1", 
                "Standard 2":"STD2", 
                "UV-NF":"UVNF",
                "UV-F":"UVFF",
                "Cross-Polarized": "XPOL", 
                "Parallel-Polarized":"PPOL",
                "CP": "XPOL",
                "PP": "PPOL",
                "No Filters" : "NOFL",
                "STD45": "SD45",
                "STD60": "SD60",
                }

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
                # timeHead = re.search(rgx, fn).group(2)
                # if "D" in timeHead:
                #     timeHead = timeHead.replace("D", "T")
                # elif "Baseline" in timeHead:
                #     timeHead = timeHead
                timeHead = times_dict[re.search(rgx, fn).group(colorface_naming_order_dict["timepoint"])]
            except:
                raise filenameError(f"check timep of {fn} for mask {rgx_mask}")  
            
            # side numbering              
            try:
                sideHead = sides_dict[re.search(rgx, fn).group(colorface_naming_order_dict["side"])]
            except:
                raise filenameError(f"check sideid of {fn} for mask {rgx_mask}")
            
            # light numbering                
            try:
                lightHead = light_dict[re.search(rgx, fn).group(colorface_naming_order_dict["light"])]
            except:
                raise filenameError(f"check light id of {fn} for mask {rgx_mask}")                

            # new filename
            new_fn = subjHead + sideHead +timeHead + lightHead + "--"+fn #+"_"+idHead 
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

    PATH = os.environ.get("STUDY_PATH", "data/study/all_images")
    STUDY_ID = os.environ.get("STUDY_ID", "XX.XXXX-XX")
    # REGX_PATTERN_WITH_GROUPING = r"([0-9]{2})*"
    FILE_EXT = ".jpg"
    LOG_PATH = os.path.join(PATH, f"{STUDY_ID}_LOG_VisiaRenamedFiles.json")

    rename_colorface_files(PATH, STUDY_ID)
    
    # uncomment for reversing renaming
    #reverse_renaming(LOG_PATH, PATH, FILE_EXT)
    
if __name__ == "__main__":
    main()