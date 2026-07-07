"""Physical systems, from canonical ODEs up to particle media.

Importing this package populates the :data:`SYSTEMS` registry, so
``from psim.systems import SYSTEMS`` is all a benchmark or UI needs to
enumerate every available model.
"""

from __future__ import annotations

from psim.systems.base import (
    SYSTEMS,
    EventFunction,
    ODESystem,
    PolynomialODE,
    SeparableSystem,
    cauchy,
    register_system,
    series_product,
)
from psim.systems.canonical import DampedOscillator, ExponentialDecay, StiffSpringDamper
from psim.systems.kepler import Kepler
from psim.systems.mass_spring import MassSpringChain
from psim.systems.particles import BouncingBall, GranularBox2D
from psim.systems.pendulum import Pendulum
from psim.systems.rigid_body import FreeRigidBody
from psim.systems.sph import SPHFluid2D

__all__ = [
    "SYSTEMS",
    "BouncingBall",
    "DampedOscillator",
    "EventFunction",
    "ExponentialDecay",
    "FreeRigidBody",
    "GranularBox2D",
    "Kepler",
    "MassSpringChain",
    "ODESystem",
    "Pendulum",
    "PolynomialODE",
    "SPHFluid2D",
    "SeparableSystem",
    "StiffSpringDamper",
    "cauchy",
    "register_system",
    "series_product",
]
