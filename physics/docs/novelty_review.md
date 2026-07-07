# Novelty review: Parker-Sochacki motion polynomials for continuous collision detection

Literature sweep performed 2026-07-07 (five search angles, 21 sources fetched,
67 claims extracted, top 25 adversarially verified with 3 independent votes
each until a session rate limit stopped verification). Seven claims were
confirmed 3-0; eighteen were extracted with supporting quotes from primary
sources but not fully verified; none were refuted. Treat unverified items as
high-confidence but re-check quotes before citing in a submission.

## Bottom line

The proposed paper ("dynamics-derived time-of-impact via Parker-Sochacki
motion polynomials, for physics-based animation") is viable, but the novelty
claim must be positioned carefully: the *mechanism* already exists in
astrodynamics, while the *graphics/animation application* is genuinely open
and the graphics state of the art explicitly declares the gap.

## What is confirmed (3-0 votes)

1. The foundational PSM literature (Rudmin's tutorial, arXiv:1007.1677;
   Nurminskii & Buryi's 2011 GPU implementation) contains no application to
   collision detection, time-of-impact, event location, graphics, animation,
   or games. Scope is celestial mechanics and pedagogy.
2. PSM's polynomial lifting of game-relevant dynamics (projectile motion with
   air drag, N-body gravity) is established prior art - cite it, do not claim
   it.
3. The state-of-the-art graphics CCD benchmark line (Wang et al. 2021
   Tight-Inclusion, ACM TOG; Belgrod et al. arXiv:2112.06300) defines CCD
   exclusively over *linearized* per-timestep trajectories. Dynamics-derived
   TOI polynomials are absent from this entire line of work.
4. An empirical evaluation of 13 state-of-the-art CCD algorithms found
   several with efficiency or accuracy problems - the motivation for
   guaranteed approaches is already established in the graphics literature.
5. Provably-correct-in-floating-point, conservative TOI root isolation
   already exists in graphics (2021-2023) - but only for linear motion.
   Novelty cannot be claimed for "guaranteed root isolation" per se.

## The critical prior art found (unverified votes, quotes on file)

**Biscani & Izzo, heyoka (MNRAS 2021, arXiv:2105.00800; and arXiv:2204.09948,
MNRAS 513, 2022).** Their Taylor-series integrator detects ODE events by
running Collins-Akritas (Descartes' rule) real-root isolation on the
integrator's *own* per-step Taylor polynomial of the event function, with
no-missed-event guarantees, and their canonical example is *sphere-sphere
collision* in collisional N-body systems and eclipse crossings. This is
exactly the "use the trajectory's own polynomial for guaranteed collision
timing" mechanism, published in astrodynamics. **A graphics submission that
does not cite heyoka and clearly differentiate from it will be rejected by
any reviewer who knows it.**

Differentiation available to us: heyoka has no contact *response* (no
restitution, impact maps, resting contact, friction), no rigid-body
quaternion dynamics with body-frame collision geometry, no comparison
against graphics CCD baselines, no deformable/mass-spring systems, and no
production concerns (fixed frame-rate resampling, motion blur, engine
integration). Those are the paper's contributions.

## The gap statements the paper can quote

* Wang et al. 2021 (Tight-Inclusion): assumes linear per-vertex motion,
  "does not support curved trajectories," names nonlinear trajectories as
  future work.
* Belgrod et al.: scopes its released dataset and ground truth to future
  *linear* CCD algorithms.
* Catto, GDC 2013 (Box2D bilateral advancement; also used in Blizzard's
  Domino): assumes constant linear and angular velocity between steps,
  **explicitly rejects analytic/polynomial TOI as intractable for rotating
  3D bodies**, and acknowledges the algorithm can miss glancing collisions
  (rotate-in-and-out within a step). PSM motion polynomials directly answer
  all three: the polynomial comes from the dynamics, tumbling is handled,
  and root isolation cannot miss grazing events.

## Contributions that would survive SCA/SIGGRAPH review

1. First application of dynamics-derived Taylor motion polynomials to CCD
   *with contact response* in physics-based animation (impact maps,
   restitution, event-driven hybrid simulation), against graphics baselines
   (Tight-Inclusion-style linear CCD, conservative advancement) on
   graphics-style stress tests (tunneling, grazing, tumbling bodies).
2. Rigid-body PSM: quaternion/Euler polynomial lifting with body-frame
   collision geometry (corner trajectories polynomial in time), exact TOI
   for rotating bodies - the case Catto declares intractable.
3. The stability-order law measured in this repo (stable step grows linearly
   with series order; cost quadratically) as the honest stiffness boundary
   of the method.
4. Production workflow results: exact fixed-fps resampling and analytic
   sub-frame motion for motion blur from the same polynomials.

## Citations to include

PSM/Taylor: Parker & Sochacki 1996; Carothers et al. (projectively
polynomial); Rudmin arXiv:1007.1677; Pruett, Rudmin & Lacy JCP 2003;
Nurminskii & Buryi 2011; Jorba & Zou, Experimental Mathematics 14 (2005)
(adaptive order/step Taylor); TIDES (Abad et al., ACM TOMS 2012).
Event location: Shampine's event location; Hairer et al. dense output;
Biscani & Izzo arXiv:2105.00800 and arXiv:2204.09948 (heyoka); Amodio,
Brugnano & Iavernaro, Applied Numerical Mathematics 179 (2022) (high-order
one-sided event location); Collins & Akritas 1976 (root isolation).
Graphics CCD: Provot 1997; Bridson, Fedkiw & Anderson 2002; Mirtich
conservative advancement; Redon et al.; Snyder 1992 (interval root finding);
Brochu et al. 2012; Tang et al. 2014; Wang et al. TOG 2021
(Tight-Inclusion); Belgrod et al. arXiv:2112.06300; Zhang/Kim/Manocha
surveys; Catto GDC 2013.

## Amusing note

The sweep independently surfaced adamwermus.wordpress.com (2016
Parker-Sochacki N-body MATLAB post) as one of the few PSM artifacts adjacent
to games/graphics - i.e., the author's own blog is part of the prior-art
trail, consistent with the assessment that PSM's game-facing history
(including its Disney Infinity use) is informal and unpublished, which is
part of the opportunity.
