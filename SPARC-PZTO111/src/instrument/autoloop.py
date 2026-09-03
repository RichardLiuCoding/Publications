# -*- coding: utf-8 -*-
"""Autonomous closed-loop search for the in-plane superdomain switching rules.

GOAL
    Find the switching rules of the IP superdomain directions under point-pulse
    lattice writing, and reach full control of the IP superdomains for arbitrary
    patterns.

HOW IT WORKS
    Each iteration is a closed cycle: propose -> preflight -> build -> execute
    -> read -> refine -> log -> decide. State lives in campaign_state.json so
    the loop survives a kernel restart or a context compaction.

    The analysis toolkit is NOT duplicated here. It is exec'd out of the
    notebook, so the notebook stays the single source of truth for every
    measurement function and the loop cannot silently diverge from what was used
    interactively.

TWO PROCESSES MUST NOT DRIVE IGOR AT ONCE
    aespm talks to Igor by writing a command file. If a Jupyter kernel and this
    module both do that, the commands interleave and the result is undefined.
    The loop takes an exclusive lock (autoloop.lock) and refuses to start if one
    is held. Do not run notebook cells that touch the instrument while the loop
    is running.

SAFETY
    PITFALLS.md section 8 is the envelope. Every item is checked here before any
    write; see preflight() and the assertions in build_and_write(). Nothing in
    section 8 may be relaxed to make an experiment fit.
"""
import os
import io
import json
import time
import glob
import types
import shutil
import traceback
import contextlib
import re

import numpy as np

PROJ = os.path.dirname(os.path.abspath(__file__))
NB = os.path.join(PROJ, 'Claude_interactive_notebook_v2.ipynb')
STATE = os.path.join(PROJ, 'campaign_state.json')
LOCK = os.path.join(PROJ, 'autoloop.lock')
STOP = os.path.join(PROJ, 'STOP')
LOG = os.path.join(PROJ, 'autoloop.log')
DATA_ROOT = os.environ.get(
    "SPARC_DATA",
    r"C:\Users\Asylum User\Documents\Asylum Research Data")

# ---------------------------------------------------------------- safety
SCAN_LIMIT = 50.0          # S2  scanner range, |offset| + size
V_CEILING = 10.0           # S1  tip bias
CHG_1PULSE_MAX = 40.0      # S8  C21 single-pulse rotation threshold
MAX_WRITE_MIN = 26.0       # S7  per iteration
MAX_ITER = 12              # S24
MAX_TOTAL_WRITE_MIN = 330.0  # S24 cumulative. Raised from 180 on 22 Aug
                             # at the operator's request to continue
                             # overnight, and because the measured probe
                             # signal shows no degradation: tile spread
                             # 0.101/0.100/0.095/0.098 across IT1-IT4.
                             # The real guard is TILE_SD_MAX below.
TILE_SD_MAX = 0.150         # stop if the baseline tile spread of w(cmd)
                            # exceeds this - 50 % above the IT1-IT4 band
                            # of 0.095-0.101. This is the measured
                            # probe/readout health signal that the
                            # minutes cap was only a proxy for.
MAX_STRIKES = 2            # S25 consecutive unreadable iterations
FLIP_MAX = 0.25            # S20 untouched-tile director-flip rate
STREAK_MAX = 0.10          # S18
MOD_MIN = 0.10             # S16


def say(msg, also_print=True):
    line = '%s  %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg)
    with io.open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    if also_print:
        print(msg)


# ================================================================ state
DEFAULT_STATE = {
    'goal': ('Find the switching rules of the IP superdomain directions under '
             'point-pulse lattice writing, and reach full control of the IP '
             'superdomains for arbitrary patterns.'),
    'iteration': 0,
    'strikes': 0,
    'total_write_min': 0.0,
    'theory': {
        'name': 'T3',
        'sigma_c': 302.0,
        'sigma_c_err': 9.0,
        'purity_law': 'w(cmd) = 0.234*ln(sigma) - 0.887',
        'conditions': ['selection: template commensurate, q = Q',
                       'drive: areal charge density sigma > sigma_c'],
        'open': ['sigma_c is fitted, not yet predicted',
                 'sigma lumps V with dwell',
                 'the halo is 4-9x the spacing yet commensuration works'],
    },
    'used_areas': [
        [[0.0, 0.0], 8.0, 'S6/7'], [[12.0, 0.0], 10.0, 'S8'],
        [[-10.0, 0.0], 10.0, 'S9'], [[-10.0, 0.0], 6.0, 'S10'],
        [[-10.0, 10.0], 8.0, 'S11'], [[0.0, 15.0], 10.0, 'S12'],
        [[12.0, 15.0], 10.0, 'S13'], [[26.0, 15.0], 12.0, 'S14'],
        [[26.0, 28.0], 12.0, 'S15'], [[-10.0, 30.0], 10.0, 'S16r1'],
        [[-22.0, 30.0], 10.0, 'S16r2'], [[-34.0, 30.0], 12.0, 'S17'],
    ],
    'completed': [],
    'queue': ['IT1_sigma_prediction', 'IT2_commensuration', 'IT3_V_vs_dwell',
              'IT4_two_director_boundary', 'IT5_potts_30deg',
              'IT6_retention_vs_drive'],
    'history': [],
}


def load_state():
    if not os.path.exists(STATE):
        save_state(DEFAULT_STATE)
        say('created %s' % os.path.basename(STATE))
        return json.loads(json.dumps(DEFAULT_STATE))
    with io.open(STATE, encoding='utf-8') as f:
        st = json.load(f)
    for k, v in DEFAULT_STATE.items():
        st.setdefault(k, v)
    return st


