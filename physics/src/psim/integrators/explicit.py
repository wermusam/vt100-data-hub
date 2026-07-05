"""Explicit Runge–Kutta methods: Euler, midpoint, RK4, and adaptive RKF45.

The classical single-step baselines. All of them evaluate the right-hand
side at trial points inside the step; none has free dense output; all
share the conditional-stability weakness on stiff problems that the
implicit family exists to fix.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray, StepResult
from psim.integrators.base import Integrator, register_integrator
from psim.systems.base import ODESystem


@register_integrator("euler")
class ExplicitEuler(Integrator):
    """Forward Euler: ``y ← y + dt·f(t, y)``. Order 1, one RHS call."""

    order = 1

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        return StepResult(t + dt, y + dt * system.rhs(t, y), dt)


@register_integrator("midpoint")
class ExplicitMidpoint(Integrator):
    """Explicit midpoint (RK2). Order 2, two RHS calls."""

    order = 2

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        k1 = system.rhs(t, y)
        k2 = system.rhs(t + 0.5 * dt, y + 0.5 * dt * k1)
        return StepResult(t + dt, y + dt * k2, dt)


@register_integrator("rk4")
class RungeKutta4(Integrator):
    """The classical fourth-order Runge–Kutta method. Four RHS calls."""

    order = 4

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        k1 = system.rhs(t, y)
        k2 = system.rhs(t + 0.5 * dt, y + 0.5 * dt * k1)
        k3 = system.rhs(t + 0.5 * dt, y + 0.5 * dt * k2)
        k4 = system.rhs(t + dt, y + dt * k3)
        return StepResult(t + dt, y + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4), dt)


# Fehlberg 4(5) coefficients.
_A = (
    (),
    (1 / 4,),
    (3 / 32, 9 / 32),
    (1932 / 2197, -7200 / 2197, 7296 / 2197),
    (439 / 216, -8.0, 3680 / 513, -845 / 4104),
    (-8 / 27, 2.0, -3544 / 2565, 1859 / 4104, -11 / 40),
)
_C = (0.0, 1 / 4, 3 / 8, 12 / 13, 1.0, 1 / 2)
_B5 = (16 / 135, 0.0, 6656 / 12825, 28561 / 56430, -9 / 50, 2 / 55)
_B4 = (25 / 216, 0.0, 1408 / 2565, 2197 / 4104, -1 / 5, 0.0)


@register_integrator("rkf45")
class RKF45(Integrator):
    """Runge–Kutta–Fehlberg 4(5) with embedded-error step control.

    :meth:`advance` sub-steps adaptively until the requested output
    interval is covered; the ``tol`` parameter (not the nominal ``dt``)
    controls accuracy, which is how adaptive methods enter the
    work–precision benchmarks.

    Parameters
    ----------
    tol:
        Target local error per step (absolute, per component).
    safety, min_factor, max_factor:
        Standard step-controller guards.
    """

    order = 5

    def __init__(
        self,
        tol: float = 1e-8,
        safety: float = 0.9,
        min_factor: float = 0.2,
        max_factor: float = 5.0,
    ) -> None:
        if tol <= 0:
            raise ValueError("tol must be positive")
        self.tol = tol
        self.safety = safety
        self.min_factor = min_factor
        self.max_factor = max_factor

    def _stages(
        self, system: ODESystem, t: float, y: FloatArray, dt: float
    ) -> tuple[FloatArray, FloatArray]:
        k = []
        for row, c in zip(_A, _C, strict=True):
            y_trial = y + dt * sum(a * ki for a, ki in zip(row, k, strict=False))
            k.append(system.rhs(t + c * dt, y_trial))
        y5 = y + dt * sum(b * ki for b, ki in zip(_B5, k, strict=True))
        y4 = y + dt * sum(b * ki for b, ki in zip(_B4, k, strict=True))
        return y5, y5 - y4

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        y5, err = self._stages(system, t, y, dt)
        return StepResult(t + dt, y5, dt, error_estimate=float(np.max(np.abs(err))))

    def advance(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        t_target = t + dt
        h = dt
        last_h = h
        while t < t_target - 1e-12 * max(1.0, abs(t_target)):
            h = min(h, t_target - t)
            y5, err_vec = self._stages(system, t, y, h)
            err = float(np.max(np.abs(err_vec)))
            if err <= self.tol or h <= 1e-12:
                t, y, last_h = t + h, y5, h
            # Standard PI-free controller: err ~ h^5 locally.
            factor = self.safety * (self.tol / max(err, 1e-300)) ** 0.2
            h *= min(self.max_factor, max(self.min_factor, factor))
        return StepResult(t, y, last_h)
