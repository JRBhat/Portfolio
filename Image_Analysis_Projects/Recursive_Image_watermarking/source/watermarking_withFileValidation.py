import os
import subprocess
import shutil
import sys

path = r'C:\path\to\images' # Location of images to be watermarked
bat_source = r"C:\path\to\watermark_batch.bat" # batch file location

count = 0
detected = []
shortcuts = []

old_dir_name = os.path.basename(path)
new_dir_name_for_orignals = old_dir_name + '_original_images_Before_Watermark'
os.mkdir(path.replace(old_dir_name, new_dir_name_for_orignals))

# checks all file extensions and corrects it to right format
for dirpath, dirname, files in os.walk(path):
    if len(files) != 0: 
        for file in files:
            if file.endswith('.JPG') or file.endswith('.JPEG') or file.endswith('.jpeg'):
                base = os.path.splitext(file)[0]              
                os.rename(os.path.join(dirpath, file), os.path.join(dirpath, base + '.jpg'))
                detected.append(os.path.join(dirpath, file))

            elif file.endswith('.TIF') or file.endswith('.TIFF') or file.endswith('tiff'):
                base = os.path.splitext(file)[0]
                os.rename(os.path.join(dirpath, file), os.path.join(dirpath, base + '.tif'))
                detected.append(os.path.join(dirpath, file))

            elif file.endswith('.PNG'):
                base = os.path.splitext(file)[0]
                os.rename(os.path.join(dirpath, file), os.path.join(dirpath, base + '.png'))
                detected.append(os.path.join(dirpath, file))
                
            elif file.endswith('.lnk'):
                shortcuts.append(os.path.join(dirpath, file))
print(detected)
print(shortcuts)


for dirpath, dirname, files in os.walk(path):
    if len(files) != 0: 
        for file in files:
            if ('.jpg'in file or '.png' in file or 'tif'in file) and count == 0:
                shutil.copy(bat_source, dirpath)
                # shutil.copy(img_source, dirpath)
                cmdline = os.path.join(dirpath,'watermark_batch.bat')
                subprocess.call(cmdline, cwd=dirpath)
                temp_path = dirpath 
                count = 1
                break

            elif ('.jpg'in file or '.png'in file or 'tif'in file)  and count == 1:
                
                shutil.move(os.path.join(temp_path,'watermark_batch.bat'), dirpath)
                # shutil.copy(img_source, dirpath)
                cmdline1 = os.path.join(dirpath,'watermark_batch.bat')
                subprocess.call(cmdline1, cwd=dirpath)
                temp_path = dirpath
                break 

    # Moves the originals folder to a specified location(in this case, it is into a folder next to the source)
    if 'originals' in os.listdir(dirpath):
        strpath = os.path.join(dirpath, 'originals')
        shutil.move(os.path.join(dirpath, 'originals'), strpath.replace(old_dir_name, new_dir_name_for_orignals))                
