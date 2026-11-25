# plotski

[![PyPI](https://img.shields.io/pypi/v/plotski.svg)](https://pypi.org/project/plotski/)
[![Docs](https://readthedocs.org/projects/plotski/badge/?version=latest)](https://plotski.readthedocs.io/en/latest/?version=latest)
[![CI](https://github.com/lukasz-migas/plotski/actions/workflows/ci.yml/badge.svg)](https://github.com/lukasz-migas/plotski/actions/workflows/ci.yml)

Plotski builds interactive HTML reports with Bokeh or Plotly. Add plots to
tabs and subplot grids, layer scientific annotations, and link axes for
synchronized navigation.

Bokeh is included. Install `plotski[plotly]` to also use Plotly. Plotski
supports Python 3.10+ and NumPy 2+.

```python
from plotski import Figure

report = Figure(title="Run overview")
grid = report.add_tab("Spectra").add_grid(rows=2, cols=1)
sample = grid.add_subplot(title="Sample", x_label="m/z")
reference = grid.add_subplot(title="Reference", x_label="m/z")
sample.line([100, 101, 102], [4, 9, 1], label="Observed")
reference.line([100, 101, 103], [2, 8, 0])
grid.link_axes(sample, reference)
report.save("run-overview.html")
```

Use `Figure(backend="plotly")` for Plotly reports. See the
[usage guide](docs/usage.md) for charts, annotations, and native customization.
Existing `PlotStore` and `CustomPlotStore` reports continue to use Bokeh.

Generate the [example reports](examples/README.md) to try linked dates, point
and table selection, statistical comparisons, and mass spectra with ion images
in both backends.

## Licence
Free software: MIT license

## Documentation
https://plotski.readthedocs.io
