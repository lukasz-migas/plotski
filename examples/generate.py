"""Generate standalone HTML versions of the example reports."""

import argparse
from pathlib import Path

import imaging_mass_spectrometry
import packaging_trial
import support_operations
from _report_style import save_report

from plotski.figure import Backend

_REPORTS = (
    (
        "support-operations",
        support_operations.build_report,
        "Four weeks of simulated ticket volume and response times for a customer support team.",
    ),
    (
        "packaging-trial",
        packaging_trial.build_report,
        "Compare material cost and packing time for two methods across 24 simulated parcels.",
    ),
    (
        "imaging-mass-spectrometry",
        imaging_mass_spectrometry.build_report,
        "Follow two simulated ion signals from a mass spectrum to spatial maps and compare their intensities by region.",
    ),
)


def main() -> None:
    """Generate the example reports for the selected backend or backends."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("bokeh", "plotly", "both"), default="both")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "output")
    args = parser.parse_args()
    backends: tuple[Backend, ...] = ("bokeh", "plotly") if args.backend == "both" else (args.backend,)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for backend in backends:
        for name, build_report, description in _REPORTS:
            try:
                report = build_report(backend)
            except ImportError as error:
                parser.exit(1, f"{error}\n")
            destination = args.output_dir / f"{name}-{backend}.html"
            save_report(report, description, destination)
            print(destination)


if __name__ == "__main__":
    main()
