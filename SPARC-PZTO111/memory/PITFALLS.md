# PITFALLS — measurement and design discipline for the PZTO trajectory-litho campaign

> ## THE GOAL
>
> **Find the switching rules of the in-plane superdomain directions under
> point-pulse-lattice writing, and reach full control of the IP superdomains for
> arbitrary patterns.**
>
> Read this file and `FINDINGS.md` at the start of any session, **after every
> context compaction**, and before proposing any experiment. §8 is the safety
> envelope and is not negotiable. §9 is the autonomous-loop protocol.

**Why this file exists.** Roughly half the instrument time in this campaign has
been spent on experiments that could not answer their own question, or on
answers that were wrong for a reason visible in advance. Each entry below cost
something real. The point is not self-criticism; it is that these are the
specific failure modes of *this* measurement, and they recur.

**The single most expensive class of error** was scoring the wrong quantity —
see §6. It voided one section for a day and withdrew another's headline.

## 0. The rules that would have prevented most of it

1. **Score the direction, not the amplitude.** The population vector over the
   pinned triad is a ratio within one frame; Δ(angular power) is a difference
   between two and carries their gain, tune and streak difference. §6
2. **Measure the thing your hypothesis is about.** An in-plane claim gated on an
   out-of-plane metric is not a test of it. §1.1
3. **A control must be untouched, and it must be untouched *now*.** Controls rot
   as the experiment fills the frame. §1.2, §2.6
4. **Never hard-code what you can measure.** Λ, the triad, the data folder, the
   panel size, the readout window: all of them have been wrong as constants. §1.5, §2.5, §7.6
5. **Give every panel the same task.** A comparison between a rotation and a
   sharpening is not a comparison. §7.1
6. **Pre-register the prediction.** Write what each outcome would mean before the
   write, as an expression in what the arm changes. §7.8
7. **Distinguish "unreadable" from "unsuccessful"** before blaming the tip. §7.9

## 1. Measuring the wrong thing

### 1.1 Wrong channel · 14 Aug · cost: nearly discarded the campaign's best result
Gated R4 on `write_check`, which scores the **out-of-plane up-fraction** (a
polarity measure), when the hypothesis was **in-plane alignment**. The gate
returned +0.02 and aborted while the panel's in-plane texture had swung to the
commanded angle (power at 2°: 0.099 → 0.760). The user caught it by looking at
the images.

> **Rule.** Before writing a pass/fail criterion, state in one sentence what
> physical quantity the hypothesis predicts will change, and confirm the metric
> is that quantity. VDART = out-of-plane. LDART = in-plane. They are not
> interchangeable and they disagree.

### 1.2 Self-referential controls · 14 Aug · cost: false abort on a +0.779 success
`[R4.2b]`'s three "controls" were fixed boxes chosen when only one panel had been
written. After file B all three lay inside treated panels — and `diag`
(5.6–7.0, 5.6–7.0) **was panel (2,2), the panel under test**. The panel was
compared against itself, so a real alignment read as "no alignment above
controls".

> **Rule.** Controls are a function of what has been treated *so far*. Recompute
> them at every stage. When the treatment covers the frame there are no spatial
> controls left — use a **temporal floor**: two frames with nothing done between
> them (`align_floor`). Cross-condition discrimination (different commands giving
> different outcomes in the same frame) is stronger than any external control.

### 1.3 Spatial confound from asymmetric placement · 14 Aug
The R4 gate panel sat in a frame corner, so "near sites" and "far field" sampled
different parts of the image. Raw near−far read +0.0636; after removing a
frame-wide trend, +0.0209. Two thirds was drift.

> **Rule.** Detrend before comparing regions that are not interleaved
> (`write_check(detrend_um=2.0)`), and require **radial structure**, not just a
> near−far difference. The write that worked fell monotonically +0.695 → +0.227.

### 1.4 Comparing across a changed setpoint · 14 Aug
`LDART_0028` (0.50 V) and `LDART_0029` (0.60 V) are the same physical state. Peak
direction differs by **>50°** in two of nine panels. On a setpoint-matched pair
the same readout repeats to a **median 0.0°** at every region size from 1.4 to
5 µm.

> **Rule.** The readout is reliable *within* a fixed setpoint and not across one.
> Never pair frames taken at different setpoints. If the setpoint changes, take a
> new baseline. Same for probe, tune centre, and pixel size.

### 1.5 Hard-coded material constants · 14 Aug
`FAM = (30, 90, 150)` was measured in one area and hard-coded. The film's triad is
**{2, 62, 122}** — a rigid fit over six frames and two areas gives φ₀ = 1.5–4.0°,
spread 2.5°. With ±12.5° wedges centred on the wrong angles, every true director
fell outside its wedge and `w` integrated tails.

> **Rule.** Measure per-area, and fit *physically constrained* models. The three
> directors are 60° apart by crystallography, so there is **one** free parameter
> (`fit_triad`), not three (`measure_triad` peak-picking, which fails on virgin
> material where the weakest family is a shoulder).

### 1.6 Overstating what a wrong constant broke · 14 Aug
Claimed the wrong `FAM` corrupted `aniso` and `peak`. It did not — both come from
the angular histogram independently of `FAM`. Only `w`, per-family `Λ`, and
`change_map`'s `switched` were affected.

> **Rule.** When retracting, check which quantities actually depend on the broken
> input. Over-retracting destroys good results and costs credibility.

### 1.7 Channel sign cancellation · 13 Aug
The two DART channels had r₁₂ = −0.87 to −0.93. Naive averaging cancelled real
structure and four frames looked like noise. Flipping one channel first: |S| 3.5
→ 19.2 pm, ξ 1 → 3 px.

> **Rule.** `signed()` returns `r12`. If it is negative and you did not flip, the
> result is meaningless. Check it on every frame.

### 1.8 Claiming a tiebreaker without checking it resolves · 14 Aug
Proposed the height channel as a bias-free arbiter between LDART and VDART, then
found neither height nor PFM shows a distinct Λ = 388 nm peak — both spectra are
dominated by ~1 µm structure.

> **Rule.** Before offering a measurement as decisive, verify it resolves the
> feature at all.

### 1.9 Other measurement errors worth not repeating
- Reported **coverage over the whole frame** instead of the scored region (6–13 %
  was really 48–91 %).
- **Registration on raw height** locked onto noise → spurious 449–625 nm shifts.
  Gaussian-filter first.
- **Cross-tip comparison with a fixed-kernel structure tensor** (S₂ 0.614 vs
  0.16) — withdrawn; a sharper tip reports different order for identical physics.
  Kernels specified in **nm** are comparable across pixel sizes; those in **px**
  are not.
- **Stage moved between baseline and write** — height correlation +0.04 vs +0.90.
  Always fingerprint the area.
- **Dict key collisions** across dates (`260802` and `260806` both hold
  `LDART_0000`).
- Called an area "already poled" when it was **uniformly single-orbit**; the
  "3.5 % up-orbit" was 252 clusters of median 1 px, a φ₀-fit tail.
- Read a figure from **text-only PDF extraction** and got it backwards; the user
  corrected twice before the figure was actually rendered.

---

## 2. Designing the experiment wrong

### 2.1 Dosing below a threshold already in `FINDINGS.md` · twice
`[2.3]` used 8 V·s and R4 used 10 V·s against a recorded ~40 V·s threshold (C21).
The second time, the mistake had **already been written up** as a lesson from the
first.

> **Rule.** Charge per pulse = |V| × dwell, and dwell = `PULSE_N` × step / speed.
> `PULSE_N = 25` at 0.02 µm / 0.5 µm·s⁻¹ is **1.0 s**. Compute it, print it, and
> compare it to `FINDINGS.md` before running. For dense lattices also compute
> **areal** dose — overlapping halos deliver far more per µm² than per-pulse
> charge suggests.

### 2.2 Treating a threshold as a material property · 14 Aug
The ~40 V·s threshold was measured with probe #2 at that day's litho setpoint. It
is not transferable across probes or writing setpoints.

> **Rule.** Thresholds are per-configuration. Re-measure after any probe or
> setpoint change.

### 2.3 No positive control before a nine-condition experiment · 14 Aug
`FINDINGS.md` §5 had said for days that no positive control existed and
`[PROBE.1]` had never been run. R4 was designed and executed anyway; ~70 min of
instrument time that could not answer its own question.

> **Rule.** Read §5 ("what we have not achieved") before designing. If it names a
> missing control that the new design depends on, run that control first.

### 2.4 A treatment that fills the frame cannot audit itself · 14 Aug
R4's 576 pulses left no area beyond 1.3 µm of a site, so the halo test returned
`nan`.

> **Rule.** Always leave untreated area — either a margin, or by staging (write
> one condition, verify, then commit). Staging also caps the loss: R4's abort cost
> 6 min instead of 46.

### 2.5 Geometry hard-coded from a dry run · 14 Aug
`N_SIDE = 6` and `PANEL_PITCH = 2.5` came from a dry run at Λ = 340 nm. The area
measured 388 nm, spacing went 170 → 194 nm, and halos overlapped by 85 nm.

> **Rule.** Derive geometry from the **measured** Λ and triad at runtime. Never
> carry numbers from a dry run into a cell. A square lattice rotated by θ has its
> bounding box inflated by |cos θ| + |sin θ| — up to 1.378× — so size for the
> worst angle in the triad.

### 2.6 Controls inside the halo · 9–13 Aug
The first `[2.1]` put both control strips inside the 625 nm halo of the edge
pulses. A 13 Aug edge strip read Λ = 95–179 nm and "changed" more than the
treated core.

> **Rule.** Controls must sit outside the **halo**, not merely outside the
> lattice footprint, and ≥0.25 µm from the frame edge.

### 2.7 Charge balance that balances the wrong thing · 9–14 Aug
- Odd cycle count leaked +0.063 V DC (H = 3.0 µm at 20 nm pitch → 75 cycles).
- A checkerboard balanced pulse *count* but not *charge* (88 V·pt out).
- Alternating signs cannot cancel **unequal dwells**.

> **Rule.** Assert on `mean(V)` of the array actually written, per panel and per
> line where possible. Even counts; exhaustive sign search when dwells differ.

### 2.8 Building a different experiment than the one specified · 14 Aug
Asked for "denser grid, forward and backward on the same line with opposite
polarity", I built 6 lines at Λ/2 each drawn once with sign alternating *between*
lines — a static ± stripe pattern, i.e. a second copy of the pulse lattice.

> **Rule.** Restate the requested scheme in the cell's comment before coding it,
> and check the code matches the restatement.

### 2.9 Preparing the state you least want · 14 Aug
Step 3 poled before seeding, on the argument that C9 showed an open gate did not
help. Poling turned out to *increase* order sharply (modulation 0.16 → 0.76,
confined to the poled square), producing a locked state to fight.

> **Rule.** Check what the preparation step does to the state variable before
> assuming it is neutral.

---

## 3. Diagnosing failures wrong

### 3.1 Two confident wrong root causes in a row · 14 Aug
Zero writing was attributed first to a **contaminated apex**, then to the **litho
deflection setpoint**. The real cause was the Igor litho panel latching: it still
believed the previous scan was running and silently refused every `TL_RunPy`.

The evidence to narrow it was already on disk. The Step 3 **poling raster
worked** (modulation +0.596 inside the poled square, controls −0.02), which
brackets the failure to *after* ~15:08. Instead the probe swap was blamed because
it was the salient recent change.

> **Rule.** Before proposing a cause, find the **most recent operation that
> demonstrably worked** and bracket the failure window. Prefer causes that explain
> the timing, not just the symptom. Grade the observation and the mechanism
> separately — "the tip is not writing" was A; "because the apex is contaminated"
> was C and wrong.

### 3.2 Validating the file instead of the instrument · 14 Aug
`run_traj` printed 25802 pts, `mean V +0.00000`, correct extent — all true, all
irrelevant, because no bias reached the tip.

> **Rule.** File validation is not execution validation. Require a **physical
> readback** after any write whose success is not otherwise observable. `run_traj`
> now issues `exp.execute('Stop')` after every litho run — the missing Stop was
> the whole bug.

### 3.3 Abort logic more confident than the measurement · 14 Aug, twice
Both aborts fired on successes (§1.1, §1.2).

> **Rule.** A gate needs a **specificity argument**: what would make it fire when
> the experiment worked? If you cannot answer, print and continue rather than
> raise.

---

## 4. Tooling

### 4.1 Never send commands to a live instrument from a test script
A verification script stubbed `ae` in a namespace dict, but the notebook's
toolkit cell runs its own `import aespm as ae`, replacing the stub. Six
`GetTune()` calls went to the real Igor. (Read-only, no harm, but only by luck.)

> **Rule.** Stub in `sys.modules` **before** any exec, and assert the stub
> survived: `assert ns['ae'] is fake`. Make blocked methods raise, not pass.

### 4.2 Heredoc backslash collapse · repeatedly
`\n` inside `<<'PY'` heredocs became real newlines, producing unterminated string
literals. Also hit by a non-raw `'''...'''` in a patch file.

> **Rule.** Write patches with the **Write tool** to a `.py` file and run that
> file. Use `r'''...'''` for any code containing `\n`. To emit a literal
> backslash-n, build it as `chr(92) + 'n'`.

### 4.3 Slice indices out of order duplicated 370 lines
`s[:lo] + NEW + s[hi:]` with `hi < lo` re-appended `tune_quality`,
`find_resonance`, `probe_fingerprint`, `contact_check`, `report`, and the **old**
`measure_triad`/`set_triad`. Because duplicates came last, the old definitions
won and the fix appeared not to work.

> **Rule.** After every patch, assert each function is defined **exactly once**
> (`src.count('def name') == 1`) and that the surviving body contains a marker
> from the new version.

### 4.4 The file is not the kernel
Editing a cell does nothing until it is re-run. Symptoms seen: `TypeError:
unexpected keyword argument 'start_sign'`, and a missing `litho stopped` line
because `[WRAPPERS]` was stale.

> **Rule.** Cells now check their dependencies' signatures up front and name the
> cell to re-run. After patching `[TOOLKIT]`/`[WRAPPERS]`, say explicitly which
> cells must be re-run before the next instrument cell.

### 4.5 Assuming an API does what its name suggests
`tune_probe(readonly=True)` does **not** sweep — it returns the last stored tune
curve and ignores `center`/`width`. A widening loop built on it was a no-op.

> **Rule.** Verify API behaviour against observed output before building logic on
> it. Six readonly calls at different centres returning identical ranges was the
> tell.

### 4.6 Smaller ones
- Octal-escape path mangling: `"...Data\260802"` renders as `Data°802`. Use raw
  strings or forward slashes.
- f-strings with multi-line expressions inside braces are invalid before 3.12.
- Unicode: `FINDINGS.md` uses en/em dashes; ASCII match strings fail silently.
- **Dead code in a guard** (checking an empty set) looks like a check and is not.

---

## 5. Pre-flight checklists

### Before designing a measurement
- [ ] Read `FINDINGS.md` §4 (numbers) and §5 (what is missing).
- [ ] Name the observable the hypothesis predicts. Confirm the metric measures it.
- [ ] Is there a positive control on record for this instrument state?
- [ ] Compute dose (per pulse **and** per µm²) and compare to `FINDINGS.md`.

### Before running a cell that writes
- [ ] Geometry derived from **measured** Λ and triad, not constants.
- [ ] `mean(V)` asserted per panel/line; `|V| ≤ 10 V`; inside the frame.
- [ ] Untreated area remains for a far field, or the run is staged.
- [ ] Controls are untreated **as of this stage**.
- [ ] Setpoint, probe and tune unchanged since the baseline.
- [ ] `[TOOLKIT]`/`[WRAPPERS]` re-run if patched.

