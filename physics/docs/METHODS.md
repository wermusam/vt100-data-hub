# Methods: the equations, the integrators, and how to re-implement everything

This is the mathematical companion to the `psim` package. Every equation the
code implements is written out here, in the order you would re-implement it:
systems first, then each integrator's update rule, then the Parker-Sochacki
machinery, then collision handling, then the experiment protocols. File
references point at the implementation of each formula.

Notation: the state is $y \in \mathbb{R}^n$, the ODE is $y' = f(t, y)$,
the step size is $h$, and $y_n \approx y(t_n)$. Mechanical systems split
$y = (q, v)$ with $q' = v$ and $v' = a(t, q, v)$.

---

## 1. The systems

### 1.1 Exponential decay (`systems/canonical.py`)

$$y' = -\lambda y, \qquad y(t) = y_0 e^{-\lambda t}$$

The linear stability test. Applying any one-step method to this equation
gives $y_{n+1} = R(z)\,y_n$ with $z = -\lambda h$; the method is stable when
$|R(z)| \le 1$. Every stability claim in the study is a statement about $R$.

### 1.2 Damped harmonic oscillator

$$m\ddot{x} + c\dot{x} + kx = 0
\quad\Longleftrightarrow\quad
\begin{pmatrix} x \\ v \end{pmatrix}' =
\underbrace{\begin{pmatrix} 0 & 1 \\ -k/m & -c/m \end{pmatrix}}_{A}
\begin{pmatrix} x \\ v \end{pmatrix}$$

Energy $E = \tfrac12 m v^2 + \tfrac12 k x^2$. Exact solution
$y(t) = e^{At} y_0$, computed by eigendecomposition. The knobs $k$
(stiffness) and $c$ (damping) move the eigenvalues
$\lambda_\pm = \frac{-c \pm \sqrt{c^2 - 4km}}{2m}$; explicit methods
require $|\lambda_\pm| h$ inside their stability region, which is what the
stiffness map and damping sweep measure. The stiff spring uses $k = 10^4$,
$c = 10^2$ (fast eigenvalue $\approx -100$, explicit limit $h \lesssim 0.02$).

### 1.3 Nonlinear pendulum (`systems/pendulum.py`)

$$\ddot\theta = -\frac{g}{L}\sin\theta - \gamma\dot\theta, \qquad
E = \tfrac12 (L\dot\theta)^2 + gL(1 - \cos\theta)$$

Not polynomial because of $\sin\theta$. The Parker-Sochacki lifting adjoins
$s = \sin\theta$, $c = \cos\theta$ as state variables:

$$\theta' = \omega, \quad
\omega' = -\tfrac{g}{L} s - \gamma\omega, \quad
s' = \omega c, \quad
c' = -\omega s$$

Now every right-hand side is a polynomial in the (lifted) state. At each
step start $s, c$ are recomputed exactly from $\theta$, so the constraint
$s^2 + c^2 = 1$ cannot drift across steps.

### 1.4 Kepler two-body (`systems/kepler.py`)

$$\ddot{\mathbf r} = -\mu\,\mathbf r / r^3, \qquad
E = \tfrac12|\mathbf v|^2 - \mu/r, \qquad
L_z = x v_y - y v_x$$

Lifting for the $r^{-3}$: adjoin $u = r^{-3}$ and $w = r^{-2}$. With
$s = \mathbf r \cdot \mathbf v$:

$$u' = -3 s\, u\, w, \qquad w' = -2 s\, w^2$$

