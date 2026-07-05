"""Plotly theme and method → style mapping for the Dash app.

Color encodes the method *family* (validated 4-hue categorical palette:
worst adjacent CVD ΔE 13.3, all ≥ 3:1 on the light surface); line dash
is the secondary encoding that distinguishes methods within a family.
Assignments are fixed per method — filtering never repaints survivors.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

# Chart chrome (light surface).
SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

#: Family → hue (validated categorical set, in fixed order:
#: worst adjacent CVD ΔE 13.3, all ≥ 3:1 on the light surface).
FAMILY_COLORS = {
    "explicit": "#2a78d6",
    "symplectic": "#008300",
    "implicit": "#e34948",
    "series": "#4a3aa7",
    "structural": "#eb6834",
}

#: Method label → (color, dash). Fixed for the life of the app.
METHOD_STYLES: dict[str, tuple[str, str]] = {
    "Euler": (FAMILY_COLORS["explicit"], "dot"),
    "Midpoint (RK2)": (FAMILY_COLORS["explicit"], "dash"),
    "RK4": (FAMILY_COLORS["explicit"], "solid"),
    "RKF45 (adaptive)": (FAMILY_COLORS["explicit"], "dashdot"),
    "Backward Euler": (FAMILY_COLORS["implicit"], "dot"),
    "Implicit midpoint": (FAMILY_COLORS["implicit"], "solid"),
    "Trapezoidal": (FAMILY_COLORS["implicit"], "dash"),
    "BDF2": (FAMILY_COLORS["implicit"], "longdash"),
    "Generalized-alpha (rho 0.9)": (FAMILY_COLORS["structural"], "solid"),
    "Symplectic Euler": (FAMILY_COLORS["symplectic"], "dot"),
    "Velocity Verlet": (FAMILY_COLORS["symplectic"], "solid"),
}


def method_style(label: str) -> tuple[str, str]:
    """Style for a method label; PSM variants all wear the series hue."""
    if label in METHOD_STYLES:
        return METHOD_STYLES[label]
    if label.startswith("PSM"):
        return (FAMILY_COLORS["series"], "dash" if "adaptive" in label else "solid")
    if label.startswith("Generalized-alpha"):
        return (FAMILY_COLORS["structural"], "solid")
    return (MUTED, "solid")


def base_figure(title: str, x_title: str, y_title: str, **layout: Any) -> go.Figure:
    """A figure with the shared chrome: recessive grid, system sans, no fluff."""
    fig = go.Figure()
    fig.update_layout(
        title={"text": title, "font": {"size": 15, "color": INK}},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": 'system-ui, -apple-system, "Segoe UI", sans-serif', "color": INK_SECONDARY},
        margin={"l": 60, "r": 20, "t": 50, "b": 50},
        legend={"font": {"size": 12}},
        hovermode="closest",
        **layout,
    )
    axis_common = {
        "gridcolor": GRID,
        "linecolor": BASELINE,
        "zerolinecolor": BASELINE,
        "title_font": {"size": 12, "color": MUTED},
        "tickfont": {"size": 11, "color": MUTED},
    }
    fig.update_xaxes(title_text=x_title, **axis_common)
    fig.update_yaxes(title_text=y_title, **axis_common)
    return fig


def line_trace(
    x, y, label: str, hovertemplate: str | None = None, style_key: str | None = None  # noqa: ANN001
) -> go.Scatter:
    """A method line+marker trace wearing its fixed style.

    ``style_key`` looks up the style when the display ``label`` carries
    extra annotation (e.g. an observed slope suffix).
    """
    color, dash = method_style(style_key or label)
    return go.Scatter(
        x=x,
        y=y,
        name=label,
        mode="lines+markers",
        line={"color": color, "dash": dash, "width": 2},
        marker={"size": 7, "color": color},
        hovertemplate=hovertemplate,
    )
