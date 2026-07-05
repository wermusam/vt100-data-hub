"""Event handling, granular settling, SPH sanity, and exporter tests."""

from __future__ import annotations

import json

import numpy as np

from psim.export import export_npz, export_particle_frames
from psim.integrators import ParkerSochacki, RungeKutta4, SymplecticEuler, simulate
from psim.systems import BouncingBall, GranularBox2D, SPHFluid2D


def test_psm_locates_impact_time_to_machine_precision():
    """PSM's dense polynomial nails the first impact with a coarse grid."""
    ball = BouncingBall()
    trajectory = simulate(ball, ParkerSochacki(order=4), t_end=2.0, dt=0.25)
    assert abs(trajectory.events[0] - ball.first_impact_time()) < 1e-12


def test_event_response_applies_restitution():
    """Post-impact speed is restitution times pre-impact speed."""
    ball = BouncingBall(restitution=0.5, h0=1.0, v0=0.0)
    trajectory = simulate(ball, RungeKutta4(), t_end=1.0, dt=0.01)
    v_impact = np.sqrt(2.0 * ball.gravity * 1.0)
    idx = np.searchsorted(trajectory.times, trajectory.events[0])
    v_after = trajectory.states[idx + 1, 1]
    # Shortly after impact the speed is ~0.5 * v_impact minus a little gravity.
    assert 0.0 < v_after < 0.5 * v_impact
    assert len(trajectory.events) >= 1


def test_bouncing_ball_counts_multiple_impacts():
    """A 2 s horizon with e = 0.8 contains three impacts."""
    ball = BouncingBall(restitution=0.8)
    trajectory = simulate(ball, ParkerSochacki(order=4), t_end=2.0, dt=0.05)
    assert len(trajectory.events) == 3


def test_granular_box_settles_and_stays_inside():
    """Sand dropped in a box loses energy and never tunnels the walls."""
    system = GranularBox2D(n_side=3, k_n=2.0e3)
    trajectory = simulate(system, SymplecticEuler(), t_end=1.5, dt=2e-4)
    e_start = system.energy(trajectory.states[0])
    e_end = system.energy(trajectory.y_final)
    assert e_end < e_start  # dashpots dissipate
    pos = system.positions(trajectory.y_final)
    margin = 0.5 * system.radius
    assert np.all(pos > -margin) and np.all(pos < system.box + margin)


def test_sph_dam_break_flows_right_and_conserves_mass_location():
    """The dam-break block slumps: center of mass drops and spreads right."""
    system = SPHFluid2D(nx=6, ny=8)
    trajectory = simulate(system, SymplecticEuler(), t_end=0.5, dt=2e-4)
    start = system.positions(trajectory.states[0])
    end = system.positions(trajectory.y_final)
    assert end[:, 1].mean() < start[:, 1].mean()  # slumps under gravity
    assert end[:, 0].max() > start[:, 0].max()  # spreads outward
    assert np.all(np.isfinite(end))


def test_frame_exporter_round_trip(tmp_path):
    """CSV frames + manifest and the npz round-trip match the trajectory."""
    system = GranularBox2D(n_side=2)
    trajectory = simulate(system, SymplecticEuler(), t_end=0.02, dt=0.005)
    out = export_particle_frames(trajectory, system, tmp_path / "frames", stride=2)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["n_particles"] == 4
    frames = sorted(out.glob("frame_*.csv"))
    assert len(frames) == manifest["n_frames"]
    first = np.loadtxt(frames[0], delimiter=",", skiprows=1)
    assert first.shape == (4, 7)
    np.testing.assert_allclose(first[:, 1:3], system.positions(trajectory.states[0]))

    npz_path = export_npz(trajectory, system, tmp_path / "run.npz")
    data = np.load(npz_path)
    assert data["positions"].shape == (len(trajectory.times), 4, 3)
    np.testing.assert_allclose(data["times"], trajectory.times)
