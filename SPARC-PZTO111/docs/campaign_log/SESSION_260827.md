# Session 27–28 August 2026 — what happened, what it cost, what to do next

Written for the operator to read at 09:00. The honest headline first, the
evidence after it.

---

## 1. The headline

**Nothing was written to the sample.** Every launch stopped at a gate before any
bias reached the tip. Campaign state is exactly where it started:

```
iteration 8 · 164.62 of 330 write-minutes · 0 areas used · 0 strikes
```

That is not a good night's yield and I am not going to dress it up. Six of the
nine stops were defects of mine, and **one of those six wasted most of the
night**: the screening code measured the lamellar period with the wrong pixel
size and reported it at exactly twice its true value, which made a perfectly
buildable region look unbuildable. Details in §2.3 — it is the most important
thing in this document.

What the session did produce is a working instrument path, a per-frame re-tune
that fixes a readout collapse which had been misdiagnosed as bad film, and
eleven graded findings — five of which **correct or narrow earlier claims**,
including three of my own from the same day.

---

## 2. Why nothing was written

Nine launches, nine stops. Grouped by cause, because the pattern matters more
than the count:

| cause | launches | mine or the sample's? |
|---|---|---|
| defects I introduced | 3 | **mine** |
| readout collapse (contact resonance drift) | 3 | instrument, now fixed |
| geometry: film "too coarse" for the frame | 3 | **mine** — the period was misread by 2x |

### 2.1 The three that were my fault

1. **A false-positive "fix".** My dict-key checker reported `run_it7.py` missing
   a `'mode'` key. It was not missing — a `**{...}` splat eleven lines below
   supplied it. Adding it explicitly made `dict()` raise `TypeError` on a
   duplicate keyword, in the scoring block, *after* the write. I turned a
   non-existent crash into a real one, in the driver about to run. Caught by the
   offline simulation while the run was still screening. → `PITFALLS` 19.8.
2. **A stale literal.** Cutting the design from four panels to two, I updated
   the layout logic and the assertions but left `if len(flat_ok) < 4` behind. It
   halted a run *immediately after* it had passed the floor gate at 0.087 —
   i.e. after the run had finally earned the right to write.
3. **A gate that measured the wrong thing.** Asked to check withdrawn
   deflection, I computed `setpoint − read_meter()[1]` and halted outside a
   range I had invented that evening. That reading is the *live* deflection: the
   free level only when the tip is withdrawn, and equal to the setpoint whenever
   the tip is engaged. It returned ~0 by construction and aborted a run whose
   only sin was starting with the tip engaged. → `PITFALLS` 19.10.

### 2.2 The readout collapse, and the fix that worked

Three launches died at the measurability gate with baseline floors of 0.589 and
0.395 and director flip rates of 58 % and 44 %. The driver's advice was "this
area cannot support the measurement — move". **It was wrong, and so was the
first explanation I reached for.**

Scoring every frame of the day with one piece of code showed |A| at one area
running **46, 73, 49, 40, 21, 21 pm** — the two 21 pm frames being the last two
*in time*, while a different area over the same interval held 34–71. The
degradation tracked the clock, not the position.

Mechanism: the contact resonance drifts over 5–10 minutes and the DART loop
loses it. `tune_here` re-tunes before every screening frame, so those held
79–110 pm all afternoon; the three-baseline block used bare `frame()` calls and
never re-tuned — and that block is the one every gate reads.

**Fix: re-tune before each baseline.** Result, on the same film:

| | before | after |
|---|---|---|
| \|A\| | 21 pm | **93–115 pm**, stable over 40 min |
| r12 | 0.67 | **0.95–0.97** |
| frequency tracking | 729 ± 46 kHz | 658 ± 0.7 kHz |
| baseline floor | 0.589 | **0.069** — best in the campaign |
| director flips | 58 % | **10 %** |

The internal control is the clincher: within a single triplet, the pair of
healthy frames gave **6 %** flips while the pair of collapsed frames gave 44 %.
Same area, same minute, same film. → `FINDINGS` M8 (corrected).

