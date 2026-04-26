# Gait IMU Analyzer

An interactive desktop tool for ankle and knee gait analysis from a
minimal two-IMU configuration. Built as the visualisation and stride-
curation layer for the Honours thesis *Validating IMU-Derived Joint
Kinematics for Pediatric Gait Analysis*
(K. Jijith, University of Sydney, 2025).

![Demo](docs/screenshots/demo.gif)

---

## Background

> Gait dysfunction is a hallmark of numerous neuromuscular and
> musculoskeletal conditions, including cerebral palsy, stroke,
> muscular dystrophy, spina bifida, and lower-limb trauma. […]
> 3D motion capture systems have been the gold standard for studying
> gait, […] however, require a specialised lab, expensive equipment,
> and trained personnel, making them impractical for frequent use,
> especially in young children. […] To address these limitations,
> inertial measurement units (IMUs) have emerged as a promising
> alternative.
>
> — *Chapter 1, Introduction*

The thesis poses a single, focused validation question:

> The central question is whether a minimal IMU configuration can
> reproduce MoCap-quality joint angles with sufficient accuracy and
> repeatability for clinical interpretation.
>
> — *Abstract*

This repository ships the **analysis tool that supported that work** —
a Python desktop application for processing, visualising, and curating
the IMU data behind those experiments.

---

## What this tool does

> I developed an interactive IMU visualiser that streamlined the
> analysis workflow by enabling efficient review of raw and processed
> signals, stride selection, and automated generation of the plots
> incorporated in this thesis.
>
> — *Statement of Student Contribution*

Concretely, the app:

- ingests two synchronised IMU CSV streams (ankle = foot + shank;
  knee = shank + thigh);
- performs sensor-to-segment **functional calibration**, so the precise
  rotation of each sensor on the limb is not critical;
- detects **heel strikes** from world-vertical foot/shank acceleration;
- segments **strides** between consecutive ipsilateral heel strikes;
- computes sagittal-plane **ankle dorsi/plantar-flexion** or
  **knee flexion** for each stride;
- normalises strides to 0–100 % gait and reports a **mean ± SD**
  ensemble curve plus spatiotemporal metrics (cadence, stride time,
  stride length, walking speed, robust coefficient of variation);
- lets the operator **keep or drop** individual strides — a reproducible
  alternative to ad-hoc cropping.

---

## Validation summary

Reported in Chapter 5 of the thesis. Vicon Blue Trident IMUs were
recorded concurrently with optical motion capture during healthy adult
level walking:

| Joint           | RMSE  | MAE   | Bias                | Pearson *r* | CCC      |
| --------------- | ----- | ----- | ------------------- | ----------- | -------- |
| Ankle (DF/PF)   | 2.89° | 2.23° | +1.39°              | 0.974       | 0.966    |
| Knee (flexion)  | 2.18° | —     | ≈ 0° (95 % CI ± 0.43°) | 0.994       | very high |

> Taken together, these findings demonstrate that a two-IMU
> configuration can estimate sagittal ankle and knee angles within
> ~3° of MoCap with high concordance across strides.
>
> — *Abstract*

---

## Install and run

Requires **Python ≥ 3.9** (macOS, Linux, or Windows).

```bash
git clone https://github.com/kalamity0513/gait-imu-analyzer.git
cd gait-imu-analyzer

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
```

> **macOS note.** The app uses Tkinter, which ships with the python.org
> installer but is not always included with Homebrew Python. If
> `python -m tkinter` raises an error, install `brew install python-tk`.

Launch:

```bash
gait-imu                # console-script
# or
python -m gait_imu      # equivalent
```

---

## How it looks — what each tab is for

The descriptions below are quoted from **Appendix C** of the thesis,
where each tab is documented as part of the methodology.

### Home — placement + upload

A two-step onboarding flow. **Step 1** shows three views of the
anatomical leg (front, side, 3D perspective) with IMU pucks marked,
alongside a numbered placement panel. **Step 2** is the joint pick
(*Ankle / Knee*) and CSV upload.

