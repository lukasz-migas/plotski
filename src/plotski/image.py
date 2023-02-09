"""Image."""
import numpy as np
from bokeh.models import BasicTicker, BoxZoomTool, ColorBar, ColumnDataSource, HoverTool, Range1d
from bokeh.plotting import figure

from plotski.base import Plot
from plotski.utilities import calculate_aspect_ratio


class PlotImageBase(Plot):
    """Basic heatmap plot"""

    # Data attributes
    DATA_KEYS = ("image", "x", "y", "dw", "dh")
    ACTIVE_DRAG = None
    TOOLS = None

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "",
        y_axis_label: str = "",
        title: str = "Heatmap",
        plot_type: str = "heatmap",
        initialize: bool = True,
        **kwargs,
    ):
        self.ACTIVE_DRAG = BoxZoomTool(match_aspect=True)
        self.TOOLS = ("pan, crosshair, reset", self.ACTIVE_DRAG)
        Plot.__init__(
            self,
            output_dir,
            source,
            x_axis_label,
            y_axis_label,
            title=title,
            plot_type=plot_type,
            initilize=initialize,
            **kwargs,
        )

    def plot(self):
        """Main plotting function."""
        raise NotImplementedError("Must implement method")

    def get_figure(self):
        """Get figure."""
        return figure(
            tools=self.kwargs["tools"],
            active_drag=self.kwargs["active_drag"],
            x_range=self.kwargs.get("x_range", Range1d()),
            y_range=self.kwargs.get("y_range", Range1d()),
        )

    def initialize_options(self):
        """Setup few options"""
        from plotski.utilities import convert_colormap_to_mapper

        # setup some common options if the user has not specified them
        if "cmap" not in self.kwargs:
            self.kwargs["cmap"] = "viridis"

        self.kwargs["palette"], self.kwargs["colormapper"] = convert_colormap_to_mapper(
            self.source.data["image"][0],
            self.kwargs["cmap"],
            z_min=self.kwargs.get("z_min", None),
            z_max=self.kwargs.get("z_max", None),
        )
        super().initialize_options()

    def set_hover(self):
        """Set hover."""
        self.figure.add_tools(
            HoverTool(
                show_arrow=True,
                tooltips=[("x, y", "$x{0.00}, $y{0.00}"), (self.kwargs.get("hover_label", "intensity"), "@image")],
            )
        )

    def set_ranges(self, **kwargs):
        """Set ranges."""
        self.figure.xaxis.axis_label_text_baseline = "bottom"

        # update x/y ranges
        src = self.source.data
        if "x_range" not in self.kwargs:
            self.figure.x_range.update(start=0, end=src["image"][0].shape[1])
        if "y_range" not in self.kwargs:
            self.figure.y_range.update(start=0, end=src["image"][0].shape[0])
        # x_range = self.kwargs.get("x_range", None)
        # if x_range is None:
        #     x_range = (0, src["image"][0].shape[1])
        # self.figure.x_range = Range1d(*x_range) if isinstance(x_range, ty.Iterable) else x_range
        # y_range = self.kwargs.get("y_range", None)
        # if y_range is None:
        #     y_range = (0, src["image"][0].shape[0])
        # self.figure.y_range = Range1d(*y_range) if isinstance(y_range, ty.Iterable) else y_range

    def set_figure_dimensions(self):
        """Set figure dimensions."""
        width = self.kwargs.get("width", 600)
        height, width = calculate_aspect_ratio(self.source.data["image"][0].shape, width)
        if height > 600:
            _ratio = 600 / height
            height = 600
            width = int(width * _ratio)
        self.figure.width = self.kwargs.get("width", width)
        self.figure.height = self.kwargs.get("height", height)

    def check_data_source(self):
        """Ensure that each field in the data source is correct"""
        if "image" not in self.source.data:
            raise ValueError("Missing field 'image' in the ColumnDataSource")
        if "image" in self.source.data:
            if not isinstance(self.source.data["image"], list) and len(self.source.data["image"]) > 1:
                raise ValueError("Field 'image' is incorrectly set in ColumnDataSource")
        if "x" not in self.source.data:
            self.source.data["x"] = [0]
        if "y" not in self.source.data:
            self.source.data["y"] = [0]
        if "dw" not in self.source.data:
            self.source.data["dw"] = [self.source.data["image"][0].shape[1]]
        if "dh" not in self.source.data:
            self.source.data["dh"] = [self.source.data["image"][0].shape[0]]
        super().check_data_source()


class PlotImage(PlotImageBase):
    """Image class"""

    def __init__(self, output_dir: str, source: ColumnDataSource, title="Image", **kwargs):
        PlotImageBase.__init__(self, output_dir, source=source, title=title, plot_type="image", **kwargs)

    def plot(self):
        """Plot image."""
        self.plots["image"] = self.figure.image(
            x="x",
            y="y",
            dw="dw",
            dh="dh",
            image="image",
            source=self.source,
            palette=self.kwargs["palette"],
            name="image",
        )
        self.plots["image"].glyph.color_mapper = self.kwargs["colormapper"]

    def add_colorbar(self):
        """Add colorbar."""
        color_bar = ColorBar(
            color_mapper=self.kwargs["colormapper"],
            ticker=BasicTicker(),
            location=(0, 0),
            major_label_text_font_size="10pt",
            label_standoff=8,
        )
        self.figure.add_layout(color_bar, "right")

    def set_options(self):
        """Set options."""
        if self.kwargs.get("add_colorbar", False):
            self.add_colorbar()


class PlotImageRGBA(PlotImageBase):
    """RGB Image class."""

    def __init__(self, output_dir: str, source: ColumnDataSource, title="Image-RGBA", **kwargs):
        PlotImageBase.__init__(self, output_dir, source=source, title=title, plot_type="rgba", **kwargs)

    def plot(self):
        """Main plotting method."""
        self.plots["rgba"] = self.figure.image_rgba(
            x="x", y="y", dw="dw", dh="dh", image="image", source=self.source, name="rgba"
        )

    def check_data_source(self):
        """Check data sources."""
        PlotImageBase.check_data_source(self)
        if self.source.data["image"][0].dtype != np.uint8:
            raise ValueError("ImageRGBA expects 8-bit values")

    def set_hover(self):
        """Add hover to the image plot."""
        tooltips = [("x, y", "$x{0.00}, $y{0.00}")]
        if "intensity" in self.source.data:
            tooltips.append(("intensity", "@intensity"))
        else:
            tooltips.append(("intensity", "@image"))

        if "r" in self.source.data:
            tooltips.append(("(R, G, B A)", "@r, @g, @b, @a"))

        self.figure.add_tools(HoverTool(show_arrow=True, tooltips=tooltips))
