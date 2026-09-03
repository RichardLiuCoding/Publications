# Instrument: how to drive it, and every constraint

Asylum AFM driven from Python via `aespm` plus a custom Igor panel
("TrajectoryLitho"). Everything below is measured on this rig, not from a manual.

---

## 1. Architecture — one implementation of every function

The measurement toolkit lives in **`Claude_interactive_notebook_v2.ipynb`**.
`autoloop.py` **execs the notebook cells** into a namespace so that scripts and
interactive work share one implementation:

```python
import autoloop as A
ns = A.load_toolkit(stub_instrument=False)   # True = no instrument, for offline work
g = ns.__getitem__
g('setup_scan')(size_um=12.0, px=256, rate=0.833, angle_deg=0.0,
                xoff_um=-14.0, yoff_um=-14.0)
```

`stub_instrument=True` replaces `aespm` in `sys.modules` **before** anything is
exec'd, and asserts the stub survived. Do not stub only inside the exec
namespace: on 14 Aug a stub placed there was overwritten by the toolkit cell's
own `import aespm as ae` and six `GetTune()` calls went to the live instrument.

`load_toolkit` skips archived section cells (those whose first line matches
`# --- [<digit>`) and asserts the whole write path is present.

Key module constants in `autoloop.py`:

```
PROJ, NB, STATE, LOCK, STOP, LOG
DATA_ROOT = C:\Users\Asylum User\Documents\Asylum Research Data
```

Frames land in dated subfolders as `PZTO_LDART_nnnn.ibw` / `PZTO_VDART_nnnn.ibw`.
Index them by basename — they are spread across date folders and taking the
directory of the first glob hit finds the wrong one.

---

## 2. The 30 toolkit functions drivers actually use

**Modes and scanning**
`goto_ldart()` — lateral DART, the in-plane texture readout.
`goto_vdart()` — vertical DART, out-of-plane classes. Use 128 px; it is enough.
`setup_scan(size_um, px, rate, angle_deg, xoff_um, yoff_um)`
`frame()` → filename tag of the frame just captured.
`find_resonance('ldart')`, `tune_here(mode, size_um, px, rate, xoff_um, yoff_um)`
— tune plus one frame; returns `(centre, {'frame': tag, 'frac': ...})`.
`contact_check(tag)`, `orbit_balance(vdart_tag)`, `frame_gate(tag, ref_tags=...)`
`check_folder()`, `scanner_ok(xoff, yoff, size)`

**Reading the data**
`ibw(tag)` → `(data, header)`; **`data[0]` is Height**, then Amplitude1/2,
Phase1/2, Frequency.
`signed(data)` → `(S, ...)` the signed texture used for period and direction.
`period(S, px_nm, angle_deg)` → lamellar period along one director (unreliable
per member — see §5 of the analysis file).
`pin_triad(tag, ref_fam=FAM_FILM)` → `(triad, {'mod': ..., ...})`
`dir_state(tag, cx, cy, win_um, triad, cmd_deg)` → `{w, dom, lead, w_cmd,
on_target, peak}` or `None` if the window is too small.
`sq_power`, `ctrl_tiles(x0, x1, y0, y1, w_um, gap_um=0.1)`, `pick_ref`,
`streak_index(tag, region)`, `window_check(win, px_nm, lam, name=...)`,
`command_for(tag, cx, cy, win, triad, sense=±1, min_lead=0.05)`

**Writing**
`TrajectoryBuilder(field_um, step_um=0.02, travel_v=0.0)` with
`.dwell((x, y), V, n=pulses)` and `.to_arrays()` → `(X, Y, V)`.
`lattice_panel(n, sp_um, centre, ang_deg, v, sign_every=1, keep_frac=1.0)` —
charge-balanced square lattice, sites in **serpentine order**.
`gen_center_out_raster(...)` — see §6.
`run_traj(tb, path, speed_um_s=0.5, preview=False)`
`sigma_of(...)`, `pulse_n_for(...)`, `visualize_trajectory(...)`

`FAM_FILM = (2.0, 62.0, 122.0)` — the film's triad, constant within ~5° across
8+ areas.

