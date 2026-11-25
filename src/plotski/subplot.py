"""Interactive subplot and its layers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from numbers import Integral
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from plotski import _plot_data as data
from plotski._plot_data import (
    AxisKind,
    AxisValue,
    Coordinates,
    Errors,
    Extent,
    HoverFields,
    HoverFormats,
    Layer,
    Limits,
    NativeLimits,
    Origin,
)

if TYPE_CHECKING:
    from plotski.figure import Grid


@dataclass(frozen=True)
class _AxisSettings:
    scale: Literal["linear", "log"] = "linear"
    reverse: bool = False
    tick_format: str | None = None


@dataclass
class _Axis:
    kind: AxisKind | None
    limits: NativeLimits | None
    categories: tuple[str, ...]
    bounds: NativeLimits | None
    scale: Literal["linear", "log"] = "linear"
    reverse: bool = False


def _merge_axes(axes: Sequence[_Axis], *, linked: bool = False) -> _Axis:
    kinds = {axis.kind for axis in axes if axis.kind is not None}
    if len(kinds) > 1:
        raise ValueError("incompatible axis types: " + ", ".join(sorted(kinds)))
    settings = {(axis.scale, axis.reverse) for axis in axes}
    if len(settings) > 1:
        raise ValueError("linked axes must have compatible scales and directions")
    scale, reverse = next(iter(settings))
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
            elif scale == "log":
                low, high = low / 1.1, low * 1.1
            else:
                padding = max(abs(low) * 0.05, 0.5)
                low, high = low - padding, low + padding
        limits_value = (high, low) if reverse else (low, high)
    return _Axis(next(iter(kinds), None), limits_value, categories, extent, scale, reverse)


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
        self._axis_settings = [_AxisSettings(), _AxisSettings()]
        self._series_count = 0
        self._grid: Grid | None = None

    def configure_axis(
        self,
        axis: Literal["x", "y"],
        *,
        scale: Literal["linear", "log"] = "linear",
        reverse: bool = False,
        tick_format: str | None = None,
    ) -> Subplot:
        """Set an axis scale, direction, and optional numeric format such as '.2f' or '.1e'."""
        if axis not in ("x", "y") or scale not in ("linear", "log"):
            raise ValueError("expected axis 'x' or 'y' and scale 'linear' or 'log'")
        if tick_format is not None and (
            not tick_format.startswith(".")
            or tick_format[-1:] not in ("f", "e")
            or not tick_format[1:-1].isdigit()
            or not 0 <= int(tick_format[1:-1]) <= 15
        ):
            raise ValueError("tick_format must be a numeric format such as '.2f' or '.1e' with up to 15 digits")
        index = "xy".index(axis)
        settings = _AxisSettings(scale, reverse, tick_format)
        self._axis(index, settings)
        self._axis_settings[index] = settings
        return self

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
        color_value = data.layer_color(color, 0 if annotation else self._series_count)
        layer = Layer(kind, values, (x, y), color_value, opacity, label, hover)
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
            settings = self._axis_settings[index]
            if settings.scale == "log":
                self._validate_log_axis(
                    index,
                    next(iter(observed), None),
                    data.axis_limit(limits)[1] if limits is not None else None,
                    [layer],
                )
            if settings.tick_format is not None and observed - {"linear"}:
                raise ValueError("tick_format requires a numeric axis")
            # Limits may be edited later. Only data contributes to the cached type.
            kinds[index] = next((data.axis_kind(column) for column in columns if len(column)), kinds[index])
        self._layers.append(layer)
        self._axis_kinds = kinds
        if not annotation:
            self._series_count += 1
        return self

    @staticmethod
    def _validate_log_axis(
        index: int, kind: AxisKind | None, limits: NativeLimits | None, layers: Sequence[Layer]
    ) -> None:
        if kind not in (None, "linear") or (limits is not None and min(limits) <= 0):
            raise ValueError("log axes require numeric data and positive limits")
        for layer in layers:
            if layer.kind in ("line", "scatter"):
                if index == 1 and (errors := layer.data.get("errors")) is not None:
                    y = layer.data["y"]
                    if np.any((y > 0) & (y - errors[0] <= 0)):
                        raise ValueError("error bars on log axes require positive endpoints")
            elif layer.kind in ("heatmap", "image") or any(np.any(column <= 0) for column in layer.axes[index]):
                raise ValueError(f"{layer.kind} is incompatible with this logarithmic axis")

    def _axis(self, index: int, settings: _AxisSettings | None = None) -> _Axis:
        settings = settings or self._axis_settings[index]
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
        if settings.scale == "log":
            self._validate_log_axis(index, kind, limits_value, self._layers)
        if settings.tick_format is not None and kind not in (None, "linear"):
            raise ValueError("tick_format requires a numeric axis")
        for layer in self._layers:
            for column in layer.axes[index]:
                if kind == "category":
                    categories.update(dict.fromkeys(column.tolist()))
                    continue
                valid = column[np.isfinite(column)]
                if settings.scale == "log":
                    valid = valid[valid > 0]
                if len(valid):
                    low, high = valid.min().item(), valid.max().item()
                    bounds = (low, high) if bounds is None else (min(bounds[0], low), max(bounds[1], high))
        if settings.reverse and limits_value is not None and limits_value[0] < limits_value[1]:
            limits_value = limits_value[::-1]
        return _Axis(kind, limits_value, tuple(categories), bounds, settings.scale, settings.reverse)

    def _render_layers(self) -> Sequence[Layer]:
        """Apply display-only log gaps and profile sampling to fresh layer data."""
        log_axes = [name for name, settings in zip("xy", self._axis_settings, strict=True) if settings.scale == "log"]
        rendered: list[Layer] = []
        for layer in self._layers:
            max_points = layer.data.get("max_points")
            if layer.kind not in ("line", "scatter") or not (log_axes or max_points):
                rendered.append(layer)
                continue
            values = layer.data.copy()
            for name in log_axes:
                column = values[name]
                values[name] = np.where(column > 0, column, np.nan)
            if max_points is not None and len(values["x"]) > max_points:
                indices = data.profile_indices(values["x"], values["y"], max_points)
                values["x"], values["y"] = values["x"][indices], values["y"][indices]
                values["hover_columns"] = {
                    name: [column[index] for index in indices] for name, column in values["hover_columns"].items()
                }
            rendered.append(replace(layer, data=values))
        return rendered

    def save_image(self, path: str | Path, *, scale: float = 1) -> Path:
        """Export this subplot as PNG or SVG using its grid's backend, or Bokeh when standalone."""
        if self._grid is not None:
            return self._grid._save_subplot(self, path, scale)
        from plotski.figure import Grid, _Placement

        grid = Grid(1, 1)
        grid._placements[0, 0] = _Placement(self, 0, 0, 1, 1)
        return grid.save_image(path, scale=scale)

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
        hover_fields: HoverFields | None = None,
        hover_formats: HoverFormats | None = None,
        max_points: int | None = None,
    ) -> Subplot:
        """Add a line with optional hover columns and peak-preserving sampling."""
        x, y = data.vector(x, "x"), data.vector(y, "y")
        data.equal_lengths(x=x, y=y)
        _positive(width, "width")
        if max_points is not None:
            if isinstance(max_points, bool) or not isinstance(max_points, Integral) or max_points < 4:
                raise ValueError("max_points must be an integer of at least 4")
            if "category" in (data.axis_kind(x), data.axis_kind(y)):
                raise ValueError("line sampling requires numeric or date coordinates")
        values = {"x": x, "y": y, "width": width, "max_points": max_points}
        values["hover_columns"] = data.hover_columns({"x": x, "y": y}, hover_fields, hover_formats)
        return self._add("line", values, (x,), (y,), color=color, opacity=opacity, label=label, hover=hover)

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
        hover_fields: HoverFields | None = None,
        hover_formats: HoverFormats | None = None,
        y_error: Errors | None = None,
        selection_group: str | None = None,
        ids: Sequence[str] | NDArray | None = None,
    ) -> Subplot:
        """Add points with optional asymmetric y errors and linked selection IDs."""
        x, y = data.vector(x, "x"), data.vector(y, "y")
        data.equal_lengths(x=x, y=y)
        _positive(size, "size")
        errors = data.error_deltas(y, y_error)
        identities = data.selection_ids(len(x), ids, selection_group)
        bounds = (y,) if errors is None else (y, y - errors[0], y + errors[1])
        return self._add(
            "scatter",
            {
                "x": x,
                "y": y,
                "size": size,
                "errors": errors,
                "ids": identities,
                "selection_group": selection_group,
                "hover_columns": data.hover_columns({"x": x, "y": y}, hover_fields, hover_formats),
            },
            (x,),
            bounds,
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
        hover_fields: HoverFields | None = None,
        hover_formats: HoverFormats | None = None,
    ) -> Subplot:
        """Add independent segments, for example centroid sticks."""
        x0, y0, x1, y1 = (
            data.vector(value, name) for name, value in zip(("x0", "y0", "x1", "y1"), (x0, y0, x1, y1), strict=False)
        )
        data.equal_lengths(x0=x0, y0=y0, x1=x1, y1=y1)
        _positive(width, "width")
        coordinates = {"x0": x0, "y0": y0, "x1": x1, "y1": y1}
        return self._add(
            "segments",
            {
                **coordinates,
                "width": width,
                "hover_columns": data.hover_columns(coordinates, hover_fields, hover_formats),
            },
            (x0, x1),
            (y0, y1),
            color=color,
            opacity=opacity,
            label=label,
            hover=hover,
        )

    def spectrum(
        self,
        mz: Coordinates,
        intensity: ArrayLike,
        *,
        centroid: bool = False,
        mirror: bool = False,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 1,
        width: float = 2,
        hover: bool = True,
        hover_fields: HoverFields | None = None,
        hover_formats: HoverFormats | None = None,
        max_points: int | None = None,
    ) -> Subplot:
        """Add a profile or centroid mass spectrum, optionally below the zero line."""
        return self._profile(
            mz,
            intensity,
            "m/z",
            centroid,
            mirror,
            label,
            color,
            opacity,
            width,
            hover,
            hover_fields,
            hover_formats,
            max_points,
        )

    def mobilogram(
        self,
        drift_time: Coordinates,
        intensity: ArrayLike,
        *,
        centroid: bool = False,
        mirror: bool = False,
        label: str | None = None,
        color: str | None = None,
        opacity: float = 1,
        width: float = 2,
        hover: bool = True,
        hover_fields: HoverFields | None = None,
        hover_formats: HoverFormats | None = None,
        max_points: int | None = None,
    ) -> Subplot:
        """Add a profile or centroid mobilogram with drift time in bins by default."""
        return self._profile(
            drift_time,
            intensity,
            "Drift time (bins)",
            centroid,
            mirror,
            label,
            color,
            opacity,
            width,
            hover,
            hover_fields,
            hover_formats,
            max_points,
        )

    def _profile(
        self,
        x: Coordinates,
        intensity: ArrayLike,
        x_label: str,
        centroid: bool,
        mirror: bool,
        label: str | None,
        color: str | None,
        opacity: float,
        width: float,
        hover: bool,
        hover_fields: HoverFields | None,
        hover_formats: HoverFormats | None,
        max_points: int | None,
    ) -> Subplot:
        x = data.vector(x, "coordinates", numeric=True)
        intensity = data.vector(intensity, "intensity", numeric=True)
        y = -intensity if mirror else intensity
        if centroid:
            if max_points is not None:
                raise ValueError("max_points applies to profile lines")
            self.segments(
                x,
                np.zeros_like(y),
                x,
                y,
                label=label,
                color=color,
                opacity=opacity,
                width=width,
                hover=hover,
                hover_fields=hover_fields,
                hover_formats=hover_formats,
            )
        else:
            self.line(
                x,
                y,
                label=label,
                color=color,
                opacity=opacity,
                width=width,
                hover=hover,
                hover_fields=hover_fields,
                hover_formats=hover_formats,
                max_points=max_points,
            )
        if mirror and hover:
            columns = self._layers[-1].data["hover_columns"]
            key = "y1" if centroid else "y"
            if not columns and centroid:
                columns = data.hover_columns({"x1": x, "y1": intensity}, {}, None)
                self._layers[-1].data["hover_columns"] = columns
            elif not columns:
                columns = data.hover_columns({"x": x, "y": intensity}, {}, None)
                self._layers[-1].data["hover_columns"] = columns
            else:
                columns.update(data.hover_columns({key: intensity}, {}, {key: (hover_formats or {}).get(key, "")}))
        self.x_label = self.x_label or x_label
        self.y_label = self.y_label or "Intensity"
        return self

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
        hover_fields: HoverFields | None = None,
        hover_formats: HoverFormats | None = None,
        y_error: Errors | None = None,
    ) -> Subplot:
        """Add vertical bars from zero, with width in x-axis units."""
        x, y = data.vector(x, "x"), data.vector(y, "y", numeric=True)
        data.equal_lengths(x=x, y=y)
        _positive(width, "width")
        return self._bar(
            x,
            y,
            np.zeros_like(y),
            width=width,
            offset=0,
            label=label,
            color=color,
            opacity=opacity,
            hover=hover,
            hover_fields=hover_fields,
            hover_formats=hover_formats,
            y_error=y_error,
        )

    def bars(
        self,
        categories: Sequence[str] | NDArray,
        series: Mapping[str, ArrayLike],
        *,
        mode: Literal["grouped", "stacked"] = "grouped",
        width: float = 0.8,
        y_error: Mapping[str, Errors] | None = None,
    ) -> Subplot:
        """Add named side-by-side or signed stacked bars for each category."""
        x = data.vector(categories, "categories")
        if data.axis_kind(x) != "category" or len(set(x)) != len(x) or not len(x):
            raise ValueError("categories must contain unique strings")
        if mode not in ("grouped", "stacked") or not series:
            raise ValueError("bars requires named series and mode 'grouped' or 'stacked'")
        if y_error is not None and y_error.keys() - series.keys():
            raise ValueError("y_error keys must match a bar series")
        _positive(width, "width")
        bar_width = width / len(series) if mode == "grouped" else width
        positive, negative = np.zeros(len(x)), np.zeros(len(x))
        previous_count = self._series_count
        previous_kinds = self._axis_kinds
        previous_layers = len(self._layers)
        try:
            for index, (name, values) in enumerate(series.items()):
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("bar series names must be nonempty strings")
                y = data.vector(values, name, numeric=True)
                data.equal_lengths(categories=x, y=y)
                base = np.zeros_like(y)
                offset = (index - (len(series) - 1) / 2) * bar_width if mode == "grouped" else 0.0
                if mode == "stacked":
                    base = np.where(y < 0, negative, positive)
                    positive += np.where(np.isfinite(y) & (y > 0), y, 0)
                    negative += np.where(np.isfinite(y) & (y < 0), y, 0)
                self._bar(
                    x,
                    y,
                    base,
                    width=bar_width,
                    offset=offset,
                    label=name,
                    color=None,
                    opacity=1,
                    hover=True,
                    hover_fields=None,
                    hover_formats=None,
                    y_error=(y_error or {}).get(name),
                )
        except ValueError:
            del self._layers[previous_layers:]
            self._series_count = previous_count
            self._axis_kinds = previous_kinds
            raise
        return self

    def _bar(
        self,
        x: NDArray,
        y: NDArray,
        base: NDArray,
        *,
        width: float,
        offset: float,
        label: str | None,
        color: str | None,
        opacity: float,
        hover: bool,
        hover_fields: HoverFields | None,
        hover_formats: HoverFormats | None,
        y_error: Errors | None,
    ) -> Subplot:
        top = base + y
        errors = data.error_deltas(y, y_error)
        bounds = (base, top) if errors is None else (base, top, top - errors[0], top + errors[1])
        return self._add(
            "bar",
            {
                "x": x,
                "y": y,
                "width": width,
                "base": base,
                "top": top,
                "offset": offset,
                "errors": errors,
                "hover_columns": data.hover_columns({"x": x, "y": y}, hover_fields, hover_formats),
            },
            data.bar_edges(x, width),
            bounds,
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