def save_state(st):
    if os.path.exists(STATE):
        shutil.copy(STATE, STATE + '.bak')
    with io.open(STATE, 'w', encoding='utf-8') as f:
        json.dump(st, f, indent=1)


def remind():
    """Print the goal, the theory and the live cautions. Call after compaction."""
    st = load_state()
    print('=' * 78)
    print('GOAL')
    print('=' * 78)
    print('  ' + st['goal'])
    t = st['theory']
    print('\nTHEORY %s   sigma_c = %.0f +- %.0f V.s/um^2'
          % (t['name'], t['sigma_c'], t['sigma_c_err']))
    for c in t['conditions']:
        print('  - ' + c)
    print('  purity above threshold: ' + t['purity_law'])
    print('\nWHAT THE THEORY STILL OWES')
    for o in t['open']:
        print('  - ' + o)
    print('\nSTATE  iteration %d, %d completed, %.0f min written, %d strike(s)'
          % (st['iteration'], len(st['completed']), st['total_write_min'],
             st['strikes']))
    print('QUEUE  ' + ', '.join(st['queue']) if st['queue'] else 'QUEUE  empty')
    print('\nREAD BEFORE PROPOSING: PITFALLS.md (goal at the top, safety in '
          'section 8),')
    print('                       FINDINGS.md (C1-C40)')
    return st


# ================================================================ toolkit
def load_toolkit(stub_instrument=False):
    """Exec the notebook's toolkit and wrappers into a fresh namespace.

    stub_instrument=True replaces aespm in sys.modules BEFORE anything is
    exec'd, and asserts the stub survived - PITFALLS 4.1. On 14 Aug a stub
    placed only in the exec namespace was replaced by the toolkit cell's own
    `import aespm as ae` and six GetTune() calls went to the live instrument.
    """
    import sys
    if stub_instrument:
        import aespm as _real
        stub = types.ModuleType('aespm')
        stub.ibw_read = _real.ibw_read
        stub.tools = _real.tools
        stub.tune_probe = lambda *a, **k: None
        stub.write_spm = lambda *a, **k: None
        stub.get_files = lambda **k: ['x']
        sys.modules['aespm'] = stub
    nb = json.load(io.open(NB, encoding='utf-8'))
    ns = {'__name__': '__main__'}
    exec('import os,time,json,glob\nimport numpy as np\nimport matplotlib\n'
         'matplotlib.use("Agg")\nimport matplotlib.pyplot as plt\n'
         'from scipy import ndimage as ndi', ns)
    import aespm as ae
    if not stub_instrument:
        ns['ae'] = ae
        folder = resolve_folder()
        exp = ae.Experiment(folder=folder)
        # The notebook attaches these to the Experiment object in cell 25 via
        # add_func. frame() calls exp.check_files and contact_check may call
        # read_meter; without them the first frame() raises AttributeError,
        # which is exactly how IT1's first launch died - after the tune, before
        # any write.
        _meter = os.path.join(r"C:\Users\Asylum User\Documents\buffer",
                              "Meter.ibw")

        def check_files(self, max_wait=150):
            return ae.check_file_number(path=self.folder, wait=0.1,
                                        retry=int(max_wait / 0.1))

        def read_meter(self):
            ae.write_spm(commands="GetMeter()", connection=self.connection)
            return ae.ibw_read(_meter, lines=True, connection=self.connection)

        def load_ibw(self, folder=None, lines=False):
            fname = ae.get_files(path=self.folder, client=self.client)[0]
            return ae.tools.load_ibw(fname)

        for _f in (check_files, read_meter, load_ibw):
            try:
                exp.add_func(_f)
            except Exception:
                setattr(exp, _f.__name__, _f.__get__(exp, type(exp)))
        if not hasattr(exp, "check_files"):
            raise RuntimeError("could not attach check_files to the Experiment "
                               "object - frame() cannot work without it")
        ns['exp'] = exp
    else:
        ns['ae'] = ae

        class _E(object):
            folder = resolve_folder()

            def execute(self, *a, **k):
                pass

            def check_files(self, **k):
                pass
        ns['exp'] = _E()
    ns['CONFIG'] = dict(work_dir=os.path.join(PROJ, 'output'))
    # Library cells first (TrajectoryBuilder etc.), then toolkit and wrappers.
    # Each is exec'd inside try/except: several library cells end with a demo
    # line that references a section variable (POLE_WH and friends), which is
    # harmless - the definitions above it are what we need. The required-name
    # check below is what actually decides whether the load succeeded.
    partial = []
    for c in nb['cells']:
        s = ''.join(c['source'])
        if c['cell_type'] != 'code':
            continue
        # Infrastructure only. Archived SECTION cells (# --- [3.2] ...) run
        # experiments and must never be exec'd here; the loader was catching
        # them and relying on try/except to survive.
        first = s.lstrip().split('\n')[0]
        if re.match(r'#\s*---\s*\[\d', first):
            continue
        if ('[LIB-' in s or 'scoring, QC and change detection' in s
                or 'tune, scan, litho' in s
                or 'def visualize_trajectory' in s):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(s, ns)
            except Exception as e:
                partial.append('%s: %s' % (s.split(chr(10))[0][:40],
                                           type(e).__name__))
    if stub_instrument:
        assert sys.modules['aespm'] is stub, 'the stub was replaced - ABORT'
        assert ns['ae'] is stub, 'the toolkit re-imported the real aespm - ABORT'
    missing = [f for f in ('dir_state', 'command_for', 'solve_grid',
                           'lattice_panel', 'scanner_ok', 'check_folder',
                           'tune_here', 'sigma_of', 'pin_triad', 'pick_ref',
                           'ctrl_tiles', 'streak_index', 'window_check',
                           'visualize_trajectory', 'run_traj', 'frame',
                           'setup_scan', 'TrajectoryBuilder')
               if f not in ns]
    if missing:
        raise RuntimeError('toolkit is missing %s - the notebook and this '
                           'module have diverged. Partial cell loads: %s'
                           % (missing, partial))
    ns['_partial_loads'] = partial
    return ns


