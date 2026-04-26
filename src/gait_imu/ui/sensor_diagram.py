"""3D anatomical leg + per-IMU axis diagrams (locked / non-interactive).

Two public builders:

* :func:`build_imu_axes_diagram` — a small 3D model of one IMU sensor with
  its X / Y / Z axes annotated. Used in the Home tab Step-1 panels.

* :func:`build_sensor_diagram` — the larger anatomical leg with the
  sensor positions marked on it. Used in the Home tab Step-1 panel.

Coordinate system for the leg uses matplotlib's z-up:

    +x  anterior (forward)
    +y  lateral  (toward camera)
    +z  superior (up)
"""

from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from ..theme import PALETTE


# ----------------------------------------------------------------------
#  Parametric primitives (anatomical leg)
# ----------------------------------------------------------------------

def _anatomical_segment(
    z_arr: np.ndarray,
    r_along_z: np.ndarray,
    *,
    x_offset: Optional[np.ndarray] = None,
    x_scale: float = 1.10,
    y_scale: float = 0.95,
    n_phi: int = 56,
):
    """Limb segment with a slightly elliptical, optionally offset cross-section."""
    phi = np.linspace(0.0, 2 * np.pi, n_phi)
    Z, P = np.meshgrid(z_arr, phi, indexing="ij")
    R = r_along_z[:, None]
    X = R * np.cos(P) * x_scale
    Y = R * np.sin(P) * y_scale
    if x_offset is not None:
        X = X + x_offset[:, None]
    return X, Y, Z


def _sphere(cx: float, cy: float, cz: float, r: float, n: int = 28):
    u = np.linspace(0.0, 2 * np.pi, n)
    v = np.linspace(0.0, np.pi, n)
    X = cx + r * np.outer(np.cos(u), np.sin(v))
    Y = cy + r * np.outer(np.sin(u), np.sin(v))
    Z = cz + r * np.outer(np.ones_like(u), np.cos(v))
    return X, Y, Z


def _foot_shape(cx: float, cy: float, cz: float, *,
                length: float = 1.55, width: float = 0.36,
                height: float = 0.20, n: int = 44):
    """Anatomical foot: longer, flatter sole, tapered toe, slight heel rise.

    Constructed by deforming an ellipsoid so that:

    * The toe end (``+x``) tapers in width and height.
    * The heel end (``-x``) keeps width but narrows slightly.
    * The bottom half (``z < 0``) is squashed → a near-flat sole.
    * The heel back is lifted a touch off the "ground".
    """
    u = np.linspace(0.0, 2 * np.pi, n)
    v = np.linspace(0.0, np.pi, n)
    UU, VV = np.meshgrid(u, v, indexing="ij")

    X0 = (length / 2) * np.cos(UU) * np.sin(VV)
    Y0 = (width  / 2) * np.sin(UU) * np.sin(VV)
    Z0 = (height / 2) * np.cos(VV)

    x_norm = X0 / (length / 2)   # -1 at heel, +1 at toe

    # Toe taper — forefoot narrows in both width and height.
    toe = np.clip(x_norm, 0.0, 1.0)
    toe_taper = 1.0 - 0.55 * (toe ** 2)
    Y0 = Y0 * toe_taper
    Z0 = Z0 * toe_taper

    # Heel — tiny narrowing so the heel reads as round but not blocky.
    heel = np.clip(-x_norm, 0.0, 1.0)
    heel_taper = 1.0 - 0.10 * (heel ** 1.5)
    Y0 = Y0 * heel_taper
    Z0 = Z0 * heel_taper

    # Flatten the sole — squash the bottom half (z < 0) by a large factor.
    Z0 = np.where(Z0 < 0, Z0 * 0.25, Z0)

    # Slight heel lift off the ground (real foot's heel is usually a bit raised
    # vs the metatarsal heads when relaxed).
    Z0 = Z0 + 0.04 * heel

    return X0 + cx, Y0 + cy, Z0 + cz


def _thigh_radius_profile(z: np.ndarray) -> np.ndarray:
    """Hip → knee. Quadriceps bulge in mid-thigh."""
    norm = (z - 1.55) / (3.20 - 1.55)
    base = 0.20 + 0.12 * norm
    quad = 0.07 * np.exp(-((norm - 0.55) ** 2) / (2 * 0.20 ** 2))
    return base + quad


