# Data

## `derived/`

Scored results and cached intermediates. These are what the figure scripts read,
so the figures can be rebuilt without the 1.84 GB of raw frames.

| File | Contents |
|---|---|
| `results_templates.csv` | One row per written panel, 40 rows. Commanded angle, template kind, exposure, site count, lamellar period, the fitted triad, the three-member population before and after the write, the dominant director before and after, the excess at the commanded member, and the same-frame null. This is the table behind the main selection figure. |
| `summary_stats.json`, `summary_stats.txt` | Output of `summary_stats.py`: every number quoted in the campaign summary. |
| `aug_numbers.json` | Numbers recomputed from raw frames for the 14–15 August summary. |
| `aug_provenance.json` | Which file, command, and instrument state produced each August frame. |
| `aug_frame_index.json` | Frame index for the August sessions. |
| `aug_r12.json` | Per-panel results for run R12. |
| `it1_proposal.json` | The agent's preregistered proposal for iteration IT1, with its alternative outcomes. |
| `survey_lambda_260828_0127.csv` | Lamellar period, modulation, and streak across the scanner. |
| `output_*.npy`, `output_*.npz` | Cached site coordinates and director population maps, including the UTK letter maps. |

Column note for `results_templates.csv`: `w0_0..w0_2` are the three populations
before the write and `w1_0..w1_2` after, indexed against `triad`, which holds
the three fitted director angles separated by `|`. `want` is the commanded
member. `sigma` is voltage-time exposure per unit area, not charge, because
current was not measured.

## `manifests/`

`frames_sha256.csv` and `frames_summary.md` describe the raw frames, which are
deposited separately. See `../docs/DATA_AVAILABILITY.md`, which also gives the
verification snippet.

Licence: CC BY 4.0, see `../LICENSE-DATA`.
