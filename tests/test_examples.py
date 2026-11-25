"""Smoke tests for the example report command."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("backend", ["bokeh", "plotly"])
def test_generate_reports(backend: str, tmp_path: Path) -> None:
    if backend == "plotly":
        pytest.importorskip("plotly")
    output = tmp_path / "example reports"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples" / "generate.py"),
            "--backend",
            backend,
            "--output-dir",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    reports = {
        "support-operations": ("Support operations", ["Weekly trends", "Channel breakdown"], "Channel totals"),
        "packaging-trial": ("Packaging trial", ["Parcel review", "Packing time"], "Parcel inspection"),
        "imaging-mass-spectrometry": (
            "Imaging mass spectrometry",
            ["Spectrum", "Ion images", "Region comparison"],
            "Median pixel signals (a.u.)",
        ),
    }
    assert {path.name for path in output.iterdir()} == {f"{name}-{backend}.html" for name in reports}
    for name, (heading, tabs, table) in reports.items():
        html = (output / f"{name}-{backend}.html").read_text(encoding="utf-8")
        assert f"<h1>{heading}</h1>" in html
        assert f'data-backend="{backend}"' in html
        assert all(f">{tab}</button>" in html for tab in tabs)
        assert f"<caption>{table}</caption>" in html
        assert "<script src=" not in html
