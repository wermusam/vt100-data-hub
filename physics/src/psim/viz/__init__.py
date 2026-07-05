"""Visualization: Plotly theme and the Dash application.

The Dash app itself is imported lazily (``python -m psim.viz.dash_app``)
so that the numerics packages never pay the Dash import cost.
"""

from __future__ import annotations

from psim.viz import theme

__all__ = ["theme"]
