# The rewriting programme — six designed iterations

Each entry is a complete design: question, geometry, dose, cost, pre-registered
outcomes, and what it would take to build it. Costs assume a 12 µm frame at
256 px (frame 5.1 min, screening 5.8 min per candidate) and Λ ≈ 300 nm.

**Run order: RW1 → RW2 → RW4 → RW3 → RW5 → RW6.** RW1 first because every later
design needs the transition matrix; RW4 before RW3 because a decay time changes
how you interpret any multi-stage result.

A session with ~6 hours of instrument time fits roughly RW1 + RW2 + one more.

---

## RW1 — the pathway map *(pathways; attacks C54 / Q31)*

**Question.** From a given starting director, which of the other two can you
actually reach? C54 found a panel commanded to 4° ending on 124° while clearing
the threshold. Is the loser a *direction* (something special about 4°, the member
nearest the fast scan axis) or a *history* (something about starting on 64°)?

**Design.** One frame, 6 slots settled, **4 panels written**, all identical in σ,
spacing, density and geometry. Select slots so that all four share the **same
starting dominant** D. Then command:

| panel | command | tests |
|---|---|---|
| A1 | D + 60° | reachability of one neighbour |
| A2 | D + 60° | replicate |
| B1 | D − 60° | reachability of the other neighbour |
| B2 | D − 60° | replicate |

Two replicates per target is the point — C54 rests on one panel per condition and
cannot separate its two explanations.

**Parameters.** σ = 1.2 σ_c, Λ/2 spacing, n = 16, sign_every = 1, V = 10.
Dwell ≈ 0.72 s → ~4 × 256 × 0.72 × 1.35 ≈ **16 min** of writing.
Total with screening, baselines and readout ≈ **80 min**.

**Pre-registered outcomes.**
- *Both targets reached, replicates agree* — the transition is symmetric and C54
  was a one-panel fluke or specific to that area. Fidelity is not
  direction-limited.
- *One target consistently fails* — a **sink or a forbidden transition** exists.
  Report which, and repeat at a different starting D to see whether the sink
  follows the absolute direction or the relative rotation sense.
- *Replicates disagree within a target* — the transition is stochastic; the
  quantity to measure is then a *probability*, which changes the whole programme
  and needs many panels rather than a few.
- *Nothing switches* — void; check the gates, do not interpret.

**Note.** Report both criteria separately for every panel: `excess > threshold`
**and** `dominant == commanded`. C54 exists because those were conflated in one
print statement.

---

## RW2 — cycling and fatigue *(dynamics + limitations; brand new)*

**Question.** Does purity survive repeated rewriting? Nothing in the campaign has
written the same region twice except once (C53), and endurance is the first thing
any memory application asks.

**Design.** Two panels, far apart (see the adjacency lesson below). Panel **CYC**
gets N alternating writes A → B → A → B …, with a **read after every write**.
Panel **REF** is written once in the first cycle and never again — it separates
fatigue from drift over the same interval and the same scans.

**Cost per cycle** = one write (256 sites, 0.72 s, ≈ 4.2 min) + one frame
(5.1 min) ≈ **9.5 min**. Six cycles ≈ **57 min** plus setup ≈ **95 min** total.
If that exceeds the per-write budget in aggregate, split as RW2a (cycles 1–3) and
RW2b (cycles 4–6) with the state committed between.

**Placement is critical.** C53's retention control sat 0.1 µm from a later write
and its 0.087 decay could not be separated from perturbation. Put REF **at least
2 halos (≈ 4 µm) clear** of CYC, and verify the separation in the offline
simulation before writing.

**Pre-registered outcomes.**
- *Purity constant across cycles* — no fatigue over N cycles; report N as a
  lower bound on endurance.
- *Monotonic decay* — fatigue. Fit the decay per cycle; that number is the
  endurance figure of merit.
- *Ratchet / asymmetry* — A → B works better than B → A, or purity accumulates
  in one direction. This would connect directly to RW1's transition matrix.
- *REF also degrades* — the interval or the readout is drifting, not the state.
  Inconclusive on fatigue; that is what REF is for.

---

## RW4 — retention, done properly *(limitations; Q29)*

**Question.** Does a **lattice**-written state decay, where a raster-aligned one
did not (C50: flat over 34 min)? C53 suggests it might (0.696 → 0.609 in 22 min)
but is confounded.

**Design.** Three panels written **identically and simultaneously** in one write,
then read at **t ≈ 0, 30 min, 2 h**, and again the next session if the operator
can leave the stage. Nothing else is written in the frame afterwards — that is the
whole design. Use the waiting time for offline analysis, not for another write.

For a same-session control on scanning damage, read one panel every interval and
a second only at the start and end: if the frequently-read panel decays faster,
the readout itself is perturbing the state, which would matter for everything.

**Cost.** One write ≈ 12 min; four reads ≈ 21 min; total instrument time ≈ 50 min
spread over 2+ hours, most of it idle. Cheap in tip-time, expensive in wall
clock — run it *alongside* offline work, not instead of it.

