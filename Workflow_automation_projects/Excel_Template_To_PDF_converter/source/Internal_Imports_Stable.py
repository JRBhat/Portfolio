'''
This file acts as a one-stop place, which contains all the input data required by the application.
Data is imported from here at various points during the flow of control.
It's isolated nature helps easy modification of repeatedly used variables and constants
'''

# Assigning path containing the image files to a variable 'path'
# Python config module - suggestions; Creating config files 

import json
from random import randint
import os
from ImageAnalysis import ColorConversion as cc

class InternalImport:
    
    def __init__(self):
        data = self.__read_config_data()
        self.mypath = data['path']
        self.studynumber = data['stdyno']
        self.filename_mask = data['MASK']
        self.draft_flag = data['FAST_DRAFT']
        self.isVisia = data['Is_Visia']
        self.path_for_validation = self.mypath
        self.validated_path = "" 
        self.No_marketing = data['No_marketing']
        self.colorfile, self.colorname, self.file_extension = self.__get_colorprofile_specs(self.path_for_validation)
        self.Test_type, self.randomfilepath = self.__get_testinfo_for_output_folder_naming(data)
        self.header = self.__get_header(self.draft_flag)
        self.pagestyle = self.__get_pagestyle(self.No_marketing, self.studynumber)
        # header handles
        self.hypersetup = r"""\hypersetup{pdftitle={Image Export},
                                pdfauthor={User},
                                pdfauthortitle={Scientist},
                                pdfcopyright={Copyright (C) 2025, YourOrganization},
                                pdfsubject={Image Overview},
                                pdfkeywords={image, overview},
                                pdflicenseurl={none},
                                pdfcaptionwriter={Author},
                                pdfcontactaddress={123 Research Avenue},
                                pdfcontactcity={Your City},
                                pdfcontactpostcode={00000},
                                pdfcontactcountry={Your Country},
                                pdfcontactemail={contact@yourorganization.com},
                                pdfcontacturl={http://www.yourorganization.com},
                                pdflang={en},
                                bookmarksopen=true,
                                bookmarksopenlevel=3,
                                hypertexnames=false,
                                linktocpage=true,
                                plainpages=false,
                                breaklinks}
                            """
        # self.ClientStudy_randomfilepath = self.__check_for_clientstudy_randomfilepath(data)
            
        self.excelfile = f'Layout_{self.studynumber}{self.Test_type}.xlsx' # create the an empty "laylout" excel file
        self.dummy_log_file = f'{self.Test_type}_missing.txt' # create the log file for logging missing data


    def __read_config_data(self):
        
        input_json_path = input("Please provide the path of the Json configuration file for the study: ")

        # load study config .json
        with open(rf"{input_json_path}", "r") as config_file:
            data = json.load(config_file)
        return data


        
    def __get_header(self, draft_flag):
        if draft_flag == "False":
            return r"""\RequirePackage{pdf14}
            \documentclass[a4paper]{scrartcl}
            \usepackage{helvet}
            \renewcommand{\familydefault}{\sfdefault}
            \usepackage[utf8]{inputenc}
            \usepackage[export]{adjustbox}
            \usepackage{fancyhdr}
            \usepackage[left=1.00cm,right=1.00cm,top=0.50cm,bottom=1.50cm,headheight=1.50cm,headsep=0.5cm,footskip=0.5cm,includeheadfoot]{geometry}
            \setlength{\parindent}{0cm}
            \usepackage[pdfa]{hyperref}
            \usepackage{hyperxmp}
            \def\arraystretch{0.9}
            \usepackage{grffile}
            \usepackage{pdf14}
            \usepackage{silence}
            \usepackage{graphicx}
            \WarningsOff*
            \ErrorsOff*

            \immediate\pdfobj stream attr{/N 3}  file{%s}
            \pdfcatalog{/OutputIntents [ <<
            /Type /OutputIntent
            /S/GTS_PDFA1
            /DestOutputProfile \the\pdflastobj\space 0 R
            /OutputConditionIdentifier (%s)
            /Info(%s)
            >> ]
            }
            """ % (self.colorfile, self.colorname, self.colorname)
        elif draft_flag == "True":
            return r"""\RequirePackage{pdf14}
                            \documentclass[a4paper, draft]{scrartcl}
                            \usepackage{helvet}
                            \renewcommand{\familydefault}{\sfdefault}
                            \usepackage[utf8]{inputenc}
                            \usepackage[export]{adjustbox}
                            \usepackage{fancyhdr}
                            \usepackage[left=1.00cm,right=1.00cm,top=0.50cm,bottom=1.50cm,headheight=1.50cm,headsep=0.5cm,footskip=0.5cm,includeheadfoot]{geometry}
                            \setlength{\parindent}{0cm}
                            \usepackage[pdfa]{hyperref}
                            \usepackage{hyperxmp}
                            \def\arraystretch{0.9}
                            \usepackage{grffile}
                            \usepackage{silence}
                            \WarningsOff*
                            \ErrorsOff*

                            \immediate\pdfobj stream attr{/N 3}  file{%s}
                            \pdfcatalog{/OutputIntents [ <<
                            /Type /OutputIntent
                            /S/GTS_PDFA1
                            /DestOutputProfile \the\pdflastobj\space 0 R
                            /OutputConditionIdentifier (%s)
                            /Info(%s)
                            >> ]
                            }
                            """ % (self.colorfile, self.colorname, self.colorname)
        
    def __get_pagestyle(self, marketing_flag, studynumber):
        # No marketing handle
        if marketing_flag == "True":
            return r"""\pagestyle{fancy}
            \rhead{\includegraphics[scale=0.5]{bin/organization_logo.jpg}}
            \lfoot{Confidential \\ Do not use for marketing purposes \\ \tiny For legal reasons, the images provided must not be used for marketing purposes.}
            \cfoot{%s\\ Image Overview}
            \rfoot{Page \thepage}
            """ % (studynumber.replace('_', '\\_') )
        else:
            return r"""\pagestyle{fancy}
                \rhead{\includegraphics[scale=0.5]{bin/organization_logo.jpg}}
                \lfoot{Confidential \\ Vertraulich}
                \cfoot{%s\\ Image Overview}
                \rfoot{Page \thepage}
                """ % (studynumber.replace('_', '\\_') )


    def __get_testinfo_for_output_folder_naming(self, data):

        user_input = input("What kind of test is this(s/t/sr/tr/c): ")
        counter = input("Iteration number: ")
        try:
            if counter == "":
                # seed(1) # for pseudo random numbers
                counter = str(randint(0,100))
                
            if user_input.lower() == "s":
                return f"S_{counter}", None
            
            elif user_input.lower() == "t":
                return f"T_{counter}", None
            
            elif user_input.lower() == "sr":
                return f"SR_{counter}", data["RANDOM"]
            
            elif user_input.lower() == "tr":
                return f"TR_{counter}", data["RANDOM"]
            
            elif user_input.lower() == "c":
                if data["RANDOM"] != "None":
                    return f"C_{counter}", data["RANDOM"]
                else:
                    return f"C_{counter}", None
        except TypeError:
            print("Incorrect input for test type - please try again with s, t, sr, tr or c")
    ## --------- COLOR PROFILE ---------- ##
    def __get_colorprofile_specs(self, path_to_images):
        """
        check_image_type_and_colorprofile 
        """
        files_list = os.listdir(path_to_images)
        # check for jpgs
        jpg_found_list = []
        for f in files_list:
            if (f.endswith("jpg") or f.endswith("JPG")) and isinstance(f, str):
                jpg_found_list.append(f)
                type = "jpg"
                filepath = os.path.join(path_to_images, f)
                colorspace_tuple = cc.get_colorprofile(filepath)
                cfile, cname = self.__color_profile_elements(colorspace_tuple)
                return cfile, cname, type
                
        # # if no jpgs found, check for pngs or tifs
        png_found_list = []
        if len(jpg_found_list) == 0:
            for f in files_list:
                if f.endswith("png") and isinstance(f, str):
                    png_found_list.append(f)
                    type = "png"
                    filepath = os.path.join(path_to_images, f)
                    colorspace_tuple = cc.get_colorprofile(filepath)
                    cfile, cname = self.__color_profile_elements(colorspace_tuple)
                    return cfile, cname, type
                        
        if len(png_found_list) == 0 and len(jpg_found_list)== 0:
            for f in files_list:
                if (f.endswith("tiff") or f.endswith("tif") or f.endswith("TIF")) and isinstance(f, str):
                    type = "tif"
                    filepath = os.path.join(path_to_images, f)
                    colorspace_tuple = cc.get_colorprofile(filepath)
                    cfile, cname = self.__color_profile_elements(colorspace_tuple)
                    return cfile, cname, type 
  
                                              
    def __color_profile_elements(self, colorspace_tuple):
        """
        get_color_profile 
        """
        try:
            if colorspace_tuple[0] == 'srgb':
                colorfile = 'bin/sRGB_Color_Space_Profile.icm'
                colorname = "sRGB Color Space Profile"
                return colorfile, colorname 
            elif colorspace_tuple[0] == 'adobe':
                colorfile = 'bin/AdobeRGB1998.icc'
                colorname = "adobeRGB Color Space Profile"
                return colorfile, colorname 
        except IndexError:
            print("No colorprofile found, applying default colorspace sRGB")
            colorfile = 'bin/sRGB_Color_Space_Profile.icm'
            colorname = "sRGB Color Space Profile"
            return colorfile, colorname 



