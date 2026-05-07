import re
import os
import json
import sys


def rename_eyelashcam_files(path, regx, file_ext, logpath):
    log_dict = {}

    for fn in os.listdir(path):
        if fn.endswith(file_ext):
            subjid = re.search(regx, fn).group(1)
            barcode = "S0" + subjid
            if "Segmentation" in fn:
                barcode += "F02T01EYE-"
            else:
                barcode += "F01T01EYE-"
            new_fn = barcode + fn
            log_dict[new_fn] = fn

    print(log_dict)

    for new_fn, fn in log_dict.items():
        os.rename(os.path.join(path, fn), os.path.join(path, new_fn))


    # dump dict to dict for logging
    with open(logpath, "w") as logJson:
        json.dump(log_dict, logJson)


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
        
    PATH = os.environ.get("STUDY_PATH", "data/study/PDF")
    STUDY_ID = os.environ.get("STUDY_ID", "XX.XXXX-XX")
    REGX_PATTERN_WITH_GROUPING = r"([0-9]{2})*"
    FILE_EXT = ".jpg"
    LOG_PATH = os.path.join(PATH, f"{STUDY_ID}_LOG_VisiaRenamedFiles.json")

    rename_eyelashcam_files(PATH, REGX_PATTERN_WITH_GROUPING, FILE_EXT, LOG_PATH)

    # uncomment for reversing renaming
    # reverse_renaming(LOG_PATH, PATH, FILE_EXT)
    
if __name__ == "__main__":
    main()