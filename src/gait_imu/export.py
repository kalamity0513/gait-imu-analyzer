"""CSV export of session results.

Writes four files under ``<base>``:

    <base>_overlay.csv       % gait, mean angle, sd angle (kept strides)
    <base>_strides_all.csv   % gait + each stride curve (all)
    <base>_strides_kept.csv  % gait + each kept stride curve
    <base>_metrics.csv       scalar/session metrics (cadence, CV, speed...)
"""

from __future__ import annotations

import csv
import os
from typing import Iterable, List, Tuple

import numpy as np

from .config import N_RESAMPLE


def _write_curves(path, pct, curves, indices: Iterable[int]):
    indices = list(indices)
    data = np.column_stack([pct, curves[indices].T.astype(float)])
    header = ["pct_gait"] + [f"stride_{i:03d}" for i in indices]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data)


def export_session(res: dict, base_path: str) -> List[str]:
    """Write the four CSVs and return their paths.

    ``base_path`` may include a trailing ``.csv``; suffixes are appended.
    """
    root, _ = os.path.splitext(base_path)
    written: List[str] = []

    time_norm = res.get("time_norm")
    curves = res.get("curves", np.empty((0, N_RESAMPLE)))
    if time_norm is not None and curves.size:
        pct = (time_norm * 100.0).astype(float)
        mean_c = np.nanmean(curves, axis=0).astype(float)
        std_c  = np.nanstd(curves, axis=0).astype(float)
        overlay_path = root + "_overlay.csv"
        np.savetxt(
            overlay_path,
            np.column_stack([pct, mean_c, std_c]),
            delimiter=",",
            header="pct_gait,angle_mean_deg,angle_std_deg",
            comments="",
        )
        written.append(overlay_path)

    curves_all = res.get("curves_all", np.empty((0, N_RESAMPLE)))
    keep_mask = np.asarray(res.get("keep_mask", np.ones(curves_all.shape[0], dtype=bool)))
    if time_norm is not None and curves_all.size:
        pct = (time_norm * 100.0).astype(float)

        all_path = root + "_strides_all.csv"
        _write_curves(all_path, pct, curves_all, range(curves_all.shape[0]))
        written.append(all_path)

        kept_idx = np.where(keep_mask)[0]
        if kept_idx.size:
            kept_path = root + "_strides_kept.csv"
            _write_curves(kept_path, pct, curves_all, kept_idx)
            written.append(kept_path)

    metrics_path = root + "_metrics.csv"
    with open(metrics_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in _metrics_rows(res):
            w.writerow([k, v])
    written.append(metrics_path)

    return written


def _metrics_rows(res: dict) -> List[Tuple[str, object]]:
    mode = res.get("mode", "ankle")
    stride_times = res.get("stride_times_s", np.array([]))
    lengths = res.get("stride_lengths_m", np.array([]))

    n_total = len(res.get("pairs_all", res.get("pairs", [])))
    n_kept = int(np.sum(res.get("keep_mask", np.ones(n_total, dtype=bool)))) if n_total else 0

    rows: List[Tuple[str, object]] = [
        ("pair_mode", mode),
        ("kept_strides", n_kept),
        ("total_strides", n_total),
        ("stride_time_mean_s", float(np.nanmean(stride_times)) if stride_times.size else np.nan),
        ("stride_time_sd_s",   float(np.nanstd(stride_times))  if stride_times.size else np.nan),
        ("cadence_spm", res.get("cadence_spm", np.nan)),
        ("robust_cv_stride_time_percent",  res.get("cv_robust", np.nan)),
        ("classic_cv_stride_time_percent", res.get("cv_classic", np.nan)),
        ("stride_length_mean_m", float(np.nanmean(lengths)) if lengths.size else np.nan),
        ("stride_length_sd_m",   float(np.nanstd(lengths))  if lengths.size else np.nan),
        ("walking_speed_ms", res.get("speed_ms", np.nan)),
        ("hs_detected_raw", len(res.get("HS_idx_raw", []))),
        ("hs_kept",         len(res.get("HS_idx", []))),
    ]
    if mode == "knee":
        rows.append(("knee_static_calibration", res.get("knee_baseline_note", "")))
    else:
        rows.append(("ankle_angle_note", res.get("ankle_angle_note", "")))
    return rows
