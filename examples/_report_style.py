"""Shared presentation for the example reports."""

from html import escape
from pathlib import Path

from plotski import Figure

BLUE = "#1f77b4"
ORANGE = "#d95f02"

_STYLES = """
:root {
    color: #172938;
    background: #f2f6f8;
    font-family: system-ui, sans-serif;
    scrollbar-gutter: stable;
}
body { margin: 0; }
.example { max-width: 960px; margin: 0 auto; padding: 32px 24px 48px; }
.example-header {
    padding: clamp(20px, 4vw, 36px);
    border: 1px solid #234654;
    border-radius: 16px;
    background: linear-gradient(130deg, #132a3a, #204c56);
    color: #fff;
}
.example-header h1 { margin: 0; font-size: clamp(1.7rem, 5vw, 2.65rem); line-height: 1.15; }
.example-header p { max-width: 62ch; margin: 12px 0 0; line-height: 1.5; color: #e1edf1; }
.example .plotski-report { margin-top: 22px; min-width: 0; color: #172938; }
.example .plotski-report .plotski-grid {
    border: 1px solid #d9e3e9;
    border-radius: 10px;
    padding: 8px;
    background: #fff;
}
.example .plotski-report [role="tablist"] { border-color: #cedae1; }
.example .plotski-report [role="tab"] { border-radius: 6px 6px 0 0; background: transparent; }
.example .plotski-report [role="tab"][aria-selected="true"] { background: #fff; color: #175476; }
.example .plotski-report [role="tabpanel"] { padding-top: 4px; }
.example .plotski-report .plotski-caption { line-height: 1.5; color: #42596a; }
.example .plotski-report table { width: 100%; background: #fff; font-variant-numeric: tabular-nums; }
.example .plotski-report caption { margin-bottom: 8px; font-size: 1.05rem; }
.example .plotski-report th { background: #e4edf2; }
.example .plotski-report th, .example .plotski-report td { padding: .5rem .7rem; }
.example .plotski-report [data-selection-id]:hover { background: #edf5fa; }
.example .plotski-report tr.plotski-selected { background: #d6eaf7; }
.example .plotski-report .plotski-cell-button { color: #15567c; text-decoration: underline; }
.narrow-caption { display: none; }
@media (max-width: 940px) {
    .narrow-caption { display: block; color: #42596a; font-size: .85rem; }
}
@media (max-width: 560px) {
    .example { padding: 14px 12px 28px; }
    .example .plotski-report table { display: block; overflow-x: auto; }
    .example .plotski-report th, .example .plotski-report td { padding: .4rem .5rem; }
}
"""


def save_report(report: Figure, description: str, destination: Path) -> None:
    """Save a styled, self-contained report as HTML."""
    title = escape(report.title)
    fragment = report.to_html_fragment()
    destination.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>{_STYLES}</style>
</head>
<body>
    <div class="example">
        <header class="example-header">
            <h1>{title}</h1>
            <p>{escape(description)}</p>
        </header>
        <p class="narrow-caption">Scroll charts horizontally to see the full plot.</p>
        {fragment}
    </div>
</body>
</html>
""",
        encoding="utf-8",
    )
