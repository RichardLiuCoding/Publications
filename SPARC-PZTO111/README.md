# SPARC: human-agent discovery of reconfigurable in-plane superdomain control in PbZr<sub>0.2</sub>Ti<sub>0.8</sub>O<sub>3</sub>(111)

Code, notebooks, memory files, write files, and derived data for

> Y. Liu, B. Slautin, C.-C. Lin, J. Kim, L. W. Martin and S. V. Kalinin,
> *Human-agent discovery of reconfigurable in-plane ferroelectric superdomain
> control*, submitted to *Digital Discovery* (2026).

SPARC, the Scanning Probe Agentic Research Cycle, pairs a coding agent with one
microscope and one operator for the length of a campaign. The two share a
notebook and two persistent memory files: `memory/FINDINGS.md`, which records
what is known about the sample with a reliability grade on every claim, and
`memory/PITFALLS.md`, which records how the analysis has previously gone wrong.
Selected PITFALLS entries were compiled into checks that refuse a design before
any voltage reaches the tip.

The experiment asks which tip operations select the in-plane superdomain
direction of a (111)-oriented PZT film, where the three allowed directions are
related by symmetry so a uniform field cannot choose between them. Campaign 1
was operator-supervised (runs R1 to R7). Campaign 2 was agent-driven (iterations
IT1 to IT10b), ending with the letters UTK written into the domain orientation.

## Layout

| Path | Contents |
|---|---|
| `memory/` | The two memory files, verbatim as the campaign left them. The paper's central artefact. |
| `src/instrument/` | Instrument interface, exclusive lock, autonomous driver, diagnostics, imaging runs. |
| `src/patterns/` | Write-file generators: charge-balanced templates, the pulse lattice, the UTK geometry. |
| `src/analysis/` | State-variable extraction, the three orientation estimators, per-question analyses. |
| `src/figures/` | Figure builders for the main text and SI, plus geometry and label-overlap self-checks. |
| `campaign2/iterations/` | One script per agent-driven iteration, as executed. |
| `campaign2/consoles/` | Recorded console output and logs from those iterations. |
| `campaign2/campaign_state.json` | Persistent campaign state at the end of the run. |
| `notebooks/` | The shared notebook and the reading, writing, and DART notebooks, with outputs. |
| `write_files/` | Every file actually sent to the instrument, both campaigns. |
| `data/derived/` | Scored results, per-iteration numbers, cached site and map arrays. |
| `data/manifests/` | SHA-256 for all 676 raw frames, which are deposited separately. |
| `interaction_record/` | The coded interaction record behind Section S12.2, and readable session renderings. |
| `docs/` | Data availability, reproduction notes, campaign log, handoff notes. |

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`igor2` reads the Igor binary wave frames. `aespm` drives the microscope and is
needed only to re-run acquisition, not analysis.

## Run the analysis

The raw frames are not in this repository. Get the deposit described in
[`docs/DATA_AVAILABILITY.md`](docs/DATA_AVAILABILITY.md), then:

```bash
export SPARC_DATA=/path/to/frames
python setup_workspace.py
cd workspace
python make_manuscript_figures.py
```

`setup_workspace.py` exists because these scripts were written for one flat
directory: they add their own folder to `sys.path` and `import autoloop`, they
read `results_templates.csv` from beside themselves, and `autoloop.load_toolkit`
reads the `[TOOLKIT]` cell out of `Claude_interactive_notebook_v2.ipynb`. The
repository is in subfolders because that reads better; the workspace gives the
code the layout it expects, by hard link, so nothing is duplicated on disk.

[`docs/REPRODUCE.md`](docs/REPRODUCE.md) maps each figure and each quoted number
to the script that produces it.

## Re-run the acquisition

The acquisition scripts are published as they ran, on a Windows instrument
computer driving Asylum Research Igor Pro through AESPM, carrying the paths that
machine used. They will not run unmodified elsewhere and are included as the
record of what was executed, not as a portable tool.
`src/instrument/experiment.py` is where the machine-specific paths live.

**Read `memory/PITFALLS.md` §8 before adapting any of this.** It is the safety
envelope: scanner range, bias ceiling, declared footprint, write budget. §9 is
the autonomous-loop protocol. The paper's own account of where this went wrong
is in Supplementary Section S12.

## Publishing this repository

Copy it out of any cloud-synced folder before `git init`. Dropbox, Google Drive,
and OneDrive rewrite files under `.git/` while git is using them, which corrupts
the object store in ways that are tedious to diagnose.

```bash
cp -R sparc-pzto111 ~/repos/ && cd ~/repos/sparc-pzto111
git init && git add -A && git commit -m "SPARC: code, notebooks, and records"
```

Two things to settle before the first push: the deposit DOI in
[`docs/DATA_AVAILABILITY.md`](docs/DATA_AVAILABILITY.md), and the release tag,
which should match the DOI so the paper can cite one version rather than a
moving branch.

## Licence

Code is MIT (`LICENSE`). Data, memory files, derived results, and records are
CC BY 4.0 (`LICENSE-DATA`).
