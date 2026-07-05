"""Decorators, registries, series algebra, and benchmark-suite tests."""

from __future__ import annotations

import numpy as np
import pytest

from psim.core.decorators import counted, memoized, registry, timed
from psim.experiments import benchmarks
from psim.experiments.metrics import convergence_order
from psim.integrators import INTEGRATORS
from psim.systems import SYSTEMS, Pendulum, cauchy, series_product


def test_registries_are_populated():
    for name in ("euler", "rk4", "backward-euler", "velocity-verlet", "parker-sochacki"):
        assert name in INTEGRATORS
    for name in ("decay", "oscillator", "pendulum", "kepler", "bouncing-ball", "sph-fluid"):
        assert name in SYSTEMS


def test_registry_rejects_duplicates():
    _, register = registry()

    @register("x")
    class A:  # noqa: D401
        pass

    with pytest.raises(ValueError, match="duplicate"):

        @register("x")
        class B:
            pass


def test_counted_and_timed_decorators():
    @counted
    @timed()
    def f(x):
        return x * 2

    assert f(3) == 6 and f(4) == 8
    assert f.calls == 2
    f.reset_count()
    assert f.calls == 0


def test_memoized_caches_by_arguments():
    calls = []

    @memoized
    def g(a, b=1):
        calls.append((a, b))
        return a + b

    assert g(1) == 2 and g(1) == 2 and g(1, b=2) == 3
    assert len(calls) == 2
    g.clear_cache()
    assert g(1) == 2 and len(calls) == 3


def test_cauchy_product_matches_polynomial_multiplication():
    """Series product coefficients equal numpy polynomial products."""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([4.0, 5.0, 6.0])
    ours = series_product(a, b, 4)
    theirs = np.convolve(a, b)
    np.testing.assert_allclose(ours, theirs[:5])
    assert cauchy(a, b, 2) == pytest.approx(theirs[2])


def test_pendulum_lift_restrict_round_trip():
    system = Pendulum()
    y = np.array([0.7, -1.2])
    z = system.ps_lift(y)
    np.testing.assert_allclose(system.ps_restrict(z), y)
    assert z[2] == pytest.approx(np.sin(0.7)) and z[3] == pytest.approx(np.cos(0.7))


def test_convergence_study_reports_correct_orders():
    frame = benchmarks.convergence_study("oscillator", t_end=2.0, n_dts=5)
    orders = frame.groupby("method")["observed_order"].first()
    assert orders["RK4"] == pytest.approx(4.0, abs=0.5)
    assert orders["Euler"] == pytest.approx(1.0, abs=0.35)


def test_stiffness_map_shows_explicit_implicit_divide():
    frame = benchmarks.stiffness_stability_study(n_stiffness=3, n_dts=3, t_end=1.0)
    hardest = frame[(frame["stiffness"] == frame["stiffness"].max()) & (frame["dt"] == frame["dt"].max())]
    assert not hardest[hardest["method"] == "Euler"]["stable"].iloc[0]
    assert hardest[hardest["method"] == "Backward Euler"]["stable"].iloc[0]


def test_collision_study_psm_flat_error_curve():
    """PSM impact-time error is roundoff-flat across dt; Euler's shrinks
    like dt (its bisection is limited by the method's own local error)."""
    frame = benchmarks.collision_study(n_dts=4)
    psm = frame[frame["method"].str.startswith("PSM")]["impact_time_error"]
    assert psm.max() < 1e-10
    euler = frame[frame["method"] == "Euler"].dropna(subset=["impact_time_error"])
    errs = euler.sort_values("dt")["impact_time_error"].to_numpy(dtype=float)
    assert errs[-1] > errs[0]  # error grows with dt for Euler


def test_convergence_order_helper_ignores_roundoff_floor():
    dts = np.array([0.1, 0.05, 0.025, 0.0125])
    errors = np.array([1e-3, 2.5e-4, 6.25e-5, 1e-16])
    assert convergence_order(dts, errors) == pytest.approx(2.0, abs=0.05)
