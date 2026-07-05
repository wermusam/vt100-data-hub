"""Symplectic / geometric integrators for separable mechanical systems.

These methods exploit the ``q' = v, v' = a(q, v)`` structure (see
:class:`~psim.systems.base.SeparableSystem`) and preserve the phase-space
volume of Hamiltonian flow. The practical consequence — the reason every
game physics engine ships semi-implicit Euler and every molecular
dynamics code ships Verlet — is that energy error stays *bounded*
forever instead of drifting secularly, at order-1/order-2 cost.

Velocity-dependent forces (damping) formally break symplecticity; the
implementations still accept them (velocity Verlet uses the standard
half-kick estimate) because damped systems are half the parameter study.
"""

from __future__ import annotations

import numpy as np

from psim.core.types import FloatArray, StepResult
from psim.integrators.base import Integrator, register_integrator
from psim.systems.base import ODESystem, SeparableSystem


def _split(system: SeparableSystem, y: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Split a flat state into ``(q, v)`` halves, validating the system."""
    if not isinstance(system, SeparableSystem):
        raise TypeError(
            f"{type(system).__name__} is not separable: symplectic integrators "
            "need q' = v, v' = a(t, q, v) structure"
        )
    n = system.n_coords
    return y[:n], y[n:]


@register_integrator("symplectic-euler")
class SymplecticEuler(Integrator):
    """Semi-implicit (symplectic) Euler: kick then drift.

    ``v ← v + dt·a(t, q, v)`` then ``q ← q + dt·v``. Order 1, one force
    evaluation per step, and the default integrator of essentially every
    real-time physics engine.
    """

    order = 1

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        q, v = _split(system, y)
        v_new = v + dt * system.acceleration(t, q, v)
        q_new = q + dt * v_new
        return StepResult(t + dt, np.concatenate([q_new, v_new]), dt)


@register_integrator("velocity-verlet")
class VelocityVerlet(Integrator):
    """Velocity Verlet (leapfrog): kick–drift–kick. Order 2.

    The closing kick is implicit for velocity-dependent forces
    (``v_new = v_half + dt/2·a(q_new, v_new)``); one fixed-point pass on
    that relation keeps the method explicit while retaining second-order
    accuracy in the damping term. For velocity-independent forces the
    extra pass changes nothing (the same acceleration comes back), so
    conservative systems get the textbook kick–drift–kick.
    """

    order = 2

    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        q, v = _split(system, y)
        a0 = system.acceleration(t, q, v)
        v_half = v + 0.5 * dt * a0
        q_new = q + dt * v_half
        v_guess = v_half + 0.5 * dt * system.acceleration(t + dt, q_new, v_half)
        v_new = v_half + 0.5 * dt * system.acceleration(t + dt, q_new, v_guess)
        return StepResult(t + dt, np.concatenate([q_new, v_new]), dt)
