"""Bokeh rendering for the shared plotting interface."""

from __future__ import annotations

from datetime import datetime
from itertools import chain
from typing import TYPE_CHECKING, Any

import numpy as np
from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import (
    ColumnDataSource,
    DataRange1d,
    FactorRange,
    GridBox,
    HoverTool,
    LinearColorMapper,
    Range,
    Range1d,
    Spacer,
    TabPanel,
    Tabs,
)
from bokeh.plotting import figure
from bokeh.resources import CDN, INLINE

from plotski._plot_data import Layer
from plotski.figure import Figure, Resources, _cells, _GridAxes, _Placement
from plotski.subplot import Subplot, _Axis

if TYPE_CHECKING:
    from bokeh.models.annotations.geometry import BoxAnnotation, Span
    from bokeh.models.annotations.labels import LabelSet
    from bokeh.models.annotations.legends import ColorBar
    from bokeh.models.renderers.glyph_renderer import GlyphRenderer
    from bokeh.models.ui.ui_element import UIElement
else:
    from bokeh.models import BoxAnnotation, ColorBar, GlyphRenderer, LabelSet, Span

_CELL_WIDTH = 440
_CELL_HEIGHT = 320
_GAP = 12


def _range(axis: _Axis) -> Range:
    if axis.kind == "category":
        return FactorRange(factors=list(axis.categories))
    if axis.limits is not None:
        start, end = axis.limits
        return Range1d(start=_timestamp(start), end=_timestamp(end))
    return DataRange1d()


def _timestamp(value: float | datetime) -> float:
    """Return a numeric coordinate for Bokeh annotations and ranges."""
    if isinstance(value, (int, float)):
        return value
    return float(np.datetime64(value, "ms").astype("int64"))


def _layer(plot: figure, layer: Layer, legend: bool, hover: bool) -> None:
    # ColumnDataSource keeps references to arrays. The native grid owns these copies.
    d: dict[str, Any] = {
        key: value.copy() if isinstance(value, (np.ndarray, list)) else value for key, value in layer.data.items()
    }
    color, alpha = layer.color, layer.opacity
    style: dict[str, Any] = {"color": color, "alpha": alpha}
    named = {"legend_label": layer.label} if legend and layer.label else {}
    renderer: GlyphRenderer
    tips = [("x", "@x"), ("y", "@y")]

    match layer.kind:
        case "line":
            renderer = plot.line("x", "y", source={"x": d["x"], "y": d["y"]}, line_width=d["width"], **style, **named)
        case "scatter":
            renderer = plot.scatter("x", "y", source={"x": d["x"], "y": d["y"]}, size=d["size"], **style, **named)
        case "segments":
            source = {key: d[key] for key in ("x0", "x1", "y0", "y1")}
            renderer = plot.segment("x0", "y0", "x1", "y1", source=source, line_width=d["width"], **style, **named)
            tips = [("start", "(@x0, @y0)"), ("end", "(@x1, @y1)")]
        case "bar":
            width = d["width"]
            source = {"x": d["x"], "y": d["y"]}
            if np.ndim(width):
                source["width"] = width
                width = "width"
            renderer = plot.vbar(x="x", top="y", width=width, source=source, line_color=None, **style, **named)
        case "area":
            renderer = plot.varea(x="x", y1="lower", y2="upper", source=d, fill_color=color, fill_alpha=alpha, **named)
            tips = [("x", "@x"), ("lower", "@lower"), ("upper", "@upper")]
        case "boxplot":
            source = {key: d[key] for key in ("x", "q1", "median", "q3", "low", "high")}
            plot.segment("x", "low", "x", "q1", source=source, **style, **named)
            plot.segment("x", "q3", "x", "high", source=source, **style, **named)
            renderer = plot.vbar(x="x", bottom="q1", top="q3", width=0.45, source=source, **style, **named)
            for key, size in (("low", 12), ("high", 12), ("median", 18)):
                plot.scatter("x", key, source=source, marker="dash", size=size, color="#333333", alpha=alpha, **named)
            if len(d["outlier_y"]):
                plot.scatter(d["outlier_x"], d["outlier_y"], size=5, **style, **named)
            tips = [("group", "@x"), ("median", "@median"), ("Q1", "@q1"), ("Q3", "@q3"), ("whiskers", "@low to @high")]
        case "heatmap" | "image":
            renderer, tips = _image(plot, d, layer.kind == "heatmap", alpha)
        case "reference_line":
            plot.add_layout(
                Span(
                    location=_timestamp(d["value"]),
                    dimension="height" if d["axis"] == "x" else "width",
                    line_color=color,
                    line_alpha=alpha,
                    line_width=d["width"],
                )
            )
            return
        case "rectangle":
            plot.add_layout(
                BoxAnnotation(
                    left=_timestamp(d["x0"]),
                    right=_timestamp(d["x1"]),
                    bottom=_timestamp(d["y0"]),
                    top=_timestamp(d["y1"]),
                    fill_color=color,
                    fill_alpha=alpha,
                    line_alpha=0,
                )
            )
            return
        case "polygon":
            plot.patch(d["x"], d["y"], fill_color=color, fill_alpha=alpha, line_color=color, line_alpha=alpha)
            return
        case "labels":
            source = {key: d[key] for key in ("x", "y", "text")}
            plot.add_layout(
                LabelSet(
                    x="x",
                    y="y",
                    text="text",
                    source=ColumnDataSource(source),
                    text_color=color,
                    text_alpha=alpha,
                    text_font_size=f"{d['size']}px",
                    text_align="center",
                )
            )
            return
        case _:
            raise ValueError(f"unsupported layer: {layer.kind}")

    if hover and layer.hover:
        plot.add_tools(HoverTool(renderers=[renderer], tooltips=tips))