def resolve_folder():
    """The date directory whose newest .ibw is most recent - PITFALLS 7.6."""
    best, newest = None, -1.0
    for d in glob.glob(os.path.join(DATA_ROOT, '*', 'PZTO')):
        f = glob.glob(os.path.join(d, '*.ibw'))
        if not f:
            continue
        t = max(os.path.getmtime(x) for x in f)
        if t > newest:
            best, newest = d, t
    if best is None:
        raise RuntimeError('no PZTO folder with .ibw files under %s' % DATA_ROOT)
    return best


def instrument_is_busy(quiet_s=90.0):
    """Has a frame landed in the last quiet_s seconds? If so something else is
    running - do not start."""
    d = resolve_folder()
    f = glob.glob(os.path.join(d, '*.ibw'))
    if not f:
        return False, 1e9
    age = time.time() - max(os.path.getmtime(x) for x in f)
    return age < quiet_s, age


# ================================================================ locking
class Lock(object):
    def __enter__(self):
        if os.path.exists(LOCK):
            with io.open(LOCK, encoding='utf-8') as f:
                who = f.read().strip()
            raise RuntimeError('autoloop.lock is held by %s. Two processes must '
                               'not drive Igor at once. Delete the lock only if '
                               'you are sure nothing is running.' % who)
        with io.open(LOCK, 'w', encoding='utf-8') as f:
            f.write('pid %d since %s' % (os.getpid(), time.strftime('%H:%M:%S')))
        return self

    def __exit__(self, *a):
        if os.path.exists(LOCK):
            os.remove(LOCK)
        return False


# ================================================================ preflight
def preflight(prop, st, ns, verbose=True):
    """The automated pitfalls and safety checklist. Returns (ok, failures).

    A proposal is a dict with at least:
        name, hypothesis, prediction, outcomes (dict), offset (x, y),
        frame_try (list), panels (list of dicts with keep, dwell, sign_every,
        spacing_div), collective (bool)
    """
    F = []

    # --- pre-registration, S27 ---------------------------------------
    for k in ('name', 'hypothesis', 'prediction', 'outcomes'):
        if not prop.get(k):
            F.append('S27 pre-registration: "%s" is missing' % k)
    if isinstance(prop.get('outcomes'), dict) and len(prop['outcomes']) < 2:
        F.append('S27 pre-registration: fewer than two possible outcomes named '
                 '- if only one outcome is imagined it is not a test')

    # --- loop stops, S23-S28 -----------------------------------------
    if os.path.exists(STOP):
        F.append('S23 a STOP file exists in the project directory')
    if st['iteration'] >= MAX_ITER:
        F.append('S24 iteration cap reached (%d)' % MAX_ITER)
    if st['total_write_min'] >= MAX_TOTAL_WRITE_MIN:
        F.append('S24 cumulative write budget spent (%.0f min)'
                 % st['total_write_min'])
    if st['strikes'] >= MAX_STRIKES:
        F.append('S25 %d consecutive unreadable iterations - halt and ask'
                 % st['strikes'])
    if prop['name'] in st['completed']:
        F.append('S26 "%s" is already in completed; state why, or rename'
                 % prop['name'])

    # --- geometry, S2 and S9 -----------------------------------------
    # Deferred, not skipped: the driver chooses the area at run time and calls
    # preflight a second time once it is known. A deferred check is reported as
    # deferred so it cannot be read as a pass.
    deferred = []
    if prop.get('offset') is None:
        deferred.append('S2/S9 geometry (offset not chosen yet)')
        x = y = None
    else:
        x, y = prop['offset']
    fmax = max(prop.get('frame_try', [10.0]))
    if x is None:
        pass
    elif abs(x) + fmax > SCAN_LIMIT or abs(y) + fmax > SCAN_LIMIT:
        F.append('S2 scanner range: |offset|+size = %.1f/%.1f against %.0f um'
                 % (abs(x) + fmax, abs(y) + fmax, SCAN_LIMIT))
    # An iteration that writes more than once preflights before each write, so
    # by the second call its OWN area is already in used_areas (PITFALLS 11.1
    # commits it the moment the trajectory is sent). S9 exists to keep one
    # experiment off another's film, so entries under this proposal's own name
    # are not conflicts. IT6 halted after a 23.5 min raster on exactly this.
    _areas = [] if x is None else [tuple(a[:2]) + (a[2],)
                                   for a in st['used_areas']]
    _own = [a for a in _areas if a[2] == prop.get('name')]
    if _own:
        print('    S9: skipping %d entry(ies) under this proposal\'s own name '
              '(%s) - a second write into the same area is by design'
              % (len(_own), prop.get('name')))
    # A proposal may also DECLARE areas it means to reuse - writing onto film
    # another iteration prepared is a legitimate design (IT10b writes letters
    # onto the canvas IT6 rastered). It has to be declared in the proposal, so
    # it appears in the log and in the notebook cell rather than being a guard
    # that quietly did not fire.
    _reuse = [str(r) for r in (prop.get('reuse_areas') or [])]
    _named = [a for a in _areas if a[2] in _reuse]
    if _reuse:
        print('    S9: proposal declares reuse of %s -> skipping %d matching '
              'entry(ies). This is an explicit exception, not a pass.'
              % (', '.join(_reuse), len(_named)))
    _skip = set([prop.get('name')]) | set(_reuse)
    for (ox, oy), sz, lab in [a for a in _areas if a[2] not in _skip]:
        need = (fmax + sz) / 2.0 + 0.5
        if abs(x - ox) < need and abs(y - oy) < need:
            F.append('S9 footprint: overlaps %s at (%+.1f,%+.1f) %.0f um '
                     '(need %.1f, have dx %.1f dy %.1f)'
                     % (lab, ox, oy, sz, need, abs(x - ox), abs(y - oy)))

    # --- dose, S1 and S8 ---------------------------------------------
    v = prop.get('v', V_CEILING)
    if abs(v) > V_CEILING:
        F.append('S1 tip bias %.1f V over the %.1f V ceiling' % (v, V_CEILING))
    if any(p.get('dwell') is None for p in prop.get('panels', [])):
        deferred.append('S8 charge per site (dwell solved at run time)')
    for p in prop.get('panels', []):
        if p.get('dwell') is None:
            continue
        q = abs(v) * p['dwell']
        if prop.get('collective', True) and q > 0.5 * CHG_1PULSE_MAX:
            F.append('S8 panel %s delivers %.0f V.s per site, over half C21s '
                     '%.0f V.s single-pulse threshold - it may switch '
                     'site-by-site rather than collectively'
                     % (p.get('label', '?'), q, CHG_1PULSE_MAX))

    # --- does the design discriminate? -------------------------------
    if prop.get('panels'):
        sigs = [p.get('sigma') for p in prop['panels'] if p.get('sigma')]
        if sigs and len(set(round(s_, 1) for s_ in sigs)) == 1 \
                and len(prop['panels']) > 1 and prop.get('vary_sigma', True):
            F.append('design: every panel has the same sigma and nothing else '
                     'is stated as varying - what does this discriminate?')

    if verbose:
        print('  preflight: %d check group(s), %d failure(s), %d deferred'
              % (7, len(F), len(deferred)))
        for f in F:
            print('    FAIL      ' + f)
        for d in deferred:
            print('    DEFERRED  %s - re-run preflight once it is known' % d)
        if not F and not deferred:
            print('    all clear')
        elif not F:
            print('    clear on everything checkable now')
    return (not F), F


