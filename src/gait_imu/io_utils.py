"""CSV ingestion and column auto-detection.

Different IMU vendors export columns under slightly different names
(e.g. ``qx`` vs. ``Quat_X``). The helpers here normalise that so the
pipelines can stay generic.
"""

from __future__ import annotations

import numpy as np


def canon(s: str) -> str:
    """Lower-case and strip non-alphanumerics for fuzzy column matching."""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def load_structured(path: str):
    """Load a CSV as a NumPy structured array using its header names."""
    return np.genfromtxt(path, delimiter=",", names=True, dtype=None, encoding=None)


def _qget(names, cmap, key):
    if key in names:
        return key
    if canon(key) in cmap:
        return cmap[canon(key)]
    alt = key.replace("r", "w")
    if alt in names:
        return alt
    if canon(alt) in cmap:
        return cmap[canon(alt)]
    for n in names:
        c = canon(n)
        if c.startswith("q") and key[-1] in c:
            return n
    return None


def _aget(names, cmap, axis):
    prefer = [
        f"a{axis}", f"accelerometer{axis}", f"acc{axis}",
        f"a{axis}_mss", f"{axis}_mss", f"acc{axis}_mss",
    ]
    for key in prefer:
        if key in names:
            return key
        if canon(key) in cmap:
            return cmap[canon(key)]
    for n in names:
        c = canon(n)
        if (axis in c) and ("acc" in c or c.startswith(f"a{axis}")):
            return n
    return None


def _tget(names, cmap):
    for k in ("time_s", "times", "timestamp", "time", "timestamps", "t", "sec", "seconds"):
        if k in names or canon(k) in cmap:
            return k if k in names else cmap[canon(k)]
    return names[0]


def guess_cols(names):
    """Return ``(t, qx, qy, qz, qr, ax, ay, az)`` column names.

    Raises ``ValueError`` listing whichever fields could not be resolved.
    """
    names = list(names)
    cmap = {canon(n): n for n in names}

    t_col = _tget(names, cmap)
    qx, qy, qz = (_qget(names, cmap, k) for k in ("qx", "qy", "qz"))
    qr = _qget(names, cmap, "qr") or _qget(names, cmap, "qw")
    ax, ay, az = (_aget(names, cmap, axis) for axis in ("x", "y", "z"))

    miss = [k for k, v in dict(t=t_col, qx=qx, qy=qy, qz=qz, qr=qr, ax=ax, ay=ay, az=az).items() if v is None]
    if miss:
        raise ValueError(f"Missing columns: {miss}")
    return t_col, qx, qy, qz, qr, ax, ay, az


def guess_quat_only(names):
    """Like :func:`guess_cols` but for quaternion-only sensors (no accel)."""
    names = list(names)
    cmap = {canon(n): n for n in names}

    t_col = _tget(names, cmap)
    qx, qy, qz = (_qget(names, cmap, k) for k in ("qx", "qy", "qz"))
    qr = _qget(names, cmap, "qr") or _qget(names, cmap, "qw")

    miss = [k for k, v in dict(t=t_col, qx=qx, qy=qy, qz=qz, qr=qr).items() if v is None]
    if miss:
        raise ValueError(f"Missing columns: {miss}")
    return t_col, qx, qy, qz, qr


def parse_range(text):
    """Parse ``"a,b"`` or ``"a-b"`` into ``(min, max)``; ``None`` when empty."""
    if text is None:
        return None
    s = text.strip()
    if not s:
        return None
    s = s.replace(" ", "")
    parts = s.split("-") if "-" in s else s.split(",")
    if len(parts) != 2:
        raise ValueError("Provide exactly two numbers, like 3,8 or 3-8")
    a, b = float(parts[0]), float(parts[1])
    if b < a:
        a, b = b, a
    return (a, b)
