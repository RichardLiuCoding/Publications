# Physics: what is known, with grades, and what is open

Condensed from 54 numbered conclusions in `FINDINGS.md`. Grades: **A** solid,
**B** the direction is right but a number or a replicate is missing, **C**
suggestive only. Go to `FINDINGS.md` for the operation and the numbers behind any
entry.

---

## 1. The system

PZTO(111) thin film. Six equivalent tetragonal variants in two C₃ᵥ orbits; three
*mechanical skeletons* related by 120° rotation about [111] project to three
surface stripe directors 60° apart — the **triad**.

```
FAM_FILM = (2°, 62°, 122°)     constant within ~5° across 8+ areas   (C31, A)
Λ ≈ 250–390 nm                 not a single number; use the frame median
```

`phi0` is only defined mod 60°, so a triad fit reported as "56/116/176, 54° from
the film triad" is the *same* triad offset by 6°, mislabelled. Do not chase it.

---

## 2. The symmetry theorem — why a year of experiments failed

**A uniform out-of-plane field cannot select an in-plane director.**

The three skeletons are related by a 120° rotation about [111]; a field along
[111] is invariant under that rotation, so the coupling energy is identical for
all three and no such field at any magnitude or duration can prefer one. Every
experiment before C23 applied exactly that — uniform bias, DC offset, large-area
poling — and all of them were **symmetry-forbidden** from selecting a direction.
Their failure (C8) was a theorem, not a materials problem.

What breaks the degeneracy is a **spatially structured drive with an axis of its
own**. That is the whole reason for trajectory writing.

---

## 3. The writing recipe, clause by clause

> Write a **charge-balanced lattice of point pulses**, axis commanded **60° from
> the LOCAL dominant director**, sign **alternating** between adjacent rows,
> delivering **≳ 210 V·s/µm²** of areal charge. The dominant director rotates to
> the commanded axis.

| clause | evidence | grade |
|---|---|---|
| command from the **local** dominant, measured in that panel's own window | every successful panel; panels commanded from a frame average did not turn | **A** (C36) |
| the template must **alternate in sign** | uniform polarity fails outright: excesses +0.015 and −0.035 against a 0.065 threshold, and \|+V − −V\| = 0.050 — polarity sign is irrelevant | **B** (C43) |
| the alternation **period does not matter** over Λ → 8Λ | all four periods select at identical σ; no ordering reproduces across iterations | **B** (C41) |
| **no threshold** in charge | 0.70 σ_c selects at 3.5× the null; σ_c = 302 was *defined* as where panels cleared a threshold that was 3× too high | **B** (C47) |
| the response **saturates** | three panels spanning 2.2× in σ converged to w = 0.47 ± 0.014 from starting points spread over 0.10–0.20 | **B** (C47) |
| the **spacing**, not the charge, sets the ceiling | Λ/2 reaches 0.45–0.76 (mean 0.557); Λ/4 reaches 0.83–0.86 and is far more reproducible | **B** (C48, softened by C53) |
| **density floor** between 50 % and 70 % | keep-50 % is the only sub-threshold balanced panel in the whole re-scored set | **B** (C34) |

**σ_c = 302 V·s/µm² is now only a convenient unit of charge, not a threshold.**
C40's law `w = 0.234 ln σ − 0.887` (r = +0.974 over 19 panels) is **probably a
spacing law in disguise**: σ = V·dwell/spacing², so spacing and σ were collinear
by construction across that set, and when one iteration held spacing fixed and
varied dwell the σ dependence vanished.

**Does not help:** pre-poling makes the lattice *worse* (C27, C); a uniform
out-of-plane field does nothing (§2); single pulses above ~40 V·s switch
site-by-site rather than collectively (C21).

---

## 4. The raster — the large-area tool

A charge-balanced raster (one pass +V, one −V) along direction M:

- **On virgin film it ALIGNS the family parallel to M.** w(62°) went
  0.415 → **0.601** while the other two fell (−0.063, −0.124), over 80 windows.
  Largest single alignment in the campaign, across 42 µm² in 23.5 min — higher
  purity than a Λ/2 lattice reaches. **B** (C49)
- **On pre-poled film it DEPLETES that family**: w(6°) 0.29 → 0.14, 0.24 → 0.10,
  0.25 → 0.04. **B** (C26, revised)
- **So the out-of-plane poling state sets the sign of the effect.** Five
  measurements, three one way and two the other, split entirely by poling state —
  and C26's own single unpoled control had been on the virgin side all along.
- The *destination* is not predicted on poled film: two panels with nearly
  identical starting populations went to opposite members.

---

## 5. Rewriting — what the new campaign starts from

