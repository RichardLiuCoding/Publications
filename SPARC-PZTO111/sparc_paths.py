# -*- coding: utf-8 -*-
"""Where the raw frames live.

The scripts in this repository were written for a single flat working directory
on the instrument computer, and they are published as they ran. `SPARC_DATA`
is the one knob that repoints them at a downloaded copy of the frame deposit.

    export SPARC_DATA=/path/to/frames      # contains 260813/ 260820/ ...

Import this module rather than hardcoding a path in new work:

    from sparc_paths import session_dir
    frames = sorted(session_dir("260829").glob("PZTO_LDART_*.ibw"))
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent


def data_root():
    """The directory holding the per-session frame folders."""
    env = os.environ.get("SPARC_DATA")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p
        raise FileNotFoundError("SPARC_DATA is set to %s, which does not exist" % p)
    raise RuntimeError(
        "Set SPARC_DATA to the frame deposit. The frames are not in this "
        "repository; see docs/DATA_AVAILABILITY.md."
    )


def session_dir(session, sample="PZTO"):
    """Frames for one acquisition session, e.g. session_dir('260829')."""
    d = data_root() / session / sample
    return d if d.is_dir() else data_root() / session


def derived(name):
    return REPO / "data" / "derived" / name


def manifest(name="frames_sha256.csv"):
    return REPO / "data" / "manifests" / name
