"""
internal_imports.py
====================
Static configuration constants shared across the NIAS reporting pipeline.

This module defines three module-level dictionaries that encode EU Food Contact
Material (FCM) group metadata, Cramer toxicological classifications, and the
starting footnote letters for each Word table.

The constants are imported by ``reporting.py`` and forwarded to ``exports.py``
via keyword arguments.  They serve as in-code defaults and can be overridden at
run-time when the live Excel database is loaded via
:func:`~utilityFuncs.util.load_fcm_group_mapping` and
:func:`~utilityFuncs.util.load_cramer_TTC_mapping`.

Contents
--------
mapping_fcm_group : dict
    Maps FCM integer keys (9, 13, 15, 878, 879) to bilingual name/classification
    metadata.  Used as a fallback when the CL_Groups Excel sheet is unavailable.

cramer_group_classification : dict
    Maps chemical group names (e.g. ``'Alkylbenzoate'``) to their Cramer class
    ('I', 'II', or 'III').  Applied when a substance has no explicit Cramer value
    but its SMILES pattern matches a known chemical group.

cramer_TTC_mapping : dict
    Maps Cramer classes to human-readable long names and TTC (Threshold of
    Toxicological Concern) values in µg/kg bw/day.

cur_ft_dict : dict
    Specifies the starting footnote letter for Table 1 and Table 3 in the Word
    output document.  Letters are incremented alphabetically as footnotes are
    appended during rendering.
"""

mapping_fcm_group = {
    9: {'Name_DE':'Monocarbonsäuren, C2-C24, aliphatische, geradkettige, aus natürlichen Fetten und Ölen, und deren Mono-, Di- und Triglycerinester (verzweigte Fettsäuren in natürlich vorkommenden Mengen sind eingeschlossen)',
        'Name_EN':'Acids, C2-C24, aliphatic, linear, monocarboxylic from natural oils and fats, and their mono-, di- and triglycerol esters (branched fatty acids at naturally occuring levels are included)',
        'CL_DE':'',
        'CL_EN':'Test CL_EN fcm9'},
    
    13: {'Name_DE':'Alkohole, aliphatische, einwertige, gesättigte, geradkettige, primäre (C4-C24)', 
        'Name_EN':'Alcohols, aliphatic, monohydric, saturated, linear, primary (C4-C24)',
        'CL_DE':'Langkettige Alkohole werden als Emulgatoren eingesetzt.',
        'CL_EN':'Long-chain alcohols are used as emulsifiers.'},
    
    15: {'Name_DE': 'Alkyl-Dimethylamine, linear mit gerader Anzahl von Kohlenstoffatomen (C12-C20)',
        'Name_EN': 'Alkyl, linear with even number of carbon atoms (C12-C20) dimethylamines',
        'CL_DE': '',
        'CL_EN': 'Test CL_EN fcm15'},
    
    878: {'Name_DE': 'Fettsäuren (C8-C22) aus tierischen oder pflanzlichen Fetten und Ölen, Ester mit verzweigten, einwertigen, primären, gesättigten, aliphatischen Alkoholen (C3-C22)',
        'Name_EN': 'Acids, fatty (C8-C22) from animal or vegetable fats and oils, esters with branched alcohols, aliphatic, monohydric, saturated, primary (C3-C22)',
        'CL_DE': 'Langkettige Alkohole werden als Emulgatoren eingesetzt.',
        'CL_EN': 'Fatty acid esters can be used as lubricants.'},
    
    879: {'Name_DE': 'Fettsäuren (C8-C22) aus tierischen oder pflanzlichen Fetten und Ölen, Ester mit linearen, einwertigen, primären, gesättigten, aliphatischen Alkoholen (C1-C22)',
        'Name_EN': 'Acids, fatty (C8-C22) from animal or vegetable fats and oils, esters with alcohols, linear, aliphatic, monohydric, saturated, primary (C1-C22)',
        'CL_DE': 'Langkettige Alkohole werden als Emulgatoren eingesetzt.',
        'CL_EN': 'Fatty acid esters can be used as lubricants.'}
    } 


cramer_group_classification = {
        'Alkylbenzoate': 'I',
        'Alkylsalicylate': 'I',
        'Alkylbenzole': 'II'
    }


cramer_TTC_mapping = {
    'I': {'Long_Name':'Low (Class I)', 'TTC':1.8},
    'II': {'Long_Name':'Intermediate (Class II)', 'TTC':0.54},
    'III': {'Long_Name':'High (Class III)', 'TTC':0.09},
    }

cur_ft_dict = {
    "Table 1" : "d",
    "Table 3": "g"
}