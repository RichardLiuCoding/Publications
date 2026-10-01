# Verification of the prepared package

The package was copied to a separate directory and executed with a fresh CPython 3.10.19 virtual environment installed from the pinned requirements. All 14 analysis stages completed. The original working-folder outputs were retained as reference results.

## Numerical results

The comparison covers 20 revised result files and split manifests. Nineteen meet the default numerical tolerance (`rtol=1e-6`, `atol=1e-8`, with matching NaN locations); the historical Qsafety correction audit has the small differences listed below. The revised AlScN predictions, grating comparison, learning curves, descriptor CV, mechanism analysis and split assignments meet the default check. See `verification/numerical_comparison.json` for the field-level results.

The historical neural Qsafety audit varies in five summary values. The largest absolute change in its error summaries is about `1.10e-5` in the dimensionless proxy; the permuted-input Spearman coefficient changes by about `1.04e-4`. These values agree when rounded to three decimal places. The comparison report retains every deviation, marks this file as failing the stricter default tolerance, and separately records agreement at that reporting precision. This exception applies only to the historical correction audit; it does not relax the checks on the revised predictive benchmark.

Raw-IBW preprocessing reproduces every field of both archived FD libraries with zero array difference. The archived AlScN convention of 31 drive entries for 30 curve rows is preserved and documented.

The intermediate AlScN bundle reproduces all 38 compared arrays exactly. For the grating bundle, 22 of 23 manuscript-used arrays match the comparison criterion. The hybrid scan-line array has a maximum absolute difference of `6.8903e-5 nm`, retained in `verification/output/bundles/bundle_regeneration_report.json`. This is the same small reconstruction difference recorded in the earlier bundle check; the supplied archived bundle remains the reference input. Development-only diagnostic arrays are listed explicitly as outside that producer's scope.

The bundle stage also refits grating conditions 0, 2 and 4. Conditions 0 and 4 reproduce the archived log-gains; condition 2 has a log10(P) difference of about `1.40e-4`, with the same log10(I) boundary value. These are selected local checks, not a refit of all historical calibration objects.

## Scope of execution

`verification/stage_status.json` records exit status and timing for FD preprocessing, bundle generation, the submitted-correction audit, revised AlScN benchmark, mechanism analysis, learning curves, grating benchmark, both encoder CV analyses, the invariance check, split manifests, revised figures, supplementary tables and historical supplementary panels. Individual logs are retained under `verification/logs/`.

The invariance check reproduces unchanged predictions for its four tested predictors on one blocked fold after perturbing held-out height lines and Qalign targets. It does not test every model family, channel or fold. The benchmark remains retrospective because the AlScN FD calibration was acquired after the grid.

The package includes all 17 images embedded in the current manuscript and SI and CSV transcriptions of its seven SI tables. Image hashes link these to available figure files. Plot regeneration is checked separately from numerical equality; rasterization can depend on fonts and plotting software. The original editable main schematics and exact embedded images are retained for this reason.

## Environment and remaining author work

The clean installation reproduces the documented aespm/NumPy metadata conflict. No additional conflict is accepted by the installer. `environment/validation_pip_check.txt` records this fact; the environment is not described as passing an unqualified dependency check.

The GitHub code is prepared locally. The linked dataset was downloaded from Google Drive and verified. Code/data licences, confirmed creator metadata, the final code release tag and commit, and code/data archive DOIs remain for author completion. The manuscript CRediT and conflict statements remain subject to author confirmation. Code upload and DOI deposition were not performed during preparation.

## GitHub package check, 30 September 2026

The GitHub package retains all 49 scientific Python source files from the verified R1 package without changes. Packaging changes are limited to dataset retrieval, archive building, instructions, metadata and the reproduction notebook's setup cell. The full 14-stage results above come from the earlier R1 validation.

The Google Drive ZIP was downloaded without account cookies and matched the expected 668,283,428 bytes and SHA-256. All 375 dataset file checksums passed after extraction. The extraction helper was tested for repeat installation, incomplete downloads, archive and member checksum errors, changed local files, unexpected ZIP members, path traversal and symbolic-link destinations. The code archive builder was also checked with the dataset installed to confirm that it excludes those files. All nine focused tests passed.

The reproduction notebook ran with CPython 3.10.19 against the downloaded data. Its integrity checks and FD preprocessing completed. All FD arrays met their comparison criterion; the largest difference was `7.11e-15` in the AlScN drive vector, with zero differences in the other arrays. The full reanalysis switch remained off for this packaging check.

Run the helper tests with `python -m unittest discover -s tests -v`. `metadata/github_package_validation.json` records these checks.
