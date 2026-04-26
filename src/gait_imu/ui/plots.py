"""Pure plotting helpers used by the UI tabs.

Each function builds a matplotlib figure from a result dict; the
:class:`gait_imu.ui.app.IMUApp` is responsible for embedding them in
their containers. The visual language across all figures mirrors the
clinical theme defined in :mod:`gait_imu.theme`.
"""

from __future__ import annotations

from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np

from ..clinical_reference import (
    GAIT_PHASES,
    TOE_OFF_PCT,
    ankle_norm_band,
    knee_norm_band,
)
from ..config import N_RESAMPLE
from ..theme import PALETTE, PLOT_COLORS, soft_glow, style_axes


# ----------------------------------------------------------------------
#  Helpers
# ----------------------------------------------------------------------

def _empty(ax, msg="No data"):
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            transform=ax.transAxes, color=PALETTE["muted"], fontsize=11)
    style_axes(ax)


def _shade_gait_phases(ax, *, label_top=True, alpha_stance=0.35, alpha_swing=0.35,
                       y_label_frac=0.93):
    """Fill stance / swing bands across % gait and label phases."""
    ax.axvspan(0,             TOE_OFF_PCT, color=PLOT_COLORS["stance_fill"], alpha=alpha_stance, lw=0)
    ax.axvspan(TOE_OFF_PCT,   100,         color=PLOT_COLORS["swing_fill"],  alpha=alpha_swing,  lw=0)

    # Toe-off boundary
    ax.axvline(TOE_OFF_PCT, color=PALETTE["muted"], linestyle=(0, (3, 3)),
               linewidth=0.9, alpha=0.6)

    if label_top:
        # Top-edge phase chips (compact)
        ymin, ymax = ax.get_ylim()
        y_line = ymin + (ymax - ymin) * y_label_frac
        for ph in GAIT_PHASES:
            x = (ph.start_pct + ph.end_pct) * 0.5
            ax.text(x, y_line, ph.short, ha="center", va="bottom",
                    fontsize=8.5, color=PALETTE["muted_strong"], alpha=0.85,
                    fontweight="bold")
        # "STANCE" / "SWING" super-labels
        ax.text(TOE_OFF_PCT / 2, ymin + (ymax - ymin) * 0.99,
                "STANCE", ha="center", va="top",
                fontsize=8.5, color=PALETTE["muted"], alpha=0.55,
                fontweight="bold")
        ax.text((100 + TOE_OFF_PCT) / 2, ymin + (ymax - ymin) * 0.99,
                "SWING", ha="center", va="top",
                fontsize=8.5, color=PALETTE["muted"], alpha=0.55,
                fontweight="bold")


def _normative_band(ax, mode: str):
    """Draw a healthy-adult reference band as a soft background fill."""
    if mode == "ankle":
        pct, mu, sd = ankle_norm_band()
        label = "Healthy-adult reference"
    else:
        pct, mu, sd = knee_norm_band()
        label = "Healthy-adult reference"
    ax.fill_between(pct, mu - sd, mu + sd,
                    color=PLOT_COLORS["norm_band"], alpha=0.55,
                    linewidth=0, zorder=0.5,
                    label=label)
    # subtle reference mean as dotted ghost line
    ax.plot(pct, mu, color=PALETTE["muted"], linewidth=1.0, alpha=0.45,
            linestyle=(0, (1, 2)), zorder=0.9)


