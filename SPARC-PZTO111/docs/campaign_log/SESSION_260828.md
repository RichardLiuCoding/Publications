# Overnight session, 28 August 2026 — what was found

Written for the operator to read at 09:00. Headline first.

---

## 1. The headline

**The point-pulse lattice did not rewrite the in-plane director in three
attempts. A DC-poled square did, decisively — and a dose-matched control shows
the lattice failed because it was under-dosed, not because of its geometry. The
threshold sits between 400 and 667 V·s/µm².**

Also: three confident conclusions I reached during the night were wrong, each
for a different and instructive reason, and all three are now corrected in
`FINDINGS.md` and `PITFALLS.md`. The corrections are the reason the session is
worth anything — the first two would have sent you to move the coarse stage on a
sample that was fine.

```
iteration 10 · 183.47 of 330 write-minutes · 2 areas · 2 strikes
```

**Two writes landed**, both from `run_it12_pathway.py`: 10.86 min at (−16,+8)
and 7.99 min at (+8,+8). Both VOID.

**Four DC-poled squares are on the sample and are NOT in `used_areas`**, because
the poling scripts are diagnostics and deliberately do not touch
`campaign_state.json`. They are at **(8,−8), (16,−8) and (16,+8)** — two 1.2 µm
squares each, centred at (1.6, 2.5) and (3.4, 2.5) µm within a 5 µm field.
Nothing stops a later iteration from screening onto them, so either add them by
hand or avoid those three offsets.

---

## 2. The result that matters

A solid 1.2 µm square, DC-poled at ±10 V, **rewrites the in-plane super-domain
director onto a single triad member**. Measured before and after on the same
patch, differenced against four untouched controls in the same frames:

| region | w before | w after | dominant | excess vs controls |
|---|---|---|---|---|
| **+10 V square** | 0.225 / 0.480 / 0.295 | **0.870** / 0.045 / 0.085 | **90° → 25°** | **0.662** |
| **−10 V square** | 0.430 / 0.339 / 0.231 | **0.659** / 0.060 / 0.281 | **45° → 20°** | **0.293** |
| ctrl A-lo | 0.481 / 0.200 / 0.319 | 0.491 / 0.175 / 0.334 | 45° → 45° | — |
| ctrl A-hi | 0.261 / 0.458 / 0.281 | 0.268 / 0.472 / 0.260 | 70° → 70° | — |
| ctrl B-lo | 0.298 / 0.497 / 0.205 | 0.243 / 0.500 / 0.258 | 90° → 90° | — |
| ctrl B-hi | 0.483 / 0.207 / 0.310 | 0.452 / 0.273 / 0.275 | 65° → 65° | — |

Control-to-control null **0.052**. The squares clear it by **12.7× and 5.6×**,
and **all four controls hold their dominant exactly** across the same two frames.

Three things in that table are worth more than the significance:

1. **The two squares started from different directors — 90° and 45° — and ended
   on the same member.** For DC poling the final state is set by the field, not
   by where the film started. That is the sink behaviour the pathway experiments
   were designed to look for, arriving from a geometry they do not use.
2. **Both polarities do it.** The −10 V square did *not* reverse out-of-plane
   (VDART phase change −1.8° vs control) and still rewrote its in-plane director.
   The in-plane response is not contingent on P_z reversal.
3. **It lands on an allowed triad member** (14° in that frame), not an arbitrary
   angle, and not the 0°/90° a raster imprint would produce.

→ `FINDINGS` **M14**, grade **A**.

## 3. The tip works — this had to be established

Three VOIDs in a row made "no bias is reaching the sample" the leading
hypothesis. It is wrong:

| region | VDART phase vs control | \|A\| before → after |
|---|---|---|
| **+10 V square** | **−180.2°** | 45.5 → **166.5 pm** |
| −10 V square | −1.8° | 52.0 → **186.5 pm** |
| control | — | 43.1 → 47.9 pm |

A textbook 180° reversal, confirmed independently on both DART phase channels
(−180.2° and −178.5°). → `FINDINGS` **M13**, grade **A**.

---

## 4. The three things I got wrong

### 4.1 Every lamellar period was measured 2× too large

