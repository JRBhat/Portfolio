import tempfile
import os
import shelve
import skimage
import shutil
import sys
import numpy as np
from skimage.transform import resize as skresize

from . import IMAGEANALYSIS_LOGGER
from . import Util, ColorConversion
from .ImageIO import readImage, rgb_to_gray_image, writeImage


def __svndata__():
    """
    | $Author: ndrews $
    | $Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $
    | $Rev: 13366 $
    | $URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ImageClasses.py $
    | $Id: ImageClasses.py 13366 2022-08-05 13:06:26Z ndrews $
    """
    # only for documentation purpose
    return {
        'author': "$Author: ndrews $".replace('$', '').replace('Author:', '').strip(),
        'date': "$Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $".replace('$', '').replace('Date:', '').strip(),
        'rev': "$Rev: 13366 $".replace('$', '').replace('Rev:', '').strip(),
        'id': "$Id: ImageClasses.py 13366 2022-08-05 13:06:26Z ndrews $".replace('$', '').replace('Id:', '').strip(),
        'url': "$URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/ImageClasses.py $".replace('$', '').replace('URL:', '').strip()
    }


class ImageClass(object):
    """ Basic Image class
    :param filename: image filename (existing or will be created as 8bit-srgb)
    :type filename: str
    :param from_lab: CIELAB input
    :type from_lab: numpy array(None)
    :param from_srgb_norm: normed srgb input (no gamma, float)
    :type from_srgb_norm: numpy array(None)
    """
    keep_data = True
    """ :param keep_data: if true keep data in memory, if false keeps data in shelve stored on disk, if None calculates data everytime new
        :type keep_data: bool"""

    def __init__(self, filename, from_lab=None, from_srgb_norm=None, from_hsv=None):
        self._filename = filename
        self._image_type = None
        self.has_data = False
        # keep_data_dict to store converted images
        if ImageClass.keep_data:
            self.keep_data_dict = {}
        # if not keep data create persistent temporary database to store imagedata
        elif not ImageClass.keep_data is None:
            # if file name build shelve path in temp dir
            if filename:
                image_name = os.path.basename(filename).split(".")[0]
                # default file path is temp file, each file need own directory because many files  are created per shelve
                self.shelve_file = os.path.normpath(os.path.join(
                    os.path.dirname(self.filename), f"ImageClassShelve {image_name}", f"{image_name}_tmp.dat"))
            # if file name build shelve path in dir of file
            else:
                image_name = str(self)
                # default file path is temp file, each file need own directory because many files  are created per shelve
                self.shelve_file = os.path.normpath(os.path.join(
                    tempfile.gettempdir(), f"ImageClassShelve {image_name}", f"{image_name}_tmp.dat"))
            os.makedirs(os.path.dirname(self.shelve_file), exist_ok=True)
            self.keep_data_dict = shelve.open(self.shelve_file, flag='n')
        # convert lab to srgb image
        if from_lab is not None:
            if filename is None:
                raise ValueError("Need filename to perform from_lab")
            if not self.keep_data is None:
                # create rgb image
                self.keep_data_dict["lab"] = from_lab
            imd = (ColorConversion.lab_to_srgb(from_lab).clip(
                0, 1) * (2 ** 16 - 1)).astype(np.uint16)
            writeImage(imd, self._filename)
        # convert hsv to srgb image
        if from_hsv is not None:
            if filename is None:
                raise ValueError("Need filename to perform from_hsv")
            if not self.keep_data is None:
                # save in keep data
                self.keep_data_dict["hsv"] = from_hsv
            imd = (ColorConversion.hsv_to_sRGB(from_hsv)
                   * (2 ** 16 - 1)).astype(np.uint16)
            writeImage(imd, self._filename)
        # convert norm srgb to srgb image
        if from_srgb_norm is not None:
            if filename is None:
                raise ValueError("Need filename to perform from_srgb_norm")
            if not self.keep_data is None:
                # save in keep data
                self.keep_data_dict["srgb_norm"] = from_srgb_norm
            imd = ((ColorConversion.sRGB_add_gamma(from_srgb_norm).clip(
                0, 1)) * (2 ** 16 - 1)).astype(np.uint16)
            writeImage(imd, self._filename)
        # check if image is a file in the given dir
        if filename is not None and not os.path.isfile(filename):
            raise FileNotFoundError("Could not find image for: " + filename)

    def write_image_srgb24(self, filename: str) -> None:
        """writes image as srgb24

        :param filename: where to save image
        :type filename: str
        """
        writeImage(self.srgb24, filename)

    @property
    def filename(self):
        """ filename """
        return self._filename

    @filename.setter
    def filename(self, filename):
        if self._filename != filename:
            self.clear_memory()
            self._filename = filename

    def _get_pillow_image_mode(self):
        """gets the pillow mode, L for greyscale images, RGB via colordepth of image

        :return: return pillow mode defined by colordepth of np_data (self.shape[2])
        :rtype: str
        """
        try:
            colordepth = self.shape[2]
        except IndexError:
            colordepth = 1
        return {1: "L", 3: "RGB", 4: "RGBA"}[colordepth]

    def clear_memory(self):
        self.keep_data_dict.clear()
        self.has_data = False

    @property
    def np_data(self):
        """np array of image as 0-1

        :return: np data as 0-1
        :rtype: ndarray
        """
        try:
            return self.keep_data_dict["np_data"]
        except KeyError:
            if self.filename is None:
                raise ValueError(
                    "Cant't create np_data without filename, please set np_image data manual when using an ImageClass without filename")
            IMAGEANALYSIS_LOGGER.info("Really Read %s" % self.filename)
            np_data = ColorConversion.convert_0_to_1(readImage(self.filename))
            self.has_data = True
            if not self.keep_data is None:
                self.keep_data_dict["np_data"] = np_data
            return np_data

    @np_data.setter
    def np_data(self, data):
        """returns np_data

        :param data: iterable with image informations (numpy array, colorspace name, colordepth)
        :type data: iterable
        :raises ValueError: if passed data has wrong format
        """
        try:
            np_data = data[0]
            # set new np data if flux use raw image data
            if data[1] != "flux":
                np_data = ColorConversion.convert_0_to_1(data[0])
            if not self.keep_data is None:
                # reset keep data dict; must be calculated new after setting new np_data
                self.keep_data_dict.clear()
            # store data if keep data or if filename is None
            if not self.keep_data is None or self.filename is None:
                #  when np data is newly set should not read images on conversion
                self.keep_data_dict["np_data"] = np_data
                self.has_data = True
            # set new imagetype
            self.image_type = (data[1], self._get_pillow_image_mode(), data[2])
        except (ValueError, IndexError) as e:
            raise ValueError(
                "Please pass iterable with (np_data, colorspace, Bitrate) when setting np_data Exception: " + str(e))

    @property
    # @numpy_testing_almost_equal()
    def rgb48bpp(self):
        try:
            return self.keep_data_dict["rgb48bpp"]
        except KeyError:
            if ColorConversion.mode_to_bpp(self.free_image.mode) == 48:
                rgb48bpp = self.np_data
            if ColorConversion.mode_to_bpp(self.free_image.mode) == (8 * 3):
                rgb48bpp = ColorConversion.convert_0_to_255(
                    self.np_data, "uint16")
            else:
                rgb48bpp = ColorConversion.convert_0_to_1(
                    self.np_data, "uint16") * 255
            if not self.keep_data is None:
                self.keep_data_dict["rgb48bpp"] = rgb48bpp
            return rgb48bpp

    @rgb48bpp.setter
    def rgb48bpp(self, *args, **kwargs):
        raise AttributeError

    @property
    # @numpy_testing_almost_equal()
    def rgb24bpp(self):
        # check if converted image is already in memory
        try:
            return self.keep_data_dict["rgb24bpp"]
        except KeyError:
            if self.colordepth == 48:
                rgb24bpp = Util.convert_uint16_to_uint8(self.np_data)
            if self.colordepth == (8 * 3):
                rgb24bpp = self.np_data
            else:
                rgb24bpp = ColorConversion.convert_0_to_1(
                    self.np_data).astype(np.uint16) * 255
            if not self.keep_data is None:
                self.keep_data_dict["rgb24bpp"] = rgb24bpp
            return rgb24bpp

    @rgb24bpp.setter
    def rgb24bpp(self, *args, **kwargs):
        raise AttributeError

    @property
    def adobe(self):
        try:
            return self.keep_data_dict["adobe"]
        except KeyError:
            adobe_img = self._check_and_convert_greyscale_to_rgb()
            # if colorspace is srgb convert to adobe and scale up
            if self.colorspace_name == 'srgb':
                adobe_img = ColorConversion.convert_0_to_255(
                    ColorConversion.sRGB_to_adobe(adobe_img).clip(0, 1))
            # else if adobe just scale up
            elif self.colorspace_name == 'adobe':
                adobe_img = ColorConversion.convert_0_to_255(adobe_img)
            if not self.keep_data is None:
                # save converted image in memory
                self.keep_data_dict["adobe"] = adobe_img
            return adobe_img

    @adobe.setter
    def adobe(self, *args, **kwargs):
        raise AttributeError

    @property
    # @numpy_testing_almost_equal()
    def srgb24(self):
        # check if image is stored in memory
        try:
            return self.keep_data_dict["srgb24"]
        except KeyError:
            srgb24_img = self._check_and_convert_greyscale_to_rgb()
            # if image is adobe convert to srgb and scale up
            if self.colorspace_name == 'adobe':
                srgb24_img = ColorConversion.convert_0_to_255(ColorConversion.adobe_to_sRGB(
                    srgb24_img).clip(0, 1))
            # if image is alread srgb just scale up
            elif self.colorspace_name == 'srgb':
                srgb24_img = ColorConversion.convert_0_to_255(
                    srgb24_img, "uint8")
            else:
                raise ValueError(
                    "Colorspace " + self.colorspace_name + " is not supported")
            if not self.keep_data is None:
                self.keep_data_dict["srgb24"] = srgb24_img
            return srgb24_img

    @srgb24.setter
    def srgb24(self, *args, **kwargs):
        raise AttributeError

    @property
    def greyscale(self):
        if len(self.np_data.shape) == 2:
            return self.np_data
        return rgb_to_gray_image(self.np_data)

    @greyscale.setter
    def greyscale(self, *args, **kwargs):
        raise AttributeError

    @property
    # @numpy_testing_almost_equal()
    def srgb_norm(self):
        return self.__run_conversion("srgb_norm", ColorConversion.adobe_to_norm_sRGB, ColorConversion.sRGB_to_norm_sRGB).clip(0, 1)

    @srgb_norm.setter
    def srgb_norm(self, *args, **kwargs):
        raise AttributeError

    @property
    def lab(self):
        return self.__run_conversion("lab", ColorConversion.adobe_to_lab, ColorConversion.sRGB_to_lab)

    @lab.setter
    def lab(self, *args, **kwargs):
        raise AttributeError

    @property
    def hsv(self):
        return self.__run_conversion("hsv", ColorConversion.adobe_to_hsv, ColorConversion.sRGB_to_hsv)

    @hsv.setter
    def hsv(self, *args, **kwargs):
        raise AttributeError

    @property
    def xyz(self):
        return self.__run_conversion("xyz", ColorConversion.adobe_to_xyz, ColorConversion.sRGB_to_xyz)

    @xyz.setter
    def xyz(self, *args, **kwargs):
        raise AttributeError

    def __run_conversion(self, colorspace_name, adobe_conversion_func, sRGB_conversion_func):
        """runs the given algorithmen, before checks if already data exists for the colorspace; if the current image
           is in adobe runs adobe algorithmen, else srgb algorithm

        :param colorspace_name: name of the colorspace to convert into (only used for loadin/storing data)
        :type colorspace_name: str
        :param adobe_conversion_func: function to run if image is in adobe colorspace
        :type adobe_conversion_func: function
        :param sRGB_conversion_func: function to run if image is in sRGB colorspace
        :type sRGB_conversion_func: function
        :param clip_values: if values should be clipped to 0-1
        :return: returns converted image in the colorspace, or exits if sys -1 if no matching algorithm were found
        :rtype: ndarray
        """
        # check if converted image is already in memory
        try:
            return self.keep_data_dict[colorspace_name]
        except KeyError:
            # check if greyscale
            np_image = self._check_and_convert_greyscale_to_rgb()
            IMAGEANALYSIS_LOGGER.debug(
                f"Colorspace name: {self.colorspace_name}")
            # if colorspace is adobe 1998 run adobe algorithm
            if self.colorspace_name == 'adobe':
                IMAGEANALYSIS_LOGGER.debug(
                    f"Running: {adobe_conversion_func.__name__} conversion")
                img = adobe_conversion_func(np_image)
            # if colorspace is sRGB run sRGB algorithm
            elif self.colorspace_name == 'srgb':
                IMAGEANALYSIS_LOGGER.debug(
                    f"Running: {sRGB_conversion_func.__name__} conversion")
                img = sRGB_conversion_func(np_image)
            # if no matching colorspace was found, exit programm
            else:
                IMAGEANALYSIS_LOGGER.error(
                    self.colorspace_name + " not supported")
                sys.exit(-1)
            if not self.keep_data is None:
                # save converted image
                self.keep_data_dict[colorspace_name] = img
            return img

    def _check_and_convert_greyscale_to_rgb(self):
        """checks if the image is greyscale and if so converts it to rgb

        :return: image in rgb 0-1
        :rtype: ndarray
        """
        is_grey_image = len(self.shape) == 2
        # convert greyscale
        if is_grey_image:
            IMAGEANALYSIS_LOGGER.warning("Converting greyscale to rgb")
        # if image is greyscale return converted image else np_data
        return ColorConversion.greyscale_to_rgb(self.np_data) if is_grey_image else self.np_data

    @property
    def shape(self):
        return self.np_data.shape

    @shape.setter
    def shape(self, *args, **kwargs):
        raise AttributeError

    @property
    def image_type(self):
        if self._image_type is None:
            if self.filename is None:
                raise ValueError(
                    "Can't define image_type without filename, please set it before using it, must be one of [srgb, adobe, hasselrgb]")
            self._image_type = ColorConversion.get_colorprofile(self.filename)
        return self._image_type

    @image_type.setter
    def image_type(self, image_type):
        # check if right amount of parameters
        if not len(image_type) == 3:
            raise ValueError(
                "Image type must be iterable with (colorspace, pillow mode, colorbits) ")
        # check if right colorspace
        if not image_type[0] in ["srgb", "adobe", "hasselrgb", "flux"]:
            raise ValueError(
                "Image type colorspace must be one of tuple [srgb, adobe, hasselrgb, mmf]")
        self._image_type = image_type

    @property
    def colorspace_name(self):
        return self.image_type[0]

    @colorspace_name.setter
    def colorspace_name(self, *args, **kwargs):
        raise AttributeError

    @property
    def colorspace_type(self):
        return self.image_type[1]

    @colorspace_type.setter
    def colorspace_type(self, *args, **kwargs):
        raise AttributeError

    @property
    def colordepth(self):
        return self.image_type[2]

    @colordepth.setter
    def colordepth(self, *args, **kwargs):
        raise AttributeError

    @property
    def np_dtype(self):
        return self.np_data.dtype

    @np_dtype.setter
    def np_dtype(self, *args, **kwargs):
        raise AttributeError

    def __del__(self):
        """deletes files created by shelve if there are any
        """
        # remove shelve files if shelve were created
        try:
            # close shelve
            self.keep_data_dict.close()
            shelve_dir = os.path.dirname(self.shelve_file)
            IMAGEANALYSIS_LOGGER.debug(
                f"Removing shelve files in {shelve_dir}")
            # remove shelve files
            shutil.rmtree(shelve_dir)
        except AttributeError:
            pass

    def __str__(self):
        if self.filename:
            return f"ImageClass {os.path.basename(self.filename).split('.')[0]}"
        else:
            return f"Temp ImageClass {self.__hash__()}"


