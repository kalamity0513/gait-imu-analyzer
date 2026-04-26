"""Functional, orientation-agnostic anatomical calibration.

We derive a sensor-to-anatomical rotation (``A2S``) for each sensor
without requiring the user to mount it in any particular orientation.

Approach
--------
1. Use a *standing still* window to estimate the world-vertical axis as
   seen by each sensor (rotation-mean of the quaternions in that window).
2. Use a *flexion* window (or the whole trial) to estimate the joint's
   hinge axis in world frame: the dominant principal axis of the
   relative rotation vectors between the two sensors.
3. Build a right-handed triad in world frame from those two directions
   (vertical + hinge → forward), and project each sensor's rotation
   into that frame to obtain ``A2S``.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation as R


def _mean_rot(q, t, win):
    if len(t) == 0:
        return R.identity()
    if win is None:
        return R.from_quat(q).mean()
    m = (t >= win[0]) & (t <= win[1])
    if not np.any(m):
        m = (t >= t[0]) & (t <= t[0] + 2.0)
        if not np.any(m):
            return R.from_quat(q).mean()
    return R.from_quat(q[m]).mean()


def _pick_sensor_axis_for_vertical(rot_sW):
    """Pick whichever sensor axis is most aligned with world Z."""
    ezW = np.array([0., 0., 1.])
    cands = np.stack([
        rot_sW.apply([1., 0., 0.]),
        rot_sW.apply([0., 1., 0.]),
        rot_sW.apply([0., 0., 1.]),
    ], axis=0)
    dots = cands @ ezW
    idx = int(np.argmax(np.abs(dots)))
    sgn = np.sign(dots[idx]) if dots[idx] != 0 else 1.0
    zW = sgn * cands[idx]
    zW /= np.linalg.norm(zW) + 1e-12
    return idx, float(sgn), zW


def _estimate_hinge_world(qA, qB, t, lo_hi=None):
    """Principal axis of relative rotations between two sensors → joint hinge."""
    m = np.ones_like(t, dtype=bool)
    if lo_hi is not None:
        m = (t >= lo_hi[0]) & (t <= lo_hi[1])
        if not np.any(m):
            m[:] = True

    Rrel = R.from_quat(qB[m]).inv() * R.from_quat(qA[m])
    rv = Rrel.as_rotvec()
    ang = np.linalg.norm(rv, axis=1)
    if rv.shape[0] < 3:
        return np.array([1., 0., 0.])

    good = ang > np.percentile(ang, 60.0)
    if not np.any(good):
        good[:] = True

    dirs = rv[good] / (ang[good][:, None] + 1e-12)
    C = dirs.T @ dirs / max(1, dirs.shape[0])
    _, V = np.linalg.eigh(C)
    k_hat = V[:, -1]
    k_hat /= np.linalg.norm(k_hat) + 1e-12
    sgn = np.sign(np.median(rv @ k_hat))
    return k_hat * (1.0 if sgn == 0 else sgn)


def _triad_from_ZK(ZW, kW):
    """Right-handed triad with Z = ZW, X ≈ k × Z."""
    ZW = ZW / (np.linalg.norm(ZW) + 1e-12)
    kW = kW / (np.linalg.norm(kW) + 1e-12)

    XW = np.cross(kW, ZW)
    nX = np.linalg.norm(XW)
    if nX < 1e-6:
        tmp = np.array([1., 0., 0.]) if abs(ZW[0]) < 0.9 else np.array([0., 1., 0.])
        XW = np.cross(tmp, ZW)
        nX = np.linalg.norm(XW)
    XW /= nX + 1e-12

    YW = np.cross(ZW, XW)
    YW /= np.linalg.norm(YW) + 1e-12
    XW = np.cross(YW, ZW)
    XW /= np.linalg.norm(XW) + 1e-12
    return XW, YW, ZW


def _proj_SO3(M):
    """Project a 3x3 matrix onto the closest rotation matrix (SVD)."""
    U, _, Vt = np.linalg.svd(M)
    Rm = U @ Vt
    if np.linalg.det(Rm) < 0:
        Rm[:, -1] *= -1
    return Rm


def auto_pair_A2S(q_distal, q_prox, t, stand_win, flex_win):
    """Calibrate two paired sensors and return ``(A2S_distal, A2S_prox, hinge_world)``."""
    Rdist_mean = _mean_rot(q_distal, t, stand_win)
    Rprox_mean = _mean_rot(q_prox,   t, stand_win)

    _, _, zDist_W = _pick_sensor_axis_for_vertical(Rdist_mean)
    _, _, zProx_W = _pick_sensor_axis_for_vertical(Rprox_mean)

    k_W = _estimate_hinge_world(q_distal, q_prox, t, lo_hi=flex_win)

    XdW, YdW, ZdW = _triad_from_ZK(zDist_W, k_W)
    XpW, YpW, ZpW = _triad_from_ZK(zProx_W, k_W)

    A2W_dist = np.column_stack([XdW, YdW, ZdW])
    A2W_prox = np.column_stack([XpW, YpW, ZpW])

    S2W_dist = Rdist_mean.as_matrix()
    S2W_prox = Rprox_mean.as_matrix()

    A2S_dist = _proj_SO3(S2W_dist.T @ A2W_dist)
    A2S_prox = _proj_SO3(S2W_prox.T @ A2W_prox)
    return A2S_dist, A2S_prox, k_W


def static_calibrate_window(t, series, win, fallback=(0., 2.)):
    """Subtract the mean of ``series`` over ``win`` (or ``fallback``).

    Returns ``(zeroed_series, note)`` where ``note`` describes the window used.
    """
    if len(t) == 0:
        return series, "no t"
    if win is not None:
        m = (t >= win[0]) & (t <= win[1])
        if np.any(m):
            return series - np.nanmean(series[m]), f"{win[0]:.1f}-{win[1]:.1f} s"
        note = f"{fallback[0]:.1f}-{fallback[1]:.1f} s (fallback)"
    else:
        note = f"{fallback[0]:.1f}-{fallback[1]:.1f} s (fallback)"
    m2 = (t >= fallback[0]) & (t <= fallback[1])
    if np.any(m2):
        return series - np.nanmean(series[m2]), note
    return series, "no baseline (unchanged)"
