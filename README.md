# Gait IMU Analyzer

K. Jijith. *Validating IMU-Derived Joint Kinematics for Pediatric
Gait Analysis.* Honours thesis, School of Biomedical Engineering,
The University of Sydney, 2025.

A desktop tool built for the validation work in the thesis above.
It computes ankle and knee joint angles from a minimal two-IMU
configuration and lets the operator review and curate the resulting
strides.

---

## Problem

Gait dysfunction is a hallmark of numerous neuromuscular and
musculoskeletal conditions, including cerebral palsy, stroke,
muscular dystrophy, spina bifida, and lower-limb trauma. 3D motion
capture has been the gold standard for studying gait, but requires
a specialised lab, expensive equipment, and trained personnel,
making it impractical for frequent use — especially in young
children. Inertial measurement units (IMUs) have emerged as a
promising alternative. The central question is whether a minimal
IMU configuration can reproduce MoCap-quality joint angles with
sufficient accuracy and repeatability for clinical interpretation.

## Solution

An interactive IMU visualiser that streamlines the analysis
workflow by enabling efficient review of raw and processed
signals, stride selection, and automated generation of plots.

The pipeline:

- Reads two synchronised IMU streams — foot + shank for ankle,
  shank + thigh for knee.
- Performs functional sensor-to-segment calibration, so precise
  mounting is not required.
- Detects heel strikes from world-vertical acceleration.
- Segments the recording into strides between consecutive heel
  strikes.
- Reports a mean ± SD joint-angle curve over the gait cycle,
  alongside cadence, stride time, stride length, and walking speed.
- Lets individual strides be kept or dropped from the average.

Validation against Vicon optical motion capture, healthy adult
level walking:

| Joint           | RMSE  | Pearson *r* | CCC   |
| --------------- | ----- | ----------- | ----- |
| Ankle (DF/PF)   | 2.89° | 0.974       | 0.966 |
| Knee (flexion)  | 2.18° | 0.994       | high  |

A two-IMU configuration estimates sagittal ankle and knee angles
within ~3° of MoCap with high concordance across strides.

## Install

Requires Python 3.9 or newer. macOS, Linux, or Windows.

```bash
git clone https://github.com/kalamity0513/gait-imu-analyzer.git
cd gait-imu-analyzer

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
```

macOS Homebrew users: if `python -m tkinter` fails, run
`brew install python-tk`.

Launch:

```bash
gait-imu
```

Demo data is bundled in `data/Subject1_A1/` (ankle) and
`data/Subject1_K1/` (knee).

## License

MIT — see [LICENSE](LICENSE).