class ImagePyramideClass(list):
    keep_data = True
    save_data = False
    temp_directory = "C:\\Experimente\\Image_Class_Pyramide_TEMP"
    do_upscale = False

    def __init__(self, filename, depth=-1):
        Util.createDirectory(self.temp_directory)
        self._filename = filename
        ImageClass.keep_data = self.keep_data
        ImageClass.save_data = self.save_data
        ImageClass.temp_directory = self.temp_directory
        image_class_pyramide = [ImageClass(filename)]
        self._save_base_name = Util.create_filename_from_basefile(
            self._filename, file_ext="", directory=self.temp_directory)
        self._max_depth = np.floor(np.log2(image_class_pyramide[0].shape[:2]))
        if depth > 0:
            self._pyramide_depth = int(min(depth, self._max_depth.min()))
        else:
            self._pyramide_depth = int(self._max_depth.min())
        if self.do_upscale:
            image_class_pyramide.extend([ImageClass(
                self._save_base_name + "_pyramide_upscale_%d.png" % rg) for rg in range(1, self._pyramide_depth)])
        else:
            image_class_pyramide.extend([ImageClass(
                self._save_base_name + "_pyramide_%d.png" % rg) for rg in range(1, self._pyramide_depth)])
        missing_files_idx = -1
        try:
            missing_files_idx = [os.path.exists(
                x.filename) for x in image_class_pyramide].index(False)
        except ValueError:
            pass
        if missing_files_idx > -1:
            im = image_class_pyramide[missing_files_idx - 1].np_data
            for x in image_class_pyramide[missing_files_idx:]:
                # need to convert so that there is no difference between saved<>created data
                im = skimage.transform.pyramid_reduce(im)
                if self.do_upscale:
                    im = skresize(
                        im, image_class_pyramide[0].shape[:2], order=1)
                im = np.round(im * ((2 ** 8) - 1)).astype(np.uint8)
                writeImage(im, x.filename)
        super(ImagePyramideClass, self).__init__(image_class_pyramide)

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, *args, **kwargs):
        raise AttributeError

    @property
    def shape(self):
        return self[0].shape

    @shape.setter
    def shape(self, *args, **kwargs):
        raise AttributeError

    @property
    def image_type(self):
        return self[0].image_type

    @image_type.setter
    def image_type(self, *args, **kwargs):
        raise AttributeError

    @property
    def colorspace_name(self):
        return self[0].colorspace_name

    @colorspace_name.setter
    def colorspace_name(self, *args, **kwargs):
        raise AttributeError

    @property
    def colorspace_type(self):
        return self[0].colorspace_type

    @colorspace_type.setter
    def colorspace_type(self, *args, **kwargs):
        raise AttributeError

    @property
    def colordepth(self):
        return self[0].colordepth

    @colordepth.setter
    def colordepth(self, *args, **kwargs):
        raise AttributeError


def _write_data_imageclasses(data, filename):
    """writes data to file

    :param data: data to write
    :type data: dtyape
    :param filename: location of the file
    :type filename: string
    """
    try:
        Util.writeData(data, filename)
    except Exception as inst:
        IMAGEANALYSIS_LOGGER.error("Could not marshale File '%s', Exception: %s" %
                                   (filename, inst))  # log error
        raise
