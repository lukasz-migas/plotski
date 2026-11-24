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

A figure or tab displays plots, grids, text, and tables in insertion order.
Content added directly to the figure appears above the tabs. Use
`add_text(text, kind="heading")` for headings, `kind="caption"` for captions,
and `add_table({"Sample": ["A"], "Peaks": [84]})` for tabular data. Text and
table cells are plain text.

Grid coordinates are zero-based. Omit both coordinates to fill the first slot
that fits, scanning rows from left to right. Use `rowspan` and `colspan` to cover
several cells. Set `cell_width` and `cell_height` on a grid, or `width` and
`height` on a standalone subplot, to size panels in pixels.

## Charts and annotations

| Methods | Data and options |
| --- | --- |
| `line(x, y)`, `scatter(x, y)` | Overlay series by calling the methods on the same subplot. Set `label` for a legend entry. |
| `segments(x0, y0, x1, y1)` | Draw independent segments, including centroid sticks. |
| `bar(x, y)` | Use numeric, date, or categorical x coordinates. Width is in axis units, or milliseconds on a date axis. |
| `bars(categories, series, mode="grouped")` | Plot named series side by side or use `mode="stacked"`. The series mapping determines legend and stack order. Positive and negative stacks build from zero independently. |
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

`report.link_axes(left, right)` also links numeric or date axes across grids and
tabs. Linked axes share scale and direction. Use
`plot.configure_axis("y", scale="log", tick_format=".1e")` for positive intensity
ranges or `plot.configure_axis("x", reverse=True, tick_format=".2f")` for a
reversed numeric axis. Limits stay in data units on a log axis. Nonpositive
line and scatter coordinates produce gaps. Zero-baseline marks such as bars
and centroid sticks require a linear y axis.

Use `y_error=(lower_delta, upper_delta)` on `scatter` and `bar`. Each delta can
be a scalar or one value per point. With `bars`, pass a mapping from series
name to its pair of deltas.

## Scientific workflows

Use `spectrum()` or `mobilogram()` for profile traces, and `centroid=True` for
sticks. Call the method again to overlay a series or pass `mirror=True` for
the lower half of a butterfly plot. Hover shows the original intensity for
mirrored data. Axis labels default to `m/z` or `Drift time (bins)` and
`Intensity`, and you can supply labels when creating the subplot.

```python
from plotski import Figure

report = Figure(title="Annotated spectrum", lazy_tabs=True)
report.add_text("Sample and reference", kind="heading")
sample = report.add_tab("Sample")
plot = sample.add_subplot(title="Sample spectrum", width=640, height=320)
plot.spectrum([100, 101, 102], [4, 9, 1], label="Observed", max_points=2000)
plot.scatter(
    [101], [9], label="Assigned peaks", ids=["p1"], selection_group="peaks",
    hover_fields={"Compound": ["Candidate A"], "Error (ppm)": [0.427]},
    hover_formats={"x": ".4f", "Error (ppm)": ".2f"},
)
sample.add_table(
    {"Peak": ["p1"], "Compound": ["Candidate A"], "Error (ppm)": [0.43]},
    title="Peak assignments", ids=["p1"], selection_group="peaks",
)

reference = report.add_tab("Reference").add_subplot(title="Reference spectrum")
reference.spectrum([100, 101, 103], [2, 8, 3], centroid=True)
report.link_axes(plot, reference)
report.save("annotated-spectrum.html")
```

Click a peak or a table row to highlight matching IDs in the same
`selection_group`. Click it again to clear the selection. The IDs are strings,
with one per plotted point or row. Repeated IDs highlight all their matches.
`hover_fields` accepts one value per point and `hover_formats` uses Python
format specs keyed by field or coordinate name. For segments, the coordinate
names are `x0`, `y0`, `x1`, and `y1`.

`max_points` applies to profile lines. Sampling keeps endpoints, gaps and
local extrema, with matching hover values. A line with many separate runs
can exceed its point budget to preserve gaps. With `lazy_tabs=True`, an
inactive tab's plots mount on first open. Its data is included in the HTML
so the report works offline.

## Export and native customization

`report.to_html()` returns the full document, `report.save(path)` writes it,
and `report.show()` opens a temporary file in the default browser and returns
its path. Exports embed the backend's JavaScript by default. Use
`resources="cdn"` for a smaller file that loads JavaScript over the network.

In a trusted Jupyter notebook, put `report` in the last line of a cell to
display it inline. For a host page, use `report.to_html_fragment()`. To embed
several reports with the same backend version, include `report.html_resources()`
once in the host and use `report.to_html_fragment(resources=None)` for each
report.

Use `plot.save_image("spectrum.png", scale=2)` to export a subplot and
`grid.save_image("comparison.svg")` for a whole grid. See
[installation](installation.md#static-image-export) for browser and exporter
requirements. PNG scaling increases pixel resolution. In SVG exports, image
and heatmap data remain raster content.

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
