"""Example packaging trial report with linked point and table selection."""

import numpy as np
from _report_style import BLUE, ORANGE

from plotski import Figure
from plotski.figure import Backend


def build_report(backend: Backend) -> Figure:
    """Compare material cost and packing time for two packing methods."""
    rng = np.random.default_rng(324)
    methods = ["Standard", "Revised"]
    count = 12
    parcel_ids = [[f"{prefix}-{i:02d}" for i in range(1, count + 1)] for prefix in ("STD", "REV")]
    inspection_ids = [parcel_id for ids in parcel_ids for parcel_id in ids]
    cost = np.round(rng.normal([[1.36], [1.15]], 0.08, size=(2, count)), 2)
    time = np.round(rng.normal([[62], [50]], [[7], [6]], size=(2, count)), 1)

    report = Figure(backend=backend, title="Packaging trial", lazy_tabs=True)
    parcels = report.add_tab("Parcel review")
    parcels.add_text("Select a point or parcel ID to highlight its match. Select it again to clear.", kind="caption")
    scatter = parcels.add_subplot(
        title="Material cost vs. packing time",
        x_label="Material cost (USD)",
        y_label="Packing time (s)",
        width=860,
        height=330,
    )
    for method, ids, parcel_cost, parcel_time, color in zip(
        methods, parcel_ids, cost, time, (BLUE, ORANGE), strict=True
    ):
        scatter.scatter(
            parcel_cost,
            parcel_time,
            label=method,
            color=color,
            size=10,
            ids=ids,
            selection_group="parcels",
            hover_fields={"Parcel": ids, "Method": [method] * count},
            hover_formats={"x": ".2f", "y": ".1f"},
        )
    parcels.add_table(
        {
            "Parcel ID": inspection_ids,
            "Method": np.repeat(methods, count),
            "Cost (USD)": [f"{value:.2f}" for value in cost.flat],
            "Packing time (s)": [f"{value:.1f}" for value in time.flat],
        },
        title="Parcel inspection",
        ids=inspection_ids,
        selection_group="parcels",
    )

    variability = report.add_tab("Packing time")
    variability.add_text(
        "Compare the full distribution with the median and middle 50% of packing times.", kind="caption"
    )
    grid = variability.add_grid(rows=1, cols=2, cell_width=420, cell_height=310)
    distribution = grid.add_subplot(title="Time by method", y_label="Packing time (s)")
    distribution.boxplot(time.ravel(), categories=np.repeat(methods, count), color=BLUE)
    summary = grid.add_subplot(title="Median and interquartile range", y_label="Packing time (s)")
    lower, median, upper = np.quantile(time, [0.25, 0.5, 0.75], axis=1)
    summary.scatter(methods, median, y_error=(median - lower, upper - median), size=10, color=BLUE)
    grid.link_axes(distribution, summary, x=False, y=True)
    return report