# ================================================================ readout
def read_direction(ns, pre, after, panels, triad, win, ctrl_tiles_list,
                   verbose=True):
    """Direction-first readout. PITFALLS 6: population, not Delta(power)."""
    dir_state = ns['dir_state']
    F_REF = panels[0]['ref']
    dl, flip = [], 0
    for rg in ctrl_tiles_list:
        cx, cy = 0.5 * (rg[0] + rg[1]), 0.5 * (rg[2] + rg[3])
        p = min(panels, key=lambda q: (q['cx'] - cx) ** 2 + (q['cy'] - cy) ** 2)
        s0 = dir_state(F_REF, cx, cy, win, triad, p['cmd'])
        s1 = dir_state(after, cx, cy, win, triad, p['cmd'])
        if s0 is None or s1 is None:
            continue
        dl.append(s1['lead'] - s0['lead'])
        flip += int(s1['dom'] != s0['dom'])
    if len(dl) < 3:
        return dict(readable=False, why='only %d control tiles scored' % len(dl))
    dl = np.array(dl)
    floor = float(np.abs(dl).max())
    flip_rate = flip / float(len(dl))
    readable = (flip_rate <= FLIP_MAX) and (floor <= 0.25)
    out = dict(readable=readable, floor=floor, flip_rate=flip_rate,
               n_tiles=len(dl), ctrl_mean=float(dl.mean()),
               ctrl_sd=float(dl.std(ddof=1)), panels={})
    if verbose:
        print('  control: %d tiles, d(lead) %+.3f +- %.3f, max|d| %.3f, '
              'director flipped %d/%d (%.0f%%)  -> %s'
              % (len(dl), dl.mean(), dl.std(ddof=1), floor, flip, len(dl),
                 100 * flip_rate, 'SOUND' if readable else 'NOT USABLE'))
        if not readable:
            print('    !! the frame pair is the problem, not the write. '
                  'Untouched film should not change direction.')
    for p in panels:
        s0 = dir_state(F_REF, p['cx'], p['cy'], win, triad, p['cmd'])
        s1 = dir_state(after, p['cx'], p['cy'], win, triad, p['cmd'])
        d_ = s1['lead'] - s0['lead']
        ok = bool(s1['on_target'] and d_ > 3 * floor)
        out['panels'][p['label']] = dict(
            turned=ok, dom0=s0['dom'], dom1=s1['dom'], lead0=s0['lead'],
            lead1=s1['lead'], dlead=d_, w_cmd=s1['w_cmd'], cmd=p['cmd'],
            sigma=p.get('sigma'), n=p.get('n'),
            w0=[float(z) for z in s0['w']], w1=[float(z) for z in s1['w']])
        if verbose:
            print('  %-6s sigma %6.1f  dom %3.0f -> %3.0f  lead %+.3f -> %+.3f'
                  '  d %+.3f (%.1fx)  w(cmd) %.3f  %s'
                  % (p['label'], p.get('sigma', float('nan')), s0['dom'],
                     s1['dom'], s0['lead'], s1['lead'], d_,
                     d_ / max(floor, 1e-9), s1['w_cmd'],
                     'TURNED' if ok else ('on target, within floor'
                                          if s1['on_target'] else
                                          'dominant %.0f, NOT the command'
                                          % s1['dom'])))
    return out


