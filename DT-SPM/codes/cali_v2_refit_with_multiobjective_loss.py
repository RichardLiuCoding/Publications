"""Refit the calibration-grating v2 PI map under the multi-objective loss.

Pipeline:
1. Load `/tmp/cali_v2_basics.npz` and `/tmp/cali_v2_pipeline.npz`.
2. Build the scanner (same architecture as the v2 notebook).
3. For each fit-set condition, run a grid search + Nelder-Mead local refine
   over (log10 P, log10 I) using `multi_objective_loss`.  Cache the new
   labels in `calibration_cache/calibration_grating_v2/local_PI_fits_multi.joblib`.
4. Train a Ridge map (same architecture) on the new labels.
5. Run the DT for every condition with the new ridge prediction.
6. Refit the data-driven and hybrid Ridge models on the new DT outputs.
7. Overwrite `/tmp/cali_v2_predictions.npz` with the new predictions, plus
   per-example loss decompositions for the three I-gain regimes.

The output cache is consumed by the existing
`codes/nature_cali_grating_figures.py`; Figures 4 and 5 are then rebuilt
unchanged from the new data.
"""
from __future__ import annotations

import json, sys, time, importlib
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import dump, load
from scipy.optimize import minimize


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from codes.cali_v2_multiobjective_loss import (
    multi_objective_loss, behaviour_signature, DEFAULT_WEIGHTS,
)  # noqa: F401  - behaviour_signature reused inside fit_local_multi


# Example conditions for the three I-gain regimes (small / optimal / large)
EXAMPLES = dict(
    small_I   = 7,
    optimal_I = 28,
    large_I   = 12,
)


def setup_scanner():
    import codes.Scanner_fixed_extended_fd as sfe
    import codes.Scanner_numba_substeps_v3 as sn
    importlib.reload(sfe); importlib.reload(sn)
    sn.install_numba_substep_methods(sfe.ScannerFD, verbose=False)
    from codes.dt_static_dynamic_calibration_scaffold_v3 import (
        ScannerRunConfig, run_scanner_line, get_height_from_out,
    )

    b = np.load('/tmp/cali_v2_basics.npz')
    fd_drive_nm = b['fd_drive_nm']; fd_height = b['fd_height']
    fd_amp = b['fd_amp']; fd_phase = b['fd_phase']
    measured_fd = {float(fd_drive_nm[i]): {'d': fd_height[i], 'A': fd_amp[i], 'phi': fd_phase[i]}
                   for i in range(len(fd_drive_nm))}
    surface = sfe.FDDriveSurface.from_measured_fd(
        measured_fd, x_mode='d_over_A0', common_range='union', n_x=1024,
        extend_to_zero_amplitude=True, extension_n_fit=5, extension_n_bridge=30,
        extension_phi_mode='linear', extension_F_mode='nearest',
    )
    params = {'k':25,'A':float(np.nanmedian(fd_amp)),'d0':float(np.nanmax(fd_height)*0.8),
              'R':10,'H':1e-19,'E_star':1e9,'Q':250}
    scanner = sfe.ScannerFD(params=params, conversions={k:1.0 for k in params},
                            fd_model=sfe.make_normalized_fd_lookup(surface, conv_L=1.0))
    cfg = ScannerRunConfig(
        dx_hat=1.0, n_substeps=50, tau_A=None, tau_phi=None, tau_z=None,
        z_rate_limit_hat=1e6, d_init_hat=0.0, A_meas_init_hat=1.0,
        phi_meas_init_deg=120.0, T_I=3e-1, h_smooth_sigma_px=0.0,
        fd_n_d=4096, use_fast=True,
    )
    return scanner, cfg, run_scanner_line, get_height_from_out


