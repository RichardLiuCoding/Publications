# -*- coding: utf-8 -*-
"""Build a flat working directory so the published scripts run unmodified.

The code was written for one flat directory: it does `sys.path.insert(0, HERE)`
and then `import autoloop`, it reads `results_templates.csv` from its own
folder, and `autoloop.load_toolkit` reads the [TOOLKIT] cell out of
`Claude_interactive_notebook_v2.ipynb` next to it. The repository is laid out in
subfolders because that is easier to read, so this script materialises the flat
layout the code expects.

    python setup_workspace.py
    cd workspace
    python make_manuscript_figures.py
"""
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
WORK = REPO / "workspace"
SOURCES = [
    "src/instrument", "src/patterns", "src/analysis", "src/figures",
    "campaign2/iterations", "data/derived", "notebooks",
]
EXTRA = ["sparc_paths.py", "campaign2/campaign_state.json"]


def link(src, dst):
    """Hard link by preference.

    aug_toolkit.py resolves its own location with Path(__file__).resolve(),
    which follows a symlink back to src/analysis/ and then cannot find the
    notebook holding the [TOOLKIT] cell. A hard link is indistinguishable from
    the original, so resolve() stays inside the workspace.
    """
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    for attempt in (os.link, os.symlink):
        try:
            attempt(src, dst)
            return "hard links" if attempt is os.link else "symlinks"
        except (OSError, NotImplementedError):
            continue
    shutil.copy2(src, dst)
    return "copies"


def main():
    WORK.mkdir(exist_ok=True)
    mode, n, seen = None, 0, {}
    for group in SOURCES + ["."]:
        base = REPO / group
        names = EXTRA if group == "." else [p.name for p in sorted(base.iterdir())]
        for name in names:
            p = (REPO / name) if group == "." else (base / name)
            if not p.is_file() or p.name.startswith("."):
                continue
            # data/derived carries an `output_` prefix to keep the two sources
            # apart in the repo; strip it so scripts find the expected name.
            flat = p.name[len("output_"):] if p.name.startswith("output_") else p.name
            if flat in seen:
                print("  name clash: %s (%s vs %s), keeping the first"
                      % (flat, seen[flat], group))
                continue
            seen[flat] = group
            mode = link(p, WORK / flat)
            n += 1
    print("workspace/: %d entries by %s" % (n, mode))
    if not os.environ.get("SPARC_DATA"):
        print("note: SPARC_DATA is not set, so anything reading raw frames will "
              "stop with a clear error. See docs/DATA_AVAILABILITY.md.")


if __name__ == "__main__":
    sys.exit(main())
