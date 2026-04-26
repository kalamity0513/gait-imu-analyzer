"""Stride pairing, curve resampling, and result aggregation.

This is the framework-agnostic core that the UI calls into:

    base = process_files_ankle(...) or process_files_knee(...)
    res  = build_outputs_from_pairs(base, ...)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from scipy.signal import savgol_filter

from ..config import N_RESAMPLE, SAVGOL_POLY, SAVGOL_WIN
from ..signal_utils import (
    build_stride_times_from_pairs,
    cadence_from_stride_times,
    classic_cv_percent,
    compute_stride_lengths_from_pairs,
    robust_cv_percent,
)


def make_pairs(hs_idx, t_m, start_idx=0, min_samples=10, trim_first=0, trim_last=0):
    """Build HS→HS stride pairs (i, i+2) from heel-strike indices."""
    if hs_idx.size < 3:
        return []
    start_idx = max(0, int(start_idx))
    pairs = [
        (hs_idx[i], hs_idx[i + 2])
        for i in range(start_idx, len(hs_idx) - 2, 2)
        if (hs_idx[i + 2] - hs_idx[i]) >= min_samples
    ]
    if trim_first > 0:
        pairs = pairs[trim_first:]
    if trim_last > 0 and pairs:
        pairs = pairs[:-trim_last] if trim_last < len(pairs) else []
    return pairs


def curves_from_pairs(angle, pairs):
    """Resample each stride to ``N_RESAMPLE`` points and savgol-smooth."""
    time_norm = np.linspace(0, 1, N_RESAMPLE)
    curves = []
    for a, b in pairs:
        seg = angle[a:b + 1]
        if seg.size < 2:
            continue
        seg_i = np.interp(time_norm, np.linspace(0, 1, len(seg)), seg)
        wl = SAVGOL_WIN if SAVGOL_WIN % 2 == 1 else SAVGOL_WIN + 1
        wl = min(wl, N_RESAMPLE - (1 - N_RESAMPLE % 2))
        curves.append(savgol_filter(seg_i, window_length=wl, polyorder=SAVGOL_POLY, mode="interp"))
    return time_norm, (np.array(curves) if curves else np.empty((0, N_RESAMPLE)))


def build_outputs_from_pairs(
    base: dict,
    *,
    start_peak_idx: Optional[int] = None,
    stride_keep: Optional[np.ndarray] = None,
    trim_first: int = 0,
    trim_last: int = 0,
):
    """Compose the per-session result dict the UI consumes.

    ``base`` is the output of :func:`process_files_ankle` /
    :func:`process_files_knee` and contains the raw working arrays
    (timebase, angle series, HS indices, foot world acceleration if any).
    """
    start = 0 if start_peak_idx is None else int(start_peak_idx)
    pairs_all = make_pairs(
        base["HS_idx"], base["tf"],
        start_idx=start,
        trim_first=trim_first,
        trim_last=trim_last,
    )
    time_norm, curves_all = curves_from_pairs(base["angle_series"], pairs_all)

    if stride_keep is None or len(stride_keep) != len(pairs_all):
        stride_keep = np.ones(len(pairs_all), dtype=bool)

    if pairs_all and curves_all.size:
        keep_mask = np.asarray(stride_keep, dtype=bool)
        pairs = [p for p, k in zip(pairs_all, keep_mask) if k]
        curves = curves_all[keep_mask] if keep_mask.any() else np.empty((0, curves_all.shape[1]))
    else:
        keep_mask = np.zeros(0, dtype=bool)
        pairs, curves = [], np.empty((0, N_RESAMPLE))

    stride_times_s = build_stride_times_from_pairs(pairs, base["tf"])
    cadence_spm = cadence_from_stride_times(stride_times_s)
    cv_robust = robust_cv_percent(stride_times_s)
    cv_classic = classic_cv_percent(stride_times_s)

    stride_lengths_m = np.array([])
    speed_ms = np.nan
    if base.get("mode") == "ankle" and base.get("af_world_all") is not None and pairs:
        stride_lengths_m, _ = compute_stride_lengths_from_pairs(
            pairs, base["tf_full"], base["af_world_all"], base["used_foot_indices"],
        )
        if stride_lengths_m.size and stride_times_s.size:
            speed_ms = float(np.nanmean(stride_lengths_m) / np.nanmean(stride_times_s))

    return dict(
        mode=base.get("mode", "ankle"),
        tf=base["tf"], vert_s=base["vert_s"],
        HS_idx_raw=base["HS_idx_raw"],
        HS_idx_drop=base.get("HS_idx_drop", np.array([], dtype=int)),
        HS_idx=base["HS_idx"],
        t_m=base["tf"],
        pairs=pairs, pairs_all=pairs_all,
        keep_mask=np.asarray(stride_keep, dtype=bool).copy(),
        used_tf_idx=base["HS_idx"],
        time_norm=time_norm, curves=curves, curves_all=curves_all,
        stride_times_s=stride_times_s,
        cadence_spm=cadence_spm,
        stride_lengths_m=stride_lengths_m,
        speed_ms=speed_ms,
        cv_robust=cv_robust,
        cv_classic=cv_classic,
        knee_baseline_note=base.get("knee_baseline_note"),
        ankle_angle_note=base.get("ankle_angle_note"),
        angle_series=base["angle_series"],
    )