# ================================================================ refine
def refine_sigma_c(st, result):
    """Tighten sigma_c from every panel ever scored. Returns a note or None."""
    ok = [], []
    lo = [p['sigma'] for p in result['panels'].values()
          if p['turned'] and p.get('sigma')]
    hi = [p['sigma'] for p in result['panels'].values()
          if not p['turned'] and p.get('sigma')]
    st.setdefault('sigma_obs', {'turned': [], 'failed': []})
    st['sigma_obs']['turned'] += [float(x) for x in lo]
    st['sigma_obs']['failed'] += [float(x) for x in hi]
    T, Fa = st['sigma_obs']['turned'], st['sigma_obs']['failed']
    if not T or not Fa:
        return None
    lo_ok, hi_no = min(T), max(Fa)
    if lo_ok > hi_no:
        new = 0.5 * (lo_ok + hi_no)
        err = 0.5 * (lo_ok - hi_no)
        old = st['theory']['sigma_c']
        st['theory']['sigma_c'] = float(new)
        st['theory']['sigma_c_err'] = float(err)
        return ('sigma_c %.0f -> %.0f +- %.0f (%d turned above %.0f, %d failed '
                'below %.0f, still no overlap)'
                % (old, new, err, len(T), lo_ok, len(Fa), hi_no))
    bad = [x for x in T if x < hi_no]
    return ('!! sigma_c NO LONGER SEPARATES: %d panel(s) turned at sigma below '
            'a failure at %.0f (lowest success %.0f). The single-threshold '
            'picture is refuted as stated - C40 needs revising.'
            % (len(bad), hi_no, lo_ok))


# ================================================================ logging
def log_to_notebook(prop, result, note, captured, iteration):
    """Append a markdown cell (motivation, prediction, result) and a code cell
    (what was actually run) to the notebook, in the interactive style."""
    nb = json.load(io.open(NB, encoding='utf-8'))
    # The tag names the EXPERIMENT, not the iteration index. Those agreed
    # until iterations ran out of order, at which point IT9 (iteration 8) was
    # tagged [IT8] - the name of a different experiment that had been built and
    # never run. Derive it from the proposal name.
    _m = re.match(r'(IT\d+[a-z]?)', str(prop.get('name') or ''))
    tag = _m.group(1) if _m else 'IT%d' % iteration
    lines = ['# ITERATION %d - %s  `[%s-doc]`' % (iteration, prop['name'], tag),
             '',
             '**Run autonomously at %s.**' % time.strftime('%Y-%m-%d %H:%M'),
             '',
             '## Why this experiment', '', prop['hypothesis'], '',
             '## Prediction, fixed before the write', '', prop['prediction'], '',
             '| outcome | what it would mean |', '|---|---|']
    for k, v in prop['outcomes'].items():
        lines.append('| %s | %s |' % (k, v))
    if prop.get('caveat'):
        lines += ['', '## Known by design, before the write', '',
                  prop['caveat'], '']
    lines += ['', '## Result', '']
    # The within-frame contrast is the PRIMARY metric (C42): panels against
    # untouched tiles in the SAME frame, so drift, gain, mode changes and stage
    # hysteresis cannot enter. Render it first, and above the before/after
    # table, so the notebook record matches how the verdict was actually
    # reached rather than showing the weaker comparison as the headline.
    W = (result or {}).get('within_frame')
    # `readable` in the result carries the WEAK before/after metric's opinion,
    # which is not the criterion the verdict uses. When a within-frame block is
    # present it is the primary metric and it defines readability: it has no
    # temporal floor, so a frame pair cannot make it unreadable. Deciding this
    # from the weak metric is what made IT3's cell claim "unreadable" while its
    # console reported three switched panels.
    if W:
        result = dict(result)
        result['readable'] = True
    if W:
        lines += ['### Within-frame contrast (primary, C42)', '',
                  'Untouched tiles in the after-frame: w(cmd) %.3f ± %.3f; '
                  'a panel counts as switched when it exceeds the tile mean by '
                  'more than 2 sd = %.3f **measured in the same frame**.'
                  % (result.get('ctrl_w_mean', float('nan')),
                     result.get('ctrl_w_sd', float('nan')),
                     result.get('within_floor', float('nan'))), '',
                  '| panel | design | dominant → after | w(cmd) | '
                  'excess over tiles | × 2 sd | |',
                  '|---|---|---|---|---|---|---|']
        for lab in sorted(W, key=lambda k: -W[k]['excess']):
            p = W[lab]
            design = p.get('design') or ('%.1f Λ' % (
                p['period_nm'] / max(result.get('lam', 1.0), 1e-9)))
            arrow = ('%.0f → %.0f (cmd %.0f)'
                     % (p['dom0'], p['dom'], p['cmd'])
                     if 'dom0' in p and 'cmd' in p else '—')
            lines.append('| %s | %s | %s | %.3f | **%+.3f** | %.1f | %s |'
                         % (lab, design, arrow, p['w_cmd'], p['excess'],
                            p['x2sd'],
                            'SWITCHED' if p['switched'] else '—'))
        lines += ['']
    if not result:
        lines += ['**The iteration did not complete.** See the code cell output.',
                  '']
    elif not result.get('readable', False):
        lines += ['**Unreadable, not unsuccessful.** The untouched control moved '
                  'as much as the panels (flip rate %.0f %%, floor %.3f), so '
                  'this frame pair cannot answer the question either way. The '
                  'written panels are still there and can be re-scored.'
                  % (100 * result.get('flip_rate', float('nan')),
                     result.get('floor', float('nan'))), '']
    else:
        # Read with .get(): ctrl_mean and ctrl_sd are set only by
        # A.read_direction(), which the within-frame path does not call. Missing
        # them is normal now, not an error - IT4 lost its whole notebook cell to
        # a KeyError here.
        if result.get('n_tiles') is not None:
            cm, cs = result.get('ctrl_mean'), result.get('ctrl_sd')
            lines += ['### Before versus after (secondary — carries every '
                      'difference between the two frames)', '',
                      'Control: %d tiles, floor %.3f, director flipped in '
                      '%.0f %% of untouched tiles%s.'
                      % (result['n_tiles'], result.get('floor', float('nan')),
                         100 * result.get('flip_rate', float('nan')),
                         '' if cm is None
                         else ', Δlead %+.3f ± %.3f' % (cm, cs)), '']
        if result.get('panels'):
            lines += ['| panel | σ | dominant before → after | lead after | '
                      'w(cmd) | |', '|---|---|---|---|---|---|']
            for lab, p in result['panels'].items():
                lines.append('| %s | %.0f | %.0f → **%.0f** | %+.3f | '
                             '**%.3f** | %s |'
                             % (lab, p.get('sigma') or 0, p['dom0'], p['dom1'],
                                p['lead1'], p['w_cmd'],
                                'turned' if p['turned'] else 'no'))
            lines += ['']
    if note:
        lines += ['## What it changes', '', note, '']
    md = dict(cell_type='markdown', metadata={},
              source='\n'.join(lines).splitlines(keepends=True))
    src = ('# --- [%s]  %s  (autonomous, iteration %d) ---\n'
           '# Parameters as run. The build and readout came from autoloop.py,\n'
           '# which exec\'s the toolkit out of this notebook so there is one\n'
           '# implementation of every measurement function.\n'
           'PROPOSAL_%s = %s\n'
           'RESULT_%s = %s\n' % (tag, prop['name'], iteration, tag,
                                 json.dumps(prop, indent=1), tag,
                                 json.dumps(result, indent=1, default=float)))
    code = dict(cell_type='code', metadata={}, execution_count=None,
                outputs=[dict(output_type='stream', name='stdout',
                              text=(captured or '').splitlines(keepends=True))],
                source=src.splitlines(keepends=True))
    at = len(nb['cells'])
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] == 'markdown' and ''.join(c['source']).startswith(
                '# ARCHIVE'):
            at = i
            break
    nb['cells'][at:at] = [md, code]
    json.dump(nb, io.open(NB, 'w', encoding='utf-8'), indent=1)
    say('logged iteration %d to the notebook at cell %d' % (iteration, at))


