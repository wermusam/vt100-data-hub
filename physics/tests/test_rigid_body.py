"""Tests for the free rigid body (quaternion + Euler equations)."""

from __future__ import annotations

import numpy as np
import pytest

from psim.integrators import RKF45, ParkerSochacki, RungeKutta4, simulate
from psim.systems import FreeRigidBody


def test_dzhanibekov_flip_actually_happens():
    """The intermediate-axis spin flips sign: the demo is real."""
    body = FreeRigidBody()
    run = simulate(body, ParkerSochacki(order=16, tol=1e-13), t_end=40.0, dt=0.1)
    w2 = run.states[:, 5]
    assert w2.max() > 0.9 and w2.min() < -0.9  # full flips both ways


def test_psm_conserves_energy_and_momentum_through_flips():
    """Energy and |L| stay at roundoff across many unstable passages."""
    body = FreeRigidBody()
    run = simulate(body, ParkerSochacki(order=16, tol=1e-13), t_end=40.0, dt=0.1)
    e0 = body.energy(run.states[0])
    l0 = body.momentum_magnitude(run.states[0])
    e_drift = max(abs(body.energy(s) - e0) for s in run.states) / e0
    l_drift = max(abs(body.momentum_magnitude(s) - l0) for s in run.states) / l0
    assert e_drift < 1e-11
    assert l_drift < 1e-11


def test_quaternion_norm_preserved_by_step_start_projection():
    """PSM re-projects onto the unit sphere each step; norm error stays
    at truncation level throughout the run."""
    body = FreeRigidBody()
    run = simulate(body, ParkerSochacki(order=16, tol=1e-13), t_end=20.0, dt=0.1)
    norms = [body.quaternion_norm(s) for s in run.states]
    assert max(abs(n - 1.0) for n in norms) < 1e-10


def test_psm_matches_tight_adaptive_reference():
    """PSM at big steps agrees with RKF45 at tol=1e-13 taking tiny ones."""
    body = FreeRigidBody(inertia=(1.0, 2.0, 3.0), omega0=(0.2, 0.9, 0.1))
    horizon = 5.0
    psm = simulate(body, ParkerSochacki(order=20, tol=1e-13), t_end=horizon, dt=0.5)
    ref = simulate(body, RKF45(tol=1e-13), t_end=horizon, dt=0.5)
    assert np.max(np.abs(psm.y_final - ref.y_final)) < 1e-8
    assert psm.rhs_evaluations < ref.rhs_evaluations


def test_rk4_needs_far_more_work_for_same_invariant_quality():
    """At equal (loose) work, RK4's energy drift dwarfs PSM's."""
    body = FreeRigidBody()
    psm = simulate(body, ParkerSochacki(order=12), t_end=20.0, dt=0.2)
    rk4 = simulate(body, RungeKutta4(), t_end=20.0, dt=0.2)
    e0 = body.energy(body.y0)
    psm_drift = abs(body.energy(psm.y_final) - e0) / e0
    rk4_drift = abs(body.energy(rk4.y_final) - e0) / e0
    assert psm_drift < 1e-10
    assert rk4_drift > 100 * psm_drift


def test_rotation_matrix_is_orthonormal():
    body = FreeRigidBody()
    run = simulate(body, ParkerSochacki(order=12), t_end=3.0, dt=0.1)
    rot = body.rotation_matrix(run.y_final)
    np.testing.assert_allclose(rot @ rot.T, np.eye(3), atol=1e-9)
    assert np.linalg.det(rot) == pytest.approx(1.0, abs=1e-9)


def test_validates_inertia():
    with pytest.raises(ValueError, match="inertia"):
        FreeRigidBody(inertia=(1.0, -2.0, 3.0))
