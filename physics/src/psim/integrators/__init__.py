"""Integrators, from forward Euler to Parker–Sochacki.

Importing this package populates the :data:`INTEGRATORS` registry, so
``from psim.integrators import INTEGRATORS`` enumerates every method.
"""

from __future__ import annotations

from psim.integrators.base import INTEGRATORS, Integrator, register_integrator, simulate
from psim.integrators.explicit import RKF45, ExplicitEuler, ExplicitMidpoint, RungeKutta4
from psim.integrators.implicit import BackwardEuler, ImplicitMidpoint, Trapezoidal
from psim.integrators.parker_sochacki import ParkerSochacki
from psim.integrators.symplectic import SymplecticEuler, VelocityVerlet

__all__ = [
    "INTEGRATORS",
    "RKF45",
    "BackwardEuler",
    "ExplicitEuler",
    "ExplicitMidpoint",
    "ImplicitMidpoint",
    "Integrator",
    "ParkerSochacki",
    "RungeKutta4",
    "SymplecticEuler",
    "Trapezoidal",
    "VelocityVerlet",
    "register_integrator",
    "simulate",
]
