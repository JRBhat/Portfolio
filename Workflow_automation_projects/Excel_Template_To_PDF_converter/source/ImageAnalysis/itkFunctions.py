from past.utils import old_div
import itk
import numpy as np

def resampleImage(ImageType, fixedFile, movingFile, compositeTransform, registerFile, resizeFactor=1, InterpolatorType=None):
    """creates a transformed image with itk

    :param ImageType: type of image
    :type ImageType: str
    :param fixedFile: target image
    :type fixedFile: str
    :param movingFile: source image
    :type movingFile: str
    :param compositeTransform: transformation between images
    :type compositeTransform: itk.transformation 
    :param registerFile: outfile as str
    :type registerFile: str
    :param resizeFactor: resize factor, defaults to 1
    :type resizeFactor: int, optional
    :param InterpolatorType: interpolation type, defaults to None
    :type InterpolatorType: itk.interpolartype, optional
    :return: nothing or ndarray if outfile = none
    :rtype: nothing /ndarray
    """
    if resizeFactor == 0:
        resizeFactor = 1
    ReaderType = itk.ImageFileReader[ImageType]
    WriterType = itk.ImageFileWriter[ImageType]
    ResampleFilterType = itk.ResampleImageFilter[ImageType, ImageType]
    fixed_reader = ReaderType.New()
    fixed_reader.SetFileName(fixedFile)
    fixed_reader.UpdateOutputInformation()
    moving_reader = ReaderType.New()
    moving_reader.SetFileName(movingFile)
    moving_reader.Update()
    movingImage = moving_reader.GetOutput()
    movingImage.DisconnectPipeline()
    movingImage.SetSpacing([1, 1])
    resampler = ResampleFilterType.New()
    if InterpolatorType is not None:
        interpolator = InterpolatorType.New()
        resampler.SetInterpolator(interpolator)
    size = old_div(np.array(fixed_reader.GetOutput(
    ).GetLargestPossibleRegion().GetSize()), resizeFactor)
    resampler.SetSize(size.astype(int).tolist())
    resampler.SetOutputSpacing([resizeFactor, resizeFactor])
    resampler.SetTransform(compositeTransform)
    resampler.SetInput(movingImage)
    resampler.Update()
    if registerFile is not None:
        writer = WriterType.New()
        writer.SetFileName(registerFile)
        writer.SetInput(resampler.GetOutput())
        writer.Update()
    #    LOGGER.info("resampled Image '%s' -> '%s' (fixed: '%s')" %
                 #   (movingFile, registerFile, registerFile))
     ##   LOGGER.info("ImageType: %s" % ImageType)
    else:
        return itk.PyBuffer[ImageType].GetArrayFromImage(resampler.GetOutput())


def moving_variance(input_image, radius=5, np_image_type=np.float32, itk_image_type='itk.Image[itk.F, 2]'):
    """Applies variance filter with itk.

    :param input_image: input image
    :type input_image: ndarray
    :param radius: radius, defaults to 5
    :type radius: int, optional
    :param np_image_type: numpy image type, defaults to np.float32
    :type np_image_type: dtype, optional
    :param itk_image_type: itk image type, defaults to 'itk.Image[itk.F, 2]'
    :type itk_image_type: str, optional
    :return: variance
    :rtype: ndarray
    """
    # Use STD(X) = sqrt(Mean(X**2) - Mean(x)**2)
    __image_itk_type = eval(itk_image_type)
    __image_np_type = np_image_type
    sub_filter = itk.SubtractImageFilter[__image_itk_type,
                                         __image_itk_type, __image_itk_type].New()
    mult_filter = itk.MultiplyImageFilter[__image_itk_type,
                                          __image_itk_type, __image_itk_type].New()
    filter1 = itk.BoxMeanImageFilter[__image_itk_type, __image_itk_type].New()
    filter2 = itk.BoxMeanImageFilter[__image_itk_type, __image_itk_type].New()
    input_image = old_div(input_image.astype(
        __image_np_type), input_image.max())
    itk_image = itk.PyBuffer[__image_itk_type].GetImageFromArray(
        input_image)  # X
    itk_image2 = itk.PyBuffer[__image_itk_type].GetImageFromArray(
        input_image ** 2)  # X^2
    filter1.SetRadius(radius)  # Kernel(structure_element)
    filter2.SetRadius(radius)  # SetKernel(structure_element)
    filter1.SetInput(itk_image2)
    filter1.Update()  # E(X^2)
    filter2.SetInput(itk_image)
    filter2.Update()  # EX
    mult_filter.SetInput(0, filter2.GetOutput())
    mult_filter.SetInput(1, filter2.GetOutput())
    mult_filter.Update()  # (EX)^2
    sub_filter.SetInput(0, filter1.GetOutput())
    sub_filter.SetInput(1, mult_filter.GetOutput())
    sub_filter.Update()
    output_image = np.copy(
        itk.PyBuffer[__image_itk_type].GetArrayFromImage(sub_filter.GetOutput()))
    return output_image