---

## 3. Timing and cost — the model that matters for planning

**Frame time = px / rate**, independent of scan size.
`rate = TIP_SPEED_MAX / (2 × size_um)` with `TIP_SPEED_MAX = 20 µm/s`.
At 12 µm and 256 px: rate 0.833 Hz → **307 s ≈ 5.1 min per frame**.
Screening one candidate area (tune + frame) ≈ **5.8 min**.

**Trajectory time = n_points × step_um / speed_um_s.** With `step_um = 0.02` and
`speed = 0.5 µm/s`, one point = 0.04 s.

**Dwell time = Area × σ / V** — the lattice spacing *cancels*. Four times the
sites at a quarter of the dwell each costs the same dwell time.

**Travel time does NOT cancel** and is where two of my cost models were wrong:

| geometry | travel overhead |
|---|---|
| solid rectangular panel | **1.35×** |
| masked lattice (letters, shapes) | **1.55×** |

Measured example, UTK mask at Λ = 301 nm: Λ/2 spacing gave 1188 sites, 16.6 min
of dwell, 8.5 min of travel, **25.1 min total**; Λ/4 gave 4756 sites, 15.9 min
dwell, 18.4 min travel, **34.3 min total**. So Λ/4 buys ~1.7× purity for ~1.4×
time — not free.

**Always gate on the built trajectory**, never on an estimate.

`dir_state` costs **~1.6 s per call** (four `sq_power` calls; the cost is compute,
not I/O — caching the frame load changed nothing). Budget it explicitly:
a director map at WIN/4 step over a whole 12 µm frame is 2738 calls = **73
minutes**. Restrict the region and step at ~WIN/2.

---

## 4. Hard constraints

