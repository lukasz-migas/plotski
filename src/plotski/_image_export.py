"""On-demand static export through the selected plotting backend."""

from __future__ import annotations

from collections.abc import Callable
from importlib.util import find_spec
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from plotski.figure import Backend


def save_image(path: str | Path, backend: Backend, render: Callable[[], Any], scale: float) -> Path:
    """Export a fresh native grid and replace the destination on success."""
    destination = Path(path)
    extension = destination.suffix.lower()
    if extension not in (".png", ".svg"):
        raise ValueError("image export requires a .png or .svg destination")
    if isinstance(scale, bool) or not isfinite(scale) or scale <= 0:
        raise ValueError("scale must be positive and finite")
    if extension == ".svg" and scale != 1:
        raise ValueError("scale applies only to PNG export")
    if backend == "bokeh":
        if find_spec("selenium") is None:
            raise ImportError("Install 'plotski[bokeh-export]' and a compatible browser and driver for image export.")
        write = _write_bokeh
    else:
        if find_spec("kaleido") is None:
            raise ImportError("Install 'plotski[plotly-export]' and Chrome or Chromium for image export.")
        write = _write_plotly
    native = render()
    with TemporaryDirectory(prefix=".plotski-", dir=destination.parent) as directory:
        temporary = Path(directory) / f"image{extension}"
        write(native, temporary, scale)
        temporary.replace(destination)
    return destination


def _write_bokeh(native: Any, destination: Path, scale: float) -> None:
    from inspect import signature

    from bokeh.io import export_png, export_svg
    from bokeh.models import Plot

    try:
        if destination.suffix == ".png":
            if scale != 1 and "scale_factor" not in signature(export_png).parameters:
                raise RuntimeError("Scaled PNG export requires the Bokeh version provided by 'plotski[bokeh-export]'.")
            options = {"scale_factor": scale} if scale != 1 else {}
            export_png(native, filename=destination, **options)
        else:
            for plot in native.select({"type": Plot}):
                plot.output_backend = "svg"
            export_svg(native, filename=destination)
        if not destination.is_file():
            raise RuntimeError("The exporter produced no image.")
    except RuntimeError as exc:
        raise RuntimeError(
            f"Bokeh image export failed. Check 'plotski[bokeh-export]' and your browser and driver setup. {exc}"
        ) from exc


def _write_plotly(native: Any, destination: Path, scale: float) -> None:
    try:
        native.write_image(destination, scale=scale)
    except (RuntimeError, ValueError) as exc:
        raise RuntimeError(
            f"Plotly image export failed. Check 'plotski[plotly-export]' and your Chrome or Chromium setup. {exc}"
        ) from exc
