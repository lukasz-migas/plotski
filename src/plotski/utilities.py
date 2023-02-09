"""Various utilities"""
import random
import typing as ty
from uuid import uuid4

import matplotlib.colors as colors
import numpy as np
from bokeh.models.mappers import LinearColorMapper


def get_colormap(cmap: str):
    """Get matplotlib colormap."""
    try:
        import matplotlib as mpl

        return mpl.colormaps[cmap]
    except AttributeError:
        from matplotlib import cm

        return cm.get_cmap(cmap)


def convert_colormap_to_mapper(array, colormap="viridis", palette=None, z_min=None, z_max=None):
    """Convert matplotlib colormap to Bokeh color mapper

    Parameters
    ----------
    array : np.ndarray
        array
    colormap : str
        name of the colormap
    palette :
    z_min : float
        starting intensity for the colormap
    z_max : float
        final intensity for the colormap

    Returns
    -------
    _palette : Palette
        Bokeh palette
    _color_mapper : LinearColorMapper
        Bokeh colormapper
    """
    array = np.nan_to_num(array)
    if z_min is None:
        z_min = np.round(np.min(array), 2)
    if z_max is None:
        z_max = np.round(np.max(array), 2)

    if palette is None:
        _colormap = get_colormap(colormap)
        _palette = [colors.rgb2hex(m) for m in _colormap(np.arange(_colormap.N))]
    else:
        _palette = palette

    _color_mapper = LinearColorMapper(palette=_palette, low=z_min, high=z_max)

    return _palette, _color_mapper


def rescale(values: ty.Union[np.ndarray, ty.List], new_min: float, new_max: float, dtype=None) -> np.ndarray:
    """Rescale values from one range to another

    Parameters
    ----------
    values : Union[np.ndarray, List]
        input range
    new_min : float
        new minimum value
    new_max : float
        new maximum value
    dtype :
        data type

    Returns
    -------
    new_values : np.ndarray
        rescaled range
    """
    values = np.asarray(values)
    if dtype is None:
        dtype = values.dtype
    old_min, old_max = np.min(values), np.max(values)
    new_values = ((values - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min
    return new_values.astype(dtype)


def convert_hex_to_rgb_1(hex_str, decimals=3):
    """Convert hex color to rgb in range 0-1."""
    hex_color = hex_str.lstrip("#")
    n = len(hex_color)
    rgb = tuple(int(hex_color[i : i + int(n / 3)], 16) for i in range(0, int(n), int(n / 3)))
    return [np.round(rgb[0] / 255.0, decimals), np.round(rgb[1] / 255.0, decimals), np.round(rgb[2] / 255.0, decimals)]


def convert_hex_to_rgb_255(hex_str):
    """Convert hex color to rgb in range 0-255."""
    hex_color = hex_str.lstrip("#")
    n = len(hex_color)
    rgb = list(int(hex_color[i : i + int(n / 3)], 16) for i in range(0, int(n), int(n / 3)))
    return rgb


def get_random_hex_color():
    """Return random hex color"""
    return "#%06x" % random.randint(0, 0xFFFFFF)


def get_min_max(values):
    """Get the minimum and maximum value of an array"""
    return [np.min(values), np.max(values)]


def get_unique_str():
    """Gives random, unique name"""
    return str(uuid4().hex)


def check_key(source, key):
    """Helper function to check source has a particular field"""
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
        raise ValueError(f"Missing '{', '.join(missing)}' from the ColumnDataSource")


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
