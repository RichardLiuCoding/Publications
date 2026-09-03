# Data availability

## What is in this repository

Everything needed to read the analysis: source, notebooks with their stored
outputs, the two memory files, every file sent to the instrument, the scored
results, and the per-iteration numbers. Roughly 120 MB.

## What is deposited separately

The raw piezoresponse frames: **676 Igor binary wave files, 1.84 GB**, too large
for git. They are organised by acquisition session and channel.

| Session | LDART | VDART | AC | Total |
|---|---|---|---|---|
| 260813 | 46 | 24 | 2 | 72 |
| 260820 | 142 | 13 | 0 | 155 |
| 260827 | 252 | 8 | 0 | 260 |
| 260829 | 122 | 67 | 0 | 189 |
| **All** | **562** | **112** | **2** | **676** |

LDART is lateral dual-frequency resonance tracking, the channel the in-plane
director is read from. VDART is the vertical channel. Frame names are
`PZTO_<channel>_<index>.ibw`.

Also deposited, and deliberately not tracked here:

- The raw Claude Code session transcripts as JSON, about 24,000 entries across
  five sessions. The repository carries the readable Markdown renderings in
  `interaction_record/transcripts/` and the coded analysis in
  `interaction_record/paper_llm/`.
- `Experiment.pxp`, the Igor experiment file.

> **Deposit DOI: to be assigned.** Replace this line with the Zenodo DOI before
> submission, and add the same DOI to the paper's Data availability statement.

## Verifying a download

`data/manifests/frames_sha256.csv` lists session, relative path, channel, index,
size, and SHA-256 for every frame. To check a copy:

```bash
python - <<'PY'
import csv, hashlib, os, sys
root = os.environ["SPARC_DATA"]
bad = missing = 0
for r in csv.DictReader(open("data/manifests/frames_sha256.csv")):
    p = os.path.join(root, *r["path"].split("/")[1:])
    if not os.path.exists(p):
        missing += 1
        continue
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    if h.hexdigest() != r["sha256"]:
        bad += 1
        print("MISMATCH", r["path"])
print("missing %d, mismatched %d" % (missing, bad))
PY
```

`data/manifests/frames_summary.md` is the same inventory in prose.

## Pointing the code at the frames

```bash
export SPARC_DATA=/path/to/frames    # the directory holding 260813/ 260820/ ...
```

`sparc_paths.py` is the only place the data root is defined. Scripts published
as they ran still carry their original instrument-computer paths; see the note
in the README.
