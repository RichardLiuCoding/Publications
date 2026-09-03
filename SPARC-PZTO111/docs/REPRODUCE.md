# Reproducing the figures and the numbers

Set up once:

```bash
export SPARC_DATA=/path/to/frames     # see DATA_AVAILABILITY.md
python setup_workspace.py
cd workspace
```

Everything below is run from `workspace/`. Scripts print the statistics they
draw, so a number in the paper that does not appear in a script's output does
not have a source. That check is the reason the scripts print at all: an
earlier factor-of-two error reached FINDINGS.md by being transcribed rather
than computed (`memory/PITFALLS.md` §19.11).

## Figures

| Script | Builds | Reads |
|---|---|---|
| `make_manuscript_figures.py` | Commanded against adopted director for every panel; the dose response and where the lattice threshold sits; real-space LDART evidence for the best selection pair; the two-term mechanism picture | `results_templates.csv`, LDART frames |
| `make_si_figures.py` | Estimator on a known input and on noise; topography screening including the area a step edge disqualified; retention of the raster-written director; the triad fit; dose and scan speed | LDART frames, plus synthetic stripe fields built in the file |
| `make_state_figure.py` | What the state variable is, on the R6 baseline area | LDART frames |
| `make_writes_figure.py` | What was actually sent to the instrument, for the three write types | `write_files/` |
| `make_tool_compare.py` | Raster against pulse lattice, on the allowed directions only | `results_templates.csv` |
| `make_tile_figure.py` | Two variants written side by side | LDART frames |
| `make_mechanism_figure.py` | The symmetry and energy-landscape schematic | nothing external |
| `make_today_figures.py` | The 29 August result panels | LDART frames |

`make_si_figures.py` takes panel selectors and defaults to `1`, so ask for all
of them:

```bash
python make_si_figures.py 1 2 3 5 t     # SF1 estimator, SF2 screening,
                                        # SF3 retention, SF4 dose and speed,
                                        # SF5, and the triad fit
```

Output goes to `figures_manuscript/` or `figures_ms/` beside the script.
`publication_style.save_figure` writes png, pdf, svg, and tiff at 600 dpi for
the raster formats.

Figures 1 and 2 of the main text are schematics, not data plots. They are
described once as `Scene` objects in `v3_scenes.py` (with icon glyphs in
`v3_glyphs.py`) and rendered either through matplotlib or as native PowerPoint
shapes through `pptx_svg.py`, so the same description produces both an editable
deck and a vector figure.

## Self-checks

| Script | Asserts |
|---|---|
| `test_fig1_geometry.py` | The domain geometry drawn in Fig. 1a is self-consistent |
| `check_overlaps.py` | No two drawn text labels intersect, per figure |
| `check_figs.py` | Every figure on disk is referenced and every reference exists |
| `check_arc_p.py` | The circular-range p-value, by simulation |

## Numbers

| Script | Produces |
|---|---|
| `summary_stats.py` | Every number quoted in the campaign summary. Applies the four-lambda rule first and visibly: a panel whose 1.4 µm readout window holds fewer than four lamellar periods is separated out rather than averaged in (`PITFALLS.md` §19.15) |
| `aug_analysis.py` | Recomputes every number in the 14–15 August summary from the raw frames |
| `retention_all.py` | Every retention pair, both estimators, one table |
| `triad_all.py` | The single-triad test against every raster write in the campaign |
| `round3_report.py` | The dose and speed series from the round-3 logs |
| `rescore.py` | Re-scores an iteration from its frames, independently of the driver that ran it |
| `verify_channel_and_sequence.py` | The two provenance checks on the R6 result |

`rescore.py` and `verify_channel_and_sequence.py` are the independent path
described in Supplementary Section S14.8. Running `rescore.py` on an iteration
should reproduce the population values the driver logged; if it does not, the
driver is wrong, not the rescore. That comparison is how the axis-order defect
in the independent loader was found: transposed axes rotated the angular
spectrum and relabelled the triad while preserving total triad power.

## Estimators

The three orientation estimators compared in Section S8 are in
`interaction_record/paper_llm/estimator_test.py` and in the `[TOOLKIT]` cell of
`Claude_interactive_notebook_v2.ipynb`, which `autoloop.load_toolkit` extracts.
`scale_tools.py` separates the superdomain and nanodomain scales;
`map_orientation.py` and `fine_angle.py` go below the FFT window limit.

## Analysis that needs no frames

These run without `SPARC_DATA`:

```bash
python make_mechanism_figure.py
python check_arc_p.py
python test_fig1_geometry.py
python -c "import template_lib, utk_geom; print('pattern geometry OK')"
```

## Verified on release

With `SPARC_DATA` pointing at the frame deposit, the following were run from a
clean `workspace/` and completed:

```
make_manuscript_figures.py   40 panel rows; 32/38 within 15 deg, median offset
                             3.5 deg; 34 dose points, sigma 19-803; on target
                             28, off target 6; lowest on-target sigma 52
make_si_figures.py 1 2 3 5 t SF1 through SF5 and the triad fit
make_mechanism_figure.py     mechanism figure written
test_fig1_geometry.py        figure 1a geometry is consistent
check_arc_p.py               circular range of the six landings 5.81 deg
```

If your numbers differ from these, the frames are not the deposited ones. Check
them against `data/manifests/frames_sha256.csv` first.