### Acceleration / HS

> The upper panel shows the smoothed vertical acceleration with
> automatically detected heel strikes (candidate peaks, rejected
> peaks, and peaks retained after gating). The middle rail
> summarises HS-to-HS stride segments over absolute time, and the
> lower panel overlays ankle or knee angle segments aligned to the
> same timebase. This view was used to verify heel-strike detection
> and to choose the starting peak for stride segmentation.
>
> — *Appendix C.1*

### Gait-Cycle Overlay

> Each kept stride is normalised from heel strike to heel strike and
> resampled to a fixed number of points, allowing computation of the
> mean joint angle trajectory and its standard deviation over the
> gait cycle. This tab was used to inspect whether IMU-derived joint
> kinematics showed the expected stance and swing features and to
> compare different calibration or trimming choices.
>
> — *Appendix C.2*

A lilac healthy-adult reference band can optionally be overlaid for
visual comparison.

### All Strides

> Each line represents a single stride normalised to percentage gait.
> Clicking a curve or its entry in the legend toggles whether that
> stride is kept for subsequent averaging and metric calculation.
> This interface was used to exclude atypical strides (e.g. first
> steps, turns, or obvious artefacts) in a transparent and
> reproducible way.
>
> — *Appendix C.3*

### Dashboard

> Compact "clinical" tiles summarise cadence, stride time, stride
> length, walking speed, and gait variability, alongside a mean ± SD
> joint-angle curve and a stride-time histogram. A session summary
> panel provides a textual description and simple sanity checks
> (e.g. unusually long stride times or very low walking speed).
>
> — *Appendix C.5*

Each tile carries a status pill (Normal / Watch / Atypical) and a
healthy-adult reference-range bar; hovering flips the card to reveal
a plain-language description of how the metric is computed.

### Setup / Export

Calibration windows (standing / flexion / ankle-zero), stride trimming,
and CSV export of overlay, all-strides, kept-strides, and metrics
tables.

---

## Bundled demo data

> **Demo data only.** The two sessions in `data/` ship with the repo
> purely so you can try the pipeline end-to-end without recording
> your own IMU streams. They are not the cohort recordings used for
> the thesis validation, and the numbers reported by the app on
> these files should be treated as illustrative.

| Folder              | Joint | Files to load                                                |
| ------------------- | ----- | ------------------------------------------------------------ |
| `data/Subject1_A1/` | Ankle | `Subject1_A1_Foot.csv`, `Subject1_A1_Shank.csv`              |
| `data/Subject1_K1/` | Knee  | `Subject1_K1_Shank.csv`, `Subject1_K1_Thigh.csv`             |

### Walk-through (ankle session)

1. Launch `gait-imu`.
2. **Home → Step 1** — read the placement panel; mount the **Foot IMU**
   on the dorsum (top of the foot, just past the laces) and the
   **Shank IMU** on the antero-medial mid-shank.
3. **Home → Step 2** — pick *Ankle (Foot + Shank)* and the
   *Functional DF/PF* angle method; press **Select CSV files**.
4. Pick `data/Subject1_A1/Subject1_A1_Foot.csv`, then
   `Subject1_A1_Shank.csv`.
5. Inspect the **Dashboard**, **Acceleration / HS**, **Gait-Cycle
   Overlay**, and **All Strides** tabs. Drop atypical strides on
   *All Strides* → press **Recompute from kept**.
6. From **Setup → Export CSV** four files are written
   (`*_overlay.csv`, `*_strides_all.csv`, `*_strides_kept.csv`,
   `*_metrics.csv`).

The knee session uses the same flow with `data/Subject1_K1/`.

---

## CSV format

One row per IMU sample. Columns are auto-detected — recognised aliases:

| Quantity     | Recognised column names                                              |
| ------------ | -------------------------------------------------------------------- |
| Time         | `time_s`, `time`, `timestamp`, `t`, `sec`, `seconds`                 |
| Quaternion   | `qx, qy, qz, qr` (or `qw`); also any `Q*` / `Quat_*` variant         |
| Acceleration | `ax, ay, az` (m/s²); also `acc_x`, `accelerometer_x`, `acc_x_mss`, … |

