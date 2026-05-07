
import re 
import os
from pathlib import Path
from itertools import chain

import Common_Functions_Stable as CFS



def randomize_custom_rand_alllightingcode(filelist, randomfilepath, area_id_list, time_id_list, sorted_subject_id_list):
    """
    Applies subject- and light-specific randomization based on external mapping (randomfilepath).
    Maps each file to a product code and reorders according to mapping.

    Parameters:
    filelist (list): List of file paths.
    randomfilepath (str): Path to randomization mapping file.
    area_id_list (list): Area IDs (e.g., ['F01', 'F02']).
    time_id_list (list): Timepoint IDs (e.g., ['T01', 'T02']).
    sorted_subject_id_list (list): Subject IDs (e.g., ['S001', 'S002']).

    Returns:
    iterator: Final randomized iterator of (filepath, product_code) tuples.
    """
    # create tuple (filepath, (subid, *areaid/timeid)) # *needs to be changed depending on template requirement
        # regex to check if ids from iterator match ids in filenames - exception when not matching

    tuple_list_with_path_and_ids = []

    # e.g. clone random sequence for each light code in visia 

    # Extract all light codes in one comprehension, then dedupe by set
    light_id_list = list({
        re.search(r"S[0-9]{3}F[0-9]{2}T[0-9]{2}([0-9A-Za-z]*)", Path(fp).name).group(1)
        for fp in filelist
    })
    
    tuple_list_with_path_and_ids = [
        (fp, (subj, ar, time, li))
        for subj in sorted_subject_id_list
        for time in time_id_list
        for ar in area_id_list
        for li in light_id_list
        for fp in filelist
        if subj in Path(fp).name
        and ar in Path(fp).name
        and time in Path(fp).name
        and li in Path(fp).name
    ]
    
    #[('data\\study...ntour1.jpg', ('S001', 'F01')), 
                                        # ('data\\study...ntour2.jpg', ('S001', 'F02'))]

    # read random sequence from the randomization file (.txt file in study folder) and validate subject ids (check if file has equal number of subjects)
    cleaned_list = CFS.validate_random_file(randomfilepath, sorted_subject_id_list) # only seq of 4 letters per line
    print(cleaned_list) # ['AB', 'BA', 'BA', 'AB', 'BA'...]

    # create a dictionary with tuple (sub, arid) as key and value as Product alphabet from line per subject    
    mapping_dict = {
        (subj, ar, time, li): p_id
        for line, subj in zip(cleaned_list, sorted_subject_id_list)
        for time in time_id_list
        for li in light_id_list
        for p_id, ar in zip(line, area_id_list)
    }    
    
    print(mapping_dict) #{('S001', 'F01'): 'A', ('S001', 'F02'): 'B', ('S002', 'F01'): 'B',...}

    # map each tuple in tuple_list_with_ids with ids(values) using mapping_dict's keys with tuple idicies(tuple[0])

    derandomized_list = []
    #                 derandomized_list.append(grouped_by_subj) # [[('data\\study...ntour1.jpg', 'A'), ('data\\study...ntour2.jpg', 'A'), ('data\\study...ntour2.jpg', 'A'), ('data\\study...ntour1.jpg', 'B'), ('data\\study...ntour1.jpg', 'B'), ('data\\study...ntour1.jpg', 'B')], [(...), (...), (...), (...), (...), (...)]
    derandomized_list = []
    for k, v in mapping_dict.items():
        derandomized_list.append([(path, v) for path, ids in tuple_list_with_path_and_ids if ids==k][0])
    print(derandomized_list)
    
    # groups list into sub-groups according to number of products - prep for derandomization
    split_len = len(cleaned_list[0])
    if split_len == 2:
        grouped_derandomized_list = [derandomized_list[i:i + split_len] for i in range(0, len(derandomized_list), split_len)]

    # derandomization - here the filenames are swapped when swapped product code sequences are detected 
    # swap if BA, do not swap if AB
    for i in range(len(grouped_derandomized_list)):
        if grouped_derandomized_list[i][0][1] == 'B':
            grouped_derandomized_list[i][0], grouped_derandomized_list[i][1] = grouped_derandomized_list[i][1], grouped_derandomized_list[i][0]
    
    print(grouped_derandomized_list)
    
    # remove nested lists so that the final list contains just single tuples
    # or in other words flatten nested lists by one level.
    final_derandomized_list = list(chain.from_iterable(grouped_derandomized_list))

    print(final_derandomized_list) # [('data\\study...ntour1.jpg', 'A'), ('data\\study...ntour1.jpg', 'A'), (path, 'A'),(path, 'B'),(path, 'B'), (path, 'B')...(...),(...),(...)]
    # define the desired lighting order
    lighting_order = {'RAKD': 0, 'XPOL': 1, 'PPOL': 2, 'STD1': 3}# TODO: get the lighting code order from the img matrix specified in the excel template

    # regex: captures subject, F, T and the lighting code (everything between T\d+ and --)
    pattern = re.compile(r'S(\d+)F(\d+)T(\d+)([^-]+)--')

    def sort_key(item):
        path, label = item
        m = pattern.search(path)
        if not m:
            # put unknown-format items at the end, preserving original order among themselves
            return (10**6, 10**6, 10**6, 10**6)
        subj = int(m.group(1))
        t = int(m.group(3))
        lighting = m.group(4)
        li = lighting_order.get(lighting, 999)  # unknown lighting -> last
        return (subj, li, t)

    # produce sorted list
    reordered_final_randomised_list = sorted(final_derandomized_list, key=sort_key)
    reordered_final_randomised_list_iter = iter(reordered_final_randomised_list)

    return reordered_final_randomised_list_iter