(derive by differentiating $u = (r^2)^{-3/2}$ and $w = (r^2)^{-1}$ and using
$(r^2)' = 2s$). The lifted system on $(x, y, v_x, v_y, u, w)$ is polynomial.
The exact solution used for error measurement comes from the Lagrange f-g
functions: solve Kepler's equation $M = E - e\sin E$ by Newton for the
eccentric anomaly, then

$$\mathbf r(t) = f\,\mathbf r_0 + g\,\mathbf v_0, \qquad
\mathbf v(t) = \dot f\,\mathbf r_0 + \dot g\,\mathbf v_0$$

with $f = 1 - \frac{a}{r_0}(1 - \cos\Delta E)$,
$g = t + (\sin\Delta E - \Delta E)/n$,
$\dot f = -\frac{\sqrt{\mu a}}{r r_0}\sin\Delta E$,
$\dot g = 1 - \frac{a}{r}(1 - \cos\Delta E)$.

### 1.5 Mass-spring chain (`systems/mass_spring.py`)

$n$ masses between fixed walls, displacement coordinates:

$$M\ddot q = -Kq - C\dot q, \qquad
K = k\,\mathrm{tridiag}(-1, 2, -1)$$

The discrete Laplacian; highest mode frequency $\approx 2\sqrt{k/m}$ caps
the explicit step. Linear, so exact solution and PSM come free.

### 1.6 Bouncing ball (`systems/particles.py`)

Free flight $\dot h = v$, $\dot v = -g$ punctuated by the impact map. Guard
$g(t, y) = h$; when $h$ crosses zero downward at $t^*$:

$$v^+ = -e\,v^-, \qquad e \in [0, 1]$$

Closed-form first impact from $(h_0, v_0)$:
$t^* = \left(v_0 + \sqrt{v_0^2 + 2gh_0}\right)/g$. Kinetic energy scales by
$e^2$ per impact; bounce times form a geometric series (Zeno point), guarded
by an event cap.

### 1.7 Granular box, soft-sphere DEM (`systems/particles.py`)

For each overlapping pair, overlap $\delta = 2R - \|\mathbf x_i - \mathbf x_j\|$,
normal $\mathbf n$, relative velocity split $v_n, \mathbf v_t$:

$$\mathbf F = \left(k_n \delta - \gamma_n v_n\right)\mathbf n - \gamma_t \mathbf v_t$$

plus gravity and identical penalty walls. Piecewise (switches at contact),
therefore not PSM-liftable; this system marks the method's boundary.

### 1.8 SPH fluid (`systems/sph.py`)

Weakly compressible 2-D SPH (Muller 2003): density
$\rho_i = m\sum_j W_{\text{poly6}}(r_{ij})$, pressure
$p_i = k(\rho_i - \rho_0)$, symmetric pressure force with the spiky kernel
gradient, viscosity via the Laplacian kernel, gravity, penalty walls.
Compact kernel support makes the RHS only piecewise smooth: also not
PSM territory, also deliberate.

### 1.9 Free rigid body (`systems/rigid_body.py`)

Body-frame Euler equations (principal inertia $I_1, I_2, I_3$) and
quaternion attitude kinematics:

$$\dot\omega_1 = \frac{I_2 - I_3}{I_1}\,\omega_2\omega_3, \quad
\dot\omega_2 = \frac{I_3 - I_1}{I_2}\,\omega_3\omega_1, \quad
\dot\omega_3 = \frac{I_1 - I_2}{I_3}\,\omega_1\omega_2$$

$$\dot q = \tfrac12\, q \otimes (0, \boldsymbol\omega)$$

Quadratic and bilinear respectively: **already polynomial, the PSM lifting
is the identity** (plus exact renormalization of $q$ at each step start).
Torque-free invariants: $T = \tfrac12\sum_i I_i\omega_i^2$ and
$|\mathbf L| = \|(I_1\omega_1, I_2\omega_2, I_3\omega_3)\|$. Default initial
data spins near the intermediate axis, producing Dzhanibekov flips. The
rotation matrix $R(q)$ is quadratic in $q$, so a corner's world position
$\mathbf x + R(q)\mathbf v$ is polynomial along a PSM step: the object
rigid-body CCD needs.

---

## 2. The integrators

Work accounting: one evaluation of $f$ is the unit; implicit methods also
spend evaluations inside Newton; PSM counts one unit per coefficient
recurrence (see 3.5).

### 2.1 Explicit Runge-Kutta (`integrators/explicit.py`)

Forward Euler (order 1): $y_{n+1} = y_n + h f(t_n, y_n)$.

Explicit midpoint (order 2):
$k_1 = f(t_n, y_n)$, $k_2 = f(t_n + \tfrac h2, y_n + \tfrac h2 k_1)$,
$y_{n+1} = y_n + h k_2$.

Classical RK4 (order 4):

$$k_1 = f(t_n, y_n), \quad
k_2 = f(t_n + \tfrac h2, y_n + \tfrac h2 k_1), \quad
k_3 = f(t_n + \tfrac h2, y_n + \tfrac h2 k_2), \quad
k_4 = f(t_n + h, y_n + h k_3)$$
$$y_{n+1} = y_n + \tfrac h6 (k_1 + 2k_2 + 2k_3 + k_4)$$

RKF45 (Fehlberg embedded 4(5)): six stages produce both a 5th and a 4th
order solution; the difference estimates the local error
$\varepsilon = \|y^{(5)} - y^{(4)}\|_\infty$ and the controller rescales

$$h \leftarrow h \cdot \mathrm{clip}\!\left(0.9\,(\mathrm{tol}/\varepsilon)^{1/5},\ 0.2,\ 5\right)$$

accepting the step when $\varepsilon \le \mathrm{tol}$.

### 2.2 Implicit one-step (`integrators/implicit.py`)

Each step solves a nonlinear residual $F(y_{n+1}) = 0$ with Newton's method:
iterate $y \leftarrow y - J_F^{-1} F(y)$ using the exact RHS Jacobian when
the system provides one, else forward differences.

Backward Euler (order 1, L-stable):
$F(Y) = Y - y_n - h f(t_{n+1}, Y)$, $J_F = I - h\,\partial f$.
$R(z) = 1/(1 - z)$, so $R(\infty) = 0$: fast transients are crushed.

Implicit midpoint (order 2, A-stable, symplectic):
$F(Y) = Y - y_n - h f\!\left(t_n + \tfrac h2, \tfrac{y_n + Y}{2}\right)$,
$J_F = I - \tfrac h2\,\partial f$. Conserves quadratic invariants exactly.

Trapezoidal (order 2, A-stable, no damping at infinity):
$F(Y) = Y - y_n - \tfrac h2\left[f(t_n, y_n) + f(t_{n+1}, Y)\right]$.
$R(z) = \frac{1 + z/2}{1 - z/2} \to -1$ as $z \to -\infty$: unresolved
stiff modes ring with amplitude near 1 forever.

### 2.3 BDF2, implicit multistep (`integrators/multistep.py`)

Constant step: $y_{n+1} = \tfrac{4y_n - y_{n-1}}{3} + \tfrac{2h}{3} f(t_{n+1}, y_{n+1})$.

Variable step with ratio $r = h_n / h_{n-1}$:

$$y_{n+1} = \frac{(1+r)^2 y_n - r^2 y_{n-1}}{1 + 2r}
+ h_n\,\frac{1+r}{1+2r}\, f(t_{n+1}, y_{n+1})$$

A-stable and stiffly damped (order 2, the fixed-order core of production
stiff solvers). Being multistep it carries history $(t_{n-1}, y_{n-1})$;
the implementation validates on every call that the incoming $(t, y)$ is
exactly the point it last produced, and restarts from one backward-Euler
step otherwise. This matters in an event-driven driver: a collision
response teleports the state and invalidates history. Startup with one
backward-Euler step costs a single $O(h^2)$ local error, which does not
reduce the global order 2.

### 2.4 Generalized-alpha (`integrators/structural.py`)

For mechanical systems $\ddot q = a(t, q, \dot q)$. Chung-Hulbert
parameters from the spectral radius at infinity $\rho_\infty \in [0, 1]$:

$$\alpha_m = \frac{2\rho_\infty - 1}{\rho_\infty + 1}, \quad
\alpha_f = \frac{\rho_\infty}{\rho_\infty + 1}, \quad
\gamma = \tfrac12 - \alpha_m + \alpha_f, \quad
\beta = \tfrac14(1 - \alpha_m + \alpha_f)^2$$

Newmark update in terms of the new algorithmic acceleration $a_{n+1}$:

$$q_{n+1} = q_n + h v_n + h^2\left[(\tfrac12 - \beta)a_n + \beta a_{n+1}\right],
\qquad
v_{n+1} = v_n + h\left[(1 - \gamma)a_n + \gamma a_{n+1}\right]$$

and the balance residual, evaluated at alpha-shifted points
$x_{n+1-\alpha} = (1-\alpha)x_{n+1} + \alpha x_n$:

$$R(a_{n+1}) = (1 - \alpha_m)a_{n+1} + \alpha_m a_n
- a\big(t_{n+1-\alpha_f},\ q_{n+1-\alpha_f},\ v_{n+1-\alpha_f}\big) = 0$$

solved by Newton with a forward-difference Jacobian in acceleration space.
Second order, unconditionally stable on linear problems, and the only
method in the suite with *frequency-selective* dissipation:
$\rho_\infty = 1$ reproduces trapezoidal behavior (no damping),
$\rho_\infty = 0$ annihilates unresolvable high frequencies in one step
while the resolved band keeps its accuracy.

### 2.5 Symplectic pair (`integrators/symplectic.py`)

Semi-implicit (symplectic) Euler, order 1:
$v_{n+1} = v_n + h\,a(t_n, q_n, v_n)$, then $q_{n+1} = q_n + h v_{n+1}$.

Velocity Verlet (order 2), kick-drift-kick:

$$v_{1/2} = v_n + \tfrac h2 a(t_n, q_n, v_n), \quad
q_{n+1} = q_n + h v_{1/2}, \quad
v_{n+1} = v_{1/2} + \tfrac h2 a(t_{n+1}, q_{n+1}, v_{n+1})$$

The closing kick is implicit when $a$ depends on $v$ (damping); one
fixed-point pass ($v_{n+1} \approx v_{1/2} + \tfrac h2 a(\ldots, v_{\text{guess}})$
with $v_{\text{guess}}$ from a first pass) keeps it explicit at full second
order. These methods preserve the symplectic form of Hamiltonian flow:
energy error stays bounded forever instead of drifting, which is why every
game engine ships them.

---

## 3. The Parker-Sochacki method (`integrators/parker_sochacki.py`)

### 3.1 The idea

If $y' = P(y)$ with polynomial $P$, write the local solution about $t_n$ as
a Maclaurin series in $\tau = t - t_n$:

$$y(t_n + \tau) = \sum_{k \ge 0} C_k\,\tau^k, \qquad C_0 = y_n.$$

Substituting the series into the ODE and matching powers of $\tau$ gives the
recurrence

$$C_{k+1} = \frac{[P(y)]_k}{k + 1}$$

where $[P(y)]_k$ is the $k$-th series coefficient of $P$ applied to the
series, computable from $C_0 \dots C_k$ using only Cauchy products:

$$[ab]_k = \sum_{j=0}^{k} a_j\, b_{k-j}.$$

This is Picard iteration made computable: the $k$-th iterate contributes
exactly the $k$-th coefficient. One step of order $K$ computes
$C_0 \dots C_K$ and evaluates the polynomial at $\tau = h$ (Horner).

### 3.2 Worked recurrence: the pendulum

Lifted state $(\theta, \omega, s, c)$, series
$(\Theta_k, \Omega_k, S_k, C_k)$:

$$\Theta_{k+1} = \frac{\Omega_k}{k+1}, \qquad
\Omega_{k+1} = \frac{-\frac{g}{L} S_k - \gamma\,\Omega_k}{k+1},$$
$$S_{k+1} = \frac{1}{k+1}\sum_{j=0}^{k} \Omega_j\, C_{k-j}, \qquad
C_{k+1} = \frac{-1}{k+1}\sum_{j=0}^{k} \Omega_j\, S_{k-j}.$$

Every system in the package reduces to a table like this; the rigid body's
is seven such lines (quaternion product terms and three gyroscopic
products), Kepler's needs intermediate series for $s$, $uw$, $w^2$.

### 3.3 Step-size control

The tail coefficients estimate the series' radius of convergence. Requiring
the truncated tail to satisfy $|C_K|\,h^K \le \mathrm{tol}$ gives

$$h = \min_{k \in \{K-1,\,K\}} \left(\frac{\mathrm{tol}}{\|C_k\|_\infty}\right)^{1/k}$$

evaluated on the last two coefficients (guarding against an accidentally
small final one). No embedded second method, no extra evaluations: the
error control is free. Adaptive *order* (stop the recurrence once the tail
passes tolerance) is the standard refinement; Jorba & Zou (2005) show the
optimal order grows like $\log(1/\mathrm{tol})$.

### 3.4 Dense output and stability

The step *is* the polynomial: evaluating $y(t_n + \tau)$ anywhere inside
the step is a Horner evaluation, exact to truncation order. This is the
property everything in section 4 builds on. Stability: the order-$K$ PSM
step applied to $y' = \lambda y$ gives the degree-$K$ Taylor polynomial of
$e^{\lambda h}$ as its amplification factor; measured in this repo, the
negative-real-axis stability boundary grows linearly with order
($|\lambda| h_{\max} \approx 2.0, 4.3, 11.8$ at $K = 2, 8, 28$), while cost
per step grows quadratically in $K$. PSM buys stiffness linearly and pays
quadratically; implicit methods get it unconditionally.

### 3.5 Measuring work fairly

For classical methods, work = evaluations of $f$. For PSM, the meter counts
coefficient recurrences (one per order per step), the closest per-unit
analogue; a recurrence at high order costs more than one $f$ call (its
Cauchy products are $O(K)$ each), so wall-clock time is recorded on every
trajectory as the tie-breaker. On these benchmarks both rankings agree.

---

## 4. Collision handling

### 4.1 Event-driven impacts

An event is a sign change of a guard $g(t, y)$. Per output step from
$(t, y)$ spanning $h$:

1. **Detect**: $g(t, y) > 0 \ge g(t + h, y_{\text{end}})$.
2. **Locate** $\tau^* \in [0, h]$ with $g(y(\tau^*)) = 0$:
   with PSM dense output, bisect (today) or root-isolate (planned, see 4.3)
   the guard on the step polynomial, cost: Horner evaluations only.
   Without dense output, each probe of the bisection re-integrates a
   partial step of size $\tau$ from the step start, cost: a full method
   step per probe, and the located time inherits the method's local error.
3. **Respond**: apply the impact map (restitution reflection) at
   $(t + \tau^*,\ y(\tau^*))$, then resume integration from the post-impact
   state. Multistep history and PSM series are invalidated by the jump;
   integrators detect this and restart (2.3).
4. **Zeno guard**: cap located events; beyond the cap crossings are left
   unhandled.

Measured on the bouncing ball: PSM impact-time error is flat at
$\sim 10^{-16}$ for every step size tested; forward Euler's grows to
$\sim 10^{-1}$ at coarse steps and can miss the impact inside the horizon
entirely.

### 4.2 Penalty contacts

The granular and SPH systems fold collision into the force law (1.7):
no events, but the contact stiffness makes the ODE stiff, moving the
problem into implicit/generalized-alpha territory. Event-driven and
penalty are the two poles; the interesting hybrid (PSM flight + implicit
contact) is future work.

### 4.3 From bisection to root isolation (planned)

When the guard is polynomial in the state (plane height, sphere-sphere
distance squared, corner-plane distance via $R(q)$), composing it with the
PSM step polynomial yields a univariate polynomial $G(\tau)$ of known
degree. Sturm sequences or Descartes'-rule bisection (Collins & Akritas)
then *isolate all real roots* in $[0, h]$ with certainty: the earliest root
is the impact, grazing double-crossings cannot be missed, and tunneling at
any step size is impossible. This replaces the endpoint sign check, whose
failure modes (miss a dip-and-return, miss a through-shot) are exactly the
CCD failure modes game engines patch heuristically. Prior art note: this
mechanism exists in astrodynamics (Biscani & Izzo, heyoka); the graphics
application with contact response is the open contribution
(see `novelty_review.md`).

---

## 5. Experiment protocols (`experiments/benchmarks.py`)

* **Convergence**: fixed-step methods on $h \in$ geometric grid; report
  $\|y_N - y_{\text{exact}}(T)\|_\infty$ and the log-log slope (observed
  order), excluding points at the roundoff floor.
* **Work-precision**: error vs work units; adaptive methods sweep tol
  instead of $h$. Down-and-left dominates.
* **Energy drift**: $|E(t) - E_0|/E_0$ time series over long horizons;
  distinguishes bounded (symplectic), secular (non-symplectic explicit),
  exact-quadratic (implicit midpoint), and roundoff-floor (high-order PSM)
  behavior.
* **Stiffness map**: stability boolean on a (stiffness x step) grid per
  method; boundary $h \propto 1/\sqrt{k}$ for all explicit methods.
* **Damping sweep**: accuracy at fixed $h$ as $c$ grows through overdamped.
* **Collision timing**: first-impact error and total work vs step size on
  the bouncing ball, against the closed-form impact time.
* **PSM order sweep**: error vs $K$ at fixed $h$ (geometric until
  roundoff); the knob no Runge-Kutta method has.

All studies return tidy DataFrames and render in the Dash app
(`python -m psim.viz.dash_app`).

---

## 6. Re-implementation checklist

1. Cauchy product helper; verify against `numpy.convolve` (test exists).
2. One linear system + exact solution via eigendecomposition; get Euler,
   RK4 converging at orders 1 and 4.
3. Newton loop; backward Euler stable on the stiff spring at $h = 0.05$.
4. PSM on the linear system (recurrence $C_{k+1} = A C_k/(k{+}1)$): machine
   precision at $h = 0.5$, order 20.
5. Pendulum lifting (3.2); then Kepler's (1.4), the hard one.
6. Event driver (4.1) on the bouncing ball against the closed-form
   $t^*$.
7. BDF2 with history restart; generalized-alpha with the $\rho_\infty$
   dissipation test (unresolved mode annihilated, resolved mode conserved).
8. Rigid body (1.9): Dzhanibekov flips with energy and $|\mathbf L|$ at
   $10^{-12}$.

Each item has a corresponding test in `tests/`; re-implementations can be
validated against the same assertions.