def vesselness_itk(input_image, object_gamma=5, object_alpha=0.5, object_beta=0.5, sigma_min=1.0, sigma_max=20.0, sigma_steps=5, object_dimension=1, scale_objectness_measure=False, bright_object=False, sigma_step_log=False, np_image_type=np.float32, itk_image_type='itk.Image[itk.F, 2]', returnScaleImage=False):
    """Applies vesselness filter with itk for more insights: https://www.insight-journal.org/download/fulldownload/zip/175/8

    :param input_image: image
    :type input_image: image
    :param object_gamma: [description], defaults to 5
    :type object_gamma: int, optional
    :param object_alpha: [description], defaults to 0.5
    :type object_alpha: float, optional
    :param object_beta: [description], defaults to 0.5
    :type object_beta: float, optional
    :param sigma_min: [description], defaults to 1.0
    :type sigma_min: float, optional
    :param sigma_max: [description], defaults to 20.0
    :type sigma_max: float, optional
    :param sigma_steps: [description], defaults to 5
    :type sigma_steps: int, optional
    :param object_dimension: [description], defaults to 1
    :type object_dimension: int, optional
    :param scale_objectness_measure: [description], defaults to False
    :type scale_objectness_measure: bool, optional
    :param bright_object: [description], defaults to False
    :type bright_object: bool, optional
    :param sigma_step_log: [description], defaults to False
    :type sigma_step_log: bool, optional
    :param np_image_type: [description], defaults to np.float32
    :type np_image_type: [type], optional
    :param itk_image_type: [description], defaults to 'itk.Image[itk.F, 2]'
    :type itk_image_type: str, optional
    :param returnScaleImage: [description], defaults to False
    :type returnScaleImage: bool, optional
    :return: [description]
    :rtype: [type]
    """
    __image_itk_type = eval(itk_image_type)
    __image_np_type = np_image_type
    HessianImageType = itk.Image[itk.SymmetricSecondRankTensor[itk.D, 2], 2]
    ObjectnessFilterType = itk.HessianToObjectnessMeasureImageFilter[
        HessianImageType, __image_itk_type]
    MultiScaleEnhancementFilterType = itk.MultiScaleHessianBasedMeasureImageFilter[
        __image_itk_type, HessianImageType, __image_itk_type]
    input_image = old_div(input_image.astype(
        __image_np_type), input_image.max())
    itk_image = itk.PyBuffer[__image_itk_type].GetImageFromArray(
        input_image)
    objectnessFilter = ObjectnessFilterType.New()
    objectnessFilter.SetScaleObjectnessMeasure(scale_objectness_measure)
    objectnessFilter.SetBrightObject(bright_object)
    objectnessFilter.SetGamma(object_gamma)
    objectnessFilter.SetAlpha(object_alpha)
    objectnessFilter.SetBeta(object_beta)
    objectnessFilter.SetObjectDimension(object_dimension)
    multiScaleEnhancementFilter = MultiScaleEnhancementFilterType.New()
    multiScaleEnhancementFilter.SetInput(itk_image)
    multiScaleEnhancementFilter.SetHessianToMeasureFilter(objectnessFilter)
    multiScaleEnhancementFilter.SetSigmaMinimum(sigma_min)
    multiScaleEnhancementFilter.SetSigmaMaximum(sigma_max)
    multiScaleEnhancementFilter.SetNumberOfSigmaSteps(sigma_steps)
    if returnScaleImage:
        multiScaleEnhancementFilter.SetGenerateScalesOutput(True)
    if sigma_step_log:
        multiScaleEnhancementFilter.SetSigmaStepMethodToLogarithmic()
    else:
        multiScaleEnhancementFilter.SetSigmaStepMethodToEquispaced()
    multiScaleEnhancementFilter.Update()
    output_image = np.copy(itk.PyBuffer[__image_itk_type].GetArrayFromImage(
        multiScaleEnhancementFilter.GetOutput()))
    if returnScaleImage:
        scaleImage = np.copy(itk.PyBuffer[itk.Image[itk.F, 2]].GetArrayFromImage(
            multiScaleEnhancementFilter.GetScalesOutput()))
        return output_image,  scaleImage
    return output_image