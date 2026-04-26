"""Console entry point: ``python -m gait_imu`` or ``gait-imu``."""

from __future__ import annotations

import tkinter as tk

from .ui import IMUApp


def main() -> None:
    root = tk.Tk()
    IMUApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
