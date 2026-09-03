# Where to pick up

Written 22 Aug 2026, 08:25, at the end of the overnight autonomous run.
Read `FINDINGS.md` and `PITFALLS.md` first; this file only says what to do next.

## State

- **No driver running, no lock, nothing holding the instrument.** State saved:
  iteration 8, 164.6 min written of a 330 min cap, 6 areas used, 0 strikes.
- Areas used (12 µm frames): (0,0) (−14,0) (0,−14) (0,−28) (−14,−28) (−14,−14),
  plus IT7 screened and rejected (−28,−14) and IT9 wrote (−28,−12).
- Notebook has eight autonomous iteration cells, IT1 → IT9, correctly tagged.
- 54 numbered conclusions; C44 withdrawn.

## Ready to run, already audited and simulated

Both were built, statically audited, simulated against real frames, and had
their verdict branches exercised against synthetic results. Neither has run.

| driver | question | write | note |
|---|---|---|---|
| `run_it7.py` | lattice axis, or sign boundary? (**Q19**) | 15 min | halted 22 Aug on the flip gate — needs an area whose populations are *not* near-degenerate (C52) |
| `run_it8.py` | is strength set by sign-boundary density? (**Q21**) | 15 min | IT3's numbers are the quantitative prediction |

Both at σ = 0.9 σ_c deliberately (C47: the response saturates, so a lower dose
leaves headroom for a difference to show as a difference).

## The three things most worth doing

1. **Q28 — the sharpest contradiction in the theory.** A spatially uniform-sign
   *raster* gives the largest alignment in the campaign (C49, +0.186); a
   spatially uniform-sign *lattice* does nothing at all (C43, 0.2× and −0.5×).
   Both cannot be right about the mechanism. Discriminating experiment is cheap:
   a raster with sign alternating between **adjacent lines** against one
   alternating only **between passes**, plus a lattice at the raster's line
   pitch.
2. **Q31 / C54 — the command is not always followed.** IT9's RW panel was
   commanded to 4°, cleared the threshold at 3.4×, and ended on 124°. This is the
   ceiling on patterning fidelity and why C51's letters read 63 % on-target
   rather than 100 %. Command one starting director to each of the other two
   members, twice each, in one frame: if 4° always loses it is the direction, if
   the loser follows the starting member it is the history.
3. **Q29 — does a lattice-written state decay?** C50: a raster-aligned state was
   flat over 34 min. C53: a lattice-written one fell 0.696 → 0.609 in ~22 min —
   but its control panel sat 0.1 µm from a second write, so decay and
   perturbation cannot be separated. Repeat with the control far from anything.

## Fixes to make before the next run

- **`run_it9.py` has no baseline flip gate.** IT7 halted on exactly that check
  and IT9 lacks it. Copy the `FLOOR_MAX` / `FLIP_MAX_PRE` block from
  `run_it7.py`.
- **`run_it9.py` stage-1 print says "SWITCHED" on excess alone**, without
  checking the dominant landed on target. It labelled RW switched when it had
  gone to the wrong member (C54). The verdict block is correct; only the
  intermediate line lies.
- **IT9's two panels were 0.1 µm apart** edge to edge. Any retention control
  must be far from a later write.
- **`run_it5.py`, `run_it7.py`, `run_it8.py` lack the `Tee` flush**, so their
  progress is invisible until they exit. One-line fix, already in
  `run_it6/9/10*`.

## Operator notes

- The **terrace edge** is real: −2.2 nm step at x ≈ 4.4 µm in the (0,−28) frame,
  42 nm peak-to-peak, and up to 107 nm across some candidate boxes. Drivers now
  rank candidate areas by height range and record topography under each panel
  before writing.
- `contact_check` has warned "RETUNE HERE / bad contact spot" repeatedly since
  IT2. It is **not** tracking readout quality: tile spread was flat at
  0.081–0.109 across IT3–IT7 (C52). Treat that warning as a hypothesis, not a
  verdict.
- A probe change would still be reasonable before a long run: |A| has drifted
  40–55 pm down to ~29 pm and the DART loop reads ~19 kHz off resonance.
