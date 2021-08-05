"""Various mass spectra plot objects"""
from bokeh.models import HoverTool, Legend, Range1d
from bokeh.plotting import figure

from .plot import Plot
from .utilities import check_key, check_source


class PlotSpectrum(Plot):
    """Basic Spectrum plot"""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="x",
        y_axis_label="y",
        title="Spectrum",
        plot_type="spectrum",
        initialize=True,
        **options,
    ):
        Plot.__init__(self, output_dir, x_axis_label, y_axis_label, title=title, **options)
        self.plot_type = plot_type

        # set source
        self.source = source
        self.check_data_source()

        # initialize options
        self.initialize_options()

        # initialize figure
        self.figure = figure(
            tools=self.options["tools"],
            active_drag=self.options["active_drag"],
            x_range=self.options.get("x_range", None),
            y_range=self.options.get("y_range", None),
        )

        # add plot
        self.add_plot_data()

        # set plot layout and misc data
        if initialize:
            self.set_ranges()
        self.set_hover()
        self.set_figure_attributes()
        self.set_options()
        self.set_figure_dimensions()
        self.set_layout()

    def add_plot_data(self):
        """Add plot data"""
        line = self.figure.line(
            x="x",
            y="y",
            source=self.source,
            line_width=self.options["line_width"],
            line_dash=self.options.get("line_dash", "solid"),
            color=self.options["line_color"],
            alpha=self.options["line_alpha"],
            name=self.plot_type,
        )
        self.plots[line.id] = line
        self.add_extents(self.source.data["x"], self.source.data["y"])

    def add_legend(self):
        """Add legend to the plot area"""
        pass

    def set_options(self):
        """Set options"""
        if self.options.get("add_legend", False):
            self.add_legend()

    def set_hover(self):
        """Set hover information"""
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[(f"{self.metadata['x_axis_label']}", "@x"), (f"{self.metadata['y_axis_label']}", "@y")],
                mode="vline",
                names=[self.plot_type],
            )
        )

    def set_figure_dimensions(self):
        """Specify figure dimensions"""
        self.figure.plot_width = self.options.get("plot_width", 800)
        self.figure.plot_height = self.options.get("plot_height", 400)

    def initialize_options(self):
        """Convenience function to handle various options set by the user"""
        if "line_width" not in self.options:
            self.options["line_width"] = 1.5
        if "line_color" not in self.options:
            self.options["line_color"] = "#000000"
        if "line_alpha" not in self.options:
            self.options["line_alpha"] = 1.0
        if "tools" not in self.options:
            self.options["tools"] = ("pan, xpan, xbox_zoom, box_zoom, crosshair, reset",)
        if "active_drag" not in self.options:
            self.options["active_drag"] = "xbox_zoom"

    def set_ranges(self):
        """Set range based on data source"""
        # update x/y ranges
        x_min, x_max, y_min, y_max = self.get_extents()
        if "x_range" not in self.options:
            self.figure.x_range = Range1d(x_min, x_max)
        if "y_range" not in self.options:
            self.figure.y_range = Range1d(y_min, y_max)

    def check_data_source(self):
        """Ensure that each field in the data source is correct"""
        check_source(self.source, ["x", "y"])

    def add_plot_line(self, source, **kwargs):
        """Add plot"""
        line = self.figure.line(
            x="x",
            y="y",
            source=source,
            **kwargs
            # line_width=self.options["line_width"],
            # color=self.options["line_color"],
            # alpha=self.options["line_alpha"],
            # name=self.plot_type,
        )
        # self.figure.segment(x0="x0", y0="y0", x1="x1", y1="y1", source=source, **kwargs)
        self.plots[line.id] = (source, "Line")
        self.add_extents(source.data["x"], source.data["y"])

    def add_segments(self, source, **kwargs):
        """Add segments"""
        segment = self.figure.segment(x0="x0", y0="y0", x1="x1", y1="y1", source=source, **kwargs)
        self.annotations[segment.id] = (source, "Segment")

    def add_centroids_x(self, source, **kwargs):
        """Add vertical centroids"""
        segment = self.figure.segment(x0="x", y0="y0", x1="x", y1="y1", source=source, **kwargs)
        self.annotations[segment.id] = (source, "Centroid-X")

    def add_centroids_y(self, source, **kwargs):
        """Add horizontal centroids"""
        segment = self.figure.segment(x0="x0", y0="y", x1="x1", y1="y", source=source, **kwargs)
        self.annotations[segment.id] = (source, "Segment")

    def add_scatter(self, source, **kwargs):
        """Add scatter points"""
        scatter = self.figure.scatter(x="x", y="y", source=source, **kwargs)
        self.annotations[scatter.id] = (source, "Scatter")


class PlotCentroid(PlotSpectrum):
    """Basic centroid plot"""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="x",
        y_axis_label="y",
        title="Centroid Spectrum",
        plot_type="centroid-spectrum",
        **options,
    ):
        PlotSpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type=plot_type,
            **options,
        )

    def add_plot_data(self):
        """Add plot data"""
        centroid = self.figure.segment(
            x0="x",
            y0="y0",
            x1="x",
            y1="y1",
            source=self.source,
            line_width=self.options["line_width"],
            color=self.options["line_color"],
            alpha=self.options["line_alpha"],
            name=self.plot_type,
        )
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

    def check_data_source(self):
        """Ensure that each field in the data source is correct"""
        check_source(self.source, ["x", "y0", "y1"])

    def set_ranges(self):
        """Set ranges"""
        # update x/y ranges
        src = self.source.data
        self.figure.x_range = Range1d(min(src["x"]), max(src["x"]))
        self.figure.y_range = Range1d(min(src["y0"]), max(src["y1"]) * 1.05)


