"""Ankle pipeline: foot + shank IMUs → ankle angle (DF/PF or |SO(3)|)."""

from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks
from scipy.spatial.transform import Rotation as R

from ..calibration import auto_pair_A2S
from ..config import (
    ACC_SMOOTH_S, G, HEIGHT_K_GLOBAL, HEIGHT_K_LOCAL,
    LOCAL_WIN_S, MATCH_TOL_S, MIN_HS_SEP_S, MIN_WIDTH_S, PROM_STD,
    ZERO_MIN_LEN_S, ZERO_TOL_MSS,
)
from ..io_utils import guess_cols, guess_quat_only, load_structured
from ..signal_utils import infer_zero_window, moving_mean, robust_std


def _match_timebases(tf, ts):
    """Match foot samples to nearest shank samples within ``MATCH_TOL_S``."""
    idx_f, idx_s = [], []
    for i, tfi in enumerate(tf):
        j = np.searchsorted(ts, tfi, side="left")
        cand = ([j] if j < len(ts) else []) + ([j - 1] if j - 1 >= 0 else [])
        if not cand:
            continue
        k = min(cand, key=lambda c: abs(ts[c] - tfi))
        if abs(ts[k] - tfi) <= MATCH_TOL_S:
            idx_f.append(i)
            idx_s.append(k)
    return np.array(idx_f, dtype=int), np.array(idx_s, dtype=int)


def compute_ankle_angle(raw, *, mode="dfpf", stand_win=None, flex_win=None,
                        zero_win=None, zero_enabled=True):
    """Compute the ankle angle series from a stashed raw dict.

    ``mode`` is ``"dfpf"`` (functional hinge projection) or
    ``"so3"`` (rotation-vector norm of the relative rotation).
    """
    t_m = raw["t_m"]
    qf_m = raw["qf_m"]
    qs_m = raw["qs_m"]

    if mode == "dfpf":
        A2S_foot, A2S_shank, k_world = auto_pair_A2S(qf_m, qs_m, t_m,
                                                     stand_win=stand_win,
                                                     flex_win=flex_win)
        rot_foot_anat  = R.from_quat(qf_m) * R.from_matrix(A2S_foot)
        rot_shank_anat = R.from_quat(qs_m) * R.from_matrix(A2S_shank)
        rel = rot_shank_anat.inv() * rot_foot_anat
        rv = rel.as_rotvec()
        k = k_world / (np.linalg.norm(k_world) + 1e-12)
        angle = np.degrees(rv @ k)
        note = "Ankle DF/PF (functional hinge projection)"
    else:
        rel = R.from_quat(qs_m) * R.from_quat(qf_m).inv()
        angle = np.rad2deg(np.linalg.norm(rel.as_rotvec(), axis=1))
        note = "Ankle |SO(3) relative| (rotation-vector norm)"

    if zero_enabled and zero_win is not None:
        m_cal = (t_m >= zero_win[0]) & (t_m <= zero_win[1])
        if np.any(m_cal):
            angle = angle - np.nanmean(angle[m_cal])
            note += f" | zeroed {zero_win[0]:.1f}-{zero_win[1]:.1f}s"
    return angle, note


def process_files_ankle(foot_path, shank_path, *,
                        ankle_mode="dfpf", stand_win=None, flex_win=None,
                        zero_win=None, zero_enabled=True):
    """Load Foot + Shank CSVs → return ``base`` dict ready for ``build_outputs_from_pairs``.

    Also returns an inferred standing window when one is found, so the
    UI can update its inputs.
    """
    Df = load_structured(foot_path)
    t_col_f, qxf, qyf, qzf, qrf, axf, ayf, azf = guess_cols(Df.dtype.names)
    tf = np.asarray(Df[t_col_f], dtype=float)
    order_f = np.argsort(tf)
    tf = tf[order_f]
    accf = np.vstack([Df[axf], Df[ayf], Df[azf]]).T.astype(float)[order_f]
    quatf = np.vstack([Df[qxf], Df[qyf], Df[qzf], Df[qrf]]).T.astype(float)[order_f]

    Ds = load_structured(shank_path)
    t_col_s, qxs, qys, qzs, qrs = guess_quat_only(Ds.dtype.names)
    ts = np.asarray(Ds[t_col_s], dtype=float)
    order_s = np.argsort(ts)
    ts = ts[order_s]
    quats = np.vstack([Ds[qxs], Ds[qys], Ds[qzs], Ds[qrs]]).T.astype(float)[order_s]

    idx_f, idx_s = _match_timebases(tf, ts)
    t_m = tf[idx_f]
    qf_m = quatf[idx_f]
    qs_m = quats[idx_s]
    accf_m = accf[idx_f]

    # World-frame foot acceleration; vertical channel drives HS detection.
    af_world_m = R.from_quat(qf_m).apply(accf_m)
    vert = af_world_m[:, 2] - G

    dt = np.nanmedian(np.diff(t_m))
    dt = 0.01 if (not np.isfinite(dt) or dt <= 0) else dt
    vert_s = moving_mean(vert, int(round(ACC_SMOOTH_S / dt)))

    HS_idx_raw, _ = find_peaks(
        vert_s,
        distance=max(1, int(round(MIN_HS_SEP_S / dt))),
        prominence=PROM_STD * robust_std(vert_s),
        width=max(1, int(round(MIN_WIDTH_S / dt))),
    )

    win_loc = max(5, int(round(LOCAL_WIN_S / dt)))
    mu_loc = moving_mean(vert_s, win_loc)
    sigma_loc = np.sqrt(moving_mean((vert_s - mu_loc) ** 2, win_loc)) + 1e-9
    sigma_glob = robust_std(vert_s)

    amp_raw = vert_s[HS_idx_raw]
    thr = np.maximum(HEIGHT_K_LOCAL * sigma_loc[HS_idx_raw], HEIGHT_K_GLOBAL * sigma_glob)
    keep_mask = amp_raw >= thr
    HS_idx = HS_idx_raw[keep_mask]
    HS_idx_drop = HS_idx_raw[~keep_mask]

    # Auto-infer a standing-still window if none was supplied.
    inferred_zwin = infer_zero_window(t_m, vert_s, ZERO_TOL_MSS, ZERO_MIN_LEN_S)
    use_stand = stand_win or inferred_zwin or (3.0, 5.0)
    use_zero  = zero_win  or inferred_zwin or (3.0, 8.0)

    raw = dict(mode="ankle", t_m=t_m, qf_m=qf_m, qs_m=qs_m,
               tf_full=tf, quatf_full=quatf, accf_full=accf, idx_f_map=idx_f)
    angle, angle_note = compute_ankle_angle(
        raw, mode=ankle_mode, stand_win=use_stand, flex_win=flex_win,
        zero_win=use_zero, zero_enabled=zero_enabled,
    )

    base = dict(
        mode="ankle",
        tf=t_m, vert_s=vert_s,
        HS_idx_raw=HS_idx_raw, HS_idx_drop=HS_idx_drop, HS_idx=HS_idx,
        angle_series=angle,
        ankle_angle_note=angle_note,
        tf_full=tf,
        af_world_all=R.from_quat(quatf).apply(accf),
        used_foot_indices=idx_f,
        raw=raw,
        inferred_zero_window=inferred_zwin,
    )
    return base
