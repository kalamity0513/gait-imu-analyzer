"""Regenerate the matplotlib screenshots used in README.md.

Run from the repo root:

    python scripts/generate_screenshots.py

The script loads the bundled demo sessions in ``data/`` and uses the
exact figure builders the live UI uses, with the same dark theme. The
GUI-only screenshots (Home tab, Dashboard tile row, pill tabs) cannot
be produced headlessly — capture those from a running app and drop them
into ``docs/screenshots/app_*.png``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend — no Tk needed
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from gait_imu.gait import (  # noqa: E402
    build_outputs_from_pairs,
    process_files_ankle,
    process_files_knee,
)
from gait_imu.theme import style_mpl  # noqa: E402
from gait_imu.ui.plots import (  # noqa: E402
    build_acceleration_figure,
    build_all_strides_figure,
    build_dashboard_histogram_figure,
    build_dashboard_overlay_figure,
    build_overlay_figure,
)
from gait_imu.ui.sensor_diagram import build_sensor_diagram  # noqa: E402


OUT = REPO / "docs" / "screenshots"
DPI = 160


def save(fig, name: str, *, tight: bool = True) -> None:
    path = OUT / name
    fig.savefig(path, dpi=DPI,
                bbox_inches="tight" if tight else None,
                pad_inches=0.15 if tight else 0.0,
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  wrote {path.relative_to(REPO)}")


def render_session(label: str, base, res) -> None:
    save(build_acceleration_figure(res), f"acceleration_{label}.png")
    save(build_overlay_figure(res, show_normative=True), f"overlay_{label}.png")
    fig, _ = build_all_strides_figure(res)
    save(fig, f"all_strides_{label}.png")
    fig, _ = build_dashboard_overlay_figure(res)
    save(fig, f"dash_overlay_{label}.png")
    fig, _ = build_dashboard_histogram_figure(res)
    save(fig, f"dash_hist_{label}.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    style_mpl()

    print("Rendering sensor-placement diagrams …")
    # tight=False — preserve the figure's full width so the 3D-perspective
    # leader labels (rendered outside the subplot's data area) are not
    # clipped at the figure edge.
    save(build_sensor_diagram("ankle"), "sensor_ankle.png", tight=False)
    save(build_sensor_diagram("knee"),  "sensor_knee.png", tight=False)

    print("Processing ankle demo session …")
    base = process_files_ankle(
        str(REPO / "data" / "Subject1_A1" / "Subject1_A1_Foot.csv"),
        str(REPO / "data" / "Subject1_A1" / "Subject1_A1_Shank.csv"),
        ankle_mode="dfpf",
    )
    res = build_outputs_from_pairs(base)
    render_session("ankle", base, res)

    print("Processing knee demo session …")
    base = process_files_knee(
        str(REPO / "data" / "Subject1_K1" / "Subject1_K1_Shank.csv"),
        str(REPO / "data" / "Subject1_K1" / "Subject1_K1_Thigh.csv"),
    )
    res = build_outputs_from_pairs(base)
    render_session("knee", base, res)

    print("Done.")


if __name__ == "__main__":
    main()
