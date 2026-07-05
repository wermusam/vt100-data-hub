"""System interfaces: plain ODEs, separable mechanics, polynomial liftings.

Design
------
Every physical model is a first-order ODE ``y' = f(t, y)`` exposed through
:class:`ODESystem`. Three optional capabilities layer on top:

* :class:`SeparableSystem` — mechanical systems with state ``y = (q, v)``
  and an acceleration function; required by symplectic integrators.
* :class:`PolynomialODE` — systems that can be *lifted* to an autonomous
  polynomial ODE ``z' = P(z)`` by adjoining auxiliary variables. This is
  the entry ticket for the Parker–Sochacki method: once the right-hand
  side is polynomial, Maclaurin coefficients of the solution follow from
  a cheap algebraic recurrence (Picard iteration collapses to Cauchy
  products). The lifting trick is central to the Parker–Sochacki
  literature: *any* ODE built from elementary functions can be made
  polynomial by adding variables (e.g. adjoin ``s = sin θ, c = cos θ``
  to a pendulum, or ``u = r⁻³`` to a gravitational two-body problem).
* :class:`EventFunction` — scalar guard functions ``g(t, y)`` whose sign
  changes mark discrete events (collisions); integrators with dense
  output can locate the crossing to high precision.

The Cauchy-product helpers at the bottom are the whole "series algebra"
the Parker–Sochacki systems need.
"""

from __future__ import annotations

import abc
from collections.abc import Callable
from typing import Protocol, runtime_checkable

import numpy as np

from psim.core.decorators import registry
from psim.core.types import FloatArray

#: Global name → class registry of benchmarkable systems. Classes join it
#: with ``@register_system("name")``.
SYSTEMS, register_system = registry()

# A scalar event guard g(t, y): an event occurs where g crosses zero.
EventFunction = Callable[[float, FloatArray], float]


class ODESystem(abc.ABC):
    """A first-order ODE system ``y' = f(t, y)`` with optional diagnostics.

    Subclasses must implement :meth:`rhs` and :attr:`dim`, and should
    implement :meth:`energy` (for conservation studies) and
    :meth:`exact` (for convergence studies) where the physics permits.
    """

    #: Human-readable registry name, stamped by ``@register_system``.
    registry_name: str = ""

    @property
    @abc.abstractmethod
    def dim(self) -> int:
        """Dimension of the state vector."""

    @property
    @abc.abstractmethod
    def y0(self) -> FloatArray:
        """Default initial condition used by benchmarks."""

    @abc.abstractmethod
    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        """Evaluate the right-hand side ``f(t, y)``."""

    def energy(self, y: FloatArray) -> float | None:
        """Total mechanical energy of state ``y``, or ``None`` if undefined.

        For dissipative systems this is still the instantaneous mechanical
        energy; benchmarks then compare against the exact dissipation rate
        rather than a constant.
        """
        return None

    def exact(self, t: float) -> FloatArray | None:
        """Closed-form solution at time ``t`` from :attr:`y0`, if known."""
        return None

    def invariants(self, y: FloatArray) -> dict[str, float]:
        """All conserved quantities of state ``y`` (empty if none)."""
        e = self.energy(y)
        return {} if e is None else {"energy": e}

    @property
    def name(self) -> str:
        """Registry name if registered, else the class name."""
        return self.registry_name or type(self).__name__


@runtime_checkable
class SeparableSystem(Protocol):
    """Mechanical structure ``q' = v, v' = a(t, q, v)`` for symplectic methods.

    The state convention is ``y = concat(q, v)`` with ``len(q) == len(v)``.
    """

    @property
    def n_coords(self) -> int:
        """Number of generalized coordinates (half the state dimension)."""
        ...

    def acceleration(self, t: float, q: FloatArray, v: FloatArray) -> FloatArray:
        """Acceleration ``a(t, q, v)`` of shape ``(n_coords,)``."""
        ...


@runtime_checkable
class PolynomialODE(Protocol):
    """A system that admits a polynomial lifting for Parker–Sochacki.

    The lifted state ``z ∈ R^{ps_dim}`` satisfies an autonomous ODE
    ``z' = P(z)`` with polynomial ``P``. The physical state is a slice or
    projection of ``z``. Implementations provide the Maclaurin-coefficient
    recurrence directly: given the coefficient table ``C`` where row ``j``
    holds the ``j``-th Taylor coefficient of ``z`` about the step's start
    time, :meth:`ps_rhs_coefficient` returns the ``k``-th Taylor
    coefficient of ``P(z(t))``; the integrator then sets
    ``C[k+1] = ps_rhs_coefficient(C, k) / (k + 1)``.

    That recurrence *is* the Parker–Sochacki method: it is what the k-th
    Picard iterate contributes, computed without symbolic algebra using
    the Cauchy-product helpers below.
    """

    @property
    def ps_dim(self) -> int:
        """Dimension of the lifted (augmented) state."""
        ...

    def ps_lift(self, y: FloatArray) -> FloatArray:
        """Map physical state ``y`` to lifted state ``z`` (recomputing
        auxiliaries exactly, which also re-synchronizes any drift in the
        auxiliary variables at each step start)."""
        ...

    def ps_restrict(self, z: FloatArray) -> FloatArray:
        """Project lifted state ``z`` back to the physical state ``y``."""
        ...

    def ps_rhs_coefficient(self, coeffs: FloatArray, k: int) -> FloatArray:
        """Return the ``k``-th Maclaurin coefficient of ``P(z(t))``.

        Parameters
        ----------
        coeffs:
            Array of shape ``(k + 1, ps_dim)``; row ``j`` is the ``j``-th
            Taylor coefficient of the lifted solution.
        k:
            Order of the requested right-hand-side coefficient.
        """
        ...


# --------------------------------------------------------------------------
# Series algebra: everything a polynomial RHS needs.
# --------------------------------------------------------------------------


def cauchy(a: FloatArray, b: FloatArray, k: int) -> float | FloatArray:
    """The ``k``-th coefficient of the product of two Maclaurin series.

    ``cauchy(a, b, k) = Σ_{j=0}^{k} a[j] · b[k−j]``.

    ``a`` and ``b`` are indexed by coefficient order along axis 0 and may
    carry trailing state axes (the sum broadcasts elementwise).
    Coefficients beyond either array's length are treated as zero, so
    truncated series compose safely.
    """
    lo = max(0, k - (len(b) - 1))
    hi = min(k, len(a) - 1)
    if lo > hi:
        return 0.0
    return sum(a[j] * b[k - j] for j in range(lo, hi + 1))


def series_product(a: FloatArray, b: FloatArray, upto: int) -> FloatArray:
    """All coefficients ``0..upto`` of the product of two series."""
    return np.array([cauchy(a, b, k) for k in range(upto + 1)])
