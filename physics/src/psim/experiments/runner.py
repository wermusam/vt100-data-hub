"""Experiment runner: sweeps of (system × method × control) → tidy DataFrames.

The runner treats fixed-step and adaptive methods uniformly through
:class:`MethodSpec`: a fixed-step method is controlled by its step size
``dt``, an adaptive method by its tolerance. Every run produces one row
with the same metric columns, so downstream plotting (the Dash app) is a
single ``plotly.express`` call per figure.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from psim.experiments import metrics
from psim.integrators.base import Integrator, simulate
from psim.systems.base import ODESystem, PolynomialODE, SeparableSystem


@dataclass(frozen=True, slots=True)
class MethodSpec:
    """A benchmarkable method: how to build it and what knob controls it.

    Attributes
    ----------
    label:
        Display name used in tables and legends.
    build:
        Factory mapping the control value to a ready integrator.
    control:
        ``"dt"`` — the value is the (output) step size — or ``"tol"`` —
        the value is an error tolerance and the integrator sub-steps
        adaptively inside a fixed output interval.
    family:
        Grouping used for color/ordering in plots
        (``explicit`` / ``implicit`` / ``symplectic`` / ``series``).
    """

    label: str
    build: Callable[[float], Integrator]
    control: str = "dt"
    family: str = "explicit"

    def __post_init__(self) -> None:
        if self.control not in ("dt", "tol"):
            raise ValueError("control must be 'dt' or 'tol'")


def applicable(spec: MethodSpec, system: ODESystem) -> bool:
    """Whether ``spec`` can integrate ``system`` at all.

    Symplectic methods need separable mechanics; Parker–Sochacki needs a
    polynomial lifting. Everything else applies universally.
    """
    probe = spec.build(1e-2)
    if probe.requires_separable and not isinstance(system, SeparableSystem):
        return False
    if probe.requires_polynomial and not isinstance(system, PolynomialODE):
        return False
    return True


def run_point(
    system: ODESystem,
    spec: MethodSpec,
    control_value: float,
    t_end: float,
    dt_out: float | None = None,
) -> dict[str, object]:
    """Run one (system, method, control-value) cell and compute metrics.

    Returns a flat dict (one DataFrame row). Failures that are *results*
    — an explicit method blowing up on a stiff problem produces ``inf``
    or ``nan`` — are recorded, not raised, so stability maps come out of
    the same pipeline.
    """
    integrator = spec.build(control_value)
    dt = control_value if spec.control == "dt" else (dt_out or t_end / 64.0)
    trajectory = simulate(system, integrator, t_end=t_end, dt=dt)
    row: dict[str, object] = {
        "system": system.name,
        "method": spec.label,
        "family": spec.family,
        "control": spec.control,
        "value": control_value,
        "rhs_evals": trajectory.rhs_evaluations,
        "wall_time": trajectory.wall_time,
        "n_events": len(trajectory.events),
        "final_error": metrics.final_error(trajectory, system),
        "energy_drift": metrics.max_energy_drift(trajectory, system),
    }
    for key, drift in metrics.invariant_drift(trajectory, system).items():
        row[f"drift_{key}"] = drift
    return row


def run_sweep(
    system: ODESystem,
    specs: Iterable[MethodSpec],
    values: Iterable[float],
    t_end: float,
    dt_out: float | None = None,
) -> pd.DataFrame:
    """Full grid of methods × control values on one system.

    Methods that don't apply to the system (see :func:`applicable`) are
    skipped silently; a cell that raises (e.g. a Newton solve on a
    detonated state) is recorded with null metrics so the grid stays
    rectangular.
    """
    rows = []
    for spec in specs:
        if not applicable(spec, system):
            continue
        for value in values:
            try:
                rows.append(run_point(system, spec, value, t_end, dt_out))
            except (FloatingPointError, ValueError, OverflowError, np.linalg.LinAlgError):
                rows.append(
                    {
                        "system": system.name,
                        "method": spec.label,
                        "family": spec.family,
                        "control": spec.control,
                        "value": value,
                        "rhs_evals": None,
                        "wall_time": None,
                        "n_events": None,
                        "final_error": None,
                        "energy_drift": None,
                    }
                )
    return pd.DataFrame(rows)
