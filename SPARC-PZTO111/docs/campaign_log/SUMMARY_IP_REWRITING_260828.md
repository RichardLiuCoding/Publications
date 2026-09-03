# Rewriting the in-plane super-domain director in PZTO(111)

**Session of 27–28 August 2026 · figures and evidence**

Every number and every image below is recomputed from the `.ibw` frames on disk
by [`make_figures_260828.py`](make_figures_260828.py); nothing is transcribed
from a log. Re-running that script regenerates all six figures and prints the
statistics used in the text, so this document and the data cannot drift apart.

---

## 1. The question and the two geometries

The mission is the **rewriting rules of the in-plane (IP) super-domain
director**. The film supports three degenerate IP directors — a *triad*, members
60° apart, each defined mod 180° — and the question is what makes the film
choose one.

Two write geometries were compared.

The **point-pulse lattice** is the campaign's designed tool, and its structure is
the point of it. In `lattice_panel()` the sign of a site is set by its row index
alone — `(bi // sign_every) % 2` — while the in-row index steps along the
commanded director **u** and the row index steps along **n**ₚₑᵣₚ, perpendicular to
it. So:

* **one polarity runs the full length of each line**, along the commanded
  director;
* **lines alternate** in sign across the command, every `sp` = Λ/2;
* the **sign period is therefore Λ, measured perpendicular to the director** —
  commensurate with the lamellae by construction.

That periodicity gives the template a wavevector of magnitude 2π/Λ directed
along **n**ₚₑᵣₚ, which is precisely T3's **Q** = (2π/Λ)·n̂⊥ (§5). It is the one
property a uniform patch cannot have.

The **solid DC square** is the crude alternative: a 60 nm raster at a single
polarity, with no periodicity at all and therefore no wavevector to match.

![Schematic of the triad, the two write geometries, and the measurement layout](figures_260828/fig1_schematic.png)

**Figure 1.** (a) The three allowed IP directors at this area, 14/74/134°.
(b) The two geometries and their areal doses σ (V·s/µm²). Note the lattice is
**lines of one sign** running along the commanded director, alternating every
Λ/2 across it — not a checkerboard; the Λ sign period perpendicular to the
director is the commensurate feature. (c) The measurement
layout inside a 5 µm frame: two 1.2 µm written squares and **four untouched
control windows of identical 1.2 µm size, placed at the same x** as the squares
they control, so area and scan position are matched.

---

## 2. First: does the tip write at all?

Three lattice iterations returned VOID, and "no bias is reaching the sample"
became the leading explanation. It had to be settled before anything else.

![VDART phase and amplitude before and after DC poling, showing a 180 degree reversal](figures_260828/fig2_vdart_switch.png)

**Figure 2.** Real VDART data, before and after two ±10 V squares.
(a) The **+10 V square appears as a uniform dark patch** — a full polarisation
reversal. The −10 V square is invisible, because the film's native state already
points the way −10 V drives it. (b) Both squares light up in amplitude, with the
60 nm raster lines resolved. (c) Quantified against the controls.

| region | phase vs control | \|A\| before → after |
|---|---|---|
| **+10 V square** | **−180.2°** | 45.5 → **166.5 pm** |
| −10 V square | −1.8° | 52.0 → **186.5 pm** |
| controls (4) | 0 to +3° | +5 to +14 pm |

Confirmed independently on both DART phase channels (−180.2° and −178.5°). Phase
scatter inside the squares collapses (sd 55.7 → 30.8 and 53.3 → **6.2**): the
written patches are driven to a single domain.

**The tip writes.** Every VOID has to be explained by the film or the recipe, not
the instrument.

---

## 3. The result: a DC square rewrites the in-plane director

The poled squares give something the lattice never produced — a patch whose state
is *known* to have been changed. Imaging the same area in LDART, before and
after, answers the mission question directly.

![LDART in-plane signal before and after, with the director change per region](figures_260828/fig3_ldart_rewrite.png)

