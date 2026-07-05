"""Mass–spring chain: the smallest "deformable body" in the ladder.

``n`` equal masses in one dimension, joined to each other and to two
fixed walls by identical springs and dashpots, written in displacement
coordinates so the dynamics are linear and homogeneous::

    M q'' = −K q − C q'

with tridiagonal stiffness ``K``. This is the discrete Laplacian — the
1-D version of every cloth/soft-body solver — and it scales the
stiff-spring story up to many coupled modes: the highest mode has
frequency ``≈ 2√(k/m)``, which is what caps the explicit stable step as
``n`` or ``k`` grow. Being linear, it inherits the exact solution and
the trivial Parker–Sochacki recurrence from :class:`LinearSystem`.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray
from psim.systems.base import register_system
from psim.systems.canonical import LinearSystem


@register_system("mass-spring-chain")
class MassSpringChain(LinearSystem):
    """A chain of ``n`` masses between fixed walls.

    State is ``(q₁..qₙ, v₁..vₙ)`` where ``qᵢ`` is displacement from rest.
    The default initial condition plucks the chain into its smoothest
    shape (a half sine), which keeps energy in low modes and makes energy
    plots readable.

    Parameters
    ----------
    n:
        Number of masses.
    stiffness, damping, mass:
        Per-spring stiffness, per-dashpot damping, per-node mass.
    pluck:
        Amplitude of the initial half-sine displacement.
    """

    def __init__(
        self,
        n: int = 8,
        stiffness: float = 40.0,
        damping: float = 0.0,
        mass: float = 1.0,
        pluck: float = 0.5,
    ) -> None:
        if n < 1:
            raise ValueError("need at least one mass")
        if stiffness <= 0 or mass <= 0 or damping < 0:
            raise ValueError("require stiffness > 0, mass > 0, damping >= 0")
        self.n = n
        self.stiffness = stiffness
        self.damping = damping
        self.mass = mass

        lap = 2.0 * np.eye(n) - np.eye(n, k=1) - np.eye(n, k=-1)
        self._k_over_m = (stiffness / mass) * lap
        self._c_over_m = (damping / mass) * lap
        matrix = np.block(
            [
                [np.zeros((n, n)), np.eye(n)],
                [-self._k_over_m, -self._c_over_m],
            ]
        )
        x = np.arange(1, n + 1) / (n + 1)
        y0 = np.concatenate([pluck * np.sin(np.pi * x), np.zeros(n)])
        super().__init__(matrix, y0)

    def energy(self, y: FloatArray) -> float:
        q, v = y[: self.n], y[self.n :]
        # Spring extensions include the two wall attachments.
        ext = np.diff(q, prepend=0.0, append=0.0)
        return 0.5 * self.mass * float(v @ v) + 0.5 * self.stiffness * float(ext @ ext)

    # -- SeparableSystem ---------------------------------------------------
    @property
    def n_coords(self) -> int:
        return self.n

    def acceleration(self, t: float, q: FloatArray, v: FloatArray) -> FloatArray:
        return -self._k_over_m @ q - self._c_over_m @ v
