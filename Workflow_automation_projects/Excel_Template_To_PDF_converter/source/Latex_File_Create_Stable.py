import os


def create_final_latex_file(studynumber, header, pagestyle, hypersetup, 
                                    lax_document, new_page_alert, colnames, Testtype, draft='False'):#, special=None):
    """
    Creates the final layout (.tex) which can then be converted to PDF

    *args: can take either client_study random file path or column_name_per_row_list
    special=None can take "ClientStudy" or  "ColumnNames"
    """    

    #  If draft mode is ON; only image paths printed in PDF, loading the images is skipped (useful for testing purposes)
    if draft == 'True':
        with open(f"{studynumber}_{Testtype}_image_overview_draft.tex", "w") as f:
            f.write(header)
            f.write(pagestyle)
            f.write(hypersetup + "\n") 

            f.write(r"\begin{document}" + "\n\n")

            for pageno, lax_page in enumerate(lax_document):
                lax_table = lax_page['table'][pageno]
                f.write(r"{\Large %s}\\[0.2cm]"%(lax_page['heading'][pageno]) + "\n")
                f.write(r"\begin{tabular}{%s}"%("".join(['cc']*(len(colnames)))) + "\n")
                f.write(lax_page['col_name_block'] + "\n")
                for lax_row in lax_table:
                    f.write(lax_row + "\n")

                if new_page_alert == 0:
                    f.write(r"\end{tabular}" + "\n")
                    if 'end' not in lax_table and not (pageno == len(lax_document)-1):
                        f.write(r"\newpage" + "\n\n")
                
            f.write(r"\end{document}" + "\n")
        tex_filename = os.path.join(os.getcwd(), f"{studynumber}_{Testtype}_image_overview_draft.tex")
    # original; where all photos are downloaded; final PDF generated
    elif draft == 'False':
        with open(f"{studynumber}_{Testtype}_image_overview.tex", "w") as f:
            f.write(header)
            f.write(pagestyle)
            f.write(hypersetup + "\n") 

            f.write(r"\begin{document}" + "\n\n")

            for pageno, lax_page in enumerate(lax_document):
                lax_table = lax_page['table'][pageno]
                f.write(r"{\Large %s}\\[0.2cm]"%(lax_page['heading'][pageno]) + "\n")
                f.write(r"\begin{tabular}{%s}"%("".join(['cc']*(len(colnames)))) + "\n")
                f.write(lax_page['col_name_block'] + "\n")
                for lax_row in lax_table:
                    f.write(lax_row + "\n")

                f.write(r"\end{tabular}" + "\n")
                if 'end' not in lax_table and not (pageno == len(lax_document)-1):
                    f.write(r"\newpage" + "\n\n")
            f.write(r"\end{document}" + "\n")
    
        tex_filename = os.path.join(os.getcwd(), f"{studynumber}_{Testtype}_image_overview.tex")

    
    return tex_filename


