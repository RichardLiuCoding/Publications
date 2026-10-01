"""Cross-validated re-estimate of Step-2 descriptor recovery (revision 2026-09).

The submitted Step-2 numbers came from one 75/25 curve split whose held-out curves were
also used to accept/reject options (weight decay, ReLoBRaLo, Fourier features,
uncertainty head). Here every curve is held out exactly once (5-fold CV over FD curves),
with the configuration fixed at the submitted defaults, and the unsupervised
consistency terms restricted to TRAINING curves (the submitted code evaluated them on all
curves). Curves that were in the ORIGINAL training split never informed a design choice,
so their CV errors are reported separately as the least-biased estimate.

The submitted notebook code is executed unmodified except for (i) FIG_DIR redirection,
(ii) the fold split, and (iii) the train-only masks on L_cons / L_ode.
python rv_step2_cv.py tap300|multi75
"""
from __future__ import annotations

import json
import os
import sys
import time
import types

import matplotlib
matplotlib.use("Agg")
import numpy as np
import nbformat

from rv_common import OUT, ROOT

SYSTEMS = {
    "tap300": dict(nb=ROOT / "DT-SPM_colab" / "DT-SPM_full_digital_twin.ipynb", cwd=ROOT / "DT-SPM_colab",
                   setup_cell=3, vocab_cell=40, train_cell=42),
    "multi75": dict(nb=ROOT / "DT-SPM framework TRANSFER — Multi75 cali.ipynb", cwd=ROOT,
                    setup_cell=2, vocab_cell=39, train_cell=41),
}


def strict(src):
    a = "    for epoch in range(N_EPOCH):"
    assert a in src
    src = src.replace(a, "    _tr_t = torch.as_tensor(np.asarray(fd_train_idx), dtype=torch.long)\n" + a, 1)
    b = "L_cons = (A0_param_z - anchors[:, iA0]).pow(2).mean()"
    c = "L_ode = d2A.pow(2).mean() * 1e-3"
    assert b in src and c in src
    src = src.replace(b, "L_cons = (A0_param_z - anchors[:, iA0])[_tr_t].pow(2).mean()")
    src = src.replace(c, "L_ode = d2A[_tr_t].pow(2).mean() * 1e-3")
    return src


def main(sysname, n_folds=5, seed=1):
    cfg = SYSTEMS[sysname]
    run = OUT / f"step2_cv_{sysname}"; run.mkdir(parents=True, exist_ok=True)
    nb = nbformat.read(cfg["nb"], as_version=4)
    os.chdir(cfg["cwd"])
    mod = types.ModuleType(f"__cv_{sysname}__"); sys.modules[mod.__name__] = mod
    ns = mod.__dict__
    t0 = time.time()
    for i, c in enumerate(nb.cells):
        if c.cell_type != "code" or i > cfg["vocab_cell"] + 1:
            continue
        exec(compile(c.source, f"<cell {i}>", "exec"), ns)
        if i == cfg["setup_cell"]:
            ns["FIG_DIR"] = run
    print(f"[{sysname}] setup cells in {time.time()-t0:.0f} s", flush=True)
    orig_train = np.asarray(ns["fd_train_idx"]); orig_test = np.asarray(ns["fd_test_idx"])
    N = len(orig_train) + len(orig_test)
    train_src = strict(nb.cells[cfg["train_cell"]].source)
    vocab = list(ns["VOCAB_COLS"]); wts = np.array([ns["VOCAB_WEIGHTS"][c] for c in vocab])
    rng = np.random.default_rng(seed); perm = rng.permutation(N)
    folds = [np.sort(perm[k::n_folds]) for k in range(n_folds)]
    pred_phys = np.full((N, len(vocab)), np.nan); err_z = np.full((N, len(vocab)), np.nan)
    err_z_prior = np.full((N, len(vocab)), np.nan)
    for k, te in enumerate(folds):
        tr = np.setdiff1d(np.arange(N), te)
        ns["fd_train_idx"], ns["fd_test_idx"] = tr, te
        t1 = time.time()
        exec(compile(train_src, f"<train fold {k}>", "exec"), ns)
        tgt = ns["target_full"]; mu, sig = ns["mu"], ns["sig"]
        az = ns["anchors_np"] if "anchors_np" in ns else None
        if az is None:
            raise RuntimeError("anchors_np not found in namespace")
        pz = np.asarray(az)
        pred_phys[te] = pz[te] * sig + mu
        tz = (tgt - mu) / sig
        err_z[te] = np.abs(pz[te] - tz[te])
        med_tr = np.nanmedian(tz[tr], axis=0)
        err_z_prior[te] = np.abs(med_tr[None, :] - tz[te])
        print(f"[{sysname}] fold {k}: {len(tr)} train / {len(te)} test curves, {time.time()-t1:.0f} s", flush=True)
    tgt = ns["target_full"]
    fin = np.isfinite(tgt)

    def tw_mae(E, rows):
        m = fin[rows] & np.isfinite(E[rows])
        W = np.where(m, wts[None, :], 0.0)
        return float(np.nansum(np.where(m, E[rows], 0) * W) / W.sum())

    allr = np.arange(N)
    res = dict(system=sysname, n_curves=int(N), n_folds=n_folds,
               tier_weighted_MAE_z=dict(all=tw_mae(err_z, allr), orig_train_curves=tw_mae(err_z, orig_train),
                                        orig_heldout_curves=tw_mae(err_z, orig_test)),
               train_median_prior_MAE_z=dict(all=tw_mae(err_z_prior, allr)),
               per_anchor_median_abs_err_phys={}, per_anchor_n={})
    for j, c in enumerate(vocab):
        m = fin[:, j]
        e = np.abs(pred_phys[m, j] - tgt[m, j])
        res["per_anchor_median_abs_err_phys"][c] = float(np.median(e)) if e.size else None
        res["per_anchor_n"][c] = int(m.sum())
    np.savez(run / "cv_predictions.npz", pred_phys=pred_phys, target=tgt, vocab=np.array(vocab),
             folds=np.array([np.isin(np.arange(N), f) for f in folds]), orig_train=orig_train,
             orig_test=orig_test)
    json.dump(res, open(OUT / f"step2_cv_{sysname}.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    import torch
    torch.set_num_threads(2)
    main(sys.argv[1])
