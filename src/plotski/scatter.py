"""Scatter plot."""
from bokeh.models import ColumnDataSource, HoverTool, Range1d
from bokeh.plotting import figure

from plotski.base import Plot


class PlotScatter(Plot):
    """Scatter plot."""

    # Data parameters
    DATA_KEYS = ("x", "y")
    TOOLS = ("pan, xpan, xbox_zoom, box_zoom, crosshair, reset",)
    ACTIVE_DRAG = "xbox_zoom"

    # Defaults
    WIDTH = 800
    HEIGHT = 400

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "x",
        y_axis_label: str = "y",
        title: str = "Scatter",
        plot_type: str = "Scatter",
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
        """Generate main plot."""
        label = self.kwargs.get("label", "")
        scatter = self.figure.scatter(
            x="x",
            y="y",
            source=self.source,
            name=self.plot_type,
        )
        if label:
            scatter.legend_label = label
        self.plots[scatter.id] = scatter

    def get_figure(self):
        """Get figure."""
        return figure(tools=self.kwargs["tools"], active_drag=self.kwargs["active_drag"])

    def set_hover(self):
        """Set hover."""
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[(f"{self.x_axis_label}", "@x"), (f"{self.y_axis_label}", "@y")],
                mode="vline",
                # names=[self.plot_type],
            )
        )

    def set_ranges(self, **kwargs):
        """Set x/y-axis ranges."""
        src = self.source.data
        x_range = self.kwargs.get("x_range", (min(src["x"]), max(src["x"]) * 1.05))
        y_range = self.kwargs.get("y_range", (min(src["y"]), max(src["y"]) * 1.05))
        self.figure.x_range = Range1d(*x_range)
        self.figure.y_range = Range1d(*y_range)
