"""Clinical reference ranges and gait-cycle phase definitions.

Used by both the dashboard (status pills, reference range bars) and
the plotting layer (phase shading on overlay plots). Sources are
healthy-adult, level-walking populations — the values are intended as
*screening cues*, not strict cut-offs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


# ----------------------------------------------------------------------
#  Reference ranges (healthy adult, level overground walking)
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class RefRange:
    """A reference range with a *normal* band and *acceptable* margins."""
    label:     str
    unit:      str
    normal:    Tuple[float, float]   # green band
    watch:     Tuple[float, float]   # amber band (extends beyond normal)
    note:      str = ""

    def status(self, value: Optional[float]) -> str:
        """Return ``"normal" | "watch" | "atypical" | "unknown"``."""
        if value is None or not np.isfinite(value):
            return "unknown"
        if self.normal[0] <= value <= self.normal[1]:
            return "normal"
        if self.watch[0] <= value <= self.watch[1]:
            return "watch"
        return "atypical"


REFERENCE = {
    # Wider, more forgiving bands so most healthy adult walking
    # — including comfortable indoor / lab pacing — reads as Normal.
    "cadence_spm": RefRange(
        label="Cadence",
        unit="spm",
        normal=(85.0, 130.0),
        watch=(70.0, 145.0),
        note="Typical adult cadence: ~85–130 steps/min.",
    ),
    "walking_speed_ms": RefRange(
        label="Walking Speed",
        unit="m/s",
        normal=(0.85, 1.55),
        watch=(0.60, 1.85),
        note="Comfortable adult walking ≈ 0.85–1.55 m/s.",
    ),
    "stride_length_m": RefRange(
        label="Stride Length",
        unit="m",
        normal=(1.05, 1.65),
        watch=(0.80, 1.90),
        note="Adult stride length scales with height; 1.05–1.65 m typical.",
    ),
    "stride_time_s": RefRange(
        label="Stride Time",
        unit="s",
        normal=(0.90, 1.30),
        watch=(0.75, 1.50),
        note="HS-to-HS stride duration; typical 0.90–1.30 s.",
    ),
    "cv_stride_time_pct": RefRange(
        label="Gait Variability",
        unit="%",
        normal=(0.0, 4.0),
        watch=(0.0, 6.5),
        note="Robust CV of stride time; healthy adults usually < 4%.",
    ),
}


# ----------------------------------------------------------------------
#  Gait-cycle phases (Perry & Burnfield)
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class GaitPhase:
    name:       str
    short:      str
    start_pct:  float
    end_pct:    float
    family:     str  # "stance" or "swing"


# Standard 8-phase model, expressed as % gait cycle from initial contact.
GAIT_PHASES: List[GaitPhase] = [
    GaitPhase("Initial Contact",   "IC",  0.0,   2.0,  "stance"),
    GaitPhase("Loading Response",  "LR",  2.0,  12.0,  "stance"),
    GaitPhase("Mid-Stance",        "MSt", 12.0, 31.0,  "stance"),
    GaitPhase("Terminal Stance",   "TSt", 31.0, 50.0,  "stance"),
    GaitPhase("Pre-Swing",         "PSw", 50.0, 62.0,  "stance"),
    GaitPhase("Initial Swing",     "ISw", 62.0, 75.0,  "swing"),
    GaitPhase("Mid-Swing",         "MSw", 75.0, 87.0,  "swing"),
    GaitPhase("Terminal Swing",    "TSw", 87.0, 100.0, "swing"),
]

# Toe-off occurs at the stance/swing boundary (~62% of the gait cycle).
TOE_OFF_PCT = 62.0


# ----------------------------------------------------------------------
#  Approximate normative bands (deg vs % gait)
# ----------------------------------------------------------------------
#
# These are coarse, healthy-adult shapes used as a *visual reference
# band* on the overlay plot — not for diagnosis. A more rigorous build
# would interpolate published normative tables (e.g. Winter, Kadaba).

def ankle_norm_band(n_pts: int = 300) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Approx. healthy-adult ankle angle (DF positive) ± SD over the cycle."""
    pct = np.linspace(0, 100, n_pts)
    # Schematic shape: small DF at IC → brief PF at LR → DF rise through
    # MSt-TSt → rapid PF at push-off → recovery to neutral DF in swing.
    mean = (
        2.0 * np.sin(2 * np.pi * pct / 100.0 - 0.5)        # base oscillation
        + 8.0 * np.exp(-((pct - 40.0) ** 2) / (2 * 12.0 ** 2))   # DF peak
        - 18.0 * np.exp(-((pct - 60.0) ** 2) / (2 * 4.0 ** 2))   # PF push-off
        + 3.0 * np.exp(-((pct - 80.0) ** 2) / (2 * 8.0 ** 2))    # swing DF
    )
    sd = 3.5 + 1.5 * np.exp(-((pct - 60.0) ** 2) / (2 * 5.0 ** 2))
    return pct, mean, sd