def draw_angle_segments(ax, t_m, angle, pairs, keep_mask, mode):
    n_t = len(t_m)
    n_a = len(angle)
    if not pairs or n_t == 0 or n_a == 0:
        _empty(ax, "No angle data")
        return

    if keep_mask is None or len(keep_mask) != len(pairs):
        keep_mask = np.ones(len(pairs), dtype=bool)

    for i, (a, b) in enumerate(pairs):
        if b <= a:
            continue
        end_idx = min(b + 1, n_t, n_a)
        start_idx = min(max(a, 0), end_idx - 1)
        if end_idx - start_idx < 2:
            continue
        kept = bool(keep_mask[i]) if i < len(keep_mask) else True
        ax.plot(
            t_m[start_idx:end_idx],
            angle[start_idx:end_idx],
            linewidth=(2.0 if kept else 1.0),
            alpha=(0.95 if kept else 0.22),
            linestyle="-" if kept else "--",
            color=PLOT_COLORS["stride"] if kept else PLOT_COLORS["stride_off"],
            solid_capstyle="round",
        )

    ax.set_ylabel("Ankle angle (deg)" if mode == "ankle" else "Knee flexion (deg)")
    style_axes(ax)
    ax.grid(True, axis="y", alpha=0.7)


def draw_stride_rail(ax, t_m, pairs_all, keep_mask):
    if not pairs_all:
        _empty(ax, "No stride segments")
        ax.grid(False)
        return

    if keep_mask is None or len(keep_mask) != len(pairs_all):
        keep_mask = np.ones(len(pairs_all), dtype=bool)

    bars_kept, bars_off = [], []
    for i, (a, b) in enumerate(pairs_all):
        if b <= a or a < 0 or b >= len(t_m):
            continue
        t0 = float(t_m[a]); t1 = float(t_m[b])
        (bars_kept if keep_mask[i] else bars_off).append((t0, t1 - t0))

    bar_y, bar_h = 0.30, 0.40
    if bars_off:
        ax.broken_barh(bars_off, (bar_y, bar_h),
                       facecolors=PLOT_COLORS["stride_off"], edgecolors="none", alpha=0.40)
    if bars_kept:
        ax.broken_barh(bars_kept, (bar_y, bar_h),
                       facecolors=PLOT_COLORS["stride"], edgecolors="none", alpha=0.95)

    for i, (a, b) in enumerate(pairs_all):
        if i >= len(keep_mask) or not keep_mask[i] or b <= a or b >= len(t_m):
            continue
        t0, t1 = float(t_m[a]), float(t_m[b])
        ax.text((t0 + t1) * 0.5, bar_y + bar_h / 2, f"{i}",
                ha="center", va="center", fontsize=8.5, color="white",
                fontweight="bold", alpha=0.95)

    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_ylabel("Strides", labelpad=10, fontsize=9.5, color=PALETTE["muted"])
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(PLOT_COLORS["axis"])
    ax.grid(False)


# ----------------------------------------------------------------------
#  Top-level figure builders
# ----------------------------------------------------------------------