def _shank_radius_profile(z: np.ndarray) -> np.ndarray:
    """Ankle → knee. Calf bulge in upper third."""
    norm = (z - 0.05) / (1.50 - 0.05)
    base = 0.10 + 0.10 * norm
    calf = 0.07 * np.exp(-((norm - 0.62) ** 2) / (2 * 0.18 ** 2))
    return base + calf


def _shank_offset_profile(z: np.ndarray) -> np.ndarray:
    norm = (z - 0.05) / (1.50 - 0.05)
    return -0.045 * np.exp(-((norm - 0.62) ** 2) / (2 * 0.18 ** 2))


# ----------------------------------------------------------------------
#  Anatomical leg drawing (smooth solid surface, no wireframe)
# ----------------------------------------------------------------------

LIMB_FILL  = "#7fb3d6"   # lighter slate-cyan — readable on dark panels
LIMB_EDGE  = "#22d3ee"


def _draw_limb(ax, X, Y, Z, *, alpha: float = 0.98):
    ax.plot_surface(
        X, Y, Z,
        color=LIMB_FILL,
        edgecolor=(1.0, 1.0, 1.0, 0.10),       # subtle white edge wash
        linewidth=0.25,
        alpha=alpha,
        antialiased=True,
        shade=True,
        rcount=22, ccount=44,
    )


def _draw_joint(ax, cx, cy, cz, *, r: float = 0.20):
    X, Y, Z = _sphere(cx, cy, cz, r, n=26)
    ax.plot_surface(X, Y, Z,
                    color=PALETTE["accent_glow"],
                    edgecolor=(0, 0, 0, 0),
                    linewidth=0,
                    alpha=0.95, shade=True,
                    rcount=18, ccount=18)


def _draw_sensor(ax, cx, cy, cz, *, color: str, label: str,
                 label_xyz, fontsize: float = 11):
    """Draw the sensor puck and a single bold label connected by a leader."""
    Xh, Yh, Zh = _sphere(cx, cy, cz, 0.16, n=18)
    ax.plot_surface(Xh, Yh, Zh, color=color, alpha=0.18,
                    linewidth=0, shade=False)
    Xp, Yp, Zp = _sphere(cx, cy, cz, 0.085, n=20)
    ax.plot_surface(Xp, Yp, Zp, color=color, alpha=1.0,
                    edgecolor="white", linewidth=0.6, shade=True)

    lx, ly, lz = label_xyz
    ax.plot([cx, lx], [cy, ly], [cz, lz],
            color=color, linewidth=1.2, alpha=0.65)
    ax.text(lx, ly, lz, label, color=color,
            fontsize=fontsize, fontweight="bold",
            ha="left", va="center")


# ----------------------------------------------------------------------
#  Public — anatomical leg
# ----------------------------------------------------------------------

DIAGRAM_BG = "#1a2540"   # slightly lighter than the card so the leg stands out


