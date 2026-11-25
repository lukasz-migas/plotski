"""Opt-in browser checks for standalone reports and native image export."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest
from PIL import Image

from plotski import Figure, Grid
from plotski.figure import Backend

pytestmark = pytest.mark.skipif(
    os.environ.get("PLOTSKI_BROWSER_TESTS") != "1",
    reason="set PLOTSKI_BROWSER_TESTS=1 with Chrome, ChromeDriver, and the export extras installed",
)

_PLOT = """
const root = document.querySelectorAll(".plotski-report")[arguments[0]];
const grid = root.querySelectorAll(".plotski-grid")[arguments[1]];
const [target, script] = grid.children;
const payload = JSON.parse(script.textContent).plot;
const doc = globalThis.Bokeh?.documents.find(doc => doc.get_model_by_id(payload.root_id));
const plot = doc?.get_model_by_id(payload.root_id).children[0][0];
"""
_RANGE = (
    _PLOT
    + """
return plot ? [plot.x_range.start, plot.x_range.end] : Array.from(target._fullLayout.xaxis.range);
"""
)
_POINT = (
    _PLOT
    + """
if (plot) {
    function find(view) {
        if (view.model === plot) return view;
        for (const child of view.children()) {
            const found = find(child);
            if (found) return found;
        }
    }
    const view = Bokeh.index.find_one?.(plot) ?? Object.values(Bokeh.index).map(find).find(Boolean);
    const rect = view.canvas_view.events_el.getBoundingClientRect();
    return [rect.left + view.frame.x_scale.compute(2), rect.top + view.frame.y_scale.compute(4)];
}
const rect = target.querySelector(".scatterlayer .point").getBoundingClientRect();
return [rect.left + rect.width / 2, rect.top + rect.height / 2];
"""
)
_SELECTION = (
    _PLOT
    + """
