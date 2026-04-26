# Gait IMU Analyzer

A desktop tool for sagittal ankle and knee gait analysis from two
IMUs. Built for the Honours thesis *Validating IMU-Derived Joint
Kinematics for Pediatric Gait Analysis* (K. Jijith, University of
Sydney, 2025).

---

## Problem

3D motion capture is the clinical gold standard for measuring joint
kinematics, but it needs a dedicated lab, multiple cameras, trained
operators, and a cooperative subject. That makes it impractical for
routine assessment — especially in young children and patients
recovering from injury or surgery, who are exactly the populations
that benefit most from regular gait monitoring.

## Solution

This tool derives sagittal ankle and knee kinematics from a minimal
two-IMU setup (foot + shank for ankle, shank + thigh for knee). It:

- performs **functional sensor-to-segment calibration**, so precise
  IMU mounting is not critical;
- detects **heel strikes** from world-vertical foot/shank acceleration;
- segments and normalises **strides** to 0–100 % gait;
- reports a **mean ± SD ensemble curve** plus spatiotemporal metrics
  (cadence, stride time, stride length, walking speed);
- lets the operator **keep or drop individual strides** as a
  reproducible alternative to ad-hoc cropping.

Validated against Vicon optical motion capture during healthy adult
level walking:

| Joint           | RMSE  | Pearson *r* | CCC   |
| --------------- | ----- | ----------- | ----- |
| Ankle (DF/PF)   | 2.89° | 0.974       | 0.966 |
| Knee (flexion)  | 2.18° | 0.994       | high  |

## Install

Requires **Python ≥ 3.9** (macOS, Linux, Windows).

```bash
git clone https://github.com/kalamity0513/gait-imu-analyzer.git
cd gait-imu-analyzer

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
```

> **macOS note.** If `python -m tkinter` fails, install Tk:
> `brew install python-tk`.

Launch:

```bash
gait-imu
```

Demo data is bundled in `data/Subject1_A1/` (ankle) and
`data/Subject1_K1/` (knee).

---

## Citation

> Jijith, K. (2025). *Validating IMU-Derived Joint Kinematics for
> Pediatric Gait Analysis.* Bachelor of Biomedical Engineering
> (Honours) thesis, School of Biomedical Engineering, The University
> of Sydney.

## License

MIT — see [LICENSE](LICENSE).
