#!/usr/bin/env python3
"""Install the frozen validation environment inside an activated CPython 3.10.19 venv.

All transitive dependencies are pinned. --no-deps is intentional: aespm 1.1.4
advertises NumPy <2, while the recorded analyses used NumPy 2.2.6.
The exact combination is tested by the supplied reproduction pipeline.
"""
from pathlib import Path
import json,subprocess,sys
if sys.prefix==sys.base_prefix:raise SystemExit('Activate a dedicated virtual environment first.')
if sys.version_info[:3]!=(3,10,19):raise SystemExit('Use CPython 3.10.19 for the recorded environment.')
p=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-m','pip','install','--no-deps','-r',str(p/'requirements-lock.txt')],check=True)
r=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
lines=[s.strip() for s in r.stdout.splitlines() if s.strip()]
expected='aespm 1.1.4 has requirement numpy<2.0, but you have numpy 2.2.6.'
print(r.stdout)
if r.returncode and lines!=[expected]:raise SystemExit('Unexpected dependency mismatch; inspect pip check before running.')
print('Frozen environment installed. The documented aespm/NumPy metadata mismatch remains.')
