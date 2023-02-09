"""Plot store."""
import typing as ty

import numpy as np
from bokeh.models import ColumnDataSource

from plotski.spectrum.custom import (
    PlotButterflyMassSpectrum,
    PlotButterflyMobilogram,
    PlotCentroidMassSpectrum,
    PlotMassSpectrum,
    PlotMobilogram,
)
from plotski.store import PlotStore


class CustomPlotStore(PlotStore):
    """Plot store with extra functionality."""

    def plot_mass_spectrum(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds mass spectrum to the plot store

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                x = list / array
                y = list / array
            the length of x and y must be the same
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
        plot : PlotMassSpectrum
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("x", "y"))

        source = ColumnDataSource(data)
        plot = PlotMassSpectrum(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        plot = self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_butterfly_mass_spectrum(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds butterfly mass spectra to the plot store (one on top / one below)

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                x_top, y_top, x_bottom, y_bottom = list / array
            the length of x_top and y_top, x_bottom and y_bottom must be the same.
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
        plot : PlotButterflyMassSpectrum
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("x_top", "y_top", "x_bottom", "y_bottom"))

        source = ColumnDataSource(data=data)
        plot = PlotButterflyMassSpectrum(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_centroid_mass_spectrum(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds centroid mass spectrum to the plot store

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
        plot : PlotCentroidMassSpectrum
            plot object
        """
        self.check_tab(tab_name)
        if "y0" not in data:
            data["y0"] = np.zeros_like(data["x"], dtype=np.int8)
        self.check_data(data, ("x", "y0", "y1"))

        source = ColumnDataSource(data)
        plot = PlotCentroidMassSpectrum(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_mobilogram(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds mobilogram to the plot store

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            dictionary containing appropriate plot fields
            in this case:
                x, y = list / array
            the length of x and y must be the same
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
        plot : PlotMobilogram
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("x", "y"))

        source = ColumnDataSource(data)
        plot = PlotMobilogram(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot

    def plot_butterfly_mobilogram(self, tab_name, data: ty.Dict, layout_name=None, **kwargs):
        """Adds butterfly mobilograms to the plot store (one on top / one below)

        Parameters
        ----------
        tab_name : str
            name of the tab where plot should be added to
        data : dict
            Dictionary containing appropriate plot fields, in this case:
                x_top, y_top, x_bottom, y_bottom = list / array
            the length of x_top and y_top, x_bottom and y_bottom must be the same.
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
        plot : PlotButterflyMobilogram
            plot object
        """
        self.check_tab(tab_name)
        self.check_data(data, ("x_top", "y_top", "x_bottom", "y_bottom"))

        source = ColumnDataSource(data)
        plot = PlotButterflyMobilogram(self.output_dir, source=source, **kwargs)

        # add figure object to tab
        layout_name = layout_name if layout_name is not None else self.get_unique_name(tab_name)
        self.append_item(tab_name, layout_name, plot)
        return tab_name, layout_name, plot
