from operator import ne
import os
import re
import pickle
import sys
import time

class filenameError(Exception):
    pass

def reverse_renaming(json_log_file_path, raw_path, file_ext=".jpg"):
    
    with open(json_log_file_path, "rb") as jsonF:
        orig_dict = pickle.load(jsonF)
    
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

def rename_visia_files(actual_path, studyID):
    
    file_ext = ".jpg"
    rgx_mask = r"([0-9]*)_([A-Za-z0-9 ]*)_([a-zA-Z \-]*)_([a-zA-Z0-9 \-]*)"
    
    side_list= []
    rgx = re.compile(rgx_mask)

    log_path = os.path.join(actual_path, f"{studyID}_LOG_VisiaRenamedFiles.pickle")

    for fn in os.listdir(actual_path):
        if fn.endswith(file_ext):    
            try:
                side_list.append(re.search(rgx, fn).group(3))
                
            except:
                raise filenameError(f"Check side id again for {fn} with mask {rgx_mask}")
                
    side_list = set(side_list)
    # associates a side number to the side names # visia only has 3 views
    sides_key_dict = {"Right View": 1, 
                      "Front View": 2, 
                      "Left View": 3,
                      "Right Face" : 1,
                      "Front Face" : 2,
                      "Left Face" : 3,
                      "Right Lower Forearm":1, #TODO: check the key names again
                      "Right Upper Forearm":2,
                      "Left Lower Forearm":3,
                      "Left Upper Forearm":4,
                      "Right Oblique": 1,
                      "Frontal": 2,
                      "Left Oblique" : 3,
                      }

    # sides_counter_list = ["F01", "F02", "F03"] # normal studies
    sides_counter_list = ["F01", "F02", "F03", "F04"] # 24.0021_UV-erythema studie; visia with wierd visia names
    

    sorted_key = [(x , sides_key_dict[x]) for x in side_list]
    sorted_side_keys = sorted(sorted_key, key= lambda x: x[1])

    side_dict = {}
    for n, ele in enumerate(sorted_side_keys):
        side_dict[ele[0]] = sides_counter_list[n]

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
                "BrownSpots": "BRSP",
                "STD1": "STD1",
                "Raked": "RAKD",
                "UV Absorption": "UVAB",
                "NB Blue Fluorescence": "NBFF",
                "NB Blue Absorption": "NBAB"
                }

    log_dict = {}

    for fn in os.listdir(actual_path):
    
        if fn.endswith(file_ext):
            try:
                orig_subj_num = re.search(rgx, fn).group(1)
            except:
                raise filenameError(f"check Subj of {fn} for mask {rgx_mask}")
            if len(orig_subj_num) == 3:
                subjHead = "S" + orig_subj_num
            elif len(orig_subj_num) == 2:
                subjHead = "S0" + orig_subj_num
            elif len(orig_subj_num) == 1:
                subjHead = "S00" + orig_subj_num
            try:
                timeHead = re.search(rgx, fn).group(2)
                if "D" in timeHead and "Day" not in timeHead:
                    timeHead = timeHead.replace(" ", "").replace("D", "T")
                elif "Day" in timeHead:
                    timeHead = timeHead.replace(" ", "").replace("Day", "T")
                elif "Baseline" in timeHead:
                    timeHead = timeHead.replace(" ", "").replace("Baseline", "T01")
                elif "t" in timeHead:
                    timeHead = timeHead.replace(" ", "").replace("t", "T")
            except:
                raise filenameError(f"check timep of {fn} for mask {rgx_mask}")                
            try:
                sideHead = side_dict[re.search(rgx, fn).group(3)]
            except:
                raise filenameError(f"check sideid of {fn} for mask {rgx_mask}")                
            try:
                lightHead = light_dict[re.search(rgx, fn).group(4)]
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
    with open(log_path, "wb") as picklef:
        pickle.dump(log_dict, picklef)

    print("Renaming finished; changes stored in json log file")
  
# uncomment for testing or reverse renaming
if __name__ == "__main__":
    
    PATH = os.environ.get("STUDY_PATH", "data/test/skin_imager_renamer_test/all")
    
    studynum = re.search(r"[0-9\.\-]{10}", PATH).group(0)
    rename_visia_files(PATH, studynum)
    
    json_log_file_path = os.environ.get("LOG_FILE_PATH", "data/test/skin_imager_renamer_test/all/XX.XXXX-XX_LOG_RenamedFiles.pickle")

    # reverse_renaming(json_log_file_path, PATH)