class PlotCentroidMassSpectrum(PlotCentroid):
    """Plot centroid mass spectrum"""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="m/z",
        y_axis_label="Intensity",
        title="Centroid Mass Spectrum",
        **options,
    ):
        PlotCentroid.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="centroid-mass-spectrum",
            **options,
        )


class PlotMassSpectrum(PlotSpectrum):
    """Mass spectrum plot"""

    def __init__(
        self, output_dir, source, x_axis_label="m/z", y_axis_label="Intensity", title="Mass Spectrum", **options
    ):
        # super(PlotMassSpectrum, self).__init__(
        PlotSpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="mass-spectrum",
            **options,
        )


class PlotMobilogram(PlotSpectrum):
    """Mobilogram plot"""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="Drift time (bins)",
        y_axis_label="Intensity",
        title="Mobilogram",
        **options,
    ):
        # super(PlotMobilogram, self).__init__(
        PlotSpectrum.__init__(
            self,
            output_dir,
            source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="mobilogram",
            **options,
        )


class PlotButterflySpectrum(PlotSpectrum):
    """Butterfly plot"""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="x",
        y_axis_label="y",
        title="Butterfly Spectrum",
        plot_type="butterfly-spectrum",
        **options,
    ):
        # super(PlotButterflyMassSpectrum, self).__init__(
        PlotSpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type=plot_type,
            **options,
        )

    def add_plot_data(self):
        """Plot data"""
        line_top = self.figure.line(
            x="x_top",
            y="y_top",
            source=self.source,
            line_width=self.options["line_width"],
            color=self.options["line_color"],
            alpha=self.options["line_alpha"],
            name=self.plot_type + "-top",
        )
        self.plots[line_top.id] = line_top
        line_bottom = self.figure.line(
            x="x_bottom",
            y="y_bottom",
            source=self.source,
            line_width=self.options["line_width"],
            color=self.options["line_color"],
            alpha=self.options["line_alpha"],
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

    def set_ranges(self):
        """Set ranges"""
        # update x/y ranges
        src = self.source.data
        x = [min(src["x_top"]), min(src["x_bottom"]), max(src["x_top"]), max(src["x_bottom"])]
        y = [min(src["y_top"]), min(src["y_bottom"]), max(src["y_top"]), max(src["y_bottom"])]
        self.figure.x_range = Range1d(min(x), max(x))
        self.figure.y_range = Range1d(min(y) * 1.05, max(y) * 1.05)

    def check_data_source(self):
        """Ensure that each field in the data source is correct"""
        check_source(self.source, ["x_top", "x_bottom", "y_top", "y_bottom"])

    def set_hover(self):
        """Set hover"""
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[
                    (f"{self.metadata['x_axis_label']}", "@x_top"),
                    (f"{self.metadata['y_axis_label']}", "@y_top"),
                ],
                renderers=self.figure.select(name=self.plot_type + "-top"),
                mode="vline",
            )
        )
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[
                    (f"{self.metadata['x_axis_label']}", "@x_bottom"),
                    (f"{self.metadata['y_axis_label']}", "@y_bottom"),
                ],
                renderers=self.figure.select(name=self.plot_type + "-bottom"),
                mode="vline",
            )
        )


class PlotButterflyMassSpectrum(PlotButterflySpectrum):
    """Make butterfly mass spectrum"""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="m/z",
        y_axis_label="Intensity",
        title="Butterfly Mass Spectrum",
        **options,
    ):
        PlotButterflySpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="butterfly-mass-spectrum",
            **options,
        )


class PlotButterflyMobilogram(PlotButterflySpectrum):
    """Make butterfly mobilogram"""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="Drift time (bins)",
        y_axis_label="Intensity",
        title="Butterfly Mobilogram",
        **options,
    ):
        PlotButterflySpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="butterfly-mobilogram",
            **options,
        )


class PlotMultiLine(PlotSpectrum):
    """Basic multiline spectrum"""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="x",
        y_axis_label="y",
        title="Multi-line",
        plot_type="multiline-spectrum",
        **options,
    ):
        PlotSpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type=plot_type,
            **options,
        )

    def add_plot_data(self):
        """Plot data"""
        multiline = self.figure.multi_line(
            xs="xs",
            ys="ys",
            source=self.source,
            line_width=self.options["line_width"],
            color=self.options["line_color"] if not check_key(self.source, "colors") else "colors",
            alpha=self.options["line_alpha"] if not check_key(self.source, "alpha") else "alpha",
            name=self.plot_type,
        )
        self.plots[multiline.id] = multiline

    def add_legend(self):
        """Add legend item to the plot"""
        pass

    def set_ranges(self):
        """Set plot ranges"""
        # update x/y ranges
        # src = self.source.data
        # x = [min(src["x_top"]), min(src["x_bottom"]), max(src["x_top"]), max(src["x_bottom"])]
        # y = [min(src["y_top"]), min(src["y_bottom"]), max(src["y_top"]), max(src["y_bottom"])]
        # self.figure.x_range = Range1d(min(x), max(x))
        # self.figure.y_range = Range1d(min(y) * 1.05, max(y) * 1.05)

    def check_data_source(self):
        """Ensure that each field in the data source is correct"""
        check_source(self.source, ["xs", "ys"])

    def set_hover(self):
        """Set hover"""
        tooltips = [
            (f"{self.metadata['x_axis_label']}", "$data_x"),
            (f"{self.metadata['y_axis_label']}", "$data_y"),
        ]
        if check_key(self.source, "line_id"):
            tooltips.append(("Line ID", "@line_id"))

        self.figure.add_tools(HoverTool(show_arrow=True, tooltips=tooltips, line_policy="next",))
