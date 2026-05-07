"""
Running this code recursively walks through directory, and watermarks images of various extention types and stores it into a separate folder
"""
import os
import subprocess
import shutil
import time

PATH = r"C:\path\to\watermarking_test\sample_images"
BAT_SOURCE = r"C:\path\to\watermark_batch.bat"


def main():
    bat_placed = False
    detected = []
    shortcuts = []

    # checks all file extensions and corrects it to right format
    for dirpath, dirname, files in os.walk(PATH):
        if files:
            for file in files:
                if file.endswith('.JPG') or file.endswith('.JPEG') or file.endswith('.jpeg'):
                    base = os.path.splitext(file)[0]
                    os.rename(os.path.join(dirpath, file), os.path.join(dirpath, base + '.jpg'))
                    detected.append(os.path.join(dirpath, file))

                elif file.endswith('.TIF') or file.endswith('.TIFF') or file.endswith('.tiff'):
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
    last_dirpathname = ""

    # Recursively iterates over each directory and sub-directories and watermarks images
    time_start = time.perf_counter()
    for dirpath, dirname, files in os.walk(PATH):
        if files:
            if "_watermarked" in dirpath or "_watermarked" in dirname:
                print(f"Skipped path: {dirpath}")
                continue
            else:
                for file in files:
                    if file.endswith(('.jpg', '.png', '.tif', '.tiff')) and not bat_placed:
                        shutil.copy(BAT_SOURCE, dirpath)
                        cmdline = os.path.join(dirpath, 'watermark_batch.bat')
                        subprocess.call(cmdline, cwd=dirpath)
                        previous_dir = dirpath
                        last_dirpathname = dirpath
                        bat_placed = True
                        break

                    elif file.endswith(('.jpg', '.png', '.tif', '.tiff')) and bat_placed:
                        shutil.move(os.path.join(previous_dir, 'watermark_batch.bat'), dirpath)
                        cmdline1 = os.path.join(dirpath, 'watermark_batch.bat')
                        subprocess.call(cmdline1, cwd=dirpath)
                        previous_dir = dirpath
                        last_dirpathname = dirpath
                        break

    if os.path.exists(os.path.join(last_dirpathname, "watermark_batch.bat")):
        os.remove(os.path.join(last_dirpathname, "watermark_batch.bat"))
    else:
        print("The file does not exist")
    time_stop = time.perf_counter()
    in_minutes = (time_stop - time_start) / 60
    in_hours = in_minutes / 60
    if in_minutes >= 60:
        print(f"Total time: {in_hours:.2f} hours")
    else:
        print(f"Total time: {in_minutes:.2f} minutes")


if __name__ == "__main__":
    main()
