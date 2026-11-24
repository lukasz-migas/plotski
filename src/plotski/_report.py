"""Shared HTML shell and native plot payloads for standalone reports."""

from __future__ import annotations

import json
from html import escape
from importlib.resources import files
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from plotski.figure import Backend, Figure, Grid, Resources, _GridAxes, _Page, _ReportTable, _ReportText
from plotski.subplot import Subplot

if TYPE_CHECKING:
    from bokeh.model import Model

_STYLE = """
.plotski-report {font-family: system-ui, sans-serif; color: #202124}
.plotski-report .plotski-grid {margin-block: .75rem; overflow-x: auto}
.plotski-report [role=tablist] {display: flex; flex-wrap: wrap; gap: .35rem; border-bottom: 1px solid #aaa}
.plotski-report [role=tab] {font: inherit; padding: .5rem .85rem; background: white; border: 1px solid transparent;
  cursor: pointer}
.plotski-report [role=tab][aria-selected=true] {color: #174a8b; border-bottom-color: currentColor; font-weight: 600}
.plotski-report [hidden] {display: none}
.plotski-report .plotski-text {white-space: pre-wrap}
.plotski-report .plotski-caption {font-size: .9em; color: #555}
.plotski-report table {margin-block: .75rem; border-collapse: collapse}
.plotski-report caption {font-weight: 600; text-align: left}
.plotski-report th, .plotski-report td {padding: .35em .65em; border-bottom: 1px solid #ddd; text-align: left}
.plotski-report tr[data-selection-id] {cursor: pointer}
.plotski-report tr.plotski-selected {background: #d9eaff}
.plotski-report .plotski-cell-button {font: inherit; color: inherit; background: transparent; border: 0; padding: 0;
  cursor: pointer}
"""


def html_resources(backend: Backend, resources: Resources, models: list[Model] | None = None) -> str:
    """Return the requested backend resource tags."""
    if resources not in ("inline", "cdn"):
        raise ValueError("resources must be 'inline' or 'cdn'")
    if backend == "bokeh":
        from bokeh.embed.bundle import bundle_for_objs_and_resources
        from bokeh.resources import CDN, INLINE

        javascript, css = bundle_for_objs_and_resources(models, INLINE if resources == "inline" else CDN)
        return css + javascript
    from plotly.offline import get_plotlyjs, get_plotlyjs_version

    if resources == "inline":
        return f"<script>{get_plotlyjs()}</script>"
    return f'<script src="https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js"></script>'


def _table(block: _ReportTable) -> str:
    caption = f"<caption>{escape(block.title)}</caption>" if block.title else ""
    header = "".join(f'<th scope="col">{escape(column)}</th>' for column in block.columns)
    rows = []
    for index, row in enumerate(block.rows):
        cells = [escape(value) for value in row]
        attributes = ""
        if block.ids is not None:
            attributes = f' data-selection-id="{escape(block.ids[index])}"'
            cells[0] = f'<button type="button" class="plotski-cell-button" aria-pressed="false">{cells[0]}</button>'
        content = "".join(f"<td>{cell}</td>" for cell in cells)
        rows.append(f"<tr{attributes}>{content}</tr>")
    group = f' data-selection-group="{escape(block.selection_group)}"' if block.selection_group is not None else ""
    return f"<table{group}>{caption}<thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _grid_payload(
    grid: Grid, state: _GridAxes, cross_grid: dict[tuple[Subplot, int], str], target: str, models: list[Model] | None
) -> dict[str, Any]:
    placements = grid._ordered_placements()
    native = grid._render(placements, state)
    axes: dict[str, str] = {}
    selection: dict[str, str] = {}
    if grid.backend == "bokeh":
        from bokeh.embed import json_item
        from bokeh.models import Plot, TapTool

        if models is not None:
            models.append(native)
        children = {(child[1], child[2]): child[0] for child in native.children}
        for placement in placements:
            plot = children.get((placement.row, placement.col))
            if not isinstance(plot, Plot):
                continue
            for index, axis in enumerate((plot.x_range, plot.y_range)):
                if (group := cross_grid.get((placement.subplot, index))) is not None:
                    axes[axis.id] = group
            for renderer in plot.renderers:
                for tag in renderer.tags:
                    if isinstance(tag, dict) and "plotski_selection" in tag:
                        selection[renderer.data_source.id] = tag["plotski_selection"]
            tap = plot.toolbar.active_tap
            if isinstance(tap, TapTool) and "plotski_selection" in tap.tags:
                tap.behavior = "inspect"
                tap.tags.append({"plotski_target": target})
        payload = json_item(native, target)
    else:
        from plotly.io import to_json

        for placement in placements:
            for index in range(2):
                if (group := cross_grid.get((placement.subplot, index))) is not None:
                    plot = native.get_subplot(placement.row + 1, placement.col + 1)
                    axis = plot.xaxis if index == 0 else plot.yaxis
                    axes[axis.plotly_name] = group
        for index, trace in enumerate(native.data):
            if isinstance(trace.meta, dict) and "plotski_selection" in trace.meta:
                selection[str(index)] = trace.meta["plotski_selection"]
        payload = json.loads(to_json(native, remove_uids=False))
        # Match the grid's ordinary HTML sizing when the caller left width automatic.
        payload["config"] = {"responsive": True}
    return {"plot": payload, "axes": axes, "selection": selection}


