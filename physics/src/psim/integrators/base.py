"""Integrator interface and the simulation driver.

An :class:`Integrator` advances a system one output interval at a time
through :meth:`~Integrator.advance` (which defaults to a single call of
the method's :meth:`~Integrator.step`, but adaptive methods sub-step
internally). The free function :func:`simulate` is the single driver
used by every benchmark and by the Dash app: it meters work, records the
trajectory, and handles discrete events (collisions) for any system that
exposes ``event`` / ``event_response``.

Event location strategy
-----------------------
When a step brackets a sign change of the event guard, the driver asks
the integrator for a *dense interpolant* over the step. Methods with
genuine dense output (Parker–Sochacki's Maclaurin polynomial) return the
polynomial itself, so the crossing is found by bisection on an *exact*
local solution — no extra right-hand-side work. Methods without dense
output fall back to bisection with repeated re-stepping from the step
start, each probe costing a full method step. That asymmetry is one of
the study's headline results; see the collision benchmark.
"""

from __future__ import annotations

import abc
import time
from collections.abc import Callable

import numpy as np

from psim.core.decorators import registry
from psim.core.types import FloatArray, StepResult, Trajectory
from psim.systems.base import ODESystem

#: Global name → class registry of integrators. Classes join it with
#: ``@register_integrator("name")``.
INTEGRATORS, register_integrator = registry()

#: A dense interpolant over one step: maps ``tau ∈ [0, dt]`` to the state.
Interpolant = Callable[[float], FloatArray]


class Integrator(abc.ABC):
    """Base class for one-step integrators.

    Attributes
    ----------
    order:
        Theoretical order of accuracy (global error ~ ``dt**order``);
        used by convergence plots and tests.
    requires_separable:
        True for methods that need ``q' = v, v' = a(t, q, v)`` structure
        (symplectic and structural-dynamics integrators).
    requires_polynomial:
        True for methods that need a Parker–Sochacki polynomial lifting.
    """

    #: Human-readable registry name, stamped by ``@register_integrator``.
    registry_name: str = ""
    order: int = 1
    requires_separable: bool = False
    requires_polynomial: bool = False

    @abc.abstractmethod
    def step(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        """Advance the state by one step of size ``dt``."""

    def advance(self, system: ODESystem, t: float, y: FloatArray, dt: float) -> StepResult:
        """Advance by one *output interval* ``dt``.

        Fixed-step methods take a single step; adaptive methods override
        this to sub-step under error control until the interval is covered.
        """
        return self.step(system, t, y, dt)

    def interpolant(
        self, system: ODESystem, t: float, y: FloatArray, dt: float, result: StepResult
    ) -> Interpolant | None:
        """Dense output over the last step, or ``None`` if unavailable."""
        return None

    @property
    def name(self) -> str:
        """Registry name if registered, else the class name."""
        return self.registry_name or type(self).__name__


class _WorkMeter:
    """Transparent system wrapper that counts work.

    Counts calls to ``rhs`` and — for Parker–Sochacki — to
    ``ps_rhs_coefficient``, the closest per-unit analogue of an RHS
    evaluation. Every other attribute is delegated untouched.
    """

    def __init__(self, system: ODESystem) -> None:
        self._system = system
        self.rhs_calls = 0

    def rhs(self, t: float, y: FloatArray) -> FloatArray:
        self.rhs_calls += 1
        return self._system.rhs(t, y)

    def ps_rhs_coefficient(self, coeffs: FloatArray, k: int) -> FloatArray:
        self.rhs_calls += 1
        return self._system.ps_rhs_coefficient(coeffs, k)

    def __getattr__(self, item: str):  # noqa: ANN204 - pure delegation
        return getattr(self._system, item)


def _locate_event_bisect(
    guard: Callable[[float], float], lo: float, hi: float, iterations: int = 80
) -> float:
    """Bisect ``guard`` (as a function of step-local time) to its root."""
    g_lo = guard(lo)
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        g_mid = guard(mid)
        if g_mid == 0.0:
            return mid
        if (g_lo < 0) == (g_mid < 0):
            lo, g_lo = mid, g_mid
        else:
            hi = mid
        if hi - lo < 1e-15 * max(1.0, abs(hi)):
            break
    return 0.5 * (lo + hi)


def simulate(
    system: ODESystem,
    integrator: Integrator,
    t_end: float,
    dt: float,
    y0: FloatArray | None = None,
    t0: float = 0.0,
    handle_events: bool = True,
    max_events: int = 10_000,
) -> Trajectory:
    """Integrate ``system`` from ``t0`` to ``t_end`` at output interval ``dt``.

    Parameters
    ----------
    system:
        The model to integrate.
    integrator:
        Any :class:`Integrator`; adaptive methods sub-step internally.
    t_end, dt, y0, t0:
        Horizon, output interval, initial state (defaults to
        ``system.y0``), and start time.
    handle_events:
        If the system defines ``event(t, y)`` and ``event_response(t, y)``,
        locate each guard crossing inside a step, apply the response
        there, and finish the step from the post-event state.
    max_events:
        Safety valve against Zeno behavior (e.g. a bouncing ball's
        accumulation point): once exceeded, further guard crossings are
        left unhandled and integration proceeds smoothly.

    Returns
    -------
    Trajectory
        Sampled states with work and wall-time accounting; located event
        times are in ``Trajectory.events``.
    """
    metered = _WorkMeter(system)
    y = np.array(system.y0 if y0 is None else y0, dtype=float)
    t = t0
    times = [t]
    states = [y.copy()]
    events: list[float] = []

    has_events = handle_events and hasattr(system, "event") and hasattr(system, "event_response")
    n_out = int(round((t_end - t0) / dt))
    if n_out < 1:
        raise ValueError("t_end must lie at least one dt after t0")

    start = time.perf_counter()
    for i in range(n_out):
        t_target = t0 + (i + 1) * dt
        # After an event the remaining sub-interval is shorter than dt.
        while t < t_target - 1e-12 * max(1.0, abs(t_target)):
            span = t_target - t
            result = integrator.advance(metered, t, y, span)
            if has_events and len(events) < max_events:
                g0 = system.event(t, y)
                g1 = system.event(result.t, result.y)
                if g0 > 0.0 >= g1:
                    dense = integrator.interpolant(metered, t, y, span, result)
                    if dense is not None:
                        guard = lambda tau: system.event(t + tau, dense(tau))  # noqa: B023
                        state_at = dense
                    else:
                        guard = lambda tau: system.event(  # noqa: B023
                            t + tau, integrator.advance(metered, t, y, tau).y
                        )
                        state_at = lambda tau: integrator.advance(metered, t, y, tau).y  # noqa: B023
                    tau_hit = _locate_event_bisect(guard, 0.0, span)
                    t_hit = t + tau_hit
                    y_hit = state_at(tau_hit)
                    y = system.event_response(t_hit, y_hit)
                    t = t_hit
                    events.append(t_hit)
                    continue
            t, y = result.t, result.y
        times.append(t)
        states.append(y.copy())
    wall = time.perf_counter() - start

    return Trajectory(
        times=np.array(times),
        states=np.array(states),
        method=integrator.name,
        system=system.name,
        rhs_evaluations=metered.rhs_calls,
        wall_time=wall,
        events=events,
    )