The screening code took the pixel size from `FRAME` (the 10 µm *scored* size)
and applied it to a 5 µm *screening* frame. Sixteen candidates read 388–755 nm;
the true values were 194–378 nm — **all inside the buildable window**, not six of
seven outside it.

This produced the first draft's headline recommendation, *"move the coarse
stage"*, which was false. It also drove a real design decision: abandoning the
two-panel within-frame pair for one panel per frame, discarding C42's drift
cancellation for nothing.

Nothing caught it because the code was *correct code computing the wrong
quantity*: no exception, plausible numbers, and the offline simulation
reproduced it faithfully. Worst of all it was **self-consistent** — sixteen
candidates agreed, and their agreement felt like evidence. A constant-factor
error moves the whole distribution and leaves its shape alone.

Found by cross-check: `survey_lambda.py`, written for another purpose, computed
its scale from its own frame and read 301 nm where the driver read 548.
→ `PITFALLS` **19.11**.

### 4.2 The re-tune fix went to the half of the measurement that was complaining

M8 established that the contact resonance drifts in 5–10 min and that re-tuning
before each frame fixes it. That fix went into the three baselines. It did not go
into the post-write frames, the angle control, or the zooms — **which are the
half the verdict is computed from.**

| phase | r12 | median \|A\| |
|---|---|---|
| baselines (re-tuned) | 0.93 / 0.93 / 0.93 | 66 / 72 / 75 pm |
| after-frame 1 | 0.93 | 64 pm |
| after-frame 2 | 0.70 | 30 pm |
| the four zooms | 0.31 / 0.28 / 0.45 / **0.16** | 25–28 pm |
| angle control | **0.40** | **25 pm** |

**The verdict fitted its triad on that last frame.** The write takes 11–22 min
and the resonance drifts in 5–10, so the readout *always* starts outside the
baselines' tune — this was structural, not bad luck.

The asymmetry is the lesson: a collapsed baseline raises the floor and halts the
run, loudly, before any write. A collapsed readout produces small excesses, which
look exactly like a null. **The unprotected half was the dangerous half.**
→ `FINDINGS` **M12**, `PITFALLS` **19.13**.

### 4.3 "No bias reaches the sample"

Reached from VDART reporting *"ONE CLASS ONLY, minority in patches ≥25 px: 0%"*
after both lattice writes. That headline is a heuristic, and on the poling frame
it printed the same string for a frame containing an unmistakable −180° square —
while its own "minority in patches: 71%" said the opposite. I read the verdict
string instead of the number under it. Section 3 is the refutation.

---

## 5. What the three tasks actually got

**Task 1 — pathway and rewriting rules.** No answer from the point-pulse lattice:
three iterations, all VOID, none clearing the leave-one-out null. Two of the
three are explained (§4.2 readout, §4.1 area selection). The third had a clean
readout and still showed panels moving no more than the untouched tiles.
**But §2 answers a version of the question**: under DC poling the director is
driven to one member regardless of starting direction and regardless of polarity.

**Task 2 — leftovers along the original director.** Quantified but not improved.
Mean residual population along the original director was **0.584** in the first
iteration and **0.366** in the second, against ~0.17 for a perfect rewrite and
0.333 for an even three-way split. `run_it13_leftovers.py` (ISO vs
denser-along-line) is validated and ready but was never reached.

**Task 3 — limitations and minimum dose. Answered.** The dose-matched control
ran and separated the confound. The same DC-square geometry at σ ≈ 400 — matched
to the lattice — largely stops working:

| | σ ≈ 400 | σ ≈ 667 |
|---|---|---|
| +10 V square excess | **0.075 — within null** (1.4×) | 0.662 (**12.7×**) |
| −10 V square excess | 0.202 — clears (3.8×) | 0.293 (5.6×) |
| dominant shift | 90→70°, 70→90° | **90→25°, 45→20°** |
| largest w after | 0.563, 0.492 | **0.870, 0.659** |

**The rewrite is dose-limited, not geometry-limited.** A geometry that works
decisively at 667 manages only a marginal effect at 400, so geometry cannot be
the main reason the lattice failed. **The threshold on this film lies between 400
and 667 V·s/µm², i.e. between about 1.3 and 2.2 σ_c.** → `FINDINGS` **M15**,
grade B (two dose points is a two-point curve).

