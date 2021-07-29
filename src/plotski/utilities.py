"""Various utilities"""
from uuid import uuid4

import numpy as np


def get_min_max(values):
    """Get the minimum and maximum value of an array"""
    return [np.min(values), np.max(values)]


def get_unique_str():
    """Gives random, unique name"""
    return str(uuid4().hex)


def check_key(source, key):
    if key in source.data:
        return True
    return False


def check_source(source, keys):
    """Helper function to check source has all of the required fields"""
    missing = []
    for key in keys:
        if key not in source.data:
            missing.append(key)

    if missing:
        missing = ", ".join(missing)
        raise ValueError(f"Missing '{missing}' from the ColumnDataSource")


def calculate_aspect_ratio(shape, plot_width):
    """Calculate aspect ratio by computing the ratio between the height and width of an array and multiplying it
    by plot width

    Parameters
    ----------
    shape : tuple
        array shape (width, height)
    plot_width : int
        plot width

    Returns
    -------
    plot_width : int
        plot width (not changed)
    plot_height : int
        plot height with array shape being taken into account

    Raises
    ------
    ValueError
        raises ValueError if the shape has fewer than two elements
    """
    if isinstance(shape, np.ndarray):
        shape = shape.shape

    if len(shape) == 2:
        height, width = shape
    else:
        height, width, _ = shape
    if len(shape) < 2:
        raise ValueError("In order to calculate the aspect ratio of the plot, the shape must have two elements (h, w)")

    plot_height = int((height / width) * plot_width)
    return plot_height, plot_width
