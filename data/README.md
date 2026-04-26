# Sample IMU sessions

Two example walking sessions ship with the project so you can try the
app immediately without your own hardware.

| Folder         | Joint | Sensors                                  | Use it with             |
| -------------- | ----- | ---------------------------------------- | ----------------------- |
| `Subject1_A1/` | Ankle | `Subject1_A1_Foot.csv`, `..._Shank.csv`  | **Pair = Ankle**        |
| `Subject1_K1/` | Knee  | `Subject1_K1_Shank.csv`, `..._Thigh.csv` | **Pair = Knee**         |

Each CSV contains a timestamp column, a quaternion (`qx, qy, qz, qr`) and
optionally a 3-axis accelerometer in m/s². Column names are auto-detected
so vendor exports under different conventions (`Quat_X`, `acc_x_mss`, …)
work the same way.

The `*_Regions/` sub-folders are auxiliary annotations exported by the
capture software and are **not** required by the app.
