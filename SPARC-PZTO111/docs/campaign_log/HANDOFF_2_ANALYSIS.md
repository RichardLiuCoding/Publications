# Analysis: how to score the data, and how this has gone wrong

**The highest-value file in the handoff.** Over three days the physics
conclusions were revised four times and the *measurement* was revised six. Every
revision was invisible from inside the analysis and became visible only when the
real code was run against real data, or when the operator said one sentence.

---

## 1. The observable — direction, never amplitude

The quantity is the **population vector over the pinned triad**: which of the
three directors dominates a window, and by how much.

```python
triad, tt = g('pin_triad')(tag, ref_fam=g('FAM_FILM'))   # FAM_FILM = (2,62,122)
s = g('dir_state')(tag, cx, cy, win_um, triad, cmd_deg)
# s['w'] = (w0,w1,w2) normalised, s['dom'], s['w_cmd'], s['lead'], s['on_target']
```

**Never score Δ(angular FFT power).** Amplitude conflates "the texture got
stronger" with "the texture turned", and every question here is about turning.
Scoring amplitude invalidated five sections of analysis; the operator caught it
with one sentence ("we only care about the directions"). Rebuilding on the
population vector turned one section from empty to 4/4 positive and withdrew
another's headline.

`lead = w(commanded) − max(w(other two))`. Use **final w(cmd)** for magnitude
comparisons and `lead` only within one frame: Δ(lead) inherits the starting
state, and on one matched comparison the between-condition gap (+0.116) was
smaller than the scatter (0.554) on Δ(lead) while being clean on final w.

---

## 2. Compare within a frame, never between frames

A before/after difference carries every difference between the two frames —
drift, gain, mode changes, and stage hysteresis. The fix (C42):

```
excess = [w_panel − mean(control tiles)](after)
       − [w_panel − mean(control tiles)](before)
```

Each bracket is within-frame, so drift cancels inside it; the difference then
cancels the *spatial* bias from tiles sitting at frame edges while panels sit in
a row. This works through conditions that defeated the old metric: during one
iteration the withdrawn deflection drifted −0.827 → −0.439 → −0.786 and the
between-frame floor was 0.223 with 21 % flips, and the within-frame contrast
still gave a clean 2.1× result.

**Score the control tiles along each panel's own command.** Reading them once at
`panels[0]['cmd']` is only harmless when every panel shares a command; the triad
members are not equally populated, so along a different director that is a real
offset.

---

## 3. The threshold must be the null of the statistic you use

This is the deepest error made in the campaign and it turned a real result into a
null and back again.

The panel statistic is a *before/after contrast*, which removes static spatial
structure. The threshold used was `2 sd of w over the tiles in the after-frame` —
a quantity **dominated by exactly what the contrast removes**. The test was
conservative by about a factor of three.

**Correct null (C45): apply the panel statistic to each untouched tile,
leave-one-out.**

```python
for i in range(n):                      # n tiles
    m = np.ones(n, bool); m[i] = False
    d[i] = (wa[i] - wa[m].mean()) - (wb[i] - wb[m].mean())
threshold = 2.0 * d.std(ddof=1)
```

Leave-one-out is not optional: keeping tile *i* in its own reference mean shrinks
`d[i]` by (1 − 1/n) and correlates the estimates. A panel is out-of-sample with
respect to the tiles, so its null must be too.

Measured: threshold 0.065 against 0.192 (40 tiles) and 0.050 against 0.128
(16 tiles) — **ratio 0.34–0.39**. Consequence: one iteration's reference read 1.0×
("nothing switched") and, rescored, **2.8× and 3.6×** on two independent
after-frames. Re-scoring everything moved another iteration's panels from
2.8/2.2/1.0× to 7.3/5.7/2.5×.

**Also report the non-parametric version**: `max|d|` over the untouched tiles
assumes nothing about the distribution. When a result is close, quote that.

**Corollary that bit hard:** improving a control can *raise* a threshold and hide
a real effect if the threshold is not the statistic's null. Gridding the tiles
instead of using two edge bands was a genuine improvement and it made the test
*less* sensitive, because it sampled more static structure into a threshold that
should never have contained any.

---

## 4. Control tiles

Build them by **subtracting the written footprints from a grid over the whole
frame**, never by arithmetic on one panel row's coordinate.

```python
step = WIN + 0.10
cand, yc = [], 0.35
while yc + WIN <= FRAME - 0.35:
    cand += g('ctrl_tiles')(0.35, FRAME - 0.35, yc, yc + WIN, WIN)
    yc += step
tiles = [rg for rg in cand if clears_every_panel(rg, halo + margin)]
```

`ctrl_tiles` tiles **only in x, at the band's centre y** — one call is one row of
tiles. The old code computed the upper band from the top edge of the *first*
panel row, so on a 2×2 grid it began inside the second row and ran tiles straight
through a written panel. Audited: 3 of 14 tiles overlapped a panel. The excesses
moved ≤ 0.022 and no verdict changed — but that was luck.

