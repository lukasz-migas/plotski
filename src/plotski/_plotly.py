"""Plotly rendering for the shared plotting interface."""

from __future__ import annotations

from html import escape
from typing import Any

import numpy as np
from plotly import graph_objects as go
from plotly.io import to_html
from plotly.offline import get_plotlyjs, get_plotlyjs_version
from plotly.subplots import make_subplots

from plotski._plot_data import Layer
from plotski.figure import Figure, Grid, Resources, _GridAxes, _Placement
from plotski.subplot import _Axis

_TAB_SCRIPT = """
const tablist = document.querySelector("[role=tablist]");
const tabs = Array.from(tablist.querySelectorAll("[role=tab]"));
function selectTab(tab, focus) {
    tabs.forEach(button => {
        const selected = button === tab;
        button.setAttribute("aria-selected", selected);
        button.tabIndex = selected ? 0 : -1;
        document.getElementById(button.getAttribute("aria-controls")).hidden = !selected;
    });
    if (focus) tab.focus();
    const panel = document.getElementById(tab.getAttribute("aria-controls"));
    requestAnimationFrame(() => {
        if (panel.hidden) return;
        panel.querySelectorAll(".plotly-graph-div").forEach(plot => {
            if (plot._fullLayout) Plotly.Plots.resize(plot).catch(() => {});
        });
    });
}
tabs.forEach(tab => tab.addEventListener("click", () => selectTab(tab, false)));
tablist.addEventListener("keydown", event => {
    const index = tabs.indexOf(event.target);
    if (index < 0) return;
    const next = {
        ArrowRight: (index + 1) % tabs.length,
        ArrowLeft: (index + tabs.length - 1) % tabs.length,
        Home: 0,
        End: tabs.length - 1
    }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    selectTab(tabs[next], true);
});
"""


def _axis_reference(figure: go.Figure, placement: _Placement, index: int) -> str:
    native = figure.get_subplot(placement.row + 1, placement.col + 1)
    axis = native.xaxis if index == 0 else native.yaxis
    return axis.plotly_name.replace("axis", "")


def _axis_options(axis: _Axis, label: str) -> dict[str, Any]:
    options: dict[str, Any] = {
        "title_text": escape(label),
        "type": {"datetime": "date", "category": "category"}.get(axis.kind or "linear", "linear"),
        "autorange": axis.limits is None,
    }
    if axis.limits is not None:
        options["range"] = axis.limits
    if axis.kind == "category":
        options.update(categoryorder="array", categoryarray=axis.categories, showgrid=False)
    return options


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
        trace = go.Scatter(
            x=d["x"], y=d["y"], mode="markers", marker={"color": color, "size": d["size"]}, **trace_style
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
        trace = go.Bar(x=d["x"], y=d["y"], width=d["width"], marker_color=color, **trace_style)
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


def render_grid(rows: int, cols: int, placements: list[_Placement], state: _GridAxes) -> go.Figure:
    """Build a native Plotly figure with Cartesian subplot cells and matched axes."""
    height = 320 * rows + 55
    if not placements:
        return go.Figure(
            layout={"height": height, "autosize": True, "xaxis": {"visible": False}, "yaxis": {"visible": False}}
        )
    specs: list[list[dict[str, int] | None]] = [[None for _ in range(cols)] for _ in range(rows)]
    for placement in placements:
        specs[placement.row][placement.col] = {"rowspan": placement.rowspan, "colspan": placement.colspan}
    fig = make_subplots(
        rows=rows,
        cols=cols,
        specs=specs,
        subplot_titles=[escape(placement.subplot.title) for placement in placements],
        vertical_spacing=65 / height,
        horizontal_spacing=70 / (440 * cols),
    )
    fig.update_layout(height=height, autosize=True, barmode="overlay", margin={"t": 55, "b": 45, "l": 65, "r": 45})
    by_subplot = {placement.subplot: placement for placement in placements}
    for placement in placements:
        subplot = placement.subplot
        axes = state.axes[subplot]
        where = {"row": placement.row + 1, "col": placement.col + 1}
        fig.update_xaxes(**_axis_options(axes[0], subplot.x_label), **where)
        # Image traces default to a reversed, scale-anchored y axis. The shared extent uses increasing y.
        fig.update_yaxes(**_axis_options(axes[1], subplot.y_label), scaleanchor=False, **where)
        for index, layer in enumerate(subplot._layers):
            _layer(fig, layer, placement, index)
    for index, groups in enumerate(state.links):
        update = fig.update_xaxes if index == 0 else fig.update_yaxes
        for anchor, *members in groups:
            reference = _axis_reference(fig, by_subplot[anchor], index)
            for subplot in members:
                placement = by_subplot[subplot]
                update(matches=reference, row=placement.row + 1, col=placement.col + 1)
    return fig


def render_html(report: Figure, resources: Resources) -> str:
    """Serialize all grids with one copy of Plotly.js and optional interactive tabs."""
    if resources == "inline":
        library = "<script>" + get_plotlyjs() + "</script>"
    else:
        library = f'<script src="https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js"></script>'

    def render_page(grids: list[Grid]) -> str:
        return "".join(
            '<div class="grid" style="min-width:'
            + str(230 * grid.cols)
            + 'px">'
            + to_html(grid.to_native(), full_html=False, include_plotlyjs=False, config={"responsive": True})
            + "</div>"
            for grid in grids
        )

    title = escape(report.title)
    content = render_page(report._grids)
    if report._tabs:
        buttons, panels = [], []
        for index, tab in enumerate(report._tabs):
            selected = "true" if index == 0 else "false"
            tabindex = 0 if index == 0 else -1
            hidden = "" if index == 0 else " hidden"
            buttons.append(
                f'<button type="button" role="tab" id="tab-{index}" aria-controls="panel-{index}" '
                f'aria-selected="{selected}" tabindex="{tabindex}">{escape(tab.title)}</button>'
            )
            panels.append(
                f'<section role="tabpanel" id="panel-{index}" aria-labelledby="tab-{index}" tabindex="0"{hidden}>'
                f"{render_page(tab._grids)}</section>"
            )
        content += '<div role="tablist" aria-label="Report tabs">' + "".join(buttons) + "</div>" + "".join(panels)
        content += f"<script>{_TAB_SCRIPT}</script>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
.grid {{ margin-block: 0.75rem; }}
[role=tablist] {{ display: flex; flex-wrap: wrap; gap: 0.35rem; border-bottom: 1px solid #aaa; }}
[role=tab] {{ font: inherit; padding: 0.5rem 0.85rem; background: white; border: 1px solid transparent; cursor: pointer; }}
[role=tab][aria-selected=true] {{ color: #174a8b; border-bottom-color: currentColor; font-weight: 600; }}
</style>
{library}
</head>
<body><main>{content}</main></body>
</html>
"""