def append_findings(text):
    P = os.path.join(PROJ, 'FINDINGS.md')
    with io.open(P, 'a', encoding='utf-8') as f:
        f.write('\n' + text.rstrip() + '\n')
    say('appended to FINDINGS.md')


# ================================================================ dose solver
def solve_dose(target_ratio, lam_nm, sigma_c, v=V_CEILING, on_resonance=True,
               max_per_pulse=0.5 * CHG_1PULSE_MAX, verbose=False):
    """Find a legal recipe that hits sigma = target_ratio * sigma_c.

    A proposal must NOT hard-code keep or spacing: sigma depends on Lambda,
    which is only known after the reference frame is taken, and Lambda has moved
    30 % between areas 10 um apart. PITFALLS rule 4. The proposal states the
    target sigma ratio; this solves the recipe at build time.

    Constraints respected:
      - template period held at Lambda when on_resonance, so
        sign_every = spacing_div / 2 (S14/Condition 1)
      - per-site charge kept under max_per_pulse, default half C21's 40 V.s, so
        the panel stays collective rather than becoming a ladder of independent
        single-pulse switches (S8)
      - dwell reachable exactly by an integer PULSE_N at 0.02 um / 0.5 um/s
      - keep in (0, 1]

    Returns dict(spacing_div, sign_every, keep, dwell, sigma, ratio, per_pulse)
    or None if the target cannot be reached legally.
    """
    want = float(target_ratio) * float(sigma_c)
    best = None
    for div in (2.0, 3.0, 4.0, 6.0, 8.0):
        if on_resonance:
            se = div / 2.0
            if abs(se - round(se)) > 1e-9 or round(se) < 1:
                continue          # period would not land on Lambda
            se = int(round(se))
        else:
            se = 1
        sp = (lam_nm / 1000.0) / div
        base = (1.0 / sp ** 2) * v           # keep = 1, dwell = 1 s
        for pn in range(1, 51):              # 1..50 points = 0.04..2.0 s
            dwell = pn * 0.02 / 0.5
            if v * dwell > max_per_pulse + 1e-9:
                continue
            keep = want / (base * dwell)
            if not (0.05 <= keep <= 1.0):
                continue
            sig = base * keep * dwell
            # prefer keep near 1 (a complete lattice is the cleanest state),
            # then the coarsest spacing (fewest pulses), then the shortest dwell
            score = (abs(keep - 1.0), div, dwell)
            if best is None or score < best[0]:
                best = (score, dict(spacing_div=div, sign_every=se, keep=keep,
                                    dwell=dwell, sigma=sig,
                                    ratio=sig / sigma_c, per_pulse=v * dwell,
                                    pulse_n=pn))
    if best is None:
        if verbose:
            print('    cannot reach %.2f x sigma_c legally at Lambda = %.0f nm'
                  % (target_ratio, lam_nm))
        return None
    r = best[1]
    if verbose:
        print('    %.2f x sigma_c -> spacing Lambda/%.0f, sign every %d row(s), '
              'keep %.0f%%, dwell %.2f s (%.0f V.s/site), sigma %.0f'
              % (target_ratio, r['spacing_div'], r['sign_every'],
                 100 * r['keep'], r['dwell'], r['per_pulse'], r['sigma']))
    return r


