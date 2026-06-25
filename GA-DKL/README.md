# GA-DKL: Closed-Loop Discovery of Out-of-Distribution Processing Protocols

Code accompanying the manuscript:

> **Closed-loop discovery of out-of-distribution processing protocols by evolutionary search and uncertainty-aware learning**
> Yu Liu, Stanislav Udovenko, Ching-Che Lin, Jaegyu Kim, Lane W. Martin, Susan Trolier-McKinstry, and Sergei V. Kalinin
> *(preprint: arXiv:2606.13859)*

## Overview

Many functional properties are governed not only by composition and structure, but by **history**: the time-dependent protocol that brings a material to its operating state. This repository implements a closed-loop workflow that discovers new processing protocols directly in experiment, using ferroelectric thin films as a model system. The processing protocol is a scanning-probe tip-bias waveform, and the experimental reward is the change in the effective nonlinear electromechanical response (ENL) measured before and after each waveform.

The workflow couples three components:

1. **VAE initialization manifold.** A 1D convolutional variational autoencoder is trained on 14 experimentally common seed waveforms. Decoding a 21 x 21 latent grid produces a continuous family of realistic candidate waveforms used to seed the search.
2. **Genetic algorithm (GA) in Fourier space.** Each waveform is parameterized by 33 Fourier coefficients (DC + 16 harmonics). Tournament selection, BLX-alpha blend crossover, and additive Gaussian mutation generate ~1,000 out-of-distribution candidates per generation, with amplitude bounds enforced at synthesis.
3. **Deep kernel learning (DKL) surrogate.** A 1D CNN feature extractor combined with an exact Gaussian process is trained on all measured waveform-response pairs and ranks the GA candidates by upper confidence bound (UCB), so that only a small, informative batch is measured each generation.

The loop runs autonomously on an Asylum Research scanning probe microscope through [aespm](https://github.com/RichardLiuCoding/aespm): generate candidates, rank, measure, retrain, repeat. On PZT thin films, the campaign discovers temporally structured, multi-harmonic waveforms that enhance nonlinearity by selectively depinning weakly pinned domain walls, in effect electrically de-aging the film.

## Repository contents

| File | Description |
|------|-------------|
| `GA-DKL_experimental_workflow.ipynb` | The full closed-loop experiment: ENL metric, seed waveforms, VAE manifold, instrument interface, DKL surrogate, GA candidate generation, seeding run, and the active-learning loop. Includes a self-contained appendix version with a synthetic objective that runs without hardware. |
| `GA-DKL_results_analysis.ipynb` | Processing and analysis of campaign results: ENL-ratio trajectories, evolution of the best waveforms and their Fourier spectra, and before/after PFM map comparisons. Reproduces the main results figures of the paper. |
| `requirements.txt` | Python dependencies. |

## Installation

```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>
pip install -r requirements.txt
```

Python 3.10 or newer is recommended. A CUDA-capable GPU accelerates VAE and DKL training but is not required.

## Hardware requirements

The instrument-facing sections (Sections 6, 10, and 11 of the workflow notebook) require an Asylum Research SPM controlled through `aespm`, and were run with dual-amplitude resonance tracking (DART) PFM. Everything else, including the complete GA-DKL optimization loop in the appendix (with a synthetic objective), runs on a regular computer. To adapt the loop to other instruments or simulators, replace `evaluate_waveform()` with your own measurement call returning a scalar reward.

## Data

The campaign archives (`.npz` files containing `waves`, the measured waveforms, and `y`, the ENL ratios) and the raw `.ibw` microscope files analyzed in the results notebook are not included in this repository due to size. They are available from the corresponding authors upon reasonable request.

## How the pieces map to the paper

- ENL metric and readout waveform: paper Fig. 1e-f
- 14 seed waveforms and VAE manifold: Fig. 2
- GA-DKL loop (Eqs. 3-5, Algorithm 1): Fig. 3
- ENL trajectories, best-waveform evolution, before/after PFM maps: Fig. 4
- Fourier-coefficient evolution: Fig. S2

## Citation

If you use this code, please cite the paper:

```bibtex
@article{liu2026gadkl,
  title   = {Closed-loop discovery of out-of-distribution processing protocols
             by evolutionary search and uncertainty-aware learning},
  author  = {Liu, Yu and Udovenko, Stanislav and Lin, Ching-Che and Kim, Jaegyu
             and Martin, Lane W. and Trolier-McKinstry, Susan and Kalinin, Sergei V.},
  year    = {2026},
  journal = {arXiv preprint arXiv:XXXX.XXXXX}
}
```

## Acknowledgements

This work is supported by the Center for 3D Ferroelectric Microelectronics Manufacturing (3DFeM2), an Energy Frontier Research Center funded by the U.S. Department of Energy, Office of Science, Basic Energy Sciences under Award Number DE-SC0021118.

## Contact

- Yu Liu (yliu206@utk.edu)
- Sergei V. Kalinin (sergei2@utk.edu)
