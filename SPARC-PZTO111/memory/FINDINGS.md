# PZTO(111) trajectory lithography — established findings

**Purpose.** This is the project's memory. Read it at the start of any session and
after every context compaction, before proposing experiments. It exists so we do
not re-run tests whose answers are already here, and so that when a new result
contradicts an old one we can tell which is better supported.

**How to use it.**

- Every conclusion carries a **reliability grade**. Trust A and B; treat C as
  provisional; D is an untested idea; W is something we asserted and later
  withdrew.
- If a new measurement contradicts an **A** or **B**, the new measurement is the
  one to doubt first — check the controls, the area fingerprint and the channel
  before believing it.
- If a new measurement contradicts a **C**, run the tie-breaker named in that
  entry rather than arguing from the existing data.
- When a conclusion changes, edit the entry in place and move the old text to
  the *superseded* line. Do not delete it — knowing what we used to believe is
  how we catch circular reasoning.

**Grading scale**

| | meaning |
|---|---|
| **A** | replicated in ≥ 2 independent areas or sessions, with valid controls, and robust to the analysis choices we know matter (q window, region size, estimator) |
| **B** | one clean measurement with valid controls, or several without |
| **C** | n = 1, or the controls failed, or the answer moves when an arbitrary analysis parameter moves |
| **D** | hypothesis, stated but not tested |
| **W** | withdrawn — we asserted this and the data since went the other way |

Last updated: 21 August 2026, after Section 16 and the T3 theory (C39-C40).

**The campaign has a quantitative law.** σ = (1/spacing²)·keep·V·dwell separates
**all 19 panels written so far** at σ_c = 302 ± 9 V·s/µm² — 14 successes above,
5 failures below, no overlap (**C40**). And a symmetry statement that reorganises
everything before C23: **a uniform out-of-plane field is invariant under the 120°
rotation relating the three skeletons, so it cannot select a director** — every
pre-C23 experiment was symmetry-forbidden, not merely under-driven.

Previously: after Sections 14-15 and the **direction re-analysis of
Sections 12-15** (C36-C38).

Two things changed and both matter more than any single new panel.

**C36 — score the DIRECTION, not the change in angular power.** Δ(angular
power) is a difference between two frames and carries every gain, tune and
streak difference between them. The population vector is a ratio *within* one
frame. Re-reading Sections 12-15 on direction rescued Section 14 from "void"
to its cleanest result and withdrew Section 15's headline.

**C41 falsifies T3's Condition 1.** Every template period from Λ to 8Λ selects
the director at identical σ — including 8Λ, which is two sign blocks rather than
a lattice. Commensuration with the lamellar period is **not** the selection rule,
and no ordering among periods reproduces (IT2 and IT3 disagree in direction). The
drive condition (C34/C40) stands; the selection condition is open (Q19).

**C34 revised.** The density threshold is between **50 % and 70 %** of the full
Λ/2 lattice, not "full lattice or nothing": 70 % rotates the superdomains
(4/4 in Section 14), 50 % does not (0/3 in Section 13). The geometry-independence
stands.

---

## 0. Inherited premises (from Docs 1–5 and Vasudevan et al. 2026)

These came from the theory/experiment documents supplied at the start, not from
our own measurements. Graded on whether *our* data has since borne them out.

| # | Premise | Grade | Status after our work |
|---|---|---|---|
| P1 | PZTO(111) has six tetragonal polar variants in two C₃ᵥ orbits; three mechanical skeletons related by 120° about [111], projecting to three stripe directors 60° apart | **A** | Confirmed — see C1 |
| P2 | Transition alphabet: type (a) within-orbit (no vertical-field driving force), type (b) cross-orbit ferroelastic, type (c) cross-orbit 180° | **D** | Never tested directly. We have never observed a clean type-(b) or (c) transition — see C8 |
| P3 | Three gates: **reachability** (bias polarity), **selectability** (trajectory), **availability** (mobile walls) | **B** | Useful framing. Reachability is measurable (orbit balance) and we have now opened it — C10. Selectability remains unachieved |
| P4 | Doc 3 §3.8 — orbit purity forecloses in-plane control | **C** → contradicted | We opened the gate to 65 % and the write *still* did not select. See C9 |
| P5 | Doc 2 §4.2 — a compatibility filter restricts the texture to three directors 60° apart | **A** | Confirmed in four areas |
| P6 | Doc 2 §6 — an intermediate/random state must be manufactured by an AC melt before rewriting | **W** | Withdrawn. Some virgin areas start near equipartition, and three AC+DC attempts failed to randomise anything (C14) |
| P7 | Doc 2 rule 5 — non-monotonic writing window in dose | **B** | Supported, with numbers: balance held at pitch × speed = 0.05 µm²/s and failed at 0.01 |
| P8 | Vasudevan Fig 2c — the inner written box is surrounded on all sides by superdomains of the **same** directionality; only the *phase* changed | **A** | Verified by extracting the figure. This is the mechanism the campaign has been chasing: the trajectory controls the sign/phase pattern, and direction follows from its geometry |

---

## 1. Conclusions from our measurements

### C1 — The in-plane texture lives on a fixed triad · **A**

> **Angles superseded by C31.** The {30°, 90°, 150°} of 13 August was a
> per-area fit. The rigid one-parameter fit across eight areas puts the film
> triad at **{2°, 62°, 122°}** (`FAM_FILM`). The *structure* — three
> directors exactly 60° apart — is what C1 established and it stands.

- **Start:** any state, any area.
- **Operation:** angular power spectrum of the signed LPFM response, q window
  1.5–14 µm⁻¹, 5° bins, normalised to unit mean.
- **End:** three peaks at 30°, 90° and 150° in every state, before and after
  every intervention, in four independent areas (2, 6, 7, 9 Aug) across two
  probes.
- **Why A:** replicated across areas and probes; the peak positions do not move
  when the q window or the angular half-width is changed.

### C2 — Lamellar period Λ = 245–400 nm · **B**

- **Start/End:** measured on 5 µm frames, 6 and 9 Aug, and again 14 Aug (325–354 nm).
- **Operation:** q²-compensated radial power along each family's k azimuth,
  15° wedge.
- **Caveat:** the per-family *difference* (30° at 333 nm vs 150° at 400 nm on
  6 Aug) rests on a wide 15° wedge and is only weakly directional — grade **C**
  for that sub-claim.
- **Use:** this number sets the erase-lattice spacing and the polarity coherence
  length. Do not use a value measured on a 2 µm frame — those are biased short.

### C3 — Score the **signed** response, never bare amplitude · **A**

- **Operation:** S = A·cos(φ − φ₀), with φ₀ fitted per frame as the offset that
  best separates the two PFM phase classes.
- **Why it matters:** |A| is positive everywhere and dips at walls, so its FFT is
  dominated by the wall network — at *half* the domain period — plus a large DC
  term. On 7 Aug this changed w₉₀ from 0.360 (amplitude) to 0.575 (signed).
- **Hard limitation:** the global sign of S is **not physically anchored**. The φ₀
  objective is symmetric under φ₀ → φ₀ + 180°, so only sign *differences* within
  one frame are meaningful. Never read an absolute polarity off S.

### C4 — The two DART channels must be made sign-consistent before averaging · **A**

- **Start:** 13 Aug, four LDART frames looked like pure noise — |S| = 3.0–4.1 pm
  despite healthy |A| = 18–25 pm, autocorrelation length ξ = 1 pixel, apparent
  Λ = 88–124 nm.
- **Operation:** measured the pixelwise correlation between the two channels'
  signed maps: **r₁₂ = −0.87 to −0.93**. The two DART sidebands sit on opposite
  sides of the contact resonance, where the phase-frequency slope has opposite
  sign, so when tracking is marginal the two φ₀ fits land 180° apart. Flipped one
  channel before averaging.
- **End:** |S| 3.5 → 19.2 pm, ξ 1 → 3 px, Λ 107 → 430 nm, and — the acid test —
  frame-to-frame |Δw| on an *unchanged* state improved from **0.047 to 0.014**.
- **Why A:** validated by a reproducibility improvement, not by argument.
- **Superseded:** we first concluded those frames were unusable and blamed the
  deflection setpoint. The setpoint may have helped, but the demonstrated fix was
  in software.

### C5 — The population vector, not a single director · **A**

- **Start:** the 2 Aug analysis reported "constant fits best", R = 0.735.
- **Operation:** recognised that a circular mean over a three-peak distribution
  barely moves as the weights shift.
- **End:** state variable is (w₃₀, w₉₀, w₁₅₀) plus anisotropy plus peak direction.
- **Caveat:** w is a *relative weight among the three families*, not a partition
  of all the power — the ±12.5° windows cover only 75° of 180°. Power at 60°
  would be invisible to w but visible in the peak. Always report both.

### C6 — Bipolar writes collapse to the local attractor; same-sign writes change the aggregate · **B**

- **Start:** various.
- **Operation:** bipolar = both polarities on every line (net 0 V per line, no
  spatial sign template). Same-sign = one polarity per line (±V template).
- **End:** bipolar writes at **eleven distinct commanded angles across three
  areas** all ended at that area's attractor. Same-sign writes moved the
  aggregate populations strongly (9 Aug: w₉₀ 0.335 → 0.622, peak → 90°).
- **Downgraded from A:** the word "obeyed" in earlier write-ups overstates it.
  C8 shows the same-sign writes did not *rotate* local orientations. The
  aggregate moved; the mechanism is not what we said.
- **Superseded:** "the write angle selects the family" → "the write angle
  influences the aggregate spectrum without rotating individual locations".

### C7 — The attractor is area-specific · **B**

- **Operation:** re-scored every *undirected* (bipolar/alternating) write with the
  population vector.
- **End:** 2 Aug area → median outcome 100° (n = 9 angles); 6 Aug → 30° (n = 3);
  7 Aug → 150–160° (n = 2). Same triad, different preferred member per area.
- **Interpretation:** a local pinning field λ_pin(r) varying on a µm scale sets
  what the film relaxes into when the write carries no directional information.
- **Superseded:** we once attributed this to a dominant cantilever-frame term.
  Withdrawn — the cantilever does not change between areas 3 µm apart.

### C8 — Every write measured so far **disorders** the local orientation; none rotates it · **A**

- **Start:** a characterised area with a valid pre-write baseline.
- **Operation:** paired change detection — register the after-frame onto the
  before-frame on the **height** channel, compute local stripe orientation
  (structure tensor) in each, mask on coherence, and take the distribution of
  Δθ(r) at the same locations. Under the triad, Δθ can only be 0 or ±60°.
- **End:** in every write measured, Δθ broadens from a spike (FWHM ~10°) into a
  broad distribution spanning ±90° **with no peaks at ±60°**.

  | write | \|Δθ\|<15° | at ±60° | disorder |
  |---|---|---|---|
  | 9 Aug, 0°, band | 0.344 | 0.090 / 0.073 | 0.79 |
  | 9 Aug, 90°, band | 0.370 | 0.094 / 0.110 | 0.76 |
  | 14 Aug, 90°, gate open | 0.867 | 0.001 / 0.026 | 0.16 |

- **Why A:** replicated on two sessions and two probes; on 9 Aug the unwritten
  control strips sat **below** the noise floor (0.046 and 0.059 against 0.116),
  which is the validity condition; robust to the coherence threshold
  (net +0.234 / +0.217 / +0.175 / +0.154 at 0.10 / 0.15 / 0.25 / 0.35).
- **This is the campaign's central negative result.** The goal is now stateable
  precisely: **produce a Δθ histogram with peaks at ±60°.** Nothing has.
- **Caveat:** written regions have lower |A|, and lower SNR broadens Δθ on its
  own. The effect survives at coherence ≥ 0.35, so it is not purely that.

### C9 — Orbit purity was **not** the limiting factor · **C**

- **Start:** 14 Aug, orbit gate open at **65 %** up (VDART_0007), the first time
  in the campaign.
- **Operation:** the standard same-sign band write, 90°, ±7 V, 20 nm pitch.
- **End:** Δθ still broad, no ±60° peaks (m₀ = 0.867). Aggregate w₉₀ rose
  0.450 → 0.659 with anisotropy 112 → 470 — the strongest aggregate shift of the
  campaign — but without local rotation.
- **Why only C:** n = 1, and the controls moved almost as much as the core
  (net +0.192 and +0.118 against +0.207), so confinement was weak.
- **Tie-breaker if contradicted:** repeat with the controls verified at the floor
  first, on a frame where the write footprint leaves ≥ 3 µm² of untouched
  material well inside the frame.
- **Contradicts P4.**

### C10 — Point pulses reopen the orbit gate · **B**

- **Start:** 14 Aug 09:38, VDART_0005: **0.0 % up-orbit**, |⟨e^iφ⟩| = 0.990,
  0 % of the minority in real patches — i.e. uniformly single-orbit.
- **Operation:** 16-pulse ladder, 4 / 6 / 8 / 10 V × 40 / 200 / 1000 / 5000 ms,
  1 µm grid, charge-balanced by exhaustive sign search, 69 s total.
- **End:** VDART_0006 at 09:45: **50.7 % up**, |⟨e^iφ⟩| = **0.342**, 98 % of the
  minority in patches ≥ 25 px, largest connected up-domain 10.5 µm² (42 % of the
  frame). Still 65 % at 10:19 and 65.0 % after a subsequent write at 10:53 —
  **open for at least 68 minutes**.
- **Why it is the pulses and not a read-out change:** the up-orbit fraction is
  spatially graded around the pulse sites — 66.9 % within 350 nm, 62.3 % in a
  400–550 nm annulus, 36.8 % far away. A read-out change would be uniform.
- **Confound, real but separable:** the same pulses also cleaned the tip. Lateral
  |S| rose **+29 % in regions the pulses never touched**, the lateral resolution
  limit improved 56 → 50 nm, and both contact resonances rose (lateral
  641.7 → 647.9 kHz, vertical 335.4 → 364.5 kHz) with vertical per-line scatter
  falling 6.8 → 1.6 kHz. Removing a compliant contaminant layer does exactly
  that. So the ladder did two things at once; the *gradient* is what proves the
  sample also changed.
- **This is the campaign's most valuable positive result.**

### C11 — A single pulse has an effective radius of ~625 nm · **C**

- **Operation:** Δ(up fraction) profiled against distance to the nearest pulse
  site; half-fall from +0.702 at r → 0 to a +0.261 far-field level.
- **End:** r_eff = **625 nm**.
- **Why only C:** all sixteen pulses contributed to one map, so amplitude and
  dwell are confounded, and at 1 µm grid spacing 2 × r_eff = 1250 nm means
  **neighbouring halos overlap** — which is why the "far" level is 0.26 rather
  than ~0.
- **Consequences already applied:** the next ladder needs ≥ 1.56 µm spacing
  (2×2 or 3×3 grid in a 5 µm frame, not 4×4), and `ERASE_SP` should be ~0.62 µm,
  not 0.175 µm — at 175 nm the lattice is over-dosed by (625/175)² ≈ **13×**.
- **Tie-breaker:** a sparse ladder at ≥ 1.5 µm spacing gives r_eff per (V, t).

### C12 — The film is grown-in / self-poled · **B**

- **Start:** genuinely fresh material, stage moved, **VDART taken first** before
  any LDART.
- **Operation:** three consecutive VDART passes without moving.
- **End:** |⟨e^iφ⟩| = 0.984 → 0.986 → 0.962; up-orbit 0.4 → 0.1 → 1.1 %. One
  class on the very *first* contact.
- **Conclusion:** our 0.4 V AC scanning did not cause it. Headers confirm
  `TipVoltage = 0`, `TipBiasOffset = 0`, `SurfaceBiasOffset = 0`, and 0.4 V is
  ~10× below the coercive voltage. Self-poling is the default expectation for a
  PZT-family film on an oxide electrode.
- **Open worry:** today's two areas read 0.1–3.5 % up-orbit while **every**
  campaign area read 21–36 %. The current locations may be unrepresentative.
  `[PROBE.2]` (an area survey at ≥ 50 µm spacing) would settle it and has not
  been run.
- **Superseded:** we first wrote "the area was already poled", implying an action
  had been taken. The defensible statement is "uniformly single-orbit, origin
  established as grown-in".

### C13 — Zero-net-DC writing preserves orbit balance; any DC offset re-poles · **A**

- **Operation / End:** 6 Aug, two zero-net-DC alternating writes took up-orbit
  21 % → 29 % → 52 %. AC + DC with +3 V drove it to 28 %, with −3 V to 66 %.
  14 Aug, a charge-balanced band write left the gate at **65.0 % → 65.0 %**.
- **Practical rule:** every trajectory must have mean(V) ≈ 0 over the path.
  `run_traj` now refuses |mean(V)| > 0.01 V. Two ways this silently broke before:
  an **odd cycle count** (H = 3.0 µm at 20 nm pitch gives 75 cycles → +0.063 V),
  and a **checkerboard sign that balances pulse count but not charge**
  (the ladder was 88 V·pt out until the sign assignment was solved properly).

### C14 — AC + DC does not randomise the state · **A**

- **Start:** 7 Aug, a written 90°-dominant area.
- **Operation:** three AC+DC conditions (5–6 V AC, 33–55 Hz, +3 and −2 V DC).
- **End:** peak stayed at 90° throughout; w₉₀ only eroded 0.575 → 0.511 → 0.369
  → 0.382 and anisotropy 76 → 37, i.e. it relaxed toward the local attractor
  rather than toward equipartition.
- **Interpretation:** a raster always carries a direction, so it can replace one
  direction with another but cannot remove direction. This is what motivated the
  isotropic pulse approach.

### C15 — No back-switching on the 5–45 minute scale · **B**

- **Start:** immediately after a same-sign band write.
- **Operation:** within-session paired comparison, written area against **itself**
  at two later times — no baseline needed, so tune, tip and location are
  identical by construction.
- **End:** 13/14 Aug, +5 → +44 min: core switched 0.123 against a floor of 0.064,
  |Δθ|<15° = **0.982**. Controls 0.855 and 0.920. Nothing moved.
  Independently, the 7 Aug texture stayed spatially phase-locked at r = 0.74–0.88
  for five hours through three AC+DC treatments.
- **Not established:** the 10-hour point. Height correlation between 13 Aug 22:04
  and 14 Aug 09:33 was **r = −0.001** — total drift, different material.

### C16 — The write's polarity reverses 8× inside one superdomain · **A** (fact) / **D** (its consequence)

- **Operation:** read the polarity structure straight out of the saved
  trajectory files.
- **End:** pitch 20 nm, polarity reverses every 20 nm → **polarity period 40 nm**
  against Λ = 325 nm. Each superdomain spans ~8 reversals and therefore sees a
  near-zero **mean** vertical field.
- **Grade split:** the geometric fact is certain. The *hypothesis* that this is
  why every write disorders (C8) rather than rotates is **D** — the test is
  `[POL.1]`, which sets `alt_period = 8` for a 320 nm polarity period.
- **Supporting circumstantial evidence:** isolated pulses, which are coherent in
  polarity across their whole 625 nm halo, *did* switch material (C10).

### C17 — Direction is recoverable by FFT even at long period · **B**

- **Operation:** synthetic single-family stripe patterns with known ground truth,
  Λ swept 150 → 1000 nm at SNR 5.
- **End:** peak recovered at 90.0° and w₉₀ ≥ 0.979 at **every** period.
- **Superseded:** we claimed "direction is not resolvable above 250–350 nm". That
  was wrong. The limit applies to *apportioning* w between families, not to
  finding a dominant direction, and the empty direction–period map that prompted
  the claim was a >2-pixels-per-bin display threshold, not a physical limit.

### C18 — Estimator comparison for directionality · **B**

Synthetic ground truth, mean |Δw| against the realised area fraction over
SNR 10 → 1:

| estimator | unequal periods | equal periods | character |
|---|---|---|---|
| FFT annulus | 0.162 | 0.155 | nearly unbiased (0.037) but **high variance** |
| Canny edge orientation | 0.045 | 0.032 | measures **wall length**, not area |
| structure tensor | **0.016** | **0.014** | lowest bias and variance |

- **Canny is the wrong tool for populations:** going from equal to unequal
  periods, its error against *area* rises 0.032 → 0.048 while its error against
  the *wall-length* prediction stays flat. Wall length ∝ area/Λ, so a
  finer-period family is over-counted. It also fails catastrophically in the
  noiseless limit (err 0.37–0.42, threshold pathology).
- **Where edges do win:** wall length per area, wall density, junction counts —
  the availability gate. Better than our adjacent-opposite-sign proxy, which
  saturates near 0.5 on a noisy phase map and is setpoint-dependent.
- **Unresolved:** on real frames the tensor and the FFT disagree on S5-before
  (w₉₀ 0.773 vs 0.460). Coverage is only ~55 % and the tensor may be partly
  wall-weighted on a near-square-wave profile. Do not swap the primary metric on
  the strength of the synthetic test alone.

### C19 — This probe is not degrading · **B**

- **Operation:** `probe_fingerprint` — a coherent degradation signature needs
  |A| down, resolution down **and** contact resonance up together.
- **End (13–14 Aug):** |A| lateral 16.6 → 59.0 pm, vertical 36.1 → 57.2 pm,
  resolution at the sampling limit throughout, z rms 0.45 → 0.39 nm. Only the
  resonance rose, and it rose at the *retune*, not by drift.
- **Note:** cross-probe |A| comparisons are meaningless. The campaign learned
  this when a fixed-kernel structure tensor reported different in-plane order for
  identical physics on a sharper tip.

### C20 — The pulse ladder did **not** break the in-plane texture · **C**

- **Start:** 14 Aug 09:33, LDART_0010, in-plane texture intact.
- **Operation:** the 16-pulse ladder (4–10 V, 40 ms–5 s, 1 µm grid).
- **End:** LDART_0011 at 09:49, same area, same tune. Paired change in the core:
  |Δθ|<15° = **0.964**, switched 0.097, **disorder 0.04** — i.e. essentially
  nothing, and *less* than an ordinary same-sign write achieves (0.16). The
  aggregate did move (w₉₀ 0.628 → 0.434, wall density 0.304 → 0.409), so
  something happened, but no location changed direction.
- **Why this matters:** hypothesis (c) says pulses break the **in-plane** strain
  and then you rewrite. What the ladder actually did was reopen the
  **out-of-plane** orbit gate (C10). Those are different claims and we conflated
  them for two turns. **The in-plane half of (c) is untested**, and `[GATE.2]`'s
  failure to rotate (C9) says nothing about it, because that write went into
  material that was gate-open but *not* IP-erased.
- **Why only C:** the height fingerprint for the pair is r = +0.378 against
  +0.90 for a clean same-spot pair, so drift or tip evolution is mixed in; and
  the ladder covers the whole frame, so there is no unwritten control — the two
  strips used as controls show disorder 0.24–0.30, *higher* than the core, which
  is unexplained.
- **Why the ladder is not an eraser:** sixteen isolated events on a 1 µm grid is
  a calibration instrument. An eraser has to tile the region. `[2.x]` was
  designed for that and has never been run.
- **Superseded:** "hypothesis (c) has already delivered its main result". It
  delivered an *unexpected* result. (c) itself is untested.


---

- **Extension, 14 Aug (the halo-spaced lattice):** repeated at the spacing C11
  actually calls for — 18 pulses, 8 V, 1000 ms, 620 nm triangular, charge-balanced
  to mean V +0.0000, with the scoring regions derived from the lattice extent plus
  the halo radius (CORE 2.63 µm², CTRL_L 3.02, CTRL_R 3.22, all outside the halo).
  This is the **best-controlled paired comparison of the campaign**: floor 0.015,
  Δθ mass 1.000, CORE height fingerprint +0.953, coverage 100 %, controls 0.054
  and 0.041. Result: CORE "switched" 0.120 but **|Δθ|<15° = 1.000 and disorder
  0.00** — the 12 % is boundary flicker, and the Δθ shape is the honest readout.
  Anisotropy went **up**, 341 → 828, the opposite of erasure; gate 67.3 → 57.9 %.
  **Erasure by pulse lattice is now a clean, well-controlled null at 8 V·s** — but
  C21 shows that charge was six times below the rotation threshold, so this is a
  null about the dose used, not about pulse lattices in general.

### C21 — A single pulse above ~40 V·s rotates its own patch by ~60° · **C**

- **Start:** the 16-pulse ladder frames already on disk, `LDART_0010` (before) →
  `LDART_0011` (after), 13 Aug. `[1.3]` had scored these on the *vertical*
  channel only; the in-plane question was never asked of them.
- **Operation:** paired Δθ inside a 350 nm disc around each of the sixteen sites,
  registered on Gaussian-filtered height, signed maps built with the C4 channel
  sign fix, coherence ≥ 0.10 in both frames.
- **End:** the response is a **threshold in charge = |V| × dwell**, not in either
  separately:

  | V | dwell | charge | \|Δθ\|<15° | +60° mass | θ before → after | \|Δθ\| |
  |---|---|---|---|---|---|---|
  | −10 | 5 s | **50 V·s** | **0.153** | **0.305** | 54.3° → 120.0° | **65.8°** |
  | +8 | 5 s | 40 V·s | 0.383 | 0.092 | 134.1° → 102.1° | 32.0° |
  | +6 | 5 s | 30 V·s | 0.988 | 0.000 | 127.2° → 118.9° | 8.3° |
  | −4 | 5 s | 20 V·s | 0.624 | 0.000 | 98.9° → 111.1° | 12.3° |
  | −10 | 1 s | 10 V·s | 0.990 | 0.000 | 111.5° → 111.1° | 0.4° |
  | +8 | 1 s | 8 V·s | 0.840 | 0.000 | 99.2° → 98.5° | 0.7° |

- **Why this matters:** the −10 V / 5 s row is the **first ±60° concentration
  anywhere in the campaign**. Every trajectory write to date produced a broad
  Δθ distribution (disorder 0.16, C8) rather than mass at a triad member. A
  single high-charge pulse produced mass at +60°.
- **Why only C:** n = 1 at the threshold. Amplitude and dwell are confounded
  along the ladder diagonal, 0.305 leaves 70 % of the mass elsewhere, and the
  neighbouring halos overlapped at 1 µm spacing (C11), so the "before" state of
  one disc was already disturbed by its neighbours.
- **Consequence already applied:** `[2.3]`'s failure is explained. The erase
  lattice used 8 V × 1 s = **8 V·s**, six times below threshold — the same
  condition that moved its patch by 0.7°. Choosing "mid-range with headroom"
  was the wrong call when the threshold was already latent in unanalysed data.
- **Tie-breaker:** `[CHG.1]`/`[CHG.2]`, a four-pulse charge ladder at fixed 10 V
  with dwells 5/10/15/20 s (50–200 V·s), 2 µm apart so the halos are separate,
  which unconfounds dwell from amplitude and asks whether more charge sharpens
  the ±60° peak or merely broadens the distribution.


### C22 — Probe #3 does not inject DC charge; every write since the swap is void · **A**

- **Start:** probe #3 fitted 14 Aug ~16:30, fresh area at +12/+5 µm offset,
  setpoint 0.65 V, LDART 656 kHz (Q 525), VDART 374 kHz (Q 112). Orbit gate
  51.2/48.8 % — the most open reading of the campaign.
- **Operation:** Δ(up fraction) inside pulse discs minus the far field, the same
  method that established C11, applied to three writes:

  | write | probe | charge/pulse | Δ(up) near − far | |
  |---|---|---|---|---|
  | 13 Aug ladder | #2 | 50 V·s | **+0.389** | wrote |
  | Step 3 seed `[3.3]` | #3 | **100 V·s** | −0.044 | nothing |
  | R4 lattice `[R4.2]` | #3 | 10 V·s | ~+0.02 | nothing |

- **End:** the Step 3 row settles it. **Twice** the charge that demonstrably
  switched with probe #2 produced nothing, so this is not a dose effect.
