"""Object-oriented layout and standalone HTML reports."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from html import escape
from numbers import Integral
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from numpy import ndarray

from plotski._plot_data import Limits, selection_ids
from plotski.subplot import Subplot, _Axis, _merge_axes

if TYPE_CHECKING:
    from bokeh.models import GridBox
    from plotly.graph_objects import Figure as PlotlyFigure

    _NativeGrid: TypeAlias = GridBox | PlotlyFigure
else:
    _NativeGrid = Any

Backend = Literal["bokeh", "plotly"]
Resources = Literal["inline", "cdn"]


def _check_backend(backend: Backend) -> None:
    if backend not in ("bokeh", "plotly"):
        raise ValueError("backend must be 'bokeh' or 'plotly'")
    if backend == "plotly":
        try:
            import plotly  # noqa: F401
        except ModuleNotFoundError as exc:
            if exc.name != "plotly":
                raise
            raise ImportError(
                "Plotly support requires the optional extra. Install it with pip install 'plotski[plotly]'."
            ) from exc


def _integer(value: int, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return int(value)


@dataclass(frozen=True)
class _Placement:
    subplot: Subplot
    row: int
    col: int
    rowspan: int
    colspan: int


@dataclass(frozen=True)
class _GridAxes:
    axes: dict[Subplot, tuple[_Axis, _Axis]]
    links: tuple[list[tuple[Subplot, ...]], list[tuple[Subplot, ...]]]


_AxisLinks: TypeAlias = tuple[list[set[Subplot]], list[set[Subplot]]]


def _join_group(groups: list[set[Subplot]], members: set[Subplot]) -> None:
    overlapping = [group for group in groups if group & members]
    merged = members.union(*overlapping)
    groups[:] = [group for group in groups if group not in overlapping]
    groups.append(merged)


def _add_axis_links(
    links: _AxisLinks, subplots: set[Subplot], members: tuple[Subplot, ...], x: bool, y: bool
) -> _AxisLinks:
    if not x and not y:
        raise ValueError("select at least one axis to link")
    unique = set(members)
    if len(unique) < 2 or len(unique) != len(members):
        raise ValueError("linking requires at least two distinct subplots")
    if not unique <= subplots:
        raise ValueError("all linked subplots must belong to this grid or figure")
    pending = (links[0].copy(), links[1].copy())
    for index, enabled in enumerate((x, y)):
        if enabled:
            _join_group(pending[index], unique)
    return pending


def _resolve_axes(subplots: list[Subplot], groups: _AxisLinks) -> _GridAxes:
    axes = {subplot: (subplot._axis(0), subplot._axis(1)) for subplot in subplots}
    links: tuple[list[tuple[Subplot, ...]], list[tuple[Subplot, ...]]] = ([], [])
    for index, dimension in enumerate(groups):
        for group in dimension:
            ordered = tuple(subplot for subplot in subplots if subplot in group)
            shared = _merge_axes([axes[subplot][index] for subplot in ordered], linked=True)
            links[index].append(ordered)
            for subplot in ordered:
                pair = axes[subplot]
                axes[subplot] = (shared, pair[1]) if index == 0 else (pair[0], shared)
    return _GridAxes(axes, links)


class Grid:
    """A fixed-size grid of subplots with optional spans and linked axes."""

    def __init__(
        self,
        rows: int,
        cols: int,
        *,
        backend: Backend = "bokeh",
        cell_width: int | None = None,
        cell_height: int | None = None,
    ) -> None:
        _check_backend(backend)
        self._rows = _integer(rows, "rows", 1)
        self._cols = _integer(cols, "cols", 1)
        self._backend = backend
        self._cell_width = _integer(cell_width, "cell_width", 10) if cell_width is not None else None
        self._cell_height = _integer(cell_height, "cell_height", 10) if cell_height is not None else None
        self._placements: dict[tuple[int, int], _Placement] = {}
        self._occupied: set[tuple[int, int]] = set()
        self._links: _AxisLinks = ([], [])
        self._customize: Callable[[_NativeGrid], None] | None = None

    @property
    def backend(self) -> Backend:
        """Return the grid's rendering backend."""
        return self._backend

    @property
    def rows(self) -> int:
        """Return the grid's row count."""
        return self._rows

    @property
    def cols(self) -> int:
        """Return the grid's column count."""
        return self._cols

    def add_subplot(
        self,
        row: int | None = None,
        col: int | None = None,
        *,
        rowspan: int = 1,
        colspan: int = 1,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        x_limits: Limits | None = None,
        y_limits: Limits | None = None,
        legend: bool = True,
        hover: bool = True,
    ) -> Subplot:
        """Place a subplot at zero-based coordinates or in the first slot that fits."""
        subplot = Subplot(
            title=title,
            x_label=x_label,
            y_label=y_label,
            x_limits=x_limits,
            y_limits=y_limits,
            legend=legend,
            hover=hover,
        )
        rowspan, colspan = _integer(rowspan, "rowspan", 1), _integer(colspan, "colspan", 1)
        if (row is None) != (col is None):
            raise ValueError("provide both row and col, or omit both")
        if rowspan > self.rows or colspan > self.cols:
            raise ValueError("subplot span is outside the grid")
        if row is None and col is None:
            for i in range(self.rows - rowspan + 1):
                for j in range(self.cols - colspan + 1):
                    if self._occupied.isdisjoint(_cells(i, j, rowspan, colspan)):
                        return self._place(subplot, i, j, rowspan, colspan)
            raise ValueError("no available grid slot fits this subplot")
        assert row is not None and col is not None
        row, col = _integer(row, "row", 0), _integer(col, "col", 0)
        if row + rowspan > self.rows or col + colspan > self.cols:
            raise ValueError("subplot placement is outside the grid")
        if not self._occupied.isdisjoint(_cells(row, col, rowspan, colspan)):
            raise ValueError("subplot placement overlaps an occupied cell")
        return self._place(subplot, row, col, rowspan, colspan)

    def _place(self, subplot: Subplot, row: int, col: int, rowspan: int, colspan: int) -> Subplot:
        self._placements[row, col] = _Placement(subplot, row, col, rowspan, colspan)
        self._occupied.update(_cells(row, col, rowspan, colspan))
        subplot._grid = self
        return subplot

    def link_axes(self, *subplots: Subplot, x: bool = True, y: bool = False) -> Grid:
        """Share ranges among two or more subplots belonging to this grid."""
        members = [placement.subplot for placement in self._ordered_placements()]
        pending = _add_axis_links(self._links, set(members), subplots, x, y)
        _resolve_axes(members, pending)
        self._links = pending
        return self

    def configure_native(self, callback: Callable[[_NativeGrid], None] | None) -> Grid:
        """Set or clear a callback that customizes the freshly built native grid."""
        self._customize = callback
        return self

    def _ordered_placements(self) -> list[_Placement]:
        return [self._placements[key] for key in sorted(self._placements)]

    def to_native(self) -> _NativeGrid:
        """Build a fresh Bokeh GridBox or Plotly Figure and apply customization."""
        placements = self._ordered_placements()
        axes = _resolve_axes([placement.subplot for placement in placements], self._links)
        return self._render(placements, axes)

    def _render(self, placements: list[_Placement], axes: _GridAxes) -> _NativeGrid:
        native: _NativeGrid
        if self.backend == "bokeh":
            from plotski._bokeh import render_grid as render_bokeh

            native = render_bokeh(
                self.rows, self.cols, placements, axes, cell_width=self._cell_width, cell_height=self._cell_height
            )
        else:
            from plotski._plotly import render_grid as render_plotly

            native = render_plotly(
                self.rows, self.cols, placements, axes, cell_width=self._cell_width, cell_height=self._cell_height
            )
        if self._customize is not None:
            self._customize(native)
        return native

    def save_image(self, path: str | Path, *, scale: float = 1) -> Path:
        """Export the grid as PNG or SVG, inferring the format from the suffix."""
        from plotski._image_export import save_image

        return save_image(path, self.backend, self.to_native, scale)

    def _save_subplot(self, subplot: Subplot, path: str | Path, scale: float) -> Path:
        placement = next(item for item in self._placements.values() if item.subplot is subplot)
        grid = Grid(
            placement.rowspan,
            placement.colspan,
            backend=self.backend,
            cell_width=self._cell_width,
            cell_height=self._cell_height,
        )
        # Reuse the data and display settings without changing its original ownership.
        grid._placements[0, 0] = replace(placement, row=0, col=0)
        return grid.save_image(path, scale=scale)


