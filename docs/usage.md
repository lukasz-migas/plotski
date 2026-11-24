# Interactive reports

Choose a backend when creating a figure. Bokeh is the default. Set
`backend="plotly"` with the [Plotly extra](installation.md) installed.

```python
from plotski import Figure

report = Figure(backend="bokeh", title="Run overview")
report.add_subplot(title="QC summary").bar(["Sample", "Reference"], [84, 91])

spectra = report.add_tab("Spectra")
grid = spectra.add_grid(rows=2, cols=2)
sample = grid.add_subplot(0, 0, colspan=2, title="Sample", x_label="m/z", y_label="Intensity")
sample.line([100, 101, 102], [4, 9, 1], label="Observed")
sample.scatter([101], [9], color="orange", label="Peak")
sample.reference_line(101)
reference = grid.add_subplot(title="Reference", x_label="m/z", y_label="Intensity")
reference.line([100, 101, 103], [2, 8, 0])
grid.link_axes(sample, reference)

report.save("run-overview.html")
```

A figure or tab stacks standalone subplots and grids in the order they are added.
Content added directly to the figure appears above the tabs. Grid coordinates are
zero-based. Omit both coordinates to fill the first slot that fits, scanning rows
from left to right. Use `rowspan` and `colspan` to cover several cells. A grid with
one row or one column provides a horizontal or vertical arrangement.

## Charts and annotations

| Methods | Data and options |
| --- | --- |
| `line(x, y)`, `scatter(x, y)` | Overlay series by calling the methods on the same subplot. Set `label` for a legend entry. |
| `segments(x0, y0, x1, y1)` | Draw independent segments, including centroid sticks. |
| `bar(x, y)` | Use numeric, date, or categorical x coordinates. Width is in axis units, or milliseconds on a date axis. |
| `histogram(values, bins=10)` | Use a positive bin count or increasing bin edges. Set `density=True` to normalize area to one. |
| `boxplot(values, categories=...)` | Optionally supply a category per observation. Uses Tukey whiskers and shows outliers. |
| `area(x, y, baseline=0)`, `band(x, lower, upper)` | Fill between a curve and a baseline, or between two curves. |
| `heatmap(z)` | Display a scalar raster. Set `cmap`, `z_min`, `z_max`, or `colorbar=False` to control the scale. |
| `image(pixels)` | Display an array with shape `(rows, columns, 3 or 4)` and channels from 0 to 255. |
| `reference_line(value, axis="x")`, `rectangle(left, bottom, right, top)`, `polygon(x, y)`, `labels(x, y, text)` | Highlight coordinates, regions, and points. |

Raster `extent=(left, right, bottom, top)` gives the outer edges in data
coordinates. The default extent is `(0, columns, 0, rows)`.
`origin="upper"` puts the first array row at the top. Set `origin="lower"`
to put it at the bottom. Missing scalar pixels are transparent.

Set `x_label`, `y_label`, `x_limits`, and `y_limits` when adding a subplot or
assign them on the returned object. Leave limits unset to fit the data. Use
`grid.link_axes(left, right, x=True, y=True)` to synchronize both axes within
a grid. Linked numeric or date axes start with the union of their data ranges
unless an explicit range is supplied. Linked categorical axes share their
category order. Use `legend=False` or `hover=False` on the subplot to disable
those interactions across its layers.

## Scientific workflows

A mass spectrum or mobilogram is a `line` with labels such as `"m/z"` or
`"Drift time (bins)"` and `"Intensity"`. Add multiple lines for a spectrum
overlay, or negate the second intensity array for a butterfly plot.
Use a zero baseline for centroid sticks.

```python
import numpy as np

mz = np.array([100, 101, 102])
intensity = np.array([4, 9, 1])
plot = report.add_subplot(title="Centroids", x_label="m/z", y_label="Intensity")
plot.segments(mz, np.zeros_like(intensity), mz, intensity, label="Centroids")
```

## Export and native customization

`report.to_html()` returns the full document, `report.save(path)` writes it,
and `report.show()` opens a temporary file in the default browser and returns
its path. Exports embed the backend's JavaScript by default. Use
`resources="cdn"` for a smaller file that loads JavaScript over the network.

`grid.to_native()` builds a fresh Bokeh `GridBox` or Plotly `Figure`.
Use `grid.configure_native(callback)` to apply native customizations on every
render, including HTML export.

```python
def move_toolbar(layout):
    for plot, *_ in layout.children:
        if hasattr(plot, "toolbar_location"):
            plot.toolbar_location = "above"

grid.configure_native(move_toolbar)  # Bokeh
```

## Migrating from PlotStore

Existing Bokeh reports can continue to use `PlotStore` and `CustomPlotStore`.
To use the shared interface, keep the tab or grid returned by `add_tab()` or
`add_grid()`. Replace `store.plot_spectrum(tab, {"x": x, "y": y})` with
`tab.add_subplot().line(x, y)`. Add overlays and annotations directly to that
subplot. Use `grid.configure_native()` for customizations previously made
through `plot.figure`.
