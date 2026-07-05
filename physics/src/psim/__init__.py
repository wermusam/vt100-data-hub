"""psim — a Parker–Sochacki physics-simulation research lab.

A small, production-style research package for comparing ODE integration
methods on physics problems of increasing complexity:

* canonical scalar/linear ODEs (decay, harmonic oscillator, stiff systems),
* nonlinear conservative systems (pendulum, Kepler two-body),
* multi-body assemblies (mass–spring chains),
* event-driven dynamics (bouncing ball with collision detection),
* particle media (soft-sphere granular "sand", a minimal SPH fluid).

The centerpiece is the Parker–Sochacki method (PSM) — the power-series /
modified-Picard integrator developed by G. Edgar Parker and James Sochacki
at James Madison University — benchmarked against classical explicit
(Euler, RK2, RK4, RKF45), implicit one-step (backward Euler, implicit
midpoint, trapezoidal), implicit multistep (BDF2), structural-dynamics
(generalized-α), and symplectic (semi-implicit Euler, velocity Verlet)
integrators.

Subpackages
-----------
``psim.core``
    Shared types, dataclasses, and decorators (timing, registries,
    work counting, memoization).
``psim.systems``
    Physical systems expressed as first-order ODEs, optionally with a
    polynomial lifting for Parker–Sochacki integration.
``psim.integrators``
    Fixed-step, adaptive, implicit, symplectic, and Parker–Sochacki
    integrators behind one interface.
``psim.experiments``
    Metrics and reproducible benchmark suites (convergence,
    work–precision, energy drift, stiffness sweeps, collision timing).
``psim.viz``
    A Plotly Dash application for interactive exploration of results.
``psim.export``
    Frame exporters for downstream DCC tools (Houdini, Unreal).
"""

from __future__ import annotations

from psim.core.types import StepResult, Trajectory

__all__ = ["StepResult", "Trajectory", "__version__"]

__version__ = "0.1.0"
