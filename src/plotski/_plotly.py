"""Plotly rendering for the shared plotting interface."""

from __future__ import annotations

from html import escape
from math import log10
from typing import Any

import numpy as np
from plotly import graph_objects as go
from plotly.subplots import make_subplots

from plotski._plot_data import Layer
from plotski.figure import _GridAxes, _Placement
from plotski.subplot import _Axis


def _axis_reference(figure: go.Figure, placement: _Placement, index: int) -> str:
    native = figure.get_subplot(placement.row + 1, placement.col + 1)
    axis = native.xaxis if index == 0 else native.yaxis
    return axis.plotly_name.replace("axis", "")


def _axis_options(axis: _Axis, label: str, tick_format: str | None) -> dict[str, Any]:
    options: dict[str, Any] = {
        "title_text": escape(label),
        "type": {"datetime": "date", "category": "category"}.get(axis.kind or "linear", axis.scale),
        "autorange": axis.limits is None,
    }
    if axis.limits is not None:
        options["range"] = tuple(map(log10, axis.limits)) if axis.scale == "log" else axis.limits
    elif axis.reverse and axis.kind != "category":
        options["autorange"] = "reversed"
    if axis.kind == "category":
        categories = axis.categories[::-1] if axis.reverse else axis.categories
        options.update(categoryorder="array", categoryarray=categories, showgrid=False)
    if tick_format is not None:
        options["tickformat"] = tick_format
    return options


def _error_y(layer: Layer) -> dict[str, Any] | None:
    if (errors := layer.data.get("errors")) is None:
        return None
    lower, upper = errors
    return {"type": "data", "symmetric": False, "array": upper, "arrayminus": lower, "color": layer.color}


def _layer(figure: go.Figure, layer: Layer, placement: _Placement, series: int) -> None:
    d = layer.data
    subplot = placement.subplot
    where = {"row": placement.row + 1, "col": placement.col + 1}
    color, alpha = layer.color, layer.opacity
    hover = layer.hover and subplot.hover
    trace_style = {
        "name": escape(layer.label) if layer.label else "",
        "showlegend": bool(subplot.legend and layer.label),
        "legendgroup": f"{placement.row}-{placement.col}-{series}",
        "opacity": alpha,
        "hoverinfo": "x+y+name" if hover else "skip",
    }
    if layer.kind == "line":
        trace = go.Scatter(x=d["x"], y=d["y"], mode="lines", line={"color": color, "width": d["width"]}, **trace_style)
    elif layer.kind == "scatter":
        selection: dict[str, Any] = {}
        if d["selection_group"] is not None:
            selection = {
                "ids": d["ids"],
                "meta": {"plotski_selection": d["selection_group"]},
                "selected": {"marker": {"size": d["size"] + 3}},
                "unselected": {"marker": {"opacity": 0.25}},
            }
            if not hover:
                trace_style["hoverinfo"] = "none"
        trace = go.Scatter(
            x=d["x"],
            y=d["y"],
            mode="markers",
            marker={"color": color, "size": d["size"]},
            error_y=_error_y(layer),
            **trace_style,
            **selection,
        )
    elif layer.kind == "segments":
        x = [
            value
            for start, end in zip(d["x0"].tolist(), d["x1"].tolist(), strict=False)
            for value in (start, end, None)
        ]
        y = [
            value
            for start, end in zip(d["y0"].tolist(), d["y1"].tolist(), strict=False)
            for value in (start, end, None)
        ]
        trace = go.Scatter(x=x, y=y, mode="lines", line={"color": color, "width": d["width"]}, **trace_style)
    elif layer.kind == "bar":
        offset = d["offset"] - d["width"] / 2 if d.get("offset") else None
        base = d.get("base")
        trace = go.Bar(
            x=d["x"],
            y=d["y"],
            width=d["width"],
            marker_color=color,
            offset=offset,
            error_y=_error_y(layer),
            base=base if base is not None and np.any(base) else None,
            **trace_style,
        )
    elif layer.kind == "boxplot":
        # Whiskers and outliers come from the same precomputed statistics as Bokeh.
        group = trace_style["legendgroup"]
        figure.add_trace(
            go.Box(
                x=d["x"],
                q1=d["q1"],
                median=d["median"],
                q3=d["q3"],
                lowerfence=d["low"],
                upperfence=d["high"],
                orientation="v",
                boxpoints=False,
                line_color=color,
                fillcolor=color,
                hoveron="boxes",
                **trace_style,
            ),
            **where,
        )
        if len(d["outlier_y"]):
            figure.add_trace(
                go.Scatter(
                    x=d["outlier_x"],
                    y=d["outlier_y"],
                    mode="markers",
                    marker={"color": color, "size": 5},
                    name=trace_style["name"],
                    legendgroup=group,
                    showlegend=False,
                    opacity=alpha,
                    hoverinfo=trace_style["hoverinfo"],
                ),
                **where,
            )
        return
    elif layer.kind == "area":
        figure.add_trace(
            go.Scatter(
                x=d["x"],
                y=d["lower"],
                mode="lines",
                line_width=0,
                showlegend=False,
                legendgroup=trace_style["legendgroup"],
                hoverinfo="skip",
            ),
            **where,
        )
        rgb = ", ".join(str(int(color[i : i + 2], 16)) for i in (1, 3, 5))
        trace_style.pop("opacity")
        trace = go.Scatter(
            x=d["x"],
            y=d["upper"],
            mode="lines",
            line_width=0,
            fill="tonexty",
            fillcolor=f"rgba({rgb}, {alpha})",
            **trace_style,
        )
    elif layer.kind in ("heatmap", "image"):
        trace = _image(layer, hover)
    elif layer.kind == "reference_line":
        line = {"color": color, "width": d["width"]}
        if d["axis"] == "x":
            figure.add_vline(x=d["value"], line=line, opacity=alpha, exclude_empty_subplots=False, **where)
        else:
            figure.add_hline(y=d["value"], line=line, opacity=alpha, exclude_empty_subplots=False, **where)
        return
    elif layer.kind == "rectangle":
        figure.add_shape(
            type="rect",
            x0=d["x0"],
            x1=d["x1"],
            y0=d["y0"],
            y1=d["y1"],
            fillcolor=color,
            opacity=alpha,
            line_width=0,
            **where,
        )
        return
    elif layer.kind == "polygon":
        trace = go.Scatter(
            x=np.append(d["x"], d["x"][0]),
            y=np.append(d["y"], d["y"][0]),
            mode="lines",
            fill="toself",
            fillcolor=color,
            line_color=color,
            **trace_style,
        )
    elif layer.kind == "labels":
        trace = go.Scatter(
            x=d["x"],
            y=d["y"],
            text=[escape(label) for label in d["text"]],
            mode="text",
            textfont={"color": color, "size": d["size"]},
            **trace_style,
        )
    else:
        raise ValueError(f"unsupported layer: {layer.kind}")
    if hover and (columns := d.get("hover_columns")):
        tips = [
            "<br>".join(f"{escape(name)}: {escape(value)}" for name, value in zip(columns, row, strict=True))
            for row in zip(*columns.values(), strict=True)
        ]
        if layer.kind == "segments":
            tips = [value for tip in tips for value in (tip, tip, "")]
        trace.update(hovertext=tips, hovertemplate="%{hovertext}<extra>%{fullData.name}</extra>")
    figure.add_trace(trace, **where)


