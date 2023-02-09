"""Custom plots."""
from bokeh.models import ColumnDataSource

from plotski.spectrum.plot import PlotButterflySpectrum, PlotCentroid, PlotSpectrum


class PlotCentroidMassSpectrum(PlotCentroid):
    """Plot centroid mass spectrum"""

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label="m/z",
        y_axis_label="Intensity",
        title="Centroid Mass Spectrum",
        **kwargs,
    ):
        PlotCentroid.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="centroid-mass-spectrum",
            **kwargs,
        )


class PlotMassSpectrum(PlotSpectrum):
    """Mass spectrum plot"""

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "m/z",
        y_axis_label: str = "Intensity",
        title: str = "Mass Spectrum",
        **kwargs,
    ):
        PlotSpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="mass-spectrum",
            **kwargs,
        )


class PlotMobilogram(PlotSpectrum):
    """Mobilogram plot"""

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "Drift time (bins)",
        y_axis_label: str = "Intensity",
        title: str = "Mobilogram",
        **kwargs,
    ):
        PlotSpectrum.__init__(
            self,
            output_dir,
            source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="mobilogram",
            **kwargs,
        )


class PlotButterflyMassSpectrum(PlotButterflySpectrum):
    """Make butterfly mass spectrum"""

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "m/z",
        y_axis_label: str = "Intensity",
        title: str = "Butterfly Mass Spectrum",
        **kwargs,
    ):
        PlotButterflySpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="butterfly-mass-spectrum",
            **kwargs,
        )


class PlotButterflyMobilogram(PlotButterflySpectrum):
    """Make butterfly mobilogram"""

    def __init__(
        self,
        output_dir: str,
        source: ColumnDataSource,
        x_axis_label: str = "Drift time (bins)",
        y_axis_label: str = "Intensity",
        title: str = "Butterfly Mobilogram",
        **kwargs,
    ):
        PlotButterflySpectrum.__init__(
            self,
            output_dir,
            source=source,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            title=title,
            plot_type="butterfly-mobilogram",
            **kwargs,
        )