**Figure 3.** Real LDART data. (a) Before: mottled, mixed-director film.
(b) After: **both squares carry clean, aligned stripes** while the surroundings
stay mottled. (c) Dominant director per window. Rings are before, dots after,
arrows drawn only where the director moved.

![Population fractions per region and excess against the control null](figures_260828/fig4_populations.png)

**Figure 4.** (a) Triad populations, before (left bar) and after (right bar) for
each window. (b) Each square's population change **differenced against the mean
control change** — the C42 within-frame statistic, so drift and any
frame-to-frame tune difference cancel.

| region | w before | w after | dominant | excess vs controls |
|---|---|---|---|---|
| **+10 V square** | 0.225 / 0.480 / 0.295 | **0.870** / 0.045 / 0.085 | **90° → 25°** | **0.662 (12.7× null)** |
| **−10 V square** | 0.430 / 0.339 / 0.231 | **0.659** / 0.060 / 0.281 | **45° → 20°** | **0.293 (5.6× null)** |
| ctrl A-lo | 0.481 / 0.200 / 0.319 | 0.491 / 0.175 / 0.334 | 45° → 45° | — |
| ctrl A-hi | 0.261 / 0.458 / 0.281 | 0.268 / 0.472 / 0.260 | 70° → 70° | — |
| ctrl B-lo | 0.298 / 0.497 / 0.205 | 0.243 / 0.500 / 0.258 | 90° → 90° | — |
| ctrl B-hi | 0.483 / 0.207 / 0.310 | 0.452 / 0.273 / 0.275 | 65° → 65° | — |

Control-to-control null **0.052**. **All four controls keep their dominant
exactly** across the same two frames.

### Three rules this establishes

1. **The final director is set by the field, not by the starting state.** The two
   squares started from *different* dominants — 90° and 45° — and both ended on
   the **same** member (~20–25°, the 14° member). This is attractor behaviour,
   and it is the pathway question the lattice experiments were built to ask.
2. **Polarity does not matter.** The −10 V square did **not** reverse P_z
   (Fig. 2, −1.8°) and rewrote its IP director just as decisively. **The IP
   response couples to |E|, not to the sign of P_z.** The two order parameters
   are not locked together.
3. **The destination is an allowed triad member**, not an arbitrary angle — and
   not the 0°/90° that a 60 nm raster imprint would produce.

---

## 4. Why the lattice failed: dose, not geometry

The DC square differs from the lattice in **both** dose (667 vs 400 V·s/µm²) and
geometry (solid vs commensurate points). Repeating the square at the lattice's
own dose separates them.

![Dose response at sigma 400 and 667](figures_260828/fig5_dose.png)

**Figure 5.** (a) Excess in units of the control null, at both doses. (b) How
single-domain the written patch ends up.

| | σ ≈ 400 (lattice-matched) | σ ≈ 667 |
|---|---|---|
| +10 V excess | **0.075 — within null** (1.4×) | 0.662 (**12.7×**) |
| −10 V excess | 0.202 — clears (3.8×) | 0.293 (5.6×) |
| dominant shift | 90→70°, 70→90° | **90→25°, 45→20°** |
| largest w after | 0.56, 0.49 | **0.87, 0.66** |

**At the lattice's dose, the geometry that works decisively at 667 largely stops
working.** One square fails the null outright; the other clears at 3.8× instead
of 12.7×; neither collapses onto a single member.

**The rewrite is dose-limited. The threshold lies between 400 and 667 V·s/µm²,
i.e. roughly 1.3–2.2 σ_c.** The point-pulse lattice's three VOIDs are consistent
with having run below that floor the whole time.

---

## 5. What theory this supports

![Theory: degenerate wells, dose threshold, polarity independence, convergence, and the open T3 test](figures_260828/fig6_theory.png)

**Figure 6.** The mechanism the observations support, and what remains untested.

