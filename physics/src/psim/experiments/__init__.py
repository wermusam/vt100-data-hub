"""Metrics, sweep runner, and canned benchmark studies."""

from __future__ import annotations

from psim.experiments.metrics import (
    convergence_order,
    energy_drift,
    final_error,
    invariant_drift,
    max_energy_drift,
    trajectory_error,
)
from psim.experiments.runner import MethodSpec, applicable, run_point, run_sweep

__all__ = [
    "MethodSpec",
    "applicable",
    "convergence_order",
    "energy_drift",
    "final_error",
    "invariant_drift",
    "max_energy_drift",
    "run_point",
    "run_sweep",
    "trajectory_error",
]