def _build_leg_axes(ax, sensors, *, view, show_labels: bool):
    """Draw the full leg + sensors into ``ax`` from the given camera view.

    ``sensors`` is a list of dicts with keys ``cx, cy, cz, color, label,
    label_xyz``. Labels are only drawn on the ``3D`` view to avoid
    overlapping the silhouette in the orthographic panels.
    """
    ax.set_facecolor(DIAGRAM_BG)
    ax.set_axis_off()
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor((0, 0, 0, 0))

    # Thigh
    z_thigh = np.linspace(1.55, 3.20, 36)
    X, Y, Z = _anatomical_segment(z_thigh, _thigh_radius_profile(z_thigh),
                                    x_scale=1.15, y_scale=0.95)
    _draw_limb(ax, X, Y, Z)

    _draw_joint(ax, 0.0, 0.0, 1.52, r=0.22)

    z_shank = np.linspace(0.05, 1.50, 32)
    X, Y, Z = _anatomical_segment(
        z_shank,
        _shank_radius_profile(z_shank),
        x_offset=_shank_offset_profile(z_shank),
        x_scale=1.05, y_scale=0.92,
    )
    _draw_limb(ax, X, Y, Z)

    _draw_joint(ax, 0.05, 0.0, 0.02, r=0.14)

    Xf, Yf, Zf = _foot_shape(cx=0.55, cy=0.0, cz=-0.18,
                              length=1.30, width=0.36, height=0.22)
    _draw_limb(ax, Xf, Yf, Zf)

    for s in sensors:
        if show_labels:
            _draw_sensor(ax, cx=s["cx"], cy=s["cy"], cz=s["cz"],
                         color=s["color"], label=s["label"],
                         label_xyz=s["label_xyz"], fontsize=10.5)
        else:
            # Orthographic panels: just the puck, no leader / label
            Xh, Yh, Zh = _sphere(s["cx"], s["cy"], s["cz"], 0.16, n=18)
            ax.plot_surface(Xh, Yh, Zh, color=s["color"], alpha=0.20,
                            linewidth=0, shade=False)
            Xp, Yp, Zp = _sphere(s["cx"], s["cy"], s["cz"], 0.10, n=20)
            ax.plot_surface(Xp, Yp, Zp, color=s["color"], alpha=1.0,
                            edgecolor="white", linewidth=0.7, shade=True)

    ax.view_init(**view)
    ax.set_xlim(-0.8, 2.0)
    ax.set_ylim(-0.8, 1.4)
    ax.set_zlim(-0.5, 3.5)
    ax.set_box_aspect((2.3, 1.9, 4.0))

    ax.disable_mouse_rotation()
    ax.mouse_init = lambda *args, **kw: None


def build_sensor_diagram(mode: str = "ankle", *, figsize=(11.4, 4.8)):
    """Three-panel anatomical diagram showing IMU placement.

    Layout: ``FRONT``  ·  ``SIDE``  ·  ``3D PERSPECTIVE``.
    Sensor labels appear only on the 3D panel; the two orthographic
    panels show the puck position cleanly without leader lines.
    """
    fig = plt.figure(figsize=figsize, facecolor=DIAGRAM_BG)
    fig.patch.set_facecolor(DIAGRAM_BG)

    if mode == "ankle":
        sensors = [
            dict(cx=0.55, cy=0.10, cz=-0.05,
                 color=PALETTE["accent"],
                 label="Foot IMU  ·  Dorsum",
                 label_xyz=(1.65, 0.60, 0.10)),
            dict(cx=0.18, cy=0.06, cz=0.85,
                 color=PALETTE["accent2"],
                 label="Shank IMU  ·  Antero-medial mid-shank",
                 label_xyz=(1.10, 0.95, 0.95)),
        ]
    else:
        sensors = [
            dict(cx=0.18, cy=0.06, cz=0.85,
                 color=PALETTE["accent"],
                 label="Shank IMU  ·  Antero-medial mid-shank",
                 label_xyz=(1.10, 0.95, 0.85)),
            dict(cx=0.27, cy=0.10, cz=2.40,
                 color=PALETTE["accent2"],
                 label="Thigh IMU  ·  Antero-lateral mid-thigh",
                 label_xyz=(1.20, 0.95, 2.50)),
        ]

    views = [
        ("FRONT",         dict(elev=0,  azim=-90), False),
        ("SIDE",          dict(elev=0,  azim=0),   False),
        ("3D PERSPECTIVE", dict(elev=8, azim=-58), True),
    ]

    for i, (title, view, show_labels) in enumerate(views, start=1):
        ax = fig.add_subplot(1, 3, i, projection="3d")
        _build_leg_axes(ax, sensors, view=view, show_labels=show_labels)
        ax.text2D(0.5, 0.97, title, transform=ax.transAxes,
                  ha="center", va="top",
                  color=PALETTE["text"], fontsize=11, fontweight="bold")

    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0,
                        wspace=0.0)
    return fig


# ----------------------------------------------------------------------
#  Public — IMU + axis triad diagram
# ----------------------------------------------------------------------

# Three colour-coded axis vectors (R / G / B-cyan) — standard convention
AXIS_COLOURS = {
    "X": "#ff6b5b",   # warm coral
    "Y": "#86e07e",   # mint
    "Z": "#22d3ee",   # cyan
}


