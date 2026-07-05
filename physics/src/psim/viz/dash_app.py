"""Interactive Dash application for the integrator study.

Run with::

    python -m psim.viz.dash_app          # http://127.0.0.1:8050

Tabs map one-to-one onto the research questions: convergence,
work–precision, long-run energy conservation, stiffness/damping
parameter sweeps, collision timing, the PSM order knob, and a free-form
trajectory playground (which can also animate the granular and SPH
systems). All benchmark data is memoized, so each tab costs its compute
once per parameter combination.
"""

from __future__ import annotations

import numpy as np
from dash import Dash, Input, Output, dcc, html

from psim.experiments import benchmarks, metrics
from psim.integrators import simulate
from psim.systems import SYSTEMS
from psim.viz import theme

app = Dash(__name__, title="Parker-Sochacki ODE Lab")

_CONTROL = {"display": "inline-block", "marginRight": "24px", "verticalAlign": "top"}
_LABEL = {"fontSize": "12px", "color": theme.MUTED, "display": "block", "marginBottom": "4px"}

#: Playground methods (label → integrator factory taking dt; dt unused for fixed).
_PLAYGROUND_METHODS = {
    spec.label: spec for spec in benchmarks.fixed_step_methods() + benchmarks.adaptive_methods()
}


def _dropdown(id_: str, options: list[str], value: str, label: str) -> html.Div:
    return html.Div(
        [html.Label(label, style=_LABEL), dcc.Dropdown(id=id_, options=options, value=value, clearable=False, style={"width": "260px"})],
        style=_CONTROL,
    )


app.layout = html.Div(
    style={
        "backgroundColor": theme.PAGE,
        "fontFamily": 'system-ui, -apple-system, "Segoe UI", sans-serif',
        "padding": "16px 24px",
        "minHeight": "100vh",
    },
    children=[
        html.H2("Parker–Sochacki ODE Lab", style={"color": theme.INK, "marginBottom": "2px"}),
        html.P(
            "Comparing the Parker–Sochacki power-series method with explicit, "
            "implicit, and symplectic integrators on physics problems from decay to particle media.",
            style={"color": theme.INK_SECONDARY, "marginTop": "0"},
        ),
        dcc.Tabs(
            colors={"border": theme.GRID, "primary": theme.FAMILY_COLORS["series"], "background": theme.SURFACE},
            children=[
                dcc.Tab(
                    label="Convergence",
                    children=[
                        html.Div(
                            [_dropdown("conv-system", list(benchmarks.BENCHMARK_SYSTEMS), "kepler", "System")],
                            style={"padding": "16px 0"},
                        ),
                        dcc.Loading(dcc.Graph(id="conv-graph", style={"height": "560px"})),
                    ],
                ),
                dcc.Tab(
                    label="Work vs precision",
                    children=[
                        html.Div(
                            [_dropdown("wp-system", list(benchmarks.BENCHMARK_SYSTEMS), "kepler", "System")],
                            style={"padding": "16px 0"},
                        ),
                        dcc.Loading(dcc.Graph(id="wp-graph", style={"height": "560px"})),
                    ],
                ),
                dcc.Tab(
                    label="Energy drift",
                    children=[
                        html.Div(
                            [
                                _dropdown(
                                    "energy-system",
                                    ["pendulum", "kepler", "oscillator", "mass-spring-chain"],
                                    "pendulum",
                                    "Conservative system",
                                )
                            ],
                            style={"padding": "16px 0"},
                        ),
                        dcc.Loading(dcc.Graph(id="energy-graph", style={"height": "560px"})),
                    ],
                ),
                dcc.Tab(
                    label="Stiffness map",
                    children=[
                        html.Div(
                            [
                                _dropdown(
                                    "stiff-method",
                                    [s.label for s in benchmarks.fixed_step_methods()],
                                    "RK4",
                                    "Method",
                                )
                            ],
                            style={"padding": "16px 0"},
                        ),
                        dcc.Loading(dcc.Graph(id="stiff-graph", style={"height": "540px"})),
                        dcc.Loading(dcc.Graph(id="damping-graph", style={"height": "480px"})),
                    ],
                ),
                dcc.Tab(
                    label="Collision timing",
                    children=[
                        dcc.Loading(dcc.Graph(id="coll-error-graph", style={"height": "480px"})),
                        dcc.Loading(dcc.Graph(id="coll-work-graph", style={"height": "480px"})),
                    ],
                ),
                dcc.Tab(
                    label="PSM order",
                    children=[
                        html.Div(
                            [_dropdown("psm-system", ["kepler", "pendulum", "oscillator"], "kepler", "System")],
                            style={"padding": "16px 0"},
                        ),
                        dcc.Loading(dcc.Graph(id="psm-order-graph", style={"height": "480px"})),
                        dcc.Loading(dcc.Graph(id="psm-work-graph", style={"height": "420px"})),
                    ],
                ),
                dcc.Tab(
                    label="Playground",
                    children=[
                        html.Div(
                            [
                                _dropdown("play-system", list(SYSTEMS), "pendulum", "System"),
                                _dropdown("play-method", list(_PLAYGROUND_METHODS), "Velocity Verlet", "Method"),
                                html.Div(
                                    [
                                        html.Label("Step / output interval dt", style=_LABEL),
                                        dcc.Slider(
                                            id="play-dt",
                                            min=-3,
                                            max=-1,
                                            step=0.25,
                                            value=-2,
                                            marks={-3: "0.001", -2: "0.01", -1: "0.1"},
                                        ),
                                    ],
                                    style={**_CONTROL, "width": "300px"},
                                ),
                            ],
                            style={"padding": "16px 0"},
                        ),
                        dcc.Loading(dcc.Graph(id="play-graph", style={"height": "560px"})),
                        dcc.Loading(dcc.Graph(id="play-energy-graph", style={"height": "380px"})),
                    ],
                ),
            ],
        ),
    ],
)