| constraint | value | source |
|---|---|---|
| scanner range | \|offset\| + size ≤ **50 µm**, both axes | operator |
| tip bias | \|V\| ≤ **10 V** | `V_CEILING` |
| charge per site | ≤ **20 V·s** (half of C21's 40 V·s single-pulse threshold) | above it, switching goes site-by-site rather than collectively |
| per-write time | ≤ **26 min** (`MAX_WRITE_MIN`) | bounds one unattended write |
| cumulative write | ≤ **330 min** (`MAX_TOTAL_WRITE_MIN`) | 164.6 used as of 22 Aug |
| iterations | ≤ **12** (`MAX_ITER`) | 8 used |
| charge balance | file-level \|mean V\| ≤ 0.01, and aim for exactly 0 | C13: a DC offset re-poles out-of-plane |
| readout window | ≥ 4Λ **and** ≥ 24 px | below either, direction is undefined |
| streak index | ≤ 0.10 (`STREAK_MAX`) | scan-line artefact reads as director 0° |
| baseline flip rate | ≤ 25 % (`FLIP_MAX`) | above it "dominant director" is not defined |
| baseline tile sd | ≤ 0.150 (`TILE_SD_MAX`) | measured readout-health signal |

`preflight(prop, st, ns)` in `autoloop.py` encodes these as S1–S29. **Call it,
twice**: once before any instrument command (pre-registration and loop stops,
with geometry and dose deferred) and once after the area and dose exist. For a
year it was never called by any driver because it crashed on `prop['offset']`
being `None`, which every driver's design guarantees — a guard that cannot run
in the normal path is not a guard.

If an iteration writes **twice** into one area (deplete-then-select, or
write-then-rewrite), S9 will otherwise flag it against itself; declare the reuse:

```python
PROP = dict(..., reuse_areas=['IT6_UTK'])   # printed as an explicit exception
```

---

## 5. Instrument gotchas — each cost real time

- **The stage does not return to the same place after an excursion.**
  Consecutive frames disagree by 0.136 in lead; frames separated by a visit to
  another area disagree by **0.45–0.51**, with 50–57 % of tiles flipping
  director. Take all baselines *consecutively at the chosen area*, after
  screening is finished. Never reuse a screening frame from before a move.
- **`read_meter` channel 2 is the live deflection = tip state, not the setpoint.**
  It swung −0.84 / −0.44 / +0.600 while `DeflectionSetpointVolts` in the frame
  header held at 0.600 V across 13 frames. If you want to know whether the force
  changed, read the header.
- **`contact_check`'s "RETUNE HERE / bad contact spot" is not a readout-quality
  signal.** It fired on five consecutive areas while the tile spread stayed flat
  at 0.081–0.109. Treat it as a hypothesis and test it against the quantity that
  matters before acting — especially before stopping work.
- **Height rows are line-flattened by the Asylum software.** A step running along
  y is invisible in a row-mean profile; only a step along x survives. Detect
  topography on the 2-D patch after removing a plane.
- **This sample has a terrace edge**: −2.2 nm step at x ≈ 4.4 µm in one frame,
  42 nm peak-to-peak, and up to 107 nm across some candidate boxes. Rank
  candidate areas by height range and record the topography under each panel
  *before* writing, so an unequal result has a measured explanation available
  instead of an invented one.
- **Serpentine ordering matters.** Sign-ordered site lists make the tip cross the
  panel between every pulse: an 870-site ladder cost 62,054 points (41 min)
  instead of ~30,000 (20 min). `lattice_panel` already returns serpentine order.

---

## 6. The raster — two traps

```python
gen_center_out_raster(W_um, H_um, pitch_um, angle_deg, center_um, v,
                      start_sign=+1, flip_each_cycle=False,
                      field_um, step_um, n_pt, tb, travel_v, verbose)
```

**Trap 1: polarity comes from `start_sign`, not from the sign of `v`.** The
generator takes the magnitude from `v`. Two calls with `v=+9` and `v=−9` both
wrote +9 V — mean +7.61, a large DC raster, which C13 says re-poles. Correct
charge-balanced form is two passes with opposite `start_sign`:

```python
for sgn in (+1, -1):
    gen_center_out_raster(..., v=V_RAST, start_sign=sgn, flip_each_cycle=False, tb=tb)
# -> mean V exactly 0.0000, equal +/- fractions
```
A single call with `flip_each_cycle=True` is **not** balanced (odd cycle count,
mean +0.587).

**Trap 2: `W_um` and `H_um` are measured in the ROTATED frame.** A 10.6 × 4.0 µm
box at 62° is a diagonal stripe across the frame, footprint x 1.81–10.19,
y 0.44–11.56. A horizontally laid-out shape then only partly overlaps it: for the
UTK word, 97 % of the T but 19 % of the U and 18 % of the K landed on treated
film. **If you raster along a triad member and want a shape covered, lay the
shape along the same direction.** That gives 97–100 % per letter.

Raster areal dose = `V / (pitch_um × speed_um_s)`. At 9 V, Λ/2 pitch, 0.5 µm/s
→ 129 V·s/µm². C26 worked at ~144.

Raster cost: `(H/pitch) × W / speed`, doubled for the balanced pair. A
10.6 × 4.0 µm box at Λ/2 pitch = 23.5 min for both passes.

---

## 7. Files and state

```
campaign_state.json   iteration, used_areas [[x,y],size,label], total_write_min,
                      completed[], strikes, theory{sigma_c}
autoloop.lock         held while a driver runs; removed in a finally clause
STOP                  create to halt the loop at the next check
it<N>_console.txt      full console per iteration, written in a finally clause
output/*.txt          the trajectory files actually sent to the instrument
rescore.py            re-derive a crashed iteration's result from its console
export_history.py     bundle transcript + docs + drivers + consoles + figures
```

`rescore.py` exists because two iterations crashed after their measurement
completed. It parses the geometry a driver printed and re-derives the C45-scored
table using the same toolkit functions — so a recovery cannot produce a third
version of the numbers.

**Nine working drivers** are in the project: `run_it1.py` … `run_it10b.py`.
Copy the closest one rather than starting fresh. `run_it5.py` is the cleanest
multi-panel ladder; `run_it9.py` is the two-stage write-then-rewrite;
`run_it10b.py` is a masked arbitrary shape with a figure.

Three of them (`run_it5/7/8.py`) still lack the per-line output flush — add it
before running them unattended.