def render_fragment(report: Figure, resources: Resources | None) -> tuple[str, str]:
    """Render a resource bundle and an isolated report with inert plot payloads."""
    root_id = f"plotski-{uuid4().hex}"
    states, cross_grid = report._report_axes(report._subplots(), report._links)
    models: list[Model] | None = [] if resources is not None and report.backend == "bokeh" else None
    grid_count = 0

    def render_page(page: _Page) -> str:
        nonlocal grid_count
        blocks = []
        for block in page._blocks:
            if isinstance(block, Grid):
                target = f"{root_id}-grid-{grid_count}"
                grid_count += 1
                state = states.get(block, _GridAxes({}, ([], [])))
                payload = _grid_payload(block, state, cross_grid, target, models)
                encoded = json.dumps(payload, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
                min_width = 230 * block.cols if block.backend == "plotly" and block._cell_width is None else 0
                blocks.append(
                    f'<div class="plotski-grid"><div id="{target}" style="min-width:{min_width}px"></div>'
                    f'<script type="application/json">{encoded}</script></div>'
                )
            elif isinstance(block, _ReportText):
                tag = "h2" if block.kind == "heading" else "p"
                blocks.append(f'<{tag} class="plotski-text plotski-{block.kind}">{escape(block.text)}</{tag}>')
            else:
                blocks.append(_table(block))
        return "".join(blocks)

    content = render_page(report)
    buttons, panels = [], []
    for index, tab in enumerate(report._tabs):
        selected = "true" if index == 0 else "false"
        tabindex = 0 if index == 0 else -1
        hidden = "" if index == 0 else " hidden"
        button, panel = f"{root_id}-tab-{index}", f"{root_id}-panel-{index}"
        buttons.append(
            f'<button type="button" role="tab" id="{button}" aria-controls="{panel}" '
            f'aria-selected="{selected}" tabindex="{tabindex}">{escape(tab.title)}</button>'
        )
        panels.append(
            f'<section role="tabpanel" id="{panel}" aria-labelledby="{button}" tabindex="0"{hidden}>'
            f"{render_page(tab)}</section>"
        )
    if buttons:
        content += '<div role="tablist" aria-label="Report tabs">' + "".join(buttons) + "</div>" + "".join(panels)
    lazy = "true" if report.lazy_tabs else "false"
    script = files("plotski").joinpath("_report.js").read_text(encoding="utf-8")
    assets = "" if resources is None else html_resources(report.backend, resources, models)
    return assets, (
        f'<main class="plotski-report" id="{root_id}" data-backend="{report.backend}" data-lazy-tabs="{lazy}">'
        f"<style>{_STYLE}</style>{content}<script>{script}</script></main>"
    )
