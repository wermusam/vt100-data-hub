"""Structural-dynamics time integration: the generalized-α method.

Chung & Hulbert's generalized-α method (1993) is the standard time
stepper of implicit FEM/structural codes (Abaqus, LS-DYNA implicit,
FEniCS examples) and of cloth/soft-body solvers that descend from them.
It integrates second-order mechanics ``q'' = a(t, q, v)`` directly via
the Newmark update, evaluating the balance equation at *shifted* points
between steps ``n`` and ``n+1``.

Its reason to exist — and the reason it belongs in this study — is
**controllable numerical dissipation**: a single parameter, the spectral
radius at infinity ``ρ∞ ∈ [0, 1]``, dials how aggressively unresolvable
high-frequency modes are damped while remaining second-order accurate
and unconditionally stable (for linear problems) in the resolved band.

* ``ρ∞ = 1``: no numerical dissipation (trapezoidal-rule behavior).
* ``ρ∞ = 0``: maximal high-frequency annihilation (one step kills an
  unresolved mode).

That is exactly the knob a stiff mass–spring chain, hard-contact sand,
or a noisy SPH pressure field wants: keep the physics you can resolve,
quietly discard the grid-frequency chatter you cannot. Neither the
implicit one-step family (uniform damping or none) nor the symplectic
family (no damping, by design) offers frequency-selective dissipation.

The Chung–Hulbert parameterization used here::

    α_m = (2ρ∞ − 1)/(ρ∞ + 1)      α_f = ρ∞/(ρ∞ + 1)
    γ   = 1/2 − α_m + α_f          β  = (1 − α_m + α_f)² / 4
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray, StepResult
from psim.integrators.base import Integrator, register_integrator
from psim.systems.base import ODESystem, SeparableSystem


@register_integrator("generalized-alpha")
class GeneralizedAlpha(Integrator):
    """Generalized-α integrator for separable mechanical systems.

    State is ``y = (q, v)``; the algorithmic acceleration ``a`` is
    carried between steps (initialized from the true acceleration on
    every restart, e.g. after a collision response). Each step solves

    ``(1−α_m)·a⁺ + α_m·aₙ = a(t_{n+α_f}, q_{n+α_f}, v_{n+α_f})``

    for ``a⁺`` with Newton iteration (forward-difference Jacobian in
    acceleration space), where ``q⁺, v⁺`` follow from the Newmark
    update and the α-shifted arguments are convex combinations of the
    ``n`` and ``n+1`` values.

    Parameters
    ----------
    rho_inf:
        Spectral radius at infinity, in ``[0, 1]``: the high-frequency
        dissipation dial (1 = none, 0 = maximal).
    newton_tol, max_newton_iter:
        Newton convergence tolerance and iteration cap.
    """

    order = 2
    requires_separable = True

    def __init__(
        self, rho_inf: float = 0.9, newton_tol: float = 1e-10, max_newton_iter: int = 30
    ) -> None:
        if not 0.0 <= rho_inf <= 1.0:
            raise ValueError("rho_inf must be in [0, 1]")
        self.rho_inf = rho_inf
        self.alpha_m = (2.0 * rho_inf - 1.0) / (rho_inf + 1.0)
        self.alpha_f = rho_inf / (rho_inf + 1.0)
        self.gamma = 0.5 - self.alpha_m + self.alpha_f
        self.beta = 0.25 * (1.0 - self.alpha_m + self.alpha_f) ** 2
        self.newton_tol = newton_tol
        self.max_newton_iter = max_newton_iter
        self._accel: FloatArray | None = None
        self._last: tuple[float, FloatArray] | None = None

    def _continuing(self, t: float, y: FloatArray) -> bool:
        """Whether ``(t, y)`` continues the point the last step produced."""
        if self._accel is None or self._last is None:
            return False
        t_last, y_last = self._last
        return abs(t - t_last) <= 1e-12 * max(1.0, abs(t)) and bool(np.array_equal(y, y_last))

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        if not isinstance(system, SeparableSystem):
            raise TypeError(
                f"{type(system).__name__} is not separable: generalized-alpha "
                "integrates q'' = a(t, q, v) mechanics"
            )
        n = system.n_coords
        q, v = y[:n], y[n:]
        a_n = self._accel if self._continuing(t, y) else system.acceleration(t, q, v)

        t_alpha = t + (1.0 - self.alpha_f) * dt

        def residual(a_new: FloatArray) -> FloatArray:
            q_new = q + dt * v + dt * dt * ((0.5 - self.beta) * a_n + self.beta * a_new)
            v_new = v + dt * ((1.0 - self.gamma) * a_n + self.gamma * a_new)
            q_alpha = (1.0 - self.alpha_f) * q_new + self.alpha_f * q
            v_alpha = (1.0 - self.alpha_f) * v_new + self.alpha_f * v
            balance = system.acceleration(t_alpha, q_alpha, v_alpha)
            return (1.0 - self.alpha_m) * a_new + self.alpha_m * a_n - balance

        a_new = a_n.copy()
        for _ in range(self.max_newton_iter):
            res = residual(a_new)
            # Forward-difference Jacobian in acceleration space (n columns).
            jac = np.empty((n, n))
            for j in range(n):
                step_j = 1e-7 * max(1.0, abs(a_new[j]))
                a_pert = a_new.copy()
                a_pert[j] += step_j
                jac[:, j] = (residual(a_pert) - res) / step_j
            delta = np.linalg.solve(jac, -res)
            a_new = a_new + delta
            if float(np.max(np.abs(delta))) < self.newton_tol * max(
                1.0, float(np.max(np.abs(a_new)))
            ):
                break

        q_new = q + dt * v + dt * dt * ((0.5 - self.beta) * a_n + self.beta * a_new)
        v_new = v + dt * ((1.0 - self.gamma) * a_n + self.gamma * a_new)
        y_new = np.concatenate([q_new, v_new])
        self._accel = a_new
        self._last = (t + dt, y_new.copy())
        return StepResult(t + dt, y_new, dt)
