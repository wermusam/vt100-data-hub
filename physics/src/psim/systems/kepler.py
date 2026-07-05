"""Planar Kepler two-body problem with a rational polynomial lifting.

Gravity's ``1/r³`` factor is not polynomial, so the Parker–Sochacki
lifting adjoins two auxiliary variables::

    u = r⁻³        u' = −3 s u w
    w = r⁻²        w' = −2 s w²      with  s = x·vx + y·vy = r·ṙ·(r/r)

giving the closed polynomial system on ``z = (x, y, vx, vy, u, w)``::

    x'  = vx            vx' = −μ x u
    y'  = vy            vy' = −μ y u

This is the classic demonstration (Parker & Sochacki 1996–2000; the
follow-up N-body work by Pruett, Rudmin & Lacy) that PSM handles
"non-polynomial" forces with a handful of extra series.

The exact solution (elliptic orbits, via the Lagrange f–g functions and
Newton's method on Kepler's equation) makes this the most demanding
convergence benchmark in the suite, and its two invariants — energy and
angular momentum — expose long-horizon drift differences between
symplectic, non-symplectic, and high-order methods.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray
from psim.systems.base import ODESystem, cauchy, register_system


@register_system("kepler")
class Kepler(ODESystem):
    """Planar two-body problem ``r'' = −μ r / |r|³``.

    State is ``(x, y, vx, vy)``. The default initial condition is the
    standard eccentric test orbit (eccentricity ``e``, perihelion start)
    with period ``2π`` when ``mu = 1``.

    Parameters
    ----------
    mu:
        Gravitational parameter ``G(m₁+m₂)``.
    eccentricity:
        Eccentricity of the default initial orbit, in ``[0, 1)``.
    """

    def __init__(self, mu: float = 1.0, eccentricity: float = 0.6) -> None:
        if mu <= 0:
            raise ValueError("mu must be positive")
        if not 0.0 <= eccentricity < 1.0:
            raise ValueError("eccentricity must be in [0, 1) for a bound orbit")
        self.mu = mu
        self.eccentricity = eccentricity
        e = eccentricity
        self._y0 = np.array([1.0 - e, 0.0, 0.0, np.sqrt(mu * (1.0 + e) / (1.0 - e))])

    @property
    def dim(self) -> int:
        return 4

    @property
    def y0(self) -> FloatArray:
        return self._y0

    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        x, ypos, vx, vy = y
        r3 = (x * x + ypos * ypos) ** 1.5
        return np.array([vx, vy, -self.mu * x / r3, -self.mu * ypos / r3])

    def energy(self, y: FloatArray) -> float:
        x, ypos, vx, vy = y
        r = np.hypot(x, ypos)
        return 0.5 * (vx * vx + vy * vy) - self.mu / r

    def angular_momentum(self, y: FloatArray) -> float:
        """Specific angular momentum ``L = x·vy − y·vx`` (conserved)."""
        x, ypos, vx, vy = y
        return x * vy - ypos * vx

    def invariants(self, y: FloatArray) -> dict[str, float]:
        return {"energy": self.energy(y), "angular_momentum": self.angular_momentum(y)}

    # -- SeparableSystem ---------------------------------------------------
    @property
    def n_coords(self) -> int:
        return 2

    def acceleration(self, t: float, q: FloatArray, v: FloatArray) -> FloatArray:
        r3 = float(q[0] * q[0] + q[1] * q[1]) ** 1.5
        return -self.mu * q / r3

    # -- Exact solution via Lagrange f–g functions --------------------------
    def exact(self, t: float) -> FloatArray:
        r0_vec = self._y0[:2]
        v0_vec = self._y0[2:]
        r0 = float(np.linalg.norm(r0_vec))
        energy = 0.5 * float(v0_vec @ v0_vec) - self.mu / r0
        a = -self.mu / (2.0 * energy)  # semi-major axis (elliptic: a > 0)
        n = np.sqrt(self.mu / a**3)  # mean motion
        sqrt_mua = np.sqrt(self.mu * a)
        rv = float(r0_vec @ v0_vec)

        # Eccentric anomaly at t = 0 from (e sin E0, e cos E0).
        esin0 = rv / sqrt_mua
        ecos0 = 1.0 - r0 / a
        e0 = np.arctan2(esin0, ecos0)
        mean0 = e0 - esin0

        # Solve Kepler's equation M = E − e·sin(E) with Newton's method.
        ecc = np.hypot(esin0, ecos0)
        mean = mean0 + n * t
        eanom = mean if ecc < 0.8 else np.pi
        for _ in range(60):
            f = eanom - ecc * np.sin(eanom) - mean
            eanom -= f / (1.0 - ecc * np.cos(eanom))
            if abs(f) < 1e-15:
                break

        de = eanom - e0
        r = a * (1.0 - ecc * np.cos(eanom))
        f_lag = 1.0 - (a / r0) * (1.0 - np.cos(de))
        g_lag = t + (np.sin(de) - de) / n
        fdot = -sqrt_mua * np.sin(de) / (r * r0)
        gdot = 1.0 - (a / r) * (1.0 - np.cos(de))
        pos = f_lag * r0_vec + g_lag * v0_vec
        vel = fdot * r0_vec + gdot * v0_vec
        return np.concatenate([pos, vel])

    # -- PolynomialODE: lifted state z = (x, y, vx, vy, u, w) ----------------
    @property
    def ps_dim(self) -> int:
        return 6

    def ps_lift(self, y: FloatArray) -> FloatArray:
        r2 = float(y[0] * y[0] + y[1] * y[1])
        return np.concatenate([y, [r2**-1.5, 1.0 / r2]])

    def ps_restrict(self, z: FloatArray) -> FloatArray:
        return z[:4]

    def ps_rhs_coefficient(self, coeffs: FloatArray, k: int) -> FloatArray:
        x, ypos = coeffs[:, 0], coeffs[:, 1]
        vx, vy = coeffs[:, 2], coeffs[:, 3]
        u, w = coeffs[:, 4], coeffs[:, 5]
        # Intermediate series up to order k (recomputed per call; the
        # O(k²) cost is dwarfed by everything else at these dimensions).
        s = np.array([cauchy(x, vx, j) + cauchy(ypos, vy, j) for j in range(k + 1)])
        uw = np.array([cauchy(u, w, j) for j in range(k + 1)])
        ww = np.array([cauchy(w, w, j) for j in range(k + 1)])
        return np.array(
            [
                coeffs[k, 2],
                coeffs[k, 3],
                -self.mu * cauchy(x, u, k),
                -self.mu * cauchy(ypos, u, k),
                -3.0 * cauchy(s, uw, k),
                -2.0 * cauchy(s, ww, k),
            ]
        )
