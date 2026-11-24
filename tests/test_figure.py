"""Shared interface tests against both native plotting backends."""

from __future__ import annotations

import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from bokeh.models import BoxAnnotation, ColorBar, FactorRange, HoverTool, LabelSet, Spacer, Span

from plotski import Figure, Grid, Subplot, Tab


@pytest.fixture(params=["bokeh", "plotly"])
def backend(request: pytest.FixtureRequest) -> str:
    name = request.param
    if name == "plotly":
        pytest.importorskip("plotly")
    return name


def test_sparse_grid_and_spans(backend: str) -> None:
    grid = Grid(3, 3, backend=backend)
    grid.add_subplot(colspan=2, title="Wide").line([0, 1], [2, 3])
    grid.add_subplot(1, 2, rowspan=2, title="Tall").scatter([1], [4])
    with pytest.raises(ValueError, match="overlaps"):
        grid.add_subplot(0, 1)
    with pytest.raises(ValueError, match="outside"):
        grid.add_subplot(2, 0, rowspan=2)
    with pytest.raises(ValueError, match="both row and col"):
        grid.add_subplot(0)
    with pytest.raises(ValueError, match="integer"):
        grid.add_subplot(rowspan=0)
    grid.add_subplot(title="Auto").bar(["a", "b"], [1, 2])

    native = grid.to_native()
    if backend == "bokeh":
        plots = [(plot.title.text, position) for plot, *position in native.children if not isinstance(plot, Spacer)]
        assert plots == [("Wide", [0, 0, 1, 2]), ("Auto", [0, 2, 1, 1]), ("Tall", [1, 2, 2, 1])]
        assert sum(isinstance(child[0], Spacer) for child in native.children) == 4
    else:
        assert [title.text for title in native.layout.annotations] == ["Wide", "Auto", "Tall"]
        assert native.get_subplot(2, 1) is None
        assert native.get_subplot(2, 3).yaxis.domain[0] == 0
        wide, auto = native.get_subplot(1, 1), native.get_subplot(1, 3)
        assert np.ptp(wide.xaxis.domain) > 2 * np.ptp(auto.xaxis.domain)


def test_axes_share_ranges_and_refresh_after_edits(backend: str) -> None:
    grid = Grid(2, 2, backend=backend)
    a = grid.add_subplot(title="Initial").line([0, 10], [1, 5])
    b = grid.add_subplot(y_limits=(-10, 20)).line([50, 60], [2, 8])
    c = grid.add_subplot().scatter([30], [4])
    grid.link_axes(a, b, y=True)
    grid.link_axes(b, c)
    a.title = "Edited"
    a.line([5, 90], [3, 4])

    native = grid.to_native()
    again = grid.to_native()
    assert native is not again
    if backend == "bokeh":
        p, q, r = (item[0] for item in native.children[:3])
        assert p.title.text == "Edited"
        assert p.x_range is q.x_range is r.x_range
        assert (p.x_range.start, p.x_range.end) == (0, 90)
        assert p.y_range is q.y_range and p.y_range is not r.y_range
        assert (p.y_range.start, p.y_range.end) == (-10, 20)
        assert len(p.renderers) == len(again.children[0][0].renderers) == 2
    else:
        assert native.layout.annotations[0].text == "Edited"
        assert native.layout.xaxis.range == (0, 90)
        assert native.layout.xaxis2.matches == native.layout.xaxis3.matches == "x"
        assert native.layout.yaxis.range == (-10, 20)
        assert native.layout.yaxis2.matches == "y"
        assert native.layout.yaxis3.matches is None
        assert len(native.data) == len(again.data) == 4


def test_link_validation_is_atomic(backend: str) -> None:
    grid = Grid(1, 3, backend=backend)
    a = grid.add_subplot(x_limits=(0, 2), y_limits=(0, 1)).line([0, 2], [0, 1])
    b = grid.add_subplot(y_limits=(1, 2)).line([1, 2], [1, 2])
    c = grid.add_subplot().bar(["a", "b"], [3, 4])

    with pytest.raises(ValueError, match="conflicting"):
        grid.link_axes(a, b, y=True)
    with pytest.raises(ValueError, match="incompatible"):
        grid.link_axes(a, c)
    with pytest.raises(ValueError, match="belong"):
        grid.link_axes(a, Subplot())
    with pytest.raises(ValueError, match="distinct"):
        grid.link_axes(a, a)

    native = grid.to_native()
    if backend == "bokeh":
        assert native.children[0][0].x_range is not native.children[1][0].x_range
    else:
        assert native.layout.xaxis2.matches is None