def main(*, n_grid_P=9, n_grid_I=9, maxiter_local=60,
         weights=None, force_refit=False, verbose=True):
    weights = weights or DEFAULT_WEIGHTS

    print('Setting up scanner...')
    scanner, scanner_cfg, run_scanner_line, get_height_from_out = setup_scanner()

    b  = np.load('/tmp/cali_v2_basics.npz')
    p2 = np.load('/tmp/cali_v2_pipeline.npz')
    traces_exp   = b['traces_exp']
    drive_exp    = b['drive_exp']
    setpoint_exp = b['setpoint_exp']
    igain_exp    = b['igain_exp']
    scan_rate_exp = b['scan_rate_exp']
    h_truth         = p2['h_truth']
    informative_mask = p2['informative_mask']
    N_COND = traces_exp.shape[0]

    FD_TABLE = {}
    def _fd_table_for(d):
        k = round(float(d), 4)
        if k not in FD_TABLE:
            FD_TABLE[k] = scanner.prepare_fd_table_for_drive(float(d), n_d=scanner_cfg.fd_n_d)
        return FD_TABLE[k]

    def run_dt(i, P, I, h_line=None):
        if h_line is None: h_line = h_truth
        out = run_scanner_line(scanner, h_line, drive_nm=float(drive_exp[i]),
            setpoint=float(setpoint_exp[i]), scan_speed_hat=float(scan_rate_exp[i]),
            P=float(P), I=float(I), cfg=scanner_cfg, fd_table=_fd_table_for(drive_exp[i]))
        return get_height_from_out(out)

    # Train/test split matches the v2 notebook
    RANDOM_SEED = 35
    info_idx = np.where(informative_mask)[0]
    rng = np.random.default_rng(RANDOM_SEED)
    shuffled = rng.permutation(info_idx)
    fit_idx  = np.sort(shuffled[:40])
    test_idx = np.sort(shuffled[40:60])
    print(f'fit_idx: {len(fit_idx)}, test_idx: {len(test_idx)}')

    cache_dir = PROJECT_ROOT / 'calibration_cache' / 'calibration_grating_v2'
    cache_path = cache_dir / 'local_PI_fits_multi.joblib'

    bounds = ((-2.5, 2.0), (-1.5, 3.0))   # log10 bounds
    lp_grid = np.linspace(bounds[0][0], bounds[0][1], n_grid_P)
    li_grid = np.linspace(bounds[1][0], bounds[1][1], n_grid_I)

    def fit_local_multi(i):
        from codes.dt_gp_static_calibration_v3 import diff_shifted
        exp_tr = traces_exp[i, 0]; exp_rt = traces_exp[i, 1]
        exp_sig_cached = behaviour_signature(exp_tr, exp_rt)

        # Pre-compute experimental signature (used inside loss)
        def L(lp, li):
            try:
                sim_tr, sim_rt = run_dt(int(i), 10.0**lp, 10.0**li)
            except Exception:
                return 1e6
            sa_tr, ea_tr = diff_shifted(sim_tr, exp_tr)
            sa_rt, ea_rt = diff_shifted(sim_rt, exp_rt)
            return multi_objective_loss(
                sim_tr, sim_rt, exp_tr, exp_rt, weights=weights,
                aligned_pairs=((sa_tr, ea_tr), (sa_rt, ea_rt)),
                exp_sig=exp_sig_cached,
            )

        # Grid search
        best = (lp_grid[len(lp_grid)//2], li_grid[len(li_grid)//2], np.inf)
        for lp in lp_grid:
            for li in li_grid:
                l = L(lp, li)
                if l < best[2]:
                    best = (float(lp), float(li), float(l))

        # Local refinement
        res = minimize(
            lambda x: L(x[0], x[1]),
            x0=np.array([best[0], best[1]]),
            method='Nelder-Mead',
            options={'xatol': 0.01, 'fatol': 1e-2, 'maxiter': maxiter_local},
        )
        if res.fun < best[2]:
            lp, li, ll = float(res.x[0]), float(res.x[1]), float(res.fun)
        else:
            lp, li, ll = best
        lp = float(np.clip(lp, bounds[0][0], bounds[0][1]))
        li = float(np.clip(li, bounds[1][0], bounds[1][1]))
        return {'cond': int(i), 'log10_P': lp, 'log10_I': li,
                'P': 10.0**lp, 'I': 10.0**li, 'loss': float(ll)}

    # Resume support: if a partial joblib exists, keep already-fitted
    # conditions and continue with the rest unless --force-refit.
    if cache_path.exists() and not force_refit:
        partial = load(cache_path)
        done = {int(r['cond']) for r in partial}
        local_fits = list(partial)
        if len(done) >= len(fit_idx):
            print(f'loaded {cache_path}  (complete: {len(local_fits)} fits)')
        else:
            print(f'loaded {cache_path}  ({len(local_fits)}/{len(fit_idx)} fits done, '
                   f'continuing)')
    else:
        local_fits = []; done = set()

    remaining = [int(i) for i in fit_idx if int(i) not in {int(r['cond']) for r in local_fits}]
    if remaining:
        print(f'Fitting {len(remaining)} remaining conditions under multi-objective loss...')
        t0 = time.time()
        for k, i in enumerate(remaining):
            r = fit_local_multi(int(i))
            local_fits.append(r)
            elapsed = time.time() - t0
            if verbose:
                k_total = len(local_fits)
                print(f'  [{k_total:3d}/{len(fit_idx)}] cond={int(i):2d} '
                       f'loss={r["loss"]:.2f}  log10P={r["log10_P"]:+.2f} '
                       f'log10I={r["log10_I"]:+.2f}  elapsed={elapsed:.1f}s', flush=True)
            if (k+1) % 5 == 0 or (k+1) == len(remaining):
                dump(local_fits, cache_path)
        print(f'  Saved {cache_path}   elapsed {(time.time()-t0)/60:.2f} min')

    local_df = pd.DataFrame(local_fits)
    print(local_df.describe()[['log10_P','log10_I','loss']])

    # --- Train ridge map on new labels ----------------------------------
    from sklearn.linear_model import RidgeCV, Ridge
    from sklearn.preprocessing import PolynomialFeatures, StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer

    FEATURES = ['log_scan_speed', 'drive_nm', 'setpoint', 'log_I_exp']
    def cf(i):
        return {'log_scan_speed': float(np.log10(max(scan_rate_exp[int(i)], 1e-12))),
                'drive_nm': float(drive_exp[int(i)]),
                'setpoint': float(setpoint_exp[int(i)]),
                'log_I_exp': float(np.log10(max(igain_exp[int(i)], 1e-12)))}

    bound_lo_P, bound_hi_P = -2.5, 2.0
    bound_lo_I, bound_hi_I = -1.5, 3.0
    log10P = local_df['log10_P'].to_numpy(float)
    log10I = local_df['log10_I'].to_numpy(float)
    loss = local_df['loss'].to_numpy(float)
    hit_P = (np.abs(log10P-bound_lo_P)<0.05)|(np.abs(log10P-bound_hi_P)<0.05)
    hit_I = (np.abs(log10I-bound_lo_I)<0.05)|(np.abs(log10I-bound_hi_I)<0.05)
    loss_cap = np.nanpercentile(loss[np.isfinite(loss)], 80)
    clean_mask = (np.isfinite(log10P) & np.isfinite(log10I) & np.isfinite(loss)
                  & ~(hit_P|hit_I) & (loss<loss_cap))
    train_records = []
    for keep, rec in zip(clean_mask, local_fits):
        if not keep: continue
        f = cf(rec['cond']); f.update({'log10_P': rec['log10_P'], 'log10_I': rec['log10_I']})
        train_records.append(f)
    train_df = pd.DataFrame(train_records)
    print(f'ridge training rows: {len(train_df)}')

    ridge_PI = make_pipeline(
        SimpleImputer(strategy='median'),
        PolynomialFeatures(degree=2, include_bias=False),
        StandardScaler(),
        RidgeCV(alphas=np.logspace(-3,3,25), cv=min(5,max(2,len(train_df)))),
    )
    ridge_PI.fit(train_df[FEATURES].to_numpy(float),
                  train_df[['log10_P','log10_I']].to_numpy(float))

    def predict_PI(idxs):
        feats = np.array([[cf(i)[c] for c in FEATURES] for i in idxs], float)
        lp = ridge_PI.predict(feats)
        lp[:,0] = np.clip(lp[:,0], bound_lo_P, bound_hi_P)
        lp[:,1] = np.clip(lp[:,1], bound_lo_I, bound_hi_I)
        return 10.0**lp[:,0], 10.0**lp[:,1]

    all_idx = np.arange(N_COND)
    P_all, I_all = predict_PI(all_idx)

    # --- Run DT for every condition with new ridge predictions ----------
    print('Running DT for all conditions under new PI...')
    t0 = time.time()
    dt_PI = np.zeros_like(traces_exp)
    for i in all_idx:
        sim_tr, sim_rt = run_dt(int(i), P_all[i], I_all[i])
        n = min(len(sim_tr), traces_exp.shape[-1])
        dt_PI[i,0,:n] = sim_tr[:n]
        dt_PI[i,1,:n] = sim_rt[:n]
    print(f'  done in {time.time()-t0:.1f}s')

    # --- DT with local-oracle PI on fit_idx (for figure 4 oracle scatter)
    oracle_PI = {r['cond']: (r['P'], r['I']) for r in local_fits}
    dt_oracle = np.full_like(traces_exp, np.nan)
    for i in fit_idx:
        if int(i) in oracle_PI:
            P,I = oracle_PI[int(i)]
            sim_tr, sim_rt = run_dt(int(i), P, I)
            n = min(len(sim_tr), traces_exp.shape[-1])
            dt_oracle[i,0,:n] = sim_tr[:n]; dt_oracle[i,1,:n] = sim_rt[:n]

    # --- Refit data-driven and hybrid Ridge models on NEW DT outputs -----
    def features_for(i):
        d = float(drive_exp[int(i)]); sp = float(setpoint_exp[int(i)])
        ig = float(igain_exp[int(i)]); A0 = float(scanner.get_A0_hat(d))
        log_ig = float(np.log10(max(ig, 1e-12)))
        return [d, sp, ig, log_ig, A0, np.log10(max(A0,1e-12)),
                d*sp, d*log_ig, sp*log_ig, A0*sp]

    X = np.array([features_for(i) for i in all_idx], float)
    Y_trace = traces_exp[:,0,:].copy(); Y_retrace = traces_exp[:,1,:].copy()
    def center(arr, trim=10):
        arr = arr.copy()
        for i in range(arr.shape[0]):
            arr[i] = arr[i] - np.nanmean(arr[i, trim:-trim])
        return arr
    Yt_c = center(Y_trace); Yr_c = center(Y_retrace)

    Xtr = X[fit_idx]; Yt_tr = Yt_c[fit_idx]; Yr_tr = Yr_c[fit_idx]
    poly = PolynomialFeatures(degree=2, include_bias=False)
    scaler = StandardScaler()
    Xtr_poly = scaler.fit_transform(poly.fit_transform(Xtr))
    Xall_poly = scaler.transform(poly.transform(X))

    ridge_trace = Ridge(alpha=10.0).fit(Xtr_poly, Yt_tr)
    ridge_retr  = Ridge(alpha=10.0).fit(Xtr_poly, Yr_tr)
    dd_PI = np.zeros_like(traces_exp)
    dd_PI[:,0,:] = ridge_trace.predict(Xall_poly)
    dd_PI[:,1,:] = ridge_retr.predict(Xall_poly)

    dt_PI_c = np.zeros_like(dt_PI)
    dt_PI_c[:,0,:] = center(dt_PI[:,0,:]); dt_PI_c[:,1,:] = center(dt_PI[:,1,:])
    Rt = Yt_c - dt_PI_c[:,0,:]; Rr = Yr_c - dt_PI_c[:,1,:]
    ridge_res_t = Ridge(alpha=10.0).fit(Xtr_poly, Rt[fit_idx])
    ridge_res_r = Ridge(alpha=10.0).fit(Xtr_poly, Rr[fit_idx])
    hyb = np.zeros_like(traces_exp)
    hyb[:,0,:] = dt_PI_c[:,0,:] + ridge_res_t.predict(Xall_poly)
    hyb[:,1,:] = dt_PI_c[:,1,:] + ridge_res_r.predict(Xall_poly)

    # --- Quality / per-line RMSE ----------------------------------------
    from codes.dt_gp_static_calibration_v3 import diff_shifted
    def line_rmse(pred, exp, trim=10):
        sa, ea = diff_shifted(pred, exp)
        n = min(len(sa), len(ea))
        if n <= 2*trim+4: lo,hi = 0,n
        else: lo,hi = trim, n-trim
        sc = sa[lo:hi]-np.nanmean(sa[lo:hi]); ec = ea[lo:hi]-np.nanmean(ea[lo:hi])
        m = np.isfinite(sc) & np.isfinite(ec)
        if m.sum() < 5: return np.nan
        return float(np.sqrt(np.nanmean((sc[m]-ec[m])**2)))

    def model_rmse(arr):
        out = np.zeros((arr.shape[0], 2))
        for i in range(arr.shape[0]):
            out[i,0] = line_rmse(arr[i,0], traces_exp[i,0])
            out[i,1] = line_rmse(arr[i,1], traces_exp[i,1])
        return out

    def trrt(arr, trim=10):
        out = np.zeros(arr.shape[0])
        for i in range(arr.shape[0]):
            t = arr[i,0,trim:-trim]-np.nanmean(arr[i,0,trim:-trim])
            r = arr[i,1,trim:-trim]-np.nanmean(arr[i,1,trim:-trim])
            m = np.isfinite(t) & np.isfinite(r)
            out[i] = float(np.sqrt(np.nanmean((t[m]-r[m])**2))) if m.sum() >=5 else np.nan
        return out

    q_exp = trrt(traces_exp)
    q_PI  = trrt(dt_PI)
    q_dd  = trrt(dd_PI)
    q_hyb = trrt(hyb)
    rmse_PI  = model_rmse(dt_PI)
    rmse_dd  = model_rmse(dd_PI)
    rmse_hyb = model_rmse(hyb)

    # --- Demonstration fits for the 3 example regimes -------------------
    # The three I-gain examples may or may not be in fit_idx.  Run a
    # dedicated local fit per example with the new loss so we can show the
    # best (P, I) the multi-objective optimizer picks for each regime,
    # alongside the corresponding DT trace/retrace.
    print('Running per-example demonstration fits...')
    demo_fits = {}
    for name, ci in EXAMPLES.items():
        t_demo = time.time()
        rec = fit_local_multi(int(ci))
        demo_fits[name] = rec
        # DT trace/retrace at the new optimum
        sim_tr, sim_rt = run_dt(int(ci), rec['P'], rec['I'])
        # Also store an "old-loss" baseline: DT with the ridge prediction
        # before any multi-objective refit (use shape-only PI from a fresh
        # grid search on the original cali_v2 loss).
        rec.update({
            'sim_tr': sim_tr.tolist(),
            'sim_rt': sim_rt.tolist(),
            'elapsed_s': round(time.time() - t_demo, 1),
        })
        print(f'  {name:9s} cond={ci:2d}  '
               f'P*={rec["P"]:.3g}  I*={rec["I"]:.3g}  loss={rec["loss"]:.2f}  '
               f'({rec["elapsed_s"]}s)')

    # --- Three-example per-regime decomposition --------------------------
    examples = []
    for name, ci in EXAMPLES.items():
        # Use the per-example demonstration fit, not the ridge prediction —
        # this is what the loss actually wants the DT to do for this cond.
        d = demo_fits[name]
        sim_tr = np.asarray(d['sim_tr']); sim_rt = np.asarray(d['sim_rt'])
        exp_tr = traces_exp[ci,0]; exp_rt = traces_exp[ci,1]
        _, comps = multi_objective_loss(sim_tr, sim_rt, exp_tr, exp_rt,
                                         weights=weights, return_components=True)
        # Cast every entry to JSON-friendly types
        sim_sig = {k: float(v) if v is not None else None for k,v in comps['sim_sig'].items()}
        exp_sig = {k: float(v) if v is not None else None for k,v in comps['exp_sig'].items()}
        examples.append({
            'regime':   name,
            'cond':     int(ci),
            'drive':    float(drive_exp[ci]),
            'setpoint': float(setpoint_exp[ci]),
            'igain_exp':float(igain_exp[ci]),
            'P_ridge':  float(P_all[ci]),
            'I_ridge':  float(I_all[ci]),
            'shape_mse': float(comps['shape_mse']),
            'trrt_term': float(comps['trrt']),
            'hf_term':   float(comps['hf']),
            'grad_term': float(comps['grad']),
            'sim_sig':   sim_sig,
            'exp_sig':   exp_sig,
        })

    # Save examples to JSON for inspection
    examples_path = Path('/tmp/cali_v2_three_examples.json')
    examples_path.write_text(json.dumps(examples, indent=2))
    print('Saved', examples_path)

    # --- Save predictions cache (overwrites v2 shape) -------------------
    # Bundle DT traces from the per-example demonstration fits so the figure
    # script can plot them without re-running the scanner.
    demo_sim_tr = np.stack([np.asarray(demo_fits[k]['sim_tr'])
                             for k in ('small_I','optimal_I','large_I')], axis=0)
    demo_sim_rt = np.stack([np.asarray(demo_fits[k]['sim_rt'])
                             for k in ('small_I','optimal_I','large_I')], axis=0)
    demo_PI = np.array([(demo_fits[k]['P'], demo_fits[k]['I'])
                         for k in ('small_I','optimal_I','large_I')], float)
    demo_cond_idx = np.array([EXAMPLES['small_I'], EXAMPLES['optimal_I'],
                               EXAMPLES['large_I']], int)

    np.savez('/tmp/cali_v2_predictions.npz',
        fit_idx=fit_idx, test_idx=test_idx,
        h_truth=h_truth,
        traces_exp=traces_exp,
        dt_PI=dt_PI, dt_oracle=dt_oracle,
        dd=dd_PI, hyb=hyb,
        P_all=P_all, I_all=I_all,
        q_exp=q_exp, q_PI=q_PI, q_dd=q_dd, q_hyb=q_hyb,
        rmse_PI=rmse_PI, rmse_dd=rmse_dd, rmse_hyb=rmse_hyb,
        drive_exp=drive_exp, setpoint_exp=setpoint_exp, igain_exp=igain_exp,
        # NEW: three example regime indices, demo DT traces, and demo PI
        example_cond_small_I=EXAMPLES['small_I'],
        example_cond_optimal_I=EXAMPLES['optimal_I'],
        example_cond_large_I=EXAMPLES['large_I'],
        demo_cond_idx=demo_cond_idx,
        demo_sim_tr=demo_sim_tr,
        demo_sim_rt=demo_sim_rt,
        demo_PI=demo_PI,
    )
    # Also write a JSON summary of the multi-objective loss weights used
    Path('/tmp/cali_v2_multi_loss_weights.json').write_text(json.dumps(weights, indent=2))

    print('\nNew held-out medians:')
    print(f'  PI  line RMSE median: {float(np.nanmedian(np.nanmean(rmse_PI[test_idx],axis=1))):.3f} nm')
    print(f'  DD  line RMSE median: {float(np.nanmedian(np.nanmean(rmse_dd[test_idx],axis=1))):.3f} nm')
    print(f'  HYB line RMSE median: {float(np.nanmedian(np.nanmean(rmse_hyb[test_idx],axis=1))):.3f} nm')
    print('\nThree-example experimental vs DT behavioural signatures:')
    for ex in examples:
        s, e = ex['sim_sig'], ex['exp_sig']
        print(f"  {ex['regime']:9s} cond={ex['cond']:2d}  Ig={ex['igain_exp']:6.1f}  "
               f"trrt sim/exp={s['trrt']:.2f}/{e['trrt']:.2f}  "
               f"hf_tr sim/exp={s['hf_tr']:.2f}/{e['hf_tr']:.2f}  "
               f"gm_tr sim/exp={s['gm_tr']:.3f}/{e['gm_tr']:.3f}")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--force-refit', action='store_true')
    p.add_argument('--w-shape', type=float, default=DEFAULT_WEIGHTS['w_shape'])
    p.add_argument('--w-trrt',  type=float, default=DEFAULT_WEIGHTS['w_trrt'])
    p.add_argument('--w-hf',    type=float, default=DEFAULT_WEIGHTS['w_hf'])
    p.add_argument('--w-grad',  type=float, default=DEFAULT_WEIGHTS['w_grad'])
    args = p.parse_args()
    main(weights=dict(w_shape=args.w_shape, w_trrt=args.w_trrt,
                       w_hf=args.w_hf, w_grad=args.w_grad),
         force_refit=args.force_refit)
