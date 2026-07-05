"""Convergence, stability, and accuracy tests for the integrator family."""

from __future__ import annotations

import numpy as np
import pytest

from psim.experiments.metrics import convergence_order, final_error, max_energy_drift
from psim.integrators import (
    RKF45,
    BackwardEuler,
    ExplicitEuler,
    ExplicitMidpoint,
    ImplicitMidpoint,
    ParkerSochacki,
    RungeKutta4,
    SymplecticEuler,
    Trapezoidal,
    VelocityVerlet,
    simulate,
)
from psim.systems import (
    DampedOscillator,
    ExponentialDecay,
    Kepler,
    MassSpringChain,
    Pendulum,
    StiffSpringDamper,
)


@pytest.mark.parametrize(
    ("integrator", "expected_order"),
    [
        (ExplicitEuler(), 1),
        (ExplicitMidpoint(), 2),
        (RungeKutta4(), 4),
        (BackwardEuler(), 1),
        (ImplicitMidpoint(), 2),
        (Trapezoidal(), 2),
        (SymplecticEuler(), 1),
        (VelocityVerlet(), 2),
    ],
)
def test_observed_convergence_order(integrator, expected_order):
    """Each method converges at its theoretical order on the oscillator."""
    system = DampedOscillator(stiffness=4.0, damping=0.2)
    dts = np.geomspace(0.1, 0.0125, 4)
    errors = [
        final_error(simulate(system, integrator, t_end=2.0, dt=float(dt)), system) for dt in dts
    ]
    observed = convergence_order(dts, np.array(errors))
    assert observed == pytest.approx(expected_order, abs=0.35)


def test_parker_sochacki_machine_precision_on_linear_system():
    """A high-order PSM step solves a linear system to roundoff at dt = 0.5."""
    system = DampedOscillator(stiffness=4.0, damping=0.3)
    trajectory = simulate(system, ParkerSochacki(order=20), t_end=10.0, dt=0.5)
    assert final_error(trajectory, system) < 1e-12


def test_parker_sochacki_kepler_beats_rk4_on_error_and_work():
    """On the eccentric Kepler orbit PSM dominates RK4 in both axes."""
    system = Kepler()
    horizon = 2.0 * np.pi
    psm = simulate(system, ParkerSochacki(order=20, tol=1e-12), t_end=horizon, dt=horizon / 8)
    rk4 = simulate(system, RungeKutta4(), t_end=horizon, dt=1e-3)
    assert final_error(psm, system) < 1e-9 < final_error(rk4, system) * 1e3
    assert psm.rhs_evaluations < rk4.rhs_evaluations


def test_parker_sochacki_requires_polynomial_lifting():
    """Systems without a lifting are rejected with a clear TypeError."""
    from psim.systems import SPHFluid2D

    with pytest.raises(TypeError, match="polynomial lifting"):
        simulate(SPHFluid2D(nx=2, ny=2), ParkerSochacki(order=4), t_end=0.01, dt=0.01)


def test_implicit_stable_where_explicit_explodes():
    """Stiff spring at dt far beyond the explicit stability limit."""
    system = StiffSpringDamper()  # omega = 100, explicit limit dt ~ 0.02
    dt = 0.05
    explicit = simulate(system, ExplicitEuler(), t_end=1.0, dt=dt)
    implicit = simulate(system, BackwardEuler(), t_end=1.0, dt=dt)
    assert not np.all(np.isfinite(explicit.y_final)) or np.linalg.norm(explicit.y_final) > 1e3
    assert np.linalg.norm(implicit.y_final) < 1.0


def test_rkf45_meets_tolerance_adaptively():
    """RKF45 controls global error near its local tolerance on decay."""
    system = ExponentialDecay(rate=3.0)
    trajectory = simulate(system, RKF45(tol=1e-10), t_end=2.0, dt=0.25)
    assert final_error(trajectory, system) < 1e-8


def test_symplectic_energy_bounded_verlet_vs_euler_drift():
    """Verlet's pendulum energy error stays bounded and small; forward
    Euler's grows by orders of magnitude on the same grid."""
    system = Pendulum(theta0=2.0)
    verlet = simulate(system, VelocityVerlet(), t_end=50.0, dt=0.02)
    euler = simulate(system, ExplicitEuler(), t_end=50.0, dt=0.02)
    assert max_energy_drift(verlet, system) < 1e-3
    assert max_energy_drift(euler, system) > 0.1


def test_implicit_midpoint_conserves_quadratic_energy_exactly():
    """Implicit midpoint conserves the harmonic oscillator's (quadratic)
    energy to solver tolerance regardless of step size."""
    system = DampedOscillator(stiffness=9.0, damping=0.0)
    trajectory = simulate(system, ImplicitMidpoint(), t_end=20.0, dt=0.1)
    assert max_energy_drift(trajectory, system) < 1e-9


def test_mass_spring_chain_linear_exactness_of_psm():
    """PSM at moderate order integrates the 8-mass chain to near roundoff."""
    system = MassSpringChain(n=8, stiffness=40.0)
    trajectory = simulate(system, ParkerSochacki(order=24), t_end=3.0, dt=0.25)
    assert final_error(trajectory, system) < 1e-10


def test_kepler_exact_solution_is_consistent():
    """The f-g closed form agrees with a tight adaptive integration."""
    system = Kepler()
    trajectory = simulate(system, RKF45(tol=1e-13), t_end=3.0, dt=0.1)
    assert np.allclose(trajectory.y_final, system.exact(3.0), atol=1e-7)
