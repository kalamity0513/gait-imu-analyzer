"""Low-level numerical helpers (filters, robust stats, integration)."""

from __future__ import annotations

import numpy as np

from .config import ZERO_MIN_LEN_S, ZERO_TOL_MSS


def moving_mean(x, win):
    """Rectangular moving mean of length ``win``."""
    win = max(1, int(win))
    if win == 1:
        return x.copy()
    k = np.ones(win) / win
    return np.convolve(x, k, mode="same")


def robust_std(x):
    """1.4826 * MAD — a heavy-tail-resistant std estimator."""
    mad = np.median(np.abs(x - np.median(x)))
    return 1.4826 * mad + 1e-9


def build_stride_times_from_pairs(pairs, t_m):
    if not pairs:
        return np.array([], dtype=float)
    return np.array([t_m[b] - t_m[a] for (a, b) in pairs], dtype=float)


def cadence_from_stride_times(stride_times_s):
    """Steps per minute (two steps per stride)."""
    if stride_times_s.size == 0:
        return np.nan
    return 120.0 / np.nanmean(stride_times_s)


def robust_cv_percent(x):
    x = np.asarray(x, dtype=float)
    if x.size == 0 or not np.isfinite(np.nanmean(x)):
        return np.nan
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))
    sd_rob = 1.4826 * mad
    mu = np.nanmean(x)
    return np.nan if mu == 0 else 100.0 * (sd_rob / abs(mu))


def classic_cv_percent(x):
    x = np.asarray(x, dtype=float)
    if x.size == 0 or not np.isfinite(np.nanmean(x)):
        return np.nan
    mu = np.nanmean(x)
    sd = np.nanstd(x)
    return np.nan if mu == 0 else 100.0 * (sd / abs(mu))


def integrate_stride_xy_linear_zupt(acc_xy, t):
    """Trapezoidal integrate horizontal accel with a linear ZUPT-like drift fix.

    Used to estimate stride length from per-stride foot acceleration.
    """
    n = acc_xy.shape[0]
    if n < 3:
        return 0.0, 0.0

    v = np.zeros_like(acc_xy)
    for i in range(1, n):
        dt = t[i] - t[i - 1]
        if not np.isfinite(dt) or dt <= 0:
            dt = 0.0
        v[i] = v[i - 1] + 0.5 * (acc_xy[i] + acc_xy[i - 1]) * dt

    # ZUPT-like: assume v should return to zero by stride end → linear drift correction
    drift = np.linspace(0.0, 1.0, n)[:, None] * v[-1]
    v_corr = v - drift

    p = np.zeros_like(acc_xy)
    for i in range(1, n):
        dt = t[i] - t[i - 1]
        if not np.isfinite(dt) or dt <= 0:
            dt = 0.0
        p[i] = p[i - 1] + 0.5 * (v_corr[i] + v_corr[i - 1]) * dt

    dx, dy = p[-1]
    return float(dx), float(dy)


def compute_stride_lengths_from_pairs(pairs, tf, af_world, idx_f):
    lengths, comps = [], []
    for (a, b) in pairs:
        i0, i1 = idx_f[a], idx_f[b]
        if i1 <= i0:
            continue
        dx, dy = integrate_stride_xy_linear_zupt(af_world[i0:i1 + 1, :2], tf[i0:i1 + 1])
        lengths.append(np.hypot(dx, dy))
        comps.append((dx, dy))
    return np.array(lengths, dtype=float), comps


def infer_zero_window(t, vert_s, tol=ZERO_TOL_MSS, min_len_s=ZERO_MIN_LEN_S):
    """Find the longest run where ``|vert_s| < tol`` and ``duration >= min_len_s``.

    Used to auto-pick a "standing still" window for calibration.
    """
    if t.size == 0 or vert_s.size == 0:
        return None
    mask = np.isfinite(vert_s) & (np.abs(vert_s) < tol)
    if not np.any(mask):
        return None
    edges = np.diff(mask.astype(int), prepend=0, append=0)
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0] - 1
    if starts.size == 0 or ends.size == 0:
        return None

    best = None
    best_len = -np.inf
    for s, e in zip(starts, ends):
        if e <= s:
            continue
        dur = t[e] - t[s]
        if dur >= min_len_s and dur > best_len:
            best, best_len = (s, e), dur
    if best is None:
        return None
    i0, i1 = best
    return float(t[i0]), float(t[i1])
