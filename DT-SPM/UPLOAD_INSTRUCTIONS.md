# Upload the DT-SPM code to GitHub

Destination: [RichardLiuCoding/Publications/DT-SPM](https://github.com/RichardLiuCoding/Publications/tree/main/DT-SPM).

The prepared folder contains the code and instructions. The dataset ZIP is hosted separately at [Google Drive](https://drive.google.com/file/d/1ckGptfEbkKzbnl_eHDzDHCAU6Hjbhyce/view?usp=sharing). Keep that ZIP unchanged so its checksum continues to match `dataset_config.json`.

## Upload from the local repository

The local checkout is `~/Documents/GitHub/Publications`. Review and commit only the `DT-SPM` changes:

```bash
cd ~/Documents/GitHub/Publications
python3 DT-SPM/verify_package.py --part code
git status --short -- DT-SPM
git diff --stat -- DT-SPM
git add --all -- DT-SPM
git diff --cached --stat -- DT-SPM
git commit -m "Prepare DT-SPM R1 code and dataset download instructions" -- DT-SPM
git push origin main
```

The staged changes include removal of the old `DT-SPM_data` files and replacement of the earlier notebooks and instructions. The R1 dataset is distributed through Drive. `.gitignore` excludes installed data, downloaded ZIPs, virtual environments and generated runs. If the repository already contains other staged work, review that work separately before committing.

The package preparation itself does not create a commit or push to GitHub. After uploading, record the actual commit with `git rev-parse HEAD`. Assign a release tag only when the version is final.

## Upload through the GitHub website

Extract `DT-SPM_GitHub_R1_2026-09-30.zip`. It contains one `DT-SPM/` folder. Upload that folder's contents to the repository's existing `DT-SPM` directory, keeping the subfolders. Do not create an extra `DT-SPM/DT-SPM` level. Include `.gitignore`, which may be hidden in Finder.

Remove the superseded `DT-SPM_data/` folder and the old root-level `DT-SPM_full_digital_twin.ipynb`, `DT-SPM_reproduce_paper.ipynb` and `requirements.txt`. File upload through the website does not remove those older paths automatically. Updating from the local repository is preferable because its recorded deletions are included in the commit.

## Check the uploaded version

Download or clone the uploaded code into a fresh folder. Follow `README.md` to install the environment and run:

```bash
python verify_package.py --part code
python download_dataset.py
python verify_package.py
python run_reproduction.py --stage fd --run-dir runs/upload_check
```

The Drive archive downloaded successfully during preparation and matched the recorded checksum. Recheck anonymous access if you change its sharing settings. For complete numerical validation, run all stages and then `compare_results.py`, as described in the README.

If you edit code or documentation before uploading, refresh the code manifests and ZIP:

```bash
python build_archives.py
python verify_package.py --part code
```

The ZIP is written to `dist/`, which is ignored by Git. The builder includes code and instructions only, even if the dataset is installed. It preserves the dataset manifest. Updating the dataset requires a new archive, checksum and version record.

Confirm creator metadata and licences, then record the release tag or commit and any archive DOIs in the manuscript availability statements. The GitHub and Drive links are access locations; DOI deposition remains pending. `DEPOSITION_CHECKLIST.md` contains the remaining fields and suggested wording.