def _box_faces(L: float, W: float, H: float):
    """Return the six rectangular faces of an L×W×H box centred at origin."""
    a, b, c = L / 2, W / 2, H / 2
    return [
        # bottom (-z)  — winding outward (CCW from below)
        [(-a, -b, -c), (a, -b, -c), (a, b, -c), (-a, b, -c)],
        # top (+z)
        [(-a, -b, +c), (a, -b, +c), (a, b, +c), (-a, b, +c)],
        # front (-y)
        [(-a, -b, -c), (a, -b, -c), (a, -b, +c), (-a, -b, +c)],
        # back (+y)
        [(-a, +b, -c), (a, +b, -c), (a, +b, +c), (-a, +b, +c)],
        # left (-x)
        [(-a, -b, -c), (-a, +b, -c), (-a, +b, +c), (-a, -b, +c)],
        # right (+x)
        [(+a, -b, -c), (+a, +b, -c), (+a, +b, +c), (+a, -b, +c)],
    ]


def _draw_axis(ax, axis: str, length: float = 1.45, *, line_w: float = 3.2):
    """Draw one coloured axis arrow with a bold X / Y / Z label at the tip."""
    colour = AXIS_COLOURS[axis]
    if axis == "X":
        ax.plot([0, length], [0, 0], [0, 0],
                color=colour, linewidth=line_w, solid_capstyle="round")
        ax.text(length * 1.10, 0, 0, "X", color=colour,
                fontsize=18, fontweight="bold", ha="left", va="center")
    elif axis == "Y":
        ax.plot([0, 0], [0, length], [0, 0],
                color=colour, linewidth=line_w, solid_capstyle="round")
        ax.text(0, length * 1.10, 0, "Y", color=colour,
                fontsize=18, fontweight="bold", ha="center", va="bottom")
    else:  # Z
        ax.plot([0, 0], [0, 0], [0, length],
                color=colour, linewidth=line_w, solid_capstyle="round")
        ax.text(0, 0, length * 1.10, "Z", color=colour,
                fontsize=18, fontweight="bold", ha="center", va="bottom")


def build_imu_axes_diagram(
    title: str,
    mount_label: str,
    *,
    accent: str,
    figsize=(2.8, 2.6),
):
    """Return a 3D figure showing a single IMU body + its X / Y / Z axes.

    The figure is intentionally compact — the per-axis anatomical
    mapping is rendered as a Tk legend by the caller, beneath the
    figure. That keeps the figure visually clean.
    """
    fig = plt.figure(figsize=figsize, facecolor=PALETTE["panel"])
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor(PALETTE["panel"])
    fig.patch.set_facecolor(PALETTE["panel"])
    ax.set_axis_off()
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor((0, 0, 0, 0))

    # IMU body — flat rectangular box with a small surface marker on top
    L, W, H = 1.0, 0.7, 0.22
    box = Poly3DCollection(
        _box_faces(L, W, H),
        facecolors=[PALETTE["panel_alt"]] * 6,
        edgecolors=accent,
        linewidths=1.2,
        alpha=0.92,
    )
    ax.add_collection3d(box)
    marker_top = Poly3DCollection(
        [[(-0.18, -0.10, H / 2 + 0.001),
          (+0.18, -0.10, H / 2 + 0.001),
          (+0.18, +0.10, H / 2 + 0.001),
          (-0.18, +0.10, H / 2 + 0.001)]],
        facecolors=[accent],
        edgecolors=accent,
        alpha=0.85,
    )
    ax.add_collection3d(marker_top)

    _draw_axis(ax, "X")
    _draw_axis(ax, "Y")
    _draw_axis(ax, "Z")

    ax.text2D(0.5, 0.97, title, transform=ax.transAxes,
              ha="center", va="top",
              color=accent, fontsize=12, fontweight="bold")
    ax.text2D(0.5, 0.04, mount_label, transform=ax.transAxes,
              ha="center", va="bottom",
              color=PALETTE["muted"], fontsize=9)

    ax.view_init(elev=20, azim=-55)
    ax.set_xlim(-0.7, 1.8)
    ax.set_ylim(-0.7, 1.8)
    ax.set_zlim(-0.5, 1.8)
    ax.set_box_aspect((1, 1, 1))

    ax.disable_mouse_rotation()
    ax.mouse_init = lambda *args, **kw: None

    fig.tight_layout()
    return fig
