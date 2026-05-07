import os
import subprocess
import shutil
import sys

spath = r'C:\path\to\images' # Location of images to be watermarked
bat_source = r"C:\path\to\move_originals_batch.bat" # batch file location

for dirpath, dirs, files in os.walk(spath):
    # print(dirpath, dirs, files)
    if len(files) == 0: 
        continue
    if 'originals' in dirs:
        subprocess.call(bat_source, cwd=dirpath)