def knee_norm_band(n_pts: int = 300) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Approx. healthy-adult knee flexion ± SD over the cycle."""
    pct = np.linspace(0, 100, n_pts)
    mean = (
        18.0 * np.exp(-((pct - 15.0) ** 2) / (2 * 8.0 ** 2))       # loading-response flex
        + 60.0 * np.exp(-((pct - 73.0) ** 2) / (2 * 9.0 ** 2))     # swing-phase flex
        + 4.0
    )
    sd = 4.0 + 2.0 * np.exp(-((pct - 73.0) ** 2) / (2 * 9.0 ** 2))
    return pct, mean, sd


# ----------------------------------------------------------------------
#  Plain-language interpretation
# ----------------------------------------------------------------------

@dataclass
class Finding:
    severity: str     # "info" | "ok" | "watch" | "atypical"
    headline: str
    detail:   str = ""


def interpret_session(res: dict) -> List[Finding]:
    """Translate a result dict into clinical-style findings.

    Each Finding is rendered as a coloured row in the interpretation
    panel. The rules are intentionally conservative so they fit any
    healthy-adult IMU walking-trial context.
    """
    out: List[Finding] = []

    cadence = res.get("cadence_spm", float("nan"))
    speed   = res.get("speed_ms",    float("nan"))
    cv_rob  = res.get("cv_robust",   float("nan"))

    stride_times = res.get("stride_times_s", np.array([]))
    lengths      = res.get("stride_lengths_m", np.array([]))

    n_total = len(res.get("pairs_all", res.get("pairs", [])))
    n_kept  = int(np.sum(res.get("keep_mask", np.ones(n_total, dtype=bool)))) if n_total else 0

    # Sample-size guard
    if n_kept < 4:
        out.append(Finding(
            "watch",
            "Very few kept strides",
            "Aim for ≥ 4 strides for stable mean ± SD. Use the All-Strides "
            "tab to keep more, or trim less aggressively.",
        ))

    # Walking speed
    s = REFERENCE["walking_speed_ms"].status(speed)
    if s == "normal":
        out.append(Finding("ok", "Walking speed within typical range",
                           f"{speed:.2f} m/s — community-ambulation level."))
    elif s == "watch":
        out.append(Finding("watch", "Walking speed slightly outside typical band",
                           f"{speed:.2f} m/s — review with reference range and trial conditions."))
    elif s == "atypical":
        below = np.isfinite(speed) and speed < REFERENCE["walking_speed_ms"].normal[0]
        out.append(Finding(
            "atypical",
            "Walking speed atypical for healthy adult",
            f"{speed:.2f} m/s — "
            + ("below community-ambulation threshold" if below else "above brisk-walking band"),
        ))

    # Cadence
    s = REFERENCE["cadence_spm"].status(cadence)
    if s == "watch":
        out.append(Finding("watch", "Cadence outside typical band",
                           f"{cadence:.0f} spm — typical 100–125 spm."))
    elif s == "atypical":
        out.append(Finding("atypical", "Cadence atypical",
                           f"{cadence:.0f} spm — well outside healthy adult range."))

    # Stride length (ankle pipeline only)
    if res.get("mode") == "ankle" and lengths.size:
        mu_L = float(np.nanmean(lengths))
        s = REFERENCE["stride_length_m"].status(mu_L)
        if s == "watch":
            out.append(Finding("watch", "Stride length slightly short",
                               f"{mu_L:.2f} m — verify ZUPT and baseline windows."))
        elif s == "atypical":
            out.append(Finding("atypical", "Stride length atypical",
                               f"{mu_L:.2f} m — check calibration windows."))

    # Variability
    s = REFERENCE["cv_stride_time_pct"].status(cv_rob)
    if s == "watch":
        out.append(Finding("watch", "Elevated stride-time variability",
                           f"CV = {cv_rob:.1f}% — borderline; review stride curation."))
    elif s == "atypical":
        out.append(Finding("atypical", "High stride-time variability",
                           f"CV = {cv_rob:.1f}% — review HS detection and trial duration."))

    # Stride-time mean band
    if stride_times.size:
        mu_st = float(np.nanmean(stride_times))
        s = REFERENCE["stride_time_s"].status(mu_st)
        if s == "watch":
            out.append(Finding("watch", "Stride duration borderline",
                               f"{mu_st:.2f} s — within acceptable but outside typical band."))
        elif s == "atypical":
            out.append(Finding("atypical", "Stride duration atypical",
                               f"{mu_st:.2f} s — verify start-HS index and trim."))

    if not out:
        out.append(Finding("info", "Session looks within typical ranges",
                           "All headline metrics fall inside healthy-adult bands."))
    return out