def legal_offsets(st, frame_max, step=2.0, limit=SCAN_LIMIT):
    """Positions that clear every used area AND stay in the scanner range."""
    out = []
    lim = int(limit - frame_max)
    for x in range(-lim, lim + 1, int(step)):
        for y in range(-lim, lim + 1, int(step)):
            ok = True
            for a in st['used_areas']:
                (ox, oy), sz = a[0], a[1]
                need = (frame_max + sz) / 2.0 + 0.5
                if abs(x - ox) < need and abs(y - oy) < need:
                    ok = False
                    break
            if ok:
                out.append((float(x), float(y)))
    return out


def nearest_legal_offset(st, frame_max, near=None):
    """The legal position closest to `near` (default: the last area used)."""
    cands = legal_offsets(st, frame_max)
    if not cands:
        raise RuntimeError('no legal offset remains for a %.0f um frame - the '
                           'scanner box is exhausted, reposition the sample'
                           % frame_max)
    if near is None:
        near = tuple(st['used_areas'][-1][0]) if st['used_areas'] else (0.0, 0.0)
    cands.sort(key=lambda c: (c[0] - near[0]) ** 2 + (c[1] - near[1]) ** 2)
    return cands[0], len(cands)


def current_offset(verbose=True):
    """Where is the stage now? Read it from the newest frame's header.

    The operator moves to a fresh area between sessions, so the loop must READ
    the position rather than choose one. Returns (x_um, y_um, size_um, tag).
    """
    import aespm as ae
    d = resolve_folder()
    f = glob.glob(os.path.join(d, '*.ibw'))
    if not f:
        raise RuntimeError('no frames in %s' % d)
    p = max(f, key=os.path.getmtime)
    h = ae.ibw_read(p).header
    x = float(h.get('XOffset', 0.0)) * 1e6
    y = float(h.get('YOffset', 0.0)) * 1e6
    sz = float(h['ScanSize']) * 1e6
    if verbose:
        print('  stage is at (%+.1f,%+.1f), last frame %.1f um: %s, %.0f min ago'
              % (x, y, sz, os.path.basename(p),
                 (time.time() - os.path.getmtime(p)) / 60.0))
    return x, y, sz, os.path.basename(p)


def check_area_fresh(st, x, y, frame_max, verbose=True):
    """Is the stage somewhere we have not written? Returns (ok, notes)."""
    notes = []
    for a in st['used_areas']:
        (ox, oy), sz, lab = a[0], a[1], a[2]
        need = (frame_max + sz) / 2.0 + 0.5
        if abs(x - ox) < need and abs(y - oy) < need:
            notes.append('overlaps %s at (%+.1f,%+.1f) %.0f um: dx %.1f dy %.1f '
                         'against %.1f needed' % (lab, ox, oy, sz,
                                                  abs(x - ox), abs(y - oy), need))
    inrange = (abs(x) + frame_max <= SCAN_LIMIT
               and abs(y) + frame_max <= SCAN_LIMIT)
    if not inrange:
        notes.append('outside the scanner range: |off|+size = %.1f/%.1f against '
                     '%.0f' % (abs(x) + frame_max, abs(y) + frame_max,
                               SCAN_LIMIT))
    if verbose:
        if notes:
            print('  !! the current position is not usable:')
            for n in notes:
                print('     - ' + n)
            off, n = nearest_legal_offset(st, frame_max, near=(x, y))
            print('     nearest legal and clear: (%+.1f,%+.1f), %d available'
                  % (off[0], off[1], n))
        else:
            print('  position (%+.1f,%+.1f) is clear of all %d used areas and '
                  'inside the scanner range at %.0f um'
                  % (x, y, len(st['used_areas']), frame_max))
    return (not notes), notes


# ================================================== efficiency: plan a frame
# Frame time is px/rate and does NOT depend on scan size, so the imaging
# overhead of an iteration (tune-verify + 2 baselines + after + VDART) is fixed
# near 21 min. The only way to cut it PER CONDITION is to fit more conditions
# into one frame - so larger frames win on both time and wear per condition:
#
#   imaging per condition  ~  frames x size / n_panels  ~  pitch^2 / size
#   sliding  per condition  ~  frames x size x px / n_panels  ~  1 / size
#
# What binds instead is the WRITE budget, and beyond a crossover the readout
# window becomes pixel-limited rather than Lambda-limited, panels grow, and the
# gain stops:
#
#   crossover frame = 4.2 * Lambda * px / (26 * 1000) = 0.0413 * Lambda[nm]
#     at 256 px: 9.7 um at Lambda 234, 12.4 at 300, 16.0 at 388
#
# Two costs of a large frame are real and handled elsewhere:
#   - one lost frame costs more panels. Re-image rather than discard; the
#     written panels persist (PITFALLS 7.9).
#   - Lambda moved 30 % between areas 10 um apart (C2), so a frame-average would
#     mis-set commensuration for outlying panels. Use lambda_uniformity() and
#     take each panel spacing from its OWN local Lambda.
TIP_SPEED_MAX = 20.0       # um/s: the 256 px / 1 Hz / 10 um condition
FRAME_PX = 256