**C53 (B) — the director is REWRITABLE.** One panel driven 64° → 124° (stage 1),
then commanded back and returning to **64°** with w = 0.757, excess +0.195 =
**3.8×**, while its population along the first command collapsed to 0.162. The
same tool that sets a state can reset it.

**C53's retention half is confounded and must be redone.** The companion panel
kept its dominant director but its amplitude fell 0.696 → 0.609 (−0.087,
comparable to the threshold) over ~22 min. Two problems: the two panels sat
**0.1 µm apart** edge-to-edge, so stage 2's write was effectively adjacent to the
"untouched" control; and they had different starting dominants and commands, so
they are not two arms of one contrast.

**C50 (B) — a raster-aligned state does not decay.** 0.601 → 0.597 → 0.598 over
34 minutes with the tip in contact, three time points, 80 windows each. So a
raster-aligned state is stable where a lattice-written one may not be — that
contrast is the sharpest retention question.

**C54 (B) — the commanded director is not always the one that wins.** Two panels,
same σ, spacing and geometry, each commanded 60° from its own dominant:

| started | commanded | ended | w(cmd) | excess |
|---|---|---|---|---|
| 4° | 64° | **64°** ✓ | 0.696 | 7.7× |
| 64° | 4° | **124°** ✗ | 0.369 | 3.4× |

The second panel's population along its command rose enough to clear the
threshold *and its dominant went to the third member*. **"Clears the threshold"
and "ends on the command" are separable outcomes**, and only the second is what
patterning needs. This is why the UTK letters read 63 % on-target rather than
100 %. It is the single biggest limitation now known, and RW1 attacks it.

**C51 (A) — the rules compose.** "UTK" written into orientation at **11.1×** the
null: strokes w = 0.483 against 0.157 between them, dominant within 20° of the
command over 63 % of stroke probes against 5 % between. Raster to align a 42 µm²
background, masked lattices to override locally.

---

## 6. Open questions, most important first

| | question | why it matters |
|---|---|---|
| **Q28** | Why does a spatially **uniform-sign raster** align strongly (C49, +0.186) when a spatially **uniform-sign lattice** does nothing at all (C43, 0.2× and −0.5×)? Each raster pass is one polarity throughout, so it has no sign boundaries between adjacent lines | **The sharpest contradiction in the theory.** Two of the strongest results cannot both be right about the mechanism. Discriminator: a raster with sign alternating between *adjacent lines* vs one alternating only between *passes*, plus a lattice at the raster's line pitch |
| **Q31** | Why does a panel sometimes end on the third member rather than the commanded one (C54)? | the ceiling on patterning fidelity |
| **Q19** | If not commensuration and not the sign period, what does the film couple to? Leading candidate: the strain / depolarisation field of a **sign boundary** | the mechanism itself. `run_it7.py` is built to separate the lattice axis from the boundary orientation and has never run |
| **Q29** | Does a lattice-written state decay where a raster-aligned one does not? | endurance; C53's answer is confounded |
| **Q21** | Where between 8Λ and uniform does alternation stop working? | `run_it8.py` is built and unrun |
| **Q25** | Where is the *lower* bound in charge? 0.70 σ_c works; nothing is known to be insufficient | efficiency, and the shape of the drive law |
| **Q27** | Is the purity ceiling set by spacing alone, independent of σ? One cell (Λ/4 at *low* σ) has never been written | the recipe's ceiling |
| **Q30** | Why did the three UTK letters gain unequally (+0.301, +0.418, +0.516) when coverage was uniform? It tracks position along the word, not topography | a spatial gradient nobody has explained |
| — | **Fatigue**: does purity survive repeated rewriting? Never tested | endurance, and it is the obvious next thing after C53 |

---

## 7. The mechanistic picture, stated as a guess

Not a conclusion — a frame for designing experiments, to be attacked rather than
defended.

Commensuration is dead (a 2Λ template works). Uniform polarity is dead (it does
nothing). What the four working template periods share is the **axis** and the
existence of **sign boundaries**; and re-scored magnitudes order themselves by
boundary count — 16 boundaries 7.3×, 4 boundaries 5.7×, 1 boundary 2.5×, zero
boundaries nothing. That suggests the film couples to the **line of alternating
polarity** — a locus with strain and a depolarisation field along it — rather
than to a periodicity.

**The raster refuses to fit this.** Its passes are uniform in sign, so it has no
such boundaries, and it produces the largest alignment measured. Either a
continuous sweep couples through something isolated dwells do not, or the
relevant structure is the line pattern at Λ/2 pitch rather than the sign pattern.
Resolving that (Q28) is worth more than any further refinement of the lattice.