### Before claiming a result
- [ ] Same channel, same setpoint, same pixel size on both sides of the pair?
- [ ] Temporal floor computed from a do-nothing pair?
- [ ] Does the effect show the expected **spatial structure**, not just a mean
      difference?
- [ ] Do different commands give different outcomes in the same frame?
- [ ] State which quantities the conclusion does **not** cover.

---

## 6. The biggest one: measuring amplitude instead of direction · 20–21 Aug

**Cost: Section 14 declared void for a day, Section 15's headline published then
withdrawn, and two statements to the operator that had to be retracted.**

### 6.1 What went wrong

Every section from 12 to 15 was scored on **Δ(angular power at the commanded
director)** — the change in a spectral weight between the before-frame and the
after-frame. That is *a difference between two frames*, so it carries every
difference in gain, tune, setpoint and scan artefact between them.

Section 14's control band "fell" by −0.110 in every tile and the floor came out
at 0.199, larger than any panel signal. I reported the section as **void**.

It was not void. One of its two baselines, `LDART_0035`, was **streaky**, and a
streaky frame reads excess power near 0° — which happened to be Section 14's
commanded direction. Re-scored on **direction**, the same data give **4/4
equivalent 60° rotations at 70, 80, 90 and 100 % density**, and they answer the
question the section was built to ask.

### 6.2 The rule

> **Score the DIRECTION of the superdomains, not the change in angular power.**
>
> The population vector over the pinned triad, normalised to sum to 1, is a
> ratio **within one frame**. `dir_power` already divides by the total power in
> the q window; normalising the three members removes what is left. An isotropic
> noise floor compresses all three toward 1/3 — attenuating contrast but never
> changing which director leads.

Report, in this order:

1. **dominant director** before and after — argmax of the population vector;
2. **lead** = w(commanded) − max(w(other two)), signed, within-frame;
3. **final w(commanded)** — how pure the aligned state is;
4. Δ(angular power) **last and only for continuity**, never as the basis of a
   verdict.

Use `dir_state()`. Do not use `align_check` or bare `dir_power` deltas for a
verdict.

### 6.3 Δ(lead) versus final w(commanded)

Section 16 showed these disagree. On **Δ(lead)** the Λ/4 and Λ/2 conditions
overlapped within their own scatter; on **final w(cmd)** they separated cleanly
with a +0.232 gap. Δ(lead) is a *change*, so it inherits the starting state;
w(cmd) is the *final* state, which is both more robust and the thing we actually
want. **Prefer final w(commanded) for cross-condition comparisons.**

### 6.4 Streaks look like superdomains at 0° · 21 Aug

Scan lines run along **x**, so line-to-line offsets put their FFT power on the
q_y axis — which `dir_power` maps to a stripe director of **0°**. A streaky
frame therefore reads excess population at 0° with no domains involved.

Measured on untouched film in the Section 14 area:

| frame | \|S\| | streak index | control-band w(0/60/120) |
|---|---|---|---|
| 0033 scout | 28.6 | 0.060 | 0.462 / 0.278 / 0.260 |
| 0034 baseline a | 30.5 | 0.069 | **0.407** / 0.326 / 0.267 |
| **0035 baseline b** | **12.9** | **0.115** | **0.569** / 0.242 / 0.189 |
| 0036 after | 32.3 | 0.077 | **0.398** / 0.324 / 0.278 |

- Healthy on this film is **0.009–0.077**; **0.115 is a bad frame.**
- Run `streak_index()` on untouched film for every baseline, and be especially
  suspicious of any command near **0°**.
- **Q14 is still open:** C23, C29 and C30 all used commands near 0° in some
  panels and none of their frames were ever screened. Those conclusions are
  load-bearing and unscreened.

### 6.5 Take THREE baselines, not two

With two frames there is no majority when they disagree. Section 14's two
baselines disagreed about the starting dominant director in **all four** panels,
so no rotation could be claimed either way. Section 16 RUN 1 had a bad frame
among its pre-write set (`LDART_0049`: \|S\| 15.1, r12 +0.82, offset 27.6 kHz) and
`pick_ref` routed around it correctly *because there was a third*.

`pick_ref` applies the **r12 gate first**, then ranks by tracked coverage over
the regions that will actually be used. An early version ranked coverage first
and chose a frame at **r12 = −0.81** over one at +0.93.

### 6.6 Score against the reference frame, not the last baseline

`[14.2]` took its triad and layout from `pick_ref`'s choice but computed every
delta against `f14_b2` — whichever frame happened to be taken last. Those
differed, and the bad one was used. **The frame used for the layout must be the
frame used for the delta.**

---

## 7. More incidents, 20–21 Aug

### 7.1 Unequal tasks · Section 15 · cost: the section's whole point

Section 15 compared Λ/2 against Λ/4 and the Λ/4 panel reached w(cmd) = 0.851
— the purest state of the campaign. I reported "over-driving nearly triples the
effect". Then, on direction:

| panel | dominant before | commanded | task |
|---|---|---|---|
| REF Λ/2 | 64° | 124° | a genuine **60° rotation** |
| OVER Λ/4 | **124°** | 124° | **already on target — a sharpening** |

The command was chosen once per frame from the **frame-wide** virgin peak. Local
texture varies, and the Λ/4 position already favoured 124°. One panel had to turn
the superdomains and the other only had to sharpen them.

> **Choose the commanded director PER PANEL, 60° from that panel's own local
> dominant director.** `command_for()` does this; `min_lead` refuses a panel
> whose dominant director is too close to call. Assert that the command is 60°
> from the local dominant.

### 7.2 A rotated panel is smaller than its bounding box · 21 Aug

The written region is a square of side `L = (n−1)·spacing` **rotated** by the
command. An axis-aligned readout window of side `W` has its worst corner at
`(W/2)·ANG` along the lattice axes, so it fits only if

```
W · ANG  ≤  L          ANG = |cos(cmd)| + |sin(cmd)|
```

`solve_grid` had required `L·ANG ≥ W`, i.e. `L ≥ W/ANG` — **looser by ANG², up
to 1.93× at 45°.** Not conservative: insufficient. Section 15's window overhung
its written lattice by 0.05 µm (REF) and 0.15 µm (OVER); both are far inside
r_eff = 625 nm so its numbers stand, but one Section 16 panel failed the correct
rule by 0.01 µm.

### 7.3 Anything fixed before the commands are known must assume the worst angle

Positions and halo clearances are chosen before any command exists, so they must
survive the widest command (ANG 1.388 at 124° against 1.067 at 4°). **Panel size
must not** — it is fixed afterwards. Sizing `N_SIDE` on the worst angle when
every panel took the cheapest command cost Section 17 **1200 pulses and 32 min
instead of 768 and 20 min**. Re-solve `N_SIDE` from the commands in use; `n` does
not enter σ, so it cannot disturb a factorial.

### 7.4 The commanded angle sets the cost

Pulses go as `n²` and `n` as `W·ANG/spacing`, so at Λ = 280 nm a Λ/4 panel is
**576** pulses commanded to 4° and **1024** commanded to 64°. C30 says the two
rotation senses are equivalent, so choosing the cheaper one costs nothing — but
choose it **explicitly** and print the alternative.

### 7.5 A 64-px probe frame is fast and useless · 21 Aug

`tune_and_verify` took a 64 px / 2 Hz frame over a 10 µm field to check the tune.
Tip lateral speed is `size × rate × 2`:

| | tip speed |
|---|---|
| 64 px, 2 Hz, 10 µm | **40 µm/s** |
| 256 px, 1 Hz, 10 µm | 20 µm/s |

Double the imaging speed, in contact, for a diagnostic. **And it did not work:**
the probe frames read 10–14 kHz offset and passed their own 12 kHz threshold in
all three sections, while the 256 px frames on the same tune read **9–26 kHz**:

```
S13  probe 13.1, 10.1  ->  full 18.1, 18.5, 22.3, 12.4
S14  probe 13.6, 12.0  ->  full 19.3, 15.9, 26.3, 12.3
S15  probe 13.1, 11.7  ->  full 18.7, 13.9, 20.2,  9.1
```

A 64 px frame at 2 Hz is a different dynamical condition, so its tracked
frequency does not transfer. Use **`tune_here()`**, which verifies on a frame at
the real px and rate and **returns it for use as baseline 1** — no extra scan.

Its gate is **line tracking**, not the offset. A DART loop sitting 20 kHz off the
nominal drive with 100 % of lines tracked and healthy \|S\| has found the peak;
that is the normal state on this film.

### 7.6 Never hard-code the data folder · 21 Aug

The setup cell named `...\260813\PZTO`. Re-running it after a kernel restart
pointed the session at a folder that **does not exist**; `frame()` shells out to
`dir` through `check_file_number`, `dir` exits 1 on a missing path, and the run
died on its first frame **after the tune** with the real error buried under an
IPython traceback-formatting crash (`AssertionError: Pieces mismatches`).

Resolve the folder from the **most recently written .ibw**, not the newest folder
*name* — this session ran past midnight and Asylum kept writing into `260820`,
so a name-based answer would have been wrong. `check_folder()` verifies it in
about a second and raises if a sibling date folder has fresher data.

### 7.7 Amplitude comparisons across modes are meaningless

I flagged "\|A\| = 23.9 pm against a campaign-healthy 50–70 pm" as probe
degradation. The 23.9 was a **VDART** number; LDART 256-px frames have run
15–33 pm all session. There was no decline: over 38 frames and ~4000 pulses,
\|A\| went 25.7 → 26.0 pm, \|S\| 32.6 → 34.0, r12 0.89 → 0.94.

Also: **64-px frames read systematically higher \|A\|** (34–58 pm) than 256-px
frames (16–33 pm) — a bandwidth effect, not probe health. Compare like with like:
same mode, same px, same rate.

### 7.8 Derive a prediction, do not assert it

I predicted P50 ≈ 0.95 × FULL because dropping columns preserves the sign period.
A structure-factor amplitude scales with the **number of sources**, so P50 is
0.5× like every other half — the "decisive" P50-vs-R50 comparison was not a
discriminator between T1 and a correctly formulated T2 at all.

**Write the prediction as an expression in the quantities the arm changes**, not
as a number per arm. The experiment was still worth running: it found the
threshold.

### 7.9 Distinguish "unreadable" from "unsuccessful"

A verdict that says "nothing turned, check the write gate" when the real problem
is the frame pair points at the tip instead of the measurement. Compute the
**untouched-tile director-flip rate** — measured entirely on virgin film, so it
grades the readout and nothing else. Sections 12–16 ran **0/6 to 3/12**. Above
about a quarter, the frame pair cannot support a direction claim and nothing
below it should be read.

### 7.10 The order of the site list sets the write time

`lattice_panel` selected sites by sign, returning all `+` then all `−`, so the
tip crossed the panel between every pair of pulses: an 870-site ladder came to
**62,054** trajectory points (**41 min**) where a serpentine path needs 30,459
(**20 min**). Sort serpentine *after* selection — the site set, signs and charge
balance are untouched. Expect a travel overhead of **1.25–1.40×** dwell; warn
above 2×.

**Writing time is not pulses × dwell.** Multiply the pulse count by ~1.35.

---

## 8. THE SAFETY ENVELOPE — hard limits, never negotiable

These protect the sample, the probe and the instrument. **An autonomous loop must
check every one of them before each write, and abort rather than proceed on any
failure.** None of them may be relaxed to make an experiment fit.

### 8.1 Instrument limits

| # | limit | value | enforced by |
|---|---|---|---|
| S1 | tip bias ceiling | **±10 V** | `V_MAX`; `run_traj` refuses any file exceeding it |
| S2 | scanner range | **−50 to +50 µm** in x and y; `\|offset\| + size ≤ 50` | `scanner_ok()`, checked against the **largest** candidate frame |
| S3 | trajectory inside the frame | every point > 0.05 µm from the edge | asserted in every build cell |
| S4 | net DC per file | `\|mean V\| ≤ 0.01` | `run_traj` refuses; also asserted per panel to < 1e-9 |
| S5 | Igor litho latch | `exp.execute('Stop')` **after every** `run_traj` | `run_traj(stop_after=True)`; without it the next run is **silently refused** |

S5 is not cosmetic: it cost ~70 min of writing across the Step 3 seed and the
whole of R4 before it was found.

### 8.2 Sample and probe care

| # | limit | value | enforced by |
|---|---|---|---|
| S6 | no fast coarse frames | never 64 px over ≥ 8 µm (40 µm/s in contact) | `tune_here()` replaces the probe frame |
| S7 | write-time budget | `MAX_WRITE_MIN` per iteration | build cell raises |
| S8 | per-pulse charge | keep below **40 V·s** (C21) when collective behaviour is intended | build cell warns above half |
| S9 | footprint | never overlap a previously written area | `USED` table + guard, checked at the worst-case frame |
| S10 | probe health trend | \|A\|, \|S\|, r12 tracked per frame; stop on a sustained fall | `probe_fingerprint`, `contact_check` |
| S11 | out-of-plane re-poling | VDART orbit check after dense writes; campaign reference 21–36 % minority | `orbit_balance` |

### 8.3 Measurement validity — a write that cannot be read is wasted sample

| # | requirement | value |
|---|---|---|
| S12 | DART band | LDART 650 ± 200 kHz, VDART 350 ± 200 kHz |
| S13 | readout window | ≥ **24 px** AND ≥ **4Λ** |
| S14 | window inside the rotated panel | `W · ANG ≤ (n−1)·spacing` |
| S15 | margin | ≥ one spacing + 0.1 µm per side |
| S16 | texture present | triad modulation ≥ **0.10**, else there is nothing to rotate |
| S17 | three baselines | and `pick_ref` with the r12 gate first |
| S18 | streak screen | on untouched film; **> 0.10 is a bad frame** |
| S19 | tiled controls | never a single box; floor = max(\|control Δ\|, \|b1−b2\|) |
| S20 | flip-rate gate | untouched-tile director flips ≤ **25 %**, else unreadable |
| S21 | triad pinned | fit once per area, never re-fit within a section (φ₀ is mod 60°) |
| S22 | per-panel command | 60° from **that panel's** local dominant, asserted |

### 8.4 Loop-specific stops

| # | stop | rule |
|---|---|---|
| S23 | abort file | if `STOP` exists in the project directory, the loop halts before the next write |
| S24 | iteration cap | a hard maximum per session, and a cumulative write-time cap |
| S25 | two strikes | two consecutive unreadable iterations → **halt and ask**, do not keep writing |
| S26 | no silent repeats | never re-run a completed condition without recording why |
| S27 | pre-registration | every proposal names the hypothesis, the prediction, and what each outcome would mean, **written before the write** |
| S28 | area budget | track legal remaining positions; refuse when the legal box is exhausted |
| S29 | no instrument command outside an iteration | analysis scripts must stub `aespm` in `sys.modules` **before** any exec, and assert the stub survived (§4.1) |
| S30 | no detached launches | never `nohup ... &` / `Start-Process`; use a harness-tracked background task, else arm a `Monitor` in the same turn (§20.1) |
| S31 | no turn ends on a promise | before ending a turn, confirm a live re-invocation handle exists; if not, do free analysis instead (§20.3) |
| S32 | launch, then work | never idle waiting on a job whose result the next action does not need (§20.4) |

---

## 9. Autonomous-loop protocol

