"""Tests specific to BDF2 and the generalized-alpha method."""

from __future__ import annotations

import numpy as np
import pytest

from psim.experiments.metrics import (
    convergence_order,
    final_error,
    max_energy_drift,
)
from psim.integrators import BDF2, GeneralizedAlpha, Trapezoidal, simulate
from psim.systems import (
    BouncingBall,
    DampedOscillator,
    Kepler,
    MassSpringChain,
    Pendulum,
    SPHFluid2D,
    StiffSpringDamper,
)


@pytest.mark.parametrize("make", [BDF2, lambda: GeneralizedAlpha(rho_inf=0.9)])
def test_second_order_convergence(make):
    """Both methods converge at order 2 on the damped oscillator."""
    system = DampedOscillator(stiffness=4.0, damping=0.2)
    dts = np.geomspace(0.1, 0.0125, 4)
    errors = [
        final_error(simulate(system, make(), t_end=2.0, dt=float(dt)), system) for dt in dts
    ]
    assert convergence_order(dts, np.array(errors)) == pytest.approx(2.0, abs=0.35)


@pytest.mark.parametrize("make", [BDF2, lambda: GeneralizedAlpha(rho_inf=0.5)])
def test_stable_on_stiff_spring_beyond_explicit_limit(make):
    """Both stay bounded on the k = 1e4 spring at 2.5x the explicit limit."""
    system = StiffSpringDamper()
    trajectory = simulate(system, make(), t_end=1.0, dt=0.05)
    assert np.all(np.isfinite(trajectory.y_final))
    assert np.linalg.norm(trajectory.y_final) < 1.5


def test_bdf2_damps_stiff_transient_without_trapezoidal_ringing():
    """On a stiff decay transient at coarse dt, trapezoidal rings — its
    amplification factor tends to −1, so the iterates alternate sign with
    amplitude stuck near 1 — while L-stable BDF2 annihilates the
    transient within a few steps."""
    from psim.systems import ExponentialDecay

    system = ExponentialDecay(rate=1e4)
    dt = 0.01  # rate * dt = 100: far into the stiff regime
    bdf = simulate(system, BDF2(), t_end=0.1, dt=dt)
    trap = simulate(system, Trapezoidal(), t_end=0.1, dt=dt)
    bdf_y = bdf.states[:, 0]
    trap_y = trap.states[:, 0]
    assert trap_y[1] * trap_y[2] < 0 and abs(trap_y[-1]) > 0.5  # rings, barely decays
    assert np.all(np.abs(bdf_y[3:]) < 1e-3)  # transient crushed


def test_bdf2_restarts_cleanly_across_collision_events():
    """History invalidation: the ball's three impacts are all located and
    the post-event dynamics stay accurate."""
    ball = BouncingBall(restitution=0.8)
    trajectory = simulate(ball, BDF2(), t_end=2.0, dt=0.01)
    assert len(trajectory.events) == 3
    assert abs(trajectory.events[0] - ball.first_impact_time()) < 1e-3
    assert np.all(np.isfinite(trajectory.states))


def test_bdf2_second_order_on_kepler():
    """Multistep history survives the driver's uneven output spans."""
    system = Kepler(eccentricity=0.3)
    dts = np.geomspace(0.02, 0.0025, 4)
    errors = [
        final_error(simulate(system, BDF2(), t_end=1.0, dt=float(dt)), system) for dt in dts
    ]
    assert convergence_order(dts, np.array(errors)) == pytest.approx(2.0, abs=0.35)


def test_generalized_alpha_dissipation_is_frequency_selective():
    """The rho_inf knob kills unresolved modes and spares resolved ones.

    At dt = 0.05 the k = 1e4 oscillator (period 0.063) is unresolvable:
    generalized-alpha with rho_inf = 0.5 should annihilate it while
    trapezoidal keeps its energy ringing forever. The same method on a
    resolved pendulum swing must conserve energy to a few permille.
    """
    stiff = DampedOscillator(stiffness=1e4, damping=0.0)
    ga = simulate(stiff, GeneralizedAlpha(rho_inf=0.5), t_end=2.0, dt=0.05)
    trap = simulate(stiff, Trapezoidal(), t_end=2.0, dt=0.05)
    e0 = stiff.energy(stiff.y0)
    assert stiff.energy(ga.y_final) < 1e-3 * e0  # unresolved mode annihilated
    assert stiff.energy(trap.y_final) > 0.5 * e0  # trapezoidal never damps

    pendulum = Pendulum(theta0=1.0)
    resolved = simulate(pendulum, GeneralizedAlpha(rho_inf=0.5), t_end=5.0, dt=0.01)
    assert max_energy_drift(resolved, pendulum) < 5e-3


def test_generalized_alpha_rho_one_matches_trapezoidal_accuracy():
    """rho_inf = 1 removes all numerical dissipation; on the oscillator
    the result is trapezoidal-grade energy conservation."""
    system = DampedOscillator(stiffness=9.0, damping=0.0)
    trajectory = simulate(system, GeneralizedAlpha(rho_inf=1.0), t_end=20.0, dt=0.05)
    assert max_energy_drift(trajectory, system) < 5e-3


def test_generalized_alpha_handles_nonlinear_chain_and_rejects_nonseparable():
    """Runs on the separable mass-spring chain; clean TypeError otherwise."""
    chain = MassSpringChain(n=4, stiffness=40.0)
    trajectory = simulate(chain, GeneralizedAlpha(rho_inf=0.8), t_end=1.0, dt=0.02)
    assert final_error(trajectory, chain) < 1e-2

    class NotSeparable:
        pass

    with pytest.raises(TypeError, match="not separable"):
        GeneralizedAlpha().step(SPHFluid2DStub(), 0.0, np.zeros(2), 0.01)


class SPHFluid2DStub:
    """A deliberately non-separable stand-in (no acceleration/n_coords)."""

    def rhs(self, t, y):
        return y


def test_generalized_alpha_validates_rho():
    with pytest.raises(ValueError, match="rho_inf"):
        GeneralizedAlpha(rho_inf=1.5)


def test_applicability_flags_route_methods_correctly():
    """The capability flags gate methods exactly like the old name check."""
    from psim.experiments.runner import MethodSpec, applicable
    from psim.systems import SPHFluid2D

    ga_spec = MethodSpec("GA", lambda v: GeneralizedAlpha(), "dt", "structural")
    bdf_spec = MethodSpec("BDF2", lambda v: BDF2(), "dt", "implicit")
    fluid = SPHFluid2D(nx=2, ny=2)
    assert applicable(ga_spec, fluid)  # SPH is separable
    assert applicable(bdf_spec, fluid)
    assert applicable(ga_spec, DampedOscillator())