def _image(
    plot: figure, data: dict[str, Any], scalar: bool, opacity: float
) -> tuple[GlyphRenderer, list[tuple[str, str]]]:
    left, right, bottom, top = data["extent"]
    pixels = data["pixels"]
    options = {"x": left, "y": bottom, "dw": right - left, "dh": top - bottom, "global_alpha": opacity}
    tips = [("x", "$x"), ("y", "$y")]
    renderer: GlyphRenderer
    if scalar:
        mapper = LinearColorMapper(palette=data["palette"], low=data["low"], high=data["high"], nan_color="#00000000")
        renderer = plot.image(image=[pixels], color_mapper=mapper, **options)
        if data["colorbar"]:
            plot.add_layout(ColorBar(color_mapper=mapper), "right")
        tips.append(("value", "@image"))
    else:
        if pixels.shape[2] == 3:
            pixels = np.concatenate((pixels, np.full((*pixels.shape[:2], 1), 255, dtype=np.uint8)), axis=2)
        packed = pixels.view("<u4").reshape(pixels.shape[:2]).astype(np.uint32, copy=False)
        renderer = plot.image_rgba(image=[packed], **options)
    return renderer, tips


def _build_subplot(placement: _Placement, ranges: tuple[Range, Range], axes: tuple[_Axis, _Axis]) -> figure:
    subplot = placement.subplot
    options: dict[str, Any] = {
        "x_axis_type": "datetime" if axes[0].kind == "datetime" else "auto",
        "y_axis_type": "datetime" if axes[1].kind == "datetime" else "auto",
        "tools": "pan,wheel_zoom,box_zoom,reset,save",
    }
    plot = figure(
        title=subplot.title or None,
        width=_CELL_WIDTH * placement.colspan + _GAP * (placement.colspan - 1),
        height=_CELL_HEIGHT * placement.rowspan + _GAP * (placement.rowspan - 1),
        x_range=ranges[0],
        y_range=ranges[1],
        **options,
    )
    plot.xaxis.axis_label = subplot.x_label
    plot.yaxis.axis_label = subplot.y_label
    for layer in subplot._layers:
        _layer(plot, layer, subplot.legend, subplot.hover)
    for legend in plot.legend:
        legend.click_policy = "hide"
    return plot


def render_grid(rows: int, cols: int, placements: list[_Placement], state: _GridAxes) -> GridBox:
    """Build a Bokeh grid with positioned panels and shared ranges."""
    ranges: dict[int, Range] = {}

    def get_range(axis: _Axis) -> Range:
        key = id(axis)
        if key not in ranges:
            ranges[key] = _range(axis)
        return ranges[key]

    plots: dict[Subplot, figure] = {}
    children: list[tuple[UIElement, int, int] | tuple[UIElement, int, int, int, int]] = []
    occupied: set[tuple[int, int]] = set()
    for placement in placements:
        axes = state.axes[placement.subplot]
        plot = _build_subplot(placement, (get_range(axes[0]), get_range(axes[1])), axes)
        plots[placement.subplot] = plot
        children.append((plot, placement.row, placement.col, placement.rowspan, placement.colspan))
        occupied.update(_cells(placement.row, placement.col, placement.rowspan, placement.colspan))

    # Ranges without finite shared data can still autorange together after native customization.
    for index, groups in enumerate(state.links):
        for group in groups:
            shared_range = ranges[id(state.axes[group[0]][index])]
            if isinstance(shared_range, DataRange1d):
                shared_range.renderers = list(chain.from_iterable(plots[subplot].renderers for subplot in group))

    for row, col in sorted(_cells(0, 0, rows, cols) - occupied):
        children.append((Spacer(width=_CELL_WIDTH, height=_CELL_HEIGHT), row, col))
    options: dict[str, Any] = {"spacing": _GAP}
    return GridBox(children=children, **options)


def render_html(report: Figure, resources: Resources) -> str:
    """Serialize a Bokeh report and its resources once."""
    children = [grid.to_native() for grid in report._grids]
    if report._tabs:
        tabs = [
            TabPanel(title=tab.title, child=column(*(grid.to_native() for grid in tab._grids))) for tab in report._tabs
        ]
        children.append(Tabs(tabs=tabs))
    layout = column(*children)
    return file_html(layout, INLINE if resources == "inline" else CDN, title=report.title)