return plot ? Array.from(plot.renderers[0].data_source.selected.indices) : target.data[0].selectedpoints;
"""
)


@pytest.fixture
def browser() -> Any:
    webdriver = pytest.importorskip("selenium.webdriver")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1300,900")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    with webdriver.Chrome(options=options) as driver:
        yield driver


@pytest.mark.parametrize("backend", ["bokeh", "plotly"])
def test_linked_report_and_independent_fragments(backend: Backend, browser: Any, tmp_path: Path) -> None:
    from selenium.webdriver.common.actions.action_builder import ActionBuilder
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait

    if backend == "plotly":
        pytest.importorskip("plotly")
    report = Figure(backend=backend, lazy_tabs=True)
    first = report.add_tab("Sample")
    plot = first.add_subplot(width=450, height=280)
    plot.scatter([2, 5], [4, 5], ids=["a", "b"], selection_group="peaks", hover_fields={"Peak": ["A", "B"]})
    first.add_table({"Peak": ["A", "B"]}, ids=["a", "b"], selection_group="peaks")
    separate_grid = first.add_grid(2, 1)
    comparison = separate_grid.add_subplot().line([0, 7], [0, 1])
    matched = separate_grid.add_subplot().line([1, 6], [1, 2])
    separate_grid.link_axes(comparison, matched)
    later = report.add_tab("Reference")
    target = later.add_subplot().scatter([3, 6], [4, 5], ids=["a", "a"], selection_group="peaks")
    report.link_axes(plot, comparison, target)
    other = Figure(backend=backend)
    other_tab = other.add_tab("Other report")
    other_tab.add_table({"Peak": ["Independent"]}, ids=["a"], selection_group="peaks")
    other_tab.add_subplot().scatter([7], [3], ids=["a"], selection_group="peaks")
    path = tmp_path / "embedded.html"
    path.write_text(
        "<!doctype html><html><head><meta charset=utf-8>"
        + report.html_resources()
        + "</head><body>"
        + report.to_html_fragment(resources=None)
        + other.to_html_fragment(resources=None)
        + "</body></html>",
        encoding="utf-8",
    )
    browser.get(path.as_uri())
    wait = WebDriverWait(browser, 12)
    ready = ".plotski-report:first-of-type .plotski-grid[data-plotski-ready]"
    wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ready)) == 2)
    assert browser.execute_script(_RANGE, 0, 0) == [0, 7]

    x, y = browser.execute_script(_POINT, 0, 0)
    actions = ActionBuilder(browser)
    actions.pointer_action.move_to_location(round(x), round(y)).click()
    actions.perform()
    wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".plotski-selected")) == 1)
    assert browser.find_element(By.CSS_SELECTOR, ".plotski-selected").text == "A"
    assert browser.execute_script(_SELECTION, 0, 0) == [0]
    assert not browser.execute_script(_SELECTION, 1, 0)
    actions = ActionBuilder(browser)
    actions.pointer_action.move_to_location(round(x) + 35, round(y)).click()
    actions.perform()
    assert browser.execute_script(_SELECTION, 0, 0) == [0]

    browser.execute_script(
        _PLOT
        + """
        return plot ? plot.x_range.setv({start: 1, end: 6}) : Plotly.relayout(target, {"xaxis.range": [1, 6]});
    """,
        0,
        0,
    )
    wait.until(lambda driver: driver.execute_script(_RANGE, 0, 1) == [1, 6])
    browser.execute_script(
        _PLOT
        + """
        if (plot) {
            const matched = doc.get_model_by_id(payload.root_id).children[1][0];
            return matched.x_range.setv({start: 2, end: 5});
        }
        return Plotly.relayout(target, {"xaxis2.range": [2, 5]});
    """,
        0,
        1,
    )
    wait.until(lambda driver: driver.execute_script(_RANGE, 0, 0) == [2, 5])
    tabs = browser.find_elements(By.CSS_SELECTOR, ".plotski-report:first-of-type [role=tab]")
    tabs[0].send_keys(Keys.ARROW_RIGHT)
    wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ready)) == 3)
    wait.until(lambda driver: driver.execute_script(_RANGE, 0, 2) == [2, 5])
    assert browser.execute_script(_SELECTION, 0, 2) == [0, 1]

    browser.execute_script(
        _PLOT
        + """
        return plot ? plot.x_range.reset() : Plotly.relayout(target, {"xaxis.autorange": true});
    """,
        0,
        2,
    )
    wait.until(lambda driver: driver.execute_script(_RANGE, 0, 0) == [0, 7])
    tabs[0].click()
    other_row = browser.find_element(By.CSS_SELECTOR, '.plotski-report:first-of-type [data-selection-id="b"] button')
    other_row.click()
    wait.until(lambda driver: driver.execute_script(_SELECTION, 0, 0) == [1])
    other_row.click()
    wait.until(lambda driver: not driver.find_elements(By.CSS_SELECTOR, ".plotski-selected"))
    wait.until(lambda driver: not driver.execute_script(_SELECTION, 0, 2))
    assert not [entry for entry in browser.get_log("browser") if entry["level"] == "SEVERE"]


@pytest.mark.parametrize("backend", ["bokeh", "plotly"])
def test_native_png_and_svg(backend: Backend, tmp_path: Path) -> None:
    pytest.importorskip("selenium" if backend == "bokeh" else "kaleido")
    if backend == "plotly":
        pytest.importorskip("plotly")
    grid = Grid(1, 2, backend=backend, cell_width=360, cell_height=270)
    panel = grid.add_subplot(title="Sample").spectrum([1, 2, 3], [3, 8, 5])
    grid.add_subplot(title="Reference").spectrum([1, 2, 3], [2, 3, 2], centroid=True)
    small = panel.save_image(tmp_path / "panel.png")
    large = panel.save_image(tmp_path / "panel@2x.png", scale=2)
    with Image.open(small) as normal, Image.open(large) as high_resolution:
        assert high_resolution.size == tuple(2 * dimension for dimension in normal.size)
        assert len(normal.getcolors(maxcolors=65536) or ()) > 10
    svg = ElementTree.parse(grid.save_image(tmp_path / "grid.svg")).getroot()
    assert svg.tag.endswith("}svg")
    assert any(element.tag.endswith("}path") for element in svg.iter())
