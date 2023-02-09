"""Bokeh plot store"""
import os
import typing as ty
import warnings
import webbrowser

import numpy as np
from bokeh.io import save
from bokeh.layouts import column, gridplot, row
from bokeh.models import ColumnDataSource

try:
    from bokeh.models import TabPanel
except ImportError:
    from bokeh.models.widgets import Panel as TabPanel

try:
    from bokeh.models import Tabs
except ImportError:
    from bokeh.models.widgets import Tabs

from plotski.base import Plot
from plotski.image import PlotImage, PlotImageRGBA
from plotski.scatter import PlotScatter
from plotski.spectrum.plot import PlotCentroid, PlotMultiLine, PlotSpectrum
from plotski.store.containers import Column, Container, Grid, Individual, Row
from plotski.utilities import get_unique_str

# TODO: add repr that shows the layout of the store e.g. tab 1 \ plot 1 plot 2 plot 3; tab 2 \ plot 1 plot 2 plot 3
# TODO: add option to annotate spectrum and heatmap with rois and/or peaks


class PlotStore:
    """Main class that is responsible for managing all plots that should be exported to static HTML document."""

    def __init__(self, output_dir: str = "", options=None, filename="figure-store.html", title: str = "Document Store"):
        self.output_dir = output_dir
        self.filename = filename
        self.options = options

        # setup document parameters
        self.document_title = title

        # store of figures
        self.tabs: ty.Dict[str, ty.Dict[str, Container[Plot]]] = {}

    def __repr__(self) -> str:
        """Print"""
        return f"PlotStore <tabs={len(self.tabs)}>"

    def __getitem__(self, tab: ty.Union[int, str]):
        """Get tab object"""
        if isinstance(tab, int):
            tab = self.tab_names[tab]
        if tab not in self.tabs:
            raise KeyError(f"Tab '{tab}' does not exist")
        return self.tabs[tab]

    def __len__(self) -> int:
        """Get number of tabs"""
        return len(self.tabs)

    @property
    def tab_names(self) -> ty.List[str]:
        """Get list of tab names"""
        return list(self.tabs.keys())

    def check_tab(self, tab_name: str, auto_add: bool = True):
        """Check whether tab exists in the container"""
        if tab_name not in self.tabs:
            if auto_add:
                self.add_tab(tab_name)
            else:
                raise ValueError(f"Missing tab {tab_name}")

    @staticmethod
    def check_data(data: ty.Dict, keys: ty.Iterable):
        """Check whether data is a dictionary and contains appropriate data keys."""
        if not isinstance(data, dict):
            raise ValueError("Provided value of `data` is incorrect. Expected dictionary.")
        missing = []
        for key in keys:
            if key not in data:
                missing.append(key)
        if missing:
            raise ValueError(
                f"Provided data is missing some keys. Expected: {', '.join(keys)}."
                f" Missing keys: {', '.join(missing)}"
            )

    def show(self, tab_names=None, always_as_tabs: bool = True):
        """Return HTML representation of the document"""
        from bokeh.io import show

        return show(self.get_layout(tab_names, always_as_tabs))

    def get_layout(self, tab_names: ty.Optional[ty.List[str]] = None, always_as_tabs: bool = True):
        """Return fully ordered Bokeh document which can be visualised (using 'show' command) or exported as HTML

        Parameters
        ----------
        tab_names : list
            list of tab names which must be present in the `tabs` container
        always_as_tabs : bool
            if 'True', the resultant HTML document will contain 'Tabs' even if only one tab is present

        Returns
        -------
        tabs : Tabs
            Tabs container

        """

        def unpack_figures():
            """Unpack layout elements from item/row/column or grid"""
            return [plot.layout for plot in item_contents]

        # user can specify which tabs they would like to export as HTML document. If 'tab_names' was not specified,
        # we will use all tabs in the exported document
        if tab_names is None:
            tab_names = self.tab_names
        else:
            # let's check if the user supplied single tab name using strings...
            if isinstance(tab_names, str):
                tab_names = [tab_names]

        # check that each tab name is actually present in the tab store
        if not all([tab_name in self.tabs for tab_name in tab_names]):
            raise ValueError("Some of the specified tab names are not present in the figure store")

        # initialize panel store
        panels = []
        # iterate over each tab and append the contents. Here, each panel corresponds to single tab
        for tab_name in tab_names:
            tab_contents = self.tabs[tab_name]
            _tab_contents = []
            # iterate over each object specified in the tab
            for item_name, item_contents in tab_contents.items():
                # items can be specified as an 'item' (single element)
                figures = unpack_figures()
                if isinstance(item_contents, Individual):
                    _tab_contents.extend(figures)
                # row (multiple elements in a row)
                elif isinstance(item_contents, Row):
                    _tab_contents.append(row(figures))
                # column (multiple elements in a column)
                elif isinstance(item_contents, Column):
                    _tab_contents.append(column(figures))
                # grid (multiple elements in a grid):
                elif isinstance(item_contents, Grid):
                    _tab_contents.append(gridplot(figures, ncols=item_contents.n_cols))

            if not _tab_contents:
                print("Tab was empty - not adding it into the HTML document")
                continue
            panels.append(TabPanel(child=column(children=_tab_contents), title=tab_name))

        # if the 'always_as_tabs' toggle is disabled and only one tab is present, the returned object will be column
        # element
        if len(panels) == 1 and not always_as_tabs:
            return panels[0].child

        return Tabs(tabs=panels)

    def save(self, filepath=None, show=True, **kwargs) -> str:
        """Save Bokeh document as HTML file

        Parameters
        ----------
        filepath : Path, optional
            path where to save the HTML document
        show : bool
            if 'True', newly generated document will be shown in the browser
        kwargs :
            parameters to be passed on to the 'get_layout' function
        """

        if filepath is None:
            filepath = os.path.join(self.output_dir, self.filename)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            save(self.get_layout(**kwargs), filepath, title=self.document_title)

        # open figure in browser
        if show:
            webbrowser.open_new_tab(filepath)
        return filepath

    def get_unique_name(self, tab_name: str, basename: str = "item"):
        """Get unique name for an item in specific tab. Names are made unique by adding #NUMBER+1 itself

        Parameters
        ----------
        tab_name : str
            name of the tab
        basename : str
            base name of the unique name, default = 'item'

        Returns
        -------

        """
        i = 0
        while f"{basename} #{i}" in self.tabs[tab_name]:
            i += 1
        return f"{basename} #{i}"

    def add_tab(self, tab_name: str, override=False) -> str:
        """Add new tab to the document

        Parameters
        ----------
        tab_name : str
            name of the tab to be added to the document
        override : bool
            if tab with name `tab_name` already exists and `reset` is set to `True` no exception will be thrown

        Returns
        -------
        tab_name : str
            name of the new tab

        Raises
        ------
        ValueError
            raised if `tab_name` already present in the `self.tabs` container. It will not be thrown if `reset` is set
            to `True
        """
        if tab_name in self.tabs and not override:
            raise ValueError(
                "This tab has previously been added! Please set 'reset' to True if you would like to"
                " override current container."
            )
        self.tabs[tab_name] = {}
        return tab_name

    def add_tabs(self, tab_names: ty.List[str], override=False):
        """Add multiple new tabs to the document

        Parameters
        ----------
        tab_names : List[str]
            List of tab names.
        override : bool, optional
            if tab with name `tab_name` already exists and `reset` is set to `True` no exception will be thrown

        Raises
        ------
        ValueError
            Raised if `tab_name` already present in the `self.tabs` container. It will not be thrown if `reset` is set
            to `True
        """
        for tab_name in tab_names:
            self.add_tab(tab_name, override)

    def add_row(self, tab_name: str) -> str:
        """Add row to particular tab.

        Parameters
        ----------
        tab_name : str
            Name of the tab where row should be added.

        Returns
        -------
        row_name : str
            Name of the generated row container. Name is automatically generated and always unique.
        """
        assert tab_name in self.tabs

        row_name = self.get_unique_name(tab_name, "row")
        self.tabs[tab_name][row_name] = Row()
        return row_name

    def add_col(self, tab_name: str) -> str:
        """Add column to particular tab.

        Parameters
        ----------
        tab_name : str
            Name of the tab where row should be added.

        Returns
        -------
        col_name : str
            Name of the generated column container. Name is automatically generated and always unique.
        """
        assert tab_name in self.tabs

        col_name = self.get_unique_name(tab_name, "col")
        self.tabs[tab_name][col_name] = Column()
        return col_name

    def add_grid(self, tab_name: str, n_cols: ty.Optional[int] = None) -> str:
        """Add grid to particular tab.

        Parameters
        ----------
        tab_name : str
            Name of the tab where grid should be added.
        n_cols : int, optional
            Number of columns the grid should use during rendering. If value is not provided, value will be calculated
            by rounding square root of the number of contained figures.

        Returns
        -------
        grid_name : str
            Name of the generated grid container. Name is automatically generated and always unique.
        """
        assert tab_name in self.tabs

        grid_name = self.get_unique_name(tab_name, "grid")
        grid = Grid()
        grid.n_cols = n_cols
        self.tabs[tab_name][grid_name] = grid
        return grid_name

    def append_item(self, tab_name: str, layout_name: str, plot: Plot):
        """Append plot object to tab/item_name so it can be easily retrieved later on

        Parameters
        ----------
        tab_name : str
            Name of the tab where plot should be added to.
        layout_name : str
            Name of the layout where plot item should be added to. The layout item is present in particular tab.
        plot : Plot
            Plot object that should be added to the layout.
        """
        assert tab_name in self.tabs, f"Tab {tab_name} not found in tabs. Make sure to add it first."
        if layout_name not in self.tabs[tab_name]:
            self.tabs[tab_name][layout_name] = Individual()

        # set the plot name
        plot.name = get_unique_str()
        self.tabs[tab_name][layout_name].append(plot)
        return plot

    def plot_scatter(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds generic scatter to the plot store

        Parameters
        ----------
        tab_name : str
            Name of the tab where plot should be added to.
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                x, y = list / array
            the length of x and y must be the same
        layout_name : str
            By default, plot objects are added to the tab in iterative way (e.g. if there are no plots in the tab, it
            will be added as 'item #0', if there is one then it will be added as 'item #1' etc. Sometimes you might want
            to add it to a 'row' or 'column' for which you have name - you can specify its name here and if its present
            the plot object will be added to that container.
        kwargs :
            dictionary containing plot parameters e.g. x/y axis labels, title, etc...

        Returns
        -------
        tab_name : str
            name of the tab
        item_name : str
            name of the plot
        plot : Plot
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("x", "y"))

        source = ColumnDataSource(data)
        plot = PlotScatter(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_spectrum(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds generic spectrum to the plot store

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                x, y = list / array
            the length of x and y must be the same
        layout_name : str
            By default, plot objects are added to the tab in iterative way (e.g. if there are no plots in the tab, it
            will be added as 'item #0', if there is one then it will be added as 'item #1' etc. Sometimes you might want
            to add it to a 'row' or 'column' for which you have name - you can specify its name here and if its present
            the plot object will be added to that container.
        kwargs :
            dictionary containing plot parameters e.g. x/y axis labels, title, etc...

        Returns
        -------
        tab_name : str
            name of the tab
        item_name : str
            name of the plot
        plot : PlotSpectrum
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("x", "y"))

        source = ColumnDataSource(data)
        plot = PlotSpectrum(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_centroids_x(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds generic spectrum to the plot store

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                x, y0, y1 = list / array
            the length of x and y0 and y1 must be the same.
            If y0 is not provided, values will be automatically generated to provide array of 0s
        layout_name : str
            By default, plot objects are added to the tab in iterative way (e.g. if there are no plots in the tab, it
            will be added as 'item #0', if there is one then it will be added as 'item #1' etc. Sometimes you might want
            to add it to a 'row' or 'column' for which you have name - you can specify its name here and if its present
            the plot object will be added to that container.
        kwargs :
            dictionary containing plot parameters e.g. x/y axis labels, title, etc...

        Returns
        -------
        tab_name : str
            name of the tab
        item_name : str
            name of the plot
        plot : PlotCentroid
            plot object
        """
        self.check_tab(tab_name)
        if "y0" not in data:
            data["y0"] = np.zeros_like(data["x"], dtype=np.int8)
        self.check_data(data, ("x", "y0", "y1"))

        source = ColumnDataSource(data)
        plot = PlotCentroid(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_centroids_y(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds generic spectrum to the plot store

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                x0, x1, y = list / array
            the length of x and y0 and y1 must be the same.
            If x0 is not provided, values will be automatically generated to provide array of 0s
        layout_name : str
            By default, plot objects are added to the tab in iterative way (e.g. if there are no plots in the tab, it
            will be added as 'item #0', if there is one then it will be added as 'item #1' etc. Sometimes you might want
            to add it to a 'row' or 'column' for which you have name - you can specify its name here and if its present
            the plot object will be added to that container.
        kwargs :
            dictionary containing plot parameters e.g. x/y axis labels, title, etc...

        Returns
        -------
        tab_name : str
            name of the tab
        item_name : str
            name of the plot
        plot : PlotCentroid
            plot object
        """
        self.check_tab(tab_name)
        if "x0" not in data:
            data["x0"] = np.zeros_like(data["y"], dtype=np.int8)
        self.check_data(data, ("x0", "x1", "y"))

        source = ColumnDataSource(data)
        plot = PlotCentroid(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_multiline_spectrum(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds multiple-lines to the same plot area

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                xs, ys = list / array
            the length of x and y must be the same
        layout_name : str
            By default, plot objects are added to the tab in iterative way (e.g. if there are no plots in the tab, it
            will be added as 'item #0', if there is one then it will be added as 'item #1' etc. Sometimes you might want
            to add it to a 'row' or 'column' for which you have name - you can specify its name here and if its present
            the plot object will be added to that container.
        kwargs :
            dictionary containing plot parameters e.g. x/y axis labels, title, etc...

        Returns
        -------
        tab_name : str
            name of the tab
        item_name : str
            name of the plot
        plot : PlotMultiLine
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("xs", "ys"))

        source = ColumnDataSource(data)
        plot = PlotMultiLine(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_image(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds image to the plot store

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                image = list with single array
            If the `image` item is not provided as list with single array then it will be automatically placed there.
        layout_name : str
            by default, plot objects are added to the tab in iterative way (e.g. if there are no plots in the tab, it
            will be added as 'item #0', if there is one then it will be added as 'item #1' etc. Sometimes you might want
            to add it to a 'row' or 'column' for which you have name - you can specify its name here and if its present
            the plot object will be added to that container
        kwargs :
            dictionary containing plot parameters e.g. x/y axis labels, title, etc...

        Returns
        -------
        tab_name : str
            name of the tab
        item_name : str
            name of the plot
        plot : PlotImage
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("image",))
        # Bokeh expects nested list to plat an image
        if isinstance(data["image"], np.ndarray):
            data["image"] = [data["image"]]

        source = ColumnDataSource(data)
        plot = PlotImage(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_rgb_image(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds RGBA image to the plot store

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                image = 3D array
            the 'image' item must be embedded in a list otherwise you will be greeted with nasty exception
        layout_name : str
            by default, plot objects are added to the tab in iterative way (e.g. if there are no plots in the tab, it
            will be added as 'item #0', if there is one then it will be added as 'item #1' etc. Sometimes you might want
            to add it to a 'row' or 'column' for which you have name - you can specify its name here and if its present
            the plot object will be added to that container
        kwargs :
            dictionary containing plot parameters e.g. x/y axis labels, title, etc...

        Returns
        -------
        tab_name : str
            name of the tab
        item_name : str
            name of the plot
        plot : Plot
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("image",))
        # Bokeh expects nested list to plat an image
        if isinstance(data["image"], np.ndarray):
            data["image"] = [data["image"]]

        source = ColumnDataSource(data)
        plot = PlotImageRGBA(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def add_line_plot(self, plot, data: ty.Dict, **kwargs):
        """Adds generic spectrum to the plot store

        Parameters
        ----------
        plot : PlotSpectrum
            plot object where line spectrum should be added to
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                x, y = list / array
            the length of x and y must be the same
        kwargs :
            dictionary containing plot parameters e.g. x/y axis labels, title, etc...

        Returns
        -------
        tab_name : str
            name of the tab
        item_name : str
            name of the plot
        plot : Plot
            plot object
        """
        self.check_data(data, ("x", "y"))
        source = ColumnDataSource(data)
        plot.add_plot_line(source, **kwargs)

    def add_band(self, plot, data: ty.Dict, **kwargs):
        """Add band to the plot area to highlight specific region, display standard deviation of display errors

        Parameters
        ----------
        plot : Plot
            plot object to add the band to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                base = the orthogonal coordinates of the upper and lower values
                lower = the coordinates of the lower portion of the filled area band
                upper = the coordinates of the upper portion of the filled area band
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields

        Examples
        --------
        >>> import numpy as np
        >>> x = np.arange(10)
        >>> y = np.arange(10)
        >>> store = PlotStore("")
        >>> _, _, plot = store.plot_spectrum("plot", dict(x=x, y=y))
        >>> store.add_band(plot, dict(base=x, lower=y-3, upper=y+3))
        """
        if not hasattr(plot, "add_band"):
            raise ValueError("Cannot add band to this plot")
        self.check_data(data, ("base", "lower", "upper"))
        source = ColumnDataSource(data)
        plot.add_band(source, **kwargs)

    def add_span(self, plot, data: ty.Dict, **kwargs):
        """Add span line(s) to the plot area

        You can specify multiple lines simultaneously by setting the `location` key to an iterable. In case multiple
        values are provided, they will have the same `dimension`

        Parameters
        ----------
        plot : Plot
            plot object to add the band to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                location = the location of the span along `dimension`
                dimension = the direction of the span. Can be either `height` (y-direction) or `width` (x-direction)
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields

        Examples
        --------
        >>> import numpy as np
        >>> x = np.arange(10)
        >>> y = np.arange(10)
        >>> store = PlotStore("")
        >>> _, _, plot = store.plot_spectrum("plot", dict(x=x, y=y))
        >>> store.add_span(plot, dict(location=1, dimension="width"))
        >>> store.add_span(plot, dict(location=1, dimension="height"))
        >>> store.add_span(plot, dict(location=[5, 3], dimension="height"))
        """
        if not hasattr(plot, "add_span"):
            raise ValueError("Cannot add band to this plot")
        self.check_data(data, ("location", "dimension"))
        plot.add_span(data, **kwargs)

    def add_box(self, plot, data: ty.Dict, **kwargs):
        """Add box to the plot area to highlight region of interest

        Parameters
        ----------
        plot : Plot
            plot object to add the band to
        data : dict
            dictionary containing appropriate plot fields - not all of the these need to be defined, so for instance
            specifying `bottom` will result in a box annotation that spans from the `bottom` to the edge of the plot
            area and if you specify `top` and `left` will result in box annotation that starts at `top` and `left`
            and spans to the edge of the plot. Specifying all four attributes will result box of the size that
            highlights specifying area and might not span the entire plot area
            in this case:
                bottom = the y-coordinates of the bottom edge of the box annotation
                top = the y-coordinates of the top edge of  the box annotation
                left = the x-coordinates of the left edge of the box annotation
                right = the x-coordinates of the right edge of the box annotation
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields

        Examples
        --------
        >>> import numpy as np
        >>> x = np.arange(10)
        >>> y = np.arange(10)
        >>> store = PlotStore("")
        >>> _, _, plot = store.plot_spectrum("plot", dict(x=x, y=y))
        >>> store.add_box(plot, dict(bottom=1, right=3, top=4, left=2), line_width=5, line_color="red")
        >>> store.add_box(plot, dict(bottom=3, right=7))
        >>> store.add_box(plot, dict(top=4, left=2))
        """
        if not hasattr(plot, "add_box"):
            raise ValueError("Cannot add box to this plot")
        self.check_data(data, ("bottom", "top", "left", "right"))
        plot.add_box(data, **kwargs)

    def add_patch(self, plot, data: ty.List[ty.List], **kwargs):
        """Add patch/polygon to the plot area to highlight region of interest

        Parameters
        ----------
        plot : Plot
            plot object to add the band to
        data : list of lists
            formatted list of x and y coordinates in format [[x1, x2, x3], [y1, y2, y3]]
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields
        """
        assert isinstance(data, list)
        if not hasattr(plot, "add_patch"):
            raise ValueError("Cannot add box to this plot")
        plot.add_patch(data, **kwargs)

    def add_labels(self, plot, data: ty.Dict, **kwargs):
        """Add label set to an plot/image

        Parameters
        ----------
        plot : Plot
            plot object to add the band to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                x = the x-coordinates of the labels
                y = the y-coordinates of the labels
                text = the labels that go with the x/y coordinates
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields

        Examples
        --------
        >>> import numpy as np
        >>> x = np.arange(10)
        >>> y = np.arange(10)
        >>> store = PlotStore("")
        >>> _, _, plot = store.plot_spectrum("plot", dict(x=x, y=y))
        >>> store.add_labels(plot, dict(x=[3, 4], y=[3, 4], text=["label 1", "label 2"]))
        """
        assert isinstance(data, dict)
        if not hasattr(plot, "add_labels"):
            raise ValueError("Cannot add band to this plot")
        self.check_data(data, ("x", "y", "text"))
        source = ColumnDataSource(data)
        plot.add_labels(source, **kwargs)

    def add_segments(self, plot: PlotSpectrum, data: ty.Dict, **kwargs):
        """Add label set to an plot/image

        Parameters
        ----------
        plot : PlotSpectrum
            plot object to add the band to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                x0 = the start of the x-coordinates for each line
                x1 = the end of the x-coordinates for each line
                y0 = the start of the y-coordinates for each vertical line
                y1 = the end of the y-coordinates for each vertical line
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields

        Examples
        --------
        >>> import numpy as np
        >>> x = np.arange(10)
        >>> y = np.arange(10)
        >>> store = PlotStore("")
        >>> _, _, plot = store.plot_spectrum("plot", dict(x=x, y=y))
        >>> store.add_segments(plot, dict(x0=[0, 9], x1=[9, 0], y0=[0, 0], y1=[10, 10]))
        """
        if not hasattr(plot, "add_segments"):
            raise ValueError("Cannot add segments to this plot")
        self.check_data(data, ("x0", "x1", "y0", "y1"))
        source = ColumnDataSource(data)
        plot.add_segments(source, **kwargs)

    def add_centroids_x(self, plot: PlotSpectrum, data: ty.Dict, **kwargs):
        """Add vertical centroids/lines to a particular plot

        Parameters
        ----------
        plot : PlotSpectrum
            plot object to add the band to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                x = the x-coordinates for each for each line
                y0 = the start of the y-coordinates for each vertical line
                y1 = the end of the y-coordinates for each vertical line
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields

        Examples
        --------
        >>> import numpy as np
        >>> x = np.arange(10)
        >>> y = np.arange(10)
        >>> store = PlotStore("")
        >>> _, _, plot = store.plot_spectrum("plot", dict(x=x, y=y))
        >>> store.add_centroids_x(plot, dict(x=[1, 2, 3], y0=[0, 0, 0], y1=[3, 5, 7]))
        """
        assert isinstance(data, dict)
        if not hasattr(plot, "add_centroids_x"):
            raise ValueError("Cannot add centroids to this plot")
        if "y0" not in data:
            data["y0"] = np.zeros_like(data["x"], dtype=np.int8)
        self.check_data(data, ("x", "y0", "y1"))
        source = ColumnDataSource(data)
        plot.add_centroids_x(source, **kwargs)

    def add_centroids_y(self, plot: PlotSpectrum, data: ty.Dict, **kwargs):
        """Add horizontal centroids/lines to a particular plot

        Parameters
        ----------
        plot : PlotSpectrum
            plot object to add the band to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                x0 = the start of the x-coordinates for each horizontal line
                x1 = the end of the x-coordinates for each horizontal
                y = the y-coordinate position for each line
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields

        Examples
        --------
        >>> import numpy as np
        >>> x = np.arange(10)
        >>> y = np.arange(10)
        >>> store = PlotStore("")
        >>> _, _, plot = store.plot_spectrum("plot", dict(x=x, y=y))
        >>> store.add_centroids_y(plot, dict(x0=[0, 0, 0], x1=[1, 2, 3], y=[3, 5, 7]))
        """
        if not hasattr(plot, "add_centroids_y"):
            raise ValueError("Cannot add centroids to this plot")
        self.check_data(data, ("y", "x0", "x1"))
        source = ColumnDataSource(data)
        plot.add_centroids_y(source, **kwargs)

    def add_scatter(self, plot: PlotSpectrum, data: ty.Dict, **kwargs):
        """Add scatter points to a particular plot

        Parameters
        ----------
        plot : PlotSpectrum
            plot object to add the band to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                x = the start of the x-coordinates for each horizontal line
                y = the y-coordinate position for each line
        kwargs :
            dictionary containing plot parameters e.g. line width, line color, transparency, etc...
            must be valid Bokeh fields

        Examples
        --------
        >>> import numpy as np
        >>> x = np.arange(10)
        >>> y = np.arange(10)
        >>> store = PlotStore("")
        >>> _, _, plot = store.plot_spectrum("plot", dict(x=x, y=y))
        >>> store.add_scatter(plot, dict(x0=[0, 0, 0], x1=[1, 2, 3], y=[3, 5, 7]))
        """
        if not hasattr(plot, "add_scatter"):
            raise ValueError("Cannot add scatter points to this plot")
        self.check_data(data, ("x", "y"))
        source = ColumnDataSource(data)
        plot.add_scatter(source, **kwargs)

    @staticmethod
    def link_plots(plot_one: Plot, plot_two: Plot, x_axis: bool = False, y_axis: bool = False):
        """Link the x/y-axis of two plots"""
        if not x_axis and not y_axis:
            return
        if x_axis:
            plot_two.figure.x_range = plot_one.figure.x_range
        if y_axis:
            plot_one.figure.y_range = plot_two.figure.y_range
