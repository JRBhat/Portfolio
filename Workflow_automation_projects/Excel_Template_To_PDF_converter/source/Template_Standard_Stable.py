import Internal_Imports_Stable as Imp 
from Latex_File_Create_Stable import create_final_latex_file
from Common_Functions_Stable import create_Latex_document

def standardize(area_code_list, time_code_list, area_sorted, 
                time_sorted, sub_sorted, 
                filepaths, filenamelist, 
                rownames, colnames, 
                random_iter, 
                Imp):
    """
    Standard template - User needs to only change the column and row names
    """    
    nr_col=len(time_code_list)#len(time_list)
    nr_row=len(area_code_list)#len(area_list)

    max_height=round(1.0/(1.25*nr_row), 2) 
    
    next_label_count = "".join(rownames).count("next")
    if next_label_count > 0:
        max_height=round((1.0*next_label_count)/(1.25*nr_row), 2)

    max_width=round(1.0/(1.5*nr_col), 2) 


    lax_document, new_page_alert = create_Latex_document(colnames, rownames,  
                                                         sub_sorted, 
                                                         max_height, max_width, 
                                                         area_sorted, time_sorted, 
                                                         filepaths, filenamelist, 
                                                         Type="Standard", 
                                                         RandomList=random_iter)

    std_tex_file = create_final_latex_file(Imp.studynumber, 
                                           Imp.header, 
                                           Imp.pagestyle, 
                                           Imp.hypersetup, 
                                           lax_document, 
                                           new_page_alert, 
                                           colnames, 
                                           Imp.Test_type, 
                                           draft=Imp.draft_flag)

    return std_tex_file

 