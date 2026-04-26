"""Knee pipeline: shank + thigh IMUs → knee flexion angle."""

from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks, savgol_filter
from scipy.spatial.transform import Rotation as R

from ..calibration import auto_pair_A2S, static_calibrate_window
from ..config import (
    G, MATCH_TOL_S, MIN_HS_SEP_S, MIN_WIDTH_S, PROM_STD,
    ZERO_MIN_LEN_S, ZERO_TOL_MSS,
)
from ..io_utils import guess_cols, guess_quat_only, load_structured
from ..signal_utils import infer_zero_window, robust_std


def _match_timebases(ts, tt):
    idx_s, idx_t = [], []
    for i, tsi in enumerate(ts):
        j = np.searchsorted(tt, tsi, side="left")
        cand = ([j] if j < len(tt) else []) + ([j - 1] if j - 1 >= 0 else [])
        if not cand:
            continue
        k = min(cand, key=lambda c: abs(tt[c] - tsi))
        if abs(tt[k] - tsi) <= MATCH_TOL_S:
            idx_s.append(i)
            idx_t.append(k)
    return np.array(idx_s, dtype=int), np.array(idx_t, dtype=int)


def compute_knee_series(raw, *, stand_win=None, flex_win=None):
    """Compute the knee flexion series (degrees) from a stashed raw dict."""
    t_m = raw["t_m"]
    qs_m = raw["qs_m"]
    qt_m = raw["qt_m"]

    A2S_shank, A2S_thigh, _ = auto_pair_A2S(qs_m, qt_m, t_m,
                                            stand_win=stand_win, flex_win=flex_win)
    rot_shank_anat = R.from_quat(qs_m) * R.from_matrix(A2S_shank)
    rot_thigh_anat = R.from_quat(qt_m) * R.from_matrix(A2S_thigh)
    rot_rel = rot_thigh_anat.inv() * rot_shank_anat

    knee = np.degrees(np.unwrap(rot_rel.as_euler("xyz", degrees=False)[:, 0]))
    knee, baseline_note = static_calibrate_window(t_m, knee, win=stand_win)

    dt = np.nanmedian(np.diff(t_m))
    dt = 0.01 if (not np.isfinite(dt) or dt <= 0) else dt
    wlen = max(5, int(round(0.21 / dt)) // 2 * 2 + 1)
    knee = savgol_filter(knee, wlen, 3)
    return knee, baseline_note


def process_files_knee(shank_path, thigh_path, *, stand_win=None, flex_win=None):
    """Load Shank + Thigh CSVs → return ``base`` dict for knee analysis."""
    Ds = load_structured(shank_path)
    t_col_s, qxs, qys, qzs, qrs, axs, ays, azs = guess_cols(Ds.dtype.names)
    ts = np.asarray(Ds[t_col_s], dtype=float)
    order_s = np.argsort(ts)
    ts = ts[order_s]
    accs = np.vstack([Ds[axs], Ds[ays], Ds[azs]]).T.astype(float)[order_s]
    qs = np.vstack([Ds[qxs], Ds[qys], Ds[qzs], Ds[qrs]]).T.astype(float)[order_s]

    Dt = load_structured(thigh_path)
    t_col_t, qxt, qyt, qzt, qrt = guess_quat_only(Dt.dtype.names)
    tt = np.asarray(Dt[t_col_t], dtype=float)
    order_t = np.argsort(tt)
    tt = tt[order_t]
    qt = np.vstack([Dt[qxt], Dt[qyt], Dt[qzt], Dt[qrt]]).T.astype(float)[order_t]

    idx_s, idx_t = _match_timebases(ts, tt)
    t_m = ts[idx_s]
    qs_m = qs[idx_s]
    qt_m = qt[idx_t]
    accs_m = accs[idx_s]

    # HS from shank world-vertical
    acc_world = R.from_quat(qs_m).apply(accs_m)
    acc_vert_up = acc_world[:, 2] - G
    dt = np.nanmedian(np.diff(t_m))
    dt = 0.01 if (not np.isfinite(dt) or dt <= 0) else dt
    acc_s = savgol_filter(acc_vert_up, max(7, int(round(0.05 / dt)) // 2 * 2 + 1), 3)

    HS_idx_raw, _ = find_peaks(
        acc_s,
        prominence=PROM_STD * robust_std(acc_s),
        distance=max(1, int(round(MIN_HS_SEP_S / dt))),
        width=max(1, int(round(MIN_WIDTH_S / dt))),
    )

    inferred_zwin = infer_zero_window(t_m, acc_s, ZERO_TOL_MSS, ZERO_MIN_LEN_S)
    use_stand = stand_win or inferred_zwin or (3.0, 5.0)

    raw = dict(mode="knee", t_m=t_m, qs_m=qs_m, qt_m=qt_m)
    knee_series, baseline_note = compute_knee_series(
        raw, stand_win=use_stand, flex_win=flex_win,
    )

    base = dict(
        mode="knee",
        tf=t_m, vert_s=acc_s,
        HS_idx_raw=HS_idx_raw, HS_idx_drop=np.array([], dtype=int), HS_idx=HS_idx_raw,
        angle_series=knee_series,
        knee_baseline_note=baseline_note,
        raw=raw,
        inferred_zero_window=inferred_zwin,
    )
    return base
