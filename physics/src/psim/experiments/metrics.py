"""Accuracy and conservation metrics computed on trajectories."""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray, Trajectory
from psim.systems.base import ODESystem


def final_error(trajectory: Trajectory, system: ODESystem) -> float | None:
    """Infinity-norm error of the final state against the exact solution.

    Returns ``None`` when the system has no closed-form solution.
    """
    exact = system.exact(float(trajectory.times[-1]))
    if exact is None:
        return None
    return float(np.max(np.abs(trajectory.y_final - exact)))


def trajectory_error(trajectory: Trajectory, system: ODESystem) -> float | None:
    """Maximum infinity-norm error over all recorded samples."""
    errors = []
    for t, y in zip(trajectory.times, trajectory.states, strict=True):
        exact = system.exact(float(t))
        if exact is None:
            return None
        errors.append(np.max(np.abs(y - exact)))
    return float(max(errors))


def energy_drift(trajectory: Trajectory, system: ODESystem, relative: bool = True) -> FloatArray | None:
    """Energy error time series ``E(t) − E(0)`` (relative by default).

    For conservative systems this is the conservation diagnostic; for
    dissipative ones compare it against the exact dissipation instead.
    Returns ``None`` if the system defines no energy.
    """
    e0 = system.energy(trajectory.states[0])
    if e0 is None:
        return None
    drift = np.array([system.energy(y) - e0 for y in trajectory.states])
    return drift / abs(e0) if relative and e0 != 0.0 else drift


def max_energy_drift(trajectory: Trajectory, system: ODESystem) -> float | None:
    """Largest absolute (relative) energy deviation over the run."""
    drift = energy_drift(trajectory, system)
    return None if drift is None else float(np.max(np.abs(drift)))


def invariant_drift(trajectory: Trajectory, system: ODESystem) -> dict[str, float]:
    """Max absolute relative drift of every declared invariant."""
    reference = system.invariants(trajectory.states[0])
    worst = dict.fromkeys(reference, 0.0)
    for y in trajectory.states:
        current = system.invariants(y)
        for key, ref in reference.items():
            scale = max(abs(ref), 1e-30)
            worst[key] = max(worst[key], abs(current[key] - ref) / scale)
    return worst


def convergence_order(dts: FloatArray, errors: FloatArray) -> float:
    """Least-squares slope of log(error) vs log(dt) — the observed order.

    Points where the error has saturated at machine precision (below
    ``1e-14``) are excluded so high-order methods aren't penalized for
    being *too* accurate.
    """
    dts = np.asarray(dts, dtype=float)
    errors = np.asarray(errors, dtype=float)
    keep = errors > 1e-14
    if keep.sum() < 2:
        return float("nan")
    slope, _ = np.polyfit(np.log(dts[keep]), np.log(errors[keep]), 1)
    return float(slope)
