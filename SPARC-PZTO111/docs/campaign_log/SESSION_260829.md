# Session of 29 August 2026 — new probe, and the controls that changed the story

**Operator:** new probe fitted, coarse stage moved to a fresh location, new data
folder `260829/PZTO`. Sample position 7.
**Instrument:** LDART 635 kHz, VDART 343 kHz (both MEASURED; the operator's
estimates were 600/320). 100 % of lines tracked in both channels on the first
tune. 2.5 µm frames at 512 px = 4.88 nm/px, 2.0 Hz — half the campaign's
usual tip speed, at the operator's request to preserve the probe.
**Budget:** S24 raised 330 → 350 with the operator's explicit sign-off.
Used 349.5 of 350.

---

## What was asked

1. Keep scans at 2.5 µm to preserve the probe and to see how the IP
   super-domain rewriting changes the **nano-domains**, and what the microscopic
   pathway is. Both LDART and VDART.
2. Design and present a 10-hour schedule for review before execution.
3. Read PITFALLS and FINDINGS, update them promptly.

Mid-session the operator added two things that changed the plan: *"a lot of the
time the nano domains are not visible until you write/align the IP super
domains"*, and *"try a full +V scan and then a full −V scan in the same area,
so the OP domains are homogeneous and it becomes easier to resolve the nano
domains."* The second turned out to be the most important experiment of the day,
though not for the reason it was suggested.

---

## The headline

**The campaign's central claim does not survive its own control.**

Every director ever commanded in this campaign was aimed AT one of the three
symmetry-allowed directions. So *"the film adopted the commanded director"* and
*"a pattern was written along the commanded direction"* predict the same answer
and had never been separated. Commanding the **midpoint between two allowed
directions** separates them — and the readout follows the command, not the
crystal:

| tested at | LDART | VDART |
|---|---|---|
| **commanded 56.5°** (forbidden) | 19.0 → **92.7 pm**, z +5.4 | 14.4 → **123.5 pm**, z +21.1 |
| the three allowed directions | all p ≥ 0.14 | all p ≥ 0.23 |

Two runs, both channels: the commanded direction gains **4.9–8.6×**;
the allowed directions **lose** power, median 0.68×. Three rescues were
tested and all three failed — it does not decay (64–92 % retained after
five hours), it is not a fine superlattice of allowed variants, and it is not
locked to the scan frame (re-imaged with the scan rotated +60°, the feature
moved **+67.5°**, i.e. with the sample).

**What survives, and got stronger:** a **spatially uniform** write — no
periodicity anywhere in it, so nothing to imprint — genuinely reorients the film
onto an allowed direction, and the direction follows the **raster angle**.

---

## Findings recorded

| # | grade | what |
|---|---|---|
| **M24** | B | Virgin film carries NO out-of-plane modulation at the in-plane wavevector: < 5 pm by injection, against 22.3 pm in-plane. The coupling T3's selection term needs is not there to couple to. |
| **M25** | A | Selection "reproduces" on the new probe — 5 panels of 5, median 2.3°. Reported, but see M28: the statistic does not mean what it was taken to mean. |
| **M26** | A | A spatially uniform +V/−V write rotates the director 76° → 16°. Imprint-free by construction. |
| **M27** | A | The modulation at the template wavevector is an imprint: with q/Q = 2.105 it appears at the TEMPLATE period (z +22, +38) and not at the film's (z −0.5, −0.3). No-write null recovered free from 14 corner pairs: median 1.08, max 1.81, against interiors at 10.16. |
| **M28** | A | Commanding a forbidden direction gives a persistent readout at exactly that direction and nothing on any allowed one. The lateral channel reports variant structure on unwritten film and a written pattern inside a panel — two different things read by one instrument. |

**Corrected in place:** M26 first reported the before-state as "no direction at
all, p 0.93". Those were the **VDART** numbers, read off the line above the S24
message without checking the channel. LDART before is a perfectly good direction
on member 76 (aniso 3.44, p 0.046, stable across every `n_perm` and seed). The
result is a clean 60° **rotation**, not disorder-to-order — a stronger claim,
not a weaker one.

---

## The poling rule — the one clean rewriting rule of the day

A +V pass and a −V pass over the same square, written as one file so the net DC
is exactly zero. The polarities are separated in **time**, not space, so the net
spatial charge pattern is uniform and the only spatial period in the write is
the 30 nm raster pitch — an order of magnitude below the band the director is
read in. Nothing periodic exists to imprint.

| raster | director before | director after | nearest allowed to the raster |
|---|---|---|---|
| 0° | 78.8° | **18.8°** | 16° |
| 60° | 63.8° | **78.8°** | 76° |
| 120° | 86.2° (p 0.74, no direction) | 78.8° (p 0.28) / VDART 138.8° (p 0.35) | 139° predicted |

