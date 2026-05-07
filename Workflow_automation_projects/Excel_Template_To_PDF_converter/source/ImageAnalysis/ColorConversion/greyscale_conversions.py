import numpy as np


def greyscale_to_rgb(image_as_np: np.ndarray) -> np.ndarray:
    """converts greyscale to rgb

    :param image_as_np: image as numpy array in 0-1
    :type image_as_np: ndarray
    :return: image as numpy array but in rgb
    :rtype: ndarray
    """
    return np.dstack([image_as_np, image_as_np, image_as_np])
