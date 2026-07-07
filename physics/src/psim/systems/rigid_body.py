"""Free rigid body: quaternion attitude + Euler's equations.

The paper's centerpiece system. A tumbling rigid body is where game
engines give up on analytic time-of-impact (Catto, GDC 2013: assumed
constant linear/angular velocity between steps, polynomial TOI declared
intractable) - yet the *actual* dynamics are already polynomial:

* Euler's equations in the body frame (principal axes, inertia
  ``I1, I2, I3``) are quadratic in the angular velocity::

      w1' = ((I2 - I3)/I1) w2 w3
      w2' = ((I3 - I1)/I2) w3 w1
      w3' = ((I1 - I2)/I3) w1 w2

* Quaternion attitude kinematics are bilinear in (q, w)::

      q' = (1/2) q x (0, w)      (quaternion product)

So the Parker-Sochacki "lifting" is the identity: no auxiliary
variables at all, just Cauchy products of state components. Each PSM
step therefore yields the body's orientation as a polynomial in time,
which is exactly the object continuous collision detection needs for a
rotating body (a corner's world position ``x + R(q)v`` is polynomial in
q, hence polynomial in time).

The default configuration tumbles about the intermediate axis (the
Dzhanibekov / tennis-racket instability), the hardest smooth test of
attitude integrators: trajectories repeatedly flip between unstable
saddle passages, punishing low-order methods.

Torque-free invariants used by the benchmarks: rotational kinetic
energy ``T = (1/2) sum_i I_i w_i^2`` and the squared angular-momentum
magnitude ``|L|^2 = sum_i (I_i w_i)^2`` (the world-frame vector ``L`` is
constant; its body-frame components move on the momentum sphere).
The unit-quaternion constraint is restored exactly at every step start
by :meth:`ps_lift` (and measured, not enforced, in between).
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray
from psim.systems.base import ODESystem, cauchy, register_system


def _quat_multiply(a: FloatArray, b: FloatArray) -> FloatArray:
    """Hamilton product of two quaternions ``(w, x, y, z)``."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.array(
        [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ]
    )


@register_system("rigid-body")
class FreeRigidBody(ODESystem):
    """Torque-free rigid body with quaternion attitude.

    State is ``y = (qw, qx, qy, qz, w1, w2, w3)`` with the angular
    velocity expressed in the body's principal frame.

    Parameters
    ----------
    inertia:
        Principal moments ``(I1, I2, I3)``, all positive.
    omega0:
        Initial body-frame angular velocity. The default spins about
        the intermediate axis with a small transverse perturbation,
        triggering the Dzhanibekov instability.
    """

    def __init__(
        self,
        inertia: tuple[float, float, float] = (1.0, 2.0, 3.0),
        omega0: tuple[float, float, float] = (0.05, 1.0, 0.05),
    ) -> None:
        if any(i <= 0 for i in inertia):
            raise ValueError("principal moments of inertia must be positive")
        self.inertia = np.asarray(inertia, dtype=float)
        i1, i2, i3 = self.inertia
        # Euler-equation gyroscopic coefficients.
        self._gyro = np.array([(i2 - i3) / i1, (i3 - i1) / i2, (i1 - i2) / i3])
        self._y0 = np.concatenate([[1.0, 0.0, 0.0, 0.0], np.asarray(omega0, dtype=float)])

    @property
    def dim(self) -> int:
        return 7

    @property
    def y0(self) -> FloatArray:
        return self._y0

    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        q, w = y[:4], y[4:]
        q_dot = 0.5 * _quat_multiply(q, np.array([0.0, w[0], w[1], w[2]]))
        w_dot = self._gyro * np.array([w[1] * w[2], w[2] * w[0], w[0] * w[1]])
        return np.concatenate([q_dot, w_dot])

    def energy(self, y: FloatArray) -> float:
        w = y[4:]
        return 0.5 * float(np.sum(self.inertia * w * w))

    def momentum_magnitude(self, y: FloatArray) -> float:
        """Norm of the angular momentum ``L = I w`` (conserved)."""
        return float(np.linalg.norm(self.inertia * y[4:]))

    def quaternion_norm(self, y: FloatArray) -> float:
        """Attitude-quaternion norm (should stay at 1)."""
        return float(np.linalg.norm(y[:4]))

    def invariants(self, y: FloatArray) -> dict[str, float]:
        return {
            "energy": self.energy(y),
            "momentum": self.momentum_magnitude(y),
            "quaternion_norm": self.quaternion_norm(y),
        }

    def rotation_matrix(self, y: FloatArray) -> FloatArray:
        """World-from-body rotation matrix of the attitude quaternion.

        Quadratic in q, hence polynomial in time along a PSM step: this
        is what makes corner trajectories ``x + R(q)v`` polynomial and
        rigid-body CCD a root-isolation problem.
        """
        w, x, yq, z = y[:4] / np.linalg.norm(y[:4])
        return np.array(
            [
                [1 - 2 * (yq * yq + z * z), 2 * (x * yq - z * w), 2 * (x * z + yq * w)],
                [2 * (x * yq + z * w), 1 - 2 * (x * x + z * z), 2 * (yq * z - x * w)],
                [2 * (x * z - yq * w), 2 * (yq * z + x * w), 1 - 2 * (x * x + yq * yq)],
            ]
        )

    # -- PolynomialODE: the RHS is already polynomial (identity lifting) -----
    @property
    def ps_dim(self) -> int:
        return 7

    def ps_lift(self, y: FloatArray) -> FloatArray:
        z = np.asarray(y, dtype=float).copy()
        z[:4] /= np.linalg.norm(z[:4])  # exact re-projection onto S^3
        return z

    def ps_restrict(self, z: FloatArray) -> FloatArray:
        return z

    def ps_rhs_coefficient(self, coeffs: FloatArray, k: int) -> FloatArray:
        qw, qx, qy, qz = (coeffs[:, i] for i in range(4))
        w1, w2, w3 = (coeffs[:, i] for i in range(4, 7))
        g1, g2, g3 = self._gyro
        return np.array(
            [
                0.5 * (-cauchy(qx, w1, k) - cauchy(qy, w2, k) - cauchy(qz, w3, k)),
                0.5 * (cauchy(qw, w1, k) + cauchy(qy, w3, k) - cauchy(qz, w2, k)),
                0.5 * (cauchy(qw, w2, k) - cauchy(qx, w3, k) + cauchy(qz, w1, k)),
                0.5 * (cauchy(qw, w3, k) + cauchy(qx, w2, k) - cauchy(qy, w1, k)),
                g1 * cauchy(w2, w3, k),
                g2 * cauchy(w3, w1, k),
                g3 * cauchy(w1, w2, k),
            ]
        )