The 120° point is **inconclusive, and the fault is in its design.** To fit
the remaining budget the poled square was shrunk from 1.4 to 1.2 µm, and
this area's Λ is 369 nm, so the 1.0 µm analysis window holds only
**2.7 Λ** — below the 4Λ floor enforced everywhere else today.
`block1_write.py` carries that gate; `block2_pole.py` does not. The VDART
direction after poling is 138.8° against a prediction of 139°, which
is either a nice confirmation or a coincidence at p = 0.35, and at that p it
has to be read as the latter. The rule stands on two points, not three.

Poling at 60° did **not** send the film to the 16° director that poling
at 0° produced. So the preference is not a standing property of the film —
it follows the write. That also answers the open question of M23: the member
asymmetry is set by the write direction.

---

## The nano-domain question

Not resolved as a separate structure, and it is now clear why every search
failed. The fine band is contaminated from both ends:

* lamellar harmonics Λ/2, Λ/3, Λ/4 fall at 50–125 nm at the **same**
  director as the lamellae;
* a broadband instrumental feature sits at ~70–80 nm within a few degrees
  of the fast scan axis in **every** frame, written or not, before and after.

**The phase channel is the better place to look.** On the 60°-poled square
at 2.44 nm/px, Phase1 and Phase2 — two independent DART channels — agree
to **0.0° in direction and 0.3 nm in period** across three bands: 335 nm
(anisotropy 27.7), 65.6 nm (8.2) and **39.8 nm** (4.4). So 40 nm structure IS
resolved, at 16 px. But all three sit at the same director, 78.8–84.5°,
at periods close to the 5th and 9th harmonics of a square-wave lamellar profile.
That is a sharp-walled lamellar stack, not the herringbone of two different
angles in the operator's screenshot.

Poling did **not** make nano-domains visible, contrary to the hope — but it did
make the lamellae far sharper (anisotropy 27.7 against 16.2 for the signed
product), which is why the phase channel is the recommendation.

**The search was then run systematically and returned nothing.** Seven frames
— both poled squares at both scales, a written panel, the off-triad panel and
unwritten film — times three bands (15–45, 45–90, 90–150 nm), each
required to be significant in **both** phase channels, to have them agree
within 12°, to lie >15° off the fast axis and >15° off the
lamellar director, and to have a period not within 12 % of Λ/n for
n = 2…9. **Zero candidates.** Every fine feature in every frame is a
fast-axis artefact, a lamellar harmonic, not significant, or a case where the
two phase channels disagree. On this probe, in these regions, there is no
separate nano-domain family to find.

---

## Method faults found and logged (PITFALLS §20–21)

Eleven, of which three produced confident wrong answers before being caught:

* **21.1–21.3** an angular estimator that reported a direction in pure noise;
  two wrong permutation nulls before an image-space surrogate worked; the
  Hermitian twin that made every null too flat.
* **21.4** a power-weighted centroid that read a 45 nm modulation as 28 nm.
* **21.5–21.6** the second harmonic mistaken for a nano-domain family, and
  the "period tracks the analysis band" test that identifies broadband
  artefacts. `streak_index` does not catch these — it reads 0.019.
* **21.8** an "incommensurate" control that was inside one resolution element
  and could not have decided anything, while printing a confident verdict.
* **21.9** at 2.5 µm with a 1.2 µm panel there is no far-field control
  in the frame; the corner patches sit 30 nm from the panel edge.
* **21.10** `dwell()` per raster point costs 3 travel points per 1 of dose —
  the poling square first built at 17.9 write-minutes for 4.4 minutes of dose.
* **21.11** two distances compared to each other instead of to their nulls.
  15.7° to the nearest of three directions 60° apart **is** the random
  value; it was about to be read as evidence for a variant superlattice.

Also: two patch scripts reported success while their replacements silently did
not match — one of them cost the no-write null, which wrote a σ 17 panel
instead of nothing. Patch scripts now assert every replacement.

---

## What to do next

1. **Establish what the written contrast IS**, since it is not variant
   orientation: KPFM for trapped charge, topography for surface modification,
   and a thermal or electrical erase test. No write budget.
2. **Finish the poling rotation series** and push it — raster at angles
   *between* allowed directions, to see whether the film still snaps to the
   nearest one. That is the rule worth building a paper around.
3. **Replicate the off-triad result** on areas whose Λ gives a clean
   4Λ window (Λ ≤ 300 nm). Two more runs, ~1 write-minute each.
4. **Nano-domains:** search the PHASE channels at 2.44 nm/px, requiring
   Phase1/Phase2 agreement, on uniformly poled regions.

---

## Files

`TrajectoryLitho_Revision_260829.docx` — the revision, with figures.
`FINDINGS.md` M24–M28 · `PITFALLS.md` §20–21 ·
`figures_today/` figT1–figT4 · `scale_tools.py` (the validated
estimator) · `block1_write.py`, `block2_pole.py`, `hires.py`,
`retention.py`, `analyse_queue.py`, `analyse_offtriad.py` ·
per-run console logs `block0_*.txt`, `block2_*.txt`, `hires_*.txt`,
`retention_*.txt`.
