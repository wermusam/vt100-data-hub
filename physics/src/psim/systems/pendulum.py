"""Nonlinear pendulum with a trigonometric polynomial lifting.

The pendulum is the smallest system where the Parker–Sochacki lifting
trick becomes visible: ``sin θ`` is not polynomial, so we adjoin
``s = sin θ`` and ``c = cos θ`` as extra state variables. Their
derivatives close the system polynomially::

    θ' = ω
    ω' = −(g/L)·s − γ·ω
    s' = ω·c
    c' = −ω·s

The products ``ω·c`` and ``ω·s`` become Cauchy products at the
coefficient level. At every step start :meth:`ps_lift` recomputes ``s``
and ``c`` from ``θ`` exactly, so the auxiliary variables cannot drift
off the circle ``s² + c² = 1`` across steps.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray
from psim.systems.base import ODESystem, cauchy, register_system


@register_system("pendulum")
class Pendulum(ODESystem):
    """Planar pendulum ``θ'' = −(g/L) sin θ − γ θ'``.

    State is ``(θ, ω)``. With ``damping = 0`` energy is conserved and the
    system is Hamiltonian — the standard testbed for symplectic-vs-
    non-symplectic long-run energy behavior.

    Parameters
    ----------
    gravity, length, damping:
        Physical parameters; ``gamma = damping`` acts on angular velocity.
    theta0, omega0:
        Default initial condition (radians, radians/second).
    """

    def __init__(
        self,
        gravity: float = 9.81,
        length: float = 1.0,
        damping: float = 0.0,
        theta0: float = 2.0,
        omega0: float = 0.0,
    ) -> None:
        if gravity <= 0 or length <= 0 or damping < 0:
            raise ValueError("require gravity > 0, length > 0, damping >= 0")
        self.gravity = gravity
        self.length = length
        self.damping = damping
        self._y0 = np.array([theta0, omega0])

    @property
    def dim(self) -> int:
        return 2

    @property
    def y0(self) -> FloatArray:
        return self._y0

    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        theta, omega = y
        alpha = -(self.gravity / self.length) * np.sin(theta) - self.damping * omega
        return np.array([omega, alpha])

    def energy(self, y: FloatArray) -> float:
        theta, omega = y
        kinetic = 0.5 * (self.length * omega) ** 2
        potential = self.gravity * self.length * (1.0 - np.cos(theta))
        return kinetic + potential

    # -- SeparableSystem ---------------------------------------------------
    @property
    def n_coords(self) -> int:
        return 1

    def acceleration(self, t: float, q: FloatArray, v: FloatArray) -> FloatArray:
        return -(self.gravity / self.length) * np.sin(q) - self.damping * v

    # -- PolynomialODE: lifted state z = (θ, ω, s, c) ------------------------
    @property
    def ps_dim(self) -> int:
        return 4

    def ps_lift(self, y: FloatArray) -> FloatArray:
        theta, omega = y
        return np.array([theta, omega, np.sin(theta), np.cos(theta)])

    def ps_restrict(self, z: FloatArray) -> FloatArray:
        return z[:2]

    def ps_rhs_coefficient(self, coeffs: FloatArray, k: int) -> FloatArray:
        omega, s, c = coeffs[:, 1], coeffs[:, 2], coeffs[:, 3]
        return np.array(
            [
                coeffs[k, 1],
                -(self.gravity / self.length) * coeffs[k, 2] - self.damping * coeffs[k, 1],
                cauchy(omega, c, k),
                -cauchy(omega, s, k),
            ]
        )
