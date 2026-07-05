"""Canned, reproducible benchmark studies backing the research questions.

Each function answers one question from the project brief and returns a
tidy DataFrame ready for plotting:

* :func:`convergence_study` — how does error scale with the time step?
* :func:`work_precision_study` — accuracy per unit of work (the honest
  comparison, since a PSM step costs many coefficient recurrences).
* :func:`energy_drift_study` — who conserves energy over long horizons?
* :func:`stiffness_stability_study` — which (stiffness, dt) cells stay
  stable per method: the "more stiffness" parameter-flexibility axis.
* :func:`damping_sweep_study` — accuracy across the damping range: the
  "more damping" axis.
* :func:`collision_study` — impact-time accuracy and cost for the
  bouncing ball: dense-output PSM vs re-stepping classical methods.
* :func:`psm_order_study` — PSM's unique knob: error vs series order.

Everything is memoized so the Dash app pays for each study once.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from psim.core.decorators import memoized
from psim.experiments import metrics
from psim.experiments.runner import MethodSpec, applicable, run_sweep
from psim.integrators import (
    BDF2,
    RKF45,
    BackwardEuler,
    ExplicitEuler,
    ExplicitMidpoint,
    GeneralizedAlpha,
    ImplicitMidpoint,
    ParkerSochacki,
    RungeKutta4,
    SymplecticEuler,
    Trapezoidal,
    VelocityVerlet,
    simulate,
)
from psim.systems import (
    SYSTEMS,
    BouncingBall,
    DampedOscillator,
    ODESystem,
)

#: Systems suitable for method benchmarks (constructed with defaults).
BENCHMARK_SYSTEMS = ("decay", "oscillator", "stiff-spring", "pendulum", "kepler", "mass-spring-chain")


def make_system(name: str) -> ODESystem:
    """Instantiate a registered system with its default parameters."""
    return SYSTEMS[name]()


def fixed_step_methods(psm_order: int = 12) -> list[MethodSpec]:
    """The fixed-step lineup used by every dt-controlled study."""
    return [
        MethodSpec("Euler", lambda v: ExplicitEuler(), "dt", "explicit"),
        MethodSpec("Midpoint (RK2)", lambda v: ExplicitMidpoint(), "dt", "explicit"),
        MethodSpec("RK4", lambda v: RungeKutta4(), "dt", "explicit"),
        MethodSpec("Backward Euler", lambda v: BackwardEuler(), "dt", "implicit"),
        MethodSpec("Implicit midpoint", lambda v: ImplicitMidpoint(), "dt", "implicit"),
        MethodSpec("Trapezoidal", lambda v: Trapezoidal(), "dt", "implicit"),
        MethodSpec("BDF2", lambda v: BDF2(), "dt", "implicit"),
        MethodSpec(
            "Generalized-alpha (rho 0.9)",
            lambda v: GeneralizedAlpha(rho_inf=0.9),
            "dt",
            "structural",
        ),
        MethodSpec("Symplectic Euler", lambda v: SymplecticEuler(), "dt", "symplectic"),
        MethodSpec("Velocity Verlet", lambda v: VelocityVerlet(), "dt", "symplectic"),
        MethodSpec(
            f"PSM (order {psm_order})",
            lambda v: ParkerSochacki(order=psm_order),
            "dt",
            "series",
        ),
    ]


def adaptive_methods(psm_order: int = 16) -> list[MethodSpec]:
    """Tolerance-controlled methods for work–precision studies."""
    return [
        MethodSpec("RKF45 (adaptive)", lambda tol: RKF45(tol=tol), "tol", "explicit"),
        MethodSpec(
            f"PSM adaptive (order {psm_order})",
            lambda tol: ParkerSochacki(order=psm_order, tol=tol),
            "tol",
            "series",
        ),
    ]


@memoized
def convergence_study(
    system_name: str, t_end: float = 5.0, n_dts: int = 8, psm_order: int = 12
) -> pd.DataFrame:
    """Error vs step size for every applicable fixed-step method.

    Adds an ``observed_order`` column (least-squares slope per method)
    so the log–log plot can be annotated with measured orders.
    """
    system = make_system(system_name)
    dts = np.geomspace(0.2, 0.003125, n_dts)
    frame = run_sweep(system, fixed_step_methods(psm_order), dts, t_end=t_end)
    orders = {}
    for method, group in frame.groupby("method"):
        good = group.dropna(subset=["final_error"])
        orders[method] = metrics.convergence_order(
            good["value"].to_numpy(), good["final_error"].to_numpy()
        )
    frame["observed_order"] = frame["method"].map(orders)
    return frame


@memoized
def work_precision_study(system_name: str, t_end: float = 5.0) -> pd.DataFrame:
    """Final error vs right-hand-side work, fixed-step and adaptive together."""
    system = make_system(system_name)
    fixed = run_sweep(system, fixed_step_methods(), np.geomspace(0.2, 0.003125, 8), t_end=t_end)
    tols = np.geomspace(1e-4, 1e-12, 7)
    adaptive = run_sweep(system, adaptive_methods(), tols, t_end=t_end, dt_out=t_end / 32.0)
    return pd.concat([fixed, adaptive], ignore_index=True)


@memoized
def energy_drift_study(
    system_name: str = "pendulum", t_end: float = 60.0, dt: float = 0.05
) -> pd.DataFrame:
    """Relative energy drift over a long horizon, per method, as time series."""
    system = make_system(system_name)
    rows = []
    for spec in fixed_step_methods():
        if not applicable(spec, system):
            continue
        trajectory = simulate(system, spec.build(dt), t_end=t_end, dt=dt)
        drift = metrics.energy_drift(trajectory, system)
        if drift is None:
            continue
        for t, d in zip(trajectory.times, drift, strict=True):
            rows.append(
                {"method": spec.label, "family": spec.family, "t": float(t), "drift": float(d)}
            )
    return pd.DataFrame(rows)


@memoized
def stiffness_stability_study(
    n_stiffness: int = 9, n_dts: int = 9, t_end: float = 2.0
) -> pd.DataFrame:
    """Stability map: is (method, stiffness, dt) bounded after ``t_end``?

    A run counts as stable when the final state norm stays within 10×
    the initial norm — crude, but it draws exactly the textbook
    stability boundaries (explicit: ``dt ∝ 1/√k``; implicit: everywhere).
    """
    rows = []
    stiffnesses = np.geomspace(1.0, 1.0e4, n_stiffness)
    dts = np.geomspace(0.2, 0.001, n_dts)
    for spec in fixed_step_methods():
        for k in stiffnesses:
            system = DampedOscillator(stiffness=float(k), damping=0.1)
            y_scale = float(np.linalg.norm(system.y0))
            for dt in dts:
                try:
                    trajectory = simulate(system, spec.build(dt), t_end=t_end, dt=float(dt))
                    final = float(np.linalg.norm(trajectory.y_final))
                    stable = bool(np.isfinite(final) and final <= 10.0 * y_scale)
                except (FloatingPointError, OverflowError, np.linalg.LinAlgError):
                    stable = False
                rows.append(
                    {
                        "method": spec.label,
                        "family": spec.family,
                        "stiffness": float(k),
                        "dt": float(dt),
                        "stable": stable,
                    }
                )
    return pd.DataFrame(rows)


@memoized
def damping_sweep_study(
    n_damping: int = 9, dt: float = 0.05, t_end: float = 5.0
) -> pd.DataFrame:
    """Accuracy across the damping range at a fixed, moderate step size.

    Sweeps the oscillator from undamped through heavily overdamped
    (where the fast eigenvalue makes the problem stiff again), asking
    which methods keep their accuracy as ``c`` grows.
    """
    rows = []
    dampings = np.geomspace(0.01, 100.0, n_damping)
    for spec in fixed_step_methods():
        for c in dampings:
            system = DampedOscillator(stiffness=4.0, damping=float(c))
            if not applicable(spec, system):
                continue
            try:
                trajectory = simulate(system, spec.build(dt), t_end=t_end, dt=dt)
                error = metrics.final_error(trajectory, system)
            except (FloatingPointError, OverflowError, np.linalg.LinAlgError):
                error = None
            rows.append(
                {
                    "method": spec.label,
                    "family": spec.family,
                    "damping": float(c),
                    "final_error": error,
                }
            )
    return pd.DataFrame(rows)


@memoized
def collision_study(n_dts: int = 8, t_end: float = 0.9) -> pd.DataFrame:
    """First-impact timing error and total work for the bouncing ball.

    The horizon contains exactly one true impact (at ~0.45 s; the next
    is at ~1.17 s), so ``events[0]`` compares directly against the
    closed-form impact time even when a coarse method locates it late.
    PSM locates it on its dense polynomial (no extra RHS work);
    classical methods bisect by re-integrating partial steps, which
    shows up in ``rhs_evals``.
    """
    rows = []
    ball = BouncingBall()
    t_star = ball.first_impact_time()
    specs = [
        MethodSpec("Euler", lambda v: ExplicitEuler(), "dt", "explicit"),
        MethodSpec("RK4", lambda v: RungeKutta4(), "dt", "explicit"),
        MethodSpec("Velocity Verlet", lambda v: VelocityVerlet(), "dt", "symplectic"),
        MethodSpec("PSM (order 4, dense)", lambda v: ParkerSochacki(order=4), "dt", "series"),
    ]
    for spec in specs:
        for dt in np.geomspace(0.3, 0.002, n_dts):
            trajectory = simulate(ball, spec.build(float(dt)), t_end=t_end, dt=float(dt))
            impact_error = abs(trajectory.events[0] - t_star) if trajectory.events else None
            rows.append(
                {
                    "method": spec.label,
                    "family": spec.family,
                    "dt": float(dt),
                    "impact_time_error": impact_error,
                    "rhs_evals": trajectory.rhs_evaluations,
                }
            )
    return pd.DataFrame(rows)


@memoized
def psm_order_study(
    system_name: str = "kepler", dt: float = 0.25, t_end: float = 5.0, max_order: int = 24
) -> pd.DataFrame:
    """PSM's unique degree of freedom: accuracy vs series order at fixed dt.

    No Runge–Kutta method can trade order for step size at runtime; this
    study shows error falling geometrically with order until roundoff,
    while work grows only quadratically.
    """
    system = make_system(system_name)
    rows = []
    for order in range(2, max_order + 1, 2):
        trajectory = simulate(system, ParkerSochacki(order=order), t_end=t_end, dt=dt)
        rows.append(
            {
                "order": order,
                "dt": dt,
                "final_error": metrics.final_error(trajectory, system),
                "energy_drift": metrics.max_energy_drift(trajectory, system),
                "rhs_evals": trajectory.rhs_evaluations,
                "wall_time": trajectory.wall_time,
            }
        )
    return pd.DataFrame(rows)