@app.callback(Output("conv-graph", "figure"), Input("conv-system", "value"))
def convergence_figure(system_name: str):  # noqa: ANN201
    frame = benchmarks.convergence_study(system_name)
    fig = theme.base_figure(
        f"Global error vs step size — {system_name}",
        "step size dt",
        "final error (∞-norm)",
        xaxis_type="log",
        yaxis_type="log",
    )
    for method, group in frame.groupby("method", sort=False):
        good = group.dropna(subset=["final_error"])
        order = good["observed_order"].iloc[0] if len(good) else float("nan")
        fig.add_trace(
            theme.line_trace(
                good["value"],
                good["final_error"],
                f"{method} (slope {order:.1f})" if np.isfinite(order) else str(method),
                hovertemplate="dt=%{x:.4g}<br>error=%{y:.3g}<extra>%{fullData.name}</extra>",
                style_key=str(method),
            )
        )
    return fig


@app.callback(Output("wp-graph", "figure"), Input("wp-system", "value"))
def work_precision_figure(system_name: str):  # noqa: ANN201
    frame = benchmarks.work_precision_study(system_name)
    fig = theme.base_figure(
        f"Work vs precision — {system_name}  (down and left is better)",
        "right-hand-side evaluations (PSM: coefficient recurrences)",
        "final error (∞-norm)",
        xaxis_type="log",
        yaxis_type="log",
    )
    for method, group in frame.groupby("method", sort=False):
        good = group.dropna(subset=["final_error", "rhs_evals"]).sort_values("rhs_evals")
        good = good[good["final_error"] > 0]
        fig.add_trace(
            theme.line_trace(
                good["rhs_evals"],
                good["final_error"],
                str(method),
                hovertemplate="work=%{x}<br>error=%{y:.3g}<extra>%{fullData.name}</extra>",
            )
        )
    return fig