The **distal** CSV (foot for ankle, shank for knee) needs quaternion
*and* accelerometer columns. The **proximal** CSV (shank or thigh)
needs quaternions only.

---

## Programmatic use

The pipelines are pure functions — callable from a notebook or batch
script without launching the UI.

```python
from gait_imu.gait import process_files_ankle, build_outputs_from_pairs
from gait_imu.export import export_session

base = process_files_ankle(
    "data/Subject1_A1/Subject1_A1_Foot.csv",
    "data/Subject1_A1/Subject1_A1_Shank.csv",
    ankle_mode="dfpf",          # or "so3"
)
res = build_outputs_from_pairs(base)
export_session(res, "exports/subject1.csv")
```

For knee analyses, swap in `process_files_knee` with shank + thigh CSVs.

---

## Project layout

```
gait-imu-analyzer/
├── data/                   demo sessions (Subject1_A1, Subject1_K1)
├── docs/screenshots/       UI screenshots + demo gif
├── src/gait_imu/
│   ├── config.py               tunable signal/calibration parameters
│   ├── theme.py                palette, typography, mpl defaults
│   ├── clinical_reference.py   normative ranges, gait-phase definitions
│   ├── io_utils.py             CSV ingest + column auto-detection
│   ├── signal_utils.py         filters, robust stats, ZUPT integration
│   ├── calibration.py          functional anatomical calibration
│   ├── gait/
│   │   ├── ankle.py            foot + shank → ankle pipeline
│   │   ├── knee.py             shank + thigh → knee pipeline
│   │   └── stride.py           HS pairing, resampling, results
│   ├── export.py               CSV export of session results
│   └── ui/
│       ├── widgets.py          Card / FlipCard / MetricTile / PillTabBar
│       ├── sensor_diagram.py   3-view anatomical leg + IMU pucks
│       ├── plots.py            figure builders (phase shading, normative bands)
│       └── app.py              IMUApp: header + tab orchestration
├── pyproject.toml
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Method notes (short)

- **Functional calibration.** A standing-still window estimates each
  sensor's vertical axis; a flexion window estimates the joint hinge
  axis from the principal rotation between the two sensors. A right-
  handed triad (vertical + hinge → forward) is constructed and
  projected back into each sensor frame to yield the per-sensor
  anatomical-to-sensor rotation.
- **Heel-strike detection.** Smoothed vertical world acceleration is
  gated with the larger of a global threshold (*k* × robust σ over
  the trial) and a local threshold (*k* × rolling σ over
  `LOCAL_WIN_S`).
- **Stride length & walking speed.** Per-stride trapezoidal velocity,
  then linear-drift correction enforcing *v*(*t*<sub>end</sub>) = 0,
  then trapezoidal position. Walking speed is computed as
  mean stride length / mean stride time.

All thresholds live in `src/gait_imu/config.py`.

---

## Recording the demo

`docs/screenshots/demo.gif` is a short walk-through of the app on the
bundled ankle session. To re-record on macOS:

1. `Cmd + Shift + 5` → *Record Selected Portion* → drag a rectangle
   around the app window → *Record*. Drive through
   *Home → Dashboard → All Strides*, then stop.
2. Convert with [`ffmpeg`](https://ffmpeg.org/):

   ```bash
   ffmpeg -i ~/Desktop/demo.mov \
          -vf "fps=12,scale=960:-1:flags=lanczos" \
          -loop 0 docs/screenshots/demo.gif
   ```

3. Commit and push.

---

## Citation

If you use this tool in academic work, please cite the underlying
thesis:

> Jijith, K. (2025). *Validating IMU-Derived Joint Kinematics for
> Pediatric Gait Analysis.* Bachelor of Biomedical Engineering
> (Honours) thesis, School of Biomedical Engineering, The University
> of Sydney.

---

## License

MIT — see [LICENSE](LICENSE).
