#!/usr/bin/env python3
"""Amplitude/phase-based Q_safety for Tap-300/AlScN.

Q_align stays height-based (alignment is a topographic property). Q_safety is redefined
as a tip-sample FORCE descriptor read from the amplitude and phase scan lines:
  amplitude reduction below the free amplitude reports the interaction force, and a phase
  pushed below 90 deg reports the repulsive branch. Together they flag large force.

    amp_force(x) = (A0 - A(x)) / A0                 # reduction from free amplitude
    phi_force(x) = clip((90 - phi(x))/90, -1, 1)    # repulsive when > 0
    force(x)     = amp_force(x) + 0.5 * relu(phi_force(x))
    Q_safety     = 90th percentile of force over the line (worst-case repulsive force)

Deterministic prior: the controller holds amplitude at the set-point and the FD library
fixes the phase at the operating point, so the prior is the steady force level. A CNN-LSTM
then corrects it from the measured amplitude/phase window, recovering the per-condition
force the deterministic model cannot make. Held-out evaluation throughout.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
FIG_T = ROOT / "output" / "descriptor_framework_Tap300"
OUTNPZ = FIG_T / "qsafety_ap.npz"

# ---------------------------------------------------------------- data
jc = np.load(FIG_T / "joint_channel_calibration.npz")
A_exp, PHI_exp = jc["A_exp"], jc["PHI_exp"]                       # (900,2,256)
sd = pd.read_csv(FIG_T / "scan_desc_pinn.csv")
exp = sd[sd.source == "exp"].reset_index(drop=True)
sp = exp.setpoint.values.astype(float)
A0 = exp.drive.values.astype(float)                              # free amplitude
ig = exp.igain.values.astype(float)
ss = exp.get("scan_speed", pd.Series(np.zeros(len(exp)))).values.astype(float) if "scan_speed" in exp else np.zeros(len(exp))
is_test = exp.is_test.values.astype(bool)
n = len(exp)

fd = np.load(ROOT / "output" / "Tap300_AlScN.npz")
fd_amp, fd_phi = fd["amp"], fd["phase"]                          # (30,1000)
fd_A0 = np.array([np.nanmean(fd_amp[i, -10:]) for i in range(fd_amp.shape[0])])


def wrap(p):
    p = np.mod(p, 360.0)
    return np.where(p > 180, p - 360, p)


def force_line(A, phi, a0):
    m = np.isfinite(A) & np.isfinite(phi)
    amp_force = (a0 - A[m]) / a0
    phi_force = np.clip((90.0 - wrap(phi[m])) / 90.0, -1, 1)
    return amp_force + 0.5 * np.maximum(0.0, phi_force)


def q_safety(i):
    return float(np.nanmean([np.nanpercentile(force_line(A_exp[i, d], PHI_exp[i, d], A0[i]), 90)
                             for d in (0, 1)]))


Q_exp = np.array([q_safety(i) for i in range(n)])

# ---------------------------------------------------------------- deterministic prior + op-point feature
def op_point(a0_target, s):
    i = int(np.argmin(np.abs(fd_A0 - a0_target)))
    A = fd_amp[i]; d = np.arange(A.size, dtype=float)
    mm = np.isfinite(A); A = A[mm]; d = d[mm]
    At = s * fd_A0[i]
    c = np.where(np.diff(np.sign(A - At)) != 0)[0]
    if c.size == 0:
        return np.nan, np.nan, np.nan
    k = c[0]
    phi_curve = fd_phi[i][mm]
    phi_op = float(phi_curve[k])
    k2 = min(k + 4, len(d) - 1); k1 = max(k - 4, 0)
    slope = abs((A[k2] - A[k1]) / (d[k2] - d[k1] + 1e-9))
    return phi_op, 1.0 / max(slope, 1e-4), s


phi_op = np.full(n, np.nan); amp_fac = np.full(n, np.nan)
for i in range(n):
    p_, f_, _ = op_point(A0[i], sp[i]); phi_op[i] = p_; amp_fac[i] = f_
phi_op = np.where(np.isfinite(phi_op), phi_op, np.nanmedian(phi_op))
amp_fac = np.where(np.isfinite(amp_fac), amp_fac, np.nanmedian(amp_fac))

# steady force = reduction from free amplitude (1-setpoint) + repulsive phase from FD
Q_prior = (1.0 - sp) + 0.5 * np.maximum(0.0, (90.0 - wrap(phi_op)) / 90.0)


def rho(a, b, mask):
    m = mask & np.isfinite(a) & np.isfinite(b)
    return float(stats.spearmanr(a[m], b[m]).statistic)


print(f"Q_safety_exp: range [{Q_exp.min():.2f},{Q_exp.max():.2f}] median {np.median(Q_exp):.3f}")
print(f"prior held-out: Spearman {rho(Q_prior, Q_exp, is_test):+.3f}  "
      f"MSE {np.nanmean((Q_prior-Q_exp)[is_test]**2):.4f}  median|e| {np.nanmedian(np.abs(Q_prior-Q_exp)[is_test]):.4f}")

# ---------------------------------------------------------------- CNN-LSTM correction over A/phi windows
try:
    import torch
    import torch.nn as nn
    torch.manual_seed(0); np.random.seed(0)

    L = 256; K = 32
    # per-condition 2-channel line: amp_force(x), phi_force(x)  (the measured signal)
    def cond_line(i):
        out = []
        for d in (0, 1):
            A = A_exp[i, d]; phi = PHI_exp[i, d]
            af = np.nan_to_num((A0[i] - A) / A0[i], nan=0.0)
            pf = np.nan_to_num(np.clip((90 - wrap(phi)) / 90.0, -1, 1), nan=0.0)
            out.append(np.stack([af, pf]))
        return np.nanmean(out, axis=0)                          # (2, 256) avg of trace/retrace

    lines = np.stack([cond_line(i) for i in range(n)]).astype(np.float32)   # (n,2,256)
    # robust z-space target
    tr = ~is_test
    med = np.median((Q_exp - Q_prior)[tr]); iqr = np.subtract(*np.percentile((Q_exp - Q_prior)[tr], [75, 25])) + 1e-6
    dQ_z = ((Q_exp - Q_prior) - med) / iqr

    feat = np.stack([np.log10(amp_fac), sp, A0 / A0.max(), ig / ig.max()], 1).astype(np.float32)

    # encode each condition's A/phi line ONCE per epoch, then run the LSTM over windows
    # of the encodings — avoids re-encoding K*B sequences per step.
    class Corr(nn.Module):
        def __init__(self, nf=24, h=48):
            super().__init__()
            self.cnn = nn.Sequential(
                nn.Conv1d(2, 16, 9, stride=2, padding=4), nn.GELU(),
                nn.Conv1d(16, 32, 9, stride=2, padding=4), nn.GELU(),
                nn.Conv1d(32, nf, 9, stride=2, padding=4), nn.GELU(),
                nn.AdaptiveAvgPool1d(1))
            self.lstm = nn.LSTM(nf + feat.shape[1], h, batch_first=True)
            self.head = nn.Sequential(nn.Linear(h, 24), nn.GELU(), nn.Linear(24, 1))

        def encode(self, lines_t):                       # (n,2,L) -> (n,nf)
            return self.cnn(lines_t).squeeze(-1)

        def predict(self, enc, feat_t, widx):            # widx: (B,K) long
            x = torch.cat([enc[widx], feat_t[widx]], -1)  # (B,K,nf+nfeat)
            o, _ = self.lstm(x)
            return self.head(o[:, -1]).squeeze(-1)

    win_cond = np.arange(K - 1, n)
    widx = np.stack([[max(0, c - K + 1 + j) if (c - K + 1 + j) >= 0 else 0
                      for j in range(K)] for c in win_cond])         # (n_win,K)
    # left-pad short windows by repeating the first index
    for r, c in enumerate(win_cond):
        start = c - K + 1
        idx = [max(start, 0)] * max(0, -start) + list(range(max(start, 0), c + 1))
        widx[r] = idx[-K:]
    is_te_w = is_test[win_cond]
    tr_rows = np.where(~is_te_w)[0]

    lines_t = torch.tensor(lines)
    feat_t = torch.tensor(feat)
    widx_t = torch.tensor(widx, dtype=torch.long)
    y_t = torch.tensor(dQ_z[win_cond].astype(np.float32))

    model = Corr(); opt = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-4)
    huber = nn.HuberLoss(delta=1.0)
    for ep in range(300):
        model.train()
        enc = model.encode(lines_t)                      # one batched forward of all conditions
        b = np.random.choice(tr_rows, min(96, len(tr_rows)), replace=False)
        pred = model.predict(enc, feat_t, widx_t[b])
        opt.zero_grad(); huber(pred, y_t[b]).backward(); opt.step()

    model.eval()
    with torch.no_grad():
        enc = model.encode(lines_t)
        dQ_pred_z = model.predict(enc, feat_t, widx_t).numpy()
    dQ_pred = dQ_pred_z * iqr + med
    te_w = list(win_cond[is_te_w])
    Q_pred = Q_prior.copy(); Q_pred[win_cond] = Q_prior[win_cond] + dQ_pred
    te_mask = np.zeros(n, bool); te_mask[te_w] = True

    print(f"corrected held-out: Spearman {rho(Q_pred, Q_exp, te_mask):+.3f}  "
          f"MSE {np.nanmean((Q_pred-Q_exp)[te_mask]**2):.4f}  median|e| {np.nanmedian(np.abs(Q_pred-Q_exp)[te_mask]):.4f}")

    np.savez(OUTNPZ, Q_exp=Q_exp, Q_prior=Q_prior, Q_pred=Q_pred, is_test=is_test,
             win_cond=win_cond, setpoint=sp, drive=A0, amp_fac=amp_fac, phi_op=phi_op,
             A_exp=A_exp, PHI_exp=PHI_exp)
    print("saved", OUTNPZ.name)
except ImportError:
    print("torch unavailable")
