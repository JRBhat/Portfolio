import re
import os
import pprint
from py import code

path = os.environ.get("TEX_FILE_PATH", "data/study/output/image_overview_final.tex")

f_list = []
with open(path, 'r') as f:
    for line in f.readlines():
        f_list.append(line)

tiny_counter = 0
for n, l in enumerate(f_list):
    if "tiny" in l:
        tiny_counter += 1
        if tiny_counter == 1:
                
            codes = re.search("(S[0-9]{3})(F[0-9]{2})(T[0-9]{2})", l)
            sub_full =  codes.group(1)
            sub =  codes.group(1).replace("S0", "")
            area_full = codes.group(2)
            area = codes.group(2).replace("F", "")
            time = codes.group(3).replace("T", "")

            print(sub_full, area_full)
            print(sub, area, time)

            if "Large" in f_list[n-3] and "Subject" in f_list[n-3]:
                replacement = f"Subject {sub_full[-2:]}" + "  Day " + time
                f_list[n-3] =  f_list[n-3].replace(f"Subject {sub_full[-2:]}", replacement) 
                print(f_list[n-3])
    
    if "end{tabular}" in l:
        tiny_counter = 0


for no, lt in enumerate(f_list):
    if "tiny" in lt:
        sp_lt = lt.split("&&")
        n_sp_lt = []
        for sp in sp_lt:
            
            codes = re.search("(S[0-9]{3})(F[0-9]{2})(T[0-9]{2})", sp)
            sub_full =  codes.group(1)
            sub =  codes.group(1).replace("S0", "")
            area_full = codes.group(2)
            area = codes.group(2).replace("F", "")
            time = codes.group(3).replace("T", "")
            sp = sp.replace(codes.group(0) +"\\_", sub )
            n_sp_lt.append(sp)
        f_list[no] = "&&".join(n_sp_lt)


new_path = path.replace(".tex", "_modfinal.tex")
with open(new_path, "w") as nf:
    for ln in f_list:
        nf.write(ln)


