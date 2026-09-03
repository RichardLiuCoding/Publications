# START HERE — mission brief for the rewriting campaign

**Read this file first, then the other four, then propose your first iteration.**
Written 22 Aug 2026 at the end of the campaign that wrote "UTK" into in-plane
super-domain orientation. You are continuing that work with a new target.

---

## 1. The mission

**Find the rewriting rules of the in-plane (IP) super-domain director in
PZTO(111): the pathways, the dynamics, the mechanisms, and the limitations.**

Writing is solved. A charge-balanced point-pulse lattice rotates the local
director to a commanded axis, and composing that with a raster produced a
readable "UTK" at 11.1× the measurement null. What is *not* known is what
happens when you write a region **again**:

- **Pathways** — from a given director, which of the other two can you reach,
  and does the film actually go where commanded? (It does not always: see C54.)
- **Dynamics** — how does the transition proceed with dose and with repetition?
  Continuous or abrupt? Does overwriting cost more than writing?
- **Mechanisms** — what does the film couple to? Two strong results currently
  contradict each other (Q28), and the selection rule is unidentified (Q19).
- **Limitations** — fidelity, endurance under cycling, retention, and how small
  a feature can be written and read.

You control the instrument directly and run autonomously, in the same loop the
UTK work used: propose → pre-register → simulate offline → write → read →
record → refine.

---

## 2. Reading order

| file | what it gives you |
|---|---|
| **this file** | mission, protocol, first actions, stop conditions |
| `HANDOFF_1_INSTRUMENT.md` | how to drive the rig, every constraint, the cost model |
| `HANDOFF_2_ANALYSIS.md` | how to score and interpret data — **the single highest-value file** |
| `HANDOFF_3_PHYSICS.md` | what is known, with grades, and what is open |
| `HANDOFF_4_REWRITE_PROGRAM.md` | six designed iterations, ready to build |
| `FINDINGS.md` | the full evidence base: 54 numbered conclusions, one withdrawn |
| `PITFALLS.md` | 18 sections of how this work has gone wrong before |

`FINDINGS.md` and `PITFALLS.md` are long. The four HANDOFF files are the
condensate; go to the sources when a specific conclusion matters.

Also present: `DOC1_process_and_agent.md` and
`DOC2_switching_rules_and_theory.md` (narrative write-ups of the previous
campaign), `NEXT_SESSION.md` (short-form leftovers), and `run_it1.py` …
`run_it10b.py` (nine working drivers to copy from).

---

## 3. The working protocol — follow this exactly

This is not bureaucracy. Every clause below exists because its absence cost an
iteration.

### Before designing
1. Read `FINDINGS.md` §2 (open questions) and `PITFALLS.md` §0 (the seven rules).
2. Check `campaign_state.json`: iteration count, cumulative write minutes, areas
   already used.

