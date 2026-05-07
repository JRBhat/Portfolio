import os
import re
import pprint
import json

######################Store replaced names as dict
# path = os.environ.get("STUDY_PATH", "data/study/jpg_small50/test")
# count = 1
# # read filenames
# swap_dict = {}
# for fname in os.listdir(path):
#     print(fname)

#     if count > 9:
#         count = 1

# # using regex, group important elements
#     reg_ex = re.search("(S[0-9]{3}F[0-9]{2}T[0-9]{2})(Ult[ _A-Za-z0-9]*)", fname)
#     barcode =  reg_ex.group(1)
#     new_barcode = barcode + "_U" + str(count)
#     swapped_val = reg_ex.group(2)
#     swap_dict[new_barcode] = swapped_val

#     count += 1

# # create a dict - key(replacement): U1-9; val(replaced): Ult1 1723 ST23_val
# pprint.pprint(swap_dict)


# with open(os.path.join(path, "swap_dict.txt"), "w") as dict_file:
#     dict_file.write(json.dumps(swap_dict))


# ##################### rename files
# for fname in os.listdir(path):

#     for key, val in swap_dict.items():
#         if val in fname:
#             os.rename(os.path.join(path, fname), os.path.join(path, key +".jpg"))
#############################################################################################################################
##################### # after PDF
path_to_tex = os.environ.get("TEX_FILE_PATH", "data/study/output/image_overview_final.tex")
path_to_dict = os.environ.get("SWAP_DICT_PATH", "data/study/swap_dict.txt")
path_to_imgs = os.environ.get("IMAGES_PATH", "data/study/jpg_small50")

with open(path_to_dict, "r") as dict_file:
    dict_data = dict_file.read()
    swap_dict = json.loads(dict_data)

with open(path_to_tex, "r") as tex_file:
    tx_lines = tex_file.readlines()

new_tex_list = []
for l in tx_lines:
    new_tex_list.append(l)        
    for k in swap_dict.keys():
        if k in l:
            new_l = l.replace(k, k[:-3]+swap_dict[k])
            new_tex_list.remove(l)
            new_tex_list.append(new_l)
            break
    if "tiny" in l:
        for k in swap_dict.keys():
            if k.replace("_", "\_") in l:
                new_l = l.replace(k.replace("_", "\_"), k[:-3].replace("_", "\_")+swap_dict[k])
                new_tex_list.remove(l)
                new_tex_list.append(new_l)
                break


with open(os.path.join(path_to_imgs, "corrected_latex.tex"), "w") as correct_tex_f:
    for line_ele in new_tex_list:
        correct_tex_f.write(line_ele)

for fname in os.listdir(path_to_imgs):
    if fname.endswith(".jpg"):
        for key in swap_dict.keys():
            if key in fname:
                new_name = fname.replace(key, key[:-3]+swap_dict[key])
                os.rename(os.path.join(path_to_imgs, fname), os.path.join(path_to_imgs, new_name))