def test_datetime_and_category_axes(backend: str) -> None:
    grid = Grid(2, 2, backend=backend)
    a = grid.add_subplot().line([datetime(2025, 1, 1, tzinfo=timezone.utc), date(2025, 1, 2)], [10, 20])
    a.reference_line(date(2025, 1, 1))
    b = grid.add_subplot().line(np.array(["2025-01-03", "2025-01-04"], dtype="datetime64[D]"), [2, 4])
    c = grid.add_subplot().bar(np.array(["z", "a"], dtype=object), [3, 1])
    d = grid.add_subplot().bar(["m", "z"], [2, 2])
    grid.link_axes(a, b).link_axes(c, d)
    native = grid.to_native()
    if backend == "bokeh":
        p, q, r, s = (item[0] for item in native.children)
        assert p.x_range is q.x_range
        assert p.x_range.end - p.x_range.start == 3 * 86_400_000
        assert isinstance(r.x_range, FactorRange)
        assert r.x_range is s.x_range and r.x_range.factors == ["z", "a", "m"]
    else:
        assert native.layout.xaxis.type == "date"
        assert native.layout.xaxis.range == (datetime(2025, 1, 1), datetime(2025, 1, 4))
        assert native.layout.xaxis2.matches == "x"
        assert native.layout.xaxis3.categoryarray == ("z", "a", "m")
        assert native.layout.xaxis4.matches == "x3"


def test_charts_and_annotations(backend: str) -> None:
    grid = Grid(2, 2, backend=backend)
    p = grid.add_subplot(0, 0, title="Scientific")
    p.line([1, 2, 3], [2, 1, 3], label="line").scatter([1, 3], [2, 7], hover=False)
    p.segments([1, 3], [0, 0], [1, 3], [3, 4], label="segments")
    p.band([1, 2, 3], [1, 1, 1], [2, 2, 2]).area([0, 2, 3], [3, -2, 3], label="area")
    p.reference_line(1).reference_line(1, axis="y").rectangle(1, 1, 2, 3)
    p.polygon([1, 2, 3], [2, 3, 1]).labels([2], [3], ["two"])
    grid.add_subplot(0, 1, legend=False, hover=False).bar(["a", "b"], [3, 4], label="bars")
    grid.add_subplot(1, 0).histogram([0, 0.5, 1, 2.5], bins=[0, 1, 3], density=True)
    grid.add_subplot(1, 1).boxplot([1, 1, 1, 1, 100, 2], categories=["a"] * 5 + ["b"], label="box")
    native = grid.to_native()

    if backend == "bokeh":
        scientific, bars, hist, box = (item[0] for item in native.children)
        assert len(scientific.select(type=Span)) == 2
        assert any(shape.left == 1 for shape in scientific.select(type=BoxAnnotation))
        assert len(scientific.select(type=LabelSet)) == 1
        assert len(scientific.select(type=HoverTool)) == 3
        assert not bars.legend and not bars.select(type=HoverTool)
        np.testing.assert_allclose(hist.renderers[0].data_source.data["y"], [0.5, 0.25])
        assert box.legend[0].click_policy == "hide"
        assert len(box.legend[0].items[0].renderers) == 7
        np.testing.assert_allclose(box.renderers[-1].data_source.data["y"], [100])
    else:
        assert len(native.layout.shapes) == 3
        assert [shape.type for shape in native.layout.shapes] == ["line", "line", "rect"]
        assert any(
            trace.mode == "text" and trace.text == ("two",) for trace in native.select_traces({"type": "scatter"})
        )
        bars, hist = native.select_traces({"type": "bar"})
        assert bars.hoverinfo == "skip" and not bars.showlegend
        np.testing.assert_allclose(hist.y, [0.5, 0.25])
        np.testing.assert_allclose(hist.width, [1, 2])
        box = next(native.select_traces({"type": "box"}))
        np.testing.assert_allclose(box.median, [1, 2])
        assert box.legendgroup == native.data[-1].legendgroup
        np.testing.assert_allclose(native.data[-1].y, [100])


def test_images_preserve_extent_orientation_and_alpha(backend: str) -> None:
    grid = Grid(1, 2, backend=backend)
    extent = (10, 30, 100, 160)
    grid.add_subplot().heatmap([[1, np.nan], [3, 4]], extent=extent, z_min=0, z_max=6)
    pixels = np.array([[[255, 0, 0, 128]], [[0, 0, 255, 255]]], dtype=np.uint8)
    grid.add_subplot().image(pixels, extent=extent, origin="lower", opacity=0.5)
    native = grid.to_native()
    if backend == "bokeh":
        heat, image = (item[0] for item in native.children)
        heat_glyph = heat.renderers[0].glyph
        assert (heat_glyph.x, heat_glyph.y, heat_glyph.dw, heat_glyph.dh) == (10, 100, 20, 60)
        colorbar = next(iter(heat.select(type=ColorBar)))
        assert colorbar.color_mapper.low == 0 and colorbar.color_mapper.high == 6
        np.testing.assert_allclose(heat.renderers[0].data_source.data["image"][0], [[3, 4], [1, np.nan]])
        assert image.renderers[0].glyph.global_alpha == 0.5
        np.testing.assert_array_equal(image.renderers[0].data_source.data["image"][0], [[0x800000FF], [0xFFFF0000]])
    else:
        heat, image = native.data
        assert (heat.x0, heat.y0, heat.dx, heat.dy) == (15, 115, 10, 30)
        assert heat.showscale and (heat.zmin, heat.zmax) == (0, 6)
        np.testing.assert_allclose(heat.z, [[3, 4], [1, np.nan]])
        assert image.colormodel == "rgba256" and image.opacity == 0.5
        np.testing.assert_array_equal(image.z, pixels)
        assert native.layout.yaxis2.autorange is True and native.layout.yaxis2.scaleanchor is False