### When designing
3. **Pre-register in code**: hypothesis, prediction, and an `outcomes` dict with
   **at least one branch that is uninformative** ("the control also failed, so
   this says nothing"). That branch fired for real on IT4 and is the only reason
   a null was not written up as physics.
4. **State which comparison is primary**, and match the panels for it. If two
   panels must be compared, put them on slots with the same starting dominant
   director. Settle *more slots than panels* so you can select matched ones.
5. Every panel is commanded **60° from its own local dominant**, measured in
   that panel's own window before the write.

### Before writing — three checks, all of which have caught real faults
6. **Static audit**: AST scan for called-but-undefined names across every
   notebook cell the loader execs, plus dangling globals in the driver.
   *Re-run it after every patch* — two faults were introduced by patches.
7. **Key-consistency check**: collect the literal keys the verdict reads off a
   dict, compare against the keys something actually puts there. A dict key is a
   string inside a subscript, so the AST audit cannot see it. This found
   `run_it5.py reads 8 keys off W, builds 27; missing: sigma` — which had
   already destroyed one verdict.
8. **Offline simulation against real frames**: slice the driver's own geometry,
   dose, build, tile and scoring code out of the file and `exec` it against
   frames on disk. Not a reimplementation — the real code. Applied for the first
   time to IT4 it found five defects in one sitting, four of them live for three
   iterations.
9. **Exercise the verdict branches** against synthetic results, once per outcome.
   The verdict runs *last*, after everything expensive is spent, and was the only
   code never tested. Three separate faults lived there.
10. **Gate on the built trajectory, not an estimate.** Travel overhead is 1.35×
    for solid panels and **1.55× for masked lattices**; an estimate passed the
    cap while the real path was 28 min against 26.

### While running
11. **Commit the written area and the write minutes to state the moment
    `run_traj` returns**, in their own `save_state` — not bundled with the
    result. IT2 wrote 512 pulses, crashed before saving, and left a written area
    invisible to every guard for two days.
12. **Flush stdout per line.** A 70-minute run whose progress sits in an 8 kB
    buffer can be neither monitored nor corrected.
13. Write the console to a file in a `finally` clause. Twice that is all that
    survived a crash, and both results were recovered from it.

### After each iteration
14. Log it to `Claude_interactive_notebook_v2.ipynb` via
    `autoloop.log_to_notebook` — markdown cell (motivation, pre-registered
    prediction table, result) plus a code cell (parameters as run, console
    output). Eight iterations are already there as models.
15. Record findings in `FINDINGS.md` with an **A/B/C grade** and an explicit
    statement of what would falsify them. Grades matter: C41 was graded B
    because its *ordering* was robust while its *ratio* was not, and when a later
    iteration reversed the ordering the withdrawal was small because the claim
    had been small.
16. **Withdraw in place.** Five conclusions were wrong; each carries a
    strike-through and the reason. C44 was withdrawn the day it was written and
    its entry is now a worked example of the error that produced it.
17. Add or close open questions in `FINDINGS.md` §2.
18. Append new failure modes to `PITFALLS.md`, organised by *pattern* rather
    than incident.

---

## 4. First three actions in the new session

1. **Confirm state**: no `autoloop.lock`, no `STOP` file, read
   `campaign_state.json`. Report iteration, minutes written, areas used.
2. **Ask the operator two questions** (do not guess):
   - Has the probe been changed? |A| had drifted from 40–55 pm to ~29 pm with
     the DART loop ~19 kHz off resonance. A fresh probe changes what you can
     trust and resets the tip-history baseline.
   - Has the coarse stage moved? If yes, the `used_areas` table in
     `campaign_state.json` is meaningless and must be reset.
3. **Propose RW1** from `HANDOFF_4_REWRITE_PROGRAM.md` — the pathway map. It
   attacks the biggest known limitation (C54: the commanded director is not
   always the one that wins) and every later iteration depends on knowing the
   transition matrix.

Do not write anything to the sample until the operator confirms they have
instrument time.

---

## 5. Stop conditions

Halt and ask rather than pressing on when any of these is true:

- `STOP` file present in the project directory.
- Cumulative write minutes ≥ 330 (`MAX_TOTAL_WRITE_MIN`), or iteration ≥ 12.
- Two consecutive iterations unreadable (`MAX_STRIKES`).
- Baseline tile spread sd(w) > 0.150 — the measured readout-health signal.
- Baseline director-flip rate > 25 % on consecutive frames: the area cannot
  support the measurement, move rather than write.
- No legal fresh area within the scanner range.
- A guard fires that you do not understand. Guards have been right and the
  reasoning wrong more often than the reverse.

**Relaxing a guard is allowed** when (a) the person who owns the risk asks and
(b) the quantity it protects has been measured and is healthy — both, in
writing, with numbers. That is how the write cap went 180 → 330. Never one
without the other.

---

## 6. What "done" looks like

A transition matrix with grades: for each ordered pair of triad members, whether
the rewrite succeeds, at what dose, with what purity, and how it fails when it
fails. Plus an endurance number (cycles before degradation), a retention number
(decay over hours, not minutes), and a resolved answer to Q28 — the contradiction
between a uniform-sign raster working and a uniform-sign lattice not.

That would turn "orientation is writable" into "orientation is a specified,
addressable, re-writable state variable with known limits", which is the
difference between a demonstration and a device.
