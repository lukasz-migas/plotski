"""Base plot."""
from bokeh.models import ColumnDataSource, HoverTool, Legend, Range1d
from bokeh.plotting import figure

from plotski.base import Plot
from plotski.utilities import check_key


class PlotSpectrum(Plot):
    """Basic Spectrum plot"""

    # Data attributes
    DATA_KEYS = ("x", "y")
    ACTIVE_DRAG = "xbox_zoom"
    TOOLS = ("pan, xpan, xbox_zoom, box_zoom, crosshair, reset",)

    # Defaults
    WIDTH = 800
    HEIGHT = 400

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "x",
        y_axis_label: str = "y",
        title: str = "Spectrum",
        plot_type: str = "spectrum",
        initialize: bool = True,
        **kwargs,
    ):
        Plot.__init__(
            self,
            output_dir,
            source,
            x_axis_label,
            y_axis_label,
            title=title,
            plot_type=plot_type,
            initialize=initialize,
            **kwargs,
        )

    def plot(self):
        """Add plot data"""
        line = self.figure.line(
            x="x",
            y="y",
            source=self.source,
            line_width=self.kwargs["line_width"],
            line_dash=self.kwargs.get("line_dash", "solid"),
            color=self.kwargs["line_color"],
            alpha=self.kwargs["line_alpha"],
            name=self.plot_type,
            legend_label=self.kwargs.get("label", ""),
        )
        self.plots[line.id] = line
        self.add_extents(self.source.data["x"], self.source.data["y"])

    def get_figure(self):
        """Create figure."""
        return figure(
            tools=self.kwargs["tools"],
            active_drag=self.kwargs["active_drag"],
            x_range=self.kwargs.get("x_range", Range1d()),
            y_range=self.kwargs.get("y_range", Range1d()),
        )

    def set_hover(self):
        """Set hover information"""
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[(f"{self.metadata['x_axis_label']}", "@x"), (f"{self.metadata['y_axis_label']}", "@y")],
                mode="vline",
                # names=[self.plot_type],
            )
        )

    def initialize_options(self):
        """Convenience function to handle various options set by the user"""
        if "line_width" not in self.kwargs:
            self.kwargs["line_width"] = 1.5
        if "line_color" not in self.kwargs:
            self.kwargs["line_color"] = "#000000"
        if "line_alpha" not in self.kwargs:
            self.kwargs["line_alpha"] = 1.0
        super().initialize_options()

    def set_ranges(self, **kwargs):
        """Set range based on data source"""
        # update x/y ranges
        x_min, x_max, y_min, y_max = self.get_extents(**kwargs)
        if "x_range" not in self.kwargs:
            self.figure.x_range.update(start=x_min, end=x_max)
        if "y_range" not in self.kwargs:
            self.figure.y_range.update(start=y_min, end=y_max)

    def add_plot_line(self, source: ColumnDataSource, **kwargs):
        """Add plot"""
        line = self.figure.line(x="x", y="y", source=source, **kwargs)
        self.plots[line.id] = (source, "Line")
        self.add_extents(source.data["x"], source.data["y"])

    def add_segments(self, source: ColumnDataSource, **kwargs):
        """Add segments"""
        segment = self.figure.segment(x0="x0", y0="y0", x1="x1", y1="y1", source=source, **kwargs)
        self.annotations[segment.id] = (source, "Segment")

    def add_centroids_x(self, source: ColumnDataSource, **kwargs):
        """Add vertical centroids"""
        segment = self.figure.segment(x0="x", y0="y0", x1="x", y1="y1", source=source, **kwargs)
        self.annotations[segment.id] = (source, "Centroid-X")

    def add_centroids_y(self, source: ColumnDataSource, **kwargs):
        """Add horizontal centroids"""
        segment = self.figure.segment(x0="x0", y0="y", x1="x1", y1="y", source=source, **kwargs)
        self.annotations[segment.id] = (source, "Centroid-Y")

    def add_scatter(self, source: ColumnDataSource, **kwargs):
        """Add scatter points."""
        scatter = self.figure.scatter(x="x", y="y", source=source, **kwargs)
        self.annotations[scatter.id] = (source, "Scatter")


class PlotCentroid(PlotSpectrum):
    """Basic centroid plot"""

    DATA_KEYS = ("x", "y0", "y1")

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "x",
        y_axis_label: str = "y",
        title: str = "Centroid Spectrum",
        plot_type: str = "centroid-spectrum",
        **kwargs,
    ):
        PlotSpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type=plot_type,
            **kwargs,
        )

    def plot(self):
        """Add plot data"""
        label = self.kwargs.get("label", "")
        centroid = self.figure.segment(
            x0="x",
            y0="y0",
            x1="x",
            y1="y1",
            source=self.source,
            line_width=self.kwargs["line_width"],
            color=self.kwargs["line_color"],
            alpha=self.kwargs["line_alpha"],
            name=self.plot_type,
        )
        if label:
            centroid.legend_label = label
        self.plots[centroid.id] = centroid

    def set_hover(self):
        """Set hover"""
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[(f"{self.metadata['x_axis_label']}", "@x"), (f"{self.metadata['y_axis_label']}", "@y1")],
                point_policy="snap_to_data",
                line_policy="none",
            )
        )

    def set_ranges(self, **kwargs):
        """Set ranges"""
        # update x/y ranges
        src = self.source.data
        if "x_range" not in self.kwargs:
            self.figure.x_range = Range1d(min(src["x"]), max(src["x"]))
        if "y_range" not in self.kwargs:
            self.figure.y_range = Range1d(min(src["y0"]), max(src["y1"]) * 1.05)