**(a, b) A three-well landscape with a field-driven barrier crossing.** The three
triad members are degenerate at zero field. The tip field deepens one well; the
director switches only if the drive exceeds the barrier. This is the simplest
picture consistent with a **sharp dose threshold** between 400 and 667 — a
smooth, sub-threshold response would have shown *partial* rotation at 400, and it
did not (the +10 V square sat inside the null).

**(c) Coupling to |E|, not to P_z.** Both polarities rewrite. Any mechanism in
which the IP director is dragged by out-of-plane switching is excluded: the
−10 V square never switched P_z. The IP order parameter responds to field
magnitude. A quadratic coupling — electrostrictive, or a field-induced change in
the local strain state — is consistent with this; a linear −P·E coupling to the
IP component is not, since that would be polarity-odd.

**(d) An attractor, not a rotation.** Two different starting directors converge
on one member. The film does not rotate *by* a fixed amount; it is driven *to* a
particular state. Which state is presumably set by the tip-field geometry, and
that is directly testable by rotating the write.

**(e) T3's selection condition is still untested.** The campaign's theory T3 has
two parts: a *drive* term, and a *selection* term in which the coupling
−∫P_z E_z is non-zero only when the template wavevector matches the intrinsic
modulation, **q = Q** with **Q** = (2π/Λ)·n̂⊥.

This is what the lattice's line structure is built to deliver: alternating lines
of period Λ perpendicular to the commanded director put the template's power at
exactly **q** = (2π/Λ)·n̂⊥, and rotating the command rotates **q** with it. A solid
square has no such wavevector, so it can supply drive but cannot select. **But
the lattice never cleared the null, so selection was never tested at a dose where
anything happens.** The three VOIDs are not evidence against T3; they are
evidence about dose.

Note this cuts both ways for §3's attractor result: the DC square drove two
different starts onto the *same* member, which is what a pure drive term with no
selection should do. If selection operates, the lattice at a working dose should
be able to choose a member the square cannot.

**(f) The experiment that decides it.** Run the point lattice at σ ≈ 667 — same
dose as the working square, different geometry.

- If the lattice drives the director to a **different** member than the square
  does, **selection is real** and the commensurate template is doing physical
  work.
- If both land on the same member, dose alone decides and the selection term is
  not operating at this scale.

For the first time this is a well-posed test, because there is now a positive
control to read it against.

---

## 6. Limits of these claims

- **σ 400 vs 667 is a two-point curve.** It brackets a threshold; it does not
  measure one. (`FINDINGS` M15 is graded **B** for this reason; M13 and M14 are
  **A**.)
- **A written square is not simply re-oriented pristine film.** Lateral \|A\|
  rises less inside the squares than in the controls (+23/+29 pm vs +32…+51 pm).
  Something about the written region's lateral response is altered beyond its
  director, and that matters for whether this is a usable patterning mechanism.
- **The triad estimate is weak in a 1.2 µm window** — about 4.3 periods at
  Λ 280 nm, the minimum the FFT tolerates. The effect sizes here are far above
  that scatter, and the null is measured from four matched windows rather than
  assumed, but it is not a precision measurement of angle.
- **The direct lattice-vs-square comparison at equal dose has not been run.**
  Section 5(f) is a proposal, not a result.

## 7. Provenance

| figure | frames used |
|---|---|
| Fig. 2 | `PZTO_VDART_0002/0003` |
| Figs. 3, 4 | `PZTO_LDART_0149/0150` (σ 667, before/after) |
| Fig. 5 | above, plus `PZTO_LDART_0151/0152` (σ 400) |

Channel order is the toolkit's — **0 height, 1 Amp1, 2 Amp2, 3 Phase1, 4 Phase2,
5 Freq** — *not* the Igor header labels, which are offset by one on this
instrument. Reading the channel labelled `Phase1` returns an amplitude and makes
the phase look identically zero (`FINDINGS` M13).

Full session narrative, including three wrong conclusions and their corrections:
[`SESSION_260828.md`](SESSION_260828.md). Graded results: `FINDINGS.md` M11–M15.
Failure modes: `PITFALLS.md` 19.11–19.13.