@app.callback(Output("energy-graph", "figure"), Input("energy-system", "value"))
def energy_figure(system_name: str):  # noqa: ANN201
    frame = benchmarks.energy_drift_study(system_name)
    fig = theme.base_figure(
        f"Relative energy drift |E(t)−E₀|/E₀ over 60 s at dt = 0.05 — {system_name}",
        "time",
        "|relative energy drift|",
        yaxis_type="log",
    )
    for method, group in frame.groupby("method", sort=False):
        fig.add_trace(
            theme.line_trace(
                group["t"],
                np.abs(group["drift"]).clip(1e-17),
                str(method),
                hovertemplate="t=%{x:.1f}<br>drift=%{y:.2g}<extra>%{fullData.name}</extra>",
            )
        )
        fig.data[-1].mode = "lines"
    return fig


@app.callback(
    Output("stiff-graph", "figure"),
    Output("damping-graph", "figure"),
    Input("stiff-method", "value"),
)
def stiffness_figures(method: str):  # noqa: ANN201
    frame = benchmarks.stiffness_stability_study()
    sub = frame[frame["method"] == method]
    pivot = sub.pivot_table(index="dt", columns="stiffness", values="stable", aggfunc="first")
    fig = theme.base_figure(
        f"Stability map — {method}: oscillator, 2 s horizon (blue = bounded)",
        "stiffness k",
        "step size dt",
        xaxis_type="log",
        yaxis_type="log",
    )
    import plotly.graph_objects as go

    fig.add_trace(
        go.Heatmap(
            x=pivot.columns,
            y=pivot.index,
            z=pivot.values.astype(float),
            colorscale=[[0.0, "#f0efec"], [1.0, theme.FAMILY_COLORS["explicit"]]],
            zmin=0,
            zmax=1,
            showscale=False,
            xgap=2,
            ygap=2,
            hovertemplate="k=%{x:.3g}<br>dt=%{y:.3g}<br>stable=%{z}<extra></extra>",
        )
    )

    damp = benchmarks.damping_sweep_study()
    fig2 = theme.base_figure(
        "Accuracy vs damping — oscillator (k = 4), dt = 0.05, all methods",
        "damping coefficient c",
        "final error (∞-norm)",
        xaxis_type="log",
        yaxis_type="log",
    )
    for m, group in damp.groupby("method", sort=False):
        good = group.dropna(subset=["final_error"])
        good = good[good["final_error"] > 0]
        fig2.add_trace(
            theme.line_trace(
                good["damping"],
                good["final_error"],
                str(m),
                hovertemplate="c=%{x:.3g}<br>error=%{y:.3g}<extra>%{fullData.name}</extra>",
            )
        )
    return fig, fig2


@app.callback(
    Output("coll-error-graph", "figure"),
    Output("coll-work-graph", "figure"),
    Input("coll-error-graph", "id"),
)
def collision_figures(_: str):  # noqa: ANN201
    frame = benchmarks.collision_study()
    fig = theme.base_figure(
        "Bouncing ball: first-impact time error vs step size",
        "step size dt",
        "|t_impact − exact|",
        xaxis_type="log",
        yaxis_type="log",
    )
    fig2 = theme.base_figure(
        "Bouncing ball: total work including event location",
        "step size dt",
        "RHS evaluations",
        xaxis_type="log",
        yaxis_type="log",
    )
    for method, group in frame.groupby("method", sort=False):
        good = group.dropna(subset=["impact_time_error"])
        good = good[good["impact_time_error"] > 0]
        fig.add_trace(theme.line_trace(good["dt"], good["impact_time_error"], str(method)))
        fig2.add_trace(theme.line_trace(group["dt"], group["rhs_evals"], str(method)))
    return fig, fig2


