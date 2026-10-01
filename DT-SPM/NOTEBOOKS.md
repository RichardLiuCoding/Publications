# Notebook guide

Use `DT-SPM_R1_reproduce.ipynb` for the tested workflow. Run it from this folder with the pinned CPython 3.10.19 environment. Its first cell downloads the dataset if needed and verifies all files. The default run rebuilds and checks the FD libraries. Set `RUN_REANALYSIS = True` to run every revised analysis stage and compare the resulting numbers with the supplied reference results.

| Notebook | Role |
|---|---|
| `DT-SPM_R1_reproduce.ipynb` | Entry point for dataset installation, integrity checks and the revised analysis driver |
| `DT-SPM_colab/DT-SPM_full_digital_twin.ipynb` | Submitted Tap300 model source used by the historical correction audit and descriptor CV |
| `DT-SPM framework TRANSFER — Multi75 cali.ipynb` | Multi75 model source used by descriptor CV |
| `FD_calibration_Tap300_v2.ipynb`, `FD_calibration_cali_fd_v2.ipynb` | Historical force–distance calibration sources |
| `Fit DT controller parameters to experimental scans_v2.ipynb` | Historical controller-calibration source |
| `Clean up data to train DT.ipynb`, `DT-SPM_FD based_RL_v9.ipynb` | Historical data preparation and exploratory model sources |

The historical notebooks document the supplied calibration records and model definitions. Some cells retain their original local paths and optional instrument code. They have not been validated as independent, start-to-finish workflows in this package. The reproduction driver loads the specific functions required for the revised analyses and runs offline.

The revised benchmark excludes target scans and uses the declared calibration inputs. The historical CNN–LSTM correction remains an audit of post-acquisition processing. The AlScN FD library postdates the scan grid, so the revised evaluation is retrospective. See `REPRODUCTION_MAP.md` for each figure's producer and inputs.

Run notebooks from a Jupyter installation with the registered `DT-SPM R1` kernel. The `DT-SPM_colab` folder name records the historical notebook location; a default Colab runtime does not reproduce the pinned environment.
