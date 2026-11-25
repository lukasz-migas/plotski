# Plotski

Plotski builds interactive HTML reports from Python. Add plots, tables, and
notes to a page, then save one file that can be opened in a browser or shared
with a colleague. Bokeh is included; install the Plotly extra to choose Plotly
for a report.

A report can pair a mass spectrum with ion images, link their axes, and include
a table of measured signals. With the default inline resources, the saved
report works offline.

## Create a report

Install Plotski, make a figure, add a subplot, and save the report as HTML:

```python
from plotski import Figure

report = Figure(title="Run overview")
plot = report.add_subplot(title="Signal by sample", x_label="Sample", y_label="Signal")
plot.bar(["Control", "Treated"], [84, 91])
report.save("run-overview.html")
```

Open `run-overview.html` in a browser. Add tabs or grids as a report grows, or
use the Plotly backend with `Figure(backend="plotly")`.

## Explore the guides

- [Installation](installation.md) covers the Bokeh and Plotly extras, plus
  browser requirements for static image export.
- [Usage](usage.md) shows chart types, annotations, linked axes, scientific
  workflows, and embedding.
- [Example reports](examples.md) describe reports for support
  operations, a packaging trial, and imaging mass spectrometry.
- [Changelog](history.md) records published changes.
