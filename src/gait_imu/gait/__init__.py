"""Gait pipelines, stride helpers, and metrics."""

from .stride import make_pairs, curves_from_pairs, build_outputs_from_pairs
from .ankle import process_files_ankle, compute_ankle_angle
from .knee import process_files_knee, compute_knee_series

__all__ = [
    "make_pairs",
    "curves_from_pairs",
    "build_outputs_from_pairs",
    "process_files_ankle",
    "compute_ankle_angle",
    "process_files_knee",
    "compute_knee_series",
]