Then **drop tiles over terrace steps**, relative to the frame median height
range (not an absolute nm cut — the absolute scale varies with sample, scan size
and noise). Keep ≥ 8 tiles or say the null is inflated.

---

## 5. Two area gates, and neither replaces the other

| gate | what it measures | limit | what it decides |
|---|---|---|---|
| **sd(w)** over untouched tiles | how much population varies place to place | 0.150 | the *size* of the threshold |
| **flip rate** on consecutive baselines | how often the argmax changes | 25 % | whether "dominant director" is *defined* at all |

An area can have a perfectly normal sd(w) and a useless flip rate: one had
sd 0.109 and 31 % flips at modulation 0.21, because the three populations were
close enough to tied that an arbitrarily small change swapped the nominal winner.
Since every verdict requires the dominant director to *end on the command*, such
an area cannot support the experiment however quiet its populations are.

Gates that were tried and **do not** predict readability: Λ-consistency across
triad members (that is estimator noise — the per-member spread runs 15–62 %
everywhere), a modulation cut at 0.20, and the before/after floor (one area
passed at 0.209 against 0.25 and still resolved nothing).

Measure both gates from the baselines you are taking anyway, **before writing**.
Refusing to write costs 35 min of screening and saves a write plus an
uninterpretable readout.

---

## 6. Resolution limits — these are physics, not choices

- The director is only defined over a few lamellar periods, so the readout window
  is at least **4Λ ≈ 1.2 µm**, and **no feature thinner than that is resolvable
  at any pixel count**. Scanning 512 px instead of 256 drops the 24-px floor but
  not the 4Λ floor.
- Legibility of a shape then follows: a stroke needs width ≥ 2 × stroke for its
  own interior gap to survive, and gaps between features ≥ stroke. A three-letter
  word spans ≥ 8 × stroke ≈ 9.6 µm.
- **Λ is not a single well-determined number.** Per-member estimates in one frame
  gave 280 / 388 / 261 nm and local estimates do not converge with block size.
  Use the **frame median**; commensuration is only ever defined to ±30 %.
- `dir_power` crops wide bands to `min(shape)` and silently scores a square at
  the left end; it returns `nan` below 24 px. Use `sq_power` / `ctrl_tiles`.
- **Streak artefact**: scan lines run along x, so line-to-line offsets put FFT
  power on q_y, which reads as a director of **0°**. Healthy frames run
  0.009–0.077; 0.115 is a bad frame. Be sceptical of any result that favours the
  member nearest 0°.

---

## 7. The catalogue — six ways the measurement was wrong

Ordered by cost. Check a new design against all six.

1. **Amplitude instead of direction** (§1). Cost: five sections.
2. **Between-frame instead of within-frame** (§2). Cost: two iterations wrongly
   declared unreadable.
3. **A threshold that was not the statistic's null** (§3). Cost: a positive
   result reported as a null, and a re-analysis of everything.
4. **Control regions that were not control regions** (§4).
5. **Gating on proxies** instead of the quantity that decides the outcome (§5).
6. **Comparing two numbers computed different ways** and attributing the
   difference to the sample. One threshold from 40 gridded tiles was compared
   against another from 14 edge-band tiles and the gap written up as a film
   difference; measured identically the two areas agree. That conclusion was
   withdrawn the day it was written.

The lesson from 4 and 6 together is symmetric: in one a procedural difference was
assumed harmless, in the other assumed physical. **Before attributing a
difference between two numbers to the sample, check the two numbers were computed
the same way.**

---

## 8. Four times the material was blamed for a measurement problem

Each was a hair's breadth from being written down as physics.

| observation | first explanation | actual cause |
|---|---|---|
| VDART minority 46 → 36 → 33 → 19.5 % over four areas | progressive out-of-plane poling of the sample | withdrawn deflection had drifted −0.8 → −0.6 V; restored, it read 38.4 % |
| control tiles flipping 31 %, floor 0.35 | region too weakly textured for the metric | frame sequencing — the stage does not return after an excursion |
| Λ = 280 / 388 / 261 nm across members | the three variants have different periods | `period()` is unreliable per member and does not converge with block size |
| `read_meter` swinging −0.84 / −0.44 / +0.600 | contact force drifting | channel 2 reports tip state; the setpoint held at 0.600 V |
| 31 % flips + "retune here" + \|A\| 30.7 pm | dying probe, stop the run | area had near-degenerate populations; tile spread flat at 0.081–0.109 across five iterations |

**Rule.** When a measurement misbehaves, exhaust the measurement before the
material: is the comparison between *consecutive* frames? Has any instrument
parameter moved? Is the estimator stable against its own window size? **Does this
number mean the same thing at each reading?** Only then consider the sample.

The last question generalises: a number that is *stable* is not necessarily a
number that means *one thing*.

---

## 9. Reporting

State, for every claim: the operation (area, Λ, σ, spacing, command, n panels),
the numbers with their threshold, the grade, and what would falsify it. Then the
honest limits — replicate count, confounds, and which comparison the design
actually matched.

Use the existing 54 entries in `FINDINGS.md` as the template. The five withdrawn
or revised ones are the most instructive.