def plan_iteration(lam_nm, n_conditions, budget_write_min=MAX_WRITE_MIN,
                   dwell_mean=1.0, ang=1.067, r_eff=0.625, px=FRAME_PX,
                   # ang MUST be the factor of the commands actually in use.
                   # The 1.067 default is only right when the command lands
                   # near an axis; with a triad at 6/66/126 the worst member is
                   # 1.397 and the grid capacity this returns is optimistic by
                   # a factor of two. Pass it explicitly.
                   n_frames=5, hold_tip_speed=True, verbose=True):
    """Cheapest frame per condition that fits n_conditions inside the budget."""
    rows = []
    for fr in (5., 6., 7., 8., 9., 10., 11., 12., 13., 14., 16.):
        rate = min(1.0, TIP_SPEED_MAX / (2.0 * fr)) if hold_tip_speed else 1.0
        frame_min = px / rate / 60.0
        pxnm = fr / px * 1000.0
        win_l, win_p = 4.2 * lam_nm / 1000.0, 26 * pxnm / 1000.0
        win = max(win_l, win_p)
        sp = lam_nm / 2000.0
        need = win * ang + 2 * (sp + 0.10)
        n = int(max(8, 4 * round((need / sp + 1) / 4.0)))
        while (n - 1) * sp < need and n < 128:
            n += 4
        ext = (n - 1) * sp * ang
        halo = ext / 2 + r_eff
        pitch = 2 * halo + 0.10
        ay, ax = fr - 0.70 - win - 0.05, fr - 0.70
        nrow = int((ay - 2 * halo) // pitch) + 1 if ay >= 2 * halo else 0
        ncol = int((ax - 2 * halo) // pitch) + 1 if ax >= 2 * halo else 0
        cap = max(0, nrow) * max(0, ncol)
        if cap < 1:
            continue
        use = min(cap, n_conditions)
        pulses = use * n * n
        wr = pulses * dwell_mean * 1.35 / 60.0
        img = n_frames * frame_min
        rows.append(dict(frame=fr, rate=rate, pxnm=pxnm, win=win,
                         limit=('Lambda' if win_l >= win_p else 'pixels'),
                         n=n, ext=ext, halo=halo, pitch=pitch,
                         grid=(ncol, nrow), cap=cap, use=use, pulses=pulses,
                         write_min=wr, img_min=img, total_min=img + wr,
                         per_cond=(img + wr) / use, tip_speed=2 * fr * rate,
                         fits=(use >= n_conditions and wr <= budget_write_min)))
    if not rows:
        return None
    ok = [r for r in rows if r['fits']]
    pick = (min(ok, key=lambda r: r['per_cond']) if ok else
            min(rows, key=lambda r: (-r['use'], r['per_cond'])))
    if verbose:
        print('  planning %d condition(s), Lambda %.0f nm, budget %.0f min of '
              'writing, mean dwell %.2f s'
              % (n_conditions, lam_nm, budget_write_min, dwell_mean))
        print('  %6s%6s%7s%8s%8s%5s%7s%6s%8s%8s%10s  %s'
              % ('frame', 'rate', 'um/s', 'window', 'limit', 'n', 'grid',
                 'cap', 'write', 'total', 'min/cond', ''))
        for r in rows:
            tail = ('<- chosen' if r is pick else
                    ('over budget' if r['write_min'] > budget_write_min else
                     ('only %d fit' % r['cap'] if r['cap'] < n_conditions
                      else '')))
            print('  %6.0f%6.2f%7.1f%8.2f%8s%5d%7s%6d%8.0f%8.0f%10.1f  %s'
                  % (r['frame'], r['rate'], r['tip_speed'], r['win'],
                     r['limit'], r['n'], '%dx%d' % r['grid'], r['cap'],
                     r['write_min'], r['total_min'], r['per_cond'], tail))
        if not ok:
            print('  !! %d conditions do not fit in the budget. Best is %d in a '
                  '%.0f um frame at %.0f min of writing.'
                  % (n_conditions, pick['use'], pick['frame'],
                     pick['write_min']))
            print('     Shorten the dwell, split across two iterations, or '
                  'raise the budget deliberately - do not quietly overrun.')
    return pick


def lambda_uniformity(ns, tag, centres, win_um, triad, verbose=True):
    """Lambda at each panel position, not once for the whole frame.

    C2: Lambda ran 231-410 nm across areas and moved 10-15 % per 10 um. A
    frame-average mis-sets the Lambda/2 spacing, and therefore commensuration,
    for panels far from where it was measured.
    """
    ibw, signed, period = ns['ibw'], ns['signed'], ns['period']
    d, h = ibw(tag)
    L = float(h['ScanSize']) * 1e6
    N = d[0].shape[0]
    pxnm = L / N * 1000.0
    S, _, _ = signed(d)
    out = []
    for (cx, cy) in centres:
        i0 = max(int((cy - win_um / 2) / L * N), 0)
        i1 = min(int((cy + win_um / 2) / L * N), N)
        j0 = max(int((cx - win_um / 2) / L * N), 0)
        j1 = min(int((cx + win_um / 2) / L * N), N)
        sub = S[i0:i1, j0:j1]
        # period() applies a 1-D window per axis and needs a SQUARE block, the
        # same way dir_power crops to S[:n,:n]. A 35x34 sub-array raised
        # "operands could not be broadcast together".
        m = min(sub.shape)
        sub = sub[:m, :m]
        vals = []
        if m >= 16:
            for f in triad:
                v = period(sub, pxnm, f)
                v = (float(v[0]) if isinstance(v, (tuple, list, np.ndarray))
                     else float(v))
                if v == v:
                    vals.append(v)
        out.append(float(np.nanmedian(vals)) if vals else float('nan'))
    arr = np.array(out, dtype=float)
    good = arr[np.isfinite(arr)]
    spread = float((good.max() - good.min()) / good.mean()) if len(good) > 1 \
        else 0.0
    if verbose:
        print('  local Lambda per panel: '
              + '  '.join(('%.0f' % v) if v == v else 'nan' for v in arr)
              + ' nm')
        print('    mean %.0f nm, spread %.0f %% across the frame'
              % (good.mean() if len(good) else float('nan'), 100 * spread))
        if spread > 0.15:
            print('    !! over 15 %% - use the PER-PANEL value for each')
            print('       spacing. With a frame-average, the outlying panels')
            print('       would be off resonance, which is the difference')
            print('       between testing Condition 1 and confounding it.')
    return arr, spread