def build_acceleration_figure(res, *, start_peak_idx=None):
    """3-row figure: vertical accel + HS markers, stride rail, angle segments."""
    fig = plt.figure(figsize=(12.0, 7.8), constrained_layout=True)
    gs = fig.add_gridspec(nrows=3, ncols=1, height_ratios=[3.0, 0.85, 2.2], hspace=0.06)
    ax_top  = fig.add_subplot(gs[0, 0])
    ax_rail = fig.add_subplot(gs[1, 0], sharex=ax_top)
    ax_ang  = fig.add_subplot(gs[2, 0], sharex=ax_top)

    tf, vert_s = res["tf"], res["vert_s"]
    HS_idx_raw = res["HS_idx_raw"]
    HS_idx_drop = res["HS_idx_drop"]
    HS_idx = res["HS_idx"]
    t_m = res["t_m"]
    pairs = res["pairs"]
    pairs_all = res.get("pairs_all", pairs)
    keep_mask_all = res.get("keep_mask", np.ones(len(pairs_all), dtype=bool))
    mode = res.get("mode", "ankle")

    # subtle line halo for the vertical-accel signal
    ax_top.plot(tf, vert_s, linewidth=1.5, color=PLOT_COLORS["accel"],
                label="Vertical acceleration", path_effects=soft_glow(PLOT_COLORS["accel_soft"], lw=4))
    ax_top.axhline(0, linestyle=(0, (4, 4)), linewidth=0.9, color=PALETTE["border_strong"])

    # Light kept-stride spans behind everything
    for a, b in pairs:
        if 0 <= a < len(t_m) and 0 <= b < len(t_m):
            ax_top.axvspan(t_m[a], t_m[b], alpha=0.06, color=PALETTE["accent"], zorder=0.5)

    if HS_idx_raw.size:
        ax_top.scatter(tf[HS_idx_raw], vert_s[HS_idx_raw], s=22, alpha=0.45,
                       label="HS detected (raw)", marker="o",
                       color=PLOT_COLORS["hs_raw"], edgecolors="none")
    if HS_idx_drop.size:
        ax_top.scatter(tf[HS_idx_drop], vert_s[HS_idx_drop], s=46, alpha=0.95,
                       marker="x", linewidths=2.0, label="HS filtered out",
                       color=PLOT_COLORS["hs_drop"])
    if HS_idx.size:
        ax_top.scatter(tf[HS_idx], vert_s[HS_idx], s=58, alpha=1.0,
                       marker="o", edgecolors="white", linewidths=1.4,
                       label="HS kept", color=PLOT_COLORS["hs_keep"], zorder=4)
        for j, k in enumerate(HS_idx):
            ax_top.text(tf[k], vert_s[k], f"{j}", fontsize=8, va="bottom", ha="center",
                        alpha=0.7, color=PALETTE["muted_strong"])

    if start_peak_idx is not None and HS_idx.size:
        j = max(0, min(int(start_peak_idx), len(HS_idx) - 1))
        k = HS_idx[j]
        ax_top.scatter([tf[k]], [vert_s[k]], s=200, marker="*", zorder=6,
                       label=f"Start HS #{j}", color=PALETTE["accent"],
                       edgecolors="white", linewidths=1.6)
        ax_top.axvline(tf[k], linestyle=":", linewidth=1.1, alpha=0.7, color=PALETTE["accent"])

    title_mode = "Foot world-vertical acceleration  ·  ANKLE" if mode == "ankle" \
        else "Shank world-vertical acceleration  ·  KNEE"
    sub = res.get("knee_baseline_note") if mode == "knee" else res.get("ankle_angle_note")
    if sub:
        title_mode += f"  ·  {sub}"
    ax_top.set_title(title_mode, loc="left", pad=12)
    ax_top.set_ylabel("Acceleration (m/s²)")
    style_axes(ax_top)
    leg = ax_top.legend(loc="upper right", frameon=False, ncol=4, handlelength=1.4)
    if leg:
        for t in leg.get_texts():
            t.set_color(PALETTE["muted_strong"])
    plt.setp(ax_top.get_xticklabels(), visible=False)

    draw_stride_rail(ax_rail, t_m, pairs_all, keep_mask_all)
    plt.setp(ax_rail.get_xticklabels(), visible=False)

    angle = res.get("angle_series", np.array([]))
    keep_kept = np.ones(len(pairs), dtype=bool)
    draw_angle_segments(ax_ang, t_m, angle, pairs, keep_kept, mode)
    ax_ang.set_xlabel("Time (s)")
    ax_ang.set_title("Per-stride joint angle (kept)", loc="left", pad=8, fontsize=10.5)

    return fig


