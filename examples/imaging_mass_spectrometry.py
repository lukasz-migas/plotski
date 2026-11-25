"""Example report comparing spectra, ion images, and regional signals."""

import numpy as np
from _report_style import BLUE, ORANGE

from plotski import Figure
from plotski.figure import Backend


def build_report(backend: Backend) -> Figure:
    """Show how two simulated ion signals vary across a sample."""
    rng = np.random.default_rng(720)
    width, height = 96, 72
    x, y = np.meshgrid(np.arange(width) + 0.5, np.arange(height) + 0.5)
    sample = ((x - 48) / 42) ** 2 + ((y - 36 + 3 * np.sin(x / 13)) / 28) ** 2 <= 1
    centers = [(31, 40), (65, 32)]
    names = ["Region A", "Region B"]
    radius = 8
    masks = [sample & ((x - cx) ** 2 + (y - cy) ** 2 <= radius**2) for cx, cy in centers]
    masses = [734.57, 798.54]
    ions = []
    for (cx, cy), strength in zip(centers, (85, 72), strict=True):
        spot = np.exp(-0.5 * (((x - cx) / 12) ** 2 + ((y - cy) / 9) ** 2))
        background = rng.gamma(shape=2, scale=2, size=x.shape)
        ions.append(np.where(sample, strength * spot + background, np.nan))
    color_limit = float(np.ceil(np.nanmax(ions) / 10) * 10)

    report = Figure(backend=backend, title="Imaging mass spectrometry", lazy_tabs=True)
    spectra = report.add_tab("Spectrum")
    spectra.add_text(
        "Compare the two region profiles. Hover over a marked peak to find the ion shown in the maps.",
        kind="caption",
    )
    spectrum = spectra.add_subplot(title="Mean spectra by region", y_label="Signal (a.u.)", width=860, height=340)
    mz = np.linspace(695, 835, 5601)
    other_masses = [703.51, 719.53, 751.56, 772.59, 813.60, 827.62]
    peak_mz = np.array([*other_masses, *masses])
    peak_shapes = np.exp(-0.5 * ((mz[:, None] - peak_mz) / 0.15) ** 2)
    for index, (name, mask, color) in enumerate(zip(names, masks, (BLUE, ORANGE), strict=True)):
        mean_signals = [float(image[mask].mean()) for image in ions]
        heights = np.array([*rng.uniform(6, 36, len(other_masses)), *mean_signals])
        spectrum.spectrum(mz, peak_shapes @ heights, label=name, color=color, max_points=1800)
        spectrum.scatter(
            [masses[index]],
            [mean_signals[index]],
            size=10,
            color=color,
            hover_fields={"Ion": [f"m/z {masses[index]:.2f}"], "Region": [name]},
            hover_formats={"x": ".2f", "y": ".1f"},
        )
    for mass in masses:
        spectrum.reference_line(mass, color="#708493", opacity=0.4)

    maps = report.add_tab("Ion images")
    maps.add_text(
        "Both ion images use the same intensity scale. The outlines mark the regions used in the box plots.",
        kind="caption",
    )
    extent = (0, width, 0, height)
    outline = np.linspace(0, 2 * np.pi, 73)
    map_grid = maps.add_grid(rows=1, cols=2, cell_width=420, cell_height=320)
    map_panels = []
    for index, (mass, image) in enumerate(zip(masses, ions, strict=True)):
        panel = map_grid.add_subplot(title=f"Ion image at m/z {mass:.2f}", x_label="X (px)", y_label="Y (px)")
        panel.heatmap(
            image,
            extent=extent,
            origin="lower",
            cmap="magma",
            z_min=0,
            z_max=color_limit,
            colorbar=index == 1,
        )
        for (cx, cy), name in zip(centers, names, strict=True):
            xs, ys = cx + radius * np.cos(outline), cy + radius * np.sin(outline)
            panel.segments(xs[:-1], ys[:-1], xs[1:], ys[1:], color="white", width=1, hover=False)
            panel.labels([cx], [cy + radius + 3], [name], color="white")
        map_panels.append(panel)
    map_grid.link_axes(*map_panels, x=True, y=True)

    regions = report.add_tab("Region comparison")
    regions.add_text("Each box summarizes the pixel intensities inside one outlined region.", kind="caption")
    boxes = regions.add_grid(rows=1, cols=2, cell_width=420, cell_height=310)
    categories = [name for name, mask in zip(names, masks, strict=True) for _ in range(int(mask.sum()))]
    box_panels = []
    for mass, image in zip(masses, ions, strict=True):
        panel = boxes.add_subplot(title=f"m/z {mass:.2f} by region", y_label="Pixel signal (a.u.)")
        panel.boxplot(np.concatenate([image[mask] for mask in masks]), categories=categories, color="#4d7483")
        box_panels.append(panel)
    boxes.link_axes(*box_panels, x=False, y=True)
    regions.add_table(
        {
            "Region": names,
            "Pixels": [int(mask.sum()) for mask in masks],
            **{
                f"m/z {mass:.2f}": [f"{np.median(image[mask]):.1f}" for mask in masks]
                for mass, image in zip(masses, ions, strict=True)
            },
        },
        title="Median pixel signals (a.u.)",
    )
    return report
