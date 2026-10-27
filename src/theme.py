"""Palette and chart defaults, kept in Python so charts and CSS cannot drift apart.

Values mirror assets/ramp.css. They approximate Ramp's public brand and are not
official Ramp brand assets; DESIGN.md records the sources.
"""

from __future__ import annotations

from pathlib import Path

INK = "#1C1B17"
INK_70 = "#55534C"
INK_40 = "#908D84"
RULE = "#E3E1DA"
PAPER = "#FFFFFF"
PAPER_WARM = "#F7F6F3"
LIME = "#E5FE54"
LIME_DEEP = "#C9E33C"
HIGHLIGHT = "#E4F222"
FLAG = "#B4451F"

FONT_UI = "Lausanne, Inter, Helvetica Neue, Helvetica, Arial, sans-serif"
FONT_DISPLAY = "Burgess, Instrument Serif, Iowan Old Style, Georgia, serif"

# Ordered ramp for root causes. Ramp's identity is near-monochrome with one
# accent, so the series scale is a single-hue ink ramp and the accent is
# reserved for the thing the reader is meant to act on.
CAUSE_SCALE = ["#1C1B17", "#4A4740", "#77736A", "#A5A098", "#CFCBC2"]

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "ramp.css"


def css() -> str:
    """Inline the token sheet for Streamlit, which has no static asset route."""
    return CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""


def altair_theme() -> dict:
    """Chart defaults: hairline axes, no gridlines on the category axis, ink type."""
    return {
        "config": {
            "background": PAPER,
            "font": FONT_UI,
            "view": {"stroke": "transparent", "continuousWidth": 560, "continuousHeight": 260},
            "axis": {
                "labelColor": INK_70,
                "titleColor": INK_40,
                "labelFontSize": 11,
                "titleFontSize": 10,
                "titleFontWeight": 600,
                "domainColor": RULE,
                "tickColor": RULE,
                "gridColor": RULE,
                "gridDash": [2, 3],
            },
            "legend": {
                "labelColor": INK_70,
                "titleColor": INK_40,
                "labelFontSize": 11,
                "titleFontSize": 10,
                "orient": "bottom",
                "direction": "horizontal",
                "symbolType": "square",
            },
            "range": {"category": CAUSE_SCALE},
            "bar": {"color": INK},
            "line": {"color": INK, "strokeWidth": 2},
            "point": {"filled": True, "color": INK},
            "title": {"color": INK, "fontSize": 13, "fontWeight": 600, "anchor": "start"},
        }
    }


def enable_altair_theme(name: str = "ramp") -> None:
    """Register and enable the chart theme across Altair 4 and 5 APIs.

    Altair 5.5 moved theme registration from `alt.themes` to `alt.theme` and
    deprecated the old path. Supporting both keeps the app running on whatever
    version a reviewer's environment resolves.
    """
    import altair as alt

    if hasattr(alt, "theme") and hasattr(alt.theme, "register"):
        alt.theme.register(name, enable=True)(altair_theme)
    else:  # Altair < 5.5
        alt.themes.register(name, altair_theme)
        alt.themes.enable(name)
