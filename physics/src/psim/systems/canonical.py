"""Canonical linear test problems: decay, damped oscillator, stiff spring.

These are the "basics" tier of the experiment ladder. All of them are
linear, so they have machine-checkable exact solutions (via the matrix
exponential, computed here with an eigendecomposition), trivially
polynomial right-hand sides for Parker–Sochacki, and tunable stiffness
and damping — which makes them the cleanest instruments for stability
and parameter-flexibility studies.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray
from psim.systems.base import ODESystem, register_system


class LinearSystem(ODESystem):
    """Base class for autonomous linear systems ``y' = A y``.

    Provides the exact solution ``y(t) = exp(At) y0`` (eigendecomposition;
    fine for the small, diagonalizable matrices used here) and the
    Parker–Sochacki recurrence, which for a linear system is simply
    ``f_k = A c_k``.
    """

    def __init__(self, matrix: FloatArray, y0: FloatArray) -> None:
        self._matrix = np.asarray(matrix, dtype=float)
        self._y0 = np.asarray(y0, dtype=float)
        # Cache the eigendecomposition once; exact() is called in hot
        # benchmark loops.
        self._eigvals, self._eigvecs = np.linalg.eig(self._matrix)
        self._proj = np.linalg.solve(self._eigvecs, self._y0.astype(complex))

    @property
    def matrix(self) -> FloatArray:
        """The system matrix ``A``."""
        return self._matrix

    @property
    def dim(self) -> int:
        return self._matrix.shape[0]

    @property
    def y0(self) -> FloatArray:
        return self._y0

    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        return self._matrix @ y

    def jacobian(self, t: float, y: FloatArray) -> FloatArray:
        """Exact Jacobian (constant); lets implicit methods skip finite
        differences."""
        return self._matrix

    def exact(self, t: float) -> FloatArray:
        modes = self._eigvecs @ (np.exp(self._eigvals * t) * self._proj)
        return np.real(modes)

    # -- PolynomialODE -----------------------------------------------------
    @property
    def ps_dim(self) -> int:
        return self.dim

    def ps_lift(self, y: FloatArray) -> FloatArray:
        return np.asarray(y, dtype=float).copy()

    def ps_restrict(self, z: FloatArray) -> FloatArray:
        return z

    def ps_rhs_coefficient(self, coeffs: FloatArray, k: int) -> FloatArray:
        return self._matrix @ coeffs[k]


@register_system("decay")
class ExponentialDecay(LinearSystem):
    """Scalar exponential decay ``y' = −λ y`` — the "hello world" ODE.

    With large ``rate`` this doubles as the standard linear stability test
    (Dahlquist's equation): explicit methods blow up once ``λ·dt`` leaves
    the stability region, A-stable implicit methods never do.
    """

    def __init__(self, rate: float = 1.0, y_init: float = 1.0) -> None:
        if rate <= 0:
            raise ValueError("decay rate must be positive")
        self.rate = rate
        super().__init__(np.array([[-rate]]), np.array([y_init]))


@register_system("oscillator")
class DampedOscillator(LinearSystem):
    """Damped harmonic oscillator ``m x'' + c x' + k x = 0``.

    State is ``(x, v)``. The two knobs — stiffness ``k`` and damping
    ``c`` — are exactly the "parameter flexibility" axes of the study:
    raising ``k`` shrinks explicit methods' stable step size like
    ``dt_max ∝ 1/√(k/m)``, while raising ``c`` moves the eigenvalues from
    oscillatory to stiff-dissipative.
    """

    def __init__(
        self,
        stiffness: float = 1.0,
        damping: float = 0.0,
        mass: float = 1.0,
        x0: float = 1.0,
        v0: float = 0.0,
    ) -> None:
        if stiffness <= 0 or mass <= 0 or damping < 0:
            raise ValueError("require stiffness > 0, mass > 0, damping >= 0")
        self.stiffness = stiffness
        self.damping = damping
        self.mass = mass
        matrix = np.array([[0.0, 1.0], [-stiffness / mass, -damping / mass]])
        super().__init__(matrix, np.array([x0, v0]))

    def energy(self, y: FloatArray) -> float:
        x, v = y
        return 0.5 * self.mass * v**2 + 0.5 * self.stiffness * x**2

    # -- SeparableSystem ---------------------------------------------------
    @property
    def n_coords(self) -> int:
        return 1

    def acceleration(self, t: float, q: FloatArray, v: FloatArray) -> FloatArray:
        return (-self.stiffness * q - self.damping * v) / self.mass


@register_system("stiff-spring")
class StiffSpringDamper(DampedOscillator):
    """A deliberately stiff oscillator (default ``k = 10⁴``, ``c = 10²``).

    The workhorse for the explicit-vs-implicit comparison: explicit
    methods need ``dt ≲ 2/ω`` (here ~0.02) merely to remain bounded,
    while backward Euler and the implicit midpoint rule stay stable at
    any step size and are limited only by accuracy.
    """

    def __init__(self, stiffness: float = 1.0e4, damping: float = 1.0e2) -> None:
        super().__init__(stiffness=stiffness, damping=damping, mass=1.0, x0=1.0, v0=0.0)