def build_overlay_figure(res, *, show_normative: bool = True):
    """Mean ± SD vs % gait, with phase shading and normative band."""
    fig, ax = plt.subplots(figsize=(11.0, 5.4))
    time_norm = res.get("time_norm")
    curves = res.get("curves", np.empty((0, N_RESAMPLE)))
    pct = (time_norm * 100.0) if time_norm is not None \
        else np.linspace(0, 100, curves.shape[1] if curves.size else 101)

    mode = res.get("mode", "ankle")

    # Pre-compute y-range for phase labels
    if curves.size:
        mean_c = np.nanmean(curves, axis=0)
        std_c  = np.nanstd(curves, axis=0)
        ymin = float(np.nanmin(mean_c - std_c))
        ymax = float(np.nanmax(mean_c + std_c))
    else:
        ymin, ymax = -10, 60

    # Background: phase shading
    ax.set_xlim(0, 100)
    pad = (ymax - ymin) * 0.18 if (ymax > ymin) else 5.0
    ax.set_ylim(ymin - pad, ymax + pad * 1.4)

    if show_normative:
        _normative_band(ax, mode)

    if curves.size:
        # Soft individual stride traces in light blue
        n = curves.shape[0]
        for i in range(n):
            ax.plot(pct, curves[i], linewidth=0.8, alpha=0.30,
                    color=PLOT_COLORS["stride_trace"], zorder=1.5)

        # Mean ± SD band
        ax.fill_between(pct, mean_c - std_c, mean_c + std_c,
                        alpha=0.30, color=PLOT_COLORS["fill"],
                        linewidth=0, label="±1 SD across kept strides",
                        zorder=2)
        # Mean line with subtle halo
        ax.plot(pct, mean_c, linewidth=3.2, color=PLOT_COLORS["mean"],
                label="Kept-stride mean",
                path_effects=soft_glow(PLOT_COLORS["mean"], lw=8, alpha=0.10),
                zorder=3)
    else:
        _empty(ax, "No kept strides — toggle some on the All Strides tab")

    _shade_gait_phases(ax)

    ax.set_title(("Ankle dorsiflexion / plantar-flexion" if mode == "ankle"
                  else "Knee flexion") + " — gait cycle (HS → HS, kept strides)",
                 loc="left", pad=14)
    ax.set_xlabel("Gait cycle (%)")
    ax.set_ylabel("Ankle angle (deg)" if mode == "ankle" else "Knee flexion (deg)")
    ax.set_xticks([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    style_axes(ax)
    if curves.size:
        leg = ax.legend(loc="upper right", frameon=False)
        for t in leg.get_texts():
            t.set_color(PALETTE["muted_strong"])
    fig.tight_layout()
    return fig


def build_all_strides_figure(res):
    """Returns ``(fig, line_artists)``; the UI hooks pick events on the artists."""
    fig, ax = plt.subplots(figsize=(11.0, 5.4))
    time_norm = res.get("time_norm")
    curves_all = res.get("curves_all", np.empty((0, N_RESAMPLE)))
    keep_mask = res.get("keep_mask", np.ones(curves_all.shape[0], dtype=bool))
    pct = (time_norm * 100.0) if time_norm is not None \
        else np.linspace(0, 100, curves_all.shape[1] if curves_all.size else 101)

    mode = res.get("mode", "ankle")

    if curves_all.size:
        ymin = float(np.nanmin(curves_all))
        ymax = float(np.nanmax(curves_all))
    else:
        ymin, ymax = -10, 60
    pad = (ymax - ymin) * 0.18 if (ymax > ymin) else 5.0
    ax.set_xlim(0, 100)
    ax.set_ylim(ymin - pad, ymax + pad * 1.4)

    _shade_gait_phases(ax)

    lines = []
    if curves_all.size:
        for i in range(curves_all.shape[0]):
            kept = bool(keep_mask[i]) if i < len(keep_mask) else True
            ln, = ax.plot(
                pct, curves_all[i],
                linewidth=(1.9 if kept else 1.0),
                alpha=(0.92 if kept else 0.18),
                linestyle=("-" if kept else "--"),
                picker=True,
                color=PLOT_COLORS["stride"] if kept else PLOT_COLORS["stride_off"],
                solid_capstyle="round",
            )
            try:
                ln.set_pickradius(5)
            except Exception:
                pass
            ln.set_gid(i)
            lines.append(ln)
    else:
        _empty(ax, "No strides yet — load files to begin")

    ax.set_title(("Ankle" if mode == "ankle" else "Knee")
                 + " — every stride (click line or row to toggle)",
                 loc="left", pad=14)
    ax.set_xlabel("Gait cycle (%)")
    ax.set_ylabel("Ankle angle (deg)" if mode == "ankle" else "Knee flexion (deg)")
    ax.set_xticks([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    style_axes(ax)
    fig.tight_layout()
    return fig, lines


# ----------------------------------------------------------------------
#  Compact dashboard plots
# ----------------------------------------------------------------------

def build_dashboard_overlay_figure(res):
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    time_norm = res.get("time_norm")
    curves = res.get("curves")
    mode = res.get("mode", "ankle")

    if curves is not None and curves.size:
        mean_c = np.nanmean(curves, axis=0)
        std_c  = np.nanstd(curves, axis=0)
        pct = time_norm * 100.0
        ymin, ymax = float(np.nanmin(mean_c - std_c)), float(np.nanmax(mean_c + std_c))
        pad = (ymax - ymin) * 0.18 if ymax > ymin else 5.0
        ax.set_ylim(ymin - pad, ymax + pad)
    else:
        ax.set_ylim(-10, 60)

    ax.set_xlim(0, 100)

    # subtle phase shading without phase labels (saves space)
    ax.axvspan(0,            TOE_OFF_PCT, color=PLOT_COLORS["stance_fill"], alpha=0.30, lw=0)
    ax.axvspan(TOE_OFF_PCT, 100,          color=PLOT_COLORS["swing_fill"],  alpha=0.30, lw=0)
    ax.axvline(TOE_OFF_PCT, color=PALETTE["muted"], linestyle=(0, (3, 3)),
               linewidth=0.8, alpha=0.5)

    if curves is not None and curves.size:
        ax.fill_between(pct, mean_c - std_c, mean_c + std_c,
                        alpha=0.30, color=PLOT_COLORS["fill"], linewidth=0)
        ax.plot(pct, mean_c, linewidth=2.6, color=PLOT_COLORS["mean"],
                path_effects=soft_glow(PLOT_COLORS["mean"], lw=6, alpha=0.10))
    else:
        _empty(ax, "Mean ± SD curve will appear here")

    ax.set_xlabel("Gait cycle (%)")
    ax.set_ylabel("Ankle (deg)" if mode == "ankle" else "Knee (deg)")
    ax.set_title("Mean stride curve  ·  ± 1 SD", loc="left", pad=10, fontsize=11)
    ax.set_xticks([0, 25, 50, 75, 100])
    style_axes(ax)
    fig.tight_layout()
    return fig


def build_dashboard_histogram_figure(res):
    fig, ax = plt.subplots(figsize=(5.0, 2.8))
    stride_times = res.get("stride_times_s", np.array([]))
    if stride_times.size:
        bins = max(6, min(18, int(np.sqrt(stride_times.size))))
        n, edges, patches = ax.hist(
            stride_times, bins=bins,
            color=PLOT_COLORS["mean"], alpha=0.92,
            edgecolor="white", linewidth=1.2,
            rwidth=0.92,
        )
        mu = float(np.nanmean(stride_times))
        if np.isfinite(mu):
            ax.axvline(mu, linestyle="--", linewidth=1.6, color=PLOT_COLORS["hs_keep"])
            ax.text(mu, ax.get_ylim()[1] * 0.95, f"  μ = {mu:.2f} s",
                    color=PLOT_COLORS["hs_keep"], fontsize=9, va="top",
                    fontweight="bold")
    else:
        _empty(ax, "Stride-time distribution")
    ax.set_xlabel("Stride time (s)")
    ax.set_ylabel("Strides")
    ax.set_title("Stride-time distribution", loc="left", pad=10, fontsize=11)
    style_axes(ax)
    fig.tight_layout()
    return fig
