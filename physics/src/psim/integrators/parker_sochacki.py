"""The Parker–Sochacki method (PSM): arbitrary-order power-series stepping.

Background
----------
G. Edgar Parker and James Sochacki (James Madison University, 1996)
observed that if an ODE's right-hand side is *polynomial*, the Picard
iteration — usually a purely theoretical device — becomes an effective
numerical algorithm: the ``k``-th iterate contributes exactly the
``k``-th Maclaurin coefficient of the solution, computable from earlier
coefficients with Cauchy products alone. Any ODE built from elementary
functions can be rewritten in polynomial form by adjoining auxiliary
variables (see :class:`~psim.systems.base.PolynomialODE`), so the method
applies far beyond textbook polynomials — the Newtonian N-body problem
being the canonical showcase.

What one PSM step looks like::

    z₀ = lift(y)                       # recompute auxiliaries exactly
    C[0] = z₀
    for k in 0..K-1:
        C[k+1] = P_k(C[0..k]) / (k+1)  # Cauchy-product recurrence
    y(t₀+τ) ≈ restrict( Σ_k C[k] τᵏ )  # a *polynomial in τ*, any τ

Three properties fall out of that last line, and they are exactly the
areas where PSM is genuinely novel among the methods in this package:

* **Arbitrary order.** ``K`` is a runtime parameter, not baked into a
  Butcher tableau. K = 30 is as easy as K = 4, so one step can be
  accurate to machine precision.
* **Free dense output.** The step *is* a polynomial. Evaluating the
  solution anywhere inside the step costs a Horner evaluation, not a
  new integration — which turns collision detection into polynomial
  root-finding on the local solution (see the collision benchmark).
* **Principled adaptivity.** The tail coefficients estimate the local
  series' radius of convergence, so the step size (and, if desired, the
  order) can be chosen per step from data the method already computed.

Limitations worth stating just as plainly: the recurrence is explicit,
so stiffness still bounds the usable step (the series knows about the
fast transient and shrinks ``h`` to resolve it); events/contacts break
analyticity, so PSM must stop at them (its dense output at least locates
them precisely); and each system needs a polynomial lifting written once
by a human.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from psim.core.types import FloatArray, StepResult
from psim.integrators.base import Integrator, Interpolant, register_integrator
from psim.systems.base import ODESystem, PolynomialODE


@dataclass(frozen=True, slots=True)
class _Segment:
    """One internal PSM step: a local Maclaurin polynomial."""

    t_start: float
    h: float
    coeffs: FloatArray  # (order + 1, ps_dim)

    def eval(self, tau: float) -> FloatArray:
        """Horner evaluation of the lifted-state polynomial at local ``tau``."""
        z = self.coeffs[-1].copy()
        for row in self.coeffs[-2::-1]:
            z = z * tau + row
        return z


@register_integrator("parker-sochacki")
class ParkerSochacki(Integrator):
    """Parker–Sochacki integrator with optional coefficient-based adaptivity.

    Parameters
    ----------
    order:
        Truncation order ``K`` of the Maclaurin series (the step
        polynomial has degree ``K``). The effective order of the method:
        local error is ``O(h^{K+1})``.
    tol:
        If ``None`` (default), behave as a fixed-step method of order
        ``K`` — each call to :meth:`step` takes the full ``dt``. If set,
        :meth:`advance` sub-steps: each internal step chooses ``h`` from
        the computed tail coefficients so the truncated tail is below
        ``tol``, which is PSM's native error control.
    max_h:
        Optional cap on internal steps in adaptive mode.

    Raises
    ------
    TypeError
        If the system does not provide a polynomial lifting.
    """

    def __init__(self, order: int = 16, tol: float | None = None, max_h: float = np.inf) -> None:
        if order < 1:
            raise ValueError("order must be at least 1")
        if tol is not None and tol <= 0:
            raise ValueError("tol must be positive when given")
        self.order = order
        self.tol = tol
        self.max_h = max_h
        self._segments: list[_Segment] = []
        self._restrict = None

    # -- Series construction -------------------------------------------------
    def _coefficients(self, system: PolynomialODE, y: FloatArray) -> FloatArray:
        if not isinstance(system, PolynomialODE):
            raise TypeError(
                f"{type(system).__name__} has no polynomial lifting; "
                "Parker-Sochacki requires the PolynomialODE interface"
            )
        coeffs = np.zeros((self.order + 1, system.ps_dim))
        coeffs[0] = system.ps_lift(y)
        for k in range(self.order):
            coeffs[k + 1] = system.ps_rhs_coefficient(coeffs[: k + 1], k) / (k + 1)
        return coeffs

    def _choose_h(self, coeffs: FloatArray, span: float) -> float:
        """Pick an internal step from the tail-coefficient error estimate.

        Requires ``|C_K| h^K ≤ tol`` using the last two computed
        coefficients (guarding against an accidentally tiny final one) —
        the classic PSM/Taylor-series step controller.
        """
        assert self.tol is not None
        h = min(span, self.max_h)
        for k in (self.order, self.order - 1):
            magnitude = float(np.max(np.abs(coeffs[k])))
            if magnitude > 0.0:
                h = min(h, (self.tol / magnitude) ** (1.0 / k))
        return max(h, 1e-12)

    # -- Integrator interface --------------------------------------------------
    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        coeffs = self._coefficients(system, y)
        segment = _Segment(t, dt, coeffs)
        self._segments = [segment]
        self._restrict = system.ps_restrict
        tail = float(np.max(np.abs(coeffs[-1]))) * dt**self.order
        return StepResult(t + dt, system.ps_restrict(segment.eval(dt)), dt, error_estimate=tail)

    def advance(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        if self.tol is None:
            return self.step(system, t, y, dt)
        t_target = t + dt
        self._segments = []
        self._restrict = system.ps_restrict
        last_h = dt
        while t < t_target - 1e-12 * max(1.0, abs(t_target)):
            coeffs = self._coefficients(system, y)
            h = self._choose_h(coeffs, t_target - t)
            segment = _Segment(t, h, coeffs)
            self._segments.append(segment)
            y = system.ps_restrict(segment.eval(h))
            t, last_h = t + h, h
        return StepResult(t, y, last_h)

    def interpolant(
        self, system: ODESystem, t: float, y: FloatArray, dt: float, result: StepResult
    ) -> Interpolant | None:
        """Piecewise-polynomial dense output over the last advance.

        This is the "free" dense output: no additional right-hand-side
        work is performed, the stored Maclaurin coefficients are simply
        evaluated wherever the caller asks.
        """
        segments = self._segments
        restrict = self._restrict
        if not segments or restrict is None or abs(segments[0].t_start - t) > 1e-12:
            return None

        def dense(tau: float) -> FloatArray:
            t_query = t + tau
            for seg in segments:
                if t_query <= seg.t_start + seg.h + 1e-15:
                    return restrict(seg.eval(t_query - seg.t_start))
            last = segments[-1]
            return restrict(last.eval(t_query - last.t_start))

        return dense