def _image(layer: Layer, hover: bool) -> go.Heatmap | go.Image:
    d = layer.data
    left, _, bottom, _ = d["extent"]
    dx, dy = d["dx"], d["dy"]
    x0, y0 = left + dx / 2, bottom + dy / 2
    if layer.kind == "heatmap":
        return go.Heatmap(
            z=d["pixels"],
            x0=x0,
            dx=dx,
            y0=y0,
            dy=dy,
            opacity=layer.opacity,
            colorscale=d["palette"],
            zmin=d["low"],
            zmax=d["high"],
            showscale=d["colorbar"],
            hovertemplate="x: %{x}<br>y: %{y}<br>value: %{z}<extra></extra>" if hover else None,
            hoverinfo="all" if hover else "skip",
            hoverongaps=False,
        )
    return go.Image(
        z=d["pixels"],
        x0=x0,
        dx=dx,
        y0=y0,
        dy=dy,
        opacity=layer.opacity,
        colormodel="rgba256" if d["pixels"].shape[2] == 4 else "rgb",
        hovertemplate="x: %{x}<br>y: %{y}<extra></extra>" if hover else None,
        hoverinfo="all" if hover else "skip",
    )


def render_grid(
    rows: int,
    cols: int,
    placements: list[_Placement],
    state: _GridAxes,
    *,
    cell_width: int | None = None,
    cell_height: int | None = None,
) -> go.Figure:
    """Build a native Plotly figure with Cartesian subplot cells and matched axes."""
    height = (cell_height or 320) * rows + (55 if cell_height is None else 0)
    width = cell_width * cols if cell_width is not None else None
    dimensions = {"width": width, "height": height, "autosize": width is None}
    if not placements:
        return go.Figure(layout={**dimensions, "xaxis": {"visible": False}, "yaxis": {"visible": False}})
    specs: list[list[dict[str, int] | None]] = [[None for _ in range(cols)] for _ in range(rows)]
    for placement in placements:
        specs[placement.row][placement.col] = {"rowspan": placement.rowspan, "colspan": placement.colspan}
    fig = make_subplots(
        rows=rows,
        cols=cols,
        specs=specs,
        subplot_titles=[escape(placement.subplot.title) for placement in placements],
        vertical_spacing=min(65 / height, 0.5 / rows),
        horizontal_spacing=min(70 / (width or 440 * cols), 0.5 / cols),
    )
    fig.update_layout(**dimensions, barmode="overlay", margin={"t": 55, "b": 45, "l": 65, "r": 45})
    by_subplot = {placement.subplot: placement for placement in placements}
    for placement in placements:
        subplot = placement.subplot
        axes = state.axes[subplot]
        where = {"row": placement.row + 1, "col": placement.col + 1}
        fig.update_xaxes(**_axis_options(axes[0], subplot.x_label, subplot._axis_settings[0].tick_format), **where)
        # Image traces default to a reversed, scale-anchored y axis. The shared extent uses increasing y.
        fig.update_yaxes(
            **_axis_options(axes[1], subplot.y_label, subplot._axis_settings[1].tick_format), scaleanchor=False, **where
        )
        for index, layer in enumerate(subplot._render_layers()):
            _layer(fig, layer, placement, index)
    for index, groups in enumerate(state.links):
        update = fig.update_xaxes if index == 0 else fig.update_yaxes
        for anchor, *members in groups:
            reference = _axis_reference(fig, by_subplot[anchor], index)
            for subplot in members:
                placement = by_subplot[subplot]
                update(matches=reference, row=placement.row + 1, col=placement.col + 1)
    return fig
