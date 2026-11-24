"""Example support operations report with linked date axes."""

import numpy as np
from _report_style import BLUE, ORANGE

from plotski import Figure
from plotski.figure import Backend


def build_report(backend: Backend) -> Figure:
    """Compare daily support volume, response time, and ticket channels."""
    rng = np.random.default_rng(671)
    days = np.arange("2026-03-02", "2026-03-30", dtype="datetime64[D]")
    channels = ["Email", "Chat", "Portal"]
    weekday = np.arange(len(days)) % 7 < 5
    rate = np.where(weekday, 1.0, 0.62)
    channel_counts = rng.poisson(np.array([75, 50, 30])[:, None] * rate)
    volume = channel_counts.sum(axis=0)
    response_base = 2.4 + 0.55 * np.sin(np.arange(len(days)) / 2.8)
    response_base[15:19] += [1.1, 2.2, 1.5, 0.7]
    response_times = [
        np.quantile(rng.lognormal(np.log(base), 0.35, size=int(count)), [0.25, 0.5, 0.75])
        for base, count in zip(response_base, volume, strict=True)
    ]
    lower, median, upper = np.asarray(response_times).T

    report = Figure(backend=backend, title="Support operations", lazy_tabs=True)
    trends = report.add_tab("Weekly trends")
    trends.add_text("Zoom or pan either chart to follow the same dates in both.", kind="caption")
    tickets = trends.add_subplot(title="Daily ticket volume", y_label="Tickets received", width=860, height=240)
    tickets.area(days, volume, color=BLUE, opacity=0.15, hover=False)
    tickets.line(days, volume, color=BLUE, width=3, hover_formats={"x": "%b %d", "y": ".0f"})
    response = trends.add_subplot(
        title="First response time", x_label="Date", y_label="Hours", width=860, height=270, y_limits=(0, 7)
    )
    response.band(days, lower, upper, color=BLUE, opacity=0.18, label="25th to 75th percentile")
    response.line(days, median, color=BLUE, width=3, label="Daily median", hover_formats={"x": "%b %d", "y": ".2f"})
    response.reference_line(4, axis="y", color=ORANGE, width=2)
    report.link_axes(tickets, response)
    trends.add_text("The orange line marks the four-hour first response target.", kind="caption")

    breakdown = report.add_tab("Channel breakdown")
    breakdown.add_text("Monday to Sunday totals for the final two weeks of March.", kind="caption")
    previous = channel_counts[:, 14:21].sum(axis=1)
    current = channel_counts[:, 21:28].sum(axis=1)
    by_channel = breakdown.add_subplot(title="Tickets by channel", y_label="Tickets received", width=860, height=320)
    by_channel.bars(channels, {"Mar 16-22": previous, "Mar 23-29": current})
    breakdown.add_table(
        {
            "Channel": channels,
            "Mar 16-22": previous,
            "Mar 23-29": current,
            "Change": [f"{n:+d}" for n in current - previous],
        },
        title="Channel totals",
    )
    return report