**Goal.** Find the switching rules of the in-plane superdomain directions under
point-pulse-lattice writing, and reach full control of the IP superdomains for
arbitrary patterns.

Each iteration is a closed cycle. State lives in `campaign_state.json` so the
loop survives a context compaction or a kernel restart.

```
 1 STATE      load campaign_state.json, FINDINGS.md, PITFALLS.md
 2 PROPOSE    pick the next hypothesis; write the prediction and the meaning
              of every outcome BEFORE anything is built            [S27]
 3 PREFLIGHT  run the automated pitfalls checklist over the proposal
 4 BUILD      solve the geometry from the MEASURED Lambda; all guards [S1-S22]
 5 EXECUTE    tune_here -> 3 baselines -> write -> after-frame -> VDART
 6 READ       direction first: dominant director, lead, final w(cmd)  [S6.2]
 7 REFINE     update theory parameters; append to FINDINGS.md
 8 LOG        append a markdown cell (motivation, prediction, result,
              what it changes) and the code cell to the notebook
 9 DECIDE     choose the next hypothesis; save state
```

**Rules for the loop itself**

- **Never skip step 2's pre-registration.** T2 died from an interpretation
  fitted after the fact.
- **Preflight is automated, not remembered.** The checklist in §5 is code.
- If step 6 reports **unreadable**, do not write again — retake baselines and
  re-score. The written panels are still there. Two strikes and halt. [S25]
- Every iteration records **what would refute the current theory**, not just
  what would support it.
- A negative result is a result. Log it with the same weight.
- **On compaction:** re-read this file and `FINDINGS.md` before proposing
  anything. The goal statement is at the top of §9.

---

## 10. Retrospective: IT1 and IT2, eight launches for one usable result

Written after IT2 finally produced C41. Eight launches, one write in IT1 and one
in IT2, and **six launches lost to my own faults**. The individual fixes are
recorded above; what matters here are the two patterns behind them, because each
recurred three times.

### 10.1 The tooling pattern: I discovered gaps by running the instrument

| # | fault | cost |
|---|---|---|
| 1 | `exp.check_files` missing — the loader never exec'd cell 25 | tune + halt |
| 2 | worst-angle sizing inflated the halo; the grid would not fit | 3 frames |
| 3 | `visualize_trajectory` missing — the loader never exec'd cell 8 | 4 frames, write file built but never sent |
| 4 | area gate too strict on criteria I had chosen badly | 3 tunes |
| 5 | `LAM_CONSIST_MAX` left dangling **by my own fix for #4** | 1 tune |
| 6 | `res` referenced before assignment **by my own fix for the metric** | nothing — the result survived |

Every one of these is statically detectable. The root cause is that
`load_toolkit(stub_instrument=False)` is the one path that cannot be dry-run, and
I repeatedly treated "it parses, and the stubbed path works" as sufficient.

**Rule.** Before every launch, run all three static checks:
1. AST scan for **called-but-undefined** names across every cell the loader execs;
2. dangling-global check on the driver script;
3. required-name assertion inside the loader, covering the whole write path.

And **simulate against real frames on disk** before launching. I did this once,
before IT1's third attempt, and it caught two real problems immediately. It was
not optional; I just treated it as optional.

**Rule.** After patching, re-run the audit. Faults 5 and 6 were introduced by
patches written to get the instrument moving again. A patch is not a fix until it
has been audited.

### 10.2 The analysis pattern: I blamed the material before the measurement

Three times I reached for a physical explanation when the cause was procedural:

| observation | my explanation | actual cause |
|---|---|---|
| VDART minority 46 → 36 → 33 → 19.5 % | progressive out-of-plane poling of the sample | withdrawn deflection drifted −0.8 → −0.6; restored, it read 38.4 % |
| control tiles flipping 31 %, floor 0.35 | the region is too weakly textured for the metric | frame sequencing — the stage does not return after an excursion |
| Λ = 280/388/261 across triad members | the three variants have different periods | `period()` is unreliable per member; it also fails to converge with block size |
| `read_meter` channel 2 reading −0.84, −0.44, +0.60 within one iteration | the withdrawn deflection is drifting badly, maybe mechanically | it reports the **live** deflection, which depends on tip state: −0.84 withdrawn, +0.600 engaged-on-setpoint. `DeflectionSetpointVolts` held at **0.600 across all 13 frames of IT2 and IT3**, nearly three hours. Nothing drifted |

Each of these was a hair's breadth from being written into `FINDINGS.md` as
physics. The poling one especially: it was monotonic across four areas and fitted
a plausible mechanism.

**Rule.** When a measurement misbehaves, exhaust the measurement before the
material. Four instances now, so treat it as the default hypothesis rather than
the fallback.

**Corollary for instrument readings:** before calling a number "drift", check
whether the number means the same thing at each reading. `read_meter` returns the
live deflection, so its value depends on whether the tip is engaged; the frame
header's `DeflectionSetpointVolts` is the parameter that would actually change if
the force were drifting, and it is recorded in every frame at no cost. Concretely: is the comparison between frames taken consecutively? Has
any instrument parameter moved? Is the estimator stable against its own window
size? Only then consider the sample.

### 10.3 Gating on proxies instead of the quantity of interest

The area gate rejected three good areas on Λ-consistency and a 0.20 modulation
cut, when what actually decides readability is the **floor** — which is directly
measurable from the baselines already being taken. Replacing two proxies with the
measured quantity fixed it immediately, and the same gate then found the real
problem (§10.2, row 2).

**Rule.** Gate on the quantity that decides the outcome, measured, not on
something believed to correlate with it.

### 10.4 When stuck, change the measurement, not the experiment

IT1 and IT2 both stalled on a floor carried across a before/after pair. Three
iterations of "find a quieter area" got nowhere. What worked was abandoning the
temporal comparison entirely for a **within-frame contrast** (C42) — available
from the start, and immune by construction to everything that had been going
wrong.

**Rule.** After two failures of the same kind, stop varying the experiment and
question the observable. Ask what could be measured that does not depend on the
thing that keeps breaking.

---

## 11. What building IT4 found in the machinery, before it ran

Section 10 ends with a rule I had written and not followed: *simulate against
real frames on disk before launching.* IT4 was the first iteration built that
way — the driver's own geometry, dose, build, tile and scoring code sliced out
of the file and exec'd offline against a real frame, rather than a
re-implementation of it. It found five defects, four of which had been live
through IT1–IT3.

### 11.1 A crash after the write loses the area record

IT2 wrote 512 pulses into (−14, 0) and then raised `UnboundLocalError` in the
verdict block, so `save_state` never ran. For two days afterwards:

- `used_areas` did not contain (−14, 0), so **S9 and `check_area_fresh` were
  both blind to a written area** and IT4 could have written on top of it;
- 19.6 min of writing was missing from the cumulative budget (S24);
- the iteration counter read 2 after three iterations;
- `completed` was empty, so **S26 could never fire**;
- the notebook had no IT2 cell at all, and IT3's cell was titled
  "ITERATION 2 — IT3_period_series `[IT2-doc]`".

**Rule.** State that records a *physical fact about the sample* is committed as
soon as the fact exists — the area and the write minutes are saved immediately
after `run_traj` returns, in their own `save_state`, never bundled with the
result. A save that must survive a later crash cannot sit after the code that
crashes.

**Rule.** Anything appended to `completed` is what makes S26 able to bite. An
envelope check that reads an empty list is not a check.

### 11.2 `preflight()` encodes S1–S29 and no driver ever called it

`grep -c preflight run_it1.py run_it2.py run_it3.py` → 0, 0, 0. The envelope
existed as code and was enforced only by whatever each driver happened to assert
inline. Those inline asserts do cover S1, S2, S8 and the write budget — but
S24, S25, S26 and S27 were checked by **nothing**.

The reason it was never called is in its own body:

```python
x, y = prop['offset']      # TypeError when the area is chosen at run time
q = abs(v) * p['dwell']    # TypeError when the dose is solved at run time
```

Every driver chooses the area and solves the dose at run time, so the function
was unusable by construction for the exact design it was written for. It now
**defers** those groups and says so, and the driver calls it twice: once before
any instrument command, once after the area and dose exist.

**Rule.** A guard that cannot run in the normal path is not a guard. When
writing one, check it against the way the caller actually works — and if it is
never called, that is a defect in the guard, not in the callers.

**Rule.** A deferred check must be *reported as deferred*. Silently skipping it
would let "0 failures" mean two different things.

### 11.3 The control tiles sat on a written panel

`ctrl_tiles(x0, x1, y0, y1, w)` tiles only in x, at the band's **centre** y. The
upper control band was built as `top = slots[0][1] + halo + 0.05` — the top edge
of the **first** row, not of the grid. With a 2×2 grid it therefore started
inside the second row and put its tiles at that row's centre height, straight
through a written panel.

Audited against IT3's own frames: **3 of its 14 tiles overlapped P8**. The
excesses moved by ≤ 0.022, the ordering and all three verdicts were unchanged —
so C41 stands — but that was luck. The tiles are now gridded across the whole
frame and every candidate touching a panel is dropped, which also *gained*
tiles (16 against 7) and put six of them inside the unwritten slot, at the same
height as the panels rather than hugging one edge.

**Rule.** A control region is defined by *what it is not near*. Compute it by
subtracting the written footprints, never by arithmetic on one row's coordinate.

### 11.4 Tiles read along one director, panels along another

The within-frame contrast scored the control tiles once, at
`panels[0]['cmd']`, and every panel's excess against that mean — while each
panel was scored along its own command. In IT3 all three panels happened to be
commanded to the same director, so it could not bite. The triad members are not
equally populated, so along a different director that is a real offset. The
expected-dominant index `ic` had the same flaw.

**Rule.** When a metric is defined relative to an axis, every term in it must be
measured along *that* axis. Check this on a case where the axes differ, not on
the one to hand.

### 11.5 Hard-coded labels propagate silently

`st['used_areas'].append([..., 'IT2'])` survived into IT3 and IT4, mislabelling
every area. `print('IT2 VERDICT')` was printed by IT3. IT3's own notebook cell
was titled ITERATION 2. Each is cosmetic alone; together they made the campaign
record disagree with itself about which experiment was which.

**Rule.** A driver derived from the previous one gets its identity from
`PROP['name']`, and the build script asserts that no stale identifier survives —
filenames, state keys, log tags. Prose references to earlier iterations are
fine and wanted; identifiers are not.

### 11.6 The pattern behind all five

Four of the five had been live for three iterations, and none would have been
caught by parsing, by the static audit, or by any amount of re-reading. They
were caught by **running the real code path offline against real data** — the
thing §10.1 already prescribed. The static audit finds names that do not exist;
only simulation finds code that runs and is wrong.

---

## 12. IT4: what a null cost, and what it should have cost

IT4 wrote for 22 minutes into an area that was already known — from its own
baselines, before the write — to be unable to resolve the effect. Nothing about
that was bad luck.

### 12.0 Withdrawn: 12.1 as first written

12.1 originally said the area gate had measured the wrong quantity a third time,
and that IT4 wrote into film that could not resolve the effect. **Both claims
were wrong**, and wrong in an instructive way: I compared IT4's threshold (40
gridded tiles) against IT3's (14 tiles in two edge bands) and attributed the
difference to the film. Measured identically the two areas agree, and the spread
is flat across all four iterations.

The actual fault was that the threshold was not the null of the statistic being
tested (C45). Correcting it turned IT4's null into a positive result.

**Rule.** Before attributing a difference between two numbers to the sample,
check that the two numbers were computed the same way. I have now made the
inverse of this error twice in one day: PITFALLS 11.3 (assuming a procedural
difference was harmless) and this one (assuming a procedural difference was
physical).

**Rule.** When a change to the method makes results *worse*, suspect the method
change before the data. Gridding the tiles was an improvement that made the test
less sensitive, and I spent an hour building a gate to reject good film because
of it.

### 12.1 The area gate — as it actually stands

| attempt | gated on | why it failed |
|---|---|---|
| IT1 | Λ-consistency, modulation ≥ 0.20 | Λ spread is estimator noise; three good areas rejected |
| IT2–IT4 | measured before/after floor ≤ 0.25, flip ≤ 0.25 | IT4 passed at 0.209 / 12 % and still resolved nothing |
| from IT5 | **2 sd of the leave-one-out before/after contrast** (C45) | it *is* the statistic the verdict uses |

The first two rows stand: Λ-consistency and the before/after floor both fail to
predict whether an iteration can be read. The third row is the fix — but note
that it barely varies between areas (C44 withdrawn), so its value is as an
absolute go/no-go before writing, not as a way to rank candidates.

**Rule, third statement.** Gate on the quantity the verdict actually compares
against, measured, at the point where it becomes knowable. Here that is 2 sd of
the control tiles, available from the baselines while the tip is still idle. If
it exceeds the smallest effect worth detecting, **do not write.**

### 12.2 Matching one comparison unmatched another

The slot assignment added this session pairs `UP` with `UM` on a shared
(dominant, command), so that a UP−UM difference means polarity. It worked. But
`A` then took whichever slot was left, and that slot started with the commanded
director already at w = 0.334 against 0.205 and 0.143 — a head start on the one
arm that was supposed to be the reference.

**Rule.** When placing panels, state which comparison is primary *and* which is
secondary, and match both if the frame allows. The way to afford that is to
settle more slots than panels and *select* the matched subset — which needs
smaller panels, not a bigger frame.

### 12.3 A null is only evidence at known power

IT4's verdict logic already said the right thing — "the reference failed too, so
this says nothing about uniform polarity" — because that branch was written
before the write, with the outcome unknown. That is the only reason the null was
not read as physics. Compare PITFALLS 10.2, four instances of exactly that
error.

**Rule.** Pre-register the threshold *and* a branch for "the control condition
also failed". A design where every outcome is informative does not exist; a
design that names the uninformative outcome in advance does.

---

## 13. Relaxing a guard, on purpose and on the record

`MAX_TOTAL_WRITE_MIN` was raised from **180 to 330 minutes** at 00:15 on 22 Aug,
and `TILE_SD_MAX = 0.150` was added beside it.

**This is a deliberate relaxation, not a drift.** Recording it here because a
safety envelope that quietly loosens whenever it becomes inconvenient is worse
than no envelope at all — the point of writing the numbers down is that changing
them has to be visible.

The reasoning:

- The 180-minute cap was a number I chose, not a physical limit and not the
  operator's constraint. The operator explicitly asked for iterations to continue
  overnight.
- The cap was a **proxy** for "the probe is still good". That quantity is
  directly measurable and was measured: the tile spread of w(cmd) in a common
  window across IT1 → IT4 is 0.101 → 0.100 → 0.095 → 0.098 — flat, not
  monotonic, over ~100 min of writing. There is no degradation trend to
  extrapolate.
- So the proxy is replaced by the measurement: **stop if the baseline tile
  spread exceeds 0.150**, 50 % above the observed band. Same correction as
  §12.1 and C44.

**What was not raised.** `MAX_WRITE_MIN = 26` per iteration stands. It bounds a
single unattended write, and nothing about working overnight makes one long
write safer. If a design needs more than 26 minutes it gets split or shrunk, as
IT6's letters were.

**Rule.** A guard may be relaxed when (a) the person who owns the risk asks, and
(b) the quantity it was protecting has been measured and is healthy. Both, in
writing, with the numbers. Never one without the other.

---

## 14. Dict keys are invisible to the static audit

At 00:55 on 22 Aug, with IT5 already past its write and into its readout, a
check found this in its verdict block:

```python
rung = sorted(W, key=lambda k: W[k]['sigma'])       # KeyError: 'sigma'
```

