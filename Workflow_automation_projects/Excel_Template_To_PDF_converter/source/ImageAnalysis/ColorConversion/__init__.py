# $Id: __init__.py 13239 2022-04-19 12:21:11Z ndrews $
"""
Color Conversion definitions and functions, intern works with image values from 0-1 and also returns images in 0-1
"""
import logging
import sys

COLORCONVERSION_LOGGER = logging.getLogger("colorconversion_logger")
COLORCONVERSION_LOGGER.setLevel(logging.DEBUG)
# create logging format
logging_formatter = logging.Formatter(
    fmt="%(levelname)s %(asctime)s:%(name)s:%(module)s:%(funcName)s: %(message)s", datefmt='%H:%M:%S')
# create logger for console
logging_console_handler = logging.StreamHandler(sys.stdout)
logging_console_handler.setFormatter(logging_formatter)
logging_console_handler.setLevel(logging.DEBUG)
COLORCONVERSION_LOGGER.addHandler(logging_console_handler)

from .adobe_conversions import *
from .sRGB_conversions import *
from .XYZ_conversions import *
from .lab_conversions import *
from .hsv_conversions import *
from .helper_functions import *
from .greyscale_conversions import *

__version__ = "$Revision: 13239 $"


def __svndata__():
    """
    | $Author: ndrews $
    | $Date: 2022-04-19 14:21:11 +0200 (Di., 19. Apr 2022) $
    | $Rev: 13239 $
    | $URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ColorConversion/__init__.py $
    | $Id: __init__.py 13239 2022-04-19 12:21:11Z ndrews $
    """
    # only for documentation purpose
    return {
        'author': "$Author: ndrews $".replace('$', '').replace('Author:', '').strip(),
        'date': "$Date: 2022-04-19 14:21:11 +0200 (Di., 19. Apr 2022) $".replace('$', '').replace('Date:', '').strip(),
        'rev': "$Rev: 13239 $".replace('$', '').replace('Rev:', '').strip(),
        'id': "$Id: __init__.py 13239 2022-04-19 12:21:11Z ndrews $".replace('$', '').replace('Id:', '').strip(),
        'url': "$URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ColorConversion/__init__.py $".replace('$', '').replace('URL:', '').strip()
    }
