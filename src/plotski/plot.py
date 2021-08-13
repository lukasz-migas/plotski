"""Classes to generate bokeh plots"""
import os
import webbrowser
from collections.abc import Iterable

import numpy as np
from bokeh.io.export import get_layout_html
from bokeh.layouts import column, row
from bokeh.models import Band, BoxAnnotation, Div, LabelSet, Span

from .enums import Position
from .utilities import get_min_max


class Plot:
    """Base class for all other plots"""

    _div_title, _div_header, _div_footer = None, None, None

    def __init__(self, output_dir: str, x_axis_label: str = "x", y_axis_label: str = "y", **options):
        """Base class for interactive plots

        Note: Not intended to be used directly and instead, please use one of the subclasses which implement the
        actual visualisation(s)

        Parameters
        ----------
        output_dir : str
            output path - not really used but it might be as some point if we want to export individual plot
        x_axis_label : str
            x-axis label
        y_axis_label : str
            y-axis label
        tools : str
            list of Bokeh tools supplied to the plot
        options :
            dictionary with key:value parameters used to prettify Bokeh plots
        """
        self.name = None
        self.output_dir = output_dir
        self.plot_type = None
        self.plots = dict()
        self.figure = None
        self._layout = None
        self.source = None
        self.annotations = dict()
        self.div_title = options.pop("title", "")
        self.div_header = options.pop("header", "")
        self._div_header_pos: Position = options.pop("header_pos", Position.ABOVE)
        self.div_footer = options.pop("footer", "")
        self._x_extents = []
        self._y_extents = []

        # plot attributes
        self.options = options
        self.metadata = dict(x_axis_label=x_axis_label, y_axis_label=y_axis_label)

    def set_figure_attributes(self):
        """Initialize common plot attributes"""
        self.figure.xaxis.axis_label_text_baseline = "bottom"
        self.figure.xaxis.axis_label = self.metadata["x_axis_label"]
        self.figure.yaxis.axis_label = self.metadata["y_axis_label"]

    def set_title(self, text: str, bold: bool = True):
        """Set title text on the title div"""
        if bold:
            text = f"<b>{text}</b>"
        self.div_title.text = text

    @property
    def div_title(self):
        """Return title"""
        return Div(text="<b>%s</b>" % self._div_title)

    @div_title.setter
    def div_title(self, value):
        """Set title"""
        self._div_title = value

    def set_header(self, text: str):
        """Set header text on the header div"""
        self._div_header = text
        self.div_header.text = text

    @property
    def div_header(self):
        """Return header"""
        return Div(text=self._div_header)

    @div_header.setter
    def div_header(self, value):
        """Set title"""
        self._div_header = value

    def set_footer(self, text: str):
        """Set footer text on the footer div"""
        self.div_footer.text = text

    @property
    def div_footer(self):
        """Return footer"""
        return Div(text=self._div_footer, visible=True if self._div_footer else False)

    @div_footer.setter
    def div_footer(self, value):
        """Set title"""
        self._div_footer = value

    @property
    def layout(self):
        """Get layout"""
        return self.set_layout()

    def set_ranges(self):
        """Set x/y-axis range"""

    def set_layout(self, init_range: bool = True):
        """Setup plot layout

        Each plot consists of three elements:
        TITLE DIV - title of the plot
        FIGURE - Bokeh Plot instance
        ANNOTATION DIV - any comments/annotations provided for particular plot

        --- to be added in the future ---
        TOOLS - interactive tools added for improved visualisation and control purposes
        """
        layout = [self.div_title]
        if self._div_header_pos == Position.ABOVE:
            layout.extend([self.div_header, self.figure])
        elif self._div_header_pos == Position.LEFT:
            layout.append(row(self.div_header, self.figure))
        elif self._div_header_pos == Position.RIGHT:
            layout.append(row(self.div_header, self.figure))
        else:
            layout.extend([self.div_header, self.figure])
        layout.append(self.div_footer)
        self._layout = column(*layout)
        if init_range:
            self.set_ranges()
        return self._layout

    def link_axes(self, x_range=None, y_range=None):
        """Link x- and/or y-axis ranges to another plot"""
        # if x_range:
        #     if hasattr(x_range, "figure"):
        #         x_range.figure.x_range = self.figure.x_range
        #         # x_range = x_range.figure.x_range
        #     # self.figure.x_range = x_range
        # if y_range:
        #     if hasattr(x_range, "figure"):
        #         y_range = x_range.figure.y_range
        #     self.figure.y_range = y_range

    def add_extents(self, x: np.ndarray = None, y: np.ndarray = None):
        """Add x-axis extents"""
        if x is not None:
            self._x_extents.append(get_min_max(x))
        if y is not None:
            self._y_extents.append(get_min_max(y))

    def get_extents(self, **kwargs):
        """Get x and y-axis extents"""
        x_min, x_max = get_min_max(self._x_extents)
        x_min, x_max = kwargs.get("x_min", x_min), kwargs.get("x_max", x_max)
        y_min, y_max = get_min_max(self._y_extents)
        y_min, y_max = kwargs.get("y_min", y_min), kwargs.get("y_max", y_max)
        return x_min, x_max, y_min, y_max

    def add_box(self, data, **kwargs):
        """Add box annotation to the plot"""
        box = BoxAnnotation(**data, **kwargs)
        self.figure.add_layout(box)
        self.annotations[box.id] = (data, "BoxAnnotation")

    def add_patch(self, data, **kwargs):
        """Add generic polygon/patch to the plot"""
        patch = self.figure.patch(*data, **kwargs)
        self.annotations[patch.id] = (data, "Patch")

    def add_labels(self, source, **kwargs):
        """Add multiple labels to the plot"""
        labels = LabelSet(x="x", y="y", text="text", source=source, **kwargs)
        self.figure.add_layout(labels)
        self.annotations[labels.id] = (source, "LabelSet")

    def add_band(self, source, **kwargs):
        """Add band to the plot"""
        band = Band(
            base="base", lower="lower", upper="upper", source=source, level=kwargs.get("level", "underlay"), **kwargs
        )
        self.figure.add_layout(band)
        self.annotations[band.id] = (source, "Band")

    def add_span(self, data, **kwargs):
        """Add span to the plot"""
        location = data["location"]
        if not isinstance(location, Iterable):
            location = [location]

        for loc in location:
            span = Span(location=loc, dimension=data["dimension"], **kwargs)
            self.figure.add_layout(span)
            self.annotations[span.id] = (dict(location=loc, dimension=data["dimension"]), "Span")

    def save(self, filepath=None, show: bool = True):
        """Save Bokeh plot as HTML file

        Parameters
        ----------
        filepath : str
            path where to save the HTML document
        show : bool
            if 'True', newly generated document will be shown in the browser
        """

        if filepath is None:
            filepath = os.path.join(self.output_dir, self.plot_type + ".html")

        html_str = get_layout_html(self.layout)
        with open(filepath, "wb") as f_ptr:
            f_ptr.write(html_str.encode("utf-8"))

        # open figure in browser
        if show:
            webbrowser.open_new_tab(filepath)
