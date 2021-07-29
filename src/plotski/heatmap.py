# Standard library imports

# Third-party imports
import numpy as np
from bokeh.models import BasicTicker, ColorBar, HoverTool, Range1d
from bokeh.plotting import figure

# Local imports
from .plot import Plot
from .utilities import calculate_aspect_ratio


class PlotHeatmap(Plot):
    """Basic heatmap plot"""

    def __init__(
        self, output_dir, source, x_axis_label="", y_axis_label="", title="Heatmap", plot_type="heatmap", **options
    ):
        Plot.__init__(self, output_dir, x_axis_label, y_axis_label, **options)

        self.plot_type = plot_type
        self._div_title = title
        self._div_header = options.pop("header", "")
        self._div_footer = options.pop("footer", "")

        # set source
        self.source = source
        self.check_data_source()

        # initialize options
        self.initialize_options()

        # initialize figure
        self.figure = figure(tools=self.options["tools"], active_drag=self.options["active_drag"])

        # add plot
        self.add_plot_data()

        # set plot layout and misc data
        self.set_ranges()
        self.set_hover()
        self.set_figure_attributes()
        self.set_options()
        self.set_figure_dimensions()
        self.set_layout()

    def initialize_options(self):
        """Setup few options"""
        from .utilities import convert_colormap_to_mapper

        # setup some common options if the user has not specified them
        if "cmap" not in self.options:
            self.options["cmap"] = "viridis"

        self.options["palette"], self.options["colormapper"] = convert_colormap_to_mapper(
            self.source.data["image"][0],
            self.options["cmap"],
            z_min=self.options.get("z_min", None),
            z_max=self.options.get("z_max", None),
        )
        if "tools" not in self.options:
            self.options["tools"] = ("pan, box_zoom, crosshair, reset",)
        if "active_drag" not in self.options:
            self.options["active_drag"] = "box_zoom"

    def add_plot_data(self):
        raise NotImplementedError("Must implement method")

    def set_hover(self):
        self.figure.add_tools(
            HoverTool(show_arrow=True, tooltips=[("x, y", "$x{0.00}, $y{0.00}"), ("intensity", "@image")])
        )

    def set_options(self):
        raise NotImplementedError("Must implement method")

    def set_ranges(self):
        self.figure.xaxis.axis_label_text_baseline = "bottom"

        # update x/y ranges
        src = self.source.data
        x_range = self.options.get("x_range", (0, src["image"][0].shape[1]))
        self.figure.x_range = Range1d(*x_range)
        y_range = self.options.get("y_range", (0, src["image"][0].shape[0]))
        self.figure.y_range = Range1d(*y_range)

    def set_figure_dimensions(self):
        plot_height, plot_width = calculate_aspect_ratio(self.source.data["image"][0].shape, 600)
        if plot_height > 600:
            _ratio = 600 / plot_height
            plot_height = 600
            plot_width = int(plot_width * _ratio)
        self.figure.plot_width = self.options.get("plot_width", plot_width)
        self.figure.plot_height = self.options.get("plot_height", plot_height)

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


class PlotImage(PlotHeatmap):
    def __init__(self, output_dir, source, title="Image", **options):
        PlotHeatmap.__init__(self, output_dir, source=source, title=title, plot_type="image", **options)

    def add_plot_data(self):
        self.plots["image"] = self.figure.image(
            x="x",
            y="y",
            dw="dw",
            dh="dh",
            image="image",
            source=self.source,
            palette=self.options["palette"],
            name="image",
        )
        self.plots["image"].glyph.color_mapper = self.options["colormapper"]

    def add_colorbar(self):
        color_bar = ColorBar(
            color_mapper=self.options["colormapper"],
            ticker=BasicTicker(),
            location=(0, 0),
            major_label_text_font_size="10pt",
            label_standoff=8,
        )
        self.figure.add_layout(color_bar, "right")

    def set_options(self):
        if self.options.get("add_colorbar", False):
            self.add_colorbar()


class PlotImageRGBA(PlotHeatmap):
    def __init__(self, output_dir, source, title="Image-RGBA", **options):
        PlotHeatmap.__init__(self, output_dir, source=source, title=title, plot_type="rgba", **options)

    def add_plot_data(self):
        self.plots["rgba"] = self.figure.image_rgba(
            x="x", y="y", dw="dw", dh="dh", image="image", source=self.source, name="rgba"
        )

    def set_options(self):
        pass

    def check_data_source(self):
        PlotHeatmap.check_data_source(self)
        if self.source.data["image"][0].dtype != np.uint8:
            raise ValueError("ImageRGBA expects 8-bit values")

    def set_hover(self):
        """Add hover to the image plto"""
        tooltips = [("x, y", "$x{0.00}, $y{0.00}")]
        if "intensity" in self.source.data:
            tooltips.append(("intensity", "@intensity"))
        else:
            tooltips.append(("intensity", "@image"))

        if "r" in self.source.data:
            tooltips.append(("(R, G, B A)", "@r, @g, @b, @a"))

        self.figure.add_tools(HoverTool(show_arrow=True, tooltips=tooltips))
