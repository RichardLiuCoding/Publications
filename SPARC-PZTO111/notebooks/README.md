# Notebooks

**Do not rename these files.** The filenames are load-bearing.
`autoloop.load_toolkit` reads the `[TOOLKIT]` cell out of
`Claude_interactive_notebook_v2.ipynb`, and `aug_toolkit.py` reads it out of
`v1`. Renaming either breaks every analysis script that imports `autoloop`.

| Notebook | What it is |
|---|---|
| `Claude_interactive_notebook_v1.ipynb` | The shared notebook for the first sessions. Carries the `[TOOLKIT]` cell used for the 260813 data. |
| `Claude_interactive_notebook_v2.ipynb` | The shared notebook for the middle of Campaign 1. Its `[TOOLKIT]` cell is the analysis code that `autoloop.py` and every figure script load at import. |
| `Claude_interactive_notebook_v3.ipynb` | The shared notebook as Campaign 2 left it: 187 cells of analysis functions, proposed experiments, write-file generators, and instrument-control calls. This is the executable scientific record described in Supplementary Section S6.1. |
| `Trajectory Litho Read Data_v2.ipynb` | Reading frames and building the state variable. The largest file here, because the stored output images are the evidence. |
| `Trajectory based domain writting_v5.ipynb` | Trajectory and lattice writing. |
| `L+VDART_v2.ipynb` | Lateral and vertical DART channels, including the sideband-consistency check added after anti-correlated sidebands were found. |
| `Spiral_Trajectory_Generator_v2.ipynb` | Spiral trajectory generation. |
| `Trajectory_domain_writing_closed_loop_v2.ipynb` | The closed-loop writing prototype. |

Outputs are kept deliberately. The notebook is the record, and a cleared
notebook would not show what the agent and the operator actually saw at the
time. Code in these cells is MIT; the stored outputs are CC BY 4.0.
