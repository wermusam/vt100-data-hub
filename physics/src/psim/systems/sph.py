"""A minimal 2-D weakly-compressible SPH fluid (dam-break toy).

Smoothed-particle hydrodynamics à la Müller et al. (2003): poly6 kernel
for density, spiky kernel gradient for pressure, viscosity Laplacian,
gravity, and penalty walls. Everything is vectorized over all particle
pairs (O(n²) — fine at demo scale; a neighbor grid is the obvious
upgrade and is on the roadmap in the README).

This is the top of the complexity ladder and, like the granular box, it
is *not* Parker–Sochacki-liftable in any useful way: the kernels have
compact support, so the right-hand side is only piecewise smooth as the
neighbor set changes. It exists to (a) exercise the classical
integrators on a real particle medium and (b) feed the Houdini/Unreal
frame exporter with something worth looking at.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray
from psim.systems.base import ODESystem, register_system


@register_system("sph-fluid")
class SPHFluid2D(ODESystem):
    """Dam-break block of SPH particles in a unit box.

    State is ``(x₁, y₁, …, xₙ, yₙ, vx₁, …, vyₙ)``, like
    :class:`~psim.systems.particles.GranularBox2D`.

    Parameters
    ----------
    nx, ny:
        The initial block is an ``nx × ny`` grid in the box's left half.
    h:
        Smoothing length; also sets particle spacing (``0.9·h``).
    rest_density, stiffness, viscosity:
        Equation-of-state and momentum parameters. ``stiffness`` maps
        density error to pressure — the fluid analogue of the study's
        stiffness knob (stiffer fluid = less compressible = smaller
        stable explicit step).
    """

    def __init__(
        self,
        nx: int = 8,
        ny: int = 10,
        h: float = 0.06,
        rest_density: float = 1000.0,
        stiffness: float = 800.0,
        viscosity: float = 0.5,
        gravity: float = 9.81,
        box: float = 1.0,
        wall_k: float = 3.0e3,
        wall_damping: float = 8.0,
    ) -> None:
        if nx < 1 or ny < 1 or h <= 0:
            raise ValueError("need a nonempty particle block and h > 0")
        self.n = nx * ny
        self.h = h
        self.rest_density = rest_density
        self.stiffness = stiffness
        self.viscosity = viscosity
        self.gravity = gravity
        self.box = box
        self.wall_k = wall_k
        self.wall_damping = wall_damping

        spacing = 0.9 * h
        # Particle mass so a filled neighborhood reproduces rest density.
        self.particle_mass = rest_density * spacing**2

        cols, rows = np.meshgrid(np.arange(nx), np.arange(ny))
        x = 0.08 + cols.ravel() * spacing
        y = 0.08 + rows.ravel() * spacing
        self._y0 = np.concatenate([np.column_stack([x, y]).ravel(), np.zeros(2 * self.n)])

        # Kernel normalization constants (2-D).
        self._poly6 = 4.0 / (np.pi * h**8)
        self._spiky_grad = -30.0 / (np.pi * h**5)
        self._visc_lap = 40.0 / (np.pi * h**5)

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

    def density(self, pos: FloatArray) -> FloatArray:
        """SPH density estimate at each particle, shape ``(n,)``."""
        r2 = self._pair_dist2(pos)
        w = np.where(r2 < self.h**2, self._poly6 * (self.h**2 - r2) ** 3, 0.0)
        return self.particle_mass * w.sum(axis=1)

    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        pos = self.positions(y)
        vel = self.velocities(y)
        return np.concatenate([vel.ravel(), self._acceleration(pos, vel).ravel()])

    def energy(self, y: FloatArray) -> float:
        """Kinetic + gravitational energy (pressure work is not tracked,
        so treat this as a settling diagnostic, not an invariant)."""
        pos = self.positions(y)
        vel = self.velocities(y)
        kinetic = 0.5 * self.particle_mass * float(np.sum(vel * vel))
        potential = self.particle_mass * self.gravity * float(np.sum(pos[:, 1]))
        return kinetic + potential

    # -- SeparableSystem ---------------------------------------------------
    @property
    def n_coords(self) -> int:
        return 2 * self.n

    def acceleration(self, t: float, q: FloatArray, v: FloatArray) -> FloatArray:
        return self._acceleration(q.reshape(self.n, 2), v.reshape(self.n, 2)).ravel()

    # -- Internals -----------------------------------------------------------
    def _pair_dist2(self, pos: FloatArray) -> FloatArray:
        delta = pos[:, None, :] - pos[None, :, :]
        return np.sum(delta * delta, axis=-1)

    def _acceleration(self, pos: FloatArray, vel: FloatArray) -> FloatArray:
        h = self.h
        m = self.particle_mass
        delta = pos[:, None, :] - pos[None, :, :]  # (n, n, 2), i minus j
        r2 = np.sum(delta * delta, axis=-1)
        r = np.sqrt(np.maximum(r2, 1e-12))
        in_range = (r2 < h * h) & ~np.eye(self.n, dtype=bool)

        density = self.density(pos)
        pressure = self.stiffness * (density - self.rest_density)

        # Pressure force: symmetric (p_i + p_j) / 2ρ_j form, spiky gradient.
        grad_mag = np.where(in_range, self._spiky_grad * (h - r) ** 2, 0.0)
        direction = delta / r[..., None]
        shared_p = (pressure[:, None] + pressure[None, :]) / (2.0 * density[None, :])
        f_pressure = -(m * shared_p * grad_mag)[..., None] * direction

        # Viscosity: Laplacian kernel on relative velocity.
        lap = np.where(in_range, self._visc_lap * (h - r), 0.0)
        rel_v = vel[None, :, :] - vel[:, None, :]
        f_visc = self.viscosity * m * (lap / density[None, :])[..., None] * rel_v

        acc = (f_pressure + f_visc).sum(axis=1) / density[:, None]
        acc[:, 1] -= self.gravity

        # Penalty walls with damping, matching the granular box.
        for axis in (0, 1):
            low = np.maximum(0.0, 0.02 - pos[:, axis])
            high = np.maximum(0.0, pos[:, axis] - (self.box - 0.02))
            acc[:, axis] += self.wall_k * low - self.wall_damping * vel[:, axis] * (low > 0)
            acc[:, axis] -= self.wall_k * high + self.wall_damping * vel[:, axis] * (high > 0)
        return acc