def _cells(row: int, col: int, rowspan: int, colspan: int) -> set[tuple[int, int]]:
    return {(i, j) for i in range(row, row + rowspan) for j in range(col, col + colspan)}


@dataclass(frozen=True)
class _ReportText:
    text: str
    kind: Literal["paragraph", "heading", "caption"]


@dataclass(frozen=True)
class _ReportTable:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    selection_group: str | None
    ids: tuple[str, ...] | None


class _Page:
    def __init__(self, backend: Backend) -> None:
        _check_backend(backend)
        self._backend = backend
        self._blocks: list[Grid | _ReportText | _ReportTable] = []

    @property
    def backend(self) -> Backend:
        """Return the backend used throughout the report."""
        return self._backend

    def add_grid(self, rows: int, cols: int, *, cell_width: int | None = None, cell_height: int | None = None) -> Grid:
        """Append a fixed-size grid and return it for adding subplots."""
        grid = Grid(rows, cols, backend=self.backend, cell_width=cell_width, cell_height=cell_height)
        self._blocks.append(grid)
        return grid

    def add_subplot(
        self,
        *,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        x_limits: Limits | None = None,
        y_limits: Limits | None = None,
        legend: bool = True,
        hover: bool = True,
        width: int | None = None,
        height: int | None = None,
    ) -> Subplot:
        """Append a standalone subplot outside any explicit grid."""
        grid = Grid(1, 1, backend=self.backend, cell_width=width, cell_height=height)
        subplot = grid.add_subplot(
            title=title,
            x_label=x_label,
            y_label=y_label,
            x_limits=x_limits,
            y_limits=y_limits,
            legend=legend,
            hover=hover,
        )
        self._blocks.append(grid)
        return subplot

    def add_text(self, text: str, *, kind: Literal["paragraph", "heading", "caption"] = "paragraph") -> None:
        """Append plain text as a paragraph, heading, or plot caption."""
        if kind not in ("paragraph", "heading", "caption"):
            raise ValueError("text kind must be 'paragraph', 'heading', or 'caption'")
        self._blocks.append(_ReportText(text, kind))

    def add_table(
        self,
        columns: Mapping[str, Sequence[object] | ndarray],
        *,
        title: str = "",
        selection_group: str | None = None,
        ids: Sequence[str] | ndarray | None = None,
    ) -> None:
        """Append a table from named columns, optionally linking rows by ID."""
        if not columns or any(not isinstance(name, str) or not name.strip() for name in columns):
            raise ValueError("tables require nonempty column names")
        if any(isinstance(column, (str, bytes)) for column in columns.values()):
            raise ValueError("table columns must be sequences of cells")
        if len({len(column) for column in columns.values()}) != 1:
            raise ValueError("table columns must have the same length")
        rows = tuple(
            tuple("" if value is None else str(value) for value in row) for row in zip(*columns.values(), strict=True)
        )
        self._blocks.append(
            _ReportTable(title, tuple(columns), rows, selection_group, selection_ids(len(rows), ids, selection_group))
        )


