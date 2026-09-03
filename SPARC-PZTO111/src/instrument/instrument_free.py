# -*- coding: utf-8 -*-
"""instrument_free.py -- refuse to start if another process is driving Igor.

Exit 0 and clear a stale lock only when NO instrument-driving python process is
alive. Exit 1 otherwise.

WHY. aespm talks to Igor through a command file. Two processes writing it
interleave their commands and the result is undefined -- which is what
autoloop.lock exists to prevent. On 29 August every launch in this session
began with `rm -f autoloop.lock` as a reflex, and one of them removed the lock
that a still-running block0_probe was holding. A screening run and a probe
qualification then drove the instrument together for five minutes; both frames
had to be discarded.

`rm -f autoloop.lock` is never safe on its own. Check first.

    python instrument_free.py && python my_driver.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK = os.path.join(HERE, 'autoloop.lock')
DRIVERS = ('block0_probe', 'block1_write', 'block2_pole', 'block3_raster',
           'run_night', 'run_round2', 'run_round3', 'run_afternoon',
           'run_blocks', 'screen_areas', 'retention_raster',
           'tile_boundary', 'tile_boundary_read', 'autoloop',
           'diag_', 'probe_health')
#
# THE LIST IS THE WEAKNESS. On 30 Aug a tiling driver that was not in it
# was declared 'not running' while it still held the instrument, a second
# job started, and the first job read back the second job's frame from a
# different area entirely. Any new driver MUST be added here, and the
# safer habit is for every driver to hold autoloop.lock for its whole
# life so that membership of this list stops mattering.

ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
      "Select-Object -ExpandProperty CommandLine")
try:
    out = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                         capture_output=True, text=True, timeout=60).stdout
except Exception as e:
    print('could not enumerate processes (%s); refusing to clear the lock' % e)
    sys.exit(1)

mine = os.getpid()
busy = [ln.strip() for ln in (out or '').split('\n')
        if any(d in ln for d in DRIVERS) and str(mine) not in ln]
if busy:
    print('INSTRUMENT BUSY -- %d driver process(es) already running:' % len(busy))
    for b in busy[:4]:
        print('   %s' % b[:150])
    print('refusing to start. Wait, or stop them deliberately.')
    sys.exit(1)

if os.path.exists(LOCK):
    os.remove(LOCK)
    print('no driver running; cleared a stale autoloop.lock')
else:
    print('no driver running; no lock present')
sys.exit(0)
