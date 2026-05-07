import os
import re

raw_path = os.environ.get("STUDY_PATH", "data/study/imgs")

rgx = r"([0-9]*)_([0-9]*)_([0-9a-z]*)"

for fn in os.listdir(raw_path):
    # print(fn)
    result = re.search(rgx, fn)
    subjid = result.group(1)
    if int(subjid) < 10:
        subjid = "0" + subjid

    dayid = result.group(2)
    if dayid == "0":
        dayid = "T01"
    elif dayid == "1":
        dayid = "T02"
    else:
        dayid = "T03"

    viewid = result.group(3)

    if viewid == "m1":
        viewid = "F01"
    elif viewid == "m2":
        viewid = "F02"
    elif viewid == "z1":
        viewid = "F03"
    elif viewid == "z2":
        viewid = "F04"
    elif viewid == "z3":
        viewid = "F05"
    else:
        viewid = "F06"    

    new_fn = "S0" + subjid + viewid + dayid + "__" + fn
    print(new_fn)
    os.rename(os.path.join(raw_path, fn), os.path.join(raw_path, new_fn))