class Tab(_Page):
    """A named page of plots and grids within a figure."""

    def __init__(self, title: str, *, backend: Backend = "bokeh") -> None:
        super().__init__(backend)
        self.title = title


class Figure(_Page):
    """An interactive HTML report using one rendering backend."""

    def __init__(self, *, backend: Backend = "bokeh", title: str = "Plotski", lazy_tabs: bool = False) -> None:
        super().__init__(backend)
        self.title = title
        self.lazy_tabs = lazy_tabs
        self._tabs: list[Tab] = []
        self._links: _AxisLinks = ([], [])

    def add_tab(self, title: str) -> Tab:
        """Append a named tab and return it for adding plots and grids."""
        if not title.strip():
            raise ValueError("tab title must not be empty")
        tab = Tab(title, backend=self.backend)
        self._tabs.append(tab)
        return tab

    def _subplots(self) -> dict[Subplot, Grid]:
        return {
            placement.subplot: grid
            for page in (self, *self._tabs)
            for grid in page._blocks
            if isinstance(grid, Grid)
            for placement in grid._ordered_placements()
        }

    def link_axes(self, *subplots: Subplot, x: bool = True, y: bool = False) -> Figure:
        """Synchronize numeric or date axes across grids and tabs in the report."""
        owners = self._subplots()
        pending = _add_axis_links(self._links, set(owners), subplots, x, y)
        self._report_axes(owners, pending)
        self._links = pending
        return self

    def _report_axes(
        self, owners: dict[Subplot, Grid], report_links: _AxisLinks
    ) -> tuple[dict[Grid, _GridAxes], dict[tuple[Subplot, int], str]]:
        all_links: _AxisLinks = ([], [])
        grids = dict.fromkeys(owners.values())
        for index in range(2):
            for grid in grids:
                for members in grid._links[index]:
                    _join_group(all_links[index], members)
            for members in report_links[index]:
                _join_group(all_links[index], members)
        resolved = _resolve_axes(list(owners), all_links)
        cross_grid: dict[tuple[Subplot, int], str] = {}
        for index, groups in enumerate(resolved.links):
            for number, group in enumerate(groups):
                if resolved.axes[group[0]][index].kind == "category" and any(
                    members.intersection(group) for members in report_links[index]
                ):
                    raise ValueError("report-level links require numeric or date axes")
                if len({owners[subplot] for subplot in group}) > 1:
                    cross_grid.update(((subplot, index), f"{index}-{number}") for subplot in group)

        by_grid = {}
        for grid in grids:
            members = [placement.subplot for placement in grid._ordered_placements()]
            links: tuple[list[tuple[Subplot, ...]], list[tuple[Subplot, ...]]] = ([], [])
            for index, groups in enumerate(resolved.links):
                for group in groups:
                    local = tuple(subplot for subplot in group if owners[subplot] is grid)
                    if len(local) > 1:
                        links[index].append(local)
            by_grid[grid] = _GridAxes({subplot: resolved.axes[subplot] for subplot in members}, links)
        return by_grid, cross_grid

    def html_resources(self, *, resources: Resources = "inline") -> str:
        """Return the backend asset tags for use with resource-free HTML fragments."""
        from plotski._report import html_resources

        return html_resources(self.backend, resources)

    def to_html_fragment(self, *, resources: Resources | None = "inline") -> str:
        """Render an embeddable report, optionally using assets loaded by the host."""
        from plotski._report import render_fragment

        assets, fragment = render_fragment(self, resources)
        return assets + fragment

    def to_html(self, *, resources: Resources = "inline") -> str:
        """Render a full HTML document with inline or CDN JavaScript resources."""
        from plotski._report import render_fragment

        if resources not in ("inline", "cdn"):
            raise ValueError("resources must be 'inline' or 'cdn'")
        assets, fragment = render_fragment(self, resources)
        return (
            '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{escape(self.title)}</title>\n{assets}</head>\n<body>{fragment}</body></html>"
        )

    def _repr_html_(self) -> str:
        """Display an isolated offline report in a trusted notebook."""
        return (
            f'<iframe title="{escape(self.title)}" sandbox="allow-scripts" '
            f'style="border:0;width:100%;height:650px" srcdoc="{escape(self.to_html())}"></iframe>'
        )

    def save(self, path: str | Path, *, show: bool = False, resources: Resources = "inline") -> Path:
        """Write the report to a UTF-8 HTML file and optionally open it."""
        destination = Path(path)
        destination.write_text(self.to_html(resources=resources), encoding="utf-8")
        if show:
            webbrowser.open_new_tab(destination.resolve().as_uri())
        return destination

    def show(self, *, resources: Resources = "inline") -> Path:
        """Open a temporary HTML report in the default browser and return its path."""
        html = self.to_html(resources=resources)
        with NamedTemporaryFile(mode="w", suffix=".html", encoding="utf-8", delete=False) as temp:
            temp.write(html)
        path = Path(temp.name)
        webbrowser.open_new_tab(path.resolve().as_uri())
        return path
