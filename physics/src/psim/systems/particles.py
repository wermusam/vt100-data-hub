"""Event-driven and granular particle systems.

Two rungs of the complexity ladder live here:

* :class:`BouncingBall` — the minimal *hybrid* system: smooth free-fall
  ODE punctuated by impact events. Free flight is exactly polynomial
  (the Parker–Sochacki series terminates at degree 2!), so PSM's dense
  polynomial output locates the impact time to machine precision — the
  cleanest demonstration of PSM's advantage for collision detection.
* :class:`GranularBox2D` — a soft-sphere DEM "sand" toy: many disks
  under gravity with penalty-spring normal contacts, dashpot damping,
  and wall contacts. Contact forces are *piecewise* (they switch on at
  touch), which breaks the analyticity PSM relies on; this system is
  deliberately in the suite to mark PSM's boundary — see the README's
  discussion of events versus smoothing.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray
from psim.systems.base import ODESystem, register_system


@register_system("bouncing-ball")
class BouncingBall(ODESystem):
    """A point mass falling onto the floor ``h = 0`` and rebounding.

    State is ``(h, v)``. Between impacts ``h' = v, v' = −g``. The impact
    guard is ``g(t, y) = h`` (downward crossing), and the impact map is
    ``v ← −e·v`` with restitution ``e``.

    Parameters
    ----------
    gravity:
        Gravitational acceleration.
    restitution:
        Coefficient of restitution ``e ∈ [0, 1]``.
    h0, v0:
        Default initial height and velocity.
    """

    def __init__(
        self,
        gravity: float = 9.81,
        restitution: float = 0.8,
        h0: float = 1.0,
        v0: float = 0.0,
    ) -> None:
        if gravity <= 0:
            raise ValueError("gravity must be positive")
        if not 0.0 <= restitution <= 1.0:
            raise ValueError("restitution must be in [0, 1]")
        self.gravity = gravity
        self.restitution = restitution
        self._y0 = np.array([h0, v0])

    @property
    def dim(self) -> int:
        return 2

    @property
    def y0(self) -> FloatArray:
        return self._y0

    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        return np.array([y[1], -self.gravity])

    def energy(self, y: FloatArray) -> float:
        h, v = y
        return 0.5 * v * v + self.gravity * h

    # -- Event interface -----------------------------------------------------
    def event(self, t: float, y: FloatArray) -> float:
        """Impact guard: zero when the ball touches the floor."""
        return float(y[0])

    def event_response(self, t: float, y: FloatArray) -> FloatArray:
        """Impact map: reflect velocity with restitution loss."""
        return np.array([0.0, -self.restitution * y[1]])

    def first_impact_time(self) -> float:
        """Closed-form time of the first floor impact from :attr:`y0`.

        Solves ``h0 + v0·t − g·t²/2 = 0`` for the positive root — the
        ground truth for the collision-timing benchmark.
        """
        h0, v0 = self._y0
        return (v0 + np.sqrt(v0 * v0 + 2.0 * self.gravity * h0)) / self.gravity

    # -- SeparableSystem ---------------------------------------------------
    @property
    def n_coords(self) -> int:
        return 1

    def acceleration(self, t: float, q: FloatArray, v: FloatArray) -> FloatArray:
        return np.array([-self.gravity])

    # -- PolynomialODE (free flight only; the series terminates at k = 1) ----
    @property
    def ps_dim(self) -> int:
        return 2

    def ps_lift(self, y: FloatArray) -> FloatArray:
        return np.asarray(y, dtype=float).copy()

    def ps_restrict(self, z: FloatArray) -> FloatArray:
        return z

    def ps_rhs_coefficient(self, coeffs: FloatArray, k: int) -> FloatArray:
        return np.array([coeffs[k, 1], -self.gravity if k == 0 else 0.0])


@register_system("granular-box")
class GranularBox2D(ODESystem):
    """Soft-sphere granular disks settling in a box under gravity.

    A miniature discrete-element-method (DEM) model: each contact (disk–
    disk or disk–wall) applies a normal penalty spring ``k_n·δ`` on the
    overlap ``δ``, a normal dashpot ``γ_n``, and a tangential dashpot
    ``γ_t`` standing in for sliding friction. State is
    ``(x₁, y₁, …, xₙ, yₙ, vx₁, …, vyₙ)``.

    The contact stiffness ``k_n`` is the stiffness knob of the sand
    experiment: hard sand (large ``k_n``, small overlaps) forces tiny
    explicit steps exactly like the stiff spring does.

    Parameters
    ----------
    n_side:
        Particles are seeded as an ``n_side × n_side`` block, slightly
        jittered (deterministically) so columns don't balance perfectly.
    radius, box, gravity:
        Disk radius, square box edge length, gravity.
    k_n, gamma_n, gamma_t:
        Contact stiffness, normal damping, tangential damping.
    """

    def __init__(
        self,
        n_side: int = 5,
        radius: float = 0.05,
        box: float = 1.0,
        gravity: float = 9.81,
        k_n: float = 5.0e3,
        gamma_n: float = 5.0,
        gamma_t: float = 1.0,
        mass: float = 1.0,
    ) -> None:
        if n_side < 1 or radius <= 0 or box <= 4 * radius:
            raise ValueError("box must comfortably contain the particles")
        self.n = n_side * n_side
        self.radius = radius
        self.box = box
        self.gravity = gravity
        self.k_n = k_n
        self.gamma_n = gamma_n
        self.gamma_t = gamma_t
        self.mass = mass

        # Deterministic jittered block drop: reproducible benchmarks need
        # reproducible piles.
        rng = np.random.default_rng(seed=7)
        spacing = 2.05 * radius
        cols, rows = np.meshgrid(np.arange(n_side), np.arange(n_side))
        x = 0.5 * box + (cols.ravel() - (n_side - 1) / 2) * spacing
        y = 0.5 * box + rows.ravel() * spacing
        pos = np.column_stack([x, y]) + rng.uniform(-0.1, 0.1, (self.n, 2)) * radius
        self._y0 = np.concatenate([pos.ravel(), np.zeros(2 * self.n)])

    @property
    def dim(self) -> int:
        return 4 * self.n

    @property
    def y0(self) -> FloatArray:
        return self._y0

    def positions(self, y: FloatArray) -> FloatArray:
        """Particle positions of shape ``(n, 2)`` from a flat state."""
        return y[: 2 * self.n].reshape(self.n, 2)

    def velocities(self, y: FloatArray) -> FloatArray:
        """Particle velocities of shape ``(n, 2)`` from a flat state."""
        return y[2 * self.n :].reshape(self.n, 2)

    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        pos = self.positions(y)
        vel = self.velocities(y)
        acc = self._forces(pos, vel) / self.mass
        return np.concatenate([vel.ravel(), acc.ravel()])

    def energy(self, y: FloatArray) -> float:
        """Kinetic + gravitational + elastic contact energy (dissipates
        through the dashpots, so expect monotone decay to a pile)."""
        pos = self.positions(y)
        vel = self.velocities(y)
        kinetic = 0.5 * self.mass * float(np.sum(vel * vel))
        potential = self.mass * self.gravity * float(np.sum(pos[:, 1]))
        overlap = self._pair_overlaps(pos)
        elastic = 0.5 * self.k_n * float(np.sum(overlap**2))
        return kinetic + potential + elastic

    # -- SeparableSystem ---------------------------------------------------
    @property
    def n_coords(self) -> int:
        return 2 * self.n

    def acceleration(self, t: float, q: FloatArray, v: FloatArray) -> FloatArray:
        pos = q.reshape(self.n, 2)
        vel = v.reshape(self.n, 2)
        return (self._forces(pos, vel) / self.mass).ravel()

    # -- Internals -----------------------------------------------------------
    def _pair_overlaps(self, pos: FloatArray) -> FloatArray:
        delta = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(delta, axis=-1)
        np.fill_diagonal(dist, np.inf)
        return np.triu(np.maximum(0.0, 2.0 * self.radius - dist), k=1)

    def _forces(self, pos: FloatArray, vel: FloatArray) -> FloatArray:
        n = self.n
        force = np.zeros((n, 2))
        force[:, 1] -= self.mass * self.gravity

        # Pairwise soft-sphere contacts (vectorized over all pairs).
        delta = pos[:, None, :] - pos[None, :, :]  # (n, n, 2), i minus j
        dist = np.linalg.norm(delta, axis=-1)
        np.fill_diagonal(dist, np.inf)
        overlap = 2.0 * self.radius - dist
        touching = overlap > 0.0
        if np.any(touching):
            normal = delta / dist[..., None]
            rel_v = vel[:, None, :] - vel[None, :, :]
            vn = np.sum(rel_v * normal, axis=-1)
            vt = rel_v - vn[..., None] * normal
            magnitude = self.k_n * np.maximum(overlap, 0.0) - self.gamma_n * vn
            pair_force = np.where(
                touching[..., None],
                magnitude[..., None] * normal - self.gamma_t * vt,
                0.0,
            )
            force += pair_force.sum(axis=1)

        # Wall contacts: penalty springs on penetration past each wall.
        for axis in (0, 1):
            low_pen = np.maximum(0.0, self.radius - pos[:, axis])
            high_pen = np.maximum(0.0, pos[:, axis] - (self.box - self.radius))
            force[:, axis] += self.k_n * low_pen - self.gamma_n * vel[:, axis] * (low_pen > 0)
            force[:, axis] -= self.k_n * high_pen + self.gamma_n * vel[:, axis] * (high_pen > 0)
        return force