def randomize_std(filelist, randomfilepath, area_id_list, time_id_list, sorted_subject_id_list):
    """
    Standard randomization that doesn't depend on lighting variation.
    Matches file paths with area + subject IDs and maps them to random product codes.

    Parameters:
    filelist (list): List of file paths.
    randomfilepath (str): Path to randomization mapping file.
    area_id_list (list): Area IDs.
    time_id_list (list): Time IDs (used for validation).
    sorted_subject_id_list (list): List of subject IDs.

    Returns:
    iterator: Final randomized iterator of (filepath, product_code) tuples.
    """
    
    tuple_list_with_path_and_ids = []

    for subj in sorted_subject_id_list:
        for ar in area_id_list:
            for tim in time_id_list:
                for filepath in filelist:
                    filenm = filepath.split("\\")[-1]
                    if subj in filenm and ar in filenm and tim in filenm:
                        # validation
                        val_code = CFS.extract_elements_from_regex_mask(filenm, r"S[0-9]{3}F[0-9]{2}")
                        comparison = str(subj + ar)
                        if  val_code == comparison:
                            tuple_list_with_path_and_ids.append((filepath, (subj, ar)))
                        else:
                            print(f"val id in path({val_code}) does not match with comparision iterator ({comparison})")
                            raise BaseException

    print(tuple_list_with_path_and_ids)  #[('data\\study...ntour1.jpg', ('S001', 'F01')), ('data\\study...ntour2.jpg', ('S001', 'F02'))]

    # read random sequence from the randomization file (.txt file in study folder) and validate subject ids (check if file has equal number of subjects)
    cleaned_list = CFS.validate_random_file(randomfilepath, sorted_subject_id_list) # only seq of 4 letters per line
    print(cleaned_list) # ['AB', 'BA', 'BA', 'AB', 'BA'...]

    # create a dictionary with tuple (sub, arid) as key and value as Product alphabet from line per subject 
    # { (S001, F01): B, (S001, F02): C, (S001, F03): D, (S001, F04): A, etc}

    mapping_dict = {}
    for line, subj in zip(cleaned_list, sorted_subject_id_list):
        for p_id, ar in zip(line, area_id_list):
            mapping_dict[(subj, ar)] = p_id        
    
    print(mapping_dict) #{('S001', 'F01'): 'A', ('S001', 'F02'): 'B', ('S002', 'F01'): 'B',...}

    # map each tuple in tuple_list_with_ids with ids(values) using mapping_dict's keys with tuple idicies(tuple[0])

    derandomized_list = []
    for subj in sorted_subject_id_list:
        grouped_by_subj = [(tupl[0], mapping_dict[tupl[1]]) for tupl in tuple_list_with_path_and_ids if subj==tupl[1][0]]
        derandomized_paths_grouped_per_subj = sorted(grouped_by_subj, key=lambda x: x[1])
        derandomized_list.append(derandomized_paths_grouped_per_subj) # [[('data\\study...ntour1.jpg', 'A'), ('data\\study...ntour2.jpg', 'A'), ('data\\study...ntour2.jpg', 'A'), ('data\\study...ntour1.jpg', 'B'), ('data\\study...ntour1.jpg', 'B'), ('data\\study...ntour1.jpg', 'B')], [(...), (...), (...), (...), (...), (...)]
    
    final_derandomized_list = list(chain.from_iterable(derandomized_list))
    
    # [('data\\study...ntour1.jpg', 'A'), ('data\\study...ntour1.jpg', 'A'), (path, 'A'),(path, 'B'),(path, 'B'), (path, 'B')...(...),(...),(...)]

    final_randomised_list_iter = iter(final_derandomized_list)
    return final_randomised_list_iter