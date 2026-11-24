"""Data normalization shared by the interactive renderers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Literal, TypeAlias

import numpy as np
from matplotlib.colors import to_hex
from numpy.typing import ArrayLike, NDArray

from plotski.utilities import get_colormap

AxisValue: TypeAlias = float | date | np.datetime64
Coordinates: TypeAlias = ArrayLike | Sequence[AxisValue | None]
Limits: TypeAlias = tuple[AxisValue, AxisValue]
NativeLimits: TypeAlias = tuple[float | datetime, float | datetime]
AxisKind = Literal["linear", "datetime", "category"]
Origin = Literal["upper", "lower"]
Extent = tuple[float, float, float, float]

_COLORS = ("#1f77b4", "#d95f02", "#2ca02c", "#9467bd", "#c23b53", "#16858c")


@dataclass
class Layer:
    """An ordered drawing operation with normalized data and style."""

    kind: str
    data: dict[str, Any]
    axes: tuple[tuple[NDArray, ...], tuple[NDArray, ...]]
    color: str
    opacity: float
    label: str | None
    hover: bool


def vector(values: Coordinates, name: str, *, numeric: bool = False) -> NDArray:
    """Copy and validate a vector of coordinates."""
    array = np.asarray(values)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if array.dtype.kind in "biuf":
        return array.astype(float, copy=True)
    if not numeric:
        if array.dtype.kind == "M":
            return array.astype("datetime64[ms]")
        if array.dtype.kind == "U":
            if isinstance(values, Sequence) and any(not isinstance(item, str) for item in values):
                raise ValueError(f"{name} cannot mix category strings with other coordinates")
            return array.copy()
        if array.dtype.kind == "O":
            if len(array) and all(isinstance(item, str) for item in array):
                return array.astype(str)
            items = [item for item in array if item is not None]
            if items and all(isinstance(item, (date, np.datetime64)) for item in items):
                return np.asarray(
                    [
                        item.astimezone(timezone.utc).replace(tzinfo=None)
                        if isinstance(item, datetime) and item.utcoffset() is not None
                        else item
                        for item in array
                    ],
                    dtype="datetime64[ms]",
                )
    if array.dtype.kind == "O" and all(
        item is None or isinstance(item, (int, float, np.integer, np.floating)) for item in array
    ):
        return array.astype(float)
    expected = "numeric values" if numeric else "numeric values, dates, or category strings"
    raise ValueError(f"{name} must contain {expected}")


def equal_lengths(**vectors: NDArray) -> None:
    """Validate that paired coordinates have the same length."""
    if len({len(array) for array in vectors.values()}) > 1:
        raise ValueError(f"{', '.join(vectors)} must have the same length")


def axis_kind(array: NDArray) -> AxisKind:
    """Identify the native axis type for a normalized coordinate vector."""
    if array.dtype.kind == "M":
        return "datetime"
    if array.dtype.kind == "U":
        return "category"
    return "linear"


def axis_limit(limits: Limits) -> tuple[AxisKind, NativeLimits]:
    """Normalize a fixed range in data coordinates."""
    values = vector(limits, "axis limits")
    if len(values) != 2 or values.dtype.kind == "U" or not np.all(np.isfinite(values)) or values[0] == values[1]:
        raise ValueError("axis limits must be two distinct finite numbers or dates")
    return axis_kind(values), (values[0].item(), values[1].item())


def layer_color(color: str | None, index: int) -> str:
    """Select or normalize a color accepted by both renderers."""
    return _COLORS[index % len(_COLORS)] if color is None else to_hex(color)


def bar_edges(x: NDArray, width: float) -> tuple[NDArray, ...]:
    """Include the width of numeric or datetime bars in autorange."""
    if axis_kind(x) == "category":
        return (x,)
    delta = np.timedelta64(round(width / 2), "ms") if axis_kind(x) == "datetime" else width / 2
    return x - delta, x + delta


def histogram(values: ArrayLike, bins: int | Sequence[float] | NDArray, density: bool) -> dict[str, NDArray]:
    """Compute bins and heights once for both backends."""
    samples = vector(values, "values", numeric=True)
    samples = samples[np.isfinite(samples)]
    if not len(samples):
        raise ValueError("histogram requires at least one finite value")
    if not isinstance(bins, (int, np.integer)):
        bins = vector(bins, "bins", numeric=True)
        if len(bins) < 2 or not np.all(np.isfinite(bins)) or np.any(np.diff(bins) <= 0):
            raise ValueError("histogram bin edges must be finite and strictly increasing")
    elif bins <= 0:
        raise ValueError("histogram requires a positive number of bins")
    counts, edges = np.histogram(samples, bins=bins)
    widths = np.diff(edges)
    if density:
        if not counts.sum():
            raise ValueError("density requires at least one sample inside the bins")
        counts = counts / (counts.sum() * widths)
    return {"x": edges[:-1] + widths / 2, "width": widths, "y": counts, "edges": edges}


def boxplot(values: ArrayLike, categories: Sequence[str] | NDArray | None) -> dict[str, NDArray]:
    """Calculate quartiles, Tukey whiskers, and outliers per category."""
    samples = vector(values, "values", numeric=True)
    groups = np.full(len(samples), "Values") if categories is None else vector(categories, "categories")
    equal_lengths(values=samples, categories=groups)
    if axis_kind(groups) != "category":
        raise ValueError("boxplot categories must be strings")
    finite = np.isfinite(samples)
    if not np.any(finite):
        raise ValueError("boxplot requires at least one finite value")
    samples, groups = samples[finite], groups[finite]
    data: dict[str, list] = {key: [] for key in ("x", "q1", "median", "q3", "low", "high", "outlier_x", "outlier_y")}
    for group in dict.fromkeys(groups.tolist()):
        sample = samples[groups == group]
        q1, median, q3 = np.percentile(sample, [25, 50, 75])
        whisker = 1.5 * (q3 - q1)
        inside = (sample >= q1 - whisker) & (sample <= q3 + whisker)
        data["x"].append(group)
        data["q1"].append(q1)
        data["median"].append(median)
        data["q3"].append(q3)
        data["low"].append(sample[inside].min())
        data["high"].append(sample[inside].max())
        outliers = sample[~inside]
        data["outlier_x"].extend([group] * len(outliers))
        data["outlier_y"].extend(outliers)
    return {key: np.asarray(values, dtype=str if key in ("x", "outlier_x") else float) for key, values in data.items()}


def image_data(pixels: ArrayLike, extent: Extent | None, origin: Origin, *, rgba: bool = False) -> dict[str, Any]:
    """Normalize rasters so the first stored row is the bottom row."""
    array = np.asarray(pixels)
    if rgba:
        if array.ndim != 3 or array.shape[2] not in (3, 4):
            raise ValueError("image requires an array of shape (rows, columns, 3 or 4)")
        if array.dtype.kind not in "iu" or np.any((array < 0) | (array > 255)):
            raise ValueError("RGB/RGBA channels must be integers between 0 and 255")
        array = array.astype(np.uint8)
    else:
        if array.ndim != 2 or array.dtype.kind not in "biuf":
            raise ValueError("heatmap requires a two-dimensional numeric array")
        array = array.astype(float)
        array[~np.isfinite(array)] = np.nan
    rows, cols = array.shape[:2]
    if not rows or not cols:
        raise ValueError("images cannot be empty")
    if origin not in ("upper", "lower"):
        raise ValueError("origin must be 'upper' or 'lower'")
    if extent is None:
        bounds = (0.0, float(cols), 0.0, float(rows))
    else:
        if len(extent) != 4:
            raise ValueError("extent must contain increasing finite (left, right, bottom, top) bounds")
        left, right, bottom, top = map(float, extent)
        bounds = left, right, bottom, top
        if not all(np.isfinite(bounds)) or not (left < right and bottom < top):
            raise ValueError("extent must contain increasing finite (left, right, bottom, top) bounds")
    left, right, bottom, top = bounds
    return {
        "pixels": np.ascontiguousarray(array[::-1] if origin == "upper" else array),
        "extent": bounds,
        "dx": (right - left) / cols,
        "dy": (top - bottom) / rows,
    }


def heatmap_scale(
    pixels: NDArray, cmap: str, z_min: float | None, z_max: float | None
) -> tuple[list[str], float, float]:
    """Sample one palette and resolve finite color limits."""
    if (z_min is not None and not np.isfinite(z_min)) or (z_max is not None and not np.isfinite(z_max)):
        raise ValueError("heatmap color limits must be finite")
    finite = pixels[np.isfinite(pixels)]
    low = float(finite.min()) if z_min is None and len(finite) else z_min
    high = float(finite.max()) if z_max is None and len(finite) else z_max
    low = (0.0 if high is None else high - 1) if low is None else low
    high = low + 1 if high is None else high
    if low > high:
        raise ValueError("heatmap z_min cannot exceed z_max")
    if low == high:
        padding = max(abs(low) * 0.01, 0.5)
        low, high = low - padding, high + padding
    palette = [to_hex(color) for color in get_colormap(cmap)(np.linspace(0, 1, 256))]
    return palette, low, high