`W` is `res['within_frame']`. It carries `w_cmd`, `excess`, `x2sd`,
`threshold`, `design`, `cmd`, `dom0`, `dom`, `switched`, `period_nm` — and not
`sigma`. Sigma lives on the `panels` dicts. Each iteration's verdict was written
reading from whichever of the two dicts was in mind at the time, and nothing
complained.

**IT7 and IT8 had inherited the identical defect** with different keys —
`W[k]['mode']`, `W[k]['sign_every']`, `W[k]['bound_per_um']` — all of which live
only on `panels`. They were fixed before running. IT5 could not be: the process
had already compiled its source, so the fault was known ~20 minutes before it
fired and was unpreventable.

### Why every existing check missed it

The static audit walks the AST for **names** that are used and never bound. A
dict key is a string literal inside a subscript, so `W[k]['sigma']` is
syntactically flawless and semantically wrong, and no amount of AST walking will
say so. The offline simulation did not catch it either, because it exercises the
*build* path — geometry, dose, charge balance — and stops before the verdict.

This is the third instance of the same meta-pattern (PITFALLS 10.1 faults 5 and
6 were the first two): **the fault was introduced by my own patch, in code that
runs only at the very end, and was invisible to every check I had.** The verdict
block is the most dangerous code in a driver precisely because it runs last —
after the write, after the readout, when everything expensive has already been
spent.

### The check that does catch it

Cheap, and it generalises: collect the literal keys a driver reads off a dict,
collect the keyword names it constructs that dict with, and compare.

```python
read  = set(re.findall(r"W\[[^\]]+\]\['(\w+)'\]", src))
built = keys_of_the_res_wf_constructor(src)
missing = read - built
```

Run against the three drivers it found exactly one problem, in exactly the right
place: `run_it5.py reads 8 keys off W, builds 27; missing: sigma`.

**Rule.** Before launching, check key consistency as well as name consistency —
for every dict the verdict reads, confirm the keys are ones something actually
puts there.

**Rule, more general and more important.** Code that only runs at the end must
be exercised before the beginning. The build path is simulated against real
frames; the *verdict* path never was. It should be: feed it a synthetic result
dict of the right shape and check it prints rather than raises. That is a
five-minute test that would have caught all three instances of this pattern.

### The consequence, and the one thing that worked

IT5's measurement completes and its console survives (`it5_console.txt` is
written in the `finally` clause), so the result is recoverable offline exactly as
IT2's was — the area and the write minutes were also committed to the state
*before* the readout, per PITFALLS 11.1, so nothing about the sample record is
lost. The chain that launches IT6 keys off the lock file, which the `finally`
clause removes, so the instrument does not sit idle either.

Three earlier fixes each did their job here. That is what a pitfalls file is
for.

---

## 15. The heredoc backslash problem, and the night it lied to me

§4.2 has said "use a file, never inline" since 20 Aug. On the night of 21–22 Aug
I violated it **five times**, every time under deadline pressure, and four of
those were harmless — a `SyntaxError` that announced itself immediately and cost
a minute.

The fifth was not harmless, and it is the reason this section exists.

### What happened

Two drivers had a note-builder ending in a join. `run_it9.py` contained a
**doubled** backslash:

```python
res['note'] = '\\n'.join(note)      # joins on a literal backslash-n
```

which would have rendered IT9's entire notebook cell as one unbroken line of
visible `\n`. `run_it6.py` contained the correct single backslash. I wrote a
throwaway heredoc to find and fix the doubled one — and the heredoc collapsed
the backslashes in my *search pattern*, so the pattern matched the **correct**
file and missed the **broken** one.

The script then reported, truthfully from its own point of view:

```
run_it9.py: join looks fine
run_it6.py: fixed the doubled backslash in the note join
```

Exactly backwards. I patched a file that was already right, left the broken one
broken, and had a confident log line saying so. It was caught only because I
printed the `grep` output alongside the script's claim and the two disagreed.

### Why this is a different failure from the other four

A `SyntaxError` is self-announcing: the command dies, you fix it, nothing is
lost. A silently mangled *search pattern* produces a script that runs, reports
success, and does the opposite of what was asked. There is no error to notice.

**Rule, restated with teeth.** Never put a backslash inside a heredoc. Not in a
regex, not in a Windows path, not in a search string. Use the Write tool for the
script, or the Edit tool for a targeted replacement — Edit takes literal text
and no shell is involved.

**Rule.** When a patch script reports what it changed, print the *file's actual
state afterwards* in the same command and read both. The disagreement is the
only thing that caught this.

**Rule.** Under time pressure, the rules that get dropped are the ones whose
violation is usually cheap. That is precisely backwards: a rule worth writing
down is worth following when it is inconvenient, because the expensive failure
looks identical to the cheap one right up until it doesn't.

---

## 16. A rotated raster does not cover the box you think it does

IT6's stage A rasters along a triad member to deplete that family (C26). The call
was

```python
gen_center_out_raster(W_um=10.6, H_um=4.0, angle_deg=62.0,
                      center_um=(6, 6), ...)
```

intending to treat the 10.6 × 4.0 µm band the letters occupy. But `W_um` and
`H_um` are measured in the **rotated** frame, so at 62° that rectangle is a
diagonal stripe. Its footprint in frame coordinates came back as
x 1.81–10.19, y 0.44–11.56 — a stripe across almost the whole frame, overlapping
the horizontal letter band only in the middle.

Measured, per letter:

| letter | stroke area on rastered film |
|---|---|
| U | 19 % |
| T | 97 % |
| K | 18 % |
| **word** | **39 %** |

So the demonstration's premise — letters written into a *uniform* background —
holds for the T and fails for the U and the K.

### Why the mistake was structural, not careless

The raster direction is not free: it must be a triad member, because that is what
depletion is defined relative to. The word layout *was* free, and I made it
horizontal because that is how words are written. Those two choices are
independent and they conflict, and nothing in the code connects them.

### The fix, and why the obvious ones do not work

- **Enlarge the raster to cover the band at any angle.** Needs a square of side
  √(10.6² + 4²) ≈ 11.3 µm: 81 lines × 11.3 µm = 915 µm of path, 30 min per pass,
  61 min for the charge-balanced pair. Over every cap.
- **Shrink the word until its band is square.** A 7 × 3 µm band rasters in 27 min
  — but 3 letters in 7 µm with a 1.2 µm stroke is below the legibility limit
  (§DOC2 6.1), so the letters stop being letters.
- **Rotate the word to lie along the raster direction.** The only option that
  keeps full coverage, legible letters and a raster that fits the cap. The mask
  generator already works in a rotated frame, so this is a coordinate change on
  the letter boxes, not new geometry.

**Rule.** When two directions in an experiment are each chosen for their own
reasons — one by physics, one by convenience — check that they are compatible
*before* the write. Compute the actual overlap; do not assume a box is where its
width and height suggest.

**Rule.** For any generator taking a size and an angle, establish whether the
size is in frame coordinates or rotated coordinates. It is one print statement
before the run and a wasted iteration afterwards.

---

## 17. Two correct guards can conflict

IT6 halted after 23.5 minutes of raster, before writing a single letter, on:

```
FAIL  S9 footprint: overlaps IT6_UTK at (-14.0,-14.0) 12 um
      (need 12.5, have dx 0.0 dy 0.0)
```

It had collided with **itself**. Two mechanisms, each added deliberately and each
right on its own:

- **PITFALLS 11.1**: commit the written area to `used_areas` the moment the
  trajectory is sent, because IT2 wrote 512 pulses, crashed before `save_state`,
  and left a written area invisible to every guard for two days.
- **S9**: refuse a footprint that overlaps an area in `used_areas`.

For a one-write iteration they never meet. IT6 writes twice — a raster, then the
letters — and preflights before each, so by the second preflight its own area is
already registered and S9 reports a separation of 0.0 µm. Writing twice into one
area is the whole design of a deplete-then-select experiment.

The fix is one line of scope: S9 exists to keep one experiment off *another's*
film, so entries under the proposal's own name are skipped — and the skip is
printed, because a skipped check that looks like a passed check is how §14
happened.

**Rule.** When adding a guard, ask which *other* guard's output it consumes.
`used_areas` is written by one mechanism and read by another, and neither
author considered an iteration that writes twice.

**Rule.** A guard should encode *why* it exists, not just what it compares. S9's
purpose is "do not disturb another experiment's film". Written as "do not overlap
anything in this list", it was correct for a year and wrong the first time an
iteration had two stages.

**What it cost.** 23.5 minutes of raster and the letters of IT6. What it did
*not* cost: the raster's result, which is in the console and turned out to
overturn C26 (see C49) — and the prepared area itself, which the next iteration
wrote into rather than re-preparing.

---

## 18. IT7: a void iteration, and the gate that made it cheap

IT7 halted before writing anything. 31 % of untouched control tiles changed their
dominant director between two consecutive baselines, against the 25 % cap added
after IT1. **Q19 — lattice axis or sign boundary — therefore remains completely
open**; nothing was measured and nothing should be inferred.

The gate cost about 35 minutes of screening and baselines and saved a 15-minute
write plus a readout that could not have been interpreted. That is the trade it
exists to make, and this is the first time it fired.

**What made it a clean halt rather than a confusing one:** the halt reason was a
measured number against a stated limit, printed at the point of decision. There
was nothing to reconstruct afterwards.

**The near-miss.** `contact_check` simultaneously warned that the DART loop was
19.5 kHz off resonance with |A| down to 30.7 pm from 40–55 pm earlier, so the
obvious story was a dying probe — and the obvious action was to stop the night's
work. The measured check said otherwise: tile spread flat at 0.081–0.109 across
five iterations, no trend, well inside the 0.150 guard. The probe was fine; the
*area* had near-degenerate populations, so "dominant director" was not a
well-defined label there (C52).

**Rule.** A warning from an instrument check is a hypothesis, not a verdict. Test
it against the quantity that actually matters before acting on it — especially
when acting on it means stopping.

---

## 19. Session of 27 August: five faults caught before any instrument time

New probe, coarse stage moved, new session folder. Nothing was written to the
sample during this phase; every item below came out of the offline checks, which
is the point of having them.

### 19.1 A brand new session folder is EMPTY, so folder auto-resolution picks yesterday

`resolve_folder()` and the notebook's setup cell both choose the date directory
whose newest `.ibw` is most recent, and both **skip directories with no `.ibw`
files at all**. On the first frame of a new session `260827/PZTO` is empty, so
both silently return `260820/PZTO`: every `ibw()` lookup, `instrument_is_busy`
and `check_folder` would have operated on yesterday's data. `check_folder` would
then have raised "a sibling folder has fresher data" and killed the run after
the tune.

The operator had already set `CONFIG['data_folder']` correctly in the notebook —
and cell 4 ignores `CONFIG` entirely and re-resolves. **An explicit setting that
a later cell overrides is worse than no setting**, because it reads as done.

Fix: `autoloop.FOLDER_OVERRIDE`, which wins outright and creates the directory
if absent. Generalisation: *auto-detection that cannot represent "empty but
correct" must be overridable, and the override must be checked, not assumed.*

### 19.2 The travel-overhead multiplier is not a constant, and 1.35x is only true at one dwell

`HANDOFF_1` and `FINDINGS.md` §4 both give ~1.35x for a solid Lambda/2 panel.
Measured from the point counts of the trajectory files actually on disk:

| iteration | dwell | dwell pts | total pts | overhead | travel per 256-site panel |
|---|---|---|---|---|---|
| IT3 | 1.48 s | 28416 | 36512 | **1.285x** | 2699 |
| IT4 | 1.36 s | 26112 | 33590 | **1.286x** | 2493 |
| IT9 s1 | 0.88 s | 11264 | 16069 | **1.427x** | 2402 |
| IT9 s2 | 0.88 s | 5632 | 7927 | **1.407x** | 2295 |
| IT5 | mixed | 14080 | 21578 | **1.533x** | 2499 |

Travel points are fixed **per site** by the geometry; dwell points scale with
dwell. So the multiplier rises as the dose falls, and it is largest exactly where
budgets are tightest — a low-dose ladder. **Do not carry a multiplier. Carry
travel per panel (~2300-2800 points, i.e. 1.5-1.9 min per 256-site panel at
Lambda/2) and add it.** Then gate on the built path anyway.

### 19.3 Four Lambda/2 panels do not fit a 12 um frame, because the halo does not shrink

Caught by the offline simulation on real frames, not by arithmetic. At the
simulated area Lambda = 354 nm, so halo = 2.45 um and a 2x2 grid needs pitch
5.0 um. The panels plus halos then cover the frame so completely that **0 of 49
grid tiles cleared every panel by the margin**. The C45 leave-one-out null had no
sample, so the primary metric did not exist, and the driver halted in the tile
block *after* the write would already have happened had the gate been weaker.

This is §2.4 ("a treatment that fills the frame cannot audit itself") with a
number attached. The rule that follows is sharper than the old one: **count the
surviving control tiles at DESIGN time, in the simulation, and treat fewer than
eight as a geometry failure rather than a reporting caveat.**

### 19.4 An experiment needing BOTH rotation senses cannot use the cheap-angle trick

Placement sizes the lattice by `ANGF = |cos(cmd)| + |sin(cmd)|`, and `run_it5`
iterated a fixed point that chose, per slot, whichever sense gave the smaller
ANGF. That is legitimate when the sense is a balancing choice (C30: the two are
equivalent). It is **not available when the sense is the independent variable**:
the two neighbours of a member are 120 deg apart, so for the triad (2, 62, 122)
the factors are 1.026 / 1.356 / 1.375 and whichever member is dominant, one
command always lands above 1.35.

Consequence, worked through with the real `geom()`: a 3x2 grid does not fit a
12 um frame at any starting member, and growing the frame at 256 px makes it
**worse** — `WIN` is floored at 26 px, so a larger `px_nm` pushes `WIN` past the
point where n = 16 still spans the window, n jumps 16 -> 32, and the halo grows
faster than the frame. Only more pixels help (14 um at 320 px restores the 12 um
geometry with room for 3x2).

So `HANDOFF_4`'s RW1 — "6 slots settled, 4 panels written, selected to share a
dominant" — is geometrically impossible as specified at 12 um / 256 px. That was
not visible from the design, only from running the sizing code.

### 19.5 A verdict-branch test that greps the whole console tests nothing

The driver deliberately prints every pre-registered branch description *before*
the write, which is good practice (S27). A branch test that searches the full
console for the expected branch text therefore matches **all** branches, every
time, including on runs that halted long before the verdict. The first run of
this test reported "wrong branch" for a verdict that was correct, and would
equally have reported "OK" for one that never ran.

Fix: match only the text after the `VERDICT` banner, and treat a `SystemExit`
as a halt rather than as a branch hit unless the banner was actually reached.
Generalisation: *a test whose oracle can be satisfied by output the code under
test did not produce is not a test.*

### 19.6 The dict-key parity check, validated against a known fault

The key-consistency check was re-run on `run_it5.py` as a control and
independently reproduced the recorded fault: **"verdict reads 8 keys off W;
res_wf builds 16; missing: ['sigma']"** — the defect that had already destroyed
one verdict. A check that finds a known bug in known-buggy code is worth
trusting on new code; one that has only ever passed is not.

**But see 19.8: within the hour it also produced a FALSE positive, and the
"fix" for the imaginary bug was a real crash.** Both halves of that sentence
matter -- reproducing a known fault establishes sensitivity, not specificity.

### 19.7 The verdict-branch harness lied three times, and every time it was the harness