@app.callback(
    Output("psm-order-graph", "figure"),
    Output("psm-work-graph", "figure"),
    Input("psm-system", "value"),
)
def psm_order_figures(system_name: str):  # noqa: ANN201
    frame = benchmarks.psm_order_study(system_name)
    color = theme.FAMILY_COLORS["series"]
    fig = theme.base_figure(
        f"PSM error vs series order at fixed dt = 0.25 — {system_name}",
        "series order K",
        "final error (∞-norm)",
        yaxis_type="log",
        showlegend=False,
    )
    good = frame.dropna(subset=["final_error"])
    fig.add_trace(theme.line_trace(good["order"], good["final_error"].clip(1e-17), "PSM"))
    fig2 = theme.base_figure(
        "PSM work vs series order (same runs)",
        "series order K",
        "coefficient recurrences",
        showlegend=False,
    )
    fig2.add_trace(theme.line_trace(frame["order"], frame["rhs_evals"], "PSM"))
    _ = color
    return fig, fig2


@app.callback(
    Output("play-graph", "figure"),
    Output("play-energy-graph", "figure"),
    Input("play-system", "value"),
    Input("play-method", "value"),
    Input("play-dt", "value"),
)
def playground_figures(system_name: str, method_label: str, log_dt: float):  # noqa: ANN201
    system = SYSTEMS[system_name]()
    spec = _PLAYGROUND_METHODS[method_label]
    dt = 10.0**log_dt
    is_particles = hasattr(system, "positions")
    t_end = 2.0 if is_particles else 10.0
    if not benchmarks.applicable(spec, system):
        fig = theme.base_figure(
            f"{method_label} does not apply to {system_name} "
            "(needs separable/polynomial structure)",
            "",
            "",
        )
        return fig, fig
    integrator = spec.build(1e-8 if spec.control == "tol" else dt)
    trajectory = simulate(system, integrator, t_end=t_end, dt=max(dt, 0.02) if is_particles else dt)

    import plotly.graph_objects as go

    if is_particles:
        stride = max(1, len(trajectory.states) // 60)
        frames = [
            go.Frame(
                data=[
                    go.Scatter(
                        x=system.positions(y)[:, 0],
                        y=system.positions(y)[:, 1],
                        mode="markers",
                        marker={"size": 9, "color": theme.FAMILY_COLORS["explicit"]},
                    )
                ],
                name=f"{t:.2f}",
            )
            for t, y in zip(
                trajectory.times[::stride], trajectory.states[::stride], strict=True
            )
        ]
        fig = theme.base_figure(
            f"{system_name} — {method_label} (press play)", "x", "y", showlegend=False
        )
        fig.add_trace(frames[0].data[0])
        fig.frames = frames
        fig.update_layout(
            updatemenus=[
                {
                    "type": "buttons",
                    "buttons": [
                        {
                            "label": "Play",
                            "method": "animate",
                            "args": [None, {"frame": {"duration": 50}, "transition": {"duration": 0}}],
                        }
                    ],
                }
            ],
            xaxis_range=[0, getattr(system, "box", 1.0)],
            yaxis_range=[0, getattr(system, "box", 1.0)],
        )
        fig.update_yaxes(scaleanchor="x", scaleratio=1)
    else:
        fig = theme.base_figure(
            f"{system_name} — {method_label}: phase portrait", "component 0", "component 1"
        )
        fig.add_trace(
            theme.line_trace(trajectory.component(0), trajectory.component(1), method_label)
        )
        fig.data[-1].mode = "lines"

    drift = metrics.energy_drift(trajectory, system)
    fig2 = theme.base_figure("Energy over the run", "time", "E(t) − E₀ (relative)", showlegend=False)
    if drift is not None:
        fig2.add_trace(theme.line_trace(trajectory.times, drift, method_label))
        fig2.data[-1].mode = "lines"
    return fig, fig2


def main() -> None:
    """Entry point: serve the app on the default Dash port."""
    app.run(debug=False, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()
