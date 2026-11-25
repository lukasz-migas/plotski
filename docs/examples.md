# Example reports

The example reports use simulated data to show how plots, tables, tabs, and
linked axes fit together in a saved HTML report. Their charts remain
interactive in the browser, including hover values and linked selections.

Clone the repository and generate all six reports with Bokeh and Plotly:

```sh
uv run --extra plotly python examples/generate.py
```

The HTML files appear in `examples/output/`. To create reports with one
backend, pass `--backend bokeh` or `--backend plotly`. The Bokeh backend works
with the base install. Plotly requires the Plotly extra.

## Support operations

The [support operations builder](https://github.com/lukasz-migas/plotski/blob/main/examples/support_operations.py)
creates a daily ticket volume chart and a response time chart. Pan or zoom
either chart to update the date range in both. A second tab compares ticket
channels over two weeks.

## Packaging trial

The [packaging trial builder](https://github.com/lukasz-migas/plotski/blob/main/examples/packaging_trial.py)
compares cost and packing time for two methods. Selecting a point highlights
the matching row in a table. A second tab compares the time distributions and
their median ranges.

## Imaging mass spectrometry

The [imaging mass spectrometry builder](https://github.com/lukasz-migas/plotski/blob/main/examples/imaging_mass_spectrometry.py)
links marked peaks in a spectrum to ion images and regional signal summaries.
Both ion images share an intensity scale, and outlined regions match the
regions in the comparison plots.
