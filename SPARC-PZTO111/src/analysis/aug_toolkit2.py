# -*- coding: utf-8 -*-
"""Load notebook v2's [TOOLKIT] cell for offline analysis of the 260820 data.

The cell is the authoritative implementation of ibw / signed / angular_power /
dir_power / dir_state / fit_triad, and it is what the autonomous loop itself
called. Re-implementing any of it here would risk a silent divergence from the
numbers already reported, so the cell is exec'd as written with aespm stubbed.
"""
import io
import json
import os
import re
import sys
import types
from pathlib import Path

import numpy as np

PROJ = Path(__file__).resolve().parent
DATA = PROJ / "260820" / "PZTO"
NB = PROJ / "Claude_interactive_notebook_v2.ipynb"
CELL = 37


def _stub_aespm(data_dir):
    """A stand in for aespm that can read a wave and nothing else."""
    from igor2.binarywave import load as _load

    def _ibw_read(path, lines=False, connection=None):
        d = _load(str(path))["wave"]
        arr = np.asarray(d["wData"], dtype=float)
        labs = [x.decode() if isinstance(x, bytes) else x
                for L in d["labels"] for x in L if x]
        note = d["note"]
        if isinstance(note, bytes):
            note = note.decode("latin-1", "replace")
        hdr = {}
        for line in note.replace("\r", "\n").split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                hdr[k.strip()] = v.strip()
        # igor2 returns wData indexed [fast, slow, layer]. aespm hands the
        # toolkit frames indexed [row, col] = [slow, fast], so the two spatial
        # axes have to be swapped. Without this the angular spectrum comes out
        # transposed, theta -> 90 - theta, and a rigid triad fit that should
        # read 4/64/124 reads 24/84/144 instead: the same numbers on the wrong
        # members. Checked against the printed fit for PZTO_LDART_0128.
        arr = np.swapaxes(arr, 0, 1)
        out = types.SimpleNamespace(data=np.moveaxis(arr, -1, 0),
                                    channels=labs, note=note, header=hdr)
        return out

    m = types.ModuleType("aespm")
    m.ibw_read = _ibw_read
    m.tools = types.SimpleNamespace(load_ibw=_ibw_read)
    m.tune_probe = lambda *a, **k: None
    m.write_spm = lambda *a, **k: None
    m.get_files = lambda **k: [str(data_dir)]
    m.check_file_number = lambda **k: None
    return m


def load_toolkit(data_dir=None):
    data_dir = str(data_dir or DATA)
    sys.modules["aespm"] = _stub_aespm(data_dir)
    nb = json.load(io.open(NB, encoding="utf-8"))
    src = "".join(nb["cells"][CELL]["source"])
    ns = {"__name__": "__main__"}
    exec("import os, time, json\nimport numpy as np\nimport matplotlib\n"
         "matplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n"
         "from scipy import ndimage as ndi", ns)

    class _E(object):
        folder = data_dir

        def execute(self, *a, **k):
            pass

        def check_files(self, **k):
            pass
    ns["exp"] = _E()
    ns["CONFIG"] = dict(work_dir=str(PROJ / "output"))
    exec(src, ns)
    assert sys.modules["aespm"].__name__ == "aespm"
    need = ("ibw", "signed", "angular_power", "dir_power", "dir_state",
            "fit_triad")
    miss = [f for f in need if f not in ns]
    if miss:
        raise RuntimeError("toolkit missing %s" % miss)
    _memoize(ns)
    ns["FOLDER"] = data_dir
    return ns


def _memoize(ns):
    """Cache ibw() and signed() per frame.

    dir_state calls sq_power four times and each call re-loads the wave and
    re-fits the phase offset, so one window costs four full frame loads. Both
    functions are pure functions of the file, so caching changes no number and
    turns a director map from hours into seconds.
    """
    _ibw, _signed = ns["ibw"], ns["signed"]
    fc, sc = {}, {}

    def ibw(tag, folder=None):
        k = (tag, folder)
        if k not in fc:
            fc[k] = _ibw(tag, folder=folder)
        return fc[k]

    def signed(d, verbose=False):
        k = id(d[0])
        if k not in sc:
            sc[k] = _signed(d, verbose=verbose)
        return sc[k]

    ns["ibw"], ns["signed"] = ibw, signed
    ns["_cache_frames"], ns["_cache_signed"] = fc, sc
