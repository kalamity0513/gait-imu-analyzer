"""Visual theme: clinical, Apple-Health-inspired light design.

A single source of truth so the UI and the embedded plots stay
visually consistent.
"""

import matplotlib.pyplot as plt
from matplotlib import patheffects


# ----------------------------------------------------------------------
#  Palette
# ----------------------------------------------------------------------
#
# Inspired by Apple Health and modern clinical dashboards: cool
# off-white background, pure-white cards, hairline borders, and
# semantic colours used sparingly so data does the talking.

PALETTE = {
    # Surfaces
    "bg":            "#f1f3f7",   # app background (cool gray)
    "bg_alt":        "#e8ebf2",
    "panel":         "#ffffff",
    "panel_alt":     "#f7f8fb",
    "panel_hover":   "#f0f2f6",
    "sidebar":       "#ffffff",
    "sidebar_alt":   "#f7f8fb",

    # Hairlines
    "border":        "#e6e8ee",
    "border_strong": "#d6dae3",
    "border_focus":  "#0071e3",
    "divider":       "#eef0f4",

    # Text
    "text":          "#0c111e",   # near-black for body
    "text_soft":     "#3c4253",
    "muted":         "#6b7280",
    "muted_strong":  "#4b5563",
    "subtle":        "#9aa3b2",

    # Accents
    "accent":        "#0071e3",   # Apple blue
    "accent_dark":   "#0058b8",
    "accent_soft":   "#e1efff",
    "accent_tint":   "#f1f7ff",

    # Semantic (Apple Health-style)
    "ok":            "#34c759",
    "ok_dark":       "#1f9d3f",
    "ok_soft":       "#e3f8e8",
    "warn":          "#ff9500",
    "warn_dark":     "#cc7700",
    "warn_soft":     "#fff1de",
    "danger":        "#ff3b30",
    "danger_dark":   "#c4312a",
    "danger_soft":   "#ffe5e3",
    "info":          "#0a84ff",
    "info_soft":     "#e0eeff",

    # Sidebar text (now on white)
    "sidebar_text":  "#0c111e",
    "sidebar_muted": "#6b7280",
    "sidebar_hover": "#f1f7ff",
}

# Plot-specific colour assignments
PLOT_COLORS = {
    "mean":         "#0071e3",
    "mean_dark":    "#0058b8",
    "fill":         "#9ec5fe",
    "fill_alt":     "#cfe1ff",
    "accel":        "#1f2937",
    "accel_soft":   "#cbd5e1",
    "hs_raw":       "#9aa3b2",
    "hs_drop":      "#ff3b30",
    "hs_keep":      "#34c759",
    "stride":       "#0071e3",
    "stride_off":   "#c5cad4",
    "grid":         "#eef0f4",
    "axis":         "#cbd1dc",

    # Gait-phase fills (very soft, used as background bands)
    "stance_fill":  "#e1efff",   # tinted blue
    "swing_fill":   "#fff1de",   # tinted amber
    "norm_band":    "#e8f0ff",   # normative reference band

    # Multi-stride traces
    "stride_trace": "#a4cafe",
    "stride_dim":   "#dde3ee",
}


# ----------------------------------------------------------------------
#  Typography
# ----------------------------------------------------------------------
#
# A single fallback chain so the same fonts apply to ttk widgets
# *and* matplotlib text. SF Pro / Helvetica Neue come first; system
# fallbacks ensure cross-platform rendering.

# SF Pro is the system UI font on macOS, but matplotlib's font finder
# doesn't always resolve it. Helvetica Neue / Helvetica are the visual
# match Apple uses as fallbacks, and DejaVu keeps Linux/Windows happy.
FONT_FAMILY = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


class FONT:
    """Ready-made (family, size, weight) tuples for ttk widgets."""
    DISPLAY     = ("Helvetica Neue", 22, "bold")
    HEADER      = ("Helvetica Neue", 17, "bold")
    SUBHEADER   = ("Helvetica Neue", 11, "normal")
    SECTION     = ("Helvetica Neue", 9,  "bold")
    BODY        = ("Helvetica Neue", 11, "normal")
    BODY_BOLD   = ("Helvetica Neue", 11, "bold")
    SMALL       = ("Helvetica Neue", 9,  "normal")
    SMALL_BOLD  = ("Helvetica Neue", 9,  "bold")
    METRIC      = ("Helvetica Neue", 26, "bold")
    METRIC_UNIT = ("Helvetica Neue", 13, "normal")
    PILL        = ("Helvetica Neue", 9,  "bold")
    MONO        = ("Menlo", 11, "normal")


# ----------------------------------------------------------------------
#  Matplotlib defaults
# ----------------------------------------------------------------------

def style_mpl() -> None:
    """Apply matplotlib rcParams that match the app's clinical theme."""
    plt.rcParams.update({
        "figure.facecolor":   PALETTE["panel"],
        "axes.facecolor":     PALETTE["panel"],
        "savefig.facecolor":  PALETTE["panel"],

        "axes.edgecolor":     PLOT_COLORS["axis"],
        "axes.linewidth":     0.9,
        "axes.labelcolor":    PALETTE["text_soft"],
        "axes.labelpad":      6,
        "axes.titlecolor":    PALETTE["text"],
        "axes.titleweight":   "semibold",
        "axes.titlesize":     12.5,
        "axes.titlepad":      14,
        "axes.labelsize":     10.5,
        "axes.labelweight":   "medium",
        "axes.spines.top":    False,
        "axes.spines.right":  False,

        "text.color":         PALETTE["text"],
        "xtick.color":        PALETTE["muted"],
        "ytick.color":        PALETTE["muted"],
        "xtick.labelsize":    9.5,
        "ytick.labelsize":    9.5,
        "xtick.major.size":   3.0,
        "ytick.major.size":   3.0,
        "xtick.major.width":  0.7,
        "ytick.major.width":  0.7,
        "xtick.major.pad":    4,
        "ytick.major.pad":    4,

        "grid.color":         PLOT_COLORS["grid"],
        "axes.grid":          True,
        "axes.grid.axis":     "y",
        "grid.linestyle":     "-",
        "grid.linewidth":     0.7,
        "grid.alpha":         1.0,

        "legend.frameon":     False,
        "legend.fontsize":    9.5,
        "legend.handlelength": 1.6,
        "legend.borderaxespad": 0.4,

        "lines.linewidth":    1.6,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",

        "font.family":        FONT_FAMILY,
        "font.size":          10.5,

        "figure.dpi":         110,
    })


def style_axes(ax) -> None:
    """Apply per-axes refinements that complement :func:`style_mpl`."""
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(PLOT_COLORS["axis"])
    ax.spines["bottom"].set_color(PLOT_COLORS["axis"])
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(direction="out", length=3, width=0.7)
    ax.set_axisbelow(True)


def soft_glow(color, lw=4, alpha=0.18):
    """Return a path-effect that draws a soft halo behind a line."""
    return [patheffects.Stroke(linewidth=lw, foreground=color, alpha=alpha),
            patheffects.Normal()]
