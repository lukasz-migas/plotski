"""Test imimspy.visualise.store.py"""
# Standard library imports
import os

# Third-party imports
import numpy as np
import pytest
from bokeh.models.widgets import Tabs

# Local imports
from imimspy.visuals.rgb import ImageRGBA
from imimspy.visuals.bokeh.store import PlotStore


@pytest.fixture
def store(tmpdir):
    output_dir = os.path.join(tmpdir, "plot-store")
    os.mkdir(output_dir)
    return PlotStore(output_dir)


class TestPlotStore:
    @staticmethod
    def test_get_unique_name(store):
        tab_name = "TEST"
        store.add_tab(tab_name)
        item_name = store.get_unique_name(tab_name)
        assert item_name not in store.tabs

    @staticmethod
    def test_add_tab(store):
        tab_name = "TEST"
        store.add_tab(tab_name)
        assert tab_name in store.tabs
        tab_name = "TEST2"
        store.add_tab(tab_name)
        assert tab_name in store.tabs
        assert len(store.tabs) == 2

    @staticmethod
    def test_add_tabs(store):
        tab_names = ["tab 1", "tab 2"]
        store.add_tabs(tab_names)
        assert all([tab_name in store.tabs for tab_name in tab_names])
        assert len(store.tabs) == 2

    @staticmethod
    def test_add_tab_twice(store):
        tab_name = "TEST"
        store.add_tab(tab_name)
        with pytest.raises(ValueError):
            store.add_tab(tab_name)

    @staticmethod
    def test_add_tab_twice_reset(store):
        tab_name = "TEST"
        store.add_tab(tab_name)
        store.add_tab(tab_name, reset=True)
        assert len(store.tabs) == 1

    @staticmethod
    def test_add_row(store):
        tab_name = "TEST"
        store.add_tab(tab_name)
        assert tab_name in store.tabs
        row_name = store.add_row(tab_name)
        assert row_name.startswith("row")
        assert row_name in store.tabs[tab_name]

    @staticmethod
    def test_add_row_forgot_tab(store):
        with pytest.raises(AssertionError):
            _ = store.add_row("TEST")

    @staticmethod
    def test_add_row_plots(store):
        image = np.random.randint(0, 100, (10, 10))
        tab_name = "heatmaps"
        store.add_tab(tab_name)
        row_name = store.add_row(tab_name)
        store.plot_image(tab_name, dict(image=[image]), item_name=row_name)
        store.plot_image(tab_name, dict(image=[image]), item_name=row_name)
        assert row_name in store.tabs[tab_name]
        assert len(store.tabs[tab_name][row_name]) == 2

    @staticmethod
    def test_add_col(store):
        tab_name = "TEST"
        store.add_tab(tab_name)
        assert tab_name in store.tabs
        col_name = store.add_col(tab_name)
        assert col_name.startswith("col")
        assert col_name in store.tabs[tab_name]

    @staticmethod
    def test_add_col_forgot_tab(store):
        with pytest.raises(AssertionError):
            _ = store.add_col("TEST")

    @staticmethod
    def test_add_col_plots(store):
        image = np.random.randint(0, 100, (10, 10))
        tab_name = "heatmaps"
        store.add_tab(tab_name)
        col_name = store.add_grid(tab_name)
        store.plot_image(tab_name, dict(image=[image]), item_name=col_name)
        store.plot_image(tab_name, dict(image=[image]), item_name=col_name)
        assert col_name in store.tabs[tab_name]
        assert len(store.tabs[tab_name][col_name]) == 2

    @staticmethod
    def test_add_grid(store):
        tab_name = "TEST"
        store.add_tab(tab_name)
        assert tab_name in store.tabs
        col_name = store.add_grid(tab_name)
        assert col_name.startswith("grid")
        assert col_name in store.tabs[tab_name]

    @staticmethod
    def test_add_grid_forgot_tab(store):
        with pytest.raises(AssertionError):
            _ = store.add_grid("TEST")

    @staticmethod
    def test_add_grid_plots(store):
        image = np.random.randint(0, 100, (10, 10))
        tab_name = "heatmaps"
        store.add_tab(tab_name)
        col_name = store.add_grid(tab_name)
        store.plot_image(tab_name, dict(image=[image]), item_name=col_name)
        store.plot_image(tab_name, dict(image=[image]), item_name=col_name)
        store.plot_image(tab_name, dict(image=[image]), item_name=col_name)
        assert col_name in store.tabs[tab_name]
        assert len(store.tabs[tab_name][col_name]) == 3

    @staticmethod
    def test_add_spectrum(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        tab_name = "spectrum"
        store.add_tab(tab_name)
        store.plot_spectrum(tab_name, dict(x=x, y=y))
        assert "item #0" in store.tabs[tab_name]
        store.plot_spectrum(tab_name, dict(x=x, y=y))
        assert "item #1" in store.tabs[tab_name]

    @staticmethod
    def test_add_multiline_spectrum(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        tab_name = "spectrum"
        store.add_tab(tab_name)
        store.plot_multiline_spectrum("spectrum", dict(xs=[x, x], ys=[y, y[::-1]]))
        assert "item #0" in store.tabs[tab_name]

    @staticmethod
    def test_add_mass_spectrum(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        tab_name = "mass spectrum"
        store.add_tab(tab_name)
        store.plot_mass_spectrum(tab_name, dict(x=x, y=y))
        assert "item #0" in store.tabs[tab_name]

    @staticmethod
    def test_add_centroid_mass_spectrum(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        tab_name = "mass spectrum"
        store.add_tab(tab_name)
        store.plot_centroid_mass_spectrum(tab_name, dict(x=x, y0=np.zeros_like(y), y1=y))
        assert "item #0" in store.tabs[tab_name]

    @staticmethod
    def test_add_butterfly_mass_spectrum(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        tab_name = "butterfly-mass-spectrum"
        store.add_tab(tab_name)
        store.plot_butterfly_mass_spectrum(tab_name, dict(x_top=x, y_top=y, x_bottom=x, y_bottom=-y))
        assert "item #0" in store.tabs[tab_name]

    @staticmethod
    def test_add_mobilogram(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        tab_name = "mass spectrum"
        store.add_tab(tab_name)
        store.plot_mobilogram(tab_name, dict(x=x, y=y))
        assert "item #0" in store.tabs[tab_name]

    @staticmethod
    def test_add_butterfly_mobilogram(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        tab_name = "butterfly-mobilogram"
        store.add_tab(tab_name)
        store.plot_butterfly_mobilogram(tab_name, dict(x_top=x, y_top=y, x_bottom=x, y_bottom=-y))
        assert "item #0" in store.tabs[tab_name]

    @staticmethod
    def test_add_image(store):
        image = np.random.randint(0, 100, (10, 10))
        tab_name = "heatmap"
        store.plot_image(tab_name, dict(image=[image]))
        assert "item #0" in store.tabs[tab_name]

    @staticmethod
    def test_add_rgba_image(store):
        image = [np.random.randint(0, 100, (10, 10))]
        rgba = ImageRGBA(image)
        rgba_img = rgba.rgb
        rgba_intensity = rgba.intensities
        tab_name = "rgba"
        store.plot_rgb_image(tab_name, dict(image=[rgba_img], intensities=[rgba_intensity]))
        assert "item #0" in store.tabs[tab_name]

    @staticmethod
    def test_add_annotations_line(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        tab_name = "plot"
        store.add_tab(tab_name)
        _, _, plot = store.plot_spectrum(tab_name, dict(x=x, y=y))
        assert "item #0" in store.tabs[tab_name]
        # band annotation
        store.add_band(plot, dict(base=x, lower=y - 3, upper=y + 3))
        # span
        store.add_span(plot, dict(location=1, dimension="width"))
        store.add_span(plot, dict(location=1, dimension="height"))
        store.add_span(plot, dict(location=[5, 3], dimension="height"))
        # add box
        store.add_box(plot, dict(bottom=1, right=3, top=4, left=2))
        store.add_box(plot, dict(bottom=3, right=7))
        store.add_box(plot, dict(top=4, left=2))
        # add labels
        store.add_labels(plot, dict(x=[3, 4], y=[3, 4], text=["label 1", "label 2"]))
        # add centroids
        store.add_segments(plot, dict(x0=[0, 9], x1=[9, 0], y0=[0, 0], y1=[10, 10]))
        store.add_centroids_x(plot, dict(x=[1, 2, 3], y0=[0, 0, 0], y1=[3, 5, 7]))
        store.add_centroids_y(plot, dict(x0=[0, 0, 0], x1=[1, 2, 3], y=[3, 5, 7]))

    @staticmethod
    def test_add_annotations_image(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        image = np.random.randint(0, 100, (10, 10))
        tab_name = "heatmap"
        _, _, plot = store.plot_image(tab_name, dict(image=[image]))
        assert "item #0" in store.tabs[tab_name]
        # band annotation
        store.add_span(plot, dict(location=1, dimension="width"))
        store.add_span(plot, dict(location=1, dimension="height"))
        store.add_span(plot, dict(location=[5, 3], dimension="height"))
        # add box
        store.add_box(plot, dict(bottom=1, right=3, top=4, left=2))
        store.add_box(plot, dict(bottom=3, right=7))
        store.add_box(plot, dict(top=4, left=2))
        # add labels
        store.add_labels(plot, dict(x=[3, 4], y=[3, 4], text=["label 1", "label 2"]))

    @staticmethod
    def test_add_annotations_fail(store):
        x, y = np.arange(0, 10), np.arange(0, 10)
        image = np.random.randint(0, 100, (10, 10))
        tab_name = "heatmap"
        _, _, plot = store.plot_image(tab_name, dict(image=[image]))
        assert "item #0" in store.tabs[tab_name]
        with pytest.raises(ValueError):
            store.add_band(plot, dict(base=x, lower=y - 3, upper=y + 3))
            # add centroids
            store.add_segments(plot, dict(x0=[0, 9], x1=[9, 0], y0=[0, 0], y1=[10, 10]))
            store.add_centroids_x(plot, dict(x=[1, 2, 3], y0=[0, 0, 0], y1=[3, 5, 7]))
            store.add_centroids_y(plot, dict(x0=[0, 0, 0], x1=[1, 2, 3], y=[3, 5, 7]))

    @staticmethod
    def test_get_layout(store):
        image = np.random.randint(0, 100, (10, 10))
        tab_name = "heatmap"
        store.plot_image(tab_name, dict(image=[image]))
        tabs = store.get_layout()
        assert isinstance(tabs, Tabs)

    @staticmethod
    def test_save(store):
        image = np.random.randint(0, 100, (10, 10))
        tab_name = "heatmap"
        store.add_tab(tab_name)
        store.plot_image(tab_name, dict(image=[image]))

        filepath = os.path.join(store.output_dir, store.filename)
        store.save(show=False)
        assert os.path.exists(filepath)
