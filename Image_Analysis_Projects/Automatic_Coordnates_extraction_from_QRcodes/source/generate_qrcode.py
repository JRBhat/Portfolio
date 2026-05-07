"""Thin convenience wrappers around the ``qrcode`` library.

Provides :func:`make_quick_qrcode` for simple default-style codes and
:func:`make_custom_qrcode` for fully parameterised codes with custom colours
and module sizes.
"""

import qrcode
import os
import logging

def make_quick_qrcode(text: str, path_to_save: str) -> None:
    """Render *text* as a default-style QR code and save to *path_to_save*.

    Overwrites any existing file at the destination.

    :param text: The string to encode in the QR code.
    :param path_to_save: Absolute or relative path where the image will be saved.
    """
    img = qrcode.make(text)
    img.save(path_to_save) # overwrites existing image1.png
    logging.info("QR code generated for %r at %s", text, path_to_save)
    # input("Press enter to continue...")

def make_custom_qrcode(text, path_to_save, box_size=8, border=4, fill_color="darkgreen",  back_color="#ffffff"):
    """Render *text* as a customised QR code and save inside *path_to_save*.

    The output file is named ``qrcode_test_custom{fill_color}.png`` and is
    written inside the directory *path_to_save*.

    :param text: The string to encode.
    :param path_to_save: Directory where the output image will be written.
    :param box_size: Size of each QR module in pixels (default 8).
    :param border: Width of the quiet-zone border in modules (default 4).
    :param fill_color: Foreground colour string accepted by Pillow (default
        ``"darkgreen"``).
    :param back_color: Background colour string accepted by Pillow (default
        ``"#ffffff"``).
    """
    qr = qrcode.QRCode(
        version=12,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border
    )

    qr.add_data(text)
    qr.make()
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    img.save(os.path.join(path_to_save, f"qrcode_test_custom{fill_color}.png"))


def main():

    PATH_TO_SAVE = "output/pos_qrcodes/pos3.png"
    TEXT = """Pos 3"""

    make_quick_qrcode(TEXT, PATH_TO_SAVE)
    # make_custom_qrcode(TEXT, PATH_TO_SAVE, fill_color="darkred")


if __name__ == '__main__':
    main()
