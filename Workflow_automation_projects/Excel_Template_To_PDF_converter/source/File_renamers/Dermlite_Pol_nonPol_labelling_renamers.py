import os
import re

def main():
    PATH = os.environ.get("STUDY_PATH", "data/study/images/raw_cleaned")
    REGEX = r"(S[0-9]{3})(F[0-9]{2})(T[0-9]{2})"
    subj_id_list = sorted(set([re.search(REGEX, fn).group(1) for fn in os.listdir(PATH) if fn.endswith(".cr2")]))
    side_id_list = sorted(set([re.search(REGEX, fn).group(2) for fn in os.listdir(PATH) if fn.endswith(".cr2")]))
    time_id_list = sorted(set([re.search(REGEX, fn).group(3) for fn in os.listdir(PATH) if fn.endswith(".cr2")]))
    EXTN = ".cr2"
    DIRECTION = ["CP", "NP"] #["NP", "CP"]#orig
    # path = pathlib.Path(PATH)

    tmp_dict = {}
    for subj in subj_id_list:
        for time in time_id_list:
            for side in side_id_list:
                for fn in os.listdir(PATH):
                    if subj in fn and side in fn and time in fn and fn.endswith(EXTN):
                        heading = (subj, side, time)
                        try:
                            tmp_dict[heading].append(fn)
                        except KeyError:
                            tmp_dict[heading] = []
                            tmp_dict[heading].append(fn)

    for k in tmp_dict.keys():
        if len(tmp_dict[k]) ==2: 
            tmp_dict[k] = sorted(tmp_dict[k], key=lambda x : x.split("_")[1].split(".")[0])
            fn_0 = tmp_dict[k][0].replace(EXTN, "_"+ DIRECTION[0] + EXTN)
            fn_1 = tmp_dict[k][1].replace(EXTN, "_"+ DIRECTION[1]+ EXTN)
            print(fn_0, fn_1)
            print(1)
            os.rename(os.path.join(PATH, tmp_dict[k][0]), os.path.join(PATH, fn_0))
            os.rename(os.path.join(PATH, tmp_dict[k][1]), os.path.join(PATH, fn_1))

        else:
            with open(os.path.join(PATH, "missing.txt"), "a+") as mf:
                print(k, file=mf)
                print(f"{k} missing - check")
                print(2)

if __name__ == "__main__":
    main()
