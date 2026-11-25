# Example reports

From the repository root, generate the reports with Bokeh and Plotly.

```sh
uv run --extra plotly python examples/generate.py
```

The six HTML files are written to `examples/output/`. Open any of them in
your browser. The reports include all the data and JavaScript they need
to work offline.

Generate only the Bokeh reports with the base installation, or pass
`--output-dir` to choose a different folder.

```sh
uv run python examples/generate.py --backend bokeh
uv run --extra plotly python examples/generate.py --backend plotly --output-dir /tmp/plotski-reports
```

## Support operations

Open `support-operations-bokeh.html` or `support-operations-plotly.html`.
Zoom or pan either chart in **Weekly trends** to change the date range in both.
The response chart shows the median, the middle 50% of response times, and
a four-hour target. Open **Channel breakdown** to compare the final two weeks.

## Packaging trial

Open `packaging-trial-bokeh.html` or `packaging-trial-plotly.html`.
Hover over a point in **Parcel review** to see the parcel ID, packing method,
cost, and time. Click the point or its row in the inspection table to highlight
both. Click it again to clear the selection. Open **Packing time** to compare
the distributions and median with the interquartile range for each method.

## Imaging mass spectrometry

Open `imaging-mass-spectrometry-bokeh.html` or
`imaging-mass-spectrometry-plotly.html`. Hover over the two marked peaks in
**Spectrum**, then find the corresponding signals in **Ion images**. Zoom
either image to compare the same locations on the shared intensity scale.
Open **Region comparison** for box plots and medians from the outlined pixels.

All examples use seeded, simulated data. See the report builders for the
plotting calls and `_report_style.py` for the shared HTML wrapper.
