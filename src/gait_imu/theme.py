"""Visual theme: dark futuristic medical UI.

Deep ink-navy background, electric cyan primary, soft purple secondary,
luminous accents on data. The palette is consistent across ttk widgets,
custom Canvas widgets, and embedded matplotlib figures.
"""

import matplotlib.pyplot as plt
from matplotlib import patheffects


# ----------------------------------------------------------------------
#  Palette — dark futuristic medical
# ----------------------------------------------------------------------

PALETTE = {
    # Surfaces
    "bg":            "#070b18",   # deep ink (almost black)
    "bg_alt":        "#0d1424",
    "panel":         "#10172a",   # card surface
    "panel_alt":     "#161e35",
    "panel_hover":   "#1c2643",   # hover lift
    "panel_active":  "#22305a",

    # Hairlines
    "border":        "#22304f",
    "border_strong": "#324568",
    "divider":       "#1a2540",
    "glow":          "#22d3ee",   # used for active outlines

    # Text
    "text":          "#e7eef8",
    "text_soft":     "#cfd9ea",
    "muted":         "#8693ad",
    "muted_strong":  "#a9b6cf",
    "subtle":        "#566385",

    # Accents — electric cyan primary
    "accent":        "#22d3ee",   # cyan
    "accent_dark":   "#0e9bb6",
    "accent_glow":   "#67e8f9",   # bright glow tone
    "accent_soft":   "#0b2a36",   # tinted dark fill
    "accent_tint":   "#0a1f2a",
    # Secondary — soft violet (used for active stride / contrast)
    "accent2":       "#a78bfa",
    "accent2_dark":  "#7c3aed",
    "accent2_soft":  "#1a1538",

    # Semantic — luminous on dark
    "ok":            "#34d399",
    "ok_soft":       "#0d2820",
    "warn":          "#fbbf24",
    "warn_soft":     "#241d09",
    "danger":        "#f87171",
    "danger_soft":   "#27110f",
    "info":          "#60a5fa",
    "info_soft":     "#0f1d36",
}

PLOT_COLORS = {
    "mean":         "#22d3ee",
    "mean_dark":    "#0e9bb6",
    "fill":         "#0d3a4d",       # cyan-tinted dark
    "fill_alt":     "#102a3a",
    "accel":        "#cfd9ea",
    "accel_soft":   "#324568",
    "hs_raw":       "#566385",
    "hs_drop":      "#f87171",
    "hs_keep":      "#34d399",
    "stride":       "#22d3ee",
    "stride_alt":   "#a78bfa",
    "stride_off":   "#324568",
    "grid":         "#1c2643",
    "axis":         "#324568",

    # Gait-phase fills (subtle on dark)
    "stance_fill":  "#0c1c34",
    "swing_fill":   "#1a1232",
    # Healthy-adult reference band — soft lilac
    "norm_band":    "#b19cd9",
    "norm_band_line": "#d4b6e8",

    # Multi-stride traces
    "stride_trace": "#3a6580",
    "stride_dim":   "#22304f",
}


# ----------------------------------------------------------------------
#  Typography
# ----------------------------------------------------------------------

FONT_FAMILY = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
MONO_FAMILY = ["JetBrains Mono", "SF Mono", "Menlo", "Monaco", "Courier"]


class FONT:
    """Ready-made (family, size, weight) tuples for ttk widgets."""
    DISPLAY     = ("Helvetica Neue", 26, "bold")
    HEADER      = ("Helvetica Neue", 18, "bold")
    SUBHEADER   = ("Helvetica Neue", 12, "normal")
    SECTION     = ("Helvetica Neue", 10, "bold")        # uppercase eyebrow text
    BODY        = ("Helvetica Neue", 12, "normal")
    BODY_BOLD   = ("Helvetica Neue", 12, "bold")
    SMALL       = ("Helvetica Neue", 10, "normal")
    SMALL_BOLD  = ("Helvetica Neue", 10, "bold")
    METRIC      = ("Menlo", 30, "bold")                  # mono for futuristic data
    METRIC_UNIT = ("Menlo", 13, "normal")
    PILL        = ("Helvetica Neue", 10, "bold")
    MONO        = ("Menlo", 12, "normal")
    MONO_BOLD   = ("Menlo", 12, "bold")
    HERO        = ("Helvetica Neue", 28, "bold")
    TAB         = ("Helvetica Neue", 11, "bold")


# ----------------------------------------------------------------------
#  Matplotlib defaults — dark canvas, luminous strokes
# ----------------------------------------------------------------------

def style_mpl() -> None:
    plt.rcParams.update({
        "figure.facecolor":   PALETTE["panel"],
        "axes.facecolor":     PALETTE["panel"],
        "savefig.facecolor":  PALETTE["panel"],

        "axes.edgecolor":     PLOT_COLORS["axis"],
        "axes.linewidth":     1.0,
        "axes.labelcolor":    PALETTE["text_soft"],
        "axes.labelpad":      6,
        "axes.titlecolor":    PALETTE["text"],
        "axes.titleweight":   "semibold",
        "axes.titlesize":     13,
        "axes.titlepad":      14,
        "axes.labelsize":     11,
        "axes.labelweight":   "medium",
        "axes.spines.top":    False,
        "axes.spines.right":  False,

        "text.color":         PALETTE["text"],
        "xtick.color":        PALETTE["muted"],
        "ytick.color":        PALETTE["muted"],
        "xtick.labelsize":    10,
        "ytick.labelsize":    10,
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
        "legend.fontsize":    10,
        "legend.handlelength": 1.6,
        "legend.borderaxespad": 0.4,
        "legend.labelcolor":  PALETTE["text_soft"],

        "lines.linewidth":    1.7,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",

        "font.family":        FONT_FAMILY,
        "font.size":          11,

        "figure.dpi":         110,
    })


def style_axes(ax) -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(PLOT_COLORS["axis"])
    ax.spines["bottom"].set_color(PLOT_COLORS["axis"])
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(direction="out", length=3, width=0.7)
    ax.set_axisbelow(True)


def soft_glow(color, lw=4, alpha=0.30):
    """Outer-glow path effect — looks great on dark."""
    return [patheffects.Stroke(linewidth=lw, foreground=color, alpha=alpha),
            patheffects.Normal()]
