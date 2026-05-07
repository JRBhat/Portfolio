
import pprint
import os


def latexify_column_name_per_row(element_from_colname_list):
    """
    Gets list of column names per row and converts them to a line as per latex convention/syntax
    """    
    try:
        split_list = element_from_colname_list.split(";")
    except AttributeError:
        print("List contains None or empty values; please check excel file or code")
        return 0
    final_column_block = "&"
    for sub_ele in split_list:
        final_column_block += sub_ele
        if sub_ele == split_list[-1]:
            final_column_block += "\\\\"
            break
        final_column_block += "&&"
    return final_column_block


def give_each_row_columnames(row_column_named_list, fpath):
    """
    generates a new latex file with independent column names attached to each row element

    """    
    
    new_latex_list = []
    counter = 0
    with open(fpath) as ftex:
        #rand_gen = iter(frand.readlines())
        org_latex_list = ftex.readlines()
        # pprint.pprint(org_latex_list)

        for lno, line in enumerate(org_latex_list):
            if '\\raisebox' in line:
                
                if latexify_column_name_per_row(row_column_named_list[counter]) == org_latex_list[lno-1]:
                    if counter == len(row_column_named_list)-1:
                        counter = 0
                    else:
                        counter += 1
                    new_latex_list.append(line) # appends current raisebox line
                    continue
                elif "begin" in org_latex_list[lno-2]:
                    new_latex_list.remove(new_latex_list[-1]) # removes the recently added element - old column name
                    new_latex_list.append(latexify_column_name_per_row(row_column_named_list[counter]))
                    if counter == len(row_column_named_list)-1:
                        counter = 0
                    else:
                        counter += 1
                    new_latex_list.append(line)
                    continue
                else: 
                    new_latex_list.append(latexify_column_name_per_row(row_column_named_list[counter]))
                    if counter == len(row_column_named_list)-1:
                        counter = 0
                    else:
                        counter += 1
                    new_latex_list.append(line)
                    continue
            new_latex_list.append(line)

    pprint.pprint(new_latex_list)
    new_list_gen = iter(new_latex_list)
    old_tex_file_name = fpath.split("\\")[-1]
    new_file_path = os.path.join("\\".join(fpath.split("\\")[:-1]), f"{old_tex_file_name[:-4]}_colnameappend.tex")

    
    with open(new_file_path, "x") as mylatexfile:
        while True:
            try:
                mylatexfile.write(str(next(new_list_gen)))
            except StopIteration:
                break
    
    return new_file_path
