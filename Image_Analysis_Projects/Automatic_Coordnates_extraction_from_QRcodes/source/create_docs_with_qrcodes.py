"""Document generation helpers for QR-code-labelled study booklets.

Reads a Word document template (stored as a zipped ``document.xml``), updates
subject-number placeholders, embeds a fresh QR-code image, re-archives the
folder as a ``.zip``, and renames the result to ``.docx``.
"""
# ASSUMPTION: document.xml exists already from the user generated docx file zipped

# open document.xml, loop through each line, if "1 t0" and "2 t0" are found, then replace "1 t0" with f"{i} t0" and "2 t0" with f"{i+1} t0"

# save the xml

# generate barcode with text = Proband {i} and save image and "image1.png"(replacement) in the media subfolder of zipped docx

# zip contents and save as Prob{i}-{i+1}.zip

# change extension from zip to docx


import xml.etree.ElementTree as ET
from generate_qrcode import make_quick_qrcode
import subprocess
import os
import shutil
import logging

def update_document_xml(path_to_xml, n):
    """Update subject-number placeholders in *document.xml* for iteration *n*.

    Rewrites the two header text nodes in-place so that they read
    ``"Proband {n} t0"`` and ``"Proband {n+1} t0"`` respectively.

    :param path_to_xml: Absolute path to the ``document.xml`` file.
    :param n: Current subject-pair index (1-based, increments by 2).
    """
    # reference document.xml - do not change
    tree = ET.parse(path_to_xml)
    root = tree.getroot()
    if n > 1:
        root[0][0][2][2][1][0][0].text = str(f"Proband {n} t0")
        root[0][0][7][2][1][0][0].text = str(f"Proband {n+1} t0")

    tree.write(path_to_xml)
    logging.info(f"document.xml updated with Proband {n} and Proband {n+1}")
    # input("Press enter to continue...")


def zip_contents(path_to_zip, n):
    """Archive the template folder as ``test_doc_prob{n}and{n+1}.zip``.

    :param path_to_zip: Directory whose contents will be archived.
    :param n: Current subject-pair index.
    """
    proc = subprocess.Popen(f"d: && cd {path_to_zip} && zip -r test_doc_prob{n}and{n+1}.zip *", shell=True)
    proc.wait()
    logging.info(f"contents of  {path_to_zip} archived successfully")
    # input("Press enter to continue...")

def main():
    """Generate one ``.docx`` booklet per subject pair.

    Iterates subject indices 1, 3, 5, … updating the XML template, embedding a
    fresh QR-code image, zipping, renaming to ``.docx``, and moving the result
    to *output_path*.
    """
    output_path = "output/results"
    path_to_docxml = "data/templates/word/document.xml"
    path_to_qrcode_img = "data/templates/word/media/image1.png"
    folderpath_to_zip = "data/templates"

    os.makedirs(output_path, exist_ok=True)

    i = 1
    while i < 56:

        # change the text in the xml file
        if i > 1:
            update_document_xml(path_to_docxml, i)

        # replace qrcode image with new one
        make_quick_qrcode("Pos 1", path_to_qrcode_img)

        # zip contents
        zip_contents(folderpath_to_zip, i)

        # change extension and move file to output folder
        if f"test_doc_prob{i}and{i+1}.zip" in os.listdir(folderpath_to_zip):
            path_with_oldname = os.path.join(folderpath_to_zip, f"test_doc_prob{i}and{i+1}.zip")
            path_with_newname = path_with_oldname.replace(".zip", ".docx")
            os.rename(path_with_oldname, path_with_newname)
            final_path = os.path.join(output_path, os.path.basename(path_with_newname))
            shutil.move(path_with_newname, final_path)
            logging.info("docx successfully moved to output folder")

        i += 2

if __name__ == "__main__":
    main()
