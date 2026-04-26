# Gait IMU Analyzer

A lightweight desktop application for measuring how the ankle and
knee move during walking, using only two small wearable sensors.
Developed alongside the Honours thesis *Validating IMU-Derived Joint
Kinematics for Pediatric Gait Analysis* (K. Jijith, University of
Sydney, 2025).

---

## The problem

Clinicians and researchers rely on optical motion capture to study
how people walk. These systems are accurate, but they require a
dedicated laboratory, multiple synchronised cameras, reflective
markers, and trained operators — a setup that is rarely available
outside specialist gait laboratories.

The patients who would benefit most from regular gait assessment
are often the hardest to bring into such a lab: young children,
post-surgical patients, and people with neuromuscular conditions
such as cerebral palsy. For them, frequent monitoring with optical
motion capture is not realistic.

Inertial measurement units (IMUs) — small wireless sensors
combining accelerometers, gyroscopes, and magnetometers — offer
a portable alternative. The open question is whether a small
number of IMUs can recover joint angles accurate enough to
support clinical interpretation.

## The solution

This tool implements a minimal two-IMU pipeline for sagittal-plane
joint kinematics:

- **Ankle** — one sensor on the foot, one on the shank.
- **Knee** — one sensor on the shank, one on the thigh.

A brief functional calibration removes the need for precise sensor
mounting. Heel-strike events are detected from vertical
acceleration, the recording is segmented into individual strides,
and a mean ± standard-deviation joint-angle curve is reported across
the gait cycle alongside spatiotemporal metrics — cadence, stride
time, stride length, and walking speed. Atypical strides can be
excluded interactively, providing a transparent alternative to
ad-hoc data trimming.

Validated against synchronised Vicon optical motion capture during
healthy adult walking trials:

| Joint           | RMSE  | Pearson *r* | Concordance (CCC) |
| --------------- | ----- | ----------- | ----------------- |
| Ankle (DF/PF)   | 2.89° | 0.974       | 0.966             |
| Knee (flexion)  | 2.18° | 0.994       | very high         |

Both joints agree with motion capture to within approximately three
degrees — the threshold typically regarded as clinically
interpretable.

## Installation

Requires **Python 3.9 or newer**, on macOS, Linux, or Windows.

```bash
git clone https://github.com/kalamity0513/gait-imu-analyzer.git
cd gait-imu-analyzer

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
```

> **macOS note.** The interface uses Tkinter, which ships with the
> python.org installer but is not always included with Homebrew
> Python. If `python -m tkinter` raises an error, install the Tk
> bindings with `brew install python-tk`.

To launch the application:

```bash
gait-imu
```

A demonstration ankle session and knee session are bundled under
`data/Subject1_A1/` and `data/Subject1_K1/` respectively, so the
pipeline can be exercised end-to-end without recording new data.

---

## Citation

If this tool supports academic work, please cite the underlying
thesis:

> Jijith, K. (2025). *Validating IMU-Derived Joint Kinematics for
> Pediatric Gait Analysis.* Bachelor of Biomedical Engineering
> (Honours) thesis, School of Biomedical Engineering, The University
> of Sydney.

## License

Released under the MIT License — see [LICENSE](LICENSE).
