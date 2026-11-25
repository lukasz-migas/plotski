# Example reports

Run this command from the repository root to generate the reports with Bokeh
and Plotly:

```sh
uv run --extra plotly python examples/generate.py
```

The command writes six HTML files to `examples/output/`. Open a file in a
browser to explore it. Each report includes its data and JavaScript, so it also
works offline.

The base installation generates Bokeh reports. Pass `--output-dir` to save
the files elsewhere.

```sh
uv run python examples/generate.py --backend bokeh
uv run --extra plotly python examples/generate.py --backend plotly --output-dir /tmp/plotski-reports
```

## Support operations

Open `support-operations-bokeh.html` or `support-operations-plotly.html`.
Zoom or pan either chart in **Weekly trends** to update the date range in both.
The response chart shows the median response time, the middle half of response
times, and a four-hour target. **Channel breakdown** compares the final two
weeks.

## Packaging trial

Open `packaging-trial-bokeh.html` or `packaging-trial-plotly.html`.
In **Parcel review**, hover over a point to see the parcel ID, packing method,
cost, and time. Click a point or its row in the inspection table to highlight
the matching item. Click again to clear the selection. **Packing time** compares
the distributions, medians, and interquartile ranges for both methods.

## Imaging mass spectrometry

Open `imaging-mass-spectrometry-bokeh.html` or
`imaging-mass-spectrometry-plotly.html`. Hover over either marked peak in
**Spectrum** to see its ion, then open **Ion images** to inspect its spatial
signal. Both images share an intensity scale. **Region comparison** shows the
pixel intensity distributions and medians for the outlined regions.

All examples use seeded, simulated data. The report builders contain the
plotting code, and `_report_style.py` adds the shared HTML wrapper.