**Pre-registered outcomes.**
- *Flat like the raster* — lattice-written states are non-volatile; C53's decay
  was the adjacent write.
- *Decays with a measurable time constant* — report it; the raster/lattice
  difference then becomes a real mechanistic clue (different final states, not
  just different purities).
- *Frequently-read panel decays faster* — the measurement perturbs the state.
  This would require re-examining every before/after result in the campaign.

---

## RW3 — does overwriting cost more than writing? *(dynamics)*

**Question.** C27 found pre-poling makes the lattice *worse*, which hints that
history raises the barrier. Does a rewrite need more charge than a virgin write?

**Design.** Four panels, all first written identically to state B. Then rewrite
each back toward A at a **σ ladder**: 0.5, 0.8, 1.2, 1.8 σ_c. Compare the
rewrite dose-response against the *virgin* dose-response already measured (C47:
0.70 σ_c gives excess +0.333 at 3.5×, and the response saturates above that).

**Parameters.** Stage 1: four panels at σ = 1.2 σ_c ≈ 16 min. Stage 2: four
panels at the ladder doses ≈ 20 min. Two writes, each under the cap.
Total ≈ **110 min**.

**Pre-registered outcomes.**
- *Same as virgin* — no history barrier; rewriting is just writing.
- *Shifted to higher σ* — a history barrier exists; its size is the shift, and
  that is a real energetic quantity.
- *No dose works* — the first write pins the state; C53's success was
  special (different starting member, or the return direction is privileged).

---

## RW5 — the mechanism, and the contradiction *(mechanisms; Q28 + Q19)*

Two experiments, both cheap, both already partly built.

**RW5a — lattice axis or sign boundary? (Q19)** `run_it7.py` exists, is audited,
simulated, and verdict-tested, and has never run: it halted on an area whose
populations were near-degenerate. Four panels — two with sign boundaries
**parallel** to the command (the standard recipe), two with them **perpendicular**
— identical sites, σ, axis and command; only the sign assignment rotates 90°.
15 min of writing. If PAR works and PERP does not, the film couples to the
boundary line, not the lattice axis, and that answers Q19.

**RW5b — the raster/lattice contradiction (Q28).** Three treatments in one frame:
1. a raster with sign alternating **between adjacent lines** (has boundaries),
2. a raster alternating only **between passes** (the current recipe; no
   boundaries within a pass),
3. a **lattice at the raster's line pitch** and matched dose.

If the continuous sweep is what matters, 1 and 2 agree and 3 fails. If the sign
structure is what matters, 1 beats 2. Either result resolves a direct
contradiction between two of the strongest conclusions in the campaign, which is
worth more than any further refinement of the lattice.

**RW5b needs building.** Copy `run_it6.py`'s two-stage structure; the raster
variant with per-line alternation may need a new generator — check whether
`gen_center_out_raster`'s `alt_period` parameter already provides it before
writing one.

---

## RW6 — the transition in progress *(dynamics)*

**Question.** Does the population move continuously with dose, or jump? RW1 and
RW3 sample end states; this samples the path.

**Design.** One panel, written in **increments**: apply σ ≈ 0.3 σ_c, read, apply
another 0.3, read, and so on to ~1.8 σ_c total. Six increments, six reads.
Because C47 found the response saturates, the interesting structure is all below
saturation.

**Cost.** Increments are cheap (0.3 σ_c ≈ 1 min each); the reads dominate:
6 × 5.1 ≈ 31 min. Total ≈ **75 min**.

**Pre-registered outcomes.**
- *Smooth sigmoid in w(cmd)* — continuous domain-wall motion; extract a
  characteristic dose.
- *A jump between two reads* — a nucleation-and-avalanche picture; the dose at
  which it jumps is the quantity to report.
- *Population moves to the third member first, then to the command* — an
  intermediate state, which would explain C54 as an incomplete two-step path and
  would be the most informative outcome available.

The last branch is worth stating loudly: if the film routinely passes *through*
the third member, then C54's "wrong" endpoint is a snapshot of an unfinished
transition rather than a failure, and the fix is more dose rather than a different
command.

---

## Cross-cutting design rules for this programme

1. **Every multi-stage iteration must declare `reuse_areas`** in its proposal, or
   S9 will refuse the second write into its own area.
2. **Space the control panel far from any later write.** ≥ 2 halos. C53's
   retention result was lost to a 0.1 µm gap.
3. **Match what you compare.** Settle more slots than panels and select the ones
   sharing a starting dominant. If you cannot, say which comparison is confounded
   and by how much.
4. **Report both criteria** — excess and on-target dominance — separately, every
   time.
5. **Read the VDART after any raster.** C51 saw the out-of-plane state go from
   ~30/70 to 54/46 across a raster-plus-letters iteration; since the letters were
   charge-balanced to the site, the raster is the likelier cause, and C13's
   re-poling warning applies to rasters more than to lattices.
6. **Budget `dir_state` at 1.6 s per call.** A per-cycle read in RW2 over 32 tiles
   plus panels is ~2 min of compute on top of the frame; a full director map is
   tens of minutes.
