"""Scatter plot."""
from bokeh.models import Range1d
from bokeh.plotting import figure

from .plot import Plot
from .utilities import check_source


class PlotScatter(Plot):
    """Scatter plot."""

    def __init__(
        self,
        output_dir,
        source,
        x_axis_label="x",
        y_axis_label="y",
        title="Scatter",
        plot_type="scatter",
        initialize=True,
        **options,
    ):
        Plot.__init__(self, output_dir, x_axis_label, y_axis_label, title=title, **options)
        self.plot_type = plot_type

        # set source
        self.source = source
        self.check_data_source()

        # initialize options
        self.initilize_options()

        # initialize figure
        self.figure = figure(tools=self.options["tools"], active_drag=self.options["active_drag"])

        # add plot
        self.add_plot_data()

        # set plot layout and misc data
        if initialize:
            self.set_ranges(**options)
        self.set_hover()
        self.set_figure_attributes()
        self.set_options()
        self.set_figure_dimensions()
        self.set_layout()

    def add_plot_data(self):
        self.plots["plot"] = self.figure.scatter(x="x", y="y", source=self.source, name=self.plot_type)

    def add_legend(self):
        pass

    def set_options(self):
        if self.options.get("add_legend", False):
            self.add_legend()

    def set_hover(self):
        pass

    #     self.figure.add_tools(
    #         HoverTool(
    #             show_arrow=True,
    #             tooltips=[(f"{self.metadata['x_axis_label']}", "@x"), (f"{self.metadata['y_axis_label']}", "@y")],
    #             mode="vline",
    #             names=[self.plot_type],
    #         )
    #     )

    def set_figure_dimensions(self):
        self.figure.plot_width = self.options.get("plot_width", 800)
        self.figure.plot_height = self.options.get("plot_height", 400)

    def initilize_options(self):
        """Convenience function to handle various options set by the user"""
        if "tools" not in self.options:
            self.options["tools"] = ("pan, xpan, xbox_zoom, box_zoom, crosshair, reset",)
        if "active_drag" not in self.options:
            self.options["active_drag"] = "xbox_zoom"

    def set_ranges(self, **kwargs):
        # update x/y ranges
        src = self.source.data
        x_range = self.options.get("x_range", (min(src["x"]), max(src["x"]) * 1.05))
        y_range = self.options.get("y_range", (min(src["y"]), max(src["y"]) * 1.05))
        self.figure.x_range = Range1d(*x_range)
        self.figure.y_range = Range1d(*y_range)

    def check_data_source(self):
        """Ensure that each field in the data source is correct"""
        check_source(self.source, ["x", "y"])