def test_export_and_native_callback(backend: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = Figure(backend=backend, title="All <samples>")
    first = report.add_subplot(title="Intro section")
    assert isinstance(first, Subplot)
    first.line([1, 2], [2, 4])
    tab = report.add_tab("A & B")
    assert isinstance(tab, Tab)
    grid = tab.add_grid(1, 1)
    panel = grid.add_subplot(title="Original chart").line([3, 4], [4, 8])

    def customize(native) -> None:
        if backend == "bokeh":
            native.children[0][0].title.text += " customized"
        else:
            native.layout.annotations[0].text += " customized"

    grid.configure_native(customize)
    report.add_tab("Empty tab").add_grid(1, 1)
    first_html = report.to_html()
    assert "<title>All &lt;samples&gt;</title>" in first_html
    assert "Original chart customized" in first_html
    assert first_html.index("Intro section") < first_html.index("Original chart")
    assert "Empty tab" in first_html
    if backend == "bokeh":
        assert first_html.count("BokehJS library") == 1
        assert "https://cdn.bokeh.org" in report.to_html(resources="cdn")
    else:
        assert first_html.count("* plotly.js v") == 1
        assert 'role="tablist"' in first_html
        assert 'id="panel-1" aria-labelledby="tab-1" tabindex="0" hidden' in first_html
        assert "https://cdn.plot.ly/" in report.to_html(resources="cdn")
    panel.title = "Edited chart"
    grid.configure_native(None)
    path = tmp_path / "report with spaces.html"
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open_new_tab", opened.append)
    assert report.save(path) == path
    assert not opened
    updated = path.read_text(encoding="utf-8")
    assert "Edited chart" in updated and "Original chart" not in updated
    assert report.save(path, show=True, resources="cdn") == path
    display_path = report.show(resources="cdn")
    try:
        assert opened == [path.resolve().as_uri(), display_path.resolve().as_uri()]
        assert "Edited chart" in display_path.read_text(encoding="utf-8")
    finally:
        display_path.unlink()


def test_invalid_chart_data_does_not_change_subplot(backend: str) -> None:
    grid = Grid(1, 1, backend=backend)
    panel = grid.add_subplot()
    with pytest.raises(ValueError, match="same length"):
        panel.line([1], [1, 2])
    with pytest.raises(ValueError, match="lower"):
        panel.band([1], [3], [2])
    with pytest.raises(ValueError, match="strictly increasing"):
        panel.histogram([3, 4], bins=[1, 2, 2])
    with pytest.raises(ValueError, match="shape"):
        panel.image([[1, 2, 3]])
    with pytest.raises(ValueError, match="extent"):
        panel.heatmap([[1]], extent=(4, 3, 1, 2))
    with pytest.raises(ValueError, match="integers"):
        panel.image([[[256, 1, 0]]])
    assert panel.line([0], [1]) is panel
    if backend == "bokeh":
        assert len(grid.to_native().children[0][0].renderers) == 1
    else:
        assert len(grid.to_native().data) == 1


def test_native_data_does_not_alias_report_data(backend: str) -> None:
    grid = Grid(1, 1, backend=backend)
    y = np.array([2.0, 4.0])
    grid.add_subplot().line([1, 2], y)
    y[0] = 100
    native = grid.to_native()
    again = grid.to_native()
    if backend == "bokeh":
        rendered = native.children[0][0].renderers[0].data_source.data["y"]
        repeated = again.children[0][0].renderers[0].data_source.data["y"]
    else:
        rendered = native.data[0].y
        repeated = again.data[0].y
    np.testing.assert_array_equal(rendered, [2, 4])
    assert not np.shares_memory(rendered, repeated)


def test_plotly_is_optional() -> None:
    code = """
import sys

class NoPlotly:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "plotly":
            raise ModuleNotFoundError("Plotly unavailable", name="plotly")

sys.meta_path.insert(0, NoPlotly())
from plotski import Figure

report = Figure()
report.add_subplot().line([0, 1], [1, 0])
assert "https://cdn.bokeh.org" in report.to_html(resources="cdn")
assert "plotly" not in sys.modules
try:
    Figure(backend="plotly")
except ImportError as error:
    assert "plotski[plotly]" in str(error)
else:
    raise AssertionError("expected an installation hint")
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
