"""Interactive subplot and its layers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from plotski import _plot_data as data
from plotski._plot_data import AxisKind, AxisValue, Coordinates, Extent, Layer, Limits, NativeLimits, Origin


@dataclass
class _Axis:
    kind: AxisKind | None
    limits: NativeLimits | None
    categories: tuple[str, ...]
    bounds: NativeLimits | None


def _merge_axes(axes: Sequence[_Axis], *, linked: bool = False) -> _Axis:
    kinds = {axis.kind for axis in axes if axis.kind is not None}
    if len(kinds) > 1:
        raise ValueError("incompatible axis types: " + ", ".join(sorted(kinds)))
    limits = {axis.limits for axis in axes if axis.limits is not None}
    if len(limits) > 1:
        raise ValueError("conflicting limits on linked axes")
    categories = tuple(dict.fromkeys(category for axis in axes for category in axis.categories))
    bounds = [axis.bounds for axis in axes if axis.bounds is not None]
    limits_value = next(iter(limits), None)
    extent = (min(low for low, _ in bounds), max(high for _, high in bounds)) if bounds else None
    if linked and extent is not None and limits_value is None:
        low, high = extent
        if low == high:
            if isinstance(low, datetime):
                low, high = low - timedelta(seconds=1), low + timedelta(seconds=1)
            else:
                padding = max(abs(low) * 0.05, 0.5)
                low, high = low - padding, low + padding
        limits_value = (low, high)
    return _Axis(next(iter(kinds), None), limits_value, categories, extent)


class Subplot:
    """A titled set of axes on which chart and annotation methods add layers."""

    def __init__(
        self,
        *,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        x_limits: Limits | None = None,
        y_limits: Limits | None = None,
        legend: bool = True,
        hover: bool = True,
    ) -> None:
        for limits in (x_limits, y_limits):
            if limits is not None:
                data.axis_limit(limits)
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.x_limits = x_limits
        self.y_limits = y_limits
        self.legend = legend
        self.hover = hover
        self._layers: list[Layer] = []
        self._axis_kinds: list[AxisKind | None] = [None, None]
        self._series_count = 0

    def _add(
        self,
        kind: str,
        values: dict[str, Any],
        x: tuple[NDArray, ...],
        y: tuple[NDArray, ...],
        *,
        color: str | None,
        opacity: float,
        label: str | None = None,
        hover: bool = False,
        annotation: bool = False,
    ) -> Subplot:
        if not 0 <= opacity <= 1:
            raise ValueError("opacity must be between 0 and 1")
        kinds = self._axis_kinds.copy()
        for index, (columns, limits) in enumerate(((x, self.x_limits), (y, self.y_limits))):
            observed = {data.axis_kind(column) for column in columns if len(column)}
            current = kinds[index]
            if current is not None:
                observed.add(current)
            if limits is not None:
                observed.add(data.axis_limit(limits)[0])
            if len(observed) > 1:
                axis = "xy"[index]
                raise ValueError(f"incompatible {axis}-axis types: {', '.join(sorted(observed))}")
            # Limits may be edited later. Only data contributes to the cached type.
            kinds[index] = next((data.axis_kind(column) for column in columns if len(column)), kinds[index])
        color_value = data.layer_color(color, 0 if annotation else self._series_count)
        self._layers.append(Layer(kind, values, (x, y), color_value, opacity, label, hover))
        self._axis_kinds = kinds
        if not annotation:
            self._series_count += 1
        return self

    def _axis(self, index: int) -> _Axis:
        limits = (self.x_limits, self.y_limits)[index]
        kind = self._axis_kinds[index]
        bounds: NativeLimits | None = None
        categories: dict[str, None] = {}
        limits_value = None
        if limits is not None:
            limit_kind, limits_value = data.axis_limit(limits)
            if kind is not None and limit_kind != kind:
                raise ValueError(f"incompatible {'xy'[index]}-axis limits for a {kind} axis")
            kind = limit_kind
        for layer in self._layers:
            for column in layer.axes[index]:
                if kind == "category":
                    categories.update(dict.fromkeys(column.tolist()))
                    continue
                valid = column[np.isfinite(column)]
                if len(valid):
                    low, high = valid.min().item(), valid.max().item()
                    bounds = (low, high) if bounds is None else (min(bounds[0], low), max(bounds[1], high))
        return _Axis(kind, limits_value, tuple(categories), bounds)

    def line(
        self,
        x: Coordinates,
        y: Coordinates,
        *,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 1,
        width: float = 2,
        hover: bool = True,
    ) -> Subplot:
        """Add a line with optional legend label, color, and stroke width."""
        x, y = data.vector(x, "x"), data.vector(y, "y")
        data.equal_lengths(x=x, y=y)
        _positive(width, "width")
        return self._add(
            "line", {"x": x, "y": y, "width": width}, (x,), (y,), color=color, opacity=opacity, label=label, hover=hover
        )

    def scatter(
        self,
        x: Coordinates,
        y: Coordinates,
        *,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 1,
        size: float = 7,
        hover: bool = True,
    ) -> Subplot:
        """Add scatter points with marker size in pixels."""
        x, y = data.vector(x, "x"), data.vector(y, "y")
        data.equal_lengths(x=x, y=y)
        _positive(size, "size")
        return self._add(
            "scatter",
            {"x": x, "y": y, "size": size},
            (x,),
            (y,),
            color=color,
            opacity=opacity,
            label=label,
            hover=hover,
        )

    def segments(
        self,
        x0: Coordinates,
        y0: Coordinates,
        x1: Coordinates,
        y1: Coordinates,
        *,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 1,
        width: float = 2,
        hover: bool = True,
    ) -> Subplot:
        """Add independent segments, for example centroid sticks."""
        x0, y0, x1, y1 = (
            data.vector(value, name) for name, value in zip(("x0", "y0", "x1", "y1"), (x0, y0, x1, y1), strict=False)
        )
        data.equal_lengths(x0=x0, y0=y0, x1=x1, y1=y1)
        _positive(width, "width")
        return self._add(
            "segments",
            {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "width": width},
            (x0, x1),
            (y0, y1),
            color=color,
            opacity=opacity,
            label=label,
            hover=hover,
        )

    def bar(
        self,
        x: Coordinates,
        y: ArrayLike,
        *,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 1,
        width: float = 0.8,
        hover: bool = True,
    ) -> Subplot:
        """Add vertical bars from zero, with width in x-axis units."""
        x, y = data.vector(x, "x"), data.vector(y, "y", numeric=True)
        data.equal_lengths(x=x, y=y)
        _positive(width, "width")
        return self._add(
            "bar",
            {"x": x, "y": y, "width": width},
            data.bar_edges(x, width),
            (y, np.zeros(1)),
            color=color,
            opacity=opacity,
            label=label,
            hover=hover,
        )

    def histogram(
        self,
        values: ArrayLike,
        *,
        bins: int | Sequence[float] | NDArray = 10,
        density: bool = False,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 1,
        hover: bool = True,
    ) -> Subplot:
        """Add a histogram with a bin count or explicit bin edges."""
        bins_data = data.histogram(values, bins, density)
        return self._add(
            "bar",
            bins_data,
            (bins_data["edges"],),
            (bins_data["y"], np.zeros(1)),
            color=color,
            opacity=opacity,
            label=label,
            hover=hover,
        )

    def boxplot(
        self,
        values: ArrayLike,
        *,
        categories: Sequence[str] | NDArray | None = None,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 0.75,
        hover: bool = True,
    ) -> Subplot:
        """Add Tukey boxplots, with one optional category per observation."""
        stats = data.boxplot(values, categories)
        return self._add(
            "boxplot",
            stats,
            (stats["x"],),
            (stats["low"], stats["high"], stats["outlier_y"]),
            color=color,
            opacity=opacity,
            label=label,
            hover=hover,
        )

    def area(
        self,
        x: Coordinates,
        y: ArrayLike,
        *,
        baseline: float = 0,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 0.35,
        hover: bool = True,
    ) -> Subplot:
        """Fill the area between a curve and a constant baseline."""
        if not np.isfinite(baseline):
            raise ValueError("baseline must be finite")
        x, y = data.vector(x, "x"), data.vector(y, "y", numeric=True)
        lower = np.full(len(x), baseline, dtype=float)
        return self._area(x, lower, y, color=color, opacity=opacity, label=label, hover=hover)

    def band(
        self,
        x: Coordinates,
        lower: ArrayLike,
        upper: ArrayLike,
        *,
        color: str | None = None,
        opacity: float = 0.2,
        label: str | None = None,
        hover: bool = False,
    ) -> Subplot:
        """Add an uncertainty band between paired lower and upper values."""
        x = data.vector(x, "x")
        lower, upper = data.vector(lower, "lower", numeric=True), data.vector(upper, "upper", numeric=True)
        data.equal_lengths(x=x, lower=lower, upper=upper)
        if np.any(lower > upper):
            raise ValueError("band lower values cannot exceed upper values")
        return self._area(x, lower, upper, color=color, opacity=opacity, label=label, hover=hover, annotation=True)

    def _area(
        self,
        x: NDArray,
        lower: NDArray,
        upper: NDArray,
        *,
        color: str | None,
        opacity: float,
        label: str | None,
        hover: bool,
        annotation: bool = False,
    ) -> Subplot:
        data.equal_lengths(x=x, lower=lower, upper=upper)
        missing = ~np.isfinite(lower) | ~np.isfinite(upper)
        lower[missing] = upper[missing] = np.nan
        return self._add(
            "area",
            {"x": x, "lower": lower, "upper": upper},
            (x,),
            (lower, upper),
            color=color,
            opacity=opacity,
            label=label,
            hover=hover,
            annotation=annotation,
        )

    def heatmap(
        self,
        z: ArrayLike,
        *,
        extent: Extent | None = None,
        origin: Origin = "upper",
        cmap: str = "viridis",
        z_min: float | None = None,
        z_max: float | None = None,
        colorbar: bool = True,
        opacity: float = 1,
        hover: bool = True,
    ) -> Subplot:
        """Add a scalar raster with optional data extent and color scale."""
        values = data.image_data(z, extent, origin)
        palette, low, high = data.heatmap_scale(values["pixels"], cmap, z_min, z_max)
        values.update(palette=palette, low=low, high=high, colorbar=colorbar)
        return self._image("heatmap", values, opacity, hover)

    def image(
        self,
        pixels: ArrayLike,
        *,
        extent: Extent | None = None,
        origin: Origin = "upper",
        opacity: float = 1,
        hover: bool = True,
    ) -> Subplot:
        """Add an RGB or RGBA raster with 8-bit channels and optional extent."""
        return self._image("image", data.image_data(pixels, extent, origin, rgba=True), opacity, hover)

    def _image(self, kind: str, values: dict[str, Any], opacity: float, hover: bool) -> Subplot:
        left, right, bottom, top = values["extent"]
        return self._add(
            kind,
            values,
            (np.array([left, right]),),
            (np.array([bottom, top]),),
            color=None,
            opacity=opacity,
            hover=hover,
        )

    def reference_line(
        self,
        value: AxisValue,
        *,
        axis: Literal["x", "y"] = "x",
        color: str | None = "#555555",
        opacity: float = 1,
        width: float = 1,
    ) -> Subplot:
        """Draw a vertical line at an x value or a horizontal line at a y value."""
        if axis not in ("x", "y"):
            raise ValueError("axis must be 'x' or 'y'")
        coord = data.vector([value], "value")
        if coord.dtype.kind == "U" or not np.isfinite(coord[0]):
            raise ValueError("reference line must be at a finite number or date")
        _positive(width, "width")
        return self._add(
            "reference_line",
            {"axis": axis, "value": coord[0].item(), "width": width},
            (coord,) if axis == "x" else (),
            (coord,) if axis == "y" else (),
            color=color,
            opacity=opacity,
            annotation=True,
        )

    def rectangle(
        self,
        left: AxisValue,
        bottom: AxisValue,
        right: AxisValue,
        top: AxisValue,
        *,
        color: str | None = None,
        opacity: float = 0.2,
    ) -> Subplot:
        """Highlight a region between two x bounds and two y bounds."""
        _, (x0, x1) = data.axis_limit((left, right))
        _, (y0, y1) = data.axis_limit((bottom, top))
        x, y = data.vector([left, right], "x"), data.vector([bottom, top], "y")
        if x[0] > x[1] or y[0] > y[1]:
            raise ValueError("rectangle bounds must be increasing")
        return self._add(
            "rectangle",
            {"x0": x0, "x1": x1, "y0": y0, "y1": y1},
            (x,),
            (y,),
            color=color,
            opacity=opacity,
            annotation=True,
        )

    def polygon(
        self,
        x: Coordinates,
        y: Coordinates,
        *,
        color: str | None = None,
        opacity: float = 0.2,
    ) -> Subplot:
        """Draw a filled polygon with at least three vertices."""
        x, y = data.vector(x, "x"), data.vector(y, "y")
        data.equal_lengths(x=x, y=y)
        if len(x) < 3 or any(array.dtype.kind != "U" and not np.all(np.isfinite(array)) for array in (x, y)):
            raise ValueError("polygon requires at least three finite vertices")
        return self._add("polygon", {"x": x, "y": y}, (x,), (y,), color=color, opacity=opacity, annotation=True)

    def labels(
        self,
        x: Coordinates,
        y: Coordinates,
        text: Sequence[str] | NDArray,
        *,
        color: str | None = "#333333",
        opacity: float = 1,
        size: float = 12,
    ) -> Subplot:
        """Place text labels at paired coordinates."""
        x, y, text = data.vector(x, "x"), data.vector(y, "y"), np.array(text, dtype=object)
        if text.ndim != 1 or not all(isinstance(value, str) for value in text):
            raise ValueError("text must contain a one-dimensional sequence of strings")
        data.equal_lengths(x=x, y=y, text=text)
        _positive(size, "size")
        return self._add(
            "labels",
            {"x": x, "y": y, "text": text, "size": size},
            (x,),
            (y,),
            color=color,
            opacity=opacity,
            annotation=True,
        )


def _positive(value: float, name: str) -> None:
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
