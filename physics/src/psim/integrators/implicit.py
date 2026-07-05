"""Implicit one-step methods: backward Euler, implicit midpoint, trapezoidal.

Each step solves a nonlinear system with Newton's method (analytic
Jacobian when the system provides one, forward differences otherwise).
The payoff is unconditional linear stability: A-stable methods take
steps orders of magnitude beyond the explicit stability limit on stiff
problems, paying per-step with Jacobian work instead.

The implicit midpoint rule earns its place twice over — it is also a
*symplectic* method, so it doubles as the bridge between the implicit
and geometric families in the energy benchmarks.
"""

from __future__ import annotations

import abc

import numpy as np

from psim.core.types import FloatArray, StepResult
from psim.integrators.base import Integrator, register_integrator
from psim.systems.base import ODESystem


def _numerical_jacobian(
    system: ODESystem, t: float, y: FloatArray, eps: float = 1e-7
) -> FloatArray:
    """Forward-difference Jacobian of the right-hand side at ``(t, y)``."""
    f0 = system.rhs(t, y)
    jac = np.empty((y.size, y.size))
    for j in range(y.size):
        step = eps * max(1.0, abs(y[j]))
        y_pert = y.copy()
        y_pert[j] += step
        jac[:, j] = (system.rhs(t, y_pert) - f0) / step
    return jac


class NewtonImplicitIntegrator(Integrator):
    """Shared Newton machinery for one-step implicit methods.

    Subclasses define the step through :meth:`residual_parts`, which
    returns the point(s) at which the RHS enters the implicit relation.

    Parameters
    ----------
    newton_tol:
        Convergence tolerance on the Newton update (infinity norm).
    max_newton_iter:
        Iteration cap; on non-convergence the last iterate is used (the
        benchmarks report accuracy, so a struggling solver shows up as
        error, not as a crash).
    """

    def __init__(self, newton_tol: float = 1e-12, max_newton_iter: int = 25) -> None:
        self.newton_tol = newton_tol
        self.max_newton_iter = max_newton_iter

    @abc.abstractmethod
    def _residual(
        self, system: ODESystem, t: float, y: FloatArray, dt: float, y_new: FloatArray
    ) -> FloatArray:
        """Residual ``F(y_new)`` whose root defines the step."""

    @abc.abstractmethod
    def _residual_jacobian(
        self, jac_rhs: FloatArray, dt: float
    ) -> FloatArray:
        """Jacobian of the residual given the RHS Jacobian at the implicit point."""

    @abc.abstractmethod
    def _implicit_point(
        self, t: float, y: FloatArray, dt: float, y_new: FloatArray
    ) -> tuple[float, FloatArray]:
        """The ``(t, y)`` argument at which the RHS Jacobian is needed."""

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        # Explicit Euler predictor.
        y_new = y + dt * system.rhs(t, y)
        for _ in range(self.max_newton_iter):
            t_j, y_j = self._implicit_point(t, y, dt, y_new)
            if hasattr(system, "jacobian"):
                jac_rhs = system.jacobian(t_j, y_j)
            else:
                jac_rhs = _numerical_jacobian(system, t_j, y_j)
            residual = self._residual(system, t, y, dt, y_new)
            delta = np.linalg.solve(self._residual_jacobian(jac_rhs, dt), -residual)
            y_new = y_new + delta
            if float(np.max(np.abs(delta))) < self.newton_tol * max(
                1.0, float(np.max(np.abs(y_new)))
            ):
                break
        return StepResult(t + dt, y_new, dt)


@register_integrator("backward-euler")
class BackwardEuler(NewtonImplicitIntegrator):
    """Backward Euler: ``y_new = y + dt·f(t+dt, y_new)``.

    Order 1, L-stable — it doesn't just tolerate stiffness, it crushes
    fast transients (excellent for settling granular piles, terrible for
    preserving oscillation amplitude: it damps everything).
    """

    order = 1

    def _residual(self, system, t, y, dt, y_new):  # noqa: ANN001, ANN202
        return y_new - y - dt * system.rhs(t + dt, y_new)

    def _residual_jacobian(self, jac_rhs, dt):  # noqa: ANN001, ANN202
        return np.eye(jac_rhs.shape[0]) - dt * jac_rhs

    def _implicit_point(self, t, y, dt, y_new):  # noqa: ANN001, ANN202
        return t + dt, y_new


@register_integrator("implicit-midpoint")
class ImplicitMidpoint(NewtonImplicitIntegrator):
    """Implicit midpoint: ``y_new = y + dt·f(t+dt/2, (y+y_new)/2)``.

    Order 2, A-stable, *and* symplectic: conserves quadratic invariants
    exactly (harmonic-oscillator energy!) and shows bounded energy error
    on general Hamiltonian systems — the only method in the suite that is
    simultaneously stiff-competent and structure-preserving.
    """

    order = 2

    def _residual(self, system, t, y, dt, y_new):  # noqa: ANN001, ANN202
        return y_new - y - dt * system.rhs(t + 0.5 * dt, 0.5 * (y + y_new))

    def _residual_jacobian(self, jac_rhs, dt):  # noqa: ANN001, ANN202
        return np.eye(jac_rhs.shape[0]) - 0.5 * dt * jac_rhs

    def _implicit_point(self, t, y, dt, y_new):  # noqa: ANN001, ANN202
        return t + 0.5 * dt, 0.5 * (y + y_new)


@register_integrator("trapezoidal")
class Trapezoidal(NewtonImplicitIntegrator):
    """Trapezoidal rule: ``y_new = y + dt/2·(f(t, y) + f(t+dt, y_new))``.

    Order 2 and A-stable (the classical Crank–Nicolson time stepper);
    contrast with backward Euler to see the accuracy/damping trade-off.
    """

    order = 2

    def _residual(self, system, t, y, dt, y_new):  # noqa: ANN001, ANN202
        return y_new - y - 0.5 * dt * (system.rhs(t, y) + system.rhs(t + dt, y_new))

    def _residual_jacobian(self, jac_rhs, dt):  # noqa: ANN001, ANN202
        return np.eye(jac_rhs.shape[0]) - 0.5 * dt * jac_rhs

    def _implicit_point(self, t, y, dt, y_new):  # noqa: ANN001, ANN202
        return t + dt, y_new
