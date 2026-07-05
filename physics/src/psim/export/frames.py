"""Frame exporters for downstream DCC visualization (Houdini, Unreal).

The interchange philosophy: keep the solver honest and the pipe dumb.
Python owns the numerics; the DCC owns shading, lighting, and camera.
Two formats cover both targets:

* **Per-frame CSV point clouds** (``frame_0001.csv`` …) with a
  ``manifest.json``. Houdini ingests these with a File/Table Import SOP
  (or three lines in a Python SOP); Unreal's Niagara has a first-class
  CSV importer for point-cache-style emission. CSV survives every
  version boundary and is human-debuggable — worth more in research
  iteration than binary speed.
* **A single compressed ``.npz``** (``times``, ``positions``,
  ``velocities``) for round-tripping back into Python/NumPy without
  re-simulation — Houdini's bundled Python can read it directly inside
  a Python SOP too.

Positions are exported as 3-D (the 2-D systems get ``z = 0``) because
both target applications think in 3-D.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from psim.core.types import FloatArray, Trajectory


@runtime_checkable
class ParticleSystem(Protocol):
    """Anything that can slice a flat state into per-particle kinematics."""

    n: int

    def positions(self, y: FloatArray) -> FloatArray:
        """Positions of shape ``(n, 2)`` or ``(n, 3)``."""
        ...

    def velocities(self, y: FloatArray) -> FloatArray:
        """Velocities matching :meth:`positions`."""
        ...


def _as_3d(array: FloatArray) -> FloatArray:
    """Pad ``(n, 2)`` planar data to ``(n, 3)`` with ``z = 0``."""
    if array.shape[1] == 3:
        return array
    return np.column_stack([array, np.zeros(len(array))])


def export_particle_frames(
    trajectory: Trajectory,
    system: ParticleSystem,
    out_dir: str | Path,
    stride: int = 1,
    fps: float | None = None,
) -> Path:
    """Write a per-frame CSV sequence plus manifest for DCC import.

    Parameters
    ----------
    trajectory:
        Output of :func:`psim.integrators.simulate` on a particle system.
    system:
        The system that produced it (provides the state slicing).
    out_dir:
        Destination directory; created if needed.
    stride:
        Keep every ``stride``-th sample (thin dense simulations before
        shipping them to the renderer).
    fps:
        Playback rate recorded in the manifest; defaults to the
        reciprocal of the (strided) sample interval.

    Returns
    -------
    Path
        The directory containing ``frame_*.csv`` and ``manifest.json``.
    """
    if not isinstance(system, ParticleSystem):
        raise TypeError(f"{type(system).__name__} does not expose per-particle state")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    times = trajectory.times[::stride]
    states = trajectory.states[::stride]
    header = "id,px,py,pz,vx,vy,vz"
    for i, y in enumerate(states):
        pos = _as_3d(system.positions(y))
        vel = _as_3d(system.velocities(y))
        table = np.column_stack([np.arange(len(pos)), pos, vel])
        np.savetxt(
            out / f"frame_{i:04d}.csv",
            table,
            delimiter=",",
            header=header,
            comments="",
            fmt=["%d"] + ["%.9g"] * 6,
        )

    if fps is None and len(times) > 1:
        fps = 1.0 / float(times[1] - times[0])
    manifest = {
        "system": trajectory.system,
        "method": trajectory.method,
        "n_particles": int(system.n),
        "n_frames": len(states),
        "fps": fps,
        "time_start": float(times[0]),
        "time_end": float(times[-1]),
        "columns": header.split(","),
        "frame_pattern": "frame_%04d.csv",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return out


def export_npz(trajectory: Trajectory, system: ParticleSystem, path: str | Path) -> Path:
    """Save the whole particle trajectory as one compressed ``.npz``.

    Arrays: ``times (T,)``, ``positions (T, n, 3)``, ``velocities
    (T, n, 3)``.
    """
    if not isinstance(system, ParticleSystem):
        raise TypeError(f"{type(system).__name__} does not expose per-particle state")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    positions = np.stack([_as_3d(system.positions(y)) for y in trajectory.states])
    velocities = np.stack([_as_3d(system.velocities(y)) for y in trajectory.states])
    np.savez_compressed(
        path, times=trajectory.times, positions=positions, velocities=velocities
    )
    return path
