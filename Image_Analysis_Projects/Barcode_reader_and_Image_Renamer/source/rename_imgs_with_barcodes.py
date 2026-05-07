"""
This script processes image files in a specified directory by reading barcodes from the files,
renaming them based on the detected barcodes, and moving them to an output directory.
It uses the `read_barcode` module for barcode detection.

Dependencies:
- `barcode_reader_simple_refactored.read_barcode`: A module used to read barcodes from image files.
- `shutil` and `os`: Python standard libraries for file operations.

Functions:
- main(): The main entry point of the script.

Workflow:
1. Define paths for the input directory (`INPUT_DIR`) and output directory (`OUTPUT_DIR`).
2. Create the output directory if it does not exist.
3. Gather all `.JPG` files from the input directory.
4. Process each image:
   - Use `read_barcode` to detect a barcode in the image.
   - If a barcode is detected:
       - Rename the `.JPG` and its associated `.CR2` file using the barcode as a prefix.
       - Store the mapping of barcodes to new filenames in a dictionary.
   - If no barcode is detected:
       - Use the last detected barcode as a prefix for renaming.
5. Move the renamed files to the output directory.

File Naming and Moving:
- Files are renamed with the barcode as a prefix.
- Associated `.CR2` files are renamed alongside their corresponding `.JPG` files.
- Renamed files are moved to the `OUTPUT_DIR` directory.

Notes:
- The script assumes that for each `.JPG` file, a corresponding `.CR2` file exists in the same directory.
- The script processes images sequentially, maintaining order.
"""


from source.barcode_reader_simple_refactored import read_barcode

import shutil
import os


def _rename_pair(jpg_path: str, prefix: str, target_dir: str) -> str:
    """Rename the .JPG and its paired .CR2 by prepending *prefix*. Returns the new JPG path."""
    new_jpg = os.path.join(target_dir, prefix + os.path.basename(jpg_path))
    os.rename(jpg_path, new_jpg)
    os.rename(jpg_path.replace(".JPG", ".CR2"), new_jpg.replace(".JPG", ".CR2"))
    return new_jpg


def _move_pair(jpg_path: str, src_dir: str, dst_dir: str) -> None:
    """Move the .JPG and its paired .CR2 from *src_dir* to *dst_dir*."""
    shutil.move(jpg_path, jpg_path.replace(src_dir, dst_dir))
    shutil.move(jpg_path.replace("JPG", "CR2"), jpg_path.replace("JPG", "CR2").replace(src_dir, dst_dir))


def main() -> None:
    """
    Walk INPUT_DIR, decode the barcode in each .JPG, and rename the .JPG plus
    its paired .CR2 with the barcode as a filename prefix. Images without a
    detectable barcode inherit the most-recent successful barcode (carry-forward).
    Successfully renamed pairs are then moved to OUTPUT_DIR.
    """
    # Paths for the input directory and output directory
    INPUT_DIR = "data/images/"
    OUTPUT_DIR = "data/images/out"

    # Ensure the output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    if not os.path.isdir(INPUT_DIR):
        raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")

    # List to hold the paths of all JPG files in the input directory
    jpg_paths = []
    for fn in os.listdir(INPUT_DIR):
        if fn.upper().endswith(".JPG"):
            jpg_paths.append(os.path.join(INPUT_DIR, fn))

    # Dictionary to map barcodes to file paths and a list to track barcodes
    barcode_dict = {}
    barcode_list = []

    # Process each JPG file
    for jpg_path in sorted(jpg_paths):
        # Read the barcode from the image file
        barcode = read_barcode(jpg_path)
        if barcode is not None:
            # Clean the barcode value for use in filenames
            clean_barcode = barcode.decode("utf-8") if isinstance(barcode, bytes) else str(barcode)

            # Generate a new filename using the barcode
            new_fn = _rename_pair(jpg_path, clean_barcode, INPUT_DIR)
            print(f"Barcode detected \n\n {jpg_path} renamed to \n {new_fn}")

            # Update the barcode dictionary and list
            barcode_dict[clean_barcode] = new_fn
            barcode_list.append(clean_barcode)
        else:
            # Carry-forward rule: when a frame has no barcode, reuse the last decoded one.
            # This assumes each barcode labels a *series* of consecutive photos.
            # Handle case where no barcode is detected
            # Use the last detected barcode for naming
            new_fn = _rename_pair(jpg_path, barcode_list[-1], INPUT_DIR)
            print(f"Continuing with barcode {barcode_list[-1]} \n\n {jpg_path} renamed to \n {new_fn}")

    # Move processed files to the output directory
    for renamed_jpg_path in barcode_dict.values():
        src = renamed_jpg_path.replace(".JPG", ".CR2")
        dst = renamed_jpg_path.replace(".JPG", ".CR2").replace(INPUT_DIR, OUTPUT_DIR)
        print(f"moving {src} to \n {dst}")

        _move_pair(renamed_jpg_path, INPUT_DIR, OUTPUT_DIR)

if __name__ == "__main__":
    main()
