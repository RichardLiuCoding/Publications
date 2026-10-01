# Release identifiers and manuscript availability

Code destination: [GitHub](https://github.com/RichardLiuCoding/Publications/tree/main/DT-SPM). Dataset access: [Google Drive](https://drive.google.com/file/d/1ckGptfEbkKzbnl_eHDzDHCAU6Hjbhyce/view?usp=sharing). The Drive ZIP was downloaded and verified during preparation. The revised code is prepared for upload; a final release tag, commit and code/data archive DOIs remain pending.

1. Upload the prepared code following `UPLOAD_INSTRUCTIONS.md`. Keep the dataset ZIP unchanged and retain public read access to the Drive file.
2. Confirm the creator list, affiliations, ORCIDs, funding metadata, code licence and data licence. Confirm the manuscript's CRediT, conflict, instrument and probe statements separately.
3. Record the uploaded code commit and, when assigned, the release tag. `R1-repro-2026-09-30` identifies the prepared reproducibility package; it is not an existing Git release.
4. If depositing in a DOI archive, deposit the final code and dataset versions and link the records to each other. Record version-specific DOIs. Verify downloaded copies against their manifests.
5. Enter the same access links and final code identifier in both Data Availability Statements. Add code/data DOIs once assigned, and update the response letter's pending-deposition sentence to match the actual release status.

Suggested wording after the revised code is uploaded:

> The code for the revised analyses is available at https://github.com/RichardLiuCoding/Publications/tree/main/DT-SPM (commit [FINAL COMMIT]; release [TAG, IF ASSIGNED]). The measured scan and force–distance data, processed libraries, calibration records, reference outputs, split manifests and verification reports are available at https://drive.google.com/file/d/1ckGptfEbkKzbnl_eHDzDHCAU6Hjbhyce/view?usp=sharing. The code includes the recorded revised-analysis environment, a pinned validation environment, scripts for reconstructing the intermediate bundles, numerical comparison reports and SHA-256 file manifests. The README describes the required calibration inputs and the tested reproduction workflow. Persistent code and data archive DOIs are [PENDING / INSERT ASSIGNED DOIs].

Replace bracketed fields with confirmed information before using this wording. Keep the pending-deposition qualification until the archive records exist. The GitHub and Drive links do not establish a DOI deposition.

`metadata/code_record_draft.json` contains editable code metadata. The dataset's `metadata/data_record_draft.json` retains the draft metadata that was packaged in the fixed ZIP. `metadata/hosting.json` records the current access plan without changing that archive. Creator, licence and DOI fields remain author decisions.