Exercising the verdict against synthetic results is a protocol requirement
because three separate faults have lived in verdict blocks. Building that
harness produced three false accusations against correct driver code, in a row.
The pattern is worth more than the incidents.

**(a) The oracle matched output the driver had not produced.** The harness
grepped the whole console for the expected branch text. But the driver prints
*every* pre-registered branch description before the write, which is good
practice (S27) -- so all four branch strings were present in every run,
including runs that halted long before the verdict. It reported "wrong branch"
for a correct verdict, and would equally have reported "OK" for a verdict that
never executed. Fix: match only after the `VERDICT` banner, and treat a
`SystemExit` as a halt, not as a branch hit.

**(b) The synthetic "after" frame aliased onto the reference frame.** With
`RESUME` set, `F_REF` is one of the three baseline tags. The harness served
frames cyclically from index 0, so the frame handed back as `a1` was sometimes
*the same tag* as `F_REF`. Then `s1` and `s0` were the identical query, every
excess came out exactly `+0.000`, and all four scenarios collapsed into VOID.
An excess of *exactly* zero to three decimals is the tell: real data does not do
that. Fix: serve post-write frames from beyond the baselines.

**(c) The oracle mis-identified which positions were panels.** The synthetic
`dir_state` decided "this is a panel query" by assuming the first four distinct
positions it saw were the slot centres. They were not: the baseline-floor block
runs *before* placement and queries **tile** centres, so the panel registry
filled with tiles and no panel query was ever recognised -- producing the same
uniform `+0.000` excess as (b), from a completely different cause. Fix: record
the slot centres where they are actually established, by wrapping `command_for`,
rather than inferring them from call order.

**The generalisation.** All three share a shape: *the harness encoded an
assumption about the driver that the driver does not guarantee* -- that branch
text appears only in verdicts, that served frames are distinct, that panels are
queried before tiles. A test built on an assumption about the code under test
fails in the same direction as the code, and its verdict is then worthless in
both directions.

Two practical rules follow:

1. **Read the oracle's failures as ambiguous until the mechanism is known.**
   Twice the harness reported a fault that did not exist; the temptation each
   time was to "fix" working driver code. Ask what value the oracle would print
   if the driver were perfect, and check it prints that.
2. **Distrust suspiciously exact numbers.** `+0.000` on every panel in every
   scenario is not a null result, it is an identity -- two paths reading the
   same input. The same instinct applies to the campaign's real data: §8's rule
   is to exhaust the measurement before the material, and an exact zero is the
   measurement telling you it never varied the thing you thought it varied.

For the record, the harness did its job once it was correct: it is what
confirmed the two-panel geometry reaches the verdict at all, after the
four-panel version could not (19.3).

### 19.8 The parity check's false positive, and a fix worse than the bug

Within an hour of 19.6 the same dict-key parity check reported that
`run_it7.py`'s `res_wf` never places `'mode'`, which its verdict groups on
(`W[k]['mode']`, par against perp). That looked exactly like the recorded
`KeyError: 'sigma'`, so I added `mode=p['mode']` to the dict.

It was a false positive. The same `dict()` call already ended with

```python
**{_k: p[_k] for _k in ('sigma', 'dwell', 'mode', 'sign_every',
                        'n_bound', 'bound_per_um', 'ratio') if _k in p}
```

which supplies precisely those keys from the panel dict. The checker walks
keyword arguments and cannot see through a `**` splat, so it saw them missing.

**The fix was strictly worse than the imaginary bug.** `dict()` with a duplicate
keyword raises `TypeError` at call time -- in the scoring block, after the write
and after both after-frames. I had turned a non-existent crash into a real one,
of exactly the class I was hunting, in the driver that was about to run. The
offline simulation caught it (`TypeError: dict() got multiple values for keyword
argument 'mode'`) while the run was still in its screening phase, so the driver
was killed before its write and relaunched; the cost was ~15 min of screening
rather than a wasted 15 min write plus an uninterpretable frame.

Three lessons, in order of how much they would have saved:

1. **Before "fixing" a reported missing key, read the whole dict call.** The
   answer was eleven lines below the insertion point.
2. **A static checker that under-approximates what code provides produces
   false positives, and false positives get "fixed".** The dangerous direction
   for this class of tool is not missing a bug, it is inventing one --
   because the remedy is an edit to working code. `run_it8.py` got the same
   treatment (`sign_every`, `bound_per_um`) in the same pass.
3. **The simulation is what stands between an audit's opinion and the sample.**
   Two checks disagreed; the one that executes the real code path against real
   frames was right. When a static check and a simulation conflict, the
   simulation wins.

The checker now resolves `**{...}` splats by collecting the string literals
inside them, and still reports `run_it5.py: missing ['sigma']` -- which is the
genuine one, because `run_it5.py` has no splat. Sensitivity preserved,
specificity added.

### 19.9 How to exercise a verdict properly: exec the real block, do not re-run the driver

Requirement 9 of the protocol -- exercise the verdict branches once per outcome
-- was implemented first by running the whole driver with a synthetic
`dir_state`. That works, badly: each scenario costs a full screening and scoring
pass (minutes), the area gates are real so most candidate offsets halt before
the verdict, and three separate harness bugs made it accuse correct code (19.7).
Worse, a full-driver simulation can only ever reach the VOID branch, because the
"after" frame it serves is untouched film -- so the branches that matter are
exactly the ones it cannot reach.

The technique that works: **slice the verdict block out of the driver by line
anchors, de-indent it, `compile()` it, and `exec` it against a namespace you
construct.** It is the same source the instrument run executes, so it is not a
reimplementation, and it takes milliseconds per scenario.

```python
i0 = index of "print('ITxx VERDICT')" + 2
i1 = index of "st['iteration'] = st.get('iteration', 0) + 1"
block = dedent one level of lines[i0:i1]
exec(compile(block, 'verdict', 'exec'),
     dict(np=np, res=..., panels=..., ds=fake, F_REF='BEFORE', a1='AFTER',
          WIN=..., triad=..., LAM=..., st={'strikes': 0}, ...))
```

Applied to IT12 this exercised all **seven** outcomes in one run -- the four
comparison branches, the unexpected-sign branch, VOID, and the case where the
adaptive trim has dropped an arm. That last one found a real `KeyError`: the
"density matters" branch printed `P['Q4']['n']`, which does not exist when Q4
was trimmed, and it would have fired *after* the write.

Two things this makes cheap that were previously expensive:

1. **Every branch, every time.** There is no reason to leave a branch unexercised
   when each costs a millisecond. The IT11 harness left one branch verified only
   by inspection because a full-driver run per scenario was too slow.
2. **Deliberately hostile inputs.** Signs the wrong way round, nan where an arm
   is missing, all-equal values. The `backwards` scenario (DEN worse than ISO)
   confirmed the driver refuses to name a mechanism rather than picking one.

The namespace you build IS the contract the verdict depends on. If constructing
it is awkward, that is the verdict reaching for too much state -- which is worth
knowing before the instrument tells you.

### 19.10 A gate that measured engagement state and called it contact force

Asked to check the withdrawn deflection for drift and compensate, I added a gate
computing `force = setpoint - read_meter()[1]` and halting outside 0.85-1.45.

`read_meter()[1]` is the LIVE deflection. Withdrawn, it is the free level and
the subtraction is meaningful. **Engaged and in feedback, it equals the
setpoint**, so the subtraction returns ~0 no matter what the force is. The gate
therefore reported "force 0.002" and aborted a run whose only sin was starting
with the tip engaged -- which is the normal state after any previous run.

Two failures at once, both in PITFALLS already:

* **3.3, abort logic more confident than the measurement.** The proxy was
  invented that evening and its range inferred from a handful of readings, and
  it was given authority to stop the night's work.
* **Section 8's closing rule: a number that is stable is not necessarily a
  number that means one thing.** The reading was perfectly reproducible. It just
  meant "engaged" on some calls and "free level" on others, and nothing in the
  value distinguished them.

It also propagated backwards into a *conclusion*: FINDINGS M8 had blamed an
earlier readout collapse on the same reading (+0.350 against a 0.350 setpoint),
which is now recognised as an engaged tip rather than a drifted free level. M8
has been corrected in place; the parts that rest on the |A| time series and on
the re-tune fixing the collapse are unaffected, because those never depended on
the deflection interpretation.

**The rule.** Before gating on a derived quantity, write down the states of the
instrument in which its inputs mean different things -- and check the gate can
tell them apart. Here two states (engaged, withdrawn) map to the same number
with opposite meanings, and the gate had no way to distinguish them. The
replacement reports the reading, classifies which state it implies, offers the
force proxy only when the tip is demonstrably withdrawn, and never halts;
readout health is judged from |A|, which is measured on every frame and means
one thing.

### 19.11 The screening ruler was calibrated to a frame it never measured

**The single most expensive defect of the campaign so far. It cost a night.**

The driver holds two sizes. `FRAME = 10.0` is the size of the frame that gets
SCORED. Screening runs at 5 um, because the operator asked for small frames and
they turn around in 2.1 min instead of 8.5. The screening block then computed

```python
PX_NM = FRAME / PX * 1000.0        # 10 um / 256 = 39.06 nm/px
...
v = g('period')(S, PX_NM, f)       # ... applied to a 5 um frame
```

Every screened Lambda came out at **exactly 2x** the true period. Not noisy --
exactly, on every point, because it is one multiplication by a constant.

**Why nothing caught it.** The failure has no signature:

* it does not raise, and the numbers stay physically plausible -- 548 nm is a
  perfectly reasonable lamellar period, just not this film's;
* the static audit, the dict-key parity check and the verdict-branch harness all
  pass, because the code is correct code that computes the wrong quantity;
* the offline simulation replays real frames and reproduced the same wrong number
  faithfully, which is exactly what a simulation is supposed to do;
* **it is self-consistent.** Every point agreed with every other point that the
  film was coarse. Sixteen candidates in a row read 388-755 nm and their
  agreement felt like evidence. A constant-factor error is invisible to internal
  consistency -- it moves the whole distribution and leaves its shape alone.

**What it produced.** A confident, quantified, entirely false conclusion: "this
region is too coarse for a 10 um frame, six of seven candidates past the cliff,
move the coarse stage." That went into `SESSION_260827.md` as the headline
recommendation and into FINDINGS M9 as supporting data. It also drove a real
design decision -- abandoning the two-panel within-frame pair for one panel per
frame -- which discarded C42's drift cancellation for nothing. **A wrong number
does not stop at being wrong; it argues, and it wins.**

**How it was found.** Not by re-reading the driver. `survey_lambda.py`, written
as a separate tool for a different purpose, computed `px_nm = SIZE_UM / PX *
1000.0` from its own frame size because that was the only size it had. Its first
two points read 301 and 245 nm where the driver had been reading 548 and 490.
Two tools disagreeing by a suspiciously round factor is what a constant-factor
error looks like from outside.

**The rule.** *A scale factor must be derived from the data it is applied to, not
from a constant that is usually the same.*

```python
_scr_um = float(h['ScanSize']) * 1e6          # THIS frame, from ITS header
SCR_PX_NM = _scr_um / float(S.shape[0]) * 1000.0
```

The header travels with the array; a module constant does not. Applied to all
three drivers, plus a warning when a screening frame is not the expected size --
so the next time the two diverge it is printed rather than silently absorbed.

**The general form, worth more than this instance.** Every check in section 19
verifies that the code does what it says. **None of them verifies that what it
says is what was meant.** The defences that work on a units error are different
in kind: derive scales from data, cross-check one quantity by two independent
routes, and treat a suspiciously round ratio (2.00, 1000, 57.3) between two
estimates as a units bug until proven otherwise. Unanimity among points sharing
one code path is not corroboration -- it is one measurement repeated.

### 19.12 The floor gate rejected a good area, and its own output said so

IT12 halted at the measurability gate on the best area of the session --
Lambda 280 nm, modulation 0.287, the highest of 20 candidates:

```
    0109 vs 0110: floor 0.213, 4/14 flipped (29%)
    0110 vs 0111: floor 0.242, 5/14 flipped (36%)
    0109 vs 0111: floor 0.091, 1/14 flipped (7%)
    worst pair:   floor 0.242 (max 0.25), flip 36% (max 25%)
HALTED: this area cannot support the measurement. Move.
```

Re-measuring the SAME area with the SAME settings twenty minutes later:

```
    0113 vs 0114: floor 0.044, 0/12 flipped (0%)
    0114 vs 0115: floor 0.039, 1/12 flipped (8%)
    0113 vs 0115: floor 0.074, 1/12 flipped (8%)
    worst pair:   floor 0.074, flip 8%   -> passed, and DESIGN M selected
```

**The diagnosis was already on screen.** Both failing pairs contained 0110; the
pair that excluded it passed by a factor of three. That is the signature of one
bad FRAME, and it is distinguishable from a bad AREA, which would degrade all
three pairs roughly equally. The gate reduced three numbers to their max and
threw the structure away.

**Worst-of-three is the right default and the wrong summary.** Taking the worst
pair is correct when the three disagree for unknown reasons -- it is what stops
IT1 happening again. But `max()` over a set whose disagreement is itself
informative discards the diagnosis to compute the verdict. The gate should
report the split, then decide.

**What made this hard to call.** `probe_health.py` put 0110 at |A| 43.1 pm,
r12 0.87 -- low-normal, not the ~21 pm collapse of M8. So the evidence was
genuinely ambiguous and the honest move was to TEST the claim, not to assert it
and write anyway. Pre-registered before relaunching: one retry; pass = worst pair
inside both limits; fail = the area is finished, move on, no second attempt.

**The trap this avoids.** An area re-screened until it passes is an area selected
on the noise in its gate rather than on its film -- gate-shopping, and it would
put an unreadable iteration through a gate built to prevent exactly that. The
protection is not judgement in the moment, it is committing to the stopping rule
BEFORE seeing the result, and to a specific falsifiable claim (0110 is the
outlier; the true floor is ~0.09) rather than the unfalsifiable "maybe it will
pass this time".

**Standing rule.** When the three-way split localises to one frame -- both
failing pairs share it, the pair excluding it passes comfortably -- re-measure
that area ONCE with fresh baselines. Otherwise move. `IT12_AREA="x,y"` screens a
single offset and takes fresh baselines there; `RESUME` is the wrong tool, since
it reuses the frames on disk, including the bad one.

### 19.13 A fix applied to the half of the measurement that was complaining

M8 diagnosed the readout collapse and fixed it: re-tune before every frame. The
fix went into the three baselines. It did not go into the post-write frames, the
angle control, or the zooms -- and those are the half the verdict is computed
from. IT12 then reported VOID off a frame at r12 0.40.

**The reasoning error, which is the reusable part.** The collapse was FOUND
through the floor gate, because that is what halts a run and gets read. So the
repair was made where the symptom appeared. But a symptom appears where there is
a detector, not where the problem is worst -- and the baselines have a detector
(the floor gate) precisely because a bad baseline is recoverable, while a bad
readout silently produces a plausible number.

**The check that would have caught it in one line.** After fixing anything, list
every OTHER call site of the thing that was wrong:

```bash
grep -n "g('frame')()" run_it12_pathway.py
```

Five call sites; one had been fixed. The fix was written on 27 Aug and this grep
was not run until 28 Aug at 05:20, after it had cost a write, an area, and a
false conclusion about dose.

**Generalisation.** When a fix is applied to one call site of a repeated pattern,
the question is never "is this site fixed" but "how many sites are there". The
same shape as PITFALLS 19.11: there, one scale constant was derived from the
wrong source in one of three drivers; here, one acquisition pattern was corrected
in one of five places. Both were found by looking at a second instance, not by
re-reading the first.

