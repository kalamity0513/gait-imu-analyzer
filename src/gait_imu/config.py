"""Tunable parameters for signal processing and calibration.

Constants are exposed as module attributes so callers and tests can
override them at runtime if needed.
"""

# Physics
G = 9.81  # m/s^2

# Heel-strike detection (vertical world acceleration)
ACC_SMOOTH_S    = 0.015   # moving-mean window
PROM_STD        = 2.3     # peak prominence in robust-std units
MIN_HS_SEP_S    = 0.30    # min spacing between adjacent HS events
MATCH_TOL_S     = 0.03    # tolerance when matching two sensor timebases

MIN_WIDTH_S     = 0.005   # min peak width
LOCAL_WIN_S     = 0.60    # window for local mean/std gating
HEIGHT_K_GLOBAL = 2.8     # global threshold (k * robust std)
HEIGHT_K_LOCAL  = 2.2     # local threshold (k * local std)

# Stride curve resampling / smoothing
N_RESAMPLE      = 300
SAVGOL_WIN      = 31
SAVGOL_POLY     = 3

# Auto-window inference (near-zero acceleration ~ standing still)
ZERO_TOL_MSS    = 0.15
ZERO_MIN_LEN_S  = 1.5
