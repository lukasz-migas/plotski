"""Object-oriented layout and standalone HTML reports."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from numbers import Integral
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from plotski._plot_data import Limits
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


class Grid:
    """A fixed-size grid of subplots with optional spans and linked axes."""

    def __init__(self, rows: int, cols: int, *, backend: Backend = "bokeh") -> None:
        _check_backend(backend)
        self._rows = _integer(rows, "rows", 1)
        self._cols = _integer(cols, "cols", 1)
        self._backend = backend
        self._placements: dict[tuple[int, int], _Placement] = {}
        self._occupied: set[tuple[int, int]] = set()
        self._links: tuple[list[set[Subplot]], list[set[Subplot]]] = ([], [])
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
        return subplot

    def link_axes(self, *subplots: Subplot, x: bool = True, y: bool = False) -> Grid:
        """Share ranges among two or more subplots belonging to this grid."""
        if not x and not y:
            raise ValueError("select at least one axis to link")
        members = set(subplots)
        if len(members) < 2 or len(members) != len(subplots):
            raise ValueError("linking requires at least two distinct subplots")
        if not members <= {placement.subplot for placement in self._placements.values()}:
            raise ValueError("all linked subplots must belong to this grid")

        pending = (self._links[0].copy(), self._links[1].copy())
        for i, enabled in enumerate((x, y)):
            if enabled:
                groups = pending[i]
                overlaps = [group for group in groups if group & members]
                merged = members.union(*overlaps)
                _merge_axes([subplot._axis(i) for subplot in merged], linked=True)
                groups[:] = [group for group in groups if group not in overlaps]
                groups.append(merged)
        self._links = pending
        return self

    def configure_native(self, callback: Callable[[_NativeGrid], None] | None) -> Grid:
        """Set or clear a callback that customizes the freshly built native grid."""
        self._customize = callback
        return self

    def _axes(self, placements: list[_Placement]) -> _GridAxes:
        subplots = [placement.subplot for placement in placements]
        axes = {subplot: (subplot._axis(0), subplot._axis(1)) for subplot in subplots}
        links: tuple[list[tuple[Subplot, ...]], list[tuple[Subplot, ...]]] = ([], [])
        for index, groups in enumerate(self._links):
            for group in groups:
                ordered = tuple(subplot for subplot in subplots if subplot in group)
                shared = _merge_axes([axes[subplot][index] for subplot in ordered], linked=True)
                links[index].append(ordered)
                for subplot in ordered:
                    pair = axes[subplot]
                    axes[subplot] = (shared, pair[1]) if index == 0 else (pair[0], shared)
        return _GridAxes(axes, links)

    def to_native(self) -> _NativeGrid:
        """Build a fresh Bokeh GridBox or Plotly Figure and apply customization."""
        placements = [self._placements[key] for key in sorted(self._placements)]
        axes = self._axes(placements)
        native: _NativeGrid
        if self.backend == "bokeh":
            from plotski._bokeh import render_grid as render_bokeh

            native = render_bokeh(self.rows, self.cols, placements, axes)
        else:
            from plotski._plotly import render_grid as render_plotly

            native = render_plotly(self.rows, self.cols, placements, axes)
        if self._customize is not None:
            self._customize(native)
        return native


def _cells(row: int, col: int, rowspan: int, colspan: int) -> set[tuple[int, int]]:
    return {(i, j) for i in range(row, row + rowspan) for j in range(col, col + colspan)}


class _Page:
    def __init__(self, backend: Backend) -> None:
        _check_backend(backend)
        self._backend = backend
        self._grids: list[Grid] = []

    @property
    def backend(self) -> Backend:
        """Return the backend used throughout the report."""
        return self._backend

    def add_grid(self, rows: int, cols: int) -> Grid:
        """Append a fixed-size grid and return it for adding subplots."""
        grid = Grid(rows, cols, backend=self.backend)
        self._grids.append(grid)
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
    ) -> Subplot:
        """Append a standalone subplot outside any explicit grid."""
        grid = Grid(1, 1, backend=self.backend)
        subplot = grid.add_subplot(
            title=title,
            x_label=x_label,
            y_label=y_label,
            x_limits=x_limits,
            y_limits=y_limits,
            legend=legend,
            hover=hover,
        )
        self._grids.append(grid)
        return subplot


class Tab(_Page):
    """A named page of plots and grids within a figure."""

    def __init__(self, title: str, *, backend: Backend = "bokeh") -> None:
        super().__init__(backend)
        self.title = title


class Figure(_Page):
    """An interactive HTML report using one rendering backend."""

    def __init__(self, *, backend: Backend = "bokeh", title: str = "Plotski") -> None:
        super().__init__(backend)
        self.title = title
        self._tabs: list[Tab] = []

    def add_tab(self, title: str) -> Tab:
        """Append a named tab and return it for adding plots and grids."""
        if not title.strip():
            raise ValueError("tab title must not be empty")
        tab = Tab(title, backend=self.backend)
        self._tabs.append(tab)
        return tab

    def to_html(self, *, resources: Resources = "inline") -> str:
        """Render a full HTML document with inline or CDN JavaScript resources."""
        if resources not in ("inline", "cdn"):
            raise ValueError("resources must be 'inline' or 'cdn'")
        if self.backend == "bokeh":
            from plotski._bokeh import render_html as render_bokeh

            return render_bokeh(self, resources)
        from plotski._plotly import render_html as render_plotly

        return render_plotly(self, resources)

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
