"""Implicit linear multistep methods: BDF2.

BDF2 is the workhorse of production stiff solvers (it is the fixed-order
core of VODE/LSODA's stiff mode and of most circuit and CFD time
steppers): A-stable like the trapezoidal rule, but with genuine damping
at infinity (stiffly accurate), so fast transients decay instead of
ringing — while staying second order, unlike backward Euler.

Being a *multistep* method it needs the previous solution point, which
is the interesting implementation problem in an event-driven driver:
after a collision response the state jumps and yesterday's history is a
lie. The implementation therefore validates continuity on every call —
if the incoming ``(t, y)`` is not the point the last step produced, the
history is discarded and the step restarts with one trapezoidal step
(second order, so the restart does not pollute the convergence order).
Unequal consecutive spans (the driver shortens steps at output and
event boundaries) are handled with the variable-step BDF2 coefficients
rather than a restart.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray, StepResult
from psim.integrators.base import Integrator, register_integrator
from psim.integrators.implicit import BackwardEuler, _numerical_jacobian
from psim.systems.base import ODESystem


@register_integrator("bdf2")
class BDF2(Integrator):
    """Second-order backward differentiation formula.

    Constant-step form ``y⁺ = (4yₙ − yₙ₋₁)/3 + (2h/3)·f(t⁺, y⁺)``;
    for consecutive spans ``h_prev, h`` with ratio ``r = h/h_prev`` the
    variable-step coefficients are used::

        y⁺ = [(1+r)² yₙ − r² yₙ₋₁] / (1+2r)  +  h(1+r)/(1+2r) · f(t⁺, y⁺)

    Each step solves the implicit relation with Newton's method (exact
    Jacobian when the system provides one, forward differences
    otherwise). The first step after any (re)start is one backward-Euler
    step: its single O(dt²) local error does not reduce the global
    second order, and unlike a trapezoidal starter it cannot ring on a
    stiff transient.

    Parameters
    ----------
    newton_tol, max_newton_iter:
        Newton convergence tolerance (infinity norm of the update) and
        iteration cap.
    """

    order = 2

    def __init__(self, newton_tol: float = 1e-12, max_newton_iter: int = 25) -> None:
        self.newton_tol = newton_tol
        self.max_newton_iter = max_newton_iter
        self._starter = BackwardEuler(newton_tol, max_newton_iter)
        # History: (t_prev, y_prev) one point back, and the (t, y) this
        # integrator last produced — used to detect continuation breaks.
        self._prev: tuple[float, FloatArray] | None = None
        self._last: tuple[float, FloatArray] | None = None

    def _continuing(self, t: float, y: FloatArray) -> bool:
        """Whether ``(t, y)`` is exactly the point the last step produced.

        Also requires genuine forward progress since the history point:
        the event locator probes zero-length steps, which would otherwise
        leave ``t == t_prev`` and a division by zero in the step ratio.
        """
        if self._prev is None or self._last is None:
            return False
        t_last, y_last = self._last
        if t - self._prev[0] <= 1e-13 * max(1.0, abs(t)):
            return False
        return abs(t - t_last) <= 1e-12 * max(1.0, abs(t)) and bool(np.array_equal(y, y_last))

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        if not self._continuing(t, y):
            result = self._starter.step(system, t, y, dt)
            self._prev = (t, y.copy())
            self._last = (result.t, result.y.copy())
            return result

        t_prev, y_prev = self._prev
        r = dt / (t - t_prev)
        denom = 1.0 + 2.0 * r
        history = ((1.0 + r) ** 2 * y - r**2 * y_prev) / denom
        beta = dt * (1.0 + r) / denom

        t_new = t + dt
        y_new = y + dt * system.rhs(t, y)  # explicit Euler predictor
        identity = np.eye(y.size)
        for _ in range(self.max_newton_iter):
            if hasattr(system, "jacobian"):
                jac_rhs = system.jacobian(t_new, y_new)
            else:
                jac_rhs = _numerical_jacobian(system, t_new, y_new)
            residual = y_new - history - beta * system.rhs(t_new, y_new)
            delta = np.linalg.solve(identity - beta * jac_rhs, -residual)
            y_new = y_new + delta
            if float(np.max(np.abs(delta))) < self.newton_tol * max(
                1.0, float(np.max(np.abs(y_new)))
            ):
                break

        self._prev = (t, y.copy())
        self._last = (t_new, y_new.copy())
        return StepResult(t_new, y_new, dt)