class PlotButterflySpectrum(PlotSpectrum):
    """Butterfly plot"""

    DATA_KEYS = ("x_top", "y_top", "x_bottom", "y_bottom")

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "x",
        y_axis_label: str = "y",
        title: str = "Butterfly Spectrum",
        plot_type: str = "butterfly-spectrum",
        **kwargs,
    ):
        PlotSpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type=plot_type,
            **kwargs,
        )

    def plot(self):
        """Plot data"""
        line_top = self.figure.line(
            x="x_top",
            y="y_top",
            source=self.source,
            line_width=self.kwargs["line_width"],
            color=self.kwargs["line_color"],
            alpha=self.kwargs["line_alpha"],
            name=self.plot_type + "-top",
        )
        self.plots[line_top.id] = line_top
        line_bottom = self.figure.line(
            x="x_bottom",
            y="y_bottom",
            source=self.source,
            line_width=self.kwargs["line_width"],
            color=self.kwargs["line_color"],
            alpha=self.kwargs["line_alpha"],
            name=self.plot_type + "-bottom",
        )
        self.plots[line_bottom.id] = line_bottom

    def add_legend(self):
        """Add legend item to the plot"""
        legend = Legend(
            items=[
                ("Top", self.figure.select(name=self.plot_type + "-top")),
                ("Bottom", self.figure.select(name=self.plot_type + "-bottom")),
            ],
            orientation="horizontal",
        )
        # Add the layout outside the plot, clicking legend item hides the line
        self.figure.add_layout(legend, "above")
        self.figure.legend.click_policy = "hide"

    def set_ranges(self, **kwargs):
        """Set ranges"""
        # update x/y ranges
        src = self.source.data
        x = [min(src["x_top"]), min(src["x_bottom"]), max(src["x_top"]), max(src["x_bottom"])]
        y = [min(src["y_top"]), min(src["y_bottom"]), max(src["y_top"]), max(src["y_bottom"])]
        self.figure.x_range = Range1d(min(x), max(x))
        self.figure.y_range = Range1d(min(y) * 1.05, max(y) * 1.05)

    def set_hover(self):
        """Set hover"""
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[
                    (f"{self.x_axis_label}", "@x_top"),
                    (f"{self.y_axis_label}", "@y_top"),
                ],
                renderers=self.figure.select(name=self.plot_type + "-top"),
                mode="vline",
            )
        )
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[
                    (f"{self.x_axis_label}", "@x_bottom"),
                    (f"{self.y_axis_label}", "@y_bottom"),
                ],
                renderers=self.figure.select(name=self.plot_type + "-bottom"),
                mode="vline",
            )
        )


class PlotMultiLine(PlotSpectrum):
    """Basic multiline spectrum"""

    DATA_KEYS = ("xs", "ys")

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "x",
        y_axis_label: str = "y",
        title: str = "Multi-line",
        plot_type: str = "multiline-spectrum",
        **kwargs,
    ):
        PlotSpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type=plot_type,
            **kwargs,
        )

    def plot(self):
        """Plot data"""
        multiline = self.figure.multi_line(
            xs="xs",
            ys="ys",
            source=self.source,
            line_width=self.kwargs["line_width"],
            color=self.kwargs["line_color"] if not check_key(self.source, "colors") else "colors",
            alpha=self.kwargs["line_alpha"] if not check_key(self.source, "alpha") else "alpha",
            name=self.plot_type,
        )
        self.plots[multiline.id] = multiline

    def set_ranges(self, **kwargs):
        """Set plot ranges"""
        src = self.source.data
        xmin = min([min(x) for x in src["xs"]])
        xmax = max([max(x) for x in src["xs"]])
        ymin = min([min(y) for y in src["ys"]])
        ymax = max([max(y) for y in src["ys"]])
        self.figure.x_range.update(start=xmin, end=xmax)
        self.figure.y_range.update(start=ymin, end=ymax)
        # x = [min(src["x_top"]), min(src["x_bottom"]), max(src["x_top"]), max(src["x_bottom"])]
        # y = [min(src["y_top"]), min(src["y_bottom"]), max(src["y_top"]), max(src["y_bottom"])]
        # self.figure.x_range = Range1d(min(x), max(x))
        # self.figure.y_range = Range1d(min(y) * 1.05, max(y) * 1.05)

    def set_hover(self):
        """Set hover"""
        tooltips = [
            (f"{self.x_axis_label}", "x"),
            (f"{self.y_axis_label}", "y"),
        ]
        if check_key(self.source, "line_id"):
            tooltips.append(("Line ID", "@line_id"))

        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=tooltips,
                line_policy="next",
            )
        )
