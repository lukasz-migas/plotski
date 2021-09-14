"""Scatter plot."""
from bokeh.models import Range1d
from bokeh.plotting import figure

from .plot import Plot


class PlotScatter(Plot):
    """Scatter plot."""

    DATA_KEYS = ("x", "y")

    def __init__(
        self,
        output_dir: str,
        source,
        x_axis_label: str = "x",
        y_axis_label: str = "y",
        title: str = "Scatter",
        plot_type: str = "Scatter",
        initialize: bool = True,
        **kwargs,
    ):
        Plot.__init__(self, output_dir, source, x_axis_label, y_axis_label, title=title, plot_type=plot_type, **kwargs)

        # set plot layout and misc data
        if initialize:
            self.set_ranges(**kwargs)
        self.set_hover()
        self.set_figure_attributes()
        self.set_options()
        self.set_figure_dimensions()
        self.set_layout()

    def plot(self):
        """Generate main plot."""
        self.plots["plot"] = self.figure.scatter(x="x", y="y", source=self.source, name=self.plot_type)

    def get_figure(self):
        """Get figure."""
        return figure(tools=self.kwargs["tools"], active_drag=self.kwargs["active_drag"])

    def add_legend(self):
        pass

    def set_options(self):
        if self.kwargs.get("add_legend", False):
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
        self.figure.plot_width = self.kwargs.get("plot_width", 800)
        self.figure.plot_height = self.kwargs.get("plot_height", 400)

    def initialize_options(self):
        """Convenience function to handle various options set by the user"""
        if "tools" not in self.kwargs:
            self.kwargs["tools"] = ("pan, xpan, xbox_zoom, box_zoom, crosshair, reset",)
        if "active_drag" not in self.kwargs:
            self.kwargs["active_drag"] = "xbox_zoom"

    def set_ranges(self, **kwargs):
        # update x/y ranges
        src = self.source.data
        x_range = self.kwargs.get("x_range", (min(src["x"]), max(src["x"]) * 1.05))
        y_range = self.kwargs.get("y_range", (min(src["y"]), max(src["y"]) * 1.05))
        self.figure.x_range = Range1d(*x_range)
        self.figure.y_range = Range1d(*y_range)