- **Mechanism (the user's, and the better one):** the **litho writing deflection
  setpoint is a separate parameter from the DART imaging setpoint.** Too low a
  writing setpoint means the tip is not pressed hard enough during the
  trajectory, so electrical contact is poor and no charge is injected — while
  imaging, on its own setpoint, stays perfect. This needs no coincidence and it
  explains why both probe #3 writes failed *regardless of dose*.
  My earlier guess — a contaminated apex passing 650 kHz AC and blocking DC —
  required a fresh probe to arrive already fouled, and is not needed.
  **The observation is grade A; this mechanism is grade C** until `[WGATE]`
  shows that raising the writing setpoint restores switching.
- **Therefore the C21 ~40 V·s threshold is NOT transferable.** It was measured at
  whatever litho setpoint probe #2 ran with, so it must be re-measured per probe
  *and* per writing setpoint. `[WGATE]` spans 10–400 V·s and sets `WG_THRESH`,
  from which `[R4.1]` now sizes `PULSE_N`.
- **Grade A** because it is replicated across two independent experiments at two
  very different doses, with a within-campaign positive control (the ladder)
  measured by the identical method.
- **What it voids:** `[3.3]`/`[3.4]` (the oriented seed) and all of R4 are void as
  *physics*. R4's null — |Δθ|<15° between 0.964 and 1.000 in all nine panels,
  ±60° mass 0.000, peak direction unchanged to the degree, trajectory-only stage
  0.986–1.000 — says nothing about the in-plane-field hypothesis. It only says the
  tip was not writing.
- **What it does NOT void:** everything measured from probe-#2 data, including
  C21, C11, and the triad fit (which is a read-only property of the images).
- **Guard added:** `write_check()` in `[TOOLKIT]` and the `[WGATE]` cell. No
  pattern experiment runs again without passing it (near − far ≥ 0.15).


### C23 — An oriented pulse lattice sets the in-plane superdomain direction · **A**

- **Start:** virgin PZTO(111), probe #3, setpoint 0.60 V, LDART ~649 kHz.
- **Operation:** square pulse lattice aligned to a commanded director, spacing
  Λ/2 so the **sign period equals Λ**, 10 V × 1 s = 10 V·s per pulse, exactly
  charge-balanced per panel. Scored as angular power within ±15° of the command,
  against a temporal floor from a do-nothing frame pair.
- **End, R4 (14 Aug, nine panels, three commands):** on LDART, the 2° command
  gave peaks 1°/1°/1° (Δpower +0.166 to +0.316) and the 122° command 124–136°.
  The 62° command did not take on LDART. Floor 0.008–0.018.
- **Replicated, R5 and R6:** R5's allowed command rotated 56° → 176°
  (Δpower@cmd **+0.384**, 48× floor). R6's write 1 gave Δpower@A **+0.392** (P1)
  and **+0.577** (P3), with the untouched panel at **−0.006**.
- **Grade A:** four areas, three sessions, with untouched in-frame controls and a
  temporal floor each time.

### C24 — A written direction can be RE-written to another allowed director · **B**

- **Start:** R6, 14 Aug ~21:20, fresh area at (−15, +10) µm. Triad {4, 64, 124},
  virgin peak 64° → M = 64, A = 4°, B = 124°.
- **Operation:** three panels. **P1** got A then B; **P2** got B only (virgin
  reference); **P3** got A then nothing (retention). Both B writes came from one
  file, minutes apart, same probe state.
- **End:** P1's peak went **64° → 1° → 124°** — two successive commanded 60°
  rotations in the same 2 µm region. During write 2, P1's power@A fell
  **0.542 → 0.255 (−0.287)** while power@B rose **+0.149**.

  | | Δpower@B on write 2 |
  |---|---|
  | B onto virgin (P2) | +0.111 |
  | **B onto written (P1)** | **+0.149** |
  | ratio | **1.34** |

- **This is the reconfigurability the campaign set out to test**, and the thing
  Vasudevan et al. could not demonstrate. Rewriting runs at least as efficiently
  as writing virgin material — there is no measurable barrier from the existing
  texture.
- **Why B and not A:** n = 1 per cell. P2's virgin baseline at 124° was already
  high (0.251) and drifted +0.021 during write 1, so the 1.34 ratio is softer
  than the peak trajectory, which is the stronger evidence.
- **Tie-breaker:** repeat with the roles swapped (A and B exchanged) and with a
  second area.

### C25 — The written direction relaxes measurably within minutes · **B**

- **Start/Operation:** R6 panel P3 — A written, then left alone while write 2 and
  a frame ran elsewhere, ~13 min.
- **End:** power@A **0.749 → 0.673, Δ −0.076**, about 4× the 0.018 floor, i.e.
  ~10 % of the written signal in 13 minutes.
- **Consequences.** (i) Every paired measurement in this campaign has a
  relaxation component; a "before" taken 15 min earlier is not the same state.
  (ii) The C24 rewrite numbers include this: P1's −0.287 at A contains roughly
  −0.055 of spontaneous decay, so the write-driven part is about −0.232 — still
  dominant. (iii) An hour-scale retention point is now the cheapesthigh-value
  measurement available and has still not been taken.
- **Why only B:** one panel, one interval, no repeat.


### C26 — A charge-balanced raster depletes the family parallel to its own scan lines — **on PRE-POLED film** · **B**

> **Revised by C49 (22 Aug).** The depletion holds for the three pre-poled
> panels measured here. On **virgin** film the sign reverses: IT6 rastered along
> 62° and the parallel family went 0.415 → **0.601**. C26's own unpoled control
> (Q2, 0.15 → 0.23) was already showing this and was recorded below as an
> unexplained anomaly. The out-of-plane poling state sets the sign of the effect,
> so every statement in this entry needs "on pre-poled film" attached.

- **Start:** R7, 14 Aug ~22:20, virgin area at (+15, +15) µm, triad {6, 66, 126},
  four 2 µm panels. Q1/Q3/Q4 poled, Q2 left untouched as the in-frame control.
- **Operation:** raster over each box **along M = 6°**, one pass at **+7 V** then
  one at **−7 V** — net charge zero — at Λ/4 = 97 nm pitch. Intended as neutral
  agitation to prepare a defined state.
- **End:** it is not neutral. The family **parallel to the raster** is depleted in
  every poled panel, while the unpoled control moves the other way:

  | panel | poled | w(6°) before → after |
  |---|---|---|
  | Q1 | yes | 0.29 → **0.14** |
  | Q3 | yes | 0.24 → **0.10** |
  | Q4 | yes | 0.25 → **0.04** |
  | Q2 | **no** | 0.15 → 0.23 |

  The redistribution is large — Q3 reached w(66°) = 0.84 and Q4 w(126°) = 0.83,
  **stronger than the pulse lattice achieves** (~0.33 at its commanded angle).
- **The gap: the destination is not predicted.** Q3 and Q4 had nearly identical
  starting populations (w = 0.24/0.24/0.52 and 0.25/0.17/0.57) and went to
  *opposite* members, 66° and 126°. So the raster reliably says "not along me"
  but does not say which of the other two wins.
- **Why only B:** one area, n = 3 poled panels, one raster direction. The
  depletion is consistent; the mechanism and the selection rule are untested.
- **Immediate consequence:** a depleter plus a selector is a complete control
  scheme. Poling along two triad members in turn should leave only the third —
  worth testing before any further lattice work.

### C27 — Pre-poling makes the pulse lattice WORSE, not better · **C**

> **Downgraded B → C by Section 7 (C30).** C27's reading was that
> pre-treatment consumes the wall mobility the lattice needs. Section 7
> then wrote a *second* lattice onto nine already-written panels and the
> gain was the same as writing onto virgin film (+0.155 to +0.162 for every
> Δ, including Δ = 0). Prior writing does not spend the resource. Whatever
> C27 saw was specific to **poling**, not to prior lattice writing, and
> n = 1.

- **Operation:** R7 Q1/Q3 (poled, then lattice at 66°) against Q2 (virgin, then
  the same lattice), one lattice file, minutes apart.
- **End:** on virgin material the lattice behaved as C23 predicts —
  power@66° **0.133 → 0.330 (+0.197)**, peak 124° → 64°. On poled material it
  went the **other way**: Q1 0.548 → 0.380 (−0.168), Q3 0.647 → 0.340 (−0.307).
  Net pre-pole effect **−0.435**.
- **Reading:** the pole had already driven the texture past what the lattice
  sustains, and the lattice pulled it back toward its own equilibrium of ~0.33–
  0.38. The lattice behaves as an **attractor at a fixed order parameter**, not as
  a monotonic driver.
- **Practical:** do not pre-pole before a lattice write. The proposed
  pole → lattice → trajectory sequence is worse than the lattice alone.

### C28 — The trajectory consolidates the lattice direction; it does not steer · **C**

- **Operation:** R7 stage 3, dense raster at Λ/4 with **+V forward, −V backward**
  on each line, commanded to **126° — 60° away from the lattice's 66°**, into
  Q1 and Q2 only.
- **End:** power at the *lattice* angle rose in both trajectory panels
  (Q1 **+0.302**, Q2 **+0.132**) while the no-trajectory controls stayed flat
  (Q3 −0.017, Q4 +0.015). Gain at the trajectory's **own** angle appeared only in
  Q2 (+0.186), and **neither peak moved to 126°** (Q1 66° → 59°, Q2 64° → 64°).
- **Reading:** a competing trajectory cannot pull the texture off a
  lattice-established direction. It sharpens what is already there. This is
  consistent with C8 (writes do not steer) and extends it: they do not disorder
  either, once a lattice has set the direction.
- **Why only C:** floor was 0.040 in this session (drive wandered 645–649.6 kHz),
  n = 2 trajectory panels, one angle pair.


### C29 — The lattice→direction rule replicates 9/9 in a Latin square · **A**

- **Operation:** Section 6, fresh probe, fresh 8 µm area. Nine 1.4 µm panels,
  three commanded directions × three replicates, assigned by a **Latin square**
  so commanded direction is orthogonal to both row and column position. Lattice
  at Λ/2 spacing (sign period Λ), 10 V × 1 s, charge-balanced per panel.
- **End:** the confusion matrix is **diagonal, 9/9**. Every panel's post-write
  peak landed on its own commanded director, none on either of the other two.
- **Retention:** re-imaged at **+90 min**, 8/9 still on target. This refines
  C25: the ~10 %/13 min relaxation does not continue to zero — it settles.
- **Why A:** three replicates per condition, position decoupled by design, and
  it reproduces C23 in a different area with a different probe.
- **Supersedes nothing; it is the replication C23 was missing.**


### C30 — All three Δ are equally accessible, and lattice writes are cumulative · **B**

- **Operation:** Section 7 re-wrote the nine Section 6 panels, commanding
  Δ = 0°, +60°, −60° (three panels each) relative to what each already held.
- **End:** **8/9** panels moved to the newly commanded director
  (sign test, p = 0.00097). The mean gain was **+0.155 to +0.162 for all three
  Δ**, statistically indistinguishable.
- **Two readings, both load-bearing:**
  1. **Three-fold symmetry is exact.** Rotating +60° is neither easier nor
     harder than −60°, and neither is harder than staying. No director is
     privileged, which is what P5's compatibility filter predicts.
  2. **The lattice is cumulative, not saturating.** The Δ = 0 panels — already
     written to that director — gained *as much* as the panels being rotated.
     Writing does not use up a finite resource. This is what downgraded C27.
- **Why B:** one session, one area; the nine panels are not independent of each
  other's history.


### C31 — The film triad is a single constant over the whole sample · **A**

- **Operation:** rigid one-parameter triad fit (`fit_triad`: one free rotation
  φ₀ ∈ [0°, 60°), members forced exactly 60° apart) on every area imaged since
  14 August — eight areas across three probes and four sessions.
- **End:** every area lands within **~5°** of `FAM_FILM = (2°, 62°, 122°)`.
  Section 13's area fit 4/64/124 — 2° off. Section 12's fit 2/62/122 — 0.5° off.
- **Use:** never re-fit the triad inside a section. Fit once per area and
  **pin** it (`pin_triad`), because φ₀ is defined mod 60° and a re-fit can
  permute the index→angle mapping. That permutation is what made `[7.1]` report
  "0/9 hold" when the truth was 8/9.
- **Why A:** eight areas, three probes, and the modulation depth cleanly
  separates virgin (0.17–0.25) from poled (~0.53) throughout.


### C32 — The order parameter is size-independent; the pulse cost is not · **B**

- **Operation:** Sections 12 and 13. Full lattices at Λ/2 written into regions
  of 1.29, 2.46 and 2.24 µm, each read in a window matched across sizes.
- **End:**

  | written | pulses | Δpower | peak err | Δ×1000/pulse |
  |---|---|---|---|---|
  | 1.29 µm (S12) | 144 | +0.265 | 1° | 1.84 |
  | 2.46 µm (S12) | 484 | +0.325 | 1° | 0.67 |
  | 2.24 µm (S13) | 256 | +0.341 | 3° | 1.33 |

- **Reading:** Δ is flat-to-rising over 3.6× in area, while pulses scale with
  area — so **per-pulse efficiency falls as 1/area**. There is no upper size
  limit within this range and no economy of scale. Writing a large region costs
  area-proportional pulses for a constant order parameter.
- **Caveat on the range:** 1.29 → 2.46 µm is 1.9× in length. A flat result over
  that span establishes "no fall within a factor of ~3.6 in area", **not** an
  upper limit. The 20× ladder of the original R9 design was never run.
- **Why B:** two sections agree, but the size axis is n = 1 per size.


### C33 — Below ~4Λ the order parameter does not exist, though writing still acts · **B**

- **Operation:** Section 12 wrote full lattices into 0.35 and 0.58 µm regions
  alongside 1.29 and 2.46 µm ones.
- **End:** both sub-micron panels returned **nan** from the FFT metric. Two
  independent floors bind:
  - `dir_power` needs **≥ 24 px** — 0.94 µm at 39 nm/px;
  - the estimate needs **≥ ~4 stripe periods** — 0.94 µm at Λ = 234 nm.
  A 0.35 µm box holds 1.5 periods. There is no direction in it to measure, at
  any pixel size.
- **But the pulses did act.** The real-space statistic (RMS change in the
  normalised signed map, against boxes of matched size on untouched film) gives
  **z = +9.9 at 0.35 µm and +33.8 at 0.58 µm**, against +36.7 and +56.8 for the
  1.29 and 2.46 µm panels. Sixteen pulses at 0.35 µm perturbed the texture as
  strongly as 484 did at 2.46 µm.
- **Consequence for the campaign's question 1 (how small?):** the lower limit is
  currently set by the **readout**, not by the physics, and it sits *below*
  2 r_eff = 1.25 µm — so the halo hypothesis (H1) was never testable with this
  metric. A different observable is needed: the real-space difference statistic
  above is the candidate, since it is defined at 9 px.
- **Design lesson:** I sized the ladder in units of r_eff without checking the
  readout could resolve it. See §3.


### C34 — The lattice needs 50–70 % of full Λ/2 density, and the geometry of the thinning is irrelevant · **A**

> **Revised 21 Aug.** The original entry read "*a THRESHOLD actuator … full
> lattice or nothing*", bracketing ρc between 70 % and 100 %. That came from
> Δ(angular power). Re-scored on **direction** (C36), Section 14 shows **4/4
> equivalent 60° rotations at 70, 80, 90 and 100 %**, so 70 % works. Section 13
> shows **0/3 at 50 %**. The bracket is **50–70 %**, and the geometry claim is
> unchanged — P50, W50 and R50 all failed on direction too.

**This is the most consequential result of the campaign so far, and it closes a
programme.**

- **Operation, part 1 (Section 12).** One panel size, one spacing, dose varied
  by removing wall-ranked sites: 100 / 70 / 40 / 20 % of a full Λ/2 lattice.
- **Operation, part 2 (Section 13).** One panel size, one dose (**50 %**), and
  the *geometry* of the removal varied three ways at identical pulse count and
  identical charge:
  - **P50** — every other column, i.e. thinned *along* the stripes. Sign period
    stays Λ.
  - **W50** — row pairs kept (0,1),(4,5),…, thinned *across* the stripes. Sign
    period becomes 2Λ.
  - **R50** — random half, ± counts matched. No period at all.
- **End:**

  | density | geometry | Δpower | fraction of full |
  |---|---|---|---|
  | 100 % (S13) | complete | **+0.341** | 1.00 |
  | 100 % (S12) | complete | **+0.265** | 1.00 |
  | 70 % (S12) | wall-ranked | +0.082 | 0.31 |
  | **50 % (S13)** | **P50, along stripes** | **+0.007** | **0.02** |
  | **50 % (S13)** | **W50, across stripes** | **+0.031** | **0.09** |
  | **50 % (S13)** | **R50, random** | **+0.011** | **0.03** |
  | 40 % (S12) | wall-ranked | +0.033 | 0.12 |
  | 20 % (S12) | wall-ranked | −0.076 | < 0 |

  Section 13's floor was 0.108; all three halves sit at 0.1–0.3× it. Section
  13's FULL panel reached the **strongest alignment of the campaign**:
  w(4°) 0.214 → 0.595 while w(124°) collapsed 0.474 → 0.082, peak locked to 1°.
- **Reading:**
  1. **The knee is between 70 % and 100 %** of full Λ/2 density, and it is
     steep. Halving the density costs ~95 % of the effect.
  2. **Which sites you remove does not matter.** Three wholly different 50 %
     geometries gave the same null. Preserving the ± template period bought
     nothing.
  3. **All four Section 13 arms perturbed the film hard** — z = +43.6 (FULL),
     +28.5 (P50), +18.6 (W50), +23.9 (R50) against a control of 0.507 ± 0.019.
     The halves failed to **orient**, not to **act**. The tip was writing.
- **What it kills:** adaptive, wall-masked, mismatch-masked and perimeter-only
  patterns. All are thinnings, and a 2× thinning already costs everything.
  Campaign question 2 — "can we use fewer writing points?" — is answered **no**.
  H5 (perimeter-only) should not be run.
- **What it demands of the theory:** both models on the table were
  linear-response and both fail. T1 (wall-pinning, effect ∝ pulses on walls)
  predicted 0.50 for every half; T2 (coherent structure factor) as I first wrote
  it predicted 0.95 for P50. Observed: 0.02–0.09. See §3 for the reasoning error
  in the T2 prediction.
- **Why A:** two independent sections, two areas, two probes, four densities and
  three geometries, with valid tiled controls in both.
- **Unexplained, and flagged rather than explained away:** Section 12's thinned
  panels barely perturbed the film (z = +2 to +4) while Section 13's carried
  *less* charge per unit area and perturbed it strongly (z = +18 to +28). The
  orientation nulls agree; the perturbation magnitudes do not.


### C35 — Wall-ranked masking beats random selection at equal dose · **W**

**Withdrawn.** Section 11 appeared to show MASKED − RANDOM = +0.265 at 4.6× the
floor with matched pulse counts. Re-reading the trajectory file and the frames on
20 August, three things are wrong with it:

1. **The control band lay inside the written material.** Both panels are strips
   spanning y ≈ 3.2–4.8 µm and the control band was y 3.3–4.7 — the same rows.
   The floor was measured on written film. (This is the `dir_power` crop bug in
   §3 compounding a placement error: the band was 7.2 × 1.4 µm, so only a
   1.4 × 1.4 µm square at its left end was ever scored, and that square sat
   inside the MASKED panel, reading Δ = +0.329.)
2. **The pulse counts were not matched** — the file splits **119 / 61**, nearly
   2×. It was never a fair comparison at fixed dose.
3. **Re-measuring in matched windows** gives MASKED +0.263 and RANDOM
   **+0.103** — the earlier −0.103 has the wrong sign.

The comparison may still hold directionally, but it has no valid control and no
dose matching, and **C34 makes the question moot**: at any thinning worth the
name, ranking does not rescue the effect. Do not re-run Section 11; run the
density ladder instead.


### C36 — Score the DIRECTION of the superdomains, not the change in angular power · **A**

**A methodological conclusion, and the most useful one on this page.**

- **The problem.** `Δ(angular power at the commanded director)` is a *difference
  between two frames*. It inherits every difference in gain, tune, setpoint and
  scan artefact between them. Section 14 was declared void on 20 August because
  its control band "fell" by −0.110 in every tile and the floor came out at
  0.199, larger than any panel signal.
- **The diagnosis.** One of its two baselines, `LDART_0035`, is **streaky**.
  Measured on untouched film only:

  | frame | role | \|S\| | streak index | control-band w(0/60/120) |
  |---|---|---|---|---|
  | 0033 | scout | 28.6 | 0.060 | 0.462 / 0.278 / 0.260 |
  | 0034 | baseline a | 30.5 | 0.069 | **0.407** / 0.326 / 0.267 |
  | 0035 | baseline b | **12.9** | **0.115** | **0.569** / 0.242 / 0.189 |
  | 0036 | after | 32.3 | 0.077 | **0.398** / 0.324 / 0.278 |

  Scan lines run along **x**, so line-to-line offsets put their FFT power on the
  q_y axis — which `dir_power` maps to a stripe director of **0°**. A streaky
  frame therefore reads excess population at 0° with no domains involved, and
  0° happened to be Section 14's commanded direction. 0035 is outvoted 3-to-1,
  and 0034 → 0036 in the untouched band is a near-perfect null.
- **The fix.** Use the **population vector** over the pinned triad, normalised
  to sum to 1. `dir_power` already divides by the total power in the q window,
  and normalising the three members removes what is left, so the quantity is a
  ratio *within one frame*. An isotropic noise floor compresses all three toward
  1/3 — attenuating contrast but never changing which director leads.
- **The two readouts that matter:**
  - **dominant director** before and after (argmax of the population vector);
  - **lead** = w(commanded) − max(w(other two)), signed, within-frame.
- **What it changed.** Section 14 went from void to 4/4. Section 15's headline was
  withdrawn (C38). Nine of fifteen panels across Sections 12–15 had two
  baselines that agreed on the before-state; where they disagree, the
  before-state is not established and no rotation can be claimed.
- **Also record the commanded angle from the trajectory file**, not from a
  re-fit of the image: the lattice's own nearest-neighbour bonds give it
  unambiguously, and a triad re-fit can permute the labels (C31, C35).
- **Why A:** it resolves a contradiction between two analyses of the same data,
  the streak mechanism is independently measurable, and the majority test is
  3-to-1.


### C37 — 70 % of full density still rotates the superdomains; 50 % does not · **B**

- **Operation:** Section 14, four panels at 100/90/80/70 % of a full Λ/2
  lattice, random thinning, ± sets drawn separately. All four started dominant
  at 60° and all four were commanded to 0°, so every panel performed an
  **equivalent 60° rotation** — the first density ladder where that is true.
- **End:**

  | density | pulses | dominant before | after | lead after | vs control floor |
  |---|---|---|---|---|---|
  | 100 % | 256 | 60° | **0°** | +0.204 | 2.3× |
  | 90 % | 230 | 60° | **0°** | +0.059 | 0.7× |
  | 80 % | 204 | 60° | **0°** | +0.590 | 6.8× |
  | 70 % | 180 | 60° | **0°** | +0.158 | 1.8× |

  Control: **0 of 6** tiles changed dominant director; Δlead −0.009 ± 0.058.
- **Against Section 13**, whose three 50 % arms were also 60° rotations
  (64° → 4°): P50 stayed at 64° (lead −0.375), R50 went to the **wrong**
  director 124°, W50 tied. **0/3.**
- **Reading:** ρc is between 50 % and 70 %. This is the answer to Q8.
- **Caveats, both real:** the 90 % panel's lead is below its own control floor,
  so the ladder is non-monotonic and panel-to-panel scatter is comparable to the
  density effect over 70–100 %. And Section 14's before-state rests on one of two
  baselines — the majority-endorsed one (C36), not a clean pair.
- **Why B:** one area, one replicate per density, and the before-state needed a
  majority vote to establish.


### C38 — A Λ/4 lattice reaches w(commanded) = 0.851 without re-poling; whether it beats Λ/2 is untested · **C**

- **Operation:** Section 15, Λ/2 (144 pulses) against Λ/4 (400 pulses) in one
  frame, sign alternating every **two** rows in the dense panel so the template
  period stays Λ in both.
- **End:** the Λ/4 panel reached **w(124°) = 0.851** — by far the purest in-plane
  state of the campaign — with w(4°) 0.307 → 0.106 and w(64°) 0.329 → 0.044.
  VDART afterwards: up 46/54 %, \|⟨e^iφ⟩\| 0.390, two classes balanced, gate
  open. **4× areal charge did not re-pole**, so P7's non-monotonic window does
  not bite here.
- **But the comparison is confounded and the original claim is withdrawn:**

  | panel | dominant before | commanded | task |
  |---|---|---|---|
  | REF Λ/2 | 64° | 124° | a genuine 60° rotation |
  | OVER Λ/4 | **124°** | 124° | **already on target — a sharpening** |

  The commanded director was chosen once per frame, as the triad member farthest
  from the *frame-wide* virgin peak. Local texture varies, and the Λ/4 position
  already favoured 124°. Per-pulse gain in w(commanded) is **REF 1.61 against
  OVER 1.04 per 1000** — over-driving looks *worse* — but w is bounded by 1 and
  OVER ends deep in saturation, so that comparison is not clean either.
- **Superseded claim:** "over-driving nearly triples the effect; Λ/2 is not the
  ceiling" (20 Aug, from Δ(angular power) = +0.462 against +0.159). Withdrawn:
  the two panels were not given the same task.
- **The decisive test** is Section 16 — matched rotation tasks, with the command
  chosen **per panel** at 60° from that panel's own local dominant director.
- **Why C:** n = 1 per condition and the one comparison it was built to make is
  confounded.
- **Second, smaller defect, found 21 Aug while building Section 16.** The
  readout window overhung the written lattice at its corners. The written region
  is a square of side `L = (n−1)·spacing` **rotated** by the command, and an
  axis-aligned window of side `W` fits inside it only if `W·ANG ≤ L`, where
  `ANG = |cos| + |sin|`. `solve_grid` had required `L·ANG ≥ W`, i.e. `L ≥ W/ANG`
  — looser by `ANG²`, up to 1.93× at 45°. At the 124° command (ANG 1.388) the
  requirement was `L ≥ 1.63 µm` and the panels had `L = 1.54` (REF) and
  `1.33 µm` (OVER), so the window corners overhung by 0.05 and 0.15 µm. Both are
  far inside `r_eff` = 625 nm, so those corners still sit in the pulse halo and
  the numbers above stand — but the rule was wrong and is now fixed.


### C39 — A Λ/4 lattice reaches a far purer aligned state than Λ/2, on matched tasks · **B**

- **Operation:** Section 16, two runs. One Λ/2 panel and one Λ/4 panel per run,
  positions swapped between runs, template period held at Λ in both (Λ/4
  alternates sign every **two** rows). Each panel commanded **60° from its own
  local dominant director** — the fix for C38's confound.
- **End:** **4/4 turned.**

  | run | | pulses | dominant | lead after | vs floor | **w(cmd)** |
  |---|---|---|---|---|---|---|
  | 1 | REF Λ/2 (left) | 256 | 64 → **4°** | +0.088 | 4.0× | 0.452 |
  | 1 | OVER Λ/4 (right) | 576 | 64 → **4°** | +0.726 | 11.8× | **0.831** |
  | 2 | OVER Λ/4 (left) | 576 | 60 → **0°** | +0.758 | 9.8× | **0.861** |
  | 2 | REF Λ/2 (right) | 256 | 60 → **0°** | +0.302 | 7.2× | 0.599 |

  RUN 2's control: **0 of 12** untouched tiles changed dominant director,
  Δlead +0.033 ± 0.052. RUN 1: 3 of 12, all in tiles whose populations were
  nearly tied.
- **Reading:** on **final w(commanded)** the conditions separate with no overlap
  — OVER 0.831/0.861 against REF 0.452/0.599, a gap of **+0.232** against a
  within-condition scatter of 0.147. Λ/4 is also **five times more
  reproducible** (spread 0.030 against 0.147).
- **Two honest qualifications.** On **Δ(lead)** the gap (+0.116) is *smaller*
  than the scatter (0.554), because Δ inherits the starting state; that is why
  final w(cmd) is the metric to use (C36 §6.3). And **per-pulse efficiency is
  not resolved** — RUN 1 favours OVER by 1.3×, RUN 2 favours REF by 1.65×.
- **No re-poling** at 4× areal density: VDART 36.4/63.6 then 33.0/67.0 %, gate
  open both times.
- **Why B:** two replicates per condition with position balanced, one area, one
  probe. It supersedes C38's withdrawn claim with a properly matched comparison.


### C40 — One areal charge density threshold governs every write in the campaign · **A**

> **Revised by C47 (22 Aug).** The **threshold** interpretation is withdrawn:
> σ_c = 302 V·s/µm² does not separate working from non-working conditions, and a
> panel at 0.70 σ_c selects at 3.5× the null. The **law** w = 0.234 ln σ − 0.887
> also fails to describe the range 0.7–1.5 σ_c, where the final population is
> flat at 0.47 ± 0.01 while σ varies 2.2×. What the r = +0.974 fit over 19
> panels was actually describing is unclear — those panels came from different
> areas, with different starting populations, scored with the *old* threshold,
> so the correlation may have been driven by the starting states and the
> detection floor rather than by a physical dose-response. Treat σ_c as a
> convenient unit of charge from here on, not as a threshold, and treat the law
> as unvalidated above 0.7 σ_c.

**The campaign's first quantitative law, and the core of theory T3.**

- **The variable:**

  ```
  sigma  =  (1 / spacing^2)  x  keep_fraction  x  V  x  dwell        [V.s / um^2]
  ```

- **The result:** σ separates **all 19 panels** written across Sections 12-16 —
  four sections, five areas, two probes, Λ from 234 to 325 nm, panel sizes
  1.3-2.5 µm, and every thinning geometry tried:

  ```
   146  S12 dose 20%   FAILED  wrong director      311  S14 70%      turned
   255  S13 P50        FAILED  stayed put          356  S14 80%      turned
   255  S13 R50        FAILED  wrong director      376  S16a REF     turned
   255  S13 W50        FAILED  tie                 400  S14 90%      turned
   292  S12 dose 40%   FAILED  lead +0.017         444  S14 100%     turned
  ------------------ sigma_c = 302 +- 9 ------------  444  S16b REF     turned
                                                     510  S13 FULL     turned
                                                     510  S15 REF      turned
                                                     731  S12 1.29 um  turned
                                                    1524  S16a OVER    turned
                                                    1778  S16b OVER    turned
  ```

  **14 successes above, 5 failures below, no overlap.**
- **The load-bearing point** is Section 13: three *unrelated* 50 % geometries —
  thinned along the stripes, across them, and at random — sit at **identical**
  σ = 255 with **identical** outcomes. A Fourier mechanism cannot do that; a
  local areal energy must. This is what killed T2.
- **Above threshold the purity is logarithmic:**
  `w(cmd) = 0.234·ln σ − 0.887`, **r = +0.974** over the four Section 16 panels,
  extrapolating to w → 1 at about **10 σ_c**.
- **T3, the theory this belongs to** — two independent conditions:
  1. **Selection (directional).** Each skeleton carries an intrinsic P_z
     modulation at **Q** = (2π/Λ)·n̂⊥ (C16). The coupling −∫P_z E_z is nonzero
     only when **q = Q**, so the template must be commensurate in period *and*
     direction. This decides *which* director and survives thinning at fixed
     period.
  2. **Drive (amplitude).** A→B is a ferroelastic transformation — nucleate and
     sweep twin walls against elastic misfit and pinning. That barrier is a
     **local areal energy**, so σ > σ_c. This decides *whether anything
     happens*, and it is blind to how the sites are arranged.
- **Why T2 failed:** I predicted P50 ≈ full effect because dropping columns
  preserves the period. It does — and P50 gave 2 % of full, because halving the
  sites took σ from 510 to 255. **The selection rule was intact and the drive
  was gone.** I had conflated the two conditions.
- **Why A:** 19 panels, four sections, five areas, two probes, no overlap, and
  the geometry-independence is measured three ways at fixed σ.
- **Three caveats, all real.**
  1. **σ_c is fitted to the data it explains.** The 19 panels share areas and
     probes. Section 17 is the first chance for it to *predict*.
  2. **σ lumps V with dwell.** C21's ~40 V·s single-pulse threshold says they are
     not freely interchangeable — note the lattice works *collectively* at
     10 V·s per site, four times below that.
  3. **The halo problem, T3's weakest joint.** r_eff = 625 nm is **4-9× the
     lattice spacing**, so a *smoothed* field would carry essentially no Fourier
     amplitude at q = 2π/Λ (q·r_eff ≈ 13). Yet commensuration demonstrably
     works. The pattern information must survive by some route we do not have —
     plausibly the halo is a **nucleation footprint** rather than a field kernel,
     or selection happens locally at each pulse. **This is the main thing T3
     owes an explanation for.**


### C41 — Every template period from Λ to 8Λ selects the director. The ± sign map is NOT the selection rule · **B**

> **Revised 21 Aug after IT3.** The original entry claimed *2Λ beats Λ at
> identical σ*, on IT2 (Δexcess +0.477 against +0.185) with IT1's panel C as
> support. **IT3 reverses the ordering**: in a quieter area (floor 0.140, 0/14
> flips on all three baseline pairs) the periods rank **Λ +0.401 > 4Λ +0.324 >
> 8Λ +0.161**, and the Λ-to-4Λ gap of 0.077 is *below* the 0.129 threshold, so
> those two are indistinguishable.
>
> Both orderings cannot be right. Panel-to-panel scatter within one area is
> comparable to the apparent period effect across areas, and IT2's evidence came
> from an area with a 0.23 floor where P1 sat at 0.8-1.8× threshold depending on
> which after-frame was used. **The "longer is better" claim is withdrawn.**
>
> What survives is stronger than either ordering, and it is what the entry now
> records.

**This falsifies T3's Condition 1 as written.**

- **Operation:** IT2, autonomous, area (−14, 0), Λ = 280 nm, modulation 0.210.
  Two panels with **identical σ = 600 V·s/µm² (1.99 σ_c), identical spacing
  Λ/2, identical site positions, identical commanded director (2°, both
  starting dominant at 122°)**. The only difference is the sign map:
  `sign_every` 1 versus 2, giving template period **Λ** versus **2Λ**.
- **End**, on the within-frame contrast (see C42):

  | | period | w(cmd) before | after | Δ(panel − tiles) | × 2 sd |
  |---|---|---|---|---|---|
  | P1 | Λ | 0.291 | 0.513 | +0.185 | 0.8 |
  | **P2** | **2Λ** | 0.238 | **0.752** | **+0.477** | **2.1** |

  Both ended dominant at the commanded 2°, from 122°. Populations:
  P1 `0.291→0.513 / 0.179→0.371 / 0.531→0.115`;
  P2 `0.238→0.752 / 0.219→0.069 / 0.542→0.179`.
  A second after-frame gives P1 +0.399 and P2 +0.404 — so P1's *magnitude* is
  uncertain (0.8× on one frame, 1.8× on the other) while P2 clears on both.
- **IT3, the decisive iteration.** Three panels at identical σ = 560 V·s/µm²
  (1.85 σ_c), identical spacing, identical sites, all commanded to 4° from a
  dominant of 64°, differing only in `sign_every` = 1 / 4 / 8:

  | | period | w(cmd) before → after | Δ(panel − tiles) | × 2 sd |
  |---|---|---|---|---|
  | P1 | Λ | 0.283 → 0.646 | +0.401 | 3.1 |
  | P4 | 4Λ | 0.334 → 0.619 | +0.324 | 2.5 |
  | P8 | 8Λ | 0.335 → 0.457 | +0.161 | 1.2 |

  **All three switched the dominant director 64° → 4°** — including 8Λ, which at
  n = 16 is two sign blocks of eight rows and barely a lattice at all.
- **Reading:** across IT1, IT2 and IT3, **every** template period tried — Λ, 2Λ,
  4Λ, 8Λ — turned the director to the command. T3's Condition 1 ("the coupling
  −∫P_z E_z is nonzero only when q = Q") cannot be what picks the director: it
  predicts that three of those four should have failed. But no *ordering* among
  the periods is reproducible either. What the four conditions share is the
  lattice **axis** and the areal density.
- **Independent replication:** IT1's panel C was also a 2Λ template at identical
  σ and was the strongest of its four (lead +0.436 against the on-resonance
  panel's +0.183). Different area, different floor, same ordering. That is what
  IT2 was built to test, and it reproduced.
- **Superseded:** S13's W50 failed at 2Λ, which had looked like support for
  Condition 1 — but W50 was at σ = 255, *below* threshold, so period and drive
  were confounded there. IT2 separates them.
- **Why B:** four periods across three iterations and two areas all select,
  which is a robust negative result about commensuration. What is *not*
  established is any dependence on period — the two iterations that measured it
  disagree in direction.
- **What it opens:** if the sign map is irrelevant, is the **axis alone**
  sufficient? IT4 strips the template further — two *uniform-polarity* panels
  (all +V and all −V, so the file still balances) against a period-Λ reference.
  If uniform panels select as well as alternating ones, the ± pattern was never
  the mechanism and a single row of pulses should work. If they fail, some
  alternation is needed and 8Λ was near the limit.


### C42 — Score panels against untouched tiles WITHIN one frame, not before-versus-after · **A**

**A methodological conclusion that rescued the autonomous run.**

- **The problem.** A before/after comparison carries every difference between the
  two frames. Measured on untouched film in one area:

  ```
  0079 vs 0082   floor 0.511   57 % of tiles flipped director
  0082 vs 0083   floor 0.136    7 %                              consecutive
  0079 vs 0089   floor 0.446   50 %
  ```

  0079 was taken while screening that area; the stage then visited two other
  candidates and came back. **The stage does not return to the same place** — the
  offset error is large enough that identical tile coordinates sample different
  material. Consecutive frames are four times quieter.
- **The fix.** The population vector is already normalised inside a frame, so
  compare **panel regions against untouched control tiles in the same frame**:

  ```
  Δexcess = [w(cmd)|panel − mean w(cmd)|tiles]_after
          − [w(cmd)|panel − mean w(cmd)|tiles]_before
  ```

  Each bracket is within-frame, so drift, gain, mode changes and stage
  hysteresis cancel inside it; the difference then cancels the *spatial* bias
  from tiles sitting at the frame edges while panels sit in a row. Threshold:
  2 sd of the tiles in the same frame.
- **It works through conditions that defeated the old metric.** During IT2 the
  withdrawn deflection drifted **−0.827 → −0.439 → −0.786** and the before/after
  floor came out at 0.223 with 21 % flips between the two after-frames. The
  within-frame contrast still gave a clean 2.1× result.
- **Also:** take all baselines **consecutively at the chosen area** after
  screening is finished. Never reuse a screening frame taken before a stage
  excursion.
- **Refinement (21 Aug, from the IT4 build).** The control tiles must be
  computed by *subtracting the written footprints*, not by arithmetic on one
  row's coordinate. IT2 and IT3 built the upper control band from the top edge
  of the **first** panel row, so on a 2×2 grid it began inside the second row
  and 3 of 14 tiles overlapped a written panel. Re-scoring IT3 with clean tiles
  moves the excesses by ≤ 0.022 and changes no verdict or ordering — **C41
  stands as recorded** — but the ordering was luck rather than design.
  Gridding the frame and subtracting the panels also *gains* tiles (16 against
  7) and places some of them inside the unwritten slot, at the same height as
  the panels, which is a better spatial match than an edge strip.
- **Refinement.** Every term in the contrast must be read along the *same*
  director. The tiles are now read once per distinct command, because panels
  commanded to different directors cannot share a control mean: the triad
  members are not equally populated.
- **What this corrects.** I concluded from IT1 that the sample region was "too
  weakly textured to support the direction metric" (modulation 0.19–0.21, Λ
  inconsistent). That was wrong. Consecutive frames in the same area give a floor
  of 0.136–0.183 with 0–7 % flips. The area was always measurable; the frame
  sequencing was not.


### C43 — Uniform polarity does NOT select the director. The lattice axis alone is not sufficient · **B**

> **Upgraded from C to B on re-analysis, same day.** The verdict below originally
> read "nothing switched, including the reference". That was a threshold error,
> not a result: the panels were scored on a before/after contrast but compared
> against 2 sd of the *static* spread of w across the tiles. Measured against the
> null of the statistic actually used (C45), the balanced reference clears at
> **2.8×** on the first after-frame and **3.6×** on the second, while both
> uniform panels stay flat at 0.2× / 0.0× and −0.5× / −0.6×. The contrast the
> iteration was built to make is therefore *present*, and the conclusion is
> stronger than first written, not weaker.

**Q20 answered provisionally: no.** A weakened Condition 1 survives C41.

- **Operation:** IT4, autonomous, area (0, −28), Λ = 301 nm, modulation 0.192.
  Three panels in a row at **identical σ = 601 V·s/µm² (1.99 σ_c), identical
  Λ/2 spacing, identical 256 sites, all commanded 0°**. The only difference is
  the sign map: `A` charge-balanced at period Λ; `UP` every site at +10 V; `UM`
  every site at −10 V. Per-panel balance was abandoned by design; the file
  balanced exactly, so there was no global DC.
- **The threshold was pre-registered at 0.194** from the three baselines
  *before* the write, and came out at 0.199 on the after-frame.

  | panel | design | dominant | w(cmd) | excess | × threshold (C45) | second frame |
  |---|---|---|---|---|---|---|
  | **A** | balanced, Λ | **120° → 0°** | 0.518 | **+0.184** | **2.8 ×** | **3.6 ×** |
  | UP | uniform +V | 60° → 60° | 0.221 | +0.015 | 0.2 × | 0.0 × |
  | UM | uniform −V | 60° → 60° | 0.109 | −0.035 | −0.5 × | −0.6 × |

  Threshold 0.065, being 2 sd of the leave-one-out before/after contrast over
  40 untouched tiles (C45). **Non-parametrically:** A's change exceeds the
  largest change at any of those 40 untouched locations (max |d| = 0.106) by
  1.7×, while UP's and UM's sit inside the bulk of them.

- **What is clean.** Neither uniform panel moved its director. Both held
  dominant 60° against a command of 0°, and their populations moved *towards*
  the incumbent rather than the command: w(60°) rose 0.477 → 0.547 in `UP` and
  0.554 → 0.675 in `UM`. And **|UP − UM| = 0.050 against a threshold of
  0.199** — the sign of the field made no measurable difference.
- **What is confounded.** `A` rotated its dominant director to the commanded
  0°, with w(cmd) 0.334 → 0.518 while the incumbent collapsed 0.414 → 0.152.
  But (i) its excess of +0.183 is **0.9×** the threshold, so it did not clear,
  and (ii) it started with the commanded director already at w = 0.334 against
  `UP`'s 0.205 and `UM`'s 0.143 — a head start, because the slot assignment
  deliberately matched `UP` to `UM` and gave `A` whichever slot was left.
- **The write took.** VDART afterwards: 32.4 / 67.6 % with 47 % minority in
  patches — two balanced classes, gate open. The uniform panels did not re-pole
  the film out-of-plane at frame scale, so C13's predicted local re-poling did
  not corrupt the in-plane readout.
- **Reading.** At identical σ, spacing, sites and command, the **balanced Λ
  template rotated its director and neither uniform panel moved at all.**
  Uniform polarity did not select at 2 σ_c, and the sign of the field was
  irrelevant. Taken with C41 — every period from
  Λ to 8Λ selects — the picture is that the template must *alternate*, but the
  period at which it alternates does not matter over at least a 8× range. Not
  commensuration; not nothing.
- **Why B and not A.** One area, one replicate per condition, and the reference
  arm is still confounded: `A` began with the commanded director already at
  w = 0.334 against `UP`'s 0.205 and `UM`'s 0.143, because the slot assignment
  matched the uniform pair to each other and gave `A` the remaining slot. A head
  start does not manufacture a +0.184 change against a 0.065 null, and it does
  not rotate a dominant director from 120° to 0° while the others hold at 60° —
  so the qualitative conclusion survives the confound. The quantitative
  comparison of *magnitudes* does not, and Q22 exists to fix it.
- **The area was never the problem.** I first read the wider threshold here as
  noisier film. It was not: measured in a common window on their own baselines,
  IT3's and IT4's areas have the same tile spread (0.095 against 0.098), and
  across all four iterations the spread is flat in time (0.101 → 0.100 → 0.095
  → 0.098) — neither a place effect nor a degrading probe. The apparent
  difference was **my own change to the control sampling**: IT3 used 14 tiles in
  two edge bands, IT4 used 40 gridded across the frame, and a wider spatial
  sample captures more static structure. See C45.


### ~~C44 — Rank areas by the tile spread of w(cmd)~~ · **WITHDRAWN**

**Withdrawn the day it was written.** It claimed IT4's area had roughly half
IT3's resolving power (tile sd 0.099 against 0.060) and that the area gate should
therefore rank on tile sd. The premise was false. Those two numbers came from
different control samplings — 40 gridded tiles against 14 tiles in two edge
bands — not from different film. Measured the same way on their own baselines
the two areas agree (0.098 against 0.095), and across IT1–IT4 the spread is flat
in time as well (0.101 → 0.100 → 0.095 → 0.098), so it is neither a place effect
nor a degrading probe.

The real fault was in the threshold, not the area: see C45. Ranking areas on
tile spread is not wrong, it is just close to useless, because the spread barely
varies. **The lesson worth keeping is the one that generated this mistake:
comparing two numbers computed by different procedures and attributing the
difference to the sample.**


### C45 — The threshold must be the null of the statistic being tested, measured leave-one-out · **A**

**Methodological, and it changed a verdict.**

- **The error.** Panels are scored on a before/after contrast (C42),

  `excess = [w_panel − mean_tiles](after) − [w_panel − mean_tiles](before)`

  but the threshold compared against was `2 sd of w over the tiles in the
  after-frame`. Those are different quantities. `sd(w)` is dominated by static,
  permanent spatial structure in the film — which the before-subtraction in
  `excess` removes. The test was therefore conservative by an unknown factor,
  and the factor turned out to be about three.
- **The fix.** Apply the panel statistic to each untouched tile, leaving that
  tile out of its own reference mean:

  `d_t = [w_t − mean(other tiles)](after) − [w_t − mean(other tiles)](before)`

  and take the threshold as 2 sd of `d`. Leave-one-out is not optional: keeping
  `t` in its own reference shrinks `d_t` by (1 − 1/n) and correlates the
  estimates. A panel is out-of-sample with respect to the tiles, so its null
  must be too.
- **Measured:**

  | | tiles | 2 sd of w (old) | 2 sd of d (correct) | ratio |
  |---|---|---|---|---|
  | IT4 | 40 | 0.192 | **0.065** | 0.34 |
  | IT3 | 16 | 0.128 | **0.050** | 0.39 |

  `d` has mean exactly 0 by construction, so the only thing at issue is its
  width.
- **What it changed.** IT4's balanced reference goes from 1.0× (not resolved) to
  **2.8×**, and to 3.6× on the second after-frame — so C43 turns from a null
  into a positive result. IT3's panels go from 2.8 / 2.2 / 1.0× to
  **7.3 / 5.7 / 2.5×**, which does not change C41's conclusions but does make
  them far less marginal.
- **Report the non-parametric statement too.** `max |d|` over the untouched
  tiles is a threshold that assumes nothing about the distribution: IT4's A
  exceeds it by 1.7×, IT3's P1 by 6×. When a result is close, this is the
  version to quote.
- **Corollary.** Improving a control can *raise* a threshold and hide a real
  effect, if the threshold is not the null of the statistic. Gridding the frame
  instead of using two edge bands was a genuine improvement (PITFALLS 11.3) and
  it made the test *less* sensitive, because it sampled more static structure
  into a threshold that should never have contained any.

### C46 — All four autonomous iterations re-scored against the C45 threshold · **B**

Once the threshold is the null of the statistic (C45), every iteration has to be
re-read. Frames already on disk; no instrument time. Threshold = 2 sd of the
leave-one-out before/after contrast at untouched tiles, per iteration.

| iter | panel | condition | σ / σ_c | excess | × thr | second after-frame |
|---|---|---|---|---|---|---|
| IT1 | A | Λ, keep 100 % | 1.49 | +0.254 | 2.1 | — |
| IT1 | B | keep **50 %** | 1.49 | +0.107 | **0.9** | — |
| IT1 | C | **2Λ** | 1.49 | +0.417 | **3.4** | — |
| IT1 | D | Λ, keep 100 % | **0.68** | +0.338 | **2.7** | — |
| IT2 | P1 | Λ | 1.99 | +0.226 | 3.3 | 14.4 |
| IT2 | P2 | 2Λ | 1.99 | +0.421 | 6.2 | 12.7 |
| IT3 | P1 | Λ | 1.85 | +0.364 | 7.3 | 4.4 |
| IT3 | P4 | 4Λ | 1.85 | +0.287 | 5.7 | 5.3 |
| IT3 | P8 | 8Λ | 1.85 | +0.124 | 2.5 | 0.7 |
| IT4 | A | Λ balanced | 1.99 | +0.184 | 2.8 | 3.6 |
| IT4 | UP | **uniform +V** | 1.99 | +0.015 | **0.2** | 0.0 |
| IT4 | UM | **uniform −V** | 1.99 | −0.035 | **−0.5** | −0.6 |

**An empirical negative control, found by accident.** Applying the statistic to
IT1's four panel locations across two frames *both taken before the write*
(0070 against 0069) gives 0.6, −0.7, 0.2 and −0.9 × threshold — nothing. Same
locations, same statistic, no write. The C45 threshold is therefore calibrated,
not merely derived: untouched film at the panel positions does not cross it.

**What survives, what strengthens, what breaks:**

- **C43 strengthens.** The balanced/uniform contrast is the cleanest thing in
  the table: 2.8 and 3.6 × for the balanced panel against 0.2 / 0.0 and
  −0.5 / −0.6 × for the two uniform ones.
- **C41's revision is confirmed.** Every template period from Λ to 8Λ selects,
  and the *ordering does not reproduce* — IT2 gives P2 > P1 on the first
  after-frame and P1 > P2 on the second (6.2 / 3.3, then 12.7 / 14.4). Withdrawing
  "longer is better" was right.
- **IT1 panel B, keep 50 %, is the only sub-threshold balanced panel** (0.9 ×),
  consistent with C34's density threshold sitting between 50 % and 70 %.
- **IT1 panel D switched at σ = 204 = 0.68 σ_c.** This is the first evidence
  against σ_c being a hard threshold, and it is the one row in the table that
  contradicts something previously concluded (C40).

**Why B and not A.** IT1's before and after frames straddle the withdrawn-
deflection change from −0.8 to −0.6 V, so its four rows carry an instrument
change the within-frame contrast is not guaranteed to remove — it removes static
spatial structure and frame-level gain, not a change in contact that alters
texture contrast non-uniformly. IT2, IT3 and IT4 are clean. **Panel D's
sub-threshold σ therefore needs its own experiment before C40 is touched.**


### C47 — σ_c is NOT a threshold, and the response saturates to a fixed point · **B**

**Q23 answered. This supersedes σ_c and puts C40's law in question.**

- **Operation:** IT5, autonomous, area (−14, −28), Λ = 301 nm, modulation 0.216,
  baseline floor 0.112. Three panels differing **only in dwell**, identical
  period Λ, identical Λ/2 spacing, identical 100 % density, identical geometry —
  and, critically, all three on slots with the **same starting dominant (64°)
  and the same command (4°)**, so a difference between them is σ and nothing
  else. (A fourth rung at 0.41 σ_c was planned; only three slots settled, and
  the rule dropped the *lowest* rung rather than the positive control.)

  | rung | σ | σ/σ_c | w(cmd) before → after | excess | × threshold |
  |---|---|---|---|---|---|
  | **S07** | 212 | **0.70** | 0.128 → 0.464 | +0.333 | **3.5** |
  | S10 | 301 | 1.00 | 0.102 → 0.480 | +0.376 | **3.9** |
  | S15 | 460 | 1.52 | 0.203 → 0.452 | +0.247 | **2.6** |

  Threshold 0.096 = 2 sd of the leave-one-out null over 27 untouched tiles
  (C45). **All three exceed max |d| = 0.109**, so the result holds
  non-parametrically as well. All three rotated the dominant director 64° → 4°.

- **There is no threshold.** A panel at **0.70 σ_c selected at 3.5× the null**.
  σ_c = 302 was *defined* as the σ where panels begin clearing a detection
  threshold, and C45 showed that threshold was three times too high; this is the
  direct test of what happens below it, and the answer is that selection works.
  IT1's panel D at 0.68 σ_c (C46) was therefore reporting real physics, not an
  artefact of the deflection change in that run.

- **The final state is set by the film, not the dose.** This is the more
  interesting half. Starting populations spread over 0.102–0.203 (sd **0.052**);
  final populations over 0.452–0.480 (sd **0.014**) — a fourfold *collapse* in
  spread — while σ varied by 2.2×. All three panels converged on
  **w(cmd) ≈ 0.47** from different starting points. The excess ordering
  (S10 > S07 > S15) is non-monotonic in σ and simply tracks how far each panel
  had to travel.

  That is a saturating attractor, not a graded response.

- **C40's law does not describe this range.** w = 0.234 ln σ − 0.887 predicts
  0.367 / 0.448 / 0.548 at σ = 212 / 301 / 460, against 0.464 / 0.480 / 0.452
  measured: S07 lands 0.10 **above** the law and S15 0.10 **below** it. The
  law's slope is not visible here at all.

- **Practical consequence.** σ ≈ 0.7 σ_c ≈ 210 V·s/µm² is already enough. Since
  write time = Area × σ / V, everything written above that has been paying two
  to three times over for no gain in the final state — including IT6's letters
  at 1.2 σ_c.

- **Why B and not A.** Three rungs, one replicate each, one area, and the 0.41
  σ_c rung was dropped — so we know 0.70 σ_c is sufficient and do **not** know
  what is insufficient. The matched starting dominants are the strength here;
  the missing bottom rung is the weakness. A fixed point measured at one Λ in
  one area may also be a property of this film rather than of the mechanism.




### C48 — The achievable purity is set by the site SPACING, not by the charge · **B**

**A synthesis of C39 and C47, not a new experiment. It reinterprets C40.**

Put every panel written at a known spacing side by side, using final w(cmd) —
the metric C36 §6.3 settled on, because it does not inherit the starting state:

| spacing | w(cmd) reached | σ range | source |
|---|---|---|---|
| **Λ/2** | 0.452, 0.464, 0.480, 0.452, 0.599, **0.696**, 0.757 — mean **0.557**, sd 0.126 | 212–576 | IT5 ×3, C39 ×2, IT9 ×2 |
| **Λ/4** | 0.831, 0.861 — mean **0.846**, sd 0.021 | ~4× the Λ/2 σ at equal dwell | C39 ×2 |

- **Charge does not move it.** IT5 varied σ by **2.2×** at fixed Λ/2 spacing —
  212, 301, 460 V·s/µm² — with matched starting dominants, and the final
  populations were 0.464, 0.480, 0.452: flat to sd 0.014 (C47).
- **Spacing does.** Halving the spacing takes it from ≈ 0.56 to ≈ 0.85, and the
  Λ/4 panels are also far more reproducible (sd 0.021 against 0.126).
- **Revised by IT9 (C53).** Two further Λ/2 panels reached **0.696 and 0.757**,
  well above the 0.452–0.599 the entry was written on. So the Λ/2 "ceiling" is
  **not sharp** — the mean rises to 0.557 with sd 0.126, and the gap to Λ/4
  narrows from 0.36 to 0.29. The ordering Λ/4 > Λ/2 survives; the claim that
  Λ/2 caps near 0.49 does not.
- **So the plateau in C47 is not a universal fixed point.** It is the ceiling
  *for Λ/2 spacing*. There is a different, higher ceiling at Λ/4. What saturates
  is not the film's willingness to switch but what a lattice of that pitch can
  reach.

**This is the most likely explanation of C40.** The law w = 0.234 ln σ − 0.887
was fitted across 19 panels drawn from five sections at different spacings — and
σ = V·dwell/spacing², so a finer-spaced panel automatically has a higher σ.
Spacing and σ were **collinear by construction** across that set. IT5 broke the
collinearity by holding spacing fixed and varying dwell, and the σ dependence
vanished. The r = +0.974 correlation was therefore most likely a *spacing* law
wearing σ's clothes.

**Why this matters practically — corrected.** The *dwell* cost of a lattice is
Area × σ / V, in which the spacing cancels: four times the sites at a quarter of
the dwell each. But the *trajectory* cost does not cancel, because travel between
sites has a floor and four times the sites means four times the hops. Measured on
the real builder for the UTK mask at Λ = 301 nm:

| spacing | sites | dwell each | dwell total | travel | **real total** |
|---|---|---|---|---|---|
| Λ/2 | 1188 | 0.84 s | 16.6 min | 8.5 min | **25.1 min** |
| Λ/4 | 4756 | 0.20 s | 15.9 min | 18.4 min | **34.3 min** |

The dwell halves agree to 4 %, as the identity requires; the travel nearly
doubles. So Λ/4 buys ~1.7× the purity for ~1.4× the time — a good trade, but not
a free one, and a Λ/4 write of this size exceeds the 26 min per-iteration cap and
must be split into two files.

*(This paragraph originally claimed Λ/4 was free. It is not; the error was
treating a charge identity as a wall-clock one. Second time tonight a cost model
has been wrong in the travel term — the masked-lattice overhead was 1.55× against
an assumed 1.35×.)*

**Why B and not A.** Two Λ/4 panels, both from one section and one area, against
five Λ/2 panels from two. The comparison is across experiments rather than within
one frame, which is exactly the kind of cross-condition inference C44 was
withdrawn for — the mitigation is that both C39 runs balanced position between
conditions and IT5 matched starting dominants, so neither leg rests on an
unmatched comparison. It still wants a single frame containing both spacings at
two σ each.

**The experiment it asks for.** A 2 × 2: spacing Λ/2 and Λ/4, each at low and
high σ, in one frame with matched starting dominants. The spacing hypothesis
predicts ≈ 0.49 / 0.49 / 0.85 / 0.85 — σ irrelevant at both spacings. C40 as
written predicts a rise with σ at both. One cell of that (Λ/4 at *low* σ) has
never been written, and it is the cell that separates the two.


### C49 — On virgin film a charge-balanced raster ALIGNS the family parallel to its scan lines · **B**

**The opposite sign to C26, and it reconciles C26 with its own control.**

- **Operation:** IT6 stage A. Virgin area (−14, −14), triad 2/62/122, Λ 280 nm.
  Charge-balanced raster (one pass at +9 V, one at −9 V, `start_sign` ±1) along
  the **62°** member — the strongest at the time — at Λ/2 pitch, areal dose
  129 V·s/µm². Populations measured over **80 windows** in a 10.6 × 4.0 µm box
  before and after.

  | director | before | after | change |
  |---|---|---|---|
  | 2° | 0.242 | 0.179 | −0.063 |
  | **62° — the raster direction** | 0.415 | **0.601** | **+0.186** |
  | 122° | 0.343 | 0.220 | −0.124 |

- **C26 said the opposite.** There, three **pre-poled** panels rastered along 6°
  went w(6°) 0.29 → 0.14, 0.24 → 0.10, 0.25 → 0.04: the family parallel to the
  raster was *depleted*, hard. But C26's single **unpoled** control moved the
  other way, 0.15 → 0.23, and that anomaly was recorded at the time and flagged
  as the weakest link in the IT6 recipe. It was not an anomaly. It was the
  virgin-film behaviour, measured once.
- **So the out-of-plane poling state sets the SIGN of the raster's in-plane
  effect.** Poled: depletes the parallel family. Virgin: aligns it. Five
  measurements, three one way and two the other, and the split is entirely by
  poling state.
- **Practically this is better than the recipe assumed.** The raster is a direct
  **aligner** on virgin film, reaching w = 0.601 with a 0.381 lead over a
  10.6 × 4.0 µm area in 23.5 min. That is *higher* than a Λ/2 pulse lattice
  achieves (≈ 0.49, C48) and far larger in area. The "deplete two members to
  leave the third" scheme C26 proposed is unnecessary on virgin film: one raster
  aligns directly.
- **And it is mechanistically puzzling.** Each pass of the raster is spatially
  **uniform in sign** — all of pass 1 at +9 V, all of pass 2 at −9 V — so within
  a pass there are no sign boundaries between adjacent scan lines. C43 found that
  a spatially uniform-polarity *lattice* does nothing at all. Yet this uniform
  raster produces the largest single alignment in the campaign. Either the
  continuous sweep couples through a mechanism the isolated dwells do not (C26
  already noted a raster is not a lattice), or the relevant structure is the
  line pattern at Λ/2 pitch rather than the sign pattern. This is now the
  sharpest inconsistency in the theory.
- **Why B:** one virgin area, one raster direction, 80 windows — but the effect
  is large (+0.186 on the parallel family, −0.06 and −0.12 on the others) and it
  agrees in sign with C26's independent unpoled control. What is missing is a
  second direction on virgin film, to confirm it follows the raster rather than
  favouring 62° for some other reason.
- **Retention, incidentally.** IT10b re-measured this same box about an hour
  later, after several intervening scans, before writing on it.


### C50 — A raster-aligned state is retained: unchanged over 34 minutes with the tip in contact · **B**

**The first retention measurement in the campaign.** Nothing before this had
written a state and then re-measured it later.

- **Operation:** IT6 rastered (−14, −14) along 62° and read the result at
  02:19:19 (frame 0123). IT10b, resuming on the same canvas to write its letters,
  re-measured the same box at 02:36:32 (frame 0124) and again at 02:53 (frame
  0125) before committing — intervals of **17 and 34 minutes**, with the tip in contact in LDART mode throughout
  and one intervening frame. Both measurements are 80 windows over the same
  10.6 × 4.0 µm box.

  | director | t = 0 (frame 0123) | +17 min (0124) | +34 min (0125) |
  |---|---|---|---|
  | 2° | 0.179 | 0.179 | **0.179** |
  | 62° (rastered) | 0.601 | 0.597 | **0.598** |
  | 122° | 0.220 | 0.223 | **0.222** |

  Dominant 62° at all three times; lead 0.381, 0.374, 0.376. Three time points,
  because IT10b's first attempt halted at preflight and re-measured on relaunch —
  an accident that turned one interval into two.

- **Nothing moved.** The largest change is 0.004, against a per-window scatter of
  0.13–0.25 and a C45 switching threshold of order 0.06–0.10. The aligned state
  is not relaxing on the timescale of an experiment, and the +34 min point is
  indistinguishable from the +17 min one, so it is not drifting slowly either.
- **Why this matters.** Every result in this campaign is a before/after
  comparison, and all of them implicitly assume the written state persists long
  enough to be read. That assumption had never been tested. It holds, at least
  over 34 minutes.
- **What it does not establish.** One interval, one area, one preparation method
  — and both intervals are gaps that happened to occur, not a designed test. It
  says nothing about hours or days, nothing about whether a *lattice*-written
  state (as opposed to a raster-aligned one) is equally stable, and nothing about
  fatigue under repeated rewriting. **IT9 is designed to test the lattice case
  properly**, with a panel deliberately left alone as a retention control
  alongside one that is rewritten.
- **Why B:** the agreement is far tighter than any threshold and rests on 80
  windows at each time point, but it is a single interval measured
  opportunistically rather than a designed retention curve.


### C51 — "UTK" written into in-plane super-domain orientation and read back as an image · **A**

**The rules compose. This is the campaign's device-level result.**

- **Operation:** IT6 stage A + IT10b. Area **(−14, −14)**,
  Λ 280 nm, window 1.22 µm.
  1. **Prepare.** Charge-balanced raster along 62° over 10.6 × 4.0 µm aligns the
     background to that member at w = 0.601, lead 0.381 (C49).
  2. **Verify.** Re-measured 17 and 34 min later: 0.597, 0.598. The canvas holds
     (C50).
  3. **Draw.** U, T and K as **masked pulse lattices** — one lattice generated in
     the command's rotated frame, sign alternating every row, then cut to the
     letter shapes — laid **along** the raster direction so every letter sits on
     prepared film. 1386 sites, Λ/2 spacing, σ = 367 = 1.22 σ_c, 7.2 V·s per
     site, commanded **2°** against the 62° background. Charge balance exact
     (693 sites of each sign after trimming; mean V = 0.000000).
- **End**, 89 probes on strokes against 43 between, window 1.22 µm:

  | region | w(2°) before | after |
  |---|---|---|
  | on a stroke | 0.081 | **0.483** |
  | between strokes | 0.076 | 0.157 |

  **Contrast +0.321 against a 2 σ null of 0.029 — 11.1×.** The dominant director
  lies within 20° of the command over **63 %** of stroke probes and **5 %**
  between them. Figure: `IT10b_UTK.png`.

  | letter | w before → after | gain | height range |
  |---|---|---|---|
  | U | 0.093 → 0.394 | +0.301 | 2.2 nm |
  | T | 0.051 → 0.469 | +0.418 | 15.3 nm |
  | K | 0.043 → 0.559 | +0.516 | 15.5 nm |

- **What it demonstrates.** Orientation is a **writable, readable, addressable**
  degree of freedom in this film. Two operations suffice: a raster to set a
  uniform background over microns, and a masked lattice to override it locally
  along an arbitrary shape. Nothing about the shape is special — the mask is a
  list of stroke centre-lines.
- **The prediction that failed.** The coverage fix was expected to make the three
  letters read *alike*; the gains span 0.301 to 0.516. They do **not** track
  topography — the U sits on the flattest film (2.2 nm) and gained least — but
  they do increase monotonically with position along the word, from (4.31, 2.82)
  through (6.00, 6.00) to (7.69, 9.18). That is a gradient in either the raster's
  effect or the film, and it is unexplained (Q30).
- **Out-of-plane.** VDART afterwards reads 53.7 / 46.3 % against ~30 / 70 before,
  with minority-in-patches 89 %. The gate is open (two balanced classes) and the
  in-plane readout is clean, but that is a large change in the out-of-plane state
  and the letters were charge-balanced to the site — so the **raster** is the
  likelier cause, and C13's re-poling warning applies to rasters more than to
  lattices.
- **Why A.** 89 stroke probes against 43 between, 11.1× a null measured on the
  same frames, a per-letter breakdown in which all three letters gain, a
  before-frame confirmed aligned beforehand, and a figure. The magnitude limits
  are honest and known: Λ/2 spacing caps purity near 0.49 (C48), and the strokes
  at 1.2 µm are at the resolution limit set by 4Λ.


### C52 — Two area gates measure different things: the tile spread sizes the threshold, the flip rate says whether "dominant director" is even defined · **A**

**Methodological, from IT7's halt.**

- **What happened.** IT7 halted before writing: 31 % of untouched control tiles
  changed their dominant director between two *consecutive* baselines, against a
  25 % cap. `contact_check` simultaneously reported the DART loop 19.5 kHz off
  the tracked resonance and |A| at 30.7 pm, against 40–55 pm earlier in the
  night — so the obvious reading was a degrading probe.
- **It was not the probe.** The tile spread of w(cmd), which is what sets the
  C45 threshold, is flat across five iterations:

  | iteration | sd(w) | modulation |
  |---|---|---|
  | IT3 | 0.081, 0.085 | 0.206, 0.209 |
  | IT4 | 0.099, 0.101 | 0.192 |
  | IT5 | 0.098, 0.103 | 0.221, 0.227 |
  | IT6 | 0.096, 0.097 | 0.190 |
  | **IT7** | **0.109, 0.104** | 0.210, 0.219 |

  All well under the 0.150 guard, no trend, and |S| bouncing 25–52 pm without
  direction. The readout was working normally.
- **The two gates measure different things.**
  - **sd(w)** is how much the *population* varies from place to place. It sets
    the size of the threshold a panel must clear (C45).
  - **flip rate** is how often the *argmax* changes between consecutive frames.
    It goes high when the three populations are near-degenerate, because then an
    arbitrarily small change swaps which member is nominally dominant.

  An area can have a perfectly normal sd(w) and a useless flip rate — that is
  exactly IT7's area, with modulation 0.21 and populations close enough to tied
  that "the dominant director" is not a well-defined label there. Since every
  verdict in this campaign requires the dominant director to *end on the
  command*, an area like that cannot support the experiment however quiet its
  populations are.
- **So keep both.** They are not redundant and neither subsumes the other. This
  also corrects the framing of C44's replacement: sd(w) is the right gate for
  *threshold size*, and it was wrong to imply it was the single gate that
  decides readability.
- **And it is the fourth time** a measurement complaint was nearly attributed to
  the hardware. The pattern in PITFALLS 10.2 held again: the probe warning was
  real but irrelevant, and the measured quantity said so.


### C53 — The director is REWRITABLE: driven off its member, then driven back · **B**

**Answers the question that decides whether this is a memory or a fuse.**

- **Operation:** IT9, area (−28, −12), triad 4/64/124, Λ 301 nm, σ = 1.3 σ_c,
  Λ/2 spacing, 32 control tiles. Two panels written identically in stage 1, then
  **only one rewritten** in stage 2, commanded back toward the director it
  started from. The other was left in place as a retention control, so that a
  return to the original could not be confused with relaxation.

  | | stage 1 | stage 2 | scored toward |
  |---|---|---|---|
  | **RW** | 64° → 124° (commanded 4°) | **124° → 64°** | w(64°) = 0.757, excess +0.195 = **3.8×** |
  | RW, old command | | | w(4°) = 0.162, excess −0.024 = −0.4× |
  | **HOLD** | 4° → 64° (commanded 64°), w 0.696, 7.7× | untouched | w(64°) = 0.609, excess +0.300 = **5.9×**, dominant still 64° |

- **Reversible.** RW was driven off 64°, then back onto it by a second lattice,
  and its population along the *first* command collapsed to 0.162 as it went. So
  a written state is not a terminal change — the same tool that sets it can
  reset it.
- **Retained, with a caveat that matters.** HOLD kept its dominant director, but
  its amplitude fell **0.696 → 0.609**, a drop of 0.087 that is comparable to
  the threshold itself. Compare C50: a *raster*-aligned state gave 0.601 →
  0.597 → 0.598 over 34 minutes with no measurable decay. **A lattice-written
  state may therefore be less stable than a raster-aligned one** — which is the
  more interesting reading and is directly Q29.
- **Two honest limits.**
  1. **HOLD was not strictly left alone.** The panels sit 3.76 µm apart with
     1.83 µm halos, so their footprints are separated by about **0.1 µm**.
     Stage 2's write on RW was effectively adjacent to HOLD's edge, and the
     0.087 decay cannot be separated from perturbation by that write. The design
     should have spaced them further apart; two slots was the constraint.
  2. **One interval, one area, one panel per role.** HOLD and RW also had
     *different* starting dominants and commands (4° → 64° against 64° → 4°), so
     they are not two arms of a matched contrast — each measures its own thing.
- **Why B and not A.** The reversal itself is clean and large (3.8×, with the old
  command's population collapsing). The retention half is confounded by
  adjacency, so "non-volatile" is not established — only "dominant held while
  amplitude fell".
- **Next.** Cycle it: ten writes alternating between two members, watching for
  fatigue; and repeat the retention arm with the control panel far from any
  second write.


### C54 — The commanded director is not always the one that wins · **B**

**A limit on the recipe that four iterations of single-write panels could not see.**

- **Operation:** IT9 stage 1. Two panels, same σ, same spacing, same geometry,
  each commanded 60° from its own local dominant — the configuration every
  successful panel has used.

  | panel | started | commanded | ended | w(cmd) | excess |
  |---|---|---|---|---|---|
  | HOLD | 4° | **64°** | **64°** ✓ | 0.696 | +0.391 = 7.7× |
  | RW | 64° | **4°** | **124°** ✗ | 0.369 | +0.187 = 3.4× |

- **RW's population along its command rose enough to clear the threshold (3.4×)
  yet its dominant went to the third member.** The lattice displaced it from
  where it started but did not steer it to where it was told. So "clears the
  threshold" and "ends on the command" are separable outcomes, and only the
  second is what a patterning application needs.
- **This is why C51's letters work at 63 % on-target rather than 100 %.** The
  same partial steering, measured per probe instead of per panel.
- **Two candidate explanations, not separated here.** Either something specific
  to the 4° command — it is the member nearest the fast scan direction, and the
  streak artefact also lives near 0° (C-note on `dir_power`) — or simply that a
  panel starting *on* 64° behaves differently from one starting on 4°. IT9 has
  one panel per condition and cannot tell them apart.
- **Consequence for the record.** Every earlier iteration reported "switched" on
  a criterion that required *both* excess and on-target dominance, so no earlier
  conclusion is affected. But IT9's own stage-1 print labelled RW "SWITCHED" on
  excess alone, which overstates it; the verdict block checked dominance properly
  and is unaffected.
- **Next.** Command the *same* starting director to each of the other two
  members, twice each, in one frame. If 4° is always the loser the cause is the
  direction; if the loser follows the starting member it is the history.


## 2. Open questions, and what would settle each

**Closed since 14 August.** Q1/Q1b — *can anything produce ±60° triad
switching?* — **yes**, and it is the pulse lattice, not the trajectory. C23
found it, C29 replicated it 9/9, C30 showed all three Δ are equally accessible.
Q2 — *does the surround control the centre?* — subsumed by C34: there is no
sub-threshold regime in which surround effects could be economised.

| # | Question | Status | Decisive test |
|---|---|---|---|
| ~~Q8~~ | ~~Where is the density knee?~~ | **answered: 50–70 %** | C37. 70 % rotates (4/4), 50 % does not (0/3), both on equivalent 60° rotations |
| ~~Q9~~ | ~~Does over-driving help?~~ | **answered: yes** | C39. Λ/4 reaches w(cmd) 0.83-0.86 against Λ/2's 0.45-0.60, 4/4, positions swapped. Per-pulse efficiency remains unresolved |
| **Q15** | **Is σ really the drive variable, or is it site count?** | **open, top priority** | Section 17 panel B: half the sites at twice the dwell, same σ. If it turns, count and charge are interchangeable |
| ~~Q16~~ | ~~Is commensuration with Λ required?~~ | **answered: NO** | C41. 2Λ beats Λ at identical σ, replicated across two areas. T3 Condition 1 is falsified |
| ~~Q18~~ | ~~Does a longer template period keep winning?~~ | **answered: no ordering reproduces** | IT3 gives Λ > 4Λ > 8Λ, IT2 gave 2Λ > Λ. All periods select; period itself is not a controlling variable at this precision |
| ~~Q20~~ | ~~Is the lattice axis alone sufficient?~~ | **answered: NO, provisionally (C43)** | uniform polarity did not select at 2 σ_c and polarity sign was irrelevant. The template must alternate; the period at which it alternates does not matter (C41). Grade C — the reference arm was sub-threshold and confounded |
| ~~Q23~~ | ~~Is σ_c a hard threshold at all?~~ | **answered: NO (C47)** | 0.70 σ_c selects at 3.5× the null, and the final population saturates at 0.47 regardless of σ over 0.7–1.5 σ_c |
| ~~Q24~~ | ~~Can the raster's destination be predicted?~~ | **answered on virgin film (C49): it aligns PARALLEL to the raster.** On pre-poled film C26's bifurcation — two panels with identical starting populations going to opposite members — stands unexplained | a second raster direction on virgin film, to confirm the director follows the scan lines rather than favouring 62° for another reason |
| **Q28** | **Why does a spatially uniform-sign RASTER align strongly (C49) when a spatially uniform-sign LATTICE does nothing at all (C43)?** Each raster pass is one polarity throughout, so it has no sign boundaries between adjacent lines — yet it produced the largest alignment in the campaign, while uniform lattices gave 0.2× and −0.5× | **open — the sharpest contradiction in the theory, and the first thing to resolve** | a raster with sign alternating between ADJACENT LINES against one alternating only between passes; and a lattice at the raster's line pitch. If the continuous sweep is what matters, the two rasters agree and the lattice fails; if the sign structure is what matters, the alternating-line raster wins |
| **Q25** | **Where is the lower bound?** 0.70 σ_c works; the 0.41 σ_c rung was dropped when only three slots settled | **open** | a ladder at 0.15–0.7 σ_c with matched starting dominants. Cheap, since low σ means short dwells |
| ~~Q26~~ | ~~Is w(cmd) ≈ 0.47 a property of the film or of the mechanism?~~ | **largely answered (C48)**: it is the ceiling for **Λ/2 spacing**. Λ/4 reaches 0.85 | what remains is whether Λ/8 goes further, and where it stops |
| **Q27** | **Is the purity ceiling set by spacing alone, independent of σ?** C48 infers this across experiments; one cell (Λ/4 at low σ) has never been written | **open, and device-relevant** | a 2 × 2 in one frame: spacing Λ/2 and Λ/4 at low and high σ, matched starting dominants. The Λ/4 arms cost about 1.4× the Λ/2 arms in wall clock — the dwell is spacing-independent but the travel is not
| **Q21** | **At what alternation does selection die?** C41: Λ to 8Λ all select. C43: uniform does not. The boundary is between 8Λ and uniform | **open, top priority** | sweep `sign_every` from 8 to n/2 to uniform at one σ, scored against the C45 threshold |
| **Q31** | **Why does a panel sometimes end on the third member rather than the commanded one (C54)?** RW cleared the threshold at 3.4× and still went to 124° instead of 4° | **open — it is the limit on patterning fidelity** | command one starting director to each of the other two members, twice each, in one frame. Direction-specific or history-specific |
| **Q30** | **Why do the three letters gain unequally (+0.301, +0.418, +0.516) when coverage is uniform?** It tracks position along the word, not topography | **open** | write the same word twice with the letter order reversed. If the gradient follows position it is the film or the raster; if it follows the letters it is the mask |
| **Q29** | **Does a lattice-written state decay where a raster-aligned one does not?** C50: raster flat over 34 min. C53: lattice fell 0.696 → 0.609 in ~22 min, but confounded by an adjacent write | **open, sharpened** | IT9: a panel written and left alone beside one rewritten, both read on the same frames. Then longer intervals |
| **Q22** | **How much of `A`'s advantage in IT4 was its head start?** It began with w(cmd) = 0.334 against 0.205 and 0.143 | **open** | two balanced replicates on slots matched to the uniform panels' starting dominant, so reference and test start from the same state
| **Q19** | **If not commensuration, what selects the director?** | open — the theory has no Condition 1 | candidates: the lattice **axis** alone; the strain field of a row of like-sign pulses; a wall-motion bias along the write direction |
| **Q17** | **How does the pattern survive a halo 4-9× the spacing?** | open — T3's weakest joint | needs a mechanism, not a measurement, first. Candidate: r_eff is a nucleation footprint, not a field kernel |
| **Q13** | **How much of our panel-to-panel scatter is just unequal starting states?** | open, and it contaminates everything before Section 16 | Section 16 fixes the task per panel by construction. If its within-condition scatter is much smaller than Section 14's, the answer is "most of it" |
| **Q10** | **What mechanism gives a threshold that is blind to thinning geometry?** | open — no model on the table survives C34 | Q8 and Q9 first. A sharp ρ_c plus a known behaviour above it constrains the mechanism far more than another pattern variant would |
| Q11 | How small a region can be aligned? C33 says the *metric* dies at ~4Λ, below 2 r_eff | open, and blocked on the observable | Re-score the Section 12 sub-micron panels with the real-space difference statistic against a *commanded-direction* version of it. Needs a metric that is directional and defined at 9 px |
| Q12 | How large? C32 saw no fall over 3.6× in area | open | Only worth doing after Q8/Q9: at 1/area cost scaling, a genuinely large region is expensive, and the answer changes if over-driving works |
| Q3 | Is the sample generally orbit-pure, or are our areas unrepresentative? | open | `[PROBE.2]`: VDART at 4–5 locations ≥ 50 µm apart. Campaign reference is 21–36 % |
| Q4 | Which (V, t) opens the gate, and does r_eff scale with amplitude or dwell? | open | sparse ladder, ≥ 1.5 µm spacing, 2×2 or 3×3 |
| Q5 | Does the written state survive 10 h? | partly answered — C29 has 8/9 at +90 min | repeat with a relocatable fiducial, or accept the 90 min result |
| Q6 | Do the FFT and structure tensor disagree because one is wall-weighted? | **worse than unresolved** — the real-space orientation metric disagreed with the FFT by 2–10× on virgin film and saturated at exactly 0.000/1.000 in small boxes | do not use the real-space *orientation* metric for populations. The real-space *difference* statistic (C33) is a different quantity and is sound |
| Q14 | Does the streak artefact at 0° (C36) contaminate any earlier conclusion whose commanded direction was near 0°? | open | the streak index is cheap. Score it on every frame behind C23, C29 and C30, all of which used commands near 0° in some panels |
| Q7 | Is the vertical-only two-class reduction hiding a family? | untested | vector PFM: two lateral scans with the sample rotated 90° |

---

## 3. Operational lessons — mistakes that cost real time

Each of these produced a wrong or uninterpretable result once. All now have
guards in the notebook.

| Lesson | Symptom it produced | Guard |
|---|---|---|
| **The stage moves.** A baseline from a different area makes every region look "switched" | 13 Aug: core *and* both controls read 0.49–0.69 switched. Height correlation between the frames was **+0.04** | `change_map` compares height maps and stage offsets, and refuses the pair |
| **Register on smoothed height.** Raw height lets phase correlation lock onto pixel noise | spurious 449–625 nm shifts where the true shift was (0, 0) | `register` Gaussian-filters first; warns when the correlation peak < 0.30 |
| **A control region at the frame edge is not a control** | a 0.9 µm edge strip read Λ = 95–179 nm and anisotropy 105–278, i.e. noise, and "changed" more than the written core | band geometry with two flanking strips, each ≥ 0.55 µm inside the frame; `[0.3]` floor-checks the controls themselves |
| **Record the write-end time, not the write-start time** | retention frames landed at +29/+34/+44 min instead of 0/+10/+40, because `run_traj` sleeps for the whole write | `t_write` is set after `run_traj` returns |
| **`orbit_balance` needs a VDART frame** | `[GATE.1]` scored an LDART frame and reported the *in-plane* sign balance as "51 % up-orbit" | raises if the drive frequency is in the lateral band |
| **An up-orbit *fraction* is meaningless on a unimodal map** | "3.5 % up-orbit" was 252 clusters of median 1 px — a φ₀ fit tail, not domains | `orbit_balance` reports \|⟨e^iφ⟩\| and the minority patch structure |
| **Odd cycle counts leak DC** | H = 3.0 µm at 20 nm pitch → 75 cycles → mean bias +0.063 V | `even_cycles()`; `run_traj` refuses \|mean V\| > 0.01 |
| **`dir_power` silently crops to `min(shape)`** | every wide control band ever passed to it was scored over a **square at its left end**. A 9.0 × 1.2 µm band at 39 nm/px became a 1.2 × 1.2 µm box — 13 % of the band. This is what voided Section 11 (C35) | `sq_power()` and `ctrl_tiles()` build square windows explicitly; `dir_power` now prints a warning before cropping |
| **A readout window has *two* independent size floors** | Section 12's sub-micron panels returned nan, and my first Section 13 draft used a 1.15 µm window holding **3.5 periods** at Λ = 325 nm | `window_check(w, px_nm, lam_nm)` checks ≥ 24 px **and** ≥ 4 periods. Section 13 *derives* the window from measured Λ rather than fixing it |
| **Never hard-code geometry from a dry run** | three experiments so far: `[9.1]`'s dry-run `N_SIDE`, `[12.1]`'s 2.7 µm dose-row pitch (halos overlapped in 6 of 12 Λ×angle cases), and the fixed window above | every dimension in `[13.1]`+ is solved from the measured Λ, and `solve_layout` refuses a layout that does not fit rather than writing a broken one |
| **Compare panels in a *matched* window** | reading each panel in a window scaled to its own size confounds size with the FFT's angular resolution (~1/radius in px). Section 12's size axis looked like +0.223 vs +0.265 in own-size windows and +0.325 vs +0.265 in a matched one | one `WIN_UM` per section, applied to every panel and every control tile |
| **Choose the reference frame by coverage, not r12 alone** | `[12.1]` picked LDART_0022 (r12 0.93) which had tracked **0 %** of its rows below y = 2.5 µm — exactly where the dose row sat. The wall ranking there came off untracked lines | `pick_ref()` applies the r12 gate first, then ranks by tracked coverage **over the regions that will actually be used** |
| **`tune_and_verify` did not carry the scan offsets** | its probe frame was taken wherever the stage was left. In Section 12 that put LDART_0019 on Section 11's written area | `xoff_um`/`yoff_um` are forwarded to `setup_scan`; `[13.1]` sets the offset *before* tuning |
| **Derive a prediction, do not assert it** | I predicted P50 ≈ 0.95 × FULL because dropping columns preserves the sign period. But a structure-factor amplitude scales with the **number of sources**, so P50 is 0.5× like every other half — the "decisive" P50-vs-R50 comparison was not a discriminator between T1 and a correctly formulated T2 at all | write the prediction as an *expression* in the quantities the arm changes, not as a number per arm. The experiment was still worth running: it found the threshold |
| **A floor from one box is a floor from one place** | Section 12's control read ±0.014 over six tiles; Section 13's read ±0.049 with one edge tile at 0.108 | `ctrl_tiles()` tiles the band and the floor is the max of \|control Δ\| and \|b1 − b2\| across all tiles |
| **The order of the site list sets the write time** | `lattice_panel` selected sites by sign, so it returned all `+` then all `−` and the tip crossed the panel between every pair of pulses. An 870-site ladder came to **62,054** trajectory points — **41.4 min** — where a serpentine path needs 30,459 and **20.3 min** | `lattice_panel()` sorts serpentine (row-major, alternating direction) *after* selection, so the site set and charge balance are untouched. `[14.1]`/`[15.1]` print the travel overhead and warn above 2× |
| **Score direction, not Δ(angular power)** | Section 14 was declared void because one streaky baseline moved its floor to 0.199. On direction the same data give 4/4 rotations | C36. The population vector is a within-frame ratio; report the dominant director and the lead |
| **Streaks look like superdomains at 0°** | `LDART_0035`: streak index 0.115 against 0.060–0.077, and control-band w(0°) = 0.569 against 0.398–0.462 | scan lines run along x, so line noise lands on the q_y axis = director 0°. Compute the streak index on untouched film before trusting any command near 0° |
| **Take THREE baselines** | with two there is no majority when they disagree, and Section 14's two disagreed about the starting director in **all four** panels | `[14.1]`/`[15.1]`/`[16.1]` take three; `pick_ref` votes; the delta is scored against `F_REF`, not against whichever frame came last |
| **Choose the commanded director PER PANEL** | Section 15's Λ/4 panel already had the commanded director dominant, so its spectacular w = 0.851 was a sharpening while its Λ/2 control performed a real 60° rotation. The one comparison the section existed to make was void | measure each panel's own local dominant director in its own readout window, then command 60° from *that*. Section 16 does this |
| **Read the commanded angle off the trajectory file** | a triad re-fit is only defined mod 60°, so it can permute the index→angle map (C31) | recover it from the written lattice's nearest-neighbour bond directions; exactly one of the two lattice axes can be a triad member, because 90 is not a multiple of 60 |
| **A rotated panel is smaller than its bounding box** | `solve_grid` sized panels so that the *bounding box* exceeded the readout window, but the written region is a square **rotated** by the command. An axis-aligned window of side `W` fits only if `W·ANG ≤ L = (n−1)·spacing` — the old rule was looser by `ANG²`, up to 1.93×. Section 15's window overhung its lattice by 0.05 and 0.15 µm; one Section 16 panel failed the correct rule by 0.01 µm | `solve_grid` now sizes on `W·ANG + 2·margin ≤ L` and returns `side` alongside `ext`. `[16.1]` prints `side` against `W·ANG` per panel |
| **The commanded angle sets the cost** | pulses go as `n²` and `n` as `W·ANG/spacing`, so a Λ/4 panel is **576** pulses commanded to 4° and **1024** commanded to 64°. Section 16's 2×2 came to 1664 pulses — 35 min of continuous writing, where losing tracking partway would cost the whole experiment | `[16.1]` picks the cheaper rotation sense explicitly (C30 says the senses are equivalent, so it costs nothing), and the section is **two runs of one replicate** at ~16 min each rather than one run of two |
| **A toolkit function can be shadowed by a section-local one** | `[11.1]` defines `lattice_sites(centre, ang, n)` and `[8.2]` defines `build_lattice(cmd_map, fname_tag)` — both names I reached for in the toolkit. Running those sections first would silently rebind them with incompatible signatures | toolkit names are audited against every `def` in the notebook (47 exports, 0 shadowed); `[14.1]`/`[15.1]` open with an `inspect.signature` guard naming the cell to re-run |
| **Pulse-count balance ≠ charge balance** | ladder checkerboard left 88 V·pt net | exhaustive sign search: zero charge, both polarities in every row and column |
| **A local ring reference sits inside a 625 nm halo** | `pulse_discs` under-reported every pulse | far-field reference (> 750 nm from every site) |
| **Report coverage over the region, not the frame** | "6–13 % coverage" was really 48–91 % | fixed |
| **Filter the session log to the current run** | the retention table silently mixed two areas | `_SESSION_MARK` |
| **`gen_center_out_raster` discards the sign of `v`** | `v = -7` and `v = +7` produced byte-identical files; every write started at +V | `start_sign` parameter added |
| **A control must sit outside the pulse HALO, not just outside the footprint** | the first `[2.1]` put both control strips inside the 625 nm halo of the edge pulses, so neither was a control | `[2.1]` derives the regions from the measured lattice extent + `R_HALO` and refuses an unusable geometry |
| **"Reopened the gate" is not "broke the strain"** | two turns spent believing hypothesis (c) had been tested when only the out-of-plane half had been touched | C20; the two readouts are now scored separately |
| **A skipped positive control makes a null ambiguous** | `[PROBE.1]` skipped, so a null ladder could not distinguish recipe from hardware | `pulse_discs` prints a hardware verdict on a complete null |

---

16. **Run the positive control BEFORE the experiment, not after the null.**
    §5 item 3 had said for days that no positive control existed and that
    `[PROBE.1]` had never been run. A nine-condition, ~70 min experiment was then
    designed and executed without one, and its null turned out to be a hardware
    fact rather than a physics result. `[WGATE]` now exists and costs ~6 min.
17. **A treatment that fills the frame cannot audit itself.** R4's 576 pulses left
    no area beyond 1.3 µm of a site, so the halo test returned `nan` — the
    experiment could not detect its own failure. Always leave far-field space.
18. **Charge per pulse is |V| × dwell, and 25 points is 1 second.** `PULSE_N = 25`
    at 10 V is 10 V·s, four times below the C21 threshold. This is the second time
    a lattice was dosed below a threshold already recorded in this file (see C20's
    8 V·s). Compute the charge and compare it to C21 before running.

## 4. Numbers worth not re-deriving

**Film and texture**

| quantity | value | source |
|---|---|---|
| film triad `FAM_FILM` | **2° / 62° / 122°**, within ~5° in 8 areas | C31 |
| lamellar period Λ | 231–410 nm across areas; **280 nm** in the (12,15) area, **234 nm** in (0,15) | C2, S12, S13 |
| modulation depth | virgin 0.17–0.25; poled ~0.53; < 0.10 means no texture to rotate | C31 |
| single-pulse radius r_eff | **625 nm** | C11 |
| charge threshold to rotate a patch | ~**40 V·s** | C21 |

**The working recipe (C23/C29/C34)**

| parameter | value | why |
|---|---|---|
| spacing | **Λ/2**, so the sign period is Λ | matches the lamellar period it is templating |
| sign pattern | alternates by **row**, stripes running along the commanded director | C23 |
| bias × dwell | **10 V × 1.0 s** = 10 V·s per site, `PULSE_N = 25` at 0.02 µm / 0.5 µm·s⁻¹ | tip ceiling is ±10 V |
| density | **≥ 70 % of full**; below 50 % it fails outright | C34, C37 |
| net DC | exactly zero per panel | C13 |
| expected final w(commanded) | **0.41–0.85**; lead over the runner-up +0.10 to +0.75 | C37, C38 |
| best in-plane purity reached | **w = 0.851** at Λ/4 spacing | C38 |
| control floor on the lead | 0.087 (S14, 6 tiles) to 0.200 (S13, 7 tiles) | C36 |
| untouched-film director flips | 0/6 tiles (S14), 1/7 (S13), 1/14 (S15), 2/6 (S12) | C36 |
| streak index, healthy frame | 0.009–0.077; **0.115 is a bad frame** | C36 |

**Readout constraints**

| quantity | value | source |
|---|---|---|
| minimum window | **≥ 24 px AND ≥ 4Λ** — at Λ = 280 nm that is 1.18 µm | C33 |
| margin, window edge to written edge | ≥ one spacing + 0.1 µm | §3 |
| typical floor (tiled control) | 0.014 (S12, mid-frame band) to 0.108 (S13, edge band) | S12, S13 |
| `tracking_rows` cut | `max(10 kHz, 4 × MAD)`; healthy frames 100 % | §3 |
| DART bands | LDART 650 ± 200 kHz, VDART 350 ± 200 kHz | C4 |

**Costs, measured**

| experiment | pulses | writing time |
|---|---|---|
| Section 12 (7 panels, size + dose) | 866 | 14.4 min |
| Section 13 (4 arms, decimation) | 640 | 10.7 min |
| Section 14 (4 densities) — planned | 490–870 | 11–20 min |
| Section 15 (Λ/2 vs Λ/4) — planned | 544–832 | 11–17 min |
| one 256 px frame at 1 Hz | — | 4.3 min |

**Writing time is not pulses × dwell.** At `PULSE_N = 25`, 0.02 µm steps and
0.5 µm·s⁻¹, one pulse is exactly 1.0 s of *dwell* — but the tip also has to
travel between sites, and that overhead runs **1.25–1.40×** for a serpentine
path over a Λ/2 lattice. Multiply the pulse count by ~1.35 for a real estimate.
A site list ordered by sign instead of position gives **2.85×** — see §3.

## 5. What we have *not* achieved

1. ~~Setting the in-plane superdomain direction on command.~~ **Achieved** —
   C23, replicated 9/9 in C29, and rewritable (C24, C30).
2. **Writing in-plane order for less than full areal density.** Closed
   negatively by C34. Every route we had — wall masking, mismatch masking,
   dose reduction, perimeter-only — is a thinning, and thinning does not work.
3. **A mechanism.** We have a rule, a density threshold between 50 % and 70 %,
   and no model. Both linear-response candidates are refuted (C34). This is
   still the main theoretical gap, and it is now better constrained: whatever
   the mechanism is, it must be insensitive to *which* sites are removed and
   must switch on between half and three-quarters of full density.
4. **A lower size limit.** Not measured, and not measurable with the present
   metric (C33). Writing demonstrably acts at 0.35 µm; whether it *orients*
   there is unknown.
5. **An upper size limit.** No fall over 3.6× in area (C32), but the 20× ladder
   was never run and cost scales as area.
6. **Selectability by trajectory.** The trajectory consolidates what a lattice
   has set and cannot steer against it (C28). Still C-grade, n = 2.
7. **Type-(b) or type-(c) transitions identified as such.** We move population
   between directors; we have never shown *which* alphabet transition does it.
8. **A positive control run before every pattern experiment.** `[WGATE]` exists
   and was the fix for the probe #3 disaster (C22), but Sections 6–15 were all
   run without it. It has been cheap luck that the tips were writing.
9. **A clean over-drive comparison.** C38's Λ/4 panel is the purest state we
   have produced and the least interpretable result we have; Section 16 exists
   to fix it.
10. **Confidence that commands near 0° were never contaminated by streaks.**
   C36 found the artefact on 21 August. Nothing earlier was screened for it.

---

## 6. Readout method, measured 27 August (offline, no instrument time)

All of this came from frames already on disk. It is method, not physics, but it
changes what the next measurements can claim.

### M1 — Resolution: the 12 um working frame cannot see the nano-domains it scores · **A**

- **Operation:** the toolkit's own `signed()` and `period()` on real LDART
  frames at three scan sizes.

  | frame | nm/px | px per lamellar period | 1.26 um director windows across |
  |---|---|---|---|
  | 12 um / 256 px | 46.9 | **6.4** | 9.5 |
  | 5 um / 256 px | 19.5 | **15.4** | 4.0 |
  | 2 um / 256 px | 7.8 | **38** | 1.6 |

- **Reading:** the campaign's entire director statistic is computed at 6.4 px per
  period, where individual lamellae are unresolved speckle. That is fine for a
  population vector and useless for watching a wall move. **5 um / 256 px is the
  operating point that does both**: it resolves lamellae and still fits ~4
  windows, so a 5 um frame centred on a 2.4 um panel leaves a ~1.3 um untreated
  annulus and is self-referencing. At 2 um exactly ONE window fits, so the
  C42/C45 machinery does not exist there and the frame is structure-only.
- **Falsified by:** a lamellar period materially different from ~300 nm, which
  would move every figure in the table.

### M2 — Frame-to-frame registration is good to a few nm, and an excursion does NOT lose the spot · **B**

- **Operation:** normalised Height cross-correlation, plane removed, Hanning
  windowed, between real frames. Height is the right channel because writing does
  not change topography.
- **End:**
  - consecutive same-offset frames: **1-11 nm** drift at 12 um, **37-74 nm**
    (0.12-0.25 Lambda) at 5 um, 28 nm at 2 um;
  - commanded stage moves are recovered to **0.5 %** (a 4.00 um move read as
    3.98 um, a 2.00 um move as 2.02 um);
  - frames at the same nominal offset **separated by an excursion elsewhere**:
    residual shift **< 25 nm**, with peak-to-background 71 +- 45 over 20 pairs —
    *better* localised than the consecutive pairs (49 +- 34).
- **Reading:** `HANDOFF_1` §5's "the stage does not return to the same place
  after an excursion" is **not a lateral-position effect**. Position is
  reproduced to better than one pixel. The 0.45-0.51 disagreement in lead and
  50-57 % tile flips after an excursion must come from tune, contact or channel
  state instead. One candidate eliminated by measurement rather than argument —
  and it is what makes zoom-in/zoom-out readout viable at all.
- **Caution against over-reading:** a first pass at this reported "zero shift,
  low correlation, therefore decorrelated and the spot is lost". The peak-to-
  background ratio says the opposite. **A correlation peak at zero lag means
  nothing until you check it against the background** — with a windowed
  correlation, zero lag is where an uncorrelated pair peaks by construction.
- **Falsified by:** a pair of same-offset frames across an excursion whose
  Height correlation peaks at a large lag with high peak/background.
- **A live example of the explanation being wrong while the practice is right.**
  Every driver prints, when it discards a screening frame: *"the stage moved away
  and back after it, and OFFSET HYSTERESIS made it disagree with consecutive
  frames by 0.45-0.51 in lead and 50-57 % in flips."* The disagreement is real
  and discarding the frame is correct. The stated cause is not: M2 measures the
  residual lateral offset across exactly that kind of excursion at **under
  25 nm**, so the frames are looking at the same film. Whatever moves the lead by
  0.45 is in the tune, the contact or the channel, not in the stage position.
  The remedy survives the correction because it does not depend on the reason --
  but anyone acting on the stated reason would go and improve the stage, which
  is measurably not the problem. Left in place deliberately rather than reworded
  mid-session; the comment should be corrected when the drivers are next
  touched.

### M3 — These `.ibw` arrays are indexed [x][y], not [y][x] · **A**

- **Operation:** IT9's screening frames command `YOffset` changes of exactly
  −2.00 and +4.00 um at constant `XOffset`. Cross-correlating Height puts those
  shifts on **array axis 1** (−2.02, +3.98 um) with 0.00 on axis 0.
- **Reading:** index 0 is X (fast scan), index 1 is Y (slow scan). The toolkit's
  own functions are self-consistent and reproduce `FAM_FILM` reliably, so this
  is **not** a campaign error — it is a trap for any *new* analysis code, which
  would silently return (90 deg − theta) for every angle. Assert the convention
  in any new registration or angle routine rather than assuming it.
- **Falsified by:** a commanded X-only move that appears on axis 1.

### M4 — Travel time must be added, not multiplied · **A**

Superseded the ~1.35x rule in §4. Travel is **~2300-2800 points per 256-site
Lambda/2 panel** (1.5-1.9 min), fixed by geometry; dwell points scale with dose.
The measured overhead therefore ran **1.285x at dwell 1.48 s and 1.533x at
0.48 s**. See `PITFALLS.md` §19.2 for the per-iteration table. Gate on the built
trajectory regardless.

### M5 — The area gate's own input is not reproducible across visits · **B**

- **Operation:** IT7 was launched, screened (0,0) on the new stage position, was
  killed before any write, and relaunched 18 minutes later. Both visits took a
  fresh LDART tune and a single 12 um / 256 px frame at the same nominal offset.
- **End:** triad modulation at the SAME nominal offset (0,0), three visits
  across ~35 minutes, each with its own fresh LDART tune and a single
  12 um / 256 px frame:

  | visit | modulation | streak | gate at 0.180 |
  |---|---|---|---|
  | 15:31 (IT7 launch 1) | **0.208** | 0.012 | passed |
  | 14:49 (IT7 launch 2) | **0.168** | 0.004 | REJECTED |
  | 15:08 (IT11) | **0.194** | 0.016 | passed |

  Range 0.168-0.208, i.e. +-0.020 about ~0.19, with the 0.180 floor sitting
  inside it. Two of three visits passed and one did not, on the same film.
  Neighbouring (-2,0) read 0.229 and 0.201 on two visits (Lambda 261 then 430),
  so the scatter is not specific to one position.
- **Reading.** The quantity the area gate keys on has visit-to-visit scatter
  comparable to the distance between "viable" and "rejected". So MOD_MIN is not
  a property of the film at that position; it is a property of the film, the
  tune and the frame together. Two consequences:
  1. **An area rejected once is not established as unusable**, and an area
     accepted once is not established as usable. IT7's first launch would have
     written at (0,0); its second refused to.
  2. **A rejected screening frame is weak evidence.** M2 showed relocation is
     good to under 25 nm, so this is not a different patch of film. The likelier
     cause is the fresh tune each visit changing what `signed()` returns -- which
     is the §8 rule again: exhaust the measurement before the material.
- **Lambda is worse.** The same three visits to (0,0) returned per-member
  Lambda of 301/354/482, 301/354/482 and 301/354/354 -- medians 354, 354, 354,
  which is stable -- but (-2,0) gave medians **261 then 430** on two visits, a
  factor of 1.6. Since Lambda sets the readout window AND the halo, and those
  set how many panels fit beside enough control tiles (M7), an unstable Lambda
  estimate propagates straight into the experiment design.
- **What would settle it:** three consecutive frames at one offset without
  re-tuning between them, then a re-tune and three more. If the scatter lives
  across the re-tune and not within the triplet, the gate should be measured on
  a tune-averaged frame, or the floor lowered and the flip rate relied on
  instead (C52 already says the flip rate, not the spread, decides whether
  "dominant director" is defined).
- **Not yet actionable on:** I did not change MOD_MIN. Relaxing a guard needs
  the owner asking and the quantity measured (PITFALLS 13), and only one pair of
  readings exists.

### M6 — On this stage position the triad is rotated 17 deg from FAM_FILM · **B**

- **Operation:** rigid triad fit on the first frames after the 27 Aug coarse-stage
  move and probe change, at two offsets.
- **End:** members **19/79/139** at (0,0) and **17/77/137** at a second area,
  against `FAM_FILM = 2/62/122`. The 60 deg internal spacing is intact; the whole
  triad is rotated. The toolkit's own guard fires: *"more than 10 deg from the
  established film triad. That would mean a different grain or a rotated sample
  - verify before trusting it."*
- **Reading.** C31 grades "the film triad is a single constant over the whole
  sample" as **A**, on 8+ areas within ~5 deg -- but every one of those areas was
  measured at the same sample mounting. A 17 deg rigid rotation after a remount
  says `FAM_FILM` is constant in the SAMPLE frame, not the LAB frame. C31 is not
  wrong, its scope is narrower than written: it should read "constant across
  areas at fixed mounting".
- **Consequence:** every driver pins the triad per area (S21), so nothing
  measured is affected. What is affected is any future code that hard-codes
  2/62/122 as a lab-frame reference -- PITFALLS 1.5, never hard-code what you
  can measure.
- **Falsified by:** a return to ~2/62/122 at this mounting, which would make the
  17 deg an artefact of the fit on weakly-textured film (modulation was 0.168
  here, near the floor -- see M5).

### M7 — Lambda sets how many panels a 12 um frame can AUDIT, and it is the binding constraint · **A**

- **Operation:** reproduced the drivers' own `geom()`, placement and
  `ctrl_tiles` grid analytically, then confirmed against the offline simulation
  on real frames. The readout window is `max(4.2*Lambda, 26 px)` and the halo is
  `(n-1)*spacing*ANGF/2 + R_EFF`, so BOTH scale with Lambda while the frame does
  not.
- **End:** control tiles surviving a 12 um / 256 px frame at the cheap command
  angle, with the panels placed by the drivers' own fixed point:

  | Lambda | 4 panels | 3 panels | 2 panels |
  |---|---|---|---|
  | 250-301 nm | 23-32 | — | many |
  | 354 nm | **7** | 14-16 | 25 |
  | 388 nm | **0** | — | 12 |
  | 430 nm | **5** | — | 10 |
  | 482 nm | no fit | no fit | no fit |

  Verified live: the IT11 four-panel design hit **0 of 49** and **0 of 64** in
  simulation on real frames; cut to two panels it left **13**.
- **Reading.** The control tiles ARE the C45 null (that is the whole point of
  C45), so a geometry that leaves fewer than ~8 does not produce a weaker
  result, it produces **no result** -- the threshold has no sample. Since the
  tiles are built from the AFTER frame in every driver of this family, that is
  discovered only once the write is spent. So **the panel count is set by
  Lambda, not by how many conditions the experiment would like.**
- **Consequences, concrete:**
  1. `run_it7.py` and `run_it8.py`, both listed in `NEXT_SESSION.md` as ready to
     run, write FOUR panels and are not viable at the Lambda of sample position
     3 (354-482 nm). Neither is a bad experiment; both need re-cutting to two
     panels or a smaller-Lambda area.
  2. `HANDOFF_4`'s RW1 (6 slots, 4 panels) is not buildable at 12 um / 256 px
     for a different reason as well -- see PITFALLS 19.4.
  3. Enlarging the frame at 256 px makes it WORSE: the window is floored at
     26 px, so a larger nm/px raises the window, which pushes n from 16 to 32
     and grows the halo faster than the frame. Only more pixels help.
- **Now guarded:** a pre-write control-tile gate was added to run_it7, run_it8
  and run_it13, and IT12 auto-trims its arm count. The gate warns below 8 tiles
  and halts below 6, matching the documented policy (HANDOFF_2 4) rather than a
  tighter number invented for the occasion.
- **Falsified by:** a frame that leaves plenty of tiles at Lambda >= 390 nm with
  four Lambda/2 panels, which would mean the halo model `(n-1)*sp*ANGF/2 +
  R_EFF` overstates the exclusion zone. R_EFF = 625 nm is C11's single-pulse
  radius and is the least-tested number in the chain.

### M8 — An area gate said "bad film"; it was a collapsed lateral signal, and a retune fixed it · **A**

- **Operation:** IT11 screened three areas on 27 Aug, chose (-2,0) at modulation
  0.200, took three consecutive baselines and refused to write: floor **0.589**
  (limit 0.25), **58 %** director flips (limit 25 %). The driver's advice was
  "this area cannot support the measurement... Move."
- **The discriminator:** score every frame taken that day with one piece of code,
  in time order, and see whether the health metrics track the CLOCK or the
  POSITION. Median |A| at (-2,0), in order: **46, 73, 49, 40, 21, 21 pm**. The
  two 21 pm frames are baselines 2 and 3 -- the last two in time. The same spot
  gave 49 pm twenty minutes earlier. At (0,0): 49, 35, 71, 34, 47 -- no collapse.
  So the degradation is TEMPORAL, not spatial.
- **The mechanism:** `contact_check` on the last baseline reported the tracked
  contact resonance at **729 +- 46.3 kHz** against a 665 kHz drive -- 64 kHz off
  with a +-46 kHz wobble, i.e. intermittent contact. A fresh `find_resonance`
  then found a clean, well-formed peak at **670.6 kHz, FWHM 2.3 kHz, Q 293**. So
  the resonance was healthy when static and unstable only while scanning.
- **The fix, and what it cost:** one retune plus one frame, about 7 minutes.

  | metric | baselines 2-3 | after retune | campaign healthy |
  |---|---|---|---|
  | \|A\| | 20.9-21.1 pm | **76.6 pm** | 40-55 |
  | r12 | +0.67 / +0.90 | **+0.95** | +0.93-0.95 |
  | tracked freq | 729 +- **46.3** kHz | 658.4 +- **0.7** kHz | +-2-4 |
  | correlation length xi | 656 nm (14 px) | **94 nm (2 px)** | 2 px |
  | deflection setpoint | 0.35 V | **0.55 V** | 0.60 V |

- **Reading, CORRECTED 27 Aug 23:30.** The original entry attributed the
  collapse to the contact force: the meter had read **+0.350 V** against a
  0.35 V setpoint, which I read as a drifted free level giving ~zero force.
  **That inference was wrong.** `read_meter()[1]` returns the LIVE deflection --
  the free level only when the tip is WITHDRAWN; when the tip is engaged and in
  feedback it simply equals the setpoint. A reading of +0.350 against a 0.350
  setpoint is therefore the signature of an engaged tip, not of a drifted one,
  and (setpoint - live) is ~0 by construction rather than by physics. The error
  surfaced when a later run halted at "force 0.002" for exactly that reason.
- **What survives, and it is the load-bearing part.** The collapse and its fix
  are established independently of any force interpretation:
  the |A|-versus-time series (screening frames, which re-tune per frame, held
  79-110 pm all afternoon while bare consecutive frames fell 40 -> 21 pm within
  two frames), the tracked contact resonance running 64 kHz off with a
  +-46 kHz wobble, and the fact that **one re-tune restored |A| to 76-110 pm and
  a per-frame re-tune then held it across eight frames**, taking the floor from
  0.589 to 0.069. The mechanism is the DART loop losing a drifting contact
  resonance. The setpoint may or may not have contributed; nothing here shows
  that it did.
- **Setpoint history, for the record.** On 20 Aug **35 of 35** of the 12 um
  IT-run frames ran at 0.60 V while that day's smaller exploratory frames used
  0.35-0.50 V. So 0.35 V is not unprecedented, but it is not what any scored
  iteration used -- which is worth knowing and is not evidence of a mechanism. The setpoint returned to
  0.55 V at the retune and the signal recovered with it, which points at contact
  force as the root cause: too little force, marginal lateral coupling, a contact
  resonance that wanders while the tip scans, a weak and noisy signed map, and
  therefore a director estimate that flips 58 % of the time. **The film was
  never the problem.**
- **Why this is worth a numbered entry.** It is the fifth time in this campaign
  that the material was blamed for a measurement failure (PITFALLS 8 lists four).
  It is also the first time the diagnosis was made from the frames rather than
  argued: the |A|-versus-time series is a two-minute offline computation on data
  already on disk, and it separates "bad area" from "bad readout" unambiguously.
  **Run it before accepting any area-gate rejection.**
- **A caution that survives the fix:** `contact_check` on the recovered frame
  still printed *"MOVE TO A DIFFERENT LOCATION AND RETUNE... the contact spot
  itself is bad"* -- while reporting |A| 76.6 pm, r12 +0.95 and +-0.7 kHz
  tracking on the same line. C52 already grades that string as not a
  readout-quality signal. It is worse than uninformative here: acting on it would
  have moved the tip away from a spot that had just been shown to be good.
- **Falsified by:** an area whose |A|-versus-time series is flat while its flip
  rate is still above 25 %. That would be a genuine near-degenerate-population
  area, which is what C52 describes and what IT7 hit on 22 Aug.
- **Consequence for the setpoint:** the run was relaunched at 0.55 V. Anything
  comparing across the 0.35 V frames and the 0.55 V frames is comparing across a
  changed setpoint (PITFALLS 1.4) and must not be pooled.

### M9 — The buildable window: Lambda_min = 0.2 / (6.5 - 4.2*ANGF), and why 14 um beats 12 · **A**

Derived, then confirmed against five screened areas and four halted launches on
27 Aug. Everything here is arithmetic on quantities the screening loop already
has, so it costs nothing to check before spending baselines.

**The n = 16 condition.** The readout window must fit inside the panel along the
commanded axis, with a margin of one spacing plus 0.1 um per side (S15):

    WIN * ANGF + 2*(sp + 0.10)  <=  (n-1) * sp,     sp = Lambda/2

At n = 16 and with WIN set by the 4.2*Lambda floor rather than the 26 px floor,
this reduces to

    4.2*Lambda*ANGF <= 6.5*Lambda - 0.2   ->   **Lambda >= 0.2 / (6.5 - 4.2*ANGF)**

| worst command ANGF | minimum Lambda for n = 16 |
|---|---|
| 1.000 (command at 0 or 90 deg) | 87 nm |
| 1.271 (19 deg on this triad) | 172 nm |
| 1.388 (122 deg, old mounting) | 305 nm |
| **1.411 (139 deg, this mounting)** | **348 nm** |

Above ANGF = 6.5/4.2 = **1.548** no Lambda works at all: the window can never fit.
ANGF peaks at 1.414 at 45 deg, so the recipe survives -- but only just, and the
139 deg member of the rotated triad sits at 1.411, i.e. 0.003 from the worst
case the geometry can express.

**Confirmed at the instrument.** Five areas screened at 12 um / 256 px:

| area | modulation | Lambda | buildable? |
|---|---|---|---|
| (0,0) | 0.188 | 354 | YES -- n 16, halo 2.50, 2x1 |
| (-2,0) | 0.207 | 280 | no: n would be 32 |
| (0,-2) | 0.139 | 301 | rejected on modulation |
| (0,+2) | **0.210** | 245 | no: n would be 32 |
| (+2,0) | 0.188 | 354 | no: n = 32 (Lambda 3 nm the wrong side of 348) |

Two things to take from that table. First, **the best-modulation areas had the
smallest Lambda and were the unbuildable ones** -- selecting an area on
modulation alone, which is what the driver did, walks straight into a geometry
that cannot be built. Second, the last row cleared 348 nm by about 3 nm on one
frame and failed on another, in a quantity whose per-member spread runs 36-66 %
(M5). **The n = 16/32 boundary is a knife edge on a noisy estimate.**

**Why the frame size matters more than it looks.** At Lambda 354 and ANGF 1.411
the halo is 2.50 um and the pitch 5.10 um. A 12 um frame then settles only a
**2x1** layout -- two slots -- and two slots give no selection freedom, so a
matched pair happens only if those two slots happen to share a starting dominant.
On 27 Aug they did not (19 and 79 deg) and the run halted, correctly, rather than
reproduce C54's confound.

A 14 um frame settles **2x2 = four slots** at Lambda 354, 388 and 430 alike. Four
slots make matching a **pigeonhole guarantee**: three triad members, four slots,
so at least two must share a dominant. That converts the matched pair from luck
into structure, for 0.9 min per frame.

**Rejected alternative, recorded so it is not retried.** Forcing 2x2 into 12 um
by shrinking the reserved tile band below the first panel row does yield four
slots -- and leaves **zero** control tiles, because the panels then span almost
the whole frame. The band is not slack; it is the null's sample. See M7.

**Falsified by:** an area with ANGF_worst >= 1.5 that nonetheless builds at
n = 16, which would mean the margin term 2*(sp + 0.10) is smaller in the toolkit
than S15 states.

**THE UPPER BOUND, added 27 Aug 23:40 -- and it is the one that bites.** The
Lambda_min above stops n jumping to 32. A second, independent ceiling comes from
the CONTROL TILES: the readout window is 4.2*Lambda and the halo grows with
Lambda too, so past a certain coarseness a panel plus its halo leaves no
untouched film to measure the C45 null on. Computed with the drivers' own grid,
ONE panel in a 10 um frame with the scan rotated:

| Lambda | control tiles |
|---|---|
| 240-320 nm | 24-48 |
| 340-420 nm | 13-24 |
| **440 nm** | **4** -- below the floor of 6 |
| 460-500 nm | 0-4 |

The collapse between 420 and 440 nm is a cliff rather than a slope, because the
tile grid is discrete. The usable window at 10 um is therefore

    148 nm <= Lambda <= ~420 nm    (one panel)
    148 nm <= Lambda <= ~396 nm    (two panels, the within-frame pair)

and it widens only with FRAME SIZE -- not with pixels, and not with dose.

**CORRECTION, 28 Aug 04:00 -- the position-4 numbers below were all 2x too
large and the conclusion drawn from them was false.** The overnight driver
screened 5 um frames but computed `px_nm` from `FRAME` (the 10 um SCORED size),
so every screened Lambda came out at exactly twice the true period. Verified on
one frame: PZTO_LDART_0086.ibw, ScanSize 5.0 um, 256 px -> correct px_nm 19.53
gives Lambda 245/301/354 (median 301); the driver's 39.06 gave 548/548/755
(median 548). Ratio 2.00, on every point. See PITFALLS 19.11.

Halving the seven medians gives **194, 215, 215, 241, 274, 318, 378 nm** --
**all seven inside the 148-420 nm window**, not six of seven past it. The region
was buildable the whole time. A survey with the corrected arithmetic found
Lambda 301 nm (modulation 0.193) and 245 nm (modulation 0.259) at the first two
points it touched.

What survives is the arithmetic above -- the n = 16 condition, the tile cliff,
and both bounds -- because none of it depends on the measurement. What does not
survive is the claim that this film is too coarse for a 10 um frame, and the
recommendation to move the coarse stage that followed from it. **The window was
right; the ruler was wrong.**

~~**Why this matters more than it looks.** Sample position 4 measured Lambda
medians of 388, 430, 430, 482, 548, 635, 755 across seven screened candidates:
six of seven past the cliff.~~ (Retracted, see above.) The general point the
passage was making still holds and is worth keeping: a region can be healthy by
every other measure -- modulation 0.20-0.24, streak 0.02, baseline floor 0.069,
flip 10 %, |A| 82-110 pm -- and still be unable to support a scored measurement
at <= 10 um purely because its lamellar period is too long. That remains a
property of the FILM meeting a property of the FRAME. It just was not what was
happening here.

**The estimator makes it worse.** Lambda's per-member spread runs 13-69 %, and
the same position read 388 nm on one visit and 430 on two others (M5) -- i.e.
194 and 215 nm once halved; the spread is real, the absolute values were not. The
n = 16/32 boundary and the tile cliff both sit inside the noise of the quantity
that decides them, so screening many positions is not fastidiousness -- it is
the only way to find the fine end of a noisy distribution.

### M13 — The tip writes: 180 deg out-of-plane reversal under +10 V, demonstrated · **A**

- **Why it was asked.** Three in-plane iterations on 28 Aug came back VOID. One
  was explained by a collapsed readout (M12) and one was not: its after-frames
  were the *stablest* part of the iteration (after-vs-after floor 0.145, 0 %
  flips) and the panels still moved no more than the untouched tiles did
  (excess 0.008 and 0.017). Before spending more time on dose, the question
  "does any bias reach the sample at all" had to be settled.
- **Operation:** `diag_poling.py`. Two solid 1.2 um squares written side by side
  at **+10 V and -10 V**, raster pitch 60 nm, 0.25 um/s, areal dose
  ~667 V.s/um^2 (~1.7x the lattice that failed), per-site 2.0 V.s. VDART before
  and after. Both polarities, because the film reads 88-96 % one class: whatever
  the starting state, one square must be writing against it.
- **End:**

  | region | phase change vs control | \|A\| before -> after | phase sd before -> after |
  |---|---|---|---|
  | **+10 V square** | **-180.2 deg** | 45.5 -> **166.5 pm** | 55.7 -> 30.8 |
  | -10 V square | -1.8 deg | 52.0 -> **186.5 pm** | 53.3 -> **6.2** |
  | control | (reference) | 43.1 -> 47.9 pm | 67.1 -> 49.5 |

  A textbook full reversal under +10 V, none under -10 V -- the film's native
  state already points the way -10 V drives it -- and both squares driven to a
  phase-uniform single domain. **Confirmed on both DART phase channels**
  independently: -180.2 deg (Phase1) and -178.5 deg (Phase2).

**What it retires.** The hypothesis that no bias was reaching the sample, which
had become the leading explanation for every void of the night. It is wrong. The
electrical path, the tip, and the litho panel all work. Any dose conclusion must
be about the FILM and the GEOMETRY, not the instrument.

**A caution about the summary line that misled me.** `orbit_balance` printed
"up 93.7-96.0 %, ONE CLASS ONLY, minority in patches >=25 px: 0 %" after both
lattice writes, and I read the absence of switched patches as evidence the tip
was dead. On the poling frame the same routine printed "ONE CLASS ONLY" for a
frame containing a 1.2 um square at exactly -180 deg -- its own
"minority in patches: 71 %" contradicted its headline. **The headline string is a
heuristic and it was wrong on a frame with an unmistakable two-class structure.**
Read the patch fraction, not the verdict string.

**Method note, recorded because it cost twenty minutes.** The Igor header labels
are offset relative to the data: `Channel3DataType='Phase1'` sits on an
amplitude, and the channel labelled `Phase2` holds the 358 kHz drive frequency.
The toolkit's own `ibw` docstring has the true order -- **0 Height, 1 Amp1,
2 Amp2, 3 Phase1, 4 Phase2, 5 Freq** -- and `make_campaign_figures.py:65`
documents it independently. Trust those, not the header strings. Reading d[2] as
a phase returns all zeros and looks like a dead channel.

### M35 — The as-grown/poled SIGN INVERSION is contradicted by this campaign's own rewrite experiment · **B**

[[C26]] reported that a charge-balanced raster on OUT-OF-PLANE POLED film
**depletes** the family parallel to its own scan lines, where [[C49]] found it
**populates** that family on virgin film — five panels, three one way and two
the other, split entirely by poling state. That inversion is the physical
content of the `B(P_z)` term in the manuscript's free-energy sketch, and it is
the most interesting claim the mechanism section makes.

**This campaign's own two-step rewrite contradicts it.** In [[M33]] the second
raster was applied to film that the FIRST raster had already written — and a
charge-balanced +V/−V raster leaves the region in the polarity of its last
pass, so that film is out-of-plane poled by construction. If C26's inversion
held, the second raster should have depleted the orientation nearest its own
axis. It did the opposite: the director moved from 18.8 deg to **78.8 deg**,
which is 4.8 deg from member 74, the member NEAREST the 60 deg raster. It
aligned, exactly as on as-grown film.

**Three ways to reconcile them, and this work cannot choose between them.**

1. **"Poled" in C26 is not "rastered" here.** C26's panels were poled by a
   separate solid DC square at ~667 V.s/um^2 before the raster; here the prior
   state was written by an identical raster. The out-of-plane states may differ
   in degree or in uniformity.
2. **C26 is confounded.** Its poled and unpoled panels were grouped in one
   frame rather than interleaved, so a frame-position effect would produce the
   same table, and no area in that experiment was screened on topography
   ([[M29]]).
3. **The inversion is real but requires a stronger out-of-plane state** than a
   charge-balanced raster leaves behind.

**What this costs the manuscript.** The sign inversion has to be demoted from a
mechanism to an open question, and the `B(P_z)` sign change in the free-energy
sketch is no longer supported by data taken with the current probe and
estimator. The sketch's first term — the crystal fixing where the minima are —
is untouched, and so is the selection rule itself.

**The experiment that settles it** is one write plus one raster on a
topography-screened area: pole with a solid unipolar-equivalent square at the
C26 dose, then raster across it at a known angle, with an unpoled control
region rastered identically in the same frame. That is the interleaving C26
lacked.

**Graded B**, and the grade is on the CONTRADICTION, which is solid: M33's step
2 is a strongly significant alignment (p 0.005) on film that had just been
rastered. What is unresolved is which of the three explanations holds.

### M34 — AC trajectory lithography never steers, at any sign period from 120 nm to 1.6 um · **A**

[[M32]] found that an alternating bias at a 120 nm sign period DISORDERS the
film where a dose-matched DC raster aligns it, and proposed that the field must
hold one sign over a length "far above 60 nm". The obvious next step was to
find the crossover. **There is no crossover in the range tested.**

Four writes, all at matched |V| = 10 V and matched delivered dose, all on
topography-screened as-grown areas, differing only in how the sign is arranged
along the path:

  | sign period | before | aniso | after | aniso | p after | outcome |
  |---|---|---|---|---|---|---|
  | 120 nm | 63.8 | 2.83 | 131.2 | **1.77** | 0.537 | **disorders** |
  | 800 nm | 63.8 | 3.69 | **63.8** | 5.96 | 0.005 | **does not move**; consolidates the incumbent |
  | 1600 nm | 33.8 | 2.07 | 41.2 | 2.11 | 0.199 | nothing |
  | **DC** (unipolar pass) | 56.2 | 2.19 | **18.8** | **22.74** | 0.005 | **steers to the predicted member** |

The 800 nm case is the informative one: the film was already on member 69, and
the AC write left it there and sharpened it slightly (3.69 -> 5.96). It
consolidated rather than steered — which is what [[C28]] reported for the
trajectory and [[C14]] for AC+DC, both of which said the write "relaxed toward
the local attractor" instead of moving it.

**So the requirement is not a length along the trajectory.** In the DC write
the ENTIRE 1.6 um square is at one polarity throughout a pass; in every AC
write, regions of the same square are at opposite polarity simultaneously.
Even at a 1.6 um sign period — where each line is half at +V and half at
−V, so the tip applies one sign over 800 nm of continuous travel — the
director does not move. What steers the film appears to be a field that is
**unipolar across the written region**, not merely sustained along a stretch of
path.

**Stated conservatively:** alternating the sign anywhere within the written
region, at any period from 120 nm to 1.6 um, abolishes steering. Whether the
governing length is the region size or something larger is not determined; a
DC raster over a much larger square, which still steers, puts the bound above
1.6 um but does not close it.

**Graded A.** Four matched writes spanning a 13x range of sign period against a
DC reference, with in-frame controls and topography-gated areas, giving a
qualitative difference rather than a graded one.

### M33 — An ALREADY-ALIGNED super-domain can be re-aimed 60 deg by a second raster, at a cost in order · **A**

**The project's central question, answered directly.** Everything else in the
campaign starts from as-grown film. This starts from a super-domain the same
tool has just aligned.

- **Operation.** One area, (-6,0), triad 24/84/144, two writes with a full
  readout between them. Both charge-balanced DC rasters, 1.6 um square, 30 nm
  pitch, sigma ~688 per polarity. The second write's BEFORE frames are the
  first write's AFTER frames, so the comparison is against the aligned state
  and not against a fresh tune.

  | step | raster | before | aniso | after | aniso | nearest allowed | offset |
  |---|---|---|---|---|---|---|---|
  | 1 | 0 deg | 78.8 (p 0.254) | 2.02 | **18.8** (p 0.005) | **13.47** | 24 | 5.2 |
  | 2 | 60 deg | **18.8** (p 0.005) | **13.47** | **78.8** (p 0.005) | **5.70** | 74 | 4.8 |

- **Step 2 is the result.** Its starting state is not weak or ambiguous: it is a
  well-ordered stack at anisotropy 13.47, p 0.005, which step 1 had just
  written. A 60 deg raster moved it a full **60.0 deg** onto the next allowed
  orientation, 4.8 deg from the member.

- **Rewriting costs order.** The anisotropy after the second write is **5.70**
  against **13.47** after the first — the re-aimed state is real and
  significant but less well ordered than the state it replaced. Whether that is
  a fundamental cost of rewriting, an accumulated-dose effect, or simply that
  the second write fights an ordered state rather than a disordered one is not
  determined by one pair. A third write on the same area would begin to answer
  it and is cheap.

**Why this matters for the application.** A medium that can only be written
once is a fuse, not a memory. This is the first demonstration in the campaign
that the same tool both writes and rewrites the in-plane director.

**Graded A.** One area, but the before-state of step 2 is a measured, strongly
significant aligned state rather than an assumption, the move is a full 60 deg,
and both steps independently satisfy the [[M31]] angle rule.

### M32 — AC trajectory lithography DISORDERS the film where DC aligns it: the field must hold one sign over a length scale far above 60 nm · **A**

- **Why it was run.** [[M13]]/[[M14]] showed the in-plane response is
  polarity-independent — a -10 V square aligns as well as a +10 V square —
  which is usually read as the drive being even in E, entering as |E|^2. If
  that were the whole story, a bias that alternates faster than the tip crosses
  a domain should align exactly as a sustained one does.

- **The controlled comparison.** Identical geometry, identical |V| = 10 V,
  identical raster lines, matched delivered dose (658 against 683 V.s/um^2,
  4 % apart and LOWER for the AC case, so equal alignment would be
  conservative). The **only** difference is that the DC write holds one sign
  for a whole 1.6 um line while the AC write flips every 60 nm — a 120 nm
  spatial sign period, chosen deliberately below the 150 nm lower edge of the
  readout band so it cannot imprint into the measurement.

  | | before | aniso | after | aniso | p after |
  |---|---|---|---|---|---|
  | DC, 0 deg (M31) | 56.2 | 2.19 | **18.8** | **22.74** | **0.005** |
  | **AC, 0 deg** | 63.8 | 2.83 | 131.2 | **1.77** | **0.537** |

- **AC does not align. It DISORDERS.** The anisotropy falls from 2.83 to 1.77
  and the after-state has no significant direction at all (p = 0.537), where
  the matched DC write reaches anisotropy 22.7 at p = 0.005. The apparent
  67.5 deg "move" is meaningless: there is no direction to have moved to.

**What this fixes in the mechanism.** Polarity independence and
|E|^2-dependence are not the same statement, and the campaign has been
conflating them. What the film requires is not a particular SIGN but a
SUSTAINED one: the field must hold its sign over a length far greater than
60 nm. Either sign will do, which is why +10 V and -10 V squares behave alike,
but a sign that reverses every 60 nm destroys order instead of selecting a
variant.

That points at a mechanism with a characteristic length — something swept,
dragged or nucleated over a contiguous biased path — rather than a purely
local |E|^2 coupling, which would not care how the sign is arranged along the
trajectory.

**The obvious next measurement** is the crossover: sign periods of 120 nm
(fails), 800 nm and 1600 nm against DC (works). Periods between 150 and 500 nm
must be avoided because they would imprint into the readout band. That series
would turn "far above 60 nm" into a number.

**Graded A.** A matched-dose, matched-field, matched-geometry pair differing in
one controlled variable, with the AC case at slightly LOWER dose, and an
outcome that is not a smaller version of the DC result but a qualitatively
different one.

### M31 — The raster angle rule, three for three on the current probe, with a pre-registered prediction hit to 0.2 deg · **A**

- **Operation.** Three charge-balanced DC rasters, 1.6 um squares, 30 nm pitch,
  0.5 um/s, sigma ~688 V.s/um^2 per polarity, on three independently screened
  as-grown areas (topography gate passed on all three). Each raster angle was
  chosen for ITS area so that the predicted destination was NOT the incumbent,
  because a raster whose prediction is the orientation the film is already on
  tests nothing.

  | raster | triad | before (p) | after | aniso after | nearest allowed | offset | moved |
  |---|---|---|---|---|---|---|---|
  | **46 deg** (forbidden) | 16/76/136 | 63.8 (0.15) | **18.8** | 10.85 | 16 | **2.2** | 45.0 |
  | 0 deg | 24/84/144 | 56.2 (0.19) | **18.8** | 22.74 | 24 | **5.2** | 37.5 |
  | **120 deg** | 19/79/139 | 63.8 (0.35) | **138.8** | 9.61 | 139 | **0.2** | 75.0 |

- **Every before-state had no significant direction** (p = 0.15-0.35), so the
  after-state cannot be the estimator sharpening something that was already
  there. The anisotropy rises to 9.6-22.7 at p = 0.005 in all three.

- **THE LAB-FRAME CONTROL, which nearly went unnoticed.** The first two runs
  both returned **18.8 deg**. Two different areas, two different triads, two
  different raster angles, one answer -- which is exactly what a fixed
  instrumental direction near 19 deg would produce, and would have meant
  neither run showed selection at all. The 120 deg run returns **138.8 deg** on
  the same instrument with the same readout and the same estimator. The
  destination tracks the commanded axis and the film's own allowed
  orientations, not the apparatus.

  The coincidence has a mundane explanation once checked: the first area's
  member 16 and the second's member 24 differ by 8 deg, and the estimator's
  angular bins in the sparse super band are ~2.7 deg wide, so both land in the
  same bin. But it had to be checked, and the check is the 120 deg point.

- **The 120 deg destination was predicted before the write** -- the driver
  prints the prediction from the triad and the raster angle before building the
  path -- and hit to **0.2 deg**.

**Together with [[M30]]** (the 46 deg raster landing 2.2 deg from an allowed
orientation and 27 deg from the commanded one) this establishes the rule as a
selection among crystallographically allowed variants, driven by the axis of
the trajectory:

> **A charge-balanced raster drives the in-plane super-domain director onto the
> symmetry-allowed orientation nearest the raster axis.**

**Graded A.** Three areas, three angles, three destinations, pre-registered
predictions, in-frame controls, topography-gated areas, 4-Lambda-valid readout
windows, and a lab-frame control that the data themselves demanded.

### M30 — THE RASTER SELECTS AN ALLOWED VARIANT; THE PULSE LATTICE WRITES A PATTERN. A raster commanded to a forbidden direction still lands on an allowed one · **A**

- **Why this is the pivotal experiment.** [[M28]] showed that a point-pulse
  lattice commanded to a crystallographically FORBIDDEN direction produces a
  persistent readout at exactly that direction and nothing on any allowed one:
  the lateral channel inside a lattice-written panel reports the written
  pattern, not the film. That raised the obvious objection against every raster
  result in the campaign — the raster is read with the same channel, and a
  raster has an AXIS, so an anisotropic surface modification along its scan
  lines would look exactly like alignment along the raster.

  The test is the one M28 applied to the lattice, never before applied to the
  raster: **raster along a direction the crystal forbids.**

- **Operation.** Area (+12,+12), sample position 8, screened on topography
  (roughness 0.40 nm, 1-99 % range 1.88 nm). Triad **16 / 76 / 136**,
  Lambda 276 nm, modulation 0.202. Readout window 1.2 um = **4.35 Lambda**.
  Charge-balanced DC raster, 1.6 um square, 30 nm pitch, 0.5 um/s,
  sigma 688 V.s/um^2 per polarity, **along 46 deg** — 30 deg from member 16
  and 30 deg from member 76, so it is equidistant from two allowed
  orientations and 30 deg from either.

- **End.**

  | | director | period | anisotropy | p |
  |---|---|---|---|---|
  | before | 63.8 deg | 244 nm | 2.21 | 0.154 -- no significant direction |
  | **after** | **18.8 deg** | 210 nm | **10.85** | **0.0050** |

  * distance from the after-state to the nearest ALLOWED orientation: **2.2 deg**
  * distance from the after-state to the RASTER angle: **27.2 deg**
  * the director **moved 45.0 deg** from its starting value

**Three readings are possible and the data pick one.** A pattern imprinted
along the scan lines would sit at 46 deg; it is 27 deg away from that. "Nothing
happened" would leave the director near its starting 63.8 deg; it moved 45 deg.
What remains is that the film reorganised onto an allowed orientation, and the
anisotropy rose from 2.21 (not significant) to 10.85 (p 0.005) in doing so.

**This is the imprint-free result the campaign needed**, and it draws a sharp
line between the two writing tools:

| | commanded to a forbidden direction | interpretation |
|---|---|---|
| **point-pulse lattice** ([[M28]]) | readout appears AT the forbidden direction, 4.9-8.6x, nothing on any allowed one | writes a pattern |
| **charge-balanced raster** (this) | readout lands 2.2 deg from an ALLOWED orientation, 27 deg from the command | selects a variant |

They are different physical processes and the campaign has been reading them
with one instrument as though they were one.

**An honest caveat about which member it chose.** 46 deg is equidistant from 16
and 76, so "nearest member" does not predict between them, and the film went to
**16 — the one it was NOT already on** (it started weakly on 76). With one run
this cannot be told apart from a coin toss, from a genuine "move away from the
incumbent" rule, or from the depletion behaviour [[C26]] reports on poled film.
A second off-triad raster on film sitting on a DIFFERENT incumbent would settle
it, and is cheap.

**Graded A.** The before-state has no significant direction, so the after-state
cannot be an artefact of sharpening a pre-existing one; the move is 45 deg; the
area passed a topography gate; the readout window holds 4.35 Lambda; and the
two candidate explanations make predictions 27 deg apart at a 15 deg criterion.

### M29 — An area can pass every gate the campaign has and still be unusable: topography was never screened · **A**

- **How it surfaced.** The operator looked at the first frame of a new stage
  position and said immediately that it sat on a large step edge, visible at a
  glance in the height channel. No gate in the campaign reads that channel.
  Every area gate — modulation, streak index, Lambda, tile spread, flip rate
  — is computed from the LATERAL signal.

- **Why it is not cosmetic.** The lateral signal is cantilever TORSION. On a
  slope the tip feels a lateral force that has nothing to do with
  piezoresponse, and a step edge is a straight line, so it injects a
  **directional** in-plane signal. That is exactly the quantity every result in
  this campaign is built on.

- **The measurement.** Plane-removed roughness and 1-99 % height range, over
  ten areas at a fresh stage position, alongside the existing gates:

  | area | roughness | 1-99 % range | modulation | streak | Lambda | verdict |
  |---|---|---|---|---|---|---|
  | (+12,+12) | 0.38 nm | 1.8 nm | 0.181 | 0.015 | 279 nm | usable |
  | (-6,-6) | 0.38 | 1.8 | 0.245 | 0.026 | 253 | usable |
  | (0,-6) | 0.52 | 2.1 | 0.278 | 0.072 | 295 | usable |
  | (-6,+6) | **1.81** | **8.3** | 0.210 | 0.018 | 288 | rejected on topography |
  | **(-12,-12)** | **35.62** | **174.8** | 0.150 | 0.049 | 248 | **rejected on topography** |

  **(-12,-12) passes every gate the campaign had.** Modulation 0.150 is above
  the 0.10 floor, streak 0.049 is far inside the 0.10 limit, Lambda 248 nm sits
  in the buildable window, and the triad fits. It is also **35 nm rough with a
  175 nm height range** — a hundred times the roughness of a good area. Under
  the old gates it would have been written on.

- **The gate.** Plane-removed roughness <= 1.0 nm AND 1-99 % range <= 5.0 nm.
  Good areas run 0.38-0.65 nm and 1.8-2.8 nm; the two rejects are 1.81/8.3 and
  35.6/174.8. The separation is a factor of three at the tightest.

- **What does NOT work, and was tried first.** Bimodality of the height
  histogram. A step edge should give two populations — and it does, but so do
  good areas, because the domain structure corrugates the surface. The test
  flagged good and bad frames alike. Roughness and range discriminate.

**What this costs retrospectively.** No area in this campaign before 29 August
was screened on topography, so it is not known how many historical results were
taken on stepped ground. The affected claims are any that rest on a single
area: [[C26]]/[[C49]]'s sign inversion in particular, which is the manuscript's
most interesting claim and rests on five panels from one experiment. Areas
screened from now on carry the gate; earlier ones cannot be re-gated because
the height data was not retained in the analysis path, though it is in the
`.ibw` files and could be recovered.

**Graded A.** Ten areas, one decisive counter-example that passes every old
gate and fails the new one by two orders of magnitude, and a stated negative
control for the metric that does not work.

### M28 — A template commanded to a CRYSTALLOGRAPHICALLY FORBIDDEN direction produces a persistent readout at exactly that direction, and no response on any allowed member · **A**

- **Why it had to be asked.** Every director in this campaign has been commanded
  TO a triad member. "The film adopted the commanded director" and "the readout
  is the pattern we wrote" therefore predict the SAME answer and have never
  been separated. Commanding the midpoint between two members separates them:
  the two predictions are 30 deg apart and the hit criterion is 15 deg.

- **Operation.** Two runs, S22 relaxed on purpose and on the record.

  | area | triad | incumbent | commanded | Lambda | sigma |
  |---|---|---|---|---|---|
  | (-8, 0) | 26 / 86 / 146 | 86 | **56.5** | 300 nm | 124 |
  | (+8,-8) | 16 / 76 / 136 | 76 | **46.5** | 338 nm | 133 |

- **End, matched filter at each candidate direction, panel interior.**

  | run (-8,0) | LDART before -> after | VDART before -> after |
  |---|---|---|
  | **commanded 56.5** | 19.0 -> **92.7 pm**, z **+5.4**, p 0.008 | 14.4 -> **123.5 pm**, z **+21.1**, p 0.008 |
  | member 26 | 10.5 -> 32.9, z +0.4, p 0.39 | 11.8 -> 10.9, z +0.2, p 0.41 |
  | member 86 | 59.6 -> 45.1, z +1.1, p 0.14 | 10.7 -> 19.8, z +0.4, p 0.23 |
  | member 146 | 37.4 -> 15.3, z -0.7, p 0.76 | 10.4 -> 1.7, z -0.3, p 1.00 |

  The repeat at (+8,-8) agrees: commanded 46.5 gives z +7.1 (LDART) and
  **z +24.7** (VDART); every member gives p >= 0.39. Across both runs and both
  channels the commanded direction gains **4.9 to 8.6x**, while the three
  allowed members **lose** power, median **0.68x**.

  Caveat on the repeat: its LDART corners drifted 2.0-3.1x, outside the
  no-write null's maximum of 1.81, so its LDART half is not clean. Its VDART
  corners (1.13-1.34) are, and the VDART result is the stronger of the two.

- **It is not a decaying surface charge.** Three panels re-imaged 4.7-5.0 hours
  after writing, identical settings:

  | area | sigma | LDART retained | VDART retained |
  |---|---|---|---|
  | (0,0) | 133 | 65 % (z +5.9) | **92 %** (z +21.8) |
  | (+4,0) | 122 | 80 % (z +7.0) | 64 % (z +30.9) |
  | (0,-4) | 263 | 75 % (z +17.5) | - |

  64-92 % retained after five hours, every one still overwhelmingly
  significant. Whatever was written is structural, not a relaxing charge.

- **And it is NOT a fine superlattice of allowed variants.** The obvious rescue
  is that a ferroelectric cannot polarise at 56.5 deg, so the film must be
  building a fine alternating stack of two ALLOWED variants whose ENVELOPE
  carries the commanded direction. That predicts local directors on members
  once the structure tensor is smoothed below the band width. Tested by
  sweeping the smoothing from 60 nm to 10 nm, **against the random-direction
  null** -- for uniform directions and three members 60 deg apart, the median
  distance to the nearest member is exactly **14.9 deg**, and to a fixed
  command **44.9 deg**:

  | smoothing | to nearest member | to command |
  |---|---|---|
  | 60 nm | 22.4 (**+7.5** vs null) | 7.9 (**-37.0**) |
  | 40 nm | 19.8 (+4.9) | 11.5 (-33.4) |
  | 25 nm | 16.3 (+1.4) | 18.7 (-26.2) |
  | 15 nm | 15.9 (+1.0) | 23.2 (-21.7) |
  | 10 nm | 15.7 (+0.8) | 26.0 (-18.9) |

  At **every** scale the local directors cluster on the COMMAND and never on
  the members -- the member distances sit at or above the random value
  throughout. The **unwritten control** behaves oppositely and correctly:
  10.9-13.4 deg to the nearest member at every scale, genuinely below the null.

  (The raw numbers briefly looked like a crossover -- 15.7 to a member against
  26.0 to the command at 10 nm reads as "members win" until one notices that
  15.7 IS the random value. See PITFALLS 21.11.)

- **And it is a real structure on the SAMPLE, not something locked to the scan
  frame.** The area was re-imaged with the scan rotated by +60 deg. A feature
  fixed on the sample must move with the rotation; anything fixed in the scan
  frame -- as the ~75 nm fast-axis artefact of PITFALLS 21.6 demonstrably is --
  must not.

  | | measured shift for a +60 deg scan rotation |
  |---|---|
  | the written feature | **+67.5 deg** (280 nm both times, aniso 2.9 and 3.2) |
  | prediction, real on the sample | +60 deg |
  | prediction, fixed in the scan | 0 deg |

  It rotated with the sample. The 7.5 deg excess is about three angular bins of
  this estimator in the sparse super band, so it is not obviously meaningful,
  and it is nowhere near zero.

  The intended internal control did NOT work and is reported as such: the
  45-90 nm band was meant to stay put, but it is not significant in either
  frame (p = 0.12 and 0.92), so its apparent shift is noise and it constrains
  nothing. The main comparison stands on its own.

**WHAT THIS MEANS.** On UNWRITTEN film the lateral channel reports genuine
ferroelastic variant structure: it clusters on allowed members at every scale.
INSIDE a template-written panel it is dominated by a persistent pattern at
whatever direction was commanded, allowed or not, which does not decompose into
variants at any resolved scale. **Those are two different things being read by
one instrument.**

The consequence for the campaign is direct. [[M16]], [[M18]], [[M20]] and
[[M25]] all commanded members, so their "the film adopted the commanded
director" is equally consistent with "a pattern was written along the commanded
direction". The 15 deg hit statistics are not evidence of variant selection.

**WHAT SURVIVES, and it is not nothing.**

* [[M26]] is untouched: a **spatially uniform** write, with no periodicity to
  imprint and no commanded direction at all, rotated the film from member 76 to
  member 16 -- and the rotated-raster repeat sent it to member 76 when the
  raster ran at 60 deg. That is genuine variant reorientation, and its
  controllable variable is the RASTER DIRECTION.
* The threshold decoupling of [[M27]]: at sigma 17 the out-of-plane pattern is
  written and the in-plane readout does not move at all.
* The written pattern persists for hours and is programmable in period and
  orientation, including orientations the crystal forbids. That is a real and
  possibly more useful capability than choosing among three variants -- but it
  needs to be characterised as what it is, not as variant selection.

**THE NEXT EXPERIMENT.** Establish what the written contrast IS. Candidates:
an in-plane polarisation pattern in a non-ferroelastic sense, a trapped charge
pattern that survives hours, or surface modification. Distinguishing them wants
a channel that is not the lateral piezoresponse -- KPFM for trapped charge,
topography for surface modification -- plus a thermal or electrical erase test.
None of these costs S24 budget.

**Graded A.** Two runs, both channels, matched filter with the corner null
measured on 14 pairs, retention measured on three panels, the superlattice
rescue tested against its correct null and excluded, and an unwritten control
that behaves as it should at every scale.

### M27 — The modulation at the template wavevector is largely an IMPRINT of the alternating bias, and the campaign's own readout cannot separate it from a film response · **A**

- **Why it was asked.** [[M25]] found that after every commensurate write, both
  channels carry a large modulation at the template wavevector where the virgin
  film had none out-of-plane ([[M24]]). The tempting reading -- the template
  creates the P_z modulation its own selection term couples to -- was pre-
  registered and is **wrong**, or at least unsupported.

- **The control that decides it.** A template whose sign period does NOT match
  the film. A passive imprint appears at the TEMPLATE's period whatever the
  film is doing; a cooperative response can only appear at the FILM's period.

  The first attempt at this was worthless: 328 nm template into 253 nm film is
  a separation of 0.90 /um against a 1.00 /um window resolution -- inside one
  resolution element (PITFALLS 21.8). The second attempt used **155 nm into
  326 nm film**, q/Q = 2.105, separation **3.39 /um**, comfortably resolvable.

  Area (-4,-4), triad 24/84/144, commanded 24 deg, sigma 133 -- matched to the
  commensurate panels.

  | matched filter at | LDART before -> after | VDART before -> after |
  |---|---|---|
  | **template** period, 155 nm | 11.6 -> **150.9 pm**, z **+22.0**, p 0.008 | 6.1 -> **62.6 pm**, z **+38.4**, p 0.008 |
  | **film** period, 326 nm | 30.3 -> 18.2 pm, z **-0.5**, p 0.67 | 5.1 -> 8.7 pm, z **-0.3**, p 0.60 |

  **The modulation follows the template, not the film.** Nothing appears at the
  film's own periodicity. That is the imprint signature and it is unambiguous.

- **The no-write null, recovered for free.** Every before/after pair contains
  four corner patches of film that was never written, imaged twice with
  independent tunes. That is the null the whole comparison needs, and it was in
  the data all along -- the run built to measure it deliberately failed when a
  patch script silently did not apply its guard, and wrote a sigma 17 panel
  instead.

  | | ratio after/before | |
  |---|---|---|
  | unwritten corners, 14 pairs | **median 1.08** | 5-95 % 0.90-1.52, max 1.81 |
  | written interiors, 14 pairs | **median 10.16** | 1.28-17.54 |

  **13 of 14 interiors exceed the null MAXIMUM.** The changes are real; the
  question was only ever what they are changes IN.

- **The one exception is the most informative point in the set.** The
  accidental sigma 17 panel -- a quarter of the lowest dose that has ever
  worked -- gives:

  | channel | interior ratio | verdict |
  |---|---|---|
  | LDART (in-plane) | **1.28** | INSIDE the null (max 1.81): indistinguishable from doing nothing |
  | VDART (out-of-plane) | **4.16** | well outside it: the imprint is already there |

  **The out-of-plane imprint and the in-plane reorganisation have different
  thresholds.** At sigma 17 the bias has plainly written a P_z pattern and the
  in-plane director has not moved at all. They are not the same phenomenon, and
  the in-plane result cannot be dismissed as a read-back of the former.

**WHAT THIS UNDERMINES.** The campaign reads the director from an angular power
spectrum over the 150-500 nm band. A commensurate template has its sign period
INSIDE that band -- by construction, since commensurate means it equals the
film's period. So for every commensurate panel ever written, the imprint and
any genuine film response sit at the same wavevector and **the standard readout
cannot tell them apart**. That applies to [[M16]], [[M18]], [[M20]] and
[[M25]]. It does not make them wrong; it makes them unresolved.

**WHAT SURVIVES IT, and why the campaign is not back to zero.**

1. **[[M26]]**: a spatially UNIFORM write -- no periodicity anywhere in it --
   ordered a disordered region onto a triad member. No imprint is available as
   an explanation, because there is no pattern to imprint.
2. **The threshold decoupling above**: the in-plane response has a dose
   threshold the imprint does not.
3. **[[M18]]**: square and triangular lattices at the same Q gave the same
   outcome. Their real-space patterns differ, so a real-space imprint should
   differ; only the shared Q is common. This argues the effect is in the
   wavevector, though an imprint is also a wavevector-domain object, so it
   constrains rather than settles.
4. **[[M17]]**: written windows show lamellae running the full 1.4 um, far
   longer than the 110 nm site spacing of the template that made them.

**THE EXPERIMENT THAT SETTLES IT** is running: command a director **halfway
between two triad members**. Imprint predicts the readout at the commanded
midpoint; a film response predicts it snaps to a member 30 deg away. The 15 deg
hit criterion cannot be satisfied by both.

**Graded A.** The incommensurate control is properly resolvable, matched in
dose and voltage, and gives a clean split between two pre-registered
predictions. The null is measured, not assumed, on 14 pairs.

### M26 — A spatially UNIFORM write orders a disordered region onto a triad member: the film reorganises, and no imprint can explain it · **A**

- **Why it was run.** The operator's method for making nano-domains visible:
  "use the full +V scan and then full -V scan in the same area. In this way,
  the OP domains are homogeneous and it becomes easier to resolve the nano
  domains." It also happens to be the cleanest possible control for the
  imprint problem, which is why it is reported here as physics rather than as
  a preparation step.

- **Why it is imprint-free BY CONSTRUCTION.** The write is a 1.4 um raster at
  30 nm line pitch, executed as a **+V pass over the whole square followed by a
  -V pass over the same square**. The two polarities are separated in TIME, not
  in space, so the net spatial charge pattern is **uniform**. The only spatial
  period in the write is the 30 nm raster pitch, an order of magnitude below
  the 150-500 nm band the director is read in. There is nothing periodic to
  imprint. (Written as one file, so the net DC is exactly zero and S4 holds.)

- **Operation.** Area (+8,0), triad **16 / 76 / 136**, whole-frame modulation
  0.198 with the population on the 76 deg member (w = 0.18 / 0.63 / 0.19).
  sigma = 681 V.s/um^2 per polarity, the dose at which M13 demonstrated a full
  180 deg out-of-plane reversal. Frames `PZTO_LDART_0014/0015`.

- **End.** The 1.0 um panel interior, super band:

  | channel | | direction | period | anisotropy | p |
  |---|---|---|---|---|---|
  | LDART | before | 78.8 deg | 266 nm | 3.44 | 0.046 |
  | LDART | **after** | **18.8 deg** | 202 nm | **8.51** | **0.007** |
  | VDART | before | 63.8 deg | 243 nm | 1.39 | 0.93 -- no direction |
  | VDART | **after** | **26.2 deg** | 196 nm | **4.83** | **0.007** |

  The in-plane director was on member **76** before and member **16** after: a
  clean **60 degree rotation**, with the anisotropy rising 2.5x as the stack
  ordered. The out-of-plane channel had no direction at all before and acquired
  one at the same place afterwards.

  **CORRECTION.** As first written this entry reported the before state as
  "63.8 deg, aniso 1.39, p 0.93 -- no direction at all" and called the result
  disorder-to-order. Those numbers are the **VDART** row of the log, not the
  LDART row; they were read off the line immediately above the S24 message
  without checking which channel it belonged to. The LDART before-frame has a
  perfectly good direction on member 76 (aniso 3.44, p 0.046, stable across
  every n_perm and seed tested). The result is a 60 deg ROTATION, not the
  ordering of a disordered region -- a different and rather stronger claim,
  since the starting state was well defined.

**What this establishes.** The in-plane reorganisation is a genuine response of
the film, not a read-back of the written pattern. Every other write in this
campaign carries its own periodicity, so "the film adopted the commanded
director" and "we are measuring the pattern we wrote" have never been
separable. Here the write has no periodicity and the film still produced one,
at its own length scale, on an allowed member. This is [[M14]] reproduced at
4x the resolution with a modern estimator and an explicit imprint control.

**What it does NOT settle, and it is the same open question as [[M23]].** The
poling raster ran along **0 deg**, and member 16 is the triad member nearest
that direction. So "the film has a preferred member" and "the write direction
selects whichever member lies nearest it" both predict this result. M23 found
that every selection failure in the campaign defected to this same ~16-19 deg
member, and PITFALLS 21.6 found that the lateral channel carries broadband
structure within 6 deg of the fast scan axis. Three independent observations
now point at the same direction, and none of them separates film from
instrument.

**The experiment that separates them, and it is one write.** Repeat this poling
with the raster rotated to 60 deg. If the film then orders on member 76, the
attractor follows the WRITE and the preference is instrumental. If it orders on
member 16 again, the preference belongs to the film. Same area type, same dose,
same everything else.

**The operator's stated purpose was not achieved.** After poling, the fine band
(18-90 nm) is still dominated by the fast-axis artefact in both channels
(LDART 70.3 nm at 0.5 deg, VDART 75.9 nm at 2.5 deg). Homogenising the
out-of-plane state did not make nano-domains visible at 4.88 nm/px. Either they
are finer than this sampling resolves, or they need the in-plane super-domain
to be written as well, or this probe does not resolve them. A 1.5 um frame at
512 px would give 2.93 nm/px and costs no write budget.

**Graded A.** One panel, but the control is structural rather than statistical:
a uniform write cannot imprint a periodic pattern, so the alternative
explanation is not merely unlikely, it is unavailable. The direction it lands
on is a separate question, flagged above.

### M25 — Selection reproduces on a new probe, a new stage position and a 2x smaller frame: 5 panels of 5, median 2.3 deg · **A**

- **Why it matters.** Every selection result before today was taken with one
  probe, on 5 um frames with 1.4 um panels. A new probe and a 2.5 um frame
  change the tip, the contact resonances (635/343 kHz against 650/350), the
  pixel size (4.88 against 19.5 nm/px) and the panel geometry at once. If the
  effect were an artefact of any of those, this is where it would break.

- **Operation.** Five single-panel runs, sample position 7, 2.5 um frames at
  512 px / 2.0 Hz, one 1.2 um panel centred, Lambda measured per area, each
  panel commanded to a member **60 deg from that area's own incumbent** (S22).

  | area | Lambda | modulation | sigma | commanded | adopted | offset |
  |---|---|---|---|---|---|---|
  | (0, 0) | 224 nm | 0.273 | 133 | 16.5 | 18.8 | **2.3 deg** |
  | (+4, 0) | 225 nm | 0.167 | 122 | 4.0 | 176.2 | **7.8 deg** |
  | (-4, 0) | 253 nm | 0.294 | 130 | 19.0 | 18.8 | **0.2 deg** |
  | (0, +4) | 242 nm | 0.206 | 53 | 21.5 | 26.2 | **4.7 deg** |
  | (0, -4) | 251 nm | 0.183 | 263 | 16.5 | 18.8 | **2.3 deg** |

  **5 of 5 within 8 deg, median 2.3 deg.** Every panel started 60 deg away and
  every panel arrived. Combined with [[M20]]'s 30 of 34 on the previous probe,
  selection is now 35 of 39 across two probes, two stage positions and two
  frame sizes.

- **It works at sigma 53.** The lowest dose here is 53 V.s/um^2 and it landed
  4.7 deg from target, consistent with [[M20]]'s bound of 52. The threshold has
  still never been crossed downward on valid film.

- **It works at modulation 0.167.** The (+4,0) area sits below the 0.18 floor
  the old area-screening gate used, and it still hit at 7.8 deg. That gate was
  calibrated for 5 um frames and is too strict at this scale.

**A large modulation at the template wavevector appears in BOTH channels after
every write.** Matched filter at the commanded direction and the template
period, panel interior, before -> after:

  | area | LDART | VDART |
  |---|---|---|
  | (0, 0) | 24.6 -> 150.3 pm (z +12.1) | 10.3 -> 122.3 pm (**z +55.4**) |
  | (+4, 0) | 7.1 -> 125.0 pm (z +13.9) | 14.1 -> 179.3 pm (z +40.4) |
  | (-4, 0) | 29.0 -> 152.3 pm (z +8.8) | 12.5 -> 158.2 pm (z +15.7) |
  | (0, +4) | 7.3 -> 95.2 pm (z +7.3) | 18.0 -> 140.7 pm (z +29.6) |
  | (0, -4) | 40.6 -> 208.9 pm (z +17.8) | 20.2 -> 202.6 pm (z +41.0) |

  The out-of-plane response is the CLEANER of the two: at (0,0) the VDART
  anisotropy after writing is 28.7 against LDART's 6.0, and both channels sit
  at the same direction (18.75 deg) and period (230.8 nm) to three figures.
  On virgin film there was no out-of-plane modulation at all at the in-plane
  wavevector ([[M24]], < 5 pm).

**WHAT THIS DOES NOT YET ESTABLISH, and the trap that was nearly walked into.**
The template alternates polarity every Lambda/2, so a P_z modulation at the
template period is ALSO what a passive imprint would produce -- each +- site
writing its own patch, with no cooperation from the film. The control written
to separate these used a template period of 328 nm against a 253 nm film, and
**that control had no power**: the two periods are separated by 0.90 /um while
a 1.0 um window resolves 1.00 /um, so they sit inside one resolution element
(PITFALLS 21.8). The analysis nevertheless printed a confident verdict, which
has been withdrawn.

A properly resolvable control at **q/Q = 1.618** is running, together with a
**no-write null** -- two before-pairs and two after-pairs at one area with no
write at all -- because every number in the table above is a before/after
difference and none of them is interpretable until the size of a no-write
difference is known.

**Graded A for the selection result**, which is a straight repeat of an
established effect under changed conditions and does not depend on any of the
above. The modulation table is reported but NOT interpreted.

### M24 — On VIRGIN film there is no P_z modulation at the in-plane wavevector, and no independent nano-domain periodicity · **B**

- **Why it matters.** The manuscript's selection term is −∫P_z E_z, which is
  non-zero only when the template wavevector matches an EXISTING P_z modulation
  in the film: **q = Q**. The campaign has assumed that modulation for two
  weeks and never measured it. Every angle to date came from the lateral
  channel. A new probe with a live VDART makes it measurable.

- **Operation.** New probe (LDART 635 kHz, VDART 343 kHz measured; 100 % of
  lines tracked in both), new stage position, sample position 7. One 2.5 um
  frame at 512 px = **4.88 nm/px**, 2.0 Hz, in each channel at the same offset,
  on untouched film. `PZTO_LDART_0000.ibw` and `PZTO_VDART_0000.ibw`.

- **The in-plane state.** Triad 16/76/136, modulation 0.273, streak 0.019.
  Super-domain director **76.8 deg**, period **223.6 nm**, p = 0.007. The
  independent rigid-triad fit puts the dominant population on the 76 deg member
  at w = 0.57. Two estimators, 0.3 deg apart.

- **The out-of-plane state, by matched filter at the SAME wavevector.** The
  direction and period are known from LDART, so this is a one-parameter test
  rather than a search, which is where the sensitivity comes from.

  | channel | amplitude at Q | z | p |
  |---|---|---|---|
  | **LDART** (positive control) | **22.3 pm** | +3.1 | **0.008** |
  | **VDART** | 7.3 pm | +1.4 | 0.15 |

  The filter finds the in-plane modulation it is supposed to find, and finds
  nothing out-of-plane at the same wavevector.

- **The null has a number on it (§12.3).** Injecting a known modulation into
  the REAL VDART frame at the LDART wavevector and re-running the same test:

  | injected | measured amp | z | p | detected |
  |---|---|---|---|---|
  | 0 pm | 7.28 | +1.4 | 0.145 | no |
  | 2 pm | 8.65 | +2.0 | 0.076 | no |
  | 3 pm | 9.76 | +2.4 | 0.031 | no |
  | **5 pm** | 12.45 | +3.6 | **0.008** | **yes** |

  So **any P_z modulation at the in-plane Q is below ~5 pm**, against an
  in-plane modulation of 22.3 pm at the same wavevector -- under ~23 % of it,
  and consistent with zero.

  A blind angular-band search on the same frame only reached 20 pm, four times
  worse. The gain is entirely from not searching: the blind test spends its
  power over every angle and period in the band.

- **No independent nano-domain periodicity either.** The only short-period
  feature is at **119 nm**, which is the **second harmonic** of the 219 nm
  lamellae -- half the period, same director (83 deg against the fundamental's
  76.8). Everything else in the fine band is broadband power within 6 deg of the
  fast scan axis, identified by the fact that **its reported period tracks the
  analysis window** (38 nm in an 18-40 band, 58 in 30-60, 86 in 45-90, 114 in
  60-120). A real periodicity does not do that. See PITFALLS 21.5 and 21.6.

**What this changes.** The manuscript states the selection term as a coupling to
a pre-existing P_z modulation. On virgin film that modulation is not there. Two
readings survive:

1. **The write CREATES it.** The operator reports that the nano-domains are
   often invisible until the in-plane super-domain is written or aligned. If a
   commensurate template generates a P_z modulation at its own wavevector, then
   selection is **self-reinforcing** rather than a coupling to existing order --
   and that would also explain why a large, already-written super-domain
   resists rewriting by a trace ([[M19]]): it has its own locked-in modulation
   to overcome. This is the reading the next run tests directly.
2. **The selection term is not −∫P_z E_z at all** and the mechanism is
   purely in-plane. [[M18]] would still stand -- selection is set by Q and not
   by the point arrangement is an experimental fact -- but its explanation
   would need rebuilding.

**Graded B.** One area, one frame per channel. The estimator is validated
against synthetic negative controls (PITFALLS 21.1-21.4) and the null is
bounded by injection rather than asserted. It is not A because a single virgin
area cannot exclude that some other area carries the modulation, and because
the VDART channel is weaker than the LDART one (|S| 38.9 against 74.3 pm), so
the 5 pm bound is specific to this frame's noise.

### M23 — The three "degenerate" members are NOT equally writable: every failure is a defection to member 0 · **B**

- **Free.** Re-analysis of the 34 targeted panels that pass the 4-Lambda gate.
  No instrument time. It was found by asking a question nobody had asked:
  *where* are the misses, rather than *how many*.

- **The result.**

  | commanded member | panels | hit | miss |
  |---|---|---|---|
  | 0 (~17 deg in the pinned triad) | 22 | **22** | 0 |
  | 1 (~75 deg) | 3 | **3** | 0 |
  | 2 (~135 deg) | 9 | 5 | **4** |

  Fisher exact, member 2 against the other two: **p = 0.0027**.

- **The obvious confound is broken by the data.** Member 2 was always commanded
  on the P2 panel, so "member 2 is hard" and "P2 is a bad position" are
  entangled -- except that **P2 was also commanded to member 0 nine times and hit
  nine times out of nine**. Restricted to P2 alone the comparison is 4/9 miss
  against 0/9, p = 0.082: the same direction, at the power nine panels allow.
  Position is not the variable.

- **All four failures land on member 0.** Final directors 0, 20, 0 and 10 deg,
  against commanded 134, 136, 132 and 132.

- **This supersedes M21.** M21 read the defections as lateral crosstalk --
  a panel adopting its NEIGHBOUR's commanded director. Three of the four are
  consistent with that. **The fourth is not, and it is decisive**: in run
  260829_0153 the neighbour was commanded to member 1 (71.5 deg) and stayed
  there, while the failing panel went from 65 deg to 0 deg -- to a member that
  NOTHING in that frame was commanded to. "Defects to the neighbour" and
  "defects to member 0" agree on three cases and disagree on one; the data pick
  the second. M21's underpowered gap test (Fisher p = 1.000) is then unsurprising
  rather than merely inconclusive: it was varying the wrong variable.

- **Member 0 is an attractor for the whole film, not just for failures.**
  Across the same 36 valid frames:

  | | member 0 | member 1 | member 2 |
  |---|---|---|---|
  | dominant BEFORE any write | 22 % | 64 % | 14 % |
  | dominant AFTER the write | **72 %** | 14 % | 14 % |

  The virgin film prefers member 1; after writing, the population piles onto
  member 0 far beyond what the commands alone require.

- **It is not a readout gradient, and the shape of the failure says so.** The
  outcome is **bimodal, not graded**: when a member-2 command succeeds it lands
  at 1.0-4.0 deg (five panels: 1.5, 1.5, 1.5, 4.0, 1.0), and when it fails it
  lands on the wrong member entirely. A channel that merely under-detects one
  orientation would blur member-2 panels toward their neighbours in proportion
  to how weak the signal is; it would not give five near-perfect hits and four
  clean defections. Partial suppression could still tip a marginal case, so this
  argument constrains the explanation without closing it.

**Two explanations remain, and they are cleanly separable.**

1. **The film.** The three members are degenerate by symmetry but not by
   history: strain, miscut or the previous domain configuration makes member 0
   the deepest well, so a command that fights it sometimes loses.
2. **The instrument.** The tip rasters along the lab x-axis, and member 0 sits
   closest to it (~15 deg). Any scan-borne contribution -- trailing field,
   asymmetric contact, a shear component along the fast axis -- would bias the
   result toward whichever member lies nearest the scan direction, entirely
   independent of the film.

**The experiment that decides it, and it costs no write budget.** Rotate the
scan by 60 deg and re-image the existing panels, then write one new set under
the rotated scan.
  * If the favoured member **follows the scan** -- i.e. the new attractor is
    whichever member now lies nearest the fast axis -- the bias is instrumental,
    and every angle-dependent statement in this campaign needs a correction.
  * If it **stays with the same crystallographic member**, the degeneracy is
    genuinely broken by the film, which is a stronger and far more interesting
    result than uniform selection: it means the template competes against a
    pre-existing preference, and the size of that preference is measurable.
Scan rotation is already characterised (M10: rotating by +phi moves measured
angles by +phi), so the analysis needs no new machinery.

**Why this matters for the manuscript.** "Any of three members on demand" is the
headline claim, and it is **not true as stated**: it holds for 25 of 25 panels on
two members and 5 of 9 on the third. Stating the asymmetry, and either explaining
it or bounding it, is the difference between a result and a result a referee will
believe.

**Graded B.** The pattern is strong (p = 0.0027), the position confound is
broken by an internal control, and the bimodality argues against the simplest
readout explanation. It is not A because the film-versus-instrument question is
open and one 60 deg scan-rotation series would answer it.

### M22 — The switching pathway, imaged: the rewrite is confined to the panel and complete inside it above a dose between 52 and 67 · **B**

- **Free.** Six 2 um / 256 px frames = **7.81 nm/px**, 33-38 px per lamellar
  period, on panels already written. No S24 minutes, which mattered because the
  cap was reached at 329.5 of 330.

**CORRECTED, AND THE FIRST VERSION WAS WRONG.** As first written, M22 classified
each zoom as UNIFORM or MIXED from four 1.12 um FFT tiles, and reported
"fragmented at sigma 52, uniform at sigma 117". **The written panel is 1.2-1.4 um
across and sits in the middle of a 2.0 um frame, so every one of those tiles
overhangs the panel edge by 0.3-0.4 um and samples unwritten film.** "Three tiles
agree, one differs" is exactly what an edge overhang produces whether or not
anything inside the panel is coexisting. The tell was the completed series: by
that classifier **sigma 306 also reads MIXED** while sigma 67 reads UNIFORM,
which is not a dose ordering at all. See PITFALLS 20.8.

**The corrected measurement.** Same frames, same structure-tensor estimator
(150 nm smoothing, so it needs no 4 Lambda), but two regions of each frame:

  * **INTERIOR** -- the central 1.0 um, inside even the smallest panel;
  * **SURROUND** -- beyond 1.5 um, outside even the largest panel.

The surround is an internal control taken from the *same frame, same tip, same
tune* as the interior, which the original whole-frame statistic did not have.

| sigma | frame | interior: dominant member holds | surround: dominant | reading |
|---|---|---|---|---|
| **52** | 0247 | **50 %** (50/50 split) | 56 % on a different member | **caught mid-transition** |
| 67 | 0248 | **99 %** | 78 % on a different member | complete |
| 111 | 0251 | **97 %** | 52 % on a different member | complete |
| 117 | 0246 | **100 %** | 55 % on a different member | complete |
| 120 | 0250 | **78 %** | 78 % on a different member | incomplete -- see below |
| 306 | 0249 | **97 %** | 90 % on a different member | complete |

**Result 1 -- the rewrite is confined to the panel and complete inside it.** In
**all six** frames the interior and the surround sit on **different** triad
members. The written region is a distinct domain with an edge sharp at the
150 nm smoothing scale, not a gradient. This is a positive result the original
whole-frame analysis could not have produced, because it averaged the two
regions together.

**Result 2 -- completion has a dose threshold, and it is between 52 and 67.**
At sigma 52 the interior is a genuine 50/50 coexistence of two members in two
large patches -- the transition caught part-way. From 67 upward the interior is
97-100 % single-orientation. That is a **nucleation-and-growth** pathway: the new
orientation appears, expands, and consumes the region, and above completion extra
dose has nothing left to do. The correlation of interior uniformity with
log(dose) is r = 0.53 on n = 6, which is the wrong statistic for a threshold and
is quoted only to show it was checked; the ordering, not the correlation, is the
result.

**Result 3 -- the one exception is a member-2 panel, and that is [[M23]] again.**
The sigma 120 panel reaches only 78 % at a dose where member-0 panels reach
97-100 %. It was commanded to member 2 (139 deg) and the coarse 5 um readout
scored it a HIT at 4.0 deg offset. The fine readout says it is only three
quarters switched. **Two independent estimators, on different frames at different
magnifications, both single out member 2.** The FFT populations say member-2
commands fail outright 4 times in 9; the structure tensor says that even when
they succeed they switch less completely.

**It also explains M20's most puzzling number.** Above threshold the final
population does not increase with dose (0.40-0.95 over a 2.6x range). If the
transition runs by growth to completion, once the region is consumed there is
nothing for extra dose to do, and the residual scatter is set by how much of the
readout window the domain fills -- by AREA, not by dose.

**Graded B.** One panel per dose, the doses come from different areas, and the
threshold rests on a single frame at sigma 52. What survives area-confounding is
Result 1, which is an internal comparison within each frame and holds six times
out of six. **What would finish it:** a dose ladder of four panels at 40, 55, 70
and 120 **inside a single frame**, zoomed. About 2 write-minutes and one 5 um
frame, giving the growth curve at fixed area, fixed tip and fixed readout.

### M21 — SUPERSEDED BY M23 — Every failed panel adopted its NEIGHBOUR's director: evidence for lateral crosstalk at 2 um · **C**

> **Superseded.** [[M23]] shows the failures are better described as defections to **member 0** than to the neighbour. The two readings agree on three of the four cases and disagree on the fourth, where the neighbour was commanded to member 1 and the failing panel went to member 0 anyway. Crosstalk is not excluded, but it is no longer the leading explanation and the gap test below was varying a variable that may not matter.

- **Observation.** Across 24 lattice panels on valid film (readout window >= 4
  Lambda, PITFALLS 19.15), 22 reached their own commensurate member with a
  median offset of 1.5 deg. **Both** of the two that did not landed on the
  director commanded for the OTHER panel in the same frame:

  | run | panel | wanted | before | after | off own | off NEIGHBOUR |
  |---|---|---|---|---|---|---|
  | (0,+8) | P1 | 14.0 | 0 | 10 | **4.0** | 56.0 |
  | (0,+8) | P2 | 134.0 | 70 | **0** | 46.0 | **14.0** |
  | (16,16) | P1 | 16.5 | 90 | 10 | **6.5** | 53.5 |
  | (16,16) | P2 | 136.5 | 90 | **20** | 63.5 | **3.5** |

  In both cases P1 hit and P2 defected to P1's member. Panels are 1.4 um wide
  with centres 2.0 um apart, i.e. a 0.6 um edge-to-edge gap.

- **Why it is plausible.** A written region is a large, strongly ordered
  single-director domain (w up to 0.95). If its boundary can advance, the
  nearest neighbouring region is what it advances into. That is the same
  nucleation-and-growth picture M17 established inside a panel, operating
  between panels.

- **Consistent with the rest of the dataset.** Misses occur ONLY in `select`
  runs, the one design where the two panels carry different targets. Every
  `dose` and `shear` run -- both panels sharing a target -- was on target, and
  in those designs crosstalk is invisible by construction, not absent. Two of
  five `select` runs showed a defection.

- **Graded C, and the reason is arithmetic.** With three triad members a random
  miss lands within 15 deg of the neighbour's target about one time in three, so
  two out of two is p ~ 0.11 by chance alone. **This is a hypothesis with a
  suggestive n = 2, not a result.** It is recorded now because it makes a sharp
  prediction and because it is the only pattern that explains any of the
  failures.

- **The discriminating experiment.** Increase the panel separation and see
  whether defections stop. If crosstalk is real the defection rate must fall
  with gap; if the misses are random the rate will not move. A second
  prediction: a single panel written alone, with no neighbour, should never
  defect.


**TESTED, ROUND 3, AND THE TEST WAS UNDERPOWERED.** Six further `select` runs
were written specifically to vary the one variable that matters: three at the
0.6 um gap that produced the defections, three at 1.8 um, with dose, targets,
panel count and readout otherwise identical.

| gap | panels | defections |
|---|---|---|
| 0.6 um | 14 | **3 (21 %)** |
| 1.8 um | 4 | **0 (0 %)** |

Fisher exact, two-sided: **p = 1.000**. And P(0 defections in 4 panels, given
the narrow arm's 21 % rate) = **0.38** -- seeing zero in the wide arm is the
likely outcome *even if the gap changes nothing*. The direction is right and the
comparison is worthless. One wide run was lost to the 4-Lambda guard (its area
measured Lambda 388 nm at run time despite screening at 245), which cost two of
the six wide panels and most of what power there was.

**Where the pattern stands after 18 different-target panels:** 14 hit, 3
defected to the neighbour's member, 1 missed both. **3 of 4 misses landed on the
neighbour**, p = 0.31 against chance. That is the same suggestive-but-not-
significant picture as before, with three times the data. The hypothesis has
survived a real attempt to test it and has not been confirmed.

**What it would take.** At a 21 % narrow rate, distinguishing it from 0 % needs
roughly 20 panels per arm for 80 % power -- about 10 `select` runs per gap. At
1.1 write-minutes each that is ~22 minutes of S24 budget, which did not exist
tonight (the cap was reached at 329.5 of 330). It is a cheap experiment for a
session that starts with budget.

**Grade stays C.** Three of four misses landing on a neighbour is a real pattern
in the data and the only candidate explanation for any failure, but it is not
established, and the one controlled test performed could not have detected it.

- **If it holds, it matters for the application.** It sets a minimum pitch for
  independently addressable features -- at a 0.6 um gap the neighbours are not
  independent -- and it is the first evidence in this campaign that written
  regions interact at all. Retention and crosstalk were listed as untested in
  the manuscript draft; this is the first data on the second.

### M20 — Template selection is REPEATABLE: 12 of 13 panels reached their own commensurate member, and the lattice works far below the solid square's threshold · **A**

- **Why it was run.** M16 and M18 each rested on one or two panels. A claim of
  deterministic, addressable selection needs a repeatability statistic, not an
  anecdote.
- **Operation.** `run_campaign.py`, sample position 6, 8 queued jobs across 8
  independently screened areas (Lambda 245-354 nm, modulation 0.216-0.280,
  triad 14/74/134). Seven completed; the eighth aborted correctly on the C21
  per-site charge limit (see below). Every panel's populations, dominant, dose,
  excess and null go to `results_templates.csv`, and the numbers here are read
  from that file, not retyped from logs.

**REPEATABILITY.** For each lattice panel, did the director end on the member
that panel's own template selects?

  | experiment | lines along | ended on | offset |
  |---|---|---|---|
  | select | 14.0 | 10 | 4.0 deg |
  | select | 134.0 | 0 | **46 deg -- MISS** |
  | select | 76.5 | 80 | 3.5 deg |
  | select | 136.5 | 135 | 1.5 deg |
  | control | 11.5 | 10 | 1.5 deg |
  | dose2 | 19.0 | 20 | 1.0 deg |
  | dose2 | 19.0 | 20 | 1.0 deg |
  | dose1 | 21.5 | 20 | 1.5 deg |
  | dose1 | 21.5 | 20 | 1.5 deg |
  | dose3 | 11.5 | 10 | 1.5 deg |
  | dose3 | 11.5 | 10 | 1.5 deg |
  | shear | 19.0 | 20 | 1.0 deg |
  | shear | 19.0 | 20 | 1.0 deg |

  **12 of 13 hit within 4 deg; median offset 1.5 deg.** Every panel cleared its
  own leave-one-out null (6.9x to 38.3x). The one miss is the second panel of
  the (0,+8) run, which went to 0 deg instead of 134; that run is the only one
  the driver labelled "DRIVE alone", and it is reported as a miss rather than
  excluded.

**THE LATTICE THRESHOLD IS MUCH LOWER THAN THE SOLID SQUARE'S.** M15 put the
threshold for a solid, aperiodic square between **400 and 667** V.s/um^2. A
commensurate lattice rewrote at **sigma 306** -- the lowest dose tried in this
series -- clearing its null by 10.4x and landing 1.5 deg from target:

  | sigma | w on the target member, after | gain | x null |
  |---|---|---|---|
  | 306 | 0.642 | +0.129 | 10.4 |
  | 392 | 0.883 | +0.526 | 11.5 |
  | 469 | 0.654 | +0.144 | 11.6 |
  | 522 | 0.947 | +0.518 | 11.4 |
  | 536 | 0.889 | +0.430 | 27.2 |
  | 663-673 | 0.483-0.800 | +0.25 to +0.43 | 6.9-34.0 |
  | 803 | 0.778 | +0.603 | 38.3 |

**Two things follow.**

1. **Commensurability lowers the cost of rewriting, it does not only choose the
   direction.** A template that matches the film's own period achieves at
   sigma 306 what an aperiodic patch could not do reliably at 400. Selection and
   drive are not independent terms simply added together; the matched wavevector
   reduces the dose required.
2. **Above threshold the outcome is not graded.** Across 306-803 -- a factor of
   2.6 in dose -- the final population on the target member scatters 0.40-0.95
   with no monotonic trend, and the variation tracks the AREA rather than the
   dose. That is what a barrier crossing looks like: once over, the region goes,
   and more dose does not push it further. It is independently consistent with
   M17, where the transition proceeds by replacement rather than by progressive
   rotation.

**The lower bound keeps falling.** `dose4` at area (8,8) then rewrote at
**sigma 144** (12.7x null) and **sigma 222** (50.2x null), both landing on the
76 deg member. So the commensurate lattice works at **less than half** the
400-667 V.s/um^2 an aperiodic square needs, and the true lattice threshold is
still below 144. `dose5` (75/110) and `dose6` (40/60) continue the search; each
costs under a write-minute because dwell scales with dose.

  | sigma | x null | outcome |
  |---|---|---|
  | 144 | 12.7 | rewrote |
  | 222 | 50.2 | rewrote |
  | 306 | 10.4 | rewrote |
  | 392-803 | 11.4-38.3 | rewrote |

**This is the sharpest quantitative statement the campaign has.** Matching the
template's wavevector to the film's own period cuts the dose needed to rewrite
by at least 3x. Selection is not a passive direction-chooser bolted onto drive;
it lowers the barrier.

**A real constraint discovered by the eighth job.** Per-site charge is
sigma*area/(n*V), and n falls as Lambda grows. At Lambda 354 nm a 1.4 um panel
holds only 64 sites, so sigma 667 needs **20.4 V.s per site** -- over C21's 20
V.s half-limit -- and the run aborted before writing. The gate was right. The
driver now caps sigma at the charge limit and says so, rather than losing the
area. **Coarse film cannot be written as hard as fine film**, which is a
practical limit worth stating in any recipe.

### M19 — A continuous trace CAN rewrite an ordered super-domain; the practical difficulty is dose, not continuity · **B**

- **The report (operator, 28 Aug).** Once a large IP super-domain has been
  written, pure scan-trace trajectory litho struggles to re-orient it, while a
  point-pulse lattice still succeeds.
- **Two explanations fit**, and the morning's control experiment could not
  separate them because its solid raster differed from the lattice in BOTH
  respects at once:
  **A**, the trace carries no commensurate Q so it can only drive (M16/M18);
  **B**, stationary pulses nucleate a new orientation and a moving tip cannot.
- **Operation.** `run_rewrite.py`, area (-8,-8), Lambda 301 nm, triad 16/76/136.
  Stage 1 wrote a lattice along **16 deg** over the whole 3.4 x 4.7 um
  measurement zone (708 sites, 15.2 V.s/site, 17.9 min), manufacturing the
  ordered domain: modulation **0.273 -> 0.547**, mean population 0.615 on the
  16 deg member, every window dominant at 10-20 deg. Stage 2 then attempted to
  rewrite two 1.4 um panels inside that ordered zone to **136 deg**:

  | panel | template | \|S\| at Q | sigma | points |
  |---|---|---|---|---|
  | P1 | **continuous trace**, 13 strokes x 5 passes | **1.000** | 665 | 3300 |
  | P2 | **pulsed lattice**, 84 sites x 39 pulses | **1.000** | 669 | 3276 |

  Matched in line direction, line spacing, wavevector and dose. The only
  difference is stationary pulses versus a moving biased tip.

- **End.** Four control windows inside the ordered zone, not rewritten:
  null **0.048**, dominants 145->145, 90->90, 20->10, 15->15.

  | panel | w before | w after | dominant | excess |
  |---|---|---|---|---|
  | **P1 trace** | 0.612 / 0.190 / 0.198 | 0.341 / 0.174 / **0.485** | 10 -> **135 deg** | 0.274 = **5.7x** null |
  | **P2 lattice** | 0.464 / 0.243 / 0.292 | 0.275 / 0.100 / **0.624** | 20 -> **135 deg** | 0.320 = **6.6x** null |

  **Both rewrote, and both landed on 135 deg -- the 136 deg target.**

**Explanation B is excluded.** At matched dose and matched Q a continuous trace
re-orients an ordered domain as well as a pulse lattice does. Continuity is not
the barrier and pulsing is not required.

**The arithmetic that explains the report.** For a continuous trace of line
pitch d traversed at speed s, the areal dose is **sigma = V / (d s)** -- it does
not depend on how long the panel is, only on how fast the tip crosses it:

  | speed (um/s) | sigma (V.s/um^2) | vs the 400-667 threshold | passes for 667 |
  |---|---|---|---|
  | 0.25 | 266 | 1.5x below | 3 |
  | 0.50 | 133 | 3x below | 5 |
  | 1.0 | 66 | 6x below | 10 |
  | 2.0 | 33 | **12x below** | 20 |
  | 5.0 | 13 | **30x below** | 50 |

A single-pass trace at any practical scan speed lands far below the M15
threshold. **The tip is over any given spot for microseconds**, whereas a
lattice site receives 39 pulses of 0.4 ms. A trace looks as though it deposits
plenty of charge and does not. That accounts for the reported behaviour with no
new physics: this run only succeeded because it made five passes.

**Practical consequence.** To rewrite with a trace, either slow to <= 0.25 um/s
or make >= 5 passes; a lattice reaches the same dose in one visit because dwell
time is decoupled from travel. That is the real advantage of the pulse lattice,
and it is a throughput argument rather than a mechanistic one.

**Graded B, and the reasons are specific.**
1. **One area, one pair.** No repeat.
2. **The lattice was marginally stronger** -- 6.6x vs 5.7x, w 0.624 vs 0.485.
   That is a 1.2x difference against a null-limited measurement and is NOT
   resolvable here. It may be a genuine secondary advantage of pulsing; it may
   be that P1 and P2 started from slightly different populations (0.198 vs
   0.292 on the target member). Repeats with the panels swapped would settle it.
3. **This trace carried the commensurate Q by construction**, which real
   scan-trace litho at an arbitrary raster pitch does not. Whether
   commensurability is separately required to rewrite ORDERED film is the
   `MODE=noQ` run, which gives the trace a non-commensurate pitch.
4. **A labelling caveat in the log.** This run used `SKIP_PRE`, so the columns
   printed as "w virgin" and "w ordered" are the SAME frame -- the already
   ordered state. The numbers are right; the header is misleading.

### M18 — Shearing the lattice from square to triangular does not move the selected director: selection is set by Q, not by the point arrangement · **A**

- **The prediction, made before the run.** In `lattice_panel`-style templates
  the sign depends on the LINE INDEX alone, so the structure factor factorises:

      S(q) = [ sum_i e^{-i q.u i a} ] x [ sum_j (-1)^j e^{-i j (q.u s + q.n d)} ]

  On the pure perpendicular (q.u = 0) the second factor peaks at
  q.n = pi/d = 2 pi / Lambda whatever the along-line offset s, and the first
  factor is at its maximum there. **Shearing the lattice therefore leaves the
  commensurate wavevector untouched.** Measured on the built templates before
  writing: |S| at **Q** = **1.000** for lattice angles 90, 75 and 60 deg alike.
  T3's selection term predicts shear changes nothing about which member is
  chosen.

- **Operation.** `run_template.py EXP=shear`, area (0,+8), Lambda 280 nm,
  triad 16/76/136, incumbent 76 deg. Both panels have lines along **16 deg** --
  same direction, same Q -- and differ only in the lattice:

  | panel | lattice | basis | offset per line | sites | sigma | V.s/site |
  |---|---|---|---|---|---|---|
  | P1 | **square**, chains at 90 deg | 140 nm | 0 nm | 100 | 673 | 13.2 |
  | P2 | **triangular**, chains at 60/120 deg | 161 nm | 81 nm | 86 | 667 | 15.2 |

- **End.**

  | window | w before | w after | dominant | excess |
  |---|---|---|---|---|
  | **P1 square** | 0.448 / 0.361 / 0.191 | **0.902** / 0.032 / 0.066 | 70 -> **10 deg** | 0.465 = **23.0x** null |
  | **P2 triangular** | 0.249 / 0.409 / 0.343 | **0.808** / 0.041 / 0.151 | 90 -> **10 deg** | 0.570 = **28.3x** null |
  | ctrl1-4 | - | - | 70->70, 65->0, 80->80, 45->45 | null **0.020** |

  Whole-frame modulation 0.200 -> 0.453.

**Result: both lattices drove the director to the SAME member, 10 deg** -- the
member their shared Q selects -- from *different* starting dominants (70 and
90 deg). Changing the real-space arrangement from square to triangular, at
matched dose and matched Q, moved the destination not at all.

**So the selection term depends on the template's WAVEVECTOR and not on where
the individual pulses sit.** That is a non-trivial confirmation of T3's
q = Q condition: two lattices that look quite different under the microscope,
with different basis vectors, different site counts and different
nearest-neighbour chains, are equivalent to the film because their sign
modulation has the same period and direction.

**Effectiveness is also unchanged.** The two panels reached w = 0.902 and 0.808,
and the CHANGES were +0.454 and +0.559 -- the triangular lattice moved the film
slightly further, having started further away. There is no evidence that either
arrangement writes better.

**What this does not cover.** Only one shear pair, at one Lambda, one dose and
one line direction. 30 deg was not reachable at matched dose: it halves the site
density, which doubles per-site charge to ~30 V.s and breaks C21's 20 V.s
half-limit, so it would have required a lower dose and stopped being a matched
comparison.

### M17 — The nano-domains are RESOLVED, and a rewrite replaces the disordered stack rather than rotating it · **A**

- **Can they be seen?** Yes, at the standard readout. 5 um frame, 256 px ->
  **19.5 nm/px**, and Lambda = 301 nm is **15.4 px per period**, comfortably
  above the 2 px Nyquist limit. Individual lamellae are resolved in the raw
  LDART maps with no special settings. Individual domain WALLS, a few nm wide,
  are not, and nothing here should be read as a statement about wall structure.
- **Operation:** the same 1.4 um window, before and after, from the M16 control
  experiment: written panel P2 (parallel lattice, lines along 14 deg) against
  untouched control c4 in the same two frames. Frames PZTO_LDART_0160 (before)
  and 0161 (after).
- **End:**

  | window | before | after |
  |---|---|---|
  | **written** | mottled, isotropic-looking blobs | **long parallel lamellae**, running the full 1.4 um |
  | control | mottled blobs | mottled blobs, unchanged |

  Angular power in the written window collapses from **broad and multi-peaked**
  -- a main lobe near 90 deg with satellites near 110, 125 and 155 -- to a
  **single narrow peak near 15 deg with essentially zero power above 30 deg**.
  The control's angular power is broad and multi-peaked both before and after.

**The mechanism this rules out and the one it supports.** A gradual rotation
would move the angular-power peak through the intermediate angles and would show
transient power at 45-70 deg. Nothing of the sort appears: power at the old
orientations simply disappears and appears at the new one. The disordered
multi-domain stack is **replaced** by a single-orientation lamellar stack
commensurate with the template -- nucleation-and-growth of a new orientation,
not a continuous re-orientation of the existing lamellae.

That is consistent with the sharp dose threshold of M15: a barrier crossing
that either happens or does not, rather than a smooth elastic response. Two
independent observations, from different measurements, pointing the same way.

**A caution about what "before" means here.** The before and after frames are
minutes apart with a write between them, and the tune is re-run for each (M12).
The control window in the SAME pair is the guard: it shows the mottled structure
surviving unchanged across exactly the same interval and the same re-tune, so
the change in the written window is not a readout artefact.

**Figure:** `figures_260828b/figC_nano_switch.png`, built directly from the two
.ibw frames by `make_figures_260828b.py`.

### M16 — SELECTION IS REAL: at matched dose, a commensurate lattice and an aperiodic square drive the director to different triad members · **A**

- **The question.** M14 showed a DC square rewrites the in-plane director;
  M15 showed the rewrite is dose-limited with a threshold of 400-667 V.s/um^2.
  Neither could say whether the *commensurate* template does anything a
  featureless patch does not -- T3's selection term was still untested at a dose
  where anything happens (28 Aug, fig6e).
- **Operation.** `run_template.py EXP=control`, sample position 5, area
  (+8,0), Lambda 301 nm, triad **14/74/134**, modulation 0.213. Two panels of
  1.4 um in ONE 5 um frame, LDART before and after, four size-matched untouched
  controls:

  | panel | template | sites | sigma | V.s/site |
  |---|---|---|---|---|
  | P1 | **solid +/- pair**, 60 nm raster, no periodicity | 264 | 647 | 4.8 |
  | P2 | **parallel lattice**, lines along 14 deg, sign period Lambda | 128 | 679 | 10.4 |

- **End.**

  | window | w before | w after | dominant | excess vs controls |
  |---|---|---|---|---|
  | **P1 solid** | 0.410 / 0.348 / 0.242 | 0.243 / **0.584** / 0.173 | 75 -> **70 deg** | 0.181 = **4.3x** null |
  | **P2 lattice** | 0.243 / 0.429 / 0.328 | **0.872** / 0.062 / 0.066 | 90 -> **10 deg** | 0.640 = **15.3x** null |
  | ctrl1 | 0.467 / 0.261 / 0.273 | 0.460 / 0.288 / 0.252 | 115 -> 20 | - |
  | ctrl2 | 0.558 / 0.272 / 0.170 | 0.548 / 0.302 / 0.150 | 70 -> 70 | - |
  | ctrl3 | 0.496 / 0.265 / 0.239 | 0.456 / 0.362 / 0.182 | 0 -> 0 | - |
  | ctrl4 | 0.254 / 0.489 / 0.257 | 0.268 / 0.555 / 0.178 | 90 -> 90 | - |

  Control null **0.042**. Whole-frame modulation 0.214 -> 0.428.

**The result.** The two panels ended on **different triad members, 60 deg
apart**, in the same frame, at the same dose, with the same tip and the same
readout. The only difference between them is the template. **That is selection.**

**And the two templates do different things, not merely different amounts.**

* The **solid** panel *sharpened onto the member the film already favoured*:
  its dominant barely moved (75 -> 70 deg) while the population on that member
  rose 0.348 -> 0.584. Drive without a wavevector concentrates the existing
  director; it does not steer.
* The **lattice** *steered against the incumbent*: from a 90 deg dominant to
  10 deg, onto the member its own Q selects (lines along 14 deg), reaching
  **w = 0.872** -- near single-domain, and the largest population this campaign
  has produced.

So the rewriting rule has two separable parts, and this is the first experiment
that separates them:

    DRIVE      supplied by field magnitude; concentrates the local director.
               Polarity-independent (M13/M14), dose-thresholded (M15).
    SELECTION  supplied by a commensurate template; chooses WHICH member.
               Requires q = Q; a featureless patch cannot do it.

**It also re-confirms the dose threshold from an independent direction.** The
same parallel-lattice geometry produced nothing detectable at sigma ~400 in
three iterations on 27-28 Aug, and produces a 15.3x effect at sigma 679. Two
areas, two stage positions, two drivers.


**CONFIRMED by a second, independent test, and it closes the loophole above.**
M16's first experiment compared a lattice against an aperiodic square, so in
principle the lattice could have had one fixed preferred destination rather than
one chosen by **Q**. `EXP=select` at area (0,-8) put TWO parallel lattices at
DIFFERENT angles in the same frame at the same dose:

| panel | lines along | ended on | excess |
|---|---|---|---|
| P1 | 72 deg | **65 deg** | 0.121 = 3.7x null |
| P2 | 132 deg | **135 deg** | 0.191 = 5.9x null |

Frame triad after 16/76/136, control null 0.032. **Each panel ended on its own
template's member**, P2 landing within 1 deg of the 136 deg member it was built
to select. The destination tracks the template, so selection is by **Q** and not
by a fixed direction.

**Read P1 with care.** The incumbent director was estimated from a single
control window, which read 25 deg while the other three read 80/65/90. That put
P1's template (72 deg) on the member the film was already sitting on, so P1 had
little to do under either hypothesis and its 3.7x is largely a "stay put"
rather than a steer. **P2 is the informative arm**; P1 is not evidence against
anything. The driver now takes the incumbent from the mean population over all
four control windows.

**Effect sizes here are smaller than in the first experiment** (5.9x vs 15.3x,
w reaching 0.44 vs 0.87), because this area started more mixed and one panel was
aimed at the incumbent. The direction of the result is what carries, and it is
unambiguous in both.

**What the first experiment alone did not establish.** One lattice orientation was tested there, so the
lattice's destination could in principle be a fixed direction rather than one
chosen by Q. `EXP=select` -- two lattices at DIFFERENT angles in one frame --
is the test that closes that gap, and it followed immediately.

**Numbers to reuse.** Panel 1.4 um, Lambda 301 nm, sp 150 nm, V 10, per-site
charge 4.8-10.4 V.s, write 6.0 min for 9006 points. Control null 0.042 over
four 1.4 um windows.

### M15 — The in-plane rewrite is dose-limited, not geometry-limited: the threshold lies between 400 and 667 V.s/um^2 · **B**

- **Why it was asked.** M14 left dose and geometry confounded. The DC square that
  rewrote the director ran at ~667 V.s/um^2 and covered its area solidly; the
  point-pulse lattice that did nothing ran at ~400 and was a commensurate array
  of points. Two variables, one comparison.
- **Operation:** the SAME DC-square geometry as M14, at (16,+8), with the speed
  raised to 0.417 um/s so the areal dose is **400 V.s/um^2** -- matched to the
  lattice. LDART before and after, six matched 1.2 um windows, differenced
  against the four controls.
- **End:**

  | | sigma ~400 (this) | sigma ~667 (M14) |
  |---|---|---|
  | +10 V square excess | **0.075 — WITHIN NULL** (1.4x) | 0.662 (**12.7x**) |
  | -10 V square excess | 0.202 — clears (3.8x) | 0.293 (5.6x) |
  | dominant shift | 90->70, 70->90 deg | **90->25, 45->20 deg** |
  | largest w after | 0.563, 0.492 | **0.870, 0.659** |
  | control null | 0.053 | 0.052 |

  At the lattice's own dose the solid square -- the geometry that works
  decisively at 667 -- manages only a marginal effect: one of two squares fails
  the null outright, the other clears at 3.8x instead of 12.7x, and neither
  collapses onto a single member.

**Conclusion.** The failure of the point-pulse lattice is **dose-limited**. A
geometry known to work at 667 largely stops working at 400, so geometry cannot
be the main explanation for the lattice's three VOIDs. The threshold on this film
lies **between 400 and 667 V.s/um^2**, i.e. between about **1.3 and 2.2
sigma_c**.

**Consequences.**
1. `run_it14_mindose.py` tests 0.25 and 0.50 sigma_c. Those are far below the
   floor established here and it would return nulls by construction. **Invert the
   ladder**: 1.3, 1.8, 2.2 sigma_c. At the lattice's spacing 2.2 sigma_c is about
   17.6 V.s/site, inside C21's 20 V.s half-limit, so the range is reachable.
2. It does NOT show geometry is irrelevant -- only that it is not the leading
   term. A point lattice at 667 is still worth running, and is now the clean
   test of T3's commensurate-selection condition with a positive control
   available.

**Graded B, not A.** The after-frame triad rotated 12 deg between frames
(12/72/132 -> 24/84/144, tripping the >10 deg warning) and lateral \|A\| fell in
most regions, so this pair is noisier than M14's. The four controls did hold
their dominants exactly (90->90, 0->0, 90->90, 20->20), which is what makes the
differenced comparison usable, but a single dose point either side of a threshold
is a two-point curve and should be treated as one.

### M14 — A DC-poled square rewrites the in-plane director to one triad member, from either starting director and under either polarity; the point-pulse lattice at sigma ~400 does not · **A**

- **Operation:** the poled area of M13 imaged in LDART (`PZTO_LDART_0148.ibw`,
  5 um, 256 px, re-tuned). In-plane populations, dominant, lateral amplitude and
  spectral sharpness measured in six matched 1.2 um windows: the two squares,
  and four untouched controls of identical size sitting directly above and below
  each square.
- **End:** frame triad **16 / 76 / 136 deg**, whole-frame modulation 0.375 (the
  highest of the session).

  | region | w0 | w1 | w2 | dominant | lat \|A\| | peak/mean |
  |---|---|---|---|---|---|---|
  | +10 V square | **0.838** | 0.075 | 0.087 | **20 deg** | 44.4 pm | 7.24 |
  | -10 V square | **0.764** | 0.176 | 0.060 | **20 deg** | 50.7 pm | 7.52 |
  | control A-below | 0.127 | 0.630 | 0.243 | 90 deg | 63.5 pm | 7.78 |
  | control A-above | 0.216 | 0.564 | 0.220 | 90 deg | 63.5 pm | 3.74 |
  | control B-below | 0.245 | 0.397 | 0.358 | 45 deg | 57.9 pm | 3.65 |
  | control B-above | 0.296 | 0.561 | 0.143 | 80 deg | 61.0 pm | 3.73 |

  Control-to-control null 0.141; the squares deviate by **0.617 and 0.543**, i.e.
  ~4x the null. Inside both squares the director collapses to a near-single
  domain at **20 deg, which is the 16 deg triad member to within the estimator's
  resolution**, while the surrounding film is dominated by the 76 deg member.

**Three things make this more than a coincidence.** The effect appears in BOTH
squares; it lands on an ALLOWED triad member rather than an arbitrary angle; and
the poling raster ran along 0 deg, so a raster imprint would show at 0 or 90 deg,
not 16-20.

**It happens under BOTH polarities.** The -10 V square did not reverse out of
plane (M13: -1.8 deg) and still rewrote its in-plane director as strongly as the
+10 V square did. So **the in-plane response is not contingent on P_z reversal**;
the field does it either way. That is a genuine constraint on any mechanism.

**Against the lattice.** The point-pulse lattice at sigma ~400 V.s/um^2 produced
no in-plane change detectable above the tile-to-tile null in three iterations.
The DC square at ~667 V.s/um^2 produced w0 = 0.84 against a control of 0.13-0.30.
Both dose and GEOMETRY differ -- solid coverage versus a commensurate point
lattice -- and this experiment cannot separate them. That separation is the
obvious next experiment.


**CONFIRMED before/after at a second area, 28 Aug 07:20 (this is what lifts the
grade from C to A).** `diag_poling2.py` repeated the two squares at (16,-8) with
LDART frames taken BEFORE and AFTER, so the comparison is no longer
inside-vs-outside on one frame. Each square's change is differenced against the
mean change of the four controls, which cancels drift and any frame-to-frame
tune difference (C42):

| region | w before | w after | dominant | excess vs controls |
|---|---|---|---|---|
| **+10 V square** | 0.225 / 0.480 / 0.295 | **0.870** / 0.045 / 0.085 | **90 -> 25 deg** | **0.662** |
| **-10 V square** | 0.430 / 0.339 / 0.231 | **0.659** / 0.060 / 0.281 | **45 -> 20 deg** | **0.293** |
| ctrl A-lo | 0.481 / 0.200 / 0.319 | 0.491 / 0.175 / 0.334 | 45 -> 45 deg | - |
| ctrl A-hi | 0.261 / 0.458 / 0.281 | 0.268 / 0.472 / 0.260 | 70 -> 70 deg | - |
| ctrl B-lo | 0.298 / 0.497 / 0.205 | 0.243 / 0.500 / 0.258 | 90 -> 90 deg | - |
| ctrl B-hi | 0.483 / 0.207 / 0.310 | 0.452 / 0.273 / 0.275 | 65 -> 65 deg | - |

Control-to-control null **0.052**; the squares clear it by **12.7x and 5.6x**.
**All four controls kept their dominant unchanged** (45->45, 70->70, 90->90,
65->65) while both squares rotated onto the after-frame's 14 deg triad member.

**The two squares started from DIFFERENT dominants -- 90 and 45 deg -- and ended
on the SAME member.** For DC poling, the final director is set by the field and
not by where the film started. That is the sink/attractor behaviour the pathway
experiments were built to look for, obtained here from a geometry the pathway
experiments do not use.

**And again under both polarities**, with the -10 V square (no out-of-plane
reversal, M13) rewriting its in-plane director as decisively as the +10 V one.

**The amplitude caveat, resolved and narrowed.** In this run lateral \|A\| rose
in EVERY region (the after-frame is better tuned: modulation 0.124 -> 0.306), so
the earlier "\|A\| drops inside the squares" was partly a tune difference. What
survives is relative: \|A\| rose by 23 and 29 pm inside the squares against 48,
32, 51 and 32 pm in the controls, so the written regions do gain less lateral
response than their surroundings. The director result does not depend on it --
the controls' dominants are rock-steady across the same two frames -- but a
written square is not simply re-oriented pristine film.

**What is still open.** Dose and geometry are still confounded: the DC square is
both stronger (~667 vs ~400 V.s/um^2) and solid rather than a commensurate point
lattice. Separating them -- a point lattice at ~667, or a DC square at ~400 -- is
the next experiment, and it is now a well-posed one with a positive control.

**Original grade-C reading, kept for the record. The reasons it was C:**
1. ~~No LDART before-image of this area.~~ **Resolved** by the before/after run
   above.
2. **A 1.2 um window is ~4.3 periods at Lambda 280 nm** -- the bare minimum the
   FFT estimate tolerates. On unwritten film four such windows scattered over
   w0 = 0.13-0.30 with dominants 45/80/90/90. The effect here is far larger than
   that scatter, but the estimator is weak and the null has only four points.
3. **Lateral amplitude DROPS inside the squares** -- 44.4 and 50.7 pm against
   61.5 +- 2.3 for the controls, i.e. -7.5 and -4.7 sd. A region that both
   changes director and loses lateral response may have been physically or
   electrostatically modified, not merely re-oriented. This is the caveat most
   likely to overturn the reading and it should be checked before the result is
   promoted.

### M12 — The re-tune was applied to the baselines and not to the readout, and a VOID was reported from a collapsed frame · **A**

- **Operation:** IT12, 28 Aug, two panels at sigma 389 = 1.29 sigma_c on a
  Lambda 280-301 nm area with modulation 0.287. Pre-write baselines were taken
  through `tune_here` (the M8 fix). Post-write frames and zooms were taken with
  bare `frame()`.
- **End:** `probe_health.py` over the whole iteration, in time order:

  | frame | phase | r12 | median \|A\| |
  |---|---|---|---|
  | 0113-0115 | baselines, RE-TUNED | 0.93 / 0.93 / 0.93 | 66 / 72 / 75 pm |
  | 0120 | after-frame 1 | **0.93** | **64 pm** |
  | 0121 | after-frame 2 | 0.70 | 30 pm |
  | 0122-0125 | the four zooms | 0.31 / 0.28 / 0.45 / **0.16** | 25-28 pm |
  | 0126 | angle control | **0.40** | **25 pm** |

  The readout collapsed immediately after the first after-frame, and **the
  verdict fitted its rigid triad on 0126** -- r12 0.40, \|A\| 25 pm.

**The verdict it produced.** Both panels VOID: excess -0.005 and +0.001 against
2sd thresholds of 0.037 and 0.051, dominant unchanged at 136 deg, populations
moving by <= 0.013. Read as physics that says "1.29 sigma_c does not rewrite this
film". Read correctly it says "the after-state was measured with a third of the
signal the before-state had", and a contrast that needs 0.04 to register was
being asked for from a frame that could not deliver it.

**Why this was structural, not bad luck.** M8 established that the contact
resonance drifts over 5-10 minutes. **The write takes 11-22 minutes.** So the
readout ALWAYS begins outside the tune the baselines were taken under -- the
collapse is the normal case, not an occasional hazard. The fix went to the
baselines because that is where the symptom was first seen (the floor gate reads
them), and the readout was left on bare `frame()` for the same reason nobody
checks the half that is not currently failing.

**The asymmetry that makes it worse.** A collapsed BASELINE is caught: it raises
the floor and the gate halts the run, loudly, before the write. A collapsed
READOUT is not caught by anything -- it produces small excesses, which look
exactly like a null. **The failure mode of a bad baseline is a halt; the failure
mode of a bad readout is a wrong answer.** The unprotected half was the dangerous
half.

**Fixed** by routing every post-write acquisition through `tune_here`: both
after-frames, the angle control (which carries the triad fit that sets the ENDING
dominant), and all four zooms. VDART is left alone -- it switches mode and tunes
separately, and read \|A\| 46 pm at coherence 0.95 at the end of the same
iteration in which LDART had collapsed, which is itself evidence the drift is
specific to the lateral contact resonance.

**Standing consequence.** IT12's VOID is **withdrawn as evidence about dose**. It
is not a null result; it is an unreadable one, and C47's table (376, 400, 444 all
turned over Lambda 234-325 nm, which brackets 280-301) gives no reason to expect
1.29 sigma_c to fail here. Any dose conclusion has to come from an iteration
whose after-frames are as healthy as its baselines.

### M11 — FAM_FILM is stale at sample position 4: the lab triad is 19/79/139, not 2/62/122 · **A**

- **Operation:** IT12's screen on 28 Aug visited 13 candidates on an 8 um grid
  over roughly +-16 um, tuning and framing each separately and fitting a triad to
  each. Thirteen independent orientation measurements, free, as a by-product of
  looking for somewhere to write.
- **End:** the fitted offset from the pinned family `FAM_FILM = (2, 62, 122)` was

      phi0 = 14.0, 11.5, 19.0, 19.0, 14.0, 16.5, 19.0, 16.5, 16.5, 19.0, 19.0,
             24.0, 21.5 deg        mean 17.7, spread 11.5-24.0

  Every candidate is offset in the SAME direction. This is not scatter about the
  pinned family; it is a different family. The lab triad here is
  **19/79/139**, which is what M10 recorded at this position from a single area.

**Why it does not invalidate anything.** `FAM_FILM` enters only as `ref_fam`,
the reference the fitted triad is ASSIGNED to, and the driver rotates it by the
scan angle before use. Triad members sit 60 deg apart mod 180, so assignment is
unambiguous while the offset stays under 30 deg. At 17.7 deg there is 12 deg of
margin, and the largest single offset seen, 24 deg, leaves 6 deg. Scores are
computed on each frame's OWN re-fitted triad (C36), so the population vector is
read in the right basis regardless.

**Why it still matters.** Two reasons, one practical and one about instruments.

1. **The margin is smaller than it looks.** 24 deg observed against a 30 deg
   aliasing threshold is 6 deg of headroom on a quantity whose per-visit spread
   is already 12.5 deg wide. If a candidate ever fits past 30, `pin_triad` will
   assign each member to its NEIGHBOUR, silently, and every subsequent angle in
   that iteration will be wrong by 60 deg with nothing in the output looking
   wrong. That is the same failure mode M10 caught with one degree to spare.
2. **A warning that fires 13 times out of 13 is not a warning.** The driver
   prints "more than 10 deg from the established film triad -- that would mean a
   different grain or a rotated sample, verify before trusting it" on every
   single candidate. It is correct every time, and precisely because it is
   correct every time it has become log furniture. An alarm that never
   distinguishes anything trains the reader to scroll past the one occasion it
   does.

**What to do.** Re-pin the family per stage position rather than holding one
constant for the sample: fit the triad once on arrival, round to the nearest
degree, and use THAT as `ref_fam` for the position, with the deviation from it
as the thing that gets flagged. Then the warning means "this area disagrees with
the rest of this position", which is a real event, instead of "the stage moved",
which is already known. Same defence as PITFALLS 19.11: derive the reference
from the data it will be applied to, not from a constant that was true once.

### M10 — Rotating the scan by +phi moves measured angles by +phi, and the sign was assumed wrong · **A**

- **Operation:** the 27 Aug overnight driver rotates the scan per area so both
  commands sit at an ANGF minimum. It built its reference triad family as
  `(FAM_FILM - phi)`, on the assumption that turning the scan by +phi makes
  features appear at lower angle.
- **End:** at phi = 34 deg on an area whose lab triad is 19/79/139, the fit
  returned **54 / 114 / 174**. That is `lab + 34` to within 1 deg
  (53/113/173), not `lab - 34` (145/45/105). `align_triad` refused the
  mismatched reference outright -- *"no member of ['54','114','174'] within
  25 deg of 148"* -- every member being exactly 26 deg out, one degree past its
  tolerance.
- **Reading.** **Measured angle = lab angle + scan rotation.** The guard is what
  made this cheap: align_triad's 25 deg tolerance turned a silent 26 deg
  systematic into a hard stop before any write. Had the tolerance been 30 deg,
  the run would have proceeded with every command 68 deg from where it was
  meant to be -- two triad members away -- and the panels would have been
  written at angles nobody chose, with a verdict that read them against the
  wrong members.
- **What it cost, and what it did not.** One halted run and a set of baselines
  taken at the wrong angle. It cost no sample: the failure is upstream of the
  write. It also invalidated those baselines rather than the area -- at
  phi = 34 the two commands land at ANGF 1.115 and 1.401, i.e. nearly the worst
  case, which is why placement could not fit them. The correct angle for a
  dominant-79 area is **56 deg**, putting both commands at 1.225.
- **The general trap.** This is M3 again in a different coordinate: a sign or
  index convention assumed rather than measured. M3 was the array being [x][y]
  and not [y][x]; this is the scan rotation adding rather than subtracting.
  Both were settled in minutes by one comparison against a known quantity, and
  both would have been invisible in the result. **Before trusting any new
  coordinate transform, image something whose angle you already know and check
  the sign.**
- **Falsified by:** a frame at known phi whose fitted triad matches
  `lab - phi`.

### M36. A matched filter reads the director to 0.2 deg, twenty times finer than the band estimator — VALIDATED

The blind band estimator bins the low-q annulus into ~48 angular bins, so it
quantises every reported director to 7.5 deg; five of six raster runs
therefore return exactly 18.8 deg. That is ample for the claims in the
manuscript, where the moves are 37-75 deg, but useless for anything at the
degree level.

A matched filter at the *measured* period does not have that limit. Scanning
the filter direction in 0.25 deg steps and interpolating the peak parabolically
(`fine_angle.peak_angle`) gives:

* **accuracy** (`fine_angle_validate.py`, 72 synthetic fields spanning a full
  60 deg of direction x periods 210/253/295 nm x snr 0.5/1/2, at the real
  window size of 1.2 um and 4.88 nm/px):
  **bias -0.005 deg, rms 0.089 deg, worst case 0.32 deg**, with no dependence
  on direction relative to the pixel grid.
* **repeatability on real data**: every written panel was imaged twice, at the
  write and again 1.3-4.8 h later in the retention run, with an independent tune
  and tip approach between. Peak directions agree to a **median of 0.34 deg,
  worst 0.47 deg**.

Precision and accuracy were measured separately and on purpose: a bias from
the square window, the Hermitian half-plane or the interpolation would repeat
perfectly across two images and still be wrong.

**Use it whenever the question is about degrees rather than tens of degrees.**
The blind estimator stays the tool for *finding* a direction and testing
whether one exists at all; the matched filter is the tool for *measuring* one
already known to be there.

### M37. The written directions share a triad across the film to a few degrees — and a re-aimed region keeps a measurable residue of what it replaced

Measured with the validated sub-degree matched filter (M36) on all six raster
panels of the current probe, each from two independent images.

**(a) One triad, common to the film, to about +/- 3 deg.**
Landing directions reduced modulo 60 deg:

    16.39, 19.63, 20.88, 20.01, 17.90, 15.07   -> circular range 5.81 deg about 18.32

Six independently screened areas, spread over 36 um, written at four different
commanded angles onto three different members. P(6 uniform draws all inside a
5.81 deg arc) = **5e-5**. The commanded angles modulo 60 span 46 deg and are
NOT clustered, so the landings did not inherit this from what was asked for.

This is the first direct evidence in the campaign that the triad is a property
of the film rather than a per-area fit: nothing in the matched filter knows
about a triad, and the 60 deg reduction is applied after the fact.

**(b) The as-grown fit, not the landing, carries the scatter.**
The same six areas' pre-write rigid-triad fits give phi0 modulo 60 of
16.5, 24.0, 19.0, 16.5, 16.5, 24.0 -- a spread of **7.5 deg**, larger than the
5.81 deg range of the written landings and 20x the 0.34 deg repeatability of
the measurement. The as-grown state has anisotropy 2-4 and frequently no
significant direction, so its triad fit is the noisy quantity.

**Consequence: the 0.2-5.2 deg "offsets from the nearest allowed orientation"
quoted from the binned estimator cannot be interpreted as a displacement of the
minimum.** They are dominated by the error of the reference they are measured
against. The landscape model's prediction that the selected minimum is pulled
toward the commanded axis by B sin(2 Delta)/(36 A) is therefore NOT tested by
those numbers -- on the matched filter only 4 of 6 lean the predicted way
(sign test p = 0.69).

**(c) A re-aimed region lands 2.83 deg short, toward the state it replaced.**
The rewrite pair is the one case where the reference cancels, because both
writes are on the same area in the same tune session:

    step 1 (raster 0 deg)   -> 17.98 deg
    step 2 (raster 60 deg)  -> 75.15 deg
    separation 57.17 deg against 60.00 -> **-2.83 deg**, 8x the repeatability

The shortfall is **toward** the orientation being replaced, and step 2's
anisotropy fell to 5.70 from 13.47. Both are what an incomplete re-aim would
give: a majority of the new variant with a surviving minority of the old one
pulls the measured director back and lowers the order.

The alternative -- that the film's triad is intrinsically not 60 deg symmetric
-- is not excluded by one pair. **The discriminator is a second rewrite pair:
if the shortfall again points toward the replaced orientation it is a residue;
if it is fixed in the crystal frame it is a distorted triad.** Round 3 writes
that pair.

### M38. Anisotropy is session-dependent and must not be compared across imaging sessions

The retention run re-imaged six raster panels 1.3-4.8 h after their writes.
Directions were reproduced to 0.0-0.1 deg (0.34 deg on the matched filter).
**Anisotropies were not**: the retained fraction is 80-300 %, median 138 %.

The obvious reading -- the written state consolidates over hours -- makes a
prediction, and the prediction fails. Gain against age gives
**Spearman -0.09 (n = 6)**; the largest gain, 3.0x, is on the *youngest* panel
(1.3 h) and the only loss is on a panel of middling age (2.5 h).

What differs is not the film but the measurement. The post-write frame is taken
immediately after the tip has delivered +/-10 V over the area; the retention
frame after withdrawal, retune and re-approach. The same panel reads 16.86 or
50.53 depending on which.

**Rules.**
1. Never compare an anisotropy across imaging sessions, and never quote a
   ratio of two as a physical result.
2. Anisotropy is a *detection* statistic -- "significantly above the null" --
   not a calibrated degree of order.
3. Direction and p-value are the quantities that reproduce. Build claims on
   those.

This retires the "the order grows after writing" reading that the raw retention
table invites, and it is the reason section 3.9 quotes drift rather than
retained fraction as the retention result.

### M39. The per-area triad fit does not predict where the film lands

M37 argued for one film-wide triad from a range comparison: written landings
span 5.81 deg modulo 60, the as-grown fits 7.50 deg. With six points that is
weak, and the landings could have inherited the fits' clustering.

The sharper test is whether the fit *predicts* the landing. Under "each area
has its own triad" the fit is an estimate of it and the landing must track it;
under "one triad plus fit noise" the fit says nothing.

    correlation fit vs landing      r = -0.193   (permutation p = 0.73)
    slope (should be 1.0)              -0.119
    3 areas fitted to exactly 16.5  land 16.39, 17.90, 20.01  spread 3.62
    2 areas fitted to exactly 24.0  land 19.63, 15.07         spread 4.56
    r.m.s. about a single common value        2.26 deg
    r.m.s. about the per-area fits            4.41 deg

**A single common orientation describes the landings twice as well as the
per-area fits do.** Areas given identical fits land up to 4.6 deg apart, and
areas given fits 7.5 deg apart land within 5.8 deg of each other with no
ordering between them.

This does not make the triad an instrumental artefact: the six writes go to
three DIFFERENT members (near 18, 75 and 141 deg absolute), each the member
nearest the commanded axis. A fixed instrumental preference would pull every
write to one absolute angle, not to three chosen by the command.

**Consequence for practice.** Stop treating the pre-write rigid-triad fit as a
per-area measurement. It is a starting guess with a few degrees of error, good
enough to predict WHICH member a write will select (the members are 60 deg
apart) and not good enough for anything at the degree level.

### M40. The charge-balanced raster does NOT pole, but it triples the vertical piezoresponse of the written square

Every raster write recorded a VDART frame before and after, and none had been
analysed. Comparing the written interior against the unwritten surround of the
SAME frame (which cancels the session offsets of M38), across seven writes:

    thresholded up-fraction change, interior minus surround
        median +0.001, range -0.022 to +0.045, |max| 0.045
    interior/surround vertical response ratio
        before  0.98, 1.01, 1.03, 1.05, 1.07, 1.12   median 1.05
        after   2.94, 3.47, 3.06, 3.21, 3.24, 3.51   median 3.21

**No poling.** A real poling event on this film flips essentially the whole
square (up-fraction change of order 1, VDART phase -180 deg). What is measured
is 0.045 at worst. The charge balance does what it is for.

**But a threefold rise in vertical response**, confined to the written square,
absent before the write, same sign as before. Before the write the interior is
indistinguishable from the surround (0.98-1.12).

**A trap avoided.** The RAW up-fraction looks like a large effect: the interior
goes to 1.000 after every write, from 0.84-0.96. That is entirely the
signal-to-noise change -- in a weak region, noise flips the sign of individual
pixels; in a strong one it does not. Counting only pixels above the surround's
median |response| removes it and leaves +0.001. **Any sign-fraction statistic
must be thresholded before it means anything.**

**Why this matters beyond the mechanism.** The vertical channel is a different
contact resonance and a different mechanical mode from the lateral one. A
torsion artefact in LDART cannot triple the VDART amplitude. A change that
appears in BOTH channels, in a region defined by the trajectory rather than by
the scan frame, is a change in the film -- which is the strongest answer we
have to the standing worry that lateral PFM artefacts mimic the measured
quantity.

**The AC control, which corrects the first reading of the amplitude rise.**
Three AC writes -- same |V|, same delivered dose, same geometry, sign
alternating along the path, and NONE of them steers the director -- give:

    interior/surround vertical response, before -> after
        DC rasters (n=7)     1.05 -> 3.21
        AC writes  (n=3)     0.94 -> 2.43   (1.26, 2.54, 2.43)

So **the amplitude rise is largely generic**: a biased tip crossing the area
raises the vertical response whether or not the director reorients. It is NOT
a signature of the reorientation, and the first draft of this entry said it
was. What does track the outcome is the size of the rise -- 3.21 for the DC
writes that steer, 2.4-2.5 for the AC writes that leave the film alone, and
1.26 for the 120 nm AC write that actively DISORDERS it (M32) -- but that is
one panel per condition and is not a result.

**A claim the null retired -- read this part before quoting the one above.**
The thresholded interior-minus-surround change is <= 0.045 in all seven DC
rasters, but the 1600 nm AC write gives **-0.137**, three times larger. The
reading almost writes itself: an AC write is charge-balanced overall, but its
polarities are separated in SPACE -- at a 1600 nm sign period the tip holds one
sign over 800 nm of continuous travel, long enough to pole locally, then
reverses -- while the DC raster is neutral in TIME, a whole +V pass then a
whole -V pass. The AC write would be laying down a spatial pattern in P_z,
exactly what section 3.1 designs the raster to avoid. This was written into
the manuscript as "the first direct evidence" for that assumption.

**Then the null was run and it is not evidence for anything.** Splitting the
UNWRITTEN surround in half and applying the identical statistic to one half
against the other, over the same ten pairs:

    thresholded sign-fraction change   median -0.004, |max| 0.127
    response-ratio change              median  0.93,  range 0.81-1.08

The written squares' largest sign change is 0.137 against a null maximum of
**0.127**. The statistic has no resolving power at this sample size, and the
AC-poling claim is withdrawn. What survives is an upper limit set by the null.

The response ratio is the opposite case: the null spans 0.81-1.08 and the
written squares sit at 2.94, so that effect is real and well outside anything
unwritten film does.

**Two statistics, one script, one set of frames, and only one of them means
anything.** The difference was invisible until the null was run -- and the null
cost nothing, since the unwritten surround is in every frame already.

The natural reading of the amplitude rise remains that the write removes weakly
responding material: before, 4-16 % of interior pixels carry a response too
weak to have a definite sign; afterwards essentially none do.

**The one decrease in the set** is step 2 of the re-aim, whose interior had
already been written (3.47 -> 2.65). Same direction as the loss of order in
M37(c).

### M41. The raster/lattice contrast is NOT a dose effect, and the single-triad result survives eleven writes

Round 3, five writes, all commanded at 41 deg (forbidden), scored against the
film-wide triad of M37 rather than the per-area as-grown fits M39 discredits.

**(a) Dose. The rule holds down to lattice-like dose.**

    pitch  speed   sigma   before (p)   landing   from member   from command
     30 nm  0.5     686    78.8 (0.08)   20.01       1.7            21.0
     30 nm  0.5     686    63.8 (0.65)   17.90       0.4            23.1
     60 nm  0.5     343    63.8 (0.31)   15.17       3.2            25.8
    120 nm  0.5     178    78.8 (0.88)   19.30       1.0            21.7
     60 nm  1.0     172    26.2 (0.51)   17.17       1.2            23.8

At sigma 178 -- within 50 % of the point-pulse lattice's own dose, and 3.9x
below the reference raster -- the raster still lands 1.0 deg from an allowed
orientation and 21.7 deg from the direction commanded, moving 60.0 deg from a
state with no significant direction. **The second referee report's decisive
objection is answered: the headline contrast is a property of the tool.**

No threshold appears across a factor of four in dose, and the distance from the
predicted member (0.4-3.2 deg) shows no trend with dose.

**(b) Speed. No effect at 2x, at matched dose.** The last two rows differ by
4 % in dose and 2x in speed and land 1.0 and 1.2 deg from the same member. This
is one of the three falsifying tests M-hypothesis 5.3 proposed for the
accumulated-charge picture, which predicts slower should steer better at
matched dose. It does not. Either the time constant is below the ~1 s per line
at these speeds, or the picture is wrong.

**(c) The single triad, now with eleven writes.**

    11 landings mod 60: 15.07 15.17 16.39 17.17 17.90 19.11 19.30 19.63
                        20.01 20.87 20.88
    circular range 5.81 deg about 18.32 -- IDENTICAL to the six-landing value
    P(11 uniform draws inside a 5.81 deg arc) = 8.0e-10
    fit-vs-landing correlation  +0.186 (p 0.59); it CHANGED SIGN from -0.19
    r.m.s. about a common value 2.02 deg; about the per-area fits 4.22 deg
    11 of 11 went to the member nearest the command, p = 5.7e-6
    10 of 10 with the one ambiguous case (margin 4.6 deg) removed, p = 1.7e-5

Adding five writes did not widen the arc at all.

**(d) A "failure" that was the reference, not the film.** The driver scored the
speed run at (-6,-12) as "did NOT go to the member nearest the raster", because
it compares against that area's as-grown fit (9/69/129), which puts the nearest
member at 69 deg; the film went to 17 deg. Against the film-wide triad it is a
clean hit with a 14.6 deg margin. **Live scoring against the per-area fit is
now known to be unreliable and should be treated as advisory only.**

**(e) The re-aim residue is withdrawn.** The second re-aim pair separates by
61.76 deg where the first separates by 57.17 -- **opposite sides of 60**. The
shortfall in pair 1 is not systematic and the "residue of the replaced
orientation" reading of M37(c) is retired. Successive written members are
60 deg apart to within 2-3 deg, the same scatter as between areas.

What survives from both pairs is the loss of order on re-aiming: 13.47 -> 5.70
and 5.89 -> 4.30.

### M42. Speed replicate on a matched triad: the rule is indifferent to a 2x speed change

The round 3 speed test at (-6,-12) was ambiguous by construction: run_round3
hard-coded a 41 deg command for every area without checking each area's own
triad, and on a 9/69/129 triad 41 deg sits 28 deg from one member and 32 from
another. "Nearest" was decided by 4 deg, less than the reference is worth.

Repeated at (+12,+6), which carries the **same triad (16/76/136) and the same
Lambda class as the sigma 178 write**, so the comparison is exact:

    sigma 172, 60 nm pitch, 1.0 um/s, commanded 41 deg
    before 131.2 deg, aniso 1.62, p 0.607   (no direction)
    after   18.8 deg, aniso 13.46, p 0.005
    moved 67.5 deg; 2.2 deg from member 16, 22.2 deg from the command

Against the film-wide triad the two fast writes land at **17.17 and 17.14 deg**
-- 0.03 deg apart, on different areas. At this sample size that is a
coincidence, but it is a striking one against a 0.34 deg repeatability.

**Conclusion.** At matched dose (178 vs 172, 4 % apart) and a factor of two in
speed, the selection rule is unchanged: all three land within 1.1 deg of the
same member. The accumulated-charge picture predicted the slower pass should
steer better and it does not.

**With this write the triad set is 12 landings on 11 areas.** The circular
range modulo 60 is **still 5.81 deg** -- unchanged from six landings through
eleven to twelve -- about a common 18.22 deg, p = 8.5e-11. Twelve of twelve go
to the member nearest the command (p = 1.9e-6); eleven of eleven with the one
ambiguous case removed.

**Design lesson.** A commanded angle must be chosen against the area's own
geometry, or against a reference known to be good, not fixed globally across
areas. A fixed 41 deg is a clean test on a 16/76/136 triad and an ambiguous one
on 9/69/129, and the driver cannot tell the difference.

### M43. The selection rule composes: adjacent regions hold different variants

Two 1.6 um squares written 12 minutes apart in neighbouring scan fields at
(-6.8,-18) and (-5.2,-18), commanded at 0 and 60 deg, sigma 342 each. Each read
inside its OWN written square (rotate the frame by minus the commanded angle,
take the largest axis-aligned window that fits, 1.50 um):

    tile A, commanded  0 deg -> 18.8 deg lab, Lambda 290, 5.18 periods,
                                aniso 15.19, p 0.0025  -> member 18.22  HIT
    tile B, commanded 60 deg -> 78.8 deg lab, Lambda 323, 4.64 periods,
                                aniso 27.44, p 0.0025  -> member 78.22  HIT
    separation 60.0 deg, commanded 60.0 deg

Both land on the member nearest their own command, on the same film-wide triad,
and the two variants sit side by side.

**The second write does not disturb the first -- withdrawn once, then
re-established on a verified frame.** The first version of this claim rested on
a "boundary frame" that had been taken by another process at (+12,+18), not at
the join (PITFALLS 21.29), and was withdrawn. The join was then re-imaged with
a driver that checks each frame against its own header offsets:

    tile A in its own frame, BEFORE tile B was written
        18.8 deg, Lambda 275 nm, 4.33 periods, aniso 19.40, p 0.0025
    tile A in the join frame, AFTER tile B was written  (PZTO_LDART_0118,
        header verified at (-6.00,-18.00))
        18.8 deg, Lambda 276 nm, 4.35 periods, aniso 23.89, p 0.0025

Director change **0.0 deg**, and the region is slightly better ordered
afterwards. Writing a neighbouring tile at a different commanded axis 1.6 um
away leaves it alone.

**What is NOT measured is the boundary itself.** Its width and character are
still unknown, for the geometric reason in PITFALLS 21.27.

This is the composition step that section 6.2 needs and section 8 listed as the
main gap between the rule and large-area patterning.

### M44. Consolidated triad numbers, every raster write, two images each where available

Final values after folding in the second images from the round 3 retention pass
(every frame verified against its own header offsets, PITFALLS 21.29):

    12 landings on 11 areas, modulo 60 deg:
      14.97 15.07 16.39 17.20 17.29 17.90 19.05 19.23 19.63 20.01 20.87 20.88
    circular range  5.91 deg about a common 18.21 deg
    P(12 uniform draws inside a 5.91 deg arc) = 1.0e-10
    fit-vs-landing correlation  +0.198 (permutation p = 0.541)
    r.m.s. about a common value 1.98 deg; about the per-area fits 4.05 deg
    12 of 12 to the member nearest the command, p = 1.9e-6
    11 of 11 with the one ambiguous case (margin 4.4 deg) removed, p = 5.7e-6
    re-aim pairs: 57.17 and 61.82 deg against 60.00 (-2.83, +1.82)

The arc widened from 5.81 to 5.91 deg when the sample doubled from six to
twelve -- a tenth of a degree. Six landings now rest on two independent images
each, and the difference between the one-image and two-image values is at most
0.2 deg.

**The estimator's binned resolution is 7.5 deg, not 3.75.** The band in a
1.2 um window holds only 88 FFT pixels, so `nang = clip(npix/12, 24, 180)` sits
on its floor of 24 and the bins are 7.5 deg wide with centres at 3.75, 11.25,
18.75 ... The 3.75 figure quoted in an earlier draft was the first bin CENTRE.
Nothing in the campaign depends on a difference below 7.5 deg -- the moves are
37-77 deg and the discriminations 21-27 deg -- but every quoted "resolution"
has been corrected.

### M45. Re-aiming always works directionally and always costs order; two of three end below significance

Three re-aim pairs, three areas. Each pair: an aligning write, a full readout,
then a second write commanded 60 or 120 deg away, with the second write's
before-frames being the first write's after-frames.

    pair  area        sigma  step2 before -> after   aniso           p after  move
      1   (-6,0)       686   18.8 -> 78.8 deg        13.47 -> 5.70   0.005    60.0
      2   (-12,-6)     685   18.8 -> 138.8 deg        5.89 -> 4.30   0.015    60.0
      3   (+6,-12)     178   18.8 -> 138.8 deg       13.67 -> 3.64   0.035    60.0

**The direction always goes where it is sent**: every second write moves the
director exactly 60.0 deg onto the member predicted from its commanded axis,
and in pairs 1 and 3 the starting state is the well-ordered stack the first
write had just made (13.47 and 13.67, both p 0.005).

**It always costs order**, in all three pairs, and in two of three the result
falls below the p < 0.01 bar. That is a limitation on the application: a medium
that degrades on each rewrite has a finite number of rewrites and we do not
know the number.

**The largest loss is at the lowest dose.** Pair 3 ran at sigma 178 and lost
the most (13.67 -> 3.64, p 0.035); pairs 1 and 2 ran at ~686. This is the one
place in the campaign where dose appears to matter, since M41 finds FIRST
writes indifferent to dose over the same range. Three pairs cannot establish
it and it is the obvious next measurement.

**The residue claim of M37(c) is now firmly dead.** Separations between the two
written members on the same area: 57.17, 61.82, 59.32 deg against 60.00 --
mean deviation -0.56 deg, scatter 2.3 deg, no consistent sign. Successive
written members are 60 deg apart to within about 2 deg, the same scatter as
between independent areas (M44).

### M46. Retention across every raster in the campaign: 14 panels, and the one "drift" is a bin boundary

All fourteen raster panels have now been re-imaged 0.4-4.8 h after their writes
-- the original six, the five of the dose and speed series, both tiles, and the
third re-aim.

    director drift <= 0.1 deg on the binned estimator   13 of 14
    still significant at p < 0.01                       13 of 14
    matched-filter agreement between sessions           0.34 deg median,
                                                        0.47 deg worst

**The single exception to the drift is instructive and is not a drift.** The
sigma 343 panel at (+12,+18) reads 26.2 deg at the write and 18.8 deg four
hours later -- adjacent bins, an apparent 7.5 deg move. The matched filter on
the same two frames reads **15.17 and 14.77 deg**: the true change is
**0.40 deg**. The underlying direction sits near a bin boundary and fell on
either side of it twice.

This is the clearest single demonstration of why the campaign now carries two
estimators. A 7.5 deg "retention failure" and a 0.4 deg "unchanged" are the
same data.

**The exception to significance is the third re-aim**, which was already below
p < 0.01 when written (3.64, p 0.035) and is unchanged 25 minutes later (3.56,
p 0.040). It was born weak; it is not decaying.

**A flaw in the retention script.** Its verdict rule requires 80 % of panels to
be significant, so a batch of three containing one weak panel prints "the
written direction does NOT hold" even when every director is within 0.1 deg.
Direction retention and significance are different questions and the script
should report them separately.
