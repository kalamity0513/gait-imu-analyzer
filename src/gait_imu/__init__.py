"""Clinical IMU gait analysis toolkit.

Public surface:
    - `gait_imu.config`        : tunable signal/calibration parameters
    - `gait_imu.io_utils`      : CSV ingestion and column auto-detection
    - `gait_imu.signal_utils`  : low-level numerical helpers
    - `gait_imu.calibration`   : functional anatomical calibration
    - `gait_imu.gait`          : ankle / knee pipelines, stride helpers, metrics
    - `gait_imu.export`        : CSV export of session results
    - `gait_imu.ui`            : Tk-based clinical visualizer
"""

__version__ = "0.1.0"
