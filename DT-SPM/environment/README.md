# Environment records

`requirements-lock.txt` pins the complete Python dependency set installed for the fresh package validation. `install_environment.py` installs these versions into a dedicated CPython 3.10.19 virtual environment. `validation_environment.json`, `validation_pip_freeze.txt`, and `validation_pip_check.txt` record the environment used for the supplied verification run.

`revised_analysis_record/` preserves the September 2026 environment record, full package listing and installation-date inventory. The original lock-file heading has been corrected to describe the revised analyses. Its package versions are unchanged. These records do not establish the environment of the original submission.

The recorded combination has one dependency-metadata conflict: aespm 1.1.4 specifies NumPy below 2.0, while the revised numerical stack uses NumPy 2.2.6. The installer uses a complete transitive pin list with `--no-deps` to reproduce this combination, then checks that no additional mismatch is present. The fresh-run reports establish whether this combination executes the packaged workflow and reproduces the archived numbers. `pip check` is retained verbatim rather than reported as clean.

Validation uses CPU PyTorch with two threads for notebook training and single-thread settings for BLAS/OpenMP in the driver. The original record's availability of Apple MPS does not mean the analyses used MPS. A new platform or package version should be assessed using `compare_results.py`; the supplied evidence applies to the platform named in the validation record.