This directly condemns `run_it14_mindose.py` as designed: it tests **0.25 and
0.50 σ_c**, far below the floor just established, and would return nulls by
construction. **Invert the ladder to 1.3 / 1.8 / 2.2 σ_c** — at the lattice
spacing 2.2 σ_c is ~17.6 V·s/site, inside C21's 20 V·s half-limit, so the whole
range is reachable.

---

## 5b. Why the session stopped writing at 07:35

`S25 — 2 consecutive unreadable iterations, halt and ask.` Both IT12 writes came
back VOID, which is two strikes, and the envelope stops there by design.

I did **not** override it, although I had a good argument to: the next run would
have used a dose above the M15 threshold, a corrected pixel scale, and a re-tuned
readout, so all three known causes of the earlier voids were addressed. Two
reasons for not touching it anyway.

1. S25 exists to stop exactly the pattern the night was in — repeated writes that
   cannot be read. "This time is different" is what it is built to be sceptical
   of, and it asks for a *human* judgement, which was not available.
2. Resetting a strike counter because I believed the next attempt would work is
   the same move as re-screening an area until its gate passes. I argued against
   that at 04:00 and wrote it into `PITFALLS` 19.12; doing it at 07:35 because it
   was now inconvenient would make the rule worthless.

**To resume**, clear the strikes deliberately and run the pathway experiment
above the threshold:

```bash
IT12_AREA="-8,0" IT12_SIGMA=2.58 IT12_TAG=abovethreshold python run_it12_pathway.py
```

`(−8,0)` screened at modulation 0.225 with four slots and 21 control tiles.
2.58 σ_c is 17.6 V·s/site, inside C21's 20 V·s half-limit, and above the
400–667 V·s/µm² threshold M15 establishes. That is the experiment the whole night
was trying to run, and it is now the first one that would run with an adequate
dose, a correct pixel scale, and a healthy readout at the same time.

---

## 6. Tools added

| file | what it does |
|---|---|
| `diag_poling.py` | two ±10 V DC squares, VDART before/after — "does the tip write" |
| `diag_poling2.py` | the same with **LDART** before/after — the in-plane before/after |
| `diag_poling3.py` | dose set by `DIAG_SPEED`, area by `DIAG_X`/`DIAG_Y` |
| `diag_ip_after_poling.py` | in-plane populations in matched windows inside/outside squares |
| `survey_lambda.py` | maps Λ, modulation, streak across the scanner; measurement only |
| `probe_health.py` | r12 and \|A\| per frame in time order — run this before believing any VOID |

Driver changes: pixel size now derived from each frame's own header; every
post-write acquisition re-tuned; screening stops after three candidates settle a
2×2 layout (was 20 candidates, ~54 min); `IT12_AREA`/`IT13_AREA`/`IT14_AREA`
screen one offset and take fresh baselines; `IT12_SIGMA` and `IT12_TAG`; the
verdict header now describes the design that was actually built.

---

## 7. What to do first

1. **Invert `run_it14_mindose.py` to 1.3 / 1.8 / 2.2 σ_c** and re-run the
   pathway experiment above the threshold. This is the one change that makes the
   whole IT12/IT13/IT14 programme viable again — every void of the night is
   consistent with having worked below the floor.
2. **Run a point lattice at σ ≈ 667.** M15 shows dose is the leading term but
   does not show geometry is irrelevant. A commensurate point lattice at a dose
   known to work is now the clean test of T3's selection condition, and for the
   first time there is a positive control to read it against.
4. **Check the written squares for damage.** Lateral \|A\| rises less inside them
   than in the controls (+23/+29 pm vs +32…+51 pm). A written square is not
   simply re-oriented pristine film, and that matters for whether this is a
   usable patterning mechanism.
5. **Re-pin `FAM_FILM` for this stage position.** The lab triad here is 19/79/139,
   ~18° off the pinned (2, 62, 122); the >10° warning fired on 13 of 13
   candidates and has become log furniture. → `FINDINGS` **M11**.
