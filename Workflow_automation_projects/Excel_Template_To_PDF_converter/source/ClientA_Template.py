
import re
import os

# Dictionary with keys(A-G) and Values(Side names)
side_name_dict = {
    "A" : "Left Upper arm",
    "B" : "Right Upper arm",
    "C" : "Left Thigh",
    "D" : "Right Thigh",
    "E" : "Left Calf",
    "F" : "Right Calf",
    "G" : "Kneecap"
}

# Product_ids = ["(Prod A)", "(Prod B)", "(Prod C)", "(Prod D)", "(Prod E)", "(Prod F)", "(Prod G)"]
# Product_seq_list = Product_ids * 30
# prod_seq_gen = iter(Product_seq_list)


# read the random list and replace each character(key) with corresponding dict value
randomList_path = os.environ.get("RANDOM_LIST_PATH", "data/randomization_clean.txt")  # path to random file cleaned
with open(randomList_path) as randPath:

    lines_randgen = iter(randPath.readlines())

# S001F01T01FTO.jpg}}&&\raisebox{

lines_rand = []
while True:
    try:
        lines_rand.append(next(lines_randgen).replace("\n",""))
    except StopIteration:
        break
print(lines_rand)

list_rand = []
for line in lines_rand:
    for alphabet in line:
        list_rand.append((alphabet, side_name_dict[alphabet]))


list_rand_gen = iter(list_rand)
# Read each line from final latex file and store as list
latest_tex_file_path = os.environ.get("TEX_FILE_PATH", "output/main.tex")  # path to tex file
with open(latest_tex_file_path) as texPath:
    lines_tex= texPath.readlines()
print(lines_tex)

barcode_mask = r"S[0-9]{3}[0-9]{2}T[0-9]{2}FTO.jpg\}\}&&\\raisebox\{"
side_mask = r"F[0-9]{2}"

side_name_mask = re.compile(r"\}\{[a-zA-Z ]*\}\}&")
# Locate the lines with row names per subject
        # if "\raisebox{-.5\height}{\rotatebox{90}" in tex_line
# 
for big_line in lines_tex:
    if r"\raisebox{-.5\height}{\rotatebox{90}" in big_line:

        side_name = side_name_mask.search(big_line).group(0)
        val = next(list_rand_gen)
        replacement = "}{" + val[1]+ "Prd" + val[0] + "}}&"
        new_big_line = big_line.replace(side_name, replacement)
        lines_tex[lines_tex.index(big_line)] = new_big_line

print(lines_tex)
new_file_gen = iter(lines_tex)


new_texfile_name = latest_tex_file_path.split("\\")[-1][:-4]
with open(os.path.join("\\".join(latest_tex_file_path.split("\\")[:-1]),
                       f"{new_texfile_name}_randomized_sidenames_revised1.tex"), "w") as f_new:
    while True:
        try:
            f_new.write(next(new_file_gen))
        except StopIteration:
            break



