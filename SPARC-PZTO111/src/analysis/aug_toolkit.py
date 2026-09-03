# -*- coding: utf-8 -*-
"""Load the notebook's [TOOLKIT] cell for offline analysis of the 260813 data.

The notebook cell is the authoritative implementation of ibw / signed /
angular_power / dir_power / fit_triad / period. Re-implementing them here would
risk a silent divergence from the numbers already reported, so the cell is
executed as-is with the instrument objects stubbed out.
"""

import io
import json
import os
import types
from pathlib import Path

import numpy as np

PROJ = Path(__file__).resolve().parent
DATA = PROJ / "260813" / "PZTO"
NB = PROJ / "Claude_interactive_notebook_v1.ipynb"


def load_toolkit(data_dir=None):
    data_dir = str(data_dir or DATA)
    nb = json.load(io.open(NB, encoding="utf-8"))
    ns = {"__name__": "__main__"}
    exec(
        "import os, time, json\n"
        "import numpy as np\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "from scipy import ndimage as ndi\n",
        ns,
    )
    import aespm as ae

    ns["ae"] = types.SimpleNamespace(
        tools=ae.tools,
        write_spm=lambda *a, **k: None,
        tune_probe=lambda *a, **k: None,
        get_files=lambda **k: ["stub"],
    )

    class _Exp:
        folder = data_dir

        def execute(self, *a, **k):
            pass

        def check_files(self, **k):
            pass

    ns["exp"] = _Exp()
    ns["CONFIG"] = {"work_dir": str(PROJ / "output")}

    for cell in nb["cells"]:
        src = "".join(cell["source"])
        if "scoring, QC and change detection" in src:
            exec(src, ns)
            break
    else:
        raise RuntimeError("[TOOLKIT] cell not found in the notebook")
    return ns


def region(cx, cy, box):
    """Square scoring region centred on (cx, cy), in microns."""
    return (cx - box / 2.0, cx + box / 2.0, cy - box / 2.0, cy + box / 2.0)


def popvec(dir_power, tag, rg, triad):
    """Population vector over the three triad directors, normalised to 1."""
    w = np.array([dir_power(tag, rg, float(t))[0] for t in triad], float)
    return w / w.sum()
