"""Shared value types for integration results.

Everything downstream (metrics, benchmarks, the Dash app) consumes these
two dataclasses, so integrators and systems never need to know about each
other beyond the interfaces in :mod:`psim.systems.base` and
:mod:`psim.integrators.base`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    pass

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class StepResult:
    """Outcome of a single integrator step.

    Attributes
    ----------
    t:
        Time reached after the step.
    y:
        State reached after the step, shape ``(dim,)``.
    dt_used:
        The step size actually taken (adaptive integrators may shrink it).
    error_estimate:
        Local truncation-error estimate if the method provides one,
        otherwise ``None``.
    """

    t: float
    y: FloatArray
    dt_used: float
    error_estimate: float | None = None


@dataclass(slots=True)
class Trajectory:
    """A time-ordered sequence of states plus bookkeeping for benchmarks.

    Attributes
    ----------
    times:
        Sample times, shape ``(n,)``.
    states:
        States at each sample time, shape ``(n, dim)``.
    method:
        Name of the integrator that produced the trajectory.
    system:
        Name of the system that was integrated.
    rhs_evaluations:
        Total work performed, in right-hand-side-evaluation equivalents.
        For Parker–Sochacki this counts Taylor-coefficient recurrences,
        which is the closest per-unit-work analogue (see the README's
        "measuring work" caveat).
    wall_time:
        Wall-clock seconds spent inside the integration loop.
    events:
        Times at which discrete events (e.g. collisions) were located.
    meta:
        Free-form extras (integrator options, adaptive statistics, ...).
    """

    times: FloatArray
    states: FloatArray
    method: str
    system: str
    rhs_evaluations: int = 0
    wall_time: float = 0.0
    events: list[float] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)

    @property
    def y_final(self) -> FloatArray:
        """State at the final sample time."""
        return self.states[-1]

    @property
    def n_steps(self) -> int:
        """Number of stored steps (samples minus the initial condition)."""
        return len(self.times) - 1

    def component(self, index: int) -> FloatArray:
        """Return the time series of a single state component."""
        return self.states[:, index]