**And: check the health of the frames a verdict was computed from BEFORE
believing the verdict.** `probe_health.py` takes seconds and prints r12 and
\|A\| per frame in time order. A VOID is exactly the result a dead readout
produces, so a VOID should trigger that check automatically rather than being
reported as physics.

### 19.14 A verdict that did not know which experiment it was reporting

The selection verdict printed, for the shear experiment:

    Both panels ended on the SAME director (10 and 10).
    Different templates, same destination: consistent with
    DRIVE alone, with the template not choosing anything.

Exactly backwards. That sentence was written for `EXP=select`, where the two
panels carry DIFFERENT wavevectors and so predict different destinations. The
shear panels deliberately share a wavevector and differ only in real-space
arrangement, so **landing on the same member is the confirmation, not the
refutation**. The driver reported its own strongest result as a null.

**Why the code was wrong in a way that reads as right.** The branch tested a
fact about the OUTCOME -- did the two panels agree? -- and attached a fixed
interpretation to it. But the meaning of agreement depends on the DESIGN, which
the block never consulted. Same shape as the fig6 design label the day before: a
verdict that does not know which experiment produced it will describe whichever
one its author had in mind while writing.

**Fix.** Compute, from the specs, whether the two templates predict the same
destination, and branch on that first:

```python
wants = [sp.get('want') for sp in spec]
same_target = (len([w for w in wants if w is not None]) == 2
               and abs((wants[0] - wants[1] + 90) % 180 - 90) < 10)
```

**And a second fault found while testing the repair.** The new
"panels landed apart despite sharing a wavevector" branch had its format
arguments on the wrong `print`, so it raised `TypeError`. That branch fires only
when the result contradicts the theory -- i.e. precisely when a crash costs the
most and when the temptation to dismiss the run as "a bug" is strongest. Both
branches are now exercised against synthetic results before every run.

**The rule.** An interpretation block must branch on the DESIGN before it
branches on the OUTCOME, and every branch must be executed at least once
off-instrument -- including, especially, the ones that only fire when the theory
is wrong.

### 19.15 The dose threshold that was really a window-size limit

Twenty-three dose points, sigma 19 to 803, on a commensurate lattice. Two of
them missed their target badly -- 64 and 56 degrees off -- and they were the two
lowest doses. Read naively that is a threshold: selection switches on somewhere
between sigma 28 and 52, ten times below the aperiodic square's 400-667. It
would have been the sharpest quantitative claim in the campaign.

**Both failures came from the same area, and that area has the coarsest film in
the set.** Lambda 388 nm against 245-354 everywhere else. The analysis window is
1.4 um, so at that area it spans

    1.4 um / 0.388 um = 3.6 periods

and the FFT estimator needs **at least 4**. The dominant direction read out of a
3.6-period window is not a measurement of anything. The two "sub-threshold"
points are a broken ruler, not a physical boundary -- the same shape as PITFALLS
19.11, where a mis-scaled Lambda produced sixteen self-consistent wrong numbers.

**Why it was seductive.** The two bad points sat exactly where a threshold was
expected, at the bottom of the dose range, and they were consistent with each
other. Two independent panels agreeing is normally evidence; here they agreed
because they shared the defect, not because they shared the physics. The
low-dose end of a series is where the estimator is also weakest, so **a
threshold and an estimator failure appear at the same place by construction**.

**The check that catches it.** Before reading any per-window direction, compute
how many periods the window holds:

    n_periods = window_um / (Lambda_um)      require >= 4

and drop the window, not the point, when it fails. The driver screens areas on
Lambda for BUILDABILITY (M9) but never checked that the READOUT window was valid
at that Lambda -- two different requirements that happen to involve the same
number.

**Standing rule.** An area is usable only if it satisfies both:
  * the template fits and the halo leaves control tiles (M9), and
  * the analysis window holds >= 4 Lambda.
At a 1.4 um window that second condition means **Lambda <= 350 nm**. Areas at
354 nm are marginal (3.95) and should be flagged; 388 nm is out.

**What survives.** The lattice is on target at every valid point from
**sigma 52** upward, with offsets of 4.0, 4.0, 6.0 and 4.0 degrees at sigma
52-117 tightening to 1.0-1.5 degrees above 144. So commensurate templates work
at least 8x below the aperiodic square's threshold. The lower bound is a BOUND,
not a measurement, and finding the real one needs low doses on FINE film.

---

## 20. Session of 28-29 August: the loop stopped three times and idled the instrument for 7.1 hours

The user asked for 13 hours of autonomous work to a 09:00 deadline and had to
restart the session by hand twice, then found it dead at 08:14 with the
instrument cold since 02:52. This section is the post-mortem. Every time and
every count below was recovered by parsing the session transcript
(6220 records) and the job logs in `%TEMP%`; none of it is recollection.

### 20.0 What actually happened

| # | agent's last turn | what it said it was waiting for | job really finished | human had to restart | agent idle | **instrument idle** |
|---|---|---|---|---|---|---|
| A | 20:18 | "the 3x3 probe is running now (~25 min)" | 20:40 (`probe3.log`) | 20:59 | 41 min | 19 min |
| B | 21:02 | "I'll report when the queue completes (~2 h)" | 22:22 (`campaign.log`) | 23:48 | 166 min | **86 min** |
| C | 02:49 | "Remaining zooms are running" | **02:52** (`zoomseries.log`) | 08:14 (user returned) | 325 min | **322 min** |

**Stall C is the one that mattered.** The three zooms it was "waiting" on
finished **3.5 minutes** after the turn ended. From 02:52 to the 09:00 deadline
there were **6.1 hours** of budget and a fully working instrument, and nothing
happened in any of them. Total instrument idle across the three stalls:
**427 min = 7.1 h of a 13 h budget.**

### 20.1 `nohup ... &` inside a foreground call detaches the job from the harness

This is the mechanical root cause, and it is not subtle once counted. Across the
session:

| launch mechanism | uses | does the agent get woken when it finishes? |
|---|---|---|
| `Bash(run_in_background=true)` | 92 | **yes** - harness tracks the task and posts a notification |
| `Monitor` on a log file | 17 | **yes** - fires on the matched line |
| `nohup <job> > log 2>&1 &` in a **foreground** Bash call | **75** | **NO** |

With `nohup ... &` the foreground command is the *launcher*, not the job. It
returns in the couple of seconds it takes to spawn, or in the 30 seconds of the
`sleep 30; head log` tail that usually followed it. The harness sees a command
that **completed successfully**, records it, and has no handle on the detached
process at all. When the real job ends -- 20 minutes or 2 hours later -- there is
nothing left that knows it was ever running, so **no notification is generated
and the agent is never re-invoked**.

Every one of the three stalls sits immediately after a `nohup ... &` launch:

```
00:15 UTC   nohup env PROBE_PTS=... python -u probe_area.py > /tmp/probe3.log 2>&1 &      -> stall A
01:01 UTC   nohup python -u run_campaign.py > /tmp/campaign.log 2>&1 &                    -> stall B
06:48 UTC   nohup bash -c 'for spec in ...; do ... zoom_pathway.py ...; done' > /tmp/zoomseries.log &  -> stall C
```

**What kept the loop alive the rest of the time was accidental.** Where work
continued, it was because the turn happened to also contain either a
`run_in_background` task or a *foreground polling loop*:

```
for i in $(seq 1 20); do grep -aqE "frame kept|Traceback" /tmp/zoom1.log && break; sleep 20; done
```

That blocks the turn until the job reports, so the turn cannot end early. It
works -- but only when I remember to write one. It is a habit standing in for a
mechanism, and habits fail at 02:49 in the morning.

### 20.2 The scheduling tools existed and were never used

`ScheduleWakeup`, `CronCreate` and `TaskOutput` were available for the whole
session. **Uses: 0.** And the last `Monitor` was armed at **01:28 on 28 Aug** --
for the following **27 hours**, covering the entire overnight campaign, not one
was armed. So after that moment the session had *no* self-restart mechanism of
any kind other than a background-task notification I might or might not have
created in the same turn.

That is the difference between a loop and a sequence of turns that happens to
continue. A loop must be able to wake itself up.

### 20.3 "I'll report when it lands" is how a turn ends a session

The mechanical fault above was made fatal by a writing habit. All three stalls
end with a fluent status paragraph in the future tense:

* *"The 3x3 probe of the new location is running now (~25 min). Next I'll build a campaign runner..."*
* *"I'll report when the queue completes (~2 h), then move to the high-resolution pathway imaging."*
* *"Remaining zooms are running; then final figures and the manuscript."*

Each reads like a progress report from something that is still running. None of
them **was** something still running, as far as the harness was concerned. The
prose describes an intention; the intention has no executor. Worse, the
narrative is *self-soothing* -- having written "then final figures and the
manuscript", it feels as though the manuscript is in hand, and the absence of
any actual next action does not register.

**There was also always free work available.** At stall C, S24 was exhausted, so
every remaining task was measurement and analysis: orientation maps on already
acquired frames, the manuscript draft, the figures. None of it needed the
instrument, none of it needed the zooms to finish, and none of it was done.
Waiting was never the only option; it was a choice that looked like a
constraint.

### 20.4 The 40-50 minute "waits" were the same fault in a milder form

Three further gaps -- 20, 50 and 43 minutes -- resolved on their own when a
background-task notification arrived. Those did not kill the session, so they do
not appear in the table, but the agent was idle in all of them while analysis
work sat undone. The healthy pattern is: **launch, then immediately do the
free work**, and let the notification interrupt that. Not: launch, then wait.

### 20.5 Standing rules, added to Section 8.4

| # | rule |
|---|---|
| **S30** | **Never start a long job with `nohup ... &` or `Start-Process`.** Use `Bash(run_in_background=true)`, which the harness tracks and which re-invokes the agent on completion. If a detached launch is genuinely unavoidable, arm a `Monitor` on its log **in the same turn**, before writing any prose about it. |
| **S31** | **A turn may not end on a promise.** Before ending a turn, verify there is at least one live re-invocation handle: a tracked background task, an armed `Monitor`, or a `ScheduleWakeup`. If there is none and the deadline has not passed, the turn does not end -- do the next piece of free analysis work instead. |
| **S32** | **Launch, then work.** Never spend a turn waiting on a job whose result is not needed for the very next action. Instrument-idle minutes are the scarcest resource in the campaign and the only one that cannot be recovered. |

### 20.6 How to audit this after the fact

The failure is invisible from inside a turn and obvious from the transcript. The
detector, which is what produced the table in 20.0:

* a **stall** is an assistant turn with no `tool_use` and no live task handle,
  followed by a long gap;
* correlate each stall's timestamp against the `mtime` of the log the turn
  claimed to be waiting on. **If the log stopped changing before the human
  restarted the session, the wait was doing nothing.**

For stall C the log's last write is 02:52:59 and the restart is 08:14. That one
comparison is the whole diagnosis.

### 20.7 Minor, but it cost a re-run: Python prints crash on non-ASCII under Windows