### 2.3 The measurement that was wrong by exactly two

This is the one that cost the night, and it was mine.

The driver holds two frame sizes: `FRAME = 10.0`, the size of the frame that
gets *scored*, and 5 µm for *screening*, because you asked for small frames. The
screening block computed the pixel size from `FRAME` and applied it to a 5 µm
frame:

```python
PX_NM = FRAME / PX * 1000.0     # 39.06 nm/px ... applied to a 19.53 nm/px frame
```

**Every screened Λ was exactly 2× the true period.** Verified directly:

```
PZTO_LDART_0086.ibw - ScanSize 5.0 um, 256 px
  correct  19.53 nm/px  ->  L = 245 / 301 / 354 nm   (median 301)
  driver   39.06 nm/px  ->  L = 548 / 548 / 755 nm   (median 548)
```

So the sixteen candidates that read 388-755 nm were really **194-378 nm — every
one of them inside the buildable window.** The region was never too coarse. The
recommendation in the first draft of this document, "move the coarse stage", was
false, and so was the geometry row of the table in §2.

**Why none of the four protocol checks caught it.** The static audit, the
dict-key parity check, the verdict-branch harness and the offline simulation all
verify that the code does what it says. This was correct code computing the
wrong quantity — no exception, no implausible number (548 nm is a perfectly
reasonable lamellar period, just not this film's), and the simulation reproduced
it faithfully because that is a simulation's job.

Worse, it was **self-consistent**. Sixteen candidates in a row agreed the film
was coarse, and their agreement felt like evidence. It was not: a constant-factor
error moves the whole distribution and leaves its shape untouched, so unanimity
among points sharing one code path is one measurement repeated, not sixteen
measurements corroborating.

**How it surfaced.** Not from re-reading the driver. `survey_lambda.py`, written
as a separate tool for a different job, computed its pixel size from its own
frame size because that was the only size it had. Its first two points read 301
and 245 nm where the driver had been reading 548 and 490 — two tools disagreeing
by a suspiciously round factor.

**Fixed** in all three drivers by taking the scale from each frame's own header,
`ScanSize / S.shape[0]`, plus a printed warning when a screening frame is not the
expected size. Recorded as `PITFALLS` 19.11; `FINDINGS` M9's extension is
corrected in place.

The rule worth carrying: **a scale factor must be derived from the data it is
applied to, not from a constant that is usually the same.** The header travels
with the array; a module constant does not.

### 2.4 The geometry itself, which is still true

The window arithmetic was never in question — it is algebra on quantities the
screening loop already has. A panel, its halo, and enough untouched film for the
C45 leave-one-out null all scale with Λ; the frame does not. At 10 µm rotated:

```
    148 nm <= L <= ~420 nm   one panel
    148 nm <= L <= ~396 nm   two panels (the within-frame pair)
```

**13 control tiles at Λ 420, 4 at 440, 0 at 460** — a cliff, not a slope, because
the tile grid is discrete. At the true Λ ≈ 245-301 nm this film sits comfortably
inside, with room for the two-panel layout.

---

## 3. What I did not do, and why

- **Did not exceed 10 µm.** You set the ceiling twice and I treated it as
  standing, not as a default to optimise away. (I had argued 12 µm "would admit
  most of this region"; at the true Λ that argument was moot — 10 µm was always
  enough.)
- **Did not write on 4 control tiles.** A leave-one-out threshold from four
  points cannot carry a conclusion; that is a weak experiment dressed as a
  result.
- **Did not move the coarse stage.** Physical, and yours — and as it turns out,
  entirely unnecessary. §2.3.
- **Did not relax the modulation floor** after you declined it, even though the
  campaign's own record shows it does not predict readability (IT7 failed at the
  *highest* modulation ever recorded, 0.217; tonight's best floor came from an
  area at 0.180).

---

## 4. What is ready to run

Three drivers, each validated on all four protocol checks — static audit,
splat-aware dict-key parity, offline simulation against real frames, and **every
verdict branch exercised** on the real verdict source:

