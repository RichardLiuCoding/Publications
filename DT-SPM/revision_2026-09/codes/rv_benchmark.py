"""Causal pre-acquisition benchmark (revision 2026-09).

Every model below sees only pre-acquisition inputs (see rv_tap300.py docstring).
Outer folds hold out whole control-space blocks; hyperparameters and the loss
function are chosen by grouped inner cross-validation on the outer-training
conditions only; all scaling/imputation is refitted inside each fit.
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.stats import spearmanr
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

warnings.filterwarnings("ignore")
NJ = 10   # grid points in parallel; each model single-threaded (OMP_NUM_THREADS=1)


# ---------------------------------------------------------------- folds
def block_folds(groups, n_folds, seed=2026):
    """Randomly assign whole groups to folds, balancing fold sizes."""
    rng = np.random.default_rng(seed)
    ug = rng.permutation(np.unique(groups))
    sizes = {g: int((groups == g).sum()) for g in ug}
    load = np.zeros(n_folds); assign = {}
    for g in sorted(ug, key=lambda g: -sizes[g]):          # greedy balance
        f = int(np.argmin(load)); assign[g] = f; load[f] += sizes[g]
    fold = np.array([assign[g] for g in groups])
    return [np.where(fold == f)[0] for f in range(n_folds)]


# ---------------------------------------------------------------- models
def _inner(groups, n=4):
    return GroupKFold(n_splits=min(n, len(np.unique(groups))))


def _hgb_grid(n=None):
    leaf = [10, 30] if (n is None or n >= 200) else [v for v in (2, 5, 10, 30) if v < max(3, n // 3)] or [2]
    return {"learning_rate": [0.05], "max_leaf_nodes": [7, 15],
            "min_samples_leaf": leaf, "loss": ["squared_error", "absolute_error"]}


class ConstMedian(BaseEstimator, RegressorMixin):
    def fit(self, X, y, **kw):
        self.c_ = float(np.median(y)); return self

    def predict(self, X):
        return np.full(len(X), self.c_)


def fit_predict(name, Xtr, ytr, gtr, Xte, prior_tr=None, prior_te=None, seed=0,
                fixed_loss=None):
    """Return (prediction on Xte in target space, chosen params)."""
    inner = _inner(gtr)
    sc = "neg_mean_absolute_error"
    if name == "median":
        return ConstMedian().fit(Xtr, ytr).predict(Xte), {}
    if name == "physics":
        return prior_te.copy(), {}
    if name == "physics_cal":                                     # y = a + b*prior
        A = np.c_[np.ones_like(prior_tr), prior_tr]
        w = np.linalg.lstsq(A, ytr, rcond=None)[0]
        return w[0] + w[1] * prior_te, {"a": w[0], "b": w[1]}
    if name == "knn":
        pipe = Pipeline([("s", StandardScaler()), ("m", KNeighborsRegressor())])
        g = GridSearchCV(pipe, {"m__n_neighbors": [3, 5, 10, 20],
                                "m__weights": ["uniform", "distance"]}, cv=inner, scoring=sc, n_jobs=NJ)
        g.fit(Xtr, ytr, groups=gtr)
        return g.predict(Xte), g.best_params_
    if name in ("gbm", "hyb_gbm"):
        grid = _hgb_grid(len(ytr))
        if fixed_loss:
            grid["loss"] = [fixed_loss]
        m = HistGradientBoostingRegressor(max_iter=200, random_state=seed)
        if name == "hyb_gbm":
            Xtr_, Xte_ = np.c_[Xtr, prior_tr], np.c_[Xte, prior_te]
            ytr_ = ytr - prior_tr
        else:
            Xtr_, Xte_, ytr_ = Xtr, Xte, ytr
        g = GridSearchCV(m, grid, cv=inner, scoring=sc, n_jobs=NJ)
        g.fit(Xtr_, ytr_, groups=gtr)
        p = g.predict(Xte_)
        return (p + prior_te if name == "hyb_gbm" else p), g.best_params_
    if name == "ridge":                                           # quadratic ridge, no prior
        pipe = Pipeline([("s", StandardScaler()), ("p", PolynomialFeatures(2, include_bias=False)),
                         ("s2", StandardScaler()), ("m", Ridge())])
        grid = [{"m": [Ridge()], "m__alpha": [0.1, 1.0, 10.0, 100.0]},
                {"m": [HuberRegressor(max_iter=2000)], "m__alpha": [0.1, 1.0, 10.0, 100.0]}]
        g = GridSearchCV(pipe, grid, cv=inner, scoring=sc, n_jobs=NJ)
        g.fit(Xtr, ytr, groups=gtr)
        bp = {k: (type(v).__name__ if k == "m" else v) for k, v in g.best_params_.items()}
        return g.predict(Xte), bp
    if name == "hyb_ridge":                                       # prior + quadratic ridge
        pipe = Pipeline([("s", StandardScaler()), ("p", PolynomialFeatures(2, include_bias=False)),
                         ("s2", StandardScaler()), ("m", Ridge())])
        grid = [{"m": [Ridge()], "m__alpha": [0.1, 1.0, 10.0, 100.0]},
                {"m": [HuberRegressor(max_iter=2000)], "m__alpha": [0.1, 1.0, 10.0, 100.0]}]
        if fixed_loss == "squared_error":
            grid = grid[:1]
        elif fixed_loss == "huber":
            grid = grid[1:]
        g = GridSearchCV(pipe, grid, cv=inner, scoring=sc, n_jobs=NJ)
        g.fit(Xtr, ytr - prior_tr, groups=gtr)
        bp = {k: (type(v).__name__ if k == "m" else v) for k, v in g.best_params_.items()}
        return g.predict(Xte) + prior_te, bp
    if name == "hyb_mlp":
        pipe = Pipeline([("s", StandardScaler()),
                         ("m", MLPRegressor(hidden_layer_sizes=(32, 32), solver="lbfgs",
                                            max_iter=2000, random_state=seed))])
        g = GridSearchCV(pipe, {"m__alpha": [1e-3, 1e-2, 1e-1, 1.0]}, cv=inner, scoring=sc, n_jobs=NJ)
        g.fit(np.c_[Xtr, prior_tr], ytr - prior_tr, groups=gtr)
        return g.predict(np.c_[Xte, prior_te]) + prior_te, g.best_params_
    raise KeyError(name)


# ---------------------------------------------------------------- metrics
def metrics(y, p, regime=None):
    e = np.abs(p - y)
    m = np.isfinite(e)
    out = dict(n=int(m.sum()), MAE=float(np.mean(e[m])), MedAE=float(np.median(e[m])),
               P90AE=float(np.percentile(e[m], 90)),
               rho=float(spearmanr(y[m], p[m]).statistic))
    if regime is not None:
        for r in np.unique(regime):
            mm = m & (regime == r)
            out[f"MAE_{r}"] = float(np.mean(e[mm])) if mm.any() else np.nan
            out[f"MedAE_{r}"] = float(np.median(e[mm])) if mm.any() else np.nan
    return out


def block_bootstrap(y, preds, blocks, n_boot=2000, seed=7, ref=None):
    """95% CIs for MAE, MedAE and Spearman per model, and paired differences vs `ref`,
    resampling whole control-space blocks (not individual conditions)."""
    rng = np.random.default_rng(seed)
    ub = np.unique(blocks)
    idx_by_b = {b: np.where(blocks == b)[0] for b in ub}
    names = list(preds)
    S = {k: {"MAE": [], "MedAE": [], "rho": [], "dMAE": [], "dMedAE": [], "drho": []} for k in names}
    for _ in range(n_boot):
        bb = rng.choice(ub, size=ub.size, replace=True)
        ii = np.concatenate([idx_by_b[b] for b in bb])
        stat = {}
        for k in names:
            e = np.abs(preds[k][ii] - y[ii])
            r = spearmanr(y[ii], preds[k][ii]).statistic if np.std(preds[k][ii]) > 0 else np.nan
            stat[k] = (np.mean(e), np.median(e), r)
        for k in names:
            S[k]["MAE"].append(stat[k][0]); S[k]["MedAE"].append(stat[k][1]); S[k]["rho"].append(stat[k][2])
            if ref:
                S[k]["dMAE"].append(stat[k][0] - stat[ref][0])
                S[k]["dMedAE"].append(stat[k][1] - stat[ref][1])
                S[k]["drho"].append(stat[k][2] - stat[ref][2])
    ci = lambda a: (float(np.nanpercentile(a, 2.5)), float(np.nanpercentile(a, 97.5)))
    out = {}
    for k in names:
        d = {f"{m}_CI": ci(S[k][m]) for m in ("MAE", "MedAE", "rho")}
        if ref:
            for m in ("dMAE", "dMedAE", "drho"):
                d[f"{m}_vs_{ref}_CI"] = ci(S[k][m])
            d["P(MedAE lower than ref)"] = float(np.mean(np.array(S[k]["dMedAE"]) < 0))
        out[k] = d
    return out