`diag_stops.py` died with

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2212'
```

part-way through its report, because a piped Python stdout on this machine
defaults to **cp1252**, and the campaign's own prose is full of `-` (U+2212),
`+-`, `um` and Greek letters. The output looked like a crash in the analysis; it
was a crash in the *printing*, after the analysis was already correct.

Prefix any script that prints campaign text with `PYTHONIOENCODING=utf-8`, or
redirect through an explicitly UTF-8 file. This is the same family as 4.2 and
15: the transport mangles the characters, and the error surfaces far from the
cause.

### 20.8 The analysis tiles were bigger than the thing being analysed

The pathway classifier read four 1.12 um FFT tiles out of each 2.0 um zoom and
called the panel UNIFORM or MIXED from how many tiles agreed. Tile size was set
by the estimator's own requirement -- **4 Lambda, from 19.15** -- and the frame
size was set by the scanner. Nobody compared either to the **panel**, which is
1.2-1.4 um. Every tile therefore overhangs the panel edge by 0.3-0.4 um and
contains unwritten film; the outer tiles are roughly a third surround by area.

So "three tiles agree and one does not" measures **how much surrounding film the
odd tile caught**, and would report exactly the same thing for a perfectly
switched panel as for a half-switched one.

**How it was caught.** Not by inspection -- by completing the series. Two frames
(sigma 52 MIXED, sigma 117 UNIFORM) look like a clean dose threshold. Six frames
give MIXED at 52, UNIFORM at 67, UNIFORM at 111, UNIFORM at 117, MIXED at 120
and **MIXED at 306**. A classifier that calls the highest dose in the set mixed
and a dose four times lower uniform is not measuring dose. *The two-point version
was more convincing than the six-point version, which is the warning sign.*

**The fix, and why it is not just a smaller tile.** Switching to the structure
tensor is what made a smaller window legal: it smooths over a length (150 nm)
rather than requiring four periods, so a 1.0 um interior window is valid for it
and would not be for the FFT. Then the frame's own border, beyond 1.5 um, gives
a **surround control from the same frame, same tip, same tune** -- which turned
the measurement from "is the panel mixed?" into "is the panel different from its
surroundings?", a question with an internal control and a much better answer.

**The standing rule.** Three lengths have to be compared before any windowed
readout, and only two of them were:

    estimator window   >= 4 Lambda        (or use an estimator without that need)
    estimator window   <= the written feature       <-- THIS ONE WAS MISSING
    frame              >= feature + margin for a control region

**Same family as 19.11 and 19.15.** In all three a ruler was applied over a
region it did not fit, produced self-consistent numbers, and the numbers were
believed because they agreed with each other.

---

## 21. New probe, 29 August: six ways to measure a direction that is not there

The new probe resolves structure inside the super-domain lamellae, so the
campaign now needs an estimator that can ask "is there a periodic structure at
THIS length scale, in THIS direction?" and be trusted when it says no. Building
one turned up six separate ways to get a confident wrong answer. Every one was
caught on synthetic fields with known answers; none of them cost instrument
time. **The negative controls did all the work: a positive control only proves
the estimator can see something that is there.**

### 21.1 Fixed angular bins report a direction in pure noise

The first version binned FFT angles into 180 fixed bins and called
`peak / median` the anisotropy. On a field of pure Gaussian noise it returned
**anisotropy 10.3 and "direction found"**.

The super-domain band at 2.5 um / 512 px is a thin low-q annulus holding only
~800 FFT pixels. Split 180 ways that is four pixels per bin, and peak/median is
measuring which bin got lucky. The nano band, with 30 000 pixels, was fine --
which is why the bug was invisible in the band anyone would have tested first.

**Rule.** Bin count follows from the pixel count in the band, never a constant:
`nang = clip(npix / 12, 24, 180)`.

### 21.2 A permutation null must preserve everything except the thing under test

Three nulls were written before one was correct.

| null | what it destroyed | result |
|---|---|---|
| permute power across the whole band | the radial fall-off of power with q | p = 0.005 on **everything**, including noise |
| permute within q-rings | the angular correlation from window leakage | null 7 % too flat; p = 0.005 on noise again |
| **isotropic surrogate built in image space** | only the direction | correct |

The first two are the same mistake in different clothes: the surrogate was
built in FOURIER space, so it could not reproduce artefacts introduced by the
pipeline itself -- the Hanning window's spectral leakage, the square grid's
angular sampling, the q^2 weighting, the binning, the smoothing. **Build the
surrogate in the same space as the data and push it through the identical code
path.** An isotropic Gaussian field with the data's own radial spectrum carries
every artefact the data carries and no direction.

**The tell was that the null was too GOOD.** A p-value of 0.005 on five
different noise seeds is not a strong result, it is a broken test. A working
significance test returns a spread of p-values on null data.

### 21.3 The Hermitian twin

`P(k) = P(-k)` for a real image, so every FFT pixel has an identical twin at
angle + 180 deg. Folded mod 180 the twins land in the SAME angular bin and
reinforce each other; any permutation scatters them into different bins. That
asymmetry alone makes the null flatter than the data whatever else is done
right. Keep one representative of each pair -- a half-plane mask -- and the
profile SHAPE is unchanged while the test becomes fair.

### 21.4 A power-weighted centroid is dragged by the noise floor

`band_period` originally took the power-weighted centroid of q over the band.
On synthetic data with a true 45 nm modulation it returned **28 nm at moderate
SNR -- a 38 % error that looks like a physical result**, because the broadband
noise floor occupies most of the band's area and sits at the short-period end.

A binned, smoothed, parabolically-refined **peak** returns 44.6 nm across a 15x
range of SNR. Errors of this kind are dangerous precisely because they are
smooth: the number moves with SNR, so it will happily produce a "trend" of
period against dose that is really a trend of period against signal strength.

### 21.5 The second harmonic is not a second structure

The first real frame reported a strong short-period feature at **119 nm**, and
the untested detector in `block0_probe.py` called it "NANO-DOMAINS RESOLVED".
The super-domain period on that frame is **219 nm**, and 219/2 = 110.

A lamellar stripe pattern is not sinusoidal, so it has harmonics. The harmonic
sits at HALF the period and at the SAME director -- which is the check: the
90-150 nm band returned 83 deg against the fundamental's 76.8 deg. A genuinely
independent nano-domain family has no reason to share the super-domain's
direction and half its period.

**Rule.** Before calling a short-period feature a separate structure, require
all three: significant, more than ~12 deg off the fast scan axis, and NOT
within 25 % of half the super-domain period at the same director.

### 21.6 "The period tracks the analysis band" identifies broadband artefacts

The same frame showed a significant direction in every fine sub-band -- and the
period it reported moved with the window:

| band | reported period | direction |
|---|---|---|
| 18-40 nm | 38 nm | 179.5 deg |
| 30-60 nm | 58 nm | 178.5 deg |
| 45-90 nm | 86 nm | 174.5 deg |
| 60-120 nm | 114 nm | 175.2 deg |

**A real periodicity returns the same number whatever window is used to look
for it.** A period that tracks the band centre means there is no characteristic
length at all -- only broadband power along one direction, here within 6 deg of
the fast scan axis. Note that `streak_index` read **0.019**, far inside its 0.10
gate, so the campaign's existing streak test does not catch this: it is looking
for line-to-line offsets, not for structure elongated along the fast axis.

This matters beyond the artefact. **M23's open question is whether the ~15 deg
triad member is favoured because it lies nearest the fast scan axis**, and this
frame shows the lateral channel does carry scan-borne structure at ~0 deg. It
is evidence for the instrumental branch of M23 and raises the priority of the
60 deg scan-rotation test.

### 21.7 Piping a long instrument run through `grep` blinds the monitor

`python -u ... | grep -avE "Igor"` was launched as a tracked background task.
`python -u` is unbuffered but **grep is not**, so 25 minutes of run produced one
line of visible output and the interim state was unreadable. The run was fine;
the visibility was not.

Redirect the raw stream and filter when READING it. This is the mirror image of
20.1: there the job could not wake the agent, here the agent could not see the
job.

### 21.8 An "incommensurate" control must be incommensurate by more than the readout can resolve

The whole point of the second queue job was to separate two explanations of the
modulation that appears after a write: a passive imprint of the alternating
bias, or a cooperative response that needs q = Q. The control wrote a template
with a sign period of **328 nm into film whose own period is 253 nm**, at
matched dose, and the analysis then asked whether the modulation sat at the
template period or the film period.

It cannot answer. The analysis window is the 1.0 um panel interior, so its
frequency resolution is

    dq_min = 1 / L = 1 / 1.0 um = 1.00 /um

and the two candidate periods are separated by

    dq = 1/0.253 - 1/0.328 = 3.95 - 3.05 = 0.90 /um

**0.90 < 1.00.** The template period and the film period are inside ONE
resolution element; the matched filter leaks 10.5 % of one into the other and
no window this small can tell them apart. The verdict the script printed --
"that is an IMPRINT" -- was produced by an experiment with no power to
distinguish the alternatives, which is exactly the fault of 12.3 and of the
underpowered gap test in M21.

**The rule, and it applies to every commensurability experiment.** Before
writing an incommensurate control, check

    |1/Lambda_template - 1/Lambda_film| * L_window  >  1

and prefer a ratio that is not a low-order rational, since a 3:2 or 2:1
template can still couple through a harmonic. **q/Q = 1.618** is the ratio least
well approximated by low-order rationals, and at Lambda ~ 250 nm it gives
dq = 2.5 /um -- two and a half resolution elements.

The seductive part is that the flawed control **looked** decisive: a clean
z = +15.7 at p = 0.008. The number was real. It just did not mean what the
script said it meant.

### 21.9 At 2.5 um with a 1.2 um panel there is no far-field control in the frame

The in-frame control is four 0.62 um corner patches. The panel spans 0.65 to
1.85 um, and a corner patch spans 0 to 0.62 um, so the nearest corner pixel is

    0.65 - 0.62 = 0.03 um = **30 nm** from the panel edge.

That is not a control, it is the panel's near field, and it shows: at the
highest dose written (sigma 263) the corner matched-filter amplitude moved by
+31 % in LDART and +81 % in VDART, while at lower doses the same corners were
stable to a few per cent.

There is no way to fix this inside a 2.5 um frame that also holds a 1.2 um
panel and a 4-Lambda interior window: the border is only 0.65 um wide and all
of it is near field. **The control has to come from somewhere else** -- the
before-frame of a different area, a dedicated unwritten frame, or a no-write
null run at the same area (which is what the next queue does).

Note what does NOT work as a control: comparing |S| in the corners. |S| is an
amplitude and drifts with tune and contact between separately-tuned frames --
that is the whole reason the campaign scores DIRECTION rather than amplitude
(C36). Corner |S| moved by up to 69 % across before/after pairs where the
matched-filter direction was rock stable.

### 21.10 `dwell()` per raster point costs 3 travel points for every 1 of dose

The poling square is a 1.4 um raster at 30 nm line pitch, 6674 biased points,
4.4 minutes of actual dose at 0.5 um/s. Built as one `dwell(n=1)` per point it
came out at **26 790 points and 17.9 write-minutes** -- over the S24 headroom
and nearly over the S7 per-iteration cap.

`TrajectoryBuilder.dwell()` makes each call its own SEGMENT, and `to_arrays()`
inserts a resampled travel move between consecutive segments. At a 20 nm step
with points 20 nm apart, every payload point therefore drags roughly three
travel points behind it. The same geometry built with `stroke()` -- one
polyline per raster line, resampled once along its length -- is **7050 points
and 4.70 minutes**, a 3.8x saving for an identical dose.

**Rule.** Anything that moves continuously (a raster, a trace, a spiral) is a
`stroke`. `dwell` is for genuinely stationary pulse sites, where the travel
between them is unavoidable and the n pulses at one spot are the point.

**And check the delivered dose against the BUILT path, not the design
formula.** `sigma = V / (pitch * speed)` gave 667 while the built path was
about to deliver 5467 -- an eightfold error -- because the formula assumes the
tip crosses each area element once and the per-point construction crossed it
four times. The driver now sums `|V| * STEP / SPEED` over the actual arrays and
prints that. Same family as PITFALLS 19.2 and the write-time gate in 20.0:
a quantity estimated from geometry rather than measured from the thing that
will actually run.

### 21.12 The 4-Lambda gate lived in one driver and not the other

`block1_write.py` measures Lambda at each area, computes how many periods the
readout window holds, and refuses or warns. `block2_pole.py` -- written later,
for the poling experiments -- does neither. On the last write of the session
the poled square was shrunk from 1.4 to 1.2 um to fit the remaining budget,
into an area whose Lambda is 369 nm. The 1.0 um interior therefore held
**2.7 Lambda**, and the readout came back at p = 0.28 and p = 0.35: a wasted
write and an inconclusive test of a pre-registered prediction.

Two separate mistakes compounded, and both are generic:
* a **validity gate implemented per-driver rather than per-measurement**, so a
  new driver silently starts without it;
* **shrinking the written feature to fit a budget** without re-checking the
  readout that depends on its size. The dose was preserved exactly; the
  measurability was not, and only the dose was being watched.

The gate belongs in the analysis helper that every driver already imports, not
in the drivers.

### 21.11 Two distances compared to each other instead of to their nulls

The variant-superlattice rescue for M28 was tested by sweeping the structure
tensor's smoothing length and asking, at each scale, whether local directors
sat closer to an allowed triad member or to the commanded angle. The numbers
at 10 nm smoothing were **15.7 deg to the nearest member** and **26.0 deg to
the command**, and the obvious reading is that the members win -- which would
have confirmed a fine superlattice of allowed variants and made a very
attractive story.

**15.7 deg is what RANDOM directions give.** For directions uniform on
[0, 180) and three members 60 deg apart, the median distance to the nearest
member is **14.94 deg** by construction. The median distance to a single fixed
angle is **44.95 deg**. Against those baselines the same two numbers read the
opposite way: +0.8 deg vs the null for members (nothing) and -18.9 deg for the
command (strong). At every smoothing length from 60 nm down to 10 nm the data
cluster on the command and never on the members.

**The rule.** A distance to the nearest of N allowed states has a floor set by
N and their spacing, and that floor is often close to the values real data
produce. Never compare two such distances to EACH OTHER; compare each to its
own null. The null here is one line of code:

    t = rng.uniform(0, 180, 400000)
    null_member = median(min over members |t - m| mod 180)

**Why it nearly worked.** The wrong reading was the physically attractive one:
a ferroelectric cannot polarise along a forbidden direction, so a fine mixture
of allowed variants is what one WANTS to find, and the numbers appeared to show
a clean crossover from envelope to variants as the smoothing dropped. The
crossover was real; what changed across it was the command-clustering weakening
from -37 to -19 deg, not member-clustering appearing.

Same family as 12.3 and 21.8: a comparison quoted without the baseline that
makes it a comparison.

### 21.13 No area gate has ever looked at the topography

Every area gate in this campaign is computed from the LATERAL channel:
modulation, streak index, Lambda, tile spread, flip rate. **Not one of them
reads the height channel.** On 29 August the operator looked at the first frame
of a new stage position and said, immediately, that it sat on a large step edge
-- visible at a glance in topography, invisible to every gate the loop runs.

Quantified on that frame against two areas that worked:

| | plane-removed roughness | 1-99 % peak-to-peak |
|---|---|---|
| the bad area | **3.28 nm** | **19.9 nm** |
| a good area (yesterday) | 0.60 nm | 3.6 nm |
| the M26 poling area | 0.39 nm | 1.8 nm |

Five to eight times rougher, five to eleven times the height range. This is not
a subtle call.

**Why it matters more than it looks.** The lateral signal is cantilever
TORSION. On a slope the tip experiences a lateral force that has nothing to do
with piezoresponse, so a step edge injects a spurious in-plane signal with a
direction set by the edge -- and the edge is a straight line, so it injects a
DIRECTIONAL one. That is precisely the quantity every result in this campaign
is built on.

**The gate**, now in `screen_areas.py` and wired into the write drivers:

    plane-removed roughness <= 1.0 nm   AND   1-99 % range <= 5.0 nm

which separates the good areas from the bad one by a factor of three either
way.

**What does NOT work, tried first:** bimodality of the height histogram. A step
edge should give two populations, and it does -- but so do perfectly good
areas, because the domain structure itself corrugates the surface. The
bimodality test flagged the good frames and the bad one alike. Roughness and
range discriminate; cleverness did not.

**The general lesson.** Every gate in this campaign was added in response to a
failure, and they are therefore all gates against failures that had already
happened. Nothing was screening topography because topography had never yet
bitten. The operator caught it by LOOKING at the data in a channel the
automation never opens.

### 21.14 `rm -f autoloop.lock` as a reflex, and two processes on one instrument

Every instrument launch this session began with `rm -f autoloop.lock`, because
a previous crash had once left a stale lock behind. On 29 August at 18:23 one
of those launches removed the lock that a **still-running** `block0_probe` was
holding, and a `screen_areas` run started on top of it. For five minutes two
python processes wrote the aespm command file that drives Igor.

The symptom was not an error. It was an area screen that appeared to take seven
minutes over a 2.1-minute frame, with no new file landing. Nothing crashed;
the commands simply interleaved. Both runs had to be killed and both their
frames discarded.

**The lock was not the problem. Clearing it unconditionally was.** A lock that
is routinely deleted before every run is not a lock, it is a file.

The fix is `instrument_free.py`: enumerate running python processes, look for
any of the known driver names, refuse to start if one is alive, and clear the
lock only when none is. Every launch becomes

    python instrument_free.py && python my_driver.py

so the check cannot be forgotten, and a genuinely stale lock still clears
automatically.

**The general shape of this mistake.** A guard fires spuriously once; the
operator adds a blanket override to get past it; the override then runs on
every subsequent invocation, including the ones where the guard was right.
Overrides must be conditional on the reason the guard fired, never on the
inconvenience of the guard.

### 21.15 A figure was generated, then never referenced, and nothing complained

`make_ms_figures.py` built six panels; `MS_main.md` carried five image
directives. **F4, the AC-versus-DC figure that carries the paper's only
mechanistic discrimination, was missing from the text.** The converter printed
`MS_main.md -> MS_main.docx (5 figures)` and exited 0, because it counts
directives it found, not figures it should have found.

Caught only by comparing `figures_ms/*.png` on disk against the directives in
the markdown.

**Rule.** Before any document build, diff the two sets:

```bash
diff <(ls figures_ms/*.png) <(grep -aoE '\]\([^)]+\)\{width' MS_main.md MS_supp.md | sed 's/.*](//;s/){width//' | sort -u)
```

A figure on disk with no directive is an unreferenced figure; a directive with
no file is a broken link. The build should fail on either, and reporting a
count is not the same as checking one.

### 21.16 A caption written from memory described panels that do not exist

The first caption placed under F4 described five panels — "(a–c) lateral
piezoresponse … (d) angular power … (e) anisotropy before and after". **The
figure has three.** The caption was written from what the section argued rather
than from the rendered image, and it invented a panel-by-panel structure to
match.

Nothing in the build catches this: the converter embeds the PNG and the caption
as independent objects, and a caption that describes a different figure renders
perfectly.

**Rule.** Open every figure before writing or editing its caption, and count
the panels. A caption is a claim about an image and gets checked against the
image, like any other claim against its raw data.

### 21.17 The Bash tool's heredoc eats backslash escapes

`python - <<'PYEOF'` with a *quoted* delimiter should pass the body through
literally, and in a normal shell it does. In this environment it does not: a
`\n` written inside a Python string literal in the heredoc body arrives as a
real newline, producing

```python
    print('
' + '-' * 82)          # SyntaxError
```

Two other forms fail as well: `python -c "..."` containing `|=` or spanning
multiple lines came back with `|| goto :error` and an `IndentationError`,
i.e. the payload was routed through a cmd.exe wrapper.

**Rule.** For any patch script containing `\n`, `\`, `|=`, or more than a
couple of lines, use the Write or Edit tool rather than a heredoc, and run
`python -m py_compile` on anything a heredoc did write before trusting it.
Heredocs remain fine for plain-text appends like this one.

### 21.18 A speed the instrument may not be able to deliver, and no way to tell

Round 3 was first designed with a 2.8 um/s raster, to reach the point-pulse
lattice's dose at the reference 30 nm pitch. The trajectory STEP is 20 nm, so
that asks the Igor litho engine for **140 points/s against the 25 points/s
this campaign has ever driven**.

The failure would be silent. `run_traj` computes `dur = npts * step / speed`,
issues `TL_RunPy`, sleeps `dur + margin`, then calls `exp.execute('Stop')`. If
the engine runs slower than commanded, the Stop lands **part-way along the
path**: the square is written incompletely, the delivered dose is neither the
commanded value nor the recorded one, and every downstream check passes,
because `run_traj` validates the trajectory FILE and not the instrument's
response. This is the same shape as the 14 Aug bug that cost 70 write-minutes.

Replaced with 60 nm pitch at 1.0 um/s (sigma 171, dose-matched to the 120 nm /
0.5 um/s point within 4 %), a 2x extrapolation rather than 5.6x.

**Rule.** Any parameter more than about 2x outside the range the campaign has
actually run is an untested regime, not a bigger number. Either stay inside it,
or add a check that would catch the failure -- here, comparing the written
square's coverage in the after-frame against the commanded geometry.

### 21.19 A gate that returns a tuple, called as if it returned a bool

`scale_tools.window_ok()` returns `(ok, n_periods, message)`. A new driver
called it as

```python
if not ST.window_ok(lam, WIN_UM, label='tile readout'):   # WRONG
```

A non-empty tuple is always truthy, so `not (...)` is always `False` and **the
4-Lambda gate never fires**. The script would have run happily on an area whose
period cannot be read in the window it uses, which is exactly the fault
21.12 and S2.4 were written about — the same gate failing for a new reason.

Caught by reading the signature before trusting the call, not by testing: there
is no test that distinguishes "gate passed" from "gate never asked".

**Rule.** When calling a validity check, read its return signature. A gate that
cannot fail is not a gate. Where practical, have such helpers return a value
that is falsy on failure *and* raise on obvious misuse, so the mistake is loud.

### 21.20 "Spread" reported as twice the largest residual, not as the range

The clustering of the written directions modulo 60 deg was first quoted as a
spread of **6.51 deg**, computed as `2 x max|residual from the circular mean|`.
That is not the circular range, and for six points it overstated it: the true
smallest arc containing all six is **5.81 deg**.

The number then went into a p-value, `n (L/60)^(n-1)`, whose L must be the
range for the expression to be the CDF of anything. With the wrong L the
p-value came out 9.0e-5 instead of 5.1e-5 -- conservative in this case, but
wrong, and it would not have been conservative had the points been asymmetric
about their mean.

Both were checked against 4 x 10^6 Monte Carlo draws (`check_arc_p.py`), which
reproduced the analytic value to within 4 standard errors. That check is cheap
and should be the default for any closed-form p-value: PITFALLS 21.2 and 21.3
are both cases where a p-value came from an expression that did not match the
null it was supposed to describe.

**Rule.** When a statistic feeds an analytic p-value, compute the statistic the
formula assumes -- and simulate the formula once before quoting it.

### 21.21 Evidence from one tool used to constrain the mechanism of the other

The mechanism section listed "replacement rather than rotation, no transient
power at intermediate angles" among the observations constraining the **raster**
mechanism. That observation is M17, and M17 was measured on a **point-pulse
lattice** panel.

The manuscript's own conclusion is that the raster and the lattice do different
physics -- one selects a variant, the other writes a pattern. Once that is the
claim, evidence from the lattice cannot be used to constrain the raster's
mechanism, and doing so quietly assumes the thing section 4 spent its length
disproving.

Replaced with the raster's own version of the same argument, which is available
and in fact stronger: across six raster runs the director is only ever found ON
a triad member and never between two, including three runs commanded at
forbidden angles, and the single partially completed case comes back 2.83 deg
short WITH REDUCED ORDER rather than at a sharp intermediate angle.

Also note that M17's original phrasing -- "no transient power at intermediate
angles" -- overstates its own design: with only a before frame and an after
frame there is no time resolution to see a transient, so what it excludes is a
*stalled* rotation, not a fast one.

**Rule.** When a paper's thesis is that two tools differ, audit every
cross-tool inference. Tag each observation in a mechanism section with the tool
it came from before using it.

### 21.22 Measuring the distance from a non-significant direction to something

Having established a single film-wide triad, the obvious next question is
whether the AS-GROWN state sits on it. Computing it gave a clean-looking
answer -- before-states a median 14.5 deg from the nearest member, after-states
1.8 deg -- and the conclusion "the as-grown film is not on the triad; the write
puts it there" was one edit away from the manuscript.

It is not a result. **Five of the six before-states have p = 0.08-0.65**, which
is the estimator saying *there is no direction here*. The number it returns in
that case is the argmax of a noisy profile, and its distance to a triad member
is a distance from noise to a fixed set of angles. That distance has an
expectation of about 15 deg for three orientations 60 deg apart -- which is
exactly the 14.5 deg "measured", and exactly the trap of PITFALLS 21.11, where
15.7 deg was quoted as a result and 14.94 deg is what random directions give.

The one before-state that IS significant is the re-aim's starting state, and it
had itself been written, so it says nothing about as-grown film.

**Rule.** A director with p > 0.01 is not a director. Never use it as an
endpoint of a distance, an input to a mean, or a term in a correlation. If a
before/after comparison needs the before-state to have a direction, check that
it does before making the comparison -- and if it does not, the honest output is
"not measurable here", not a number.

### 21.23 Per-row values written into a table that the script only summarised

`vdart_check.py` printed a per-run raw delta and a *summary* of the thresholded
one (median +0.001, range -0.022 to +0.045). The SM table was then written with
a per-run thresholded column filled in from what those numbers "must have
been" -- +0.004, +0.000, +0.001, +0.045, -0.022, +0.000, +0.002.

Four of the seven were wrong. The real values are -0.022, +0.002, +0.005,
+0.045, -0.004, -0.000, +0.001: the -0.022 belongs to a different run than
assumed, and so does the -0.004.

The summary constrained only the median and the extremes; everything else was
reconstruction. It looked harmless because the conclusion does not change.

**Rule.** Every number in a table comes from a line the script actually
printed. If a per-row value is wanted, change the script to print per-row
values and re-run it -- which costs a minute -- rather than inferring the rows
from a summary.

### 21.24 A one-panel effect that the null, run afterwards, erased

The out-of-plane analysis found the 1600 nm AC write shifting its interior's
polarised fraction by -0.137, three times more than any of the seven
charge-balanced rasters (<= 0.045). It had an excellent mechanism attached: an
AC write is neutral in SPACE and can pole locally over its 800 nm same-sign
strokes, while the raster is neutral in TIME and cannot. It was written into
the main text, the SM and FINDINGS as "the first direct evidence" for the
assumption section 3.1 rests on.

Then the null was run -- the same statistic on two halves of the UNWRITTEN
surround, which cannot have changed. **Its maximum is 0.127.** The effect and
the null are the same size, and the claim is withdrawn.

The same run showed the *other* statistic from the same script, the
interior/surround response ratio, sitting at 2.94 against a null of 0.81-1.08.
One of the two numbers was meaningful and the other was not, and nothing about
either -- not the size, not the consistency with a mechanism, not the fact that
they came from the same frames -- distinguished them beforehand.

**Rule.** Run the null FIRST, not after the claim is drafted. For any statistic
computed on a written region against a reference, there is almost always a
free null available by applying it to two unwritten regions of the same frame.
Cost: minutes. This is the third time in the campaign a clean-looking result
has failed its own null (see 21.11, 21.22).

### 21.25 Live scoring against a reference the analysis has already discredited

`block3_raster.py` prints a verdict at the end of every write -- "ALIGNED to
the member nearest the raster. Rule holds." or "did NOT go to the member
nearest the raster." It computes that verdict against the **per-area as-grown
triad fit**.

M39 established that this fit carries no information about where a write lands
(r = -0.19 over six writes, +0.19 over eleven, permutation p ~ 0.6-0.7). The
driver was still scoring against it.

The cost was nearly a wrong conclusion. Round 3's speed control at (-6,-12) was
reported as a FAILURE: the area's fit puts members at 9/69/129, so the nearest
member to the commanded 41 deg is 69, and the film went to 17. Against the
film-wide triad (18.32/78.32/138.32) it is a clean hit with a 14.6 deg margin,
and the draft paragraph beginning "doubling the scan speed breaks the rule" was
already being composed.

**Rules.**
1. When an analysis retires a reference, grep for every consumer of it. A
   driver that prints a verdict is a consumer.
2. Treat live, in-run verdicts as advisory. The verdict a driver prints at
   3 a.m. is computed from whatever was believed when the driver was written.
3. Prefer drivers that print the raw quantities and defer the verdict to the
   analysis that will actually be cited.

### 21.26 One commanded angle applied to areas with different triads

`run_round3.py` commanded 41 deg on every area in its queue. Against a
16/76/136 triad that is 25 deg from one member and 35 from the next -- a clean
test of "nearest". Against the 9/69/129 triad of one of the areas it is 32 and
28 -- decided by 4 deg, which is smaller than the uncertainty on the reference
itself.

The result was an apparent failure of the selection rule that was really an
ill-posed test, and it took a repeat on a matched triad to resolve.

**Rule.** Choose the commanded angle per area, from that area's geometry, so
that the margin between the nearest and second-nearest member is comfortably
larger than the reference uncertainty. Print the margin alongside the
prediction so an ambiguous test announces itself before it is run, not after.

### 21.27 The written square rotates with the commanded angle

`tile_boundary.py` was designed to abut two 1.6 um squares at a shared edge:
write at X-0.8 and X+0.8, read a frame at X, put a window in each half.

`block3_raster` builds its serpentine over a square **rotated to the commanded
angle**. The 0 deg tile is axis-aligned and 1.6 um wide; the 60 deg tile is a
rotated square with a bounding box of 1.6 x (cos60 + sin60) = **2.19 um**. The
two do not tile: they overlap in a wedge and leave gaps elsewhere, and the
readout window for the rotated tile had its corners outside the written region.

The trajectory extent was in the log the whole time --
`X[0.192,2.343] Y[0.157,2.323] um` for the rotated tile against
`X[0.450,2.050] Y[0.450,2.010]` for the axis-aligned one -- and was not read.

**A correction to this entry.** It was first written as the explanation for a
wrong boundary reading, in which both tiles came out on the same member
0.50 deg apart. That was NOT the cause: the frame being analysed had been taken
by another process at a different area entirely (21.29). The rotated-square
geometry is real and does prevent the two squares from tiling, but it did not
produce the symptom it was blamed for. Two true facts, one wrong causal link.

**Rules.**
1. Read the trajectory's printed bounding box before believing any geometry
   built on top of it.
2. To read a rotated written region, rotate the frame by minus the commanded
   angle and use an axis-aligned window inside it (`tile_reread.py`).
3. Tiling regions written at different angles needs a writer that clips the
   raster to a fixed square, which this one does not do.

### 21.28 A rotation sign guessed instead of measured

The fix for 21.27 rotates the frame by -ang and converts the measured director
back to the laboratory frame. The conversion was written as `theta + ang`.

It is `theta - ang`. With the wrong sign the correct 78.8 deg came out as
18.8 deg -- identical to the neighbouring tile -- which is exactly the wrong
answer the whole exercise was meant to correct, and it looked consistent with
the (also wrong) boundary-frame reading.

Settled in one minute by pushing synthetic fields of known direction through
the identical code at two angles.

**Rule.** Never reason about a rotation, reflection or transpose convention.
Put a known input through the code and read the output. This applies equally
to `ndimage.rotate`, FFT axis order, and the director/wavevector convention of
PITFALLS 21.x -- three separate 90-or-more-degree sign errors in this campaign
so far.

### 21.29 Two processes on the instrument again, and a frame read from the wrong area

**This is 21.14 recurring through a different hole, and it produced a fully
formed wrong result that was written into the manuscript before it was caught.**

The tiling driver `tile_boundary.py` was still running its final readout when a
queued retention job polled `instrument_free.py`, was told "no driver running",
and started scanning. `instrument_free.py` decides by matching process command
lines against a hard-coded `DRIVERS` tuple, and `tile_boundary` was not in it.

The tiling script then called `tune_here` at (-6,-18), scanned, and read back
"the newest frame" -- which was **PZTO_LDART_0110, taken by the retention job at
(+12,+18)**. That area had been written at 41 deg and sits on member 18, so both
of the script's "tile windows" reported ~18.8 deg, 0.50 deg apart.

The failure was invisible in every way that matters:

* both windows returned significant directions (p 0.0025);
* the numbers were mutually consistent;
* the script's own verdict logic fired correctly on the data it had;
* and a *plausible physical explanation was available and wrong* -- the raster
  square really is built rotated to the commanded angle (21.27), so "the
  rotated tile's window fell outside its written square" fitted the symptom
  perfectly. That explanation was written into FINDINGS, PITFALLS and the
  manuscript before the frame headers were checked.

Only the frame headers settled it: 0110 has XOffset +12.00, YOffset +18.00.

**Rules.**
1. **Check the header offsets of every frame before analysing it.** A frame
   knows where it was taken; nothing else in the chain does. Drivers that
   compare a requested position against the returned frame's header cannot
   have this failure at all. `tile_boundary_read.py` now refuses to analyse a
   frame that is not where it asked to be, and this should be moved into the
   shared toolkit.
2. Do not identify "a driver is running" by a list of names. Every driver
   should hold `autoloop.lock` for its whole life, so membership of a list
   stops mattering. Until that is done, adding a driver means adding it to
   `DRIVERS` in the same commit.
3. Reading back "the newest file in the folder" is only safe under an
   exclusive lock. Otherwise match the file to the request.
4. When a wrong result has a ready explanation, check the plumbing before
   accepting the physics. The rotated-square story was true, elegant, and not
   the cause.

### 21.30 Rewriting a section silently deleted its figure

Section 3.7 was replaced wholesale to fold in the second and third re-aim
pairs. The replacement text was written from the new tables and **the figure
directive that lived inside the old section went with it**. The document built
cleanly and reported "6 figures" where it had reported 7.

Caught by `check_figs.py`, which compares the PNGs on disk against the
directives in the markdown and calls an unreferenced figure an ORPHAN. That
script exists because of 21.16, where a figure was built and never placed; it
now also catches a figure that was placed and then lost.

**Rule.** After replacing a whole section, run the figure check. More
generally: a build that reports a count is not a build that checks one, and any
count that can change silently needs an assertion somewhere.

### 21.31 A verdict rule that conflates two questions

`retention_raster.py` ends with:

    if median(drift) <= 10 and n_significant >= 0.8 * n:
        "THE WRITTEN DIRECTION HOLDS"
    else:
        "the written direction does NOT hold; report the drift"

Run on three panels of which one was *written* weak, it printed **"the written
direction does NOT hold"** while every director in the batch had moved by
0.0-0.1 deg. The failing condition was significance, not drift, and the message
says drift.

Retention of a direction and significance of a state are different questions.
Compounding them into one boolean produces a headline that contradicts the
table printed immediately above it -- and a headline is what gets read at
5 a.m.

**Rule.** One verdict per question. If a script must summarise, it reports each
criterion and its own outcome; it does not AND them into a sentence that names
only one.