| driver | task | design |
|---|---|---|
| `run_it12_pathway.py` | pathway (C54 / Q31) | **two panels in one frame**, one per sense, matched start (single-panel fallback via an argument) |
| `run_it13_leftovers.py` | leftovers | ISO vs denser-along-line, σ matched to machine precision |
| `run_it14_mindose.py` | minimum dose | 0.25 and 0.50 σ_c, both below C47's lowest working dose |

Shared machinery new this session: 5 µm screening (2.1 min/frame), per-area scan
rotation, per-frame re-tuned baselines, a screening-time feasibility gate that
rejects an unusable area for one frame instead of four, a pre-write control-tile
gate, and a deflection report that classifies engaged-vs-withdrawn instead of
guessing.

---

## 5. What is running now

The stage does **not** need to move. With Λ ≈ 245-301 nm the two-panel
within-frame design fits again — 2×2, four slots, ~12 control tiles — so that is
what is running:

```bash
python run_it12_pathway.py
```

Two panels in one frame, one per rotation sense, both starting from the same
triad member. Four settled slots make the shared start a **pigeonhole certainty**
(three triad members, four slots), which is C54's comparison with its confound
removed, and the comparison is *within* one frame, so C42's drift cancellation
applies. The one-panel design stays available for genuinely coarse film:

```bash
python run_it12_pathway.py +1
```

Then `run_it13_leftovers.py` (ISO vs denser-along-line) and
`run_it14_mindose.py` (0.25 and 0.50 sigma_c). Both carry the same pixel-size fix
and both get it verified in simulation before they launch.

`survey_lambda.py` is left in the project as a reusable tool: it maps Λ,
modulation and streak across the scanner from 5 µm frames, measurement only, and
appends to its CSV after every point so an interruption keeps what it measured.
Two points before it was stopped, both buildable — (0,0) Λ 301 nm mod 0.193, and
(−9,0) Λ 245 nm mod 0.259.

---

## 6. Findings recorded

`FINDINGS.md` M1–M10 (M9 corrected), `PITFALLS.md` 19.1–19.11. The ones that change how the
next session should work:

- **M8** — an area gate said "bad film"; it was a collapsed lateral signal, and
  a re-tune fixed it. *Corrected in place*: the contact-force explanation I first
  gave was wrong for the reason in `PITFALLS` 19.10. What survives is the |A|
  time series and the re-tune, which never depended on it.
- **M9** — the buildable window, both bounds, with the tile-count cliff. Its
  *derivation* stands; its supporting measurements were the 2×-wrong ones and are
  corrected in place. The window was right; the ruler was wrong.
- **`PITFALLS` 19.11** — the pixel-size bug in full, and the general lesson: every
  other check in that section verifies that the code does what it says, and
  **none of them verifies that what it says is what was meant.** Units errors
  need different defences — derive scales from data, cross-check one quantity by
  two independent routes, and treat a round ratio between two estimates (2.00,
  1000, 57.3) as a units bug until proven otherwise.
- **M10** — rotating the scan by +φ moves measured angles by **+φ**. I assumed
  the opposite; `align_triad`'s 25° tolerance caught a 26° error. One degree
  more slack and every command would have been 68° from where it was meant to
  be, with nothing in the output looking wrong.
- **M5** — the area gate's own input is not reproducible: the same position read
  modulation 0.208 / 0.168 / 0.194 across 35 minutes, straddling the 0.18 floor.
- **M2** — relocation after a stage excursion is good to < 25 nm, so
  `HANDOFF_1` §5's "the stage does not return" is *not* a lateral-position
  effect. The practice (consecutive baselines) is right; the stated reason is
  not, and the drivers still print the wrong one.
- **`PITFALLS` 19.9** — how to exercise a verdict properly: slice the block,
  `compile`, `exec` against a namespace you build. It found a real `KeyError`
  and two branches that would have reported confident nonsense from n = 1.

`probe_health.py` is installed as a reusable tool: run it before accepting any
area-gate rejection.
