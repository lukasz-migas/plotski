"""Top-level package for plotski.

Plotski is meant to make it easier to create static HTML documents.
"""

from plotski.base import Plot  # noqa
from plotski.figure import Figure as Figure
from plotski.figure import Grid as Grid
from plotski.figure import Tab as Tab
from plotski.store import PlotStore  # noqa
from plotski.store.custom import CustomPlotStore  # noqa
from plotski.subplot import Subplot as Subplot

__author__ = "Lukasz G. Migas"
__email__ = "l.g.migas@tudelft.nl"
__version__ = "0.1.0"
