"""Reusable styled widgets: ttk style installer plus rounded clinical cards.

Tkinter doesn't natively give us rounded corners or shadows, so the
:class:`RoundedCard` widget draws its background on a :class:`tk.Canvas`
and embeds a real ``tk.Frame`` inside via ``create_window``. This lets
us put any ttk content on top while still getting the soft-rounded
look of a modern clinical UI.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..theme import FONT, PALETTE


# ----------------------------------------------------------------------
#  Style installer
# ----------------------------------------------------------------------

def install_styles() -> None:
    """Install the clinical ttk theme. Call once after creating the root."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # ------- base -------
    style.configure(".", background=PALETTE["panel"], foreground=PALETTE["text"],
                    font=FONT.BODY)

    # ------- frames -------
    for name, bg in [
        ("App.TFrame",       PALETTE["bg"]),
        ("Panel.TFrame",     PALETTE["panel"]),
        ("PanelAlt.TFrame",  PALETTE["panel_alt"]),
        ("Sidebar.TFrame",   PALETTE["sidebar"]),
        ("Card.TFrame",      PALETTE["panel"]),
        ("Status.TFrame",    PALETTE["panel_alt"]),
    ]:
        style.configure(name, background=bg, borderwidth=0)

    # ------- labels -------
    style.configure("TLabel",         background=PALETTE["panel"], foreground=PALETTE["text"])
    style.configure("App.TLabel",     background=PALETTE["bg"],    foreground=PALETTE["text"])
    style.configure("Muted.TLabel",   background=PALETTE["panel"], foreground=PALETTE["muted"])
    style.configure("AppMuted.TLabel",background=PALETTE["bg"],    foreground=PALETTE["muted"])
    style.configure("Sidebar.TLabel", background=PALETTE["sidebar"], foreground=PALETTE["sidebar_text"])
    style.configure("SidebarMuted.TLabel", background=PALETTE["sidebar"],
                    foreground=PALETTE["sidebar_muted"], font=FONT.SMALL)
    style.configure("SidebarHeader.TLabel", background=PALETTE["sidebar"],
                    foreground=PALETTE["muted"], font=FONT.SECTION)

    style.configure("Header.TLabel",   background=PALETTE["panel"],
                    foreground=PALETTE["text"], font=FONT.HEADER)
    style.configure("AppHeader.TLabel",background=PALETTE["bg"],
                    foreground=PALETTE["text"], font=FONT.HEADER)
    style.configure("Subheader.TLabel",background=PALETTE["panel"],
                    foreground=PALETTE["muted"], font=FONT.SUBHEADER)
    style.configure("AppSubheader.TLabel", background=PALETTE["bg"],
                    foreground=PALETTE["muted"], font=FONT.SUBHEADER)

    style.configure("CardTitle.TLabel",   background=PALETTE["panel"],
                    foreground=PALETTE["muted"], font=FONT.SECTION)
    style.configure("CardValue.TLabel",   background=PALETTE["panel"],
                    foreground=PALETTE["text"],  font=FONT.METRIC)
    style.configure("CardUnit.TLabel",    background=PALETTE["panel"],
                    foreground=PALETTE["muted_strong"], font=FONT.METRIC_UNIT)
    style.configure("CardCaption.TLabel", background=PALETTE["panel"],
                    foreground=PALETTE["muted"], font=FONT.SMALL)

    style.configure("Status.TLabel", background=PALETTE["panel_alt"],
                    foreground=PALETTE["muted_strong"], font=FONT.SMALL)

    # ------- notebook -------
    style.configure("TNotebook", background=PALETTE["bg"], borderwidth=0,
                    tabmargins=(0, 4, 0, 0))
    style.configure("TNotebook.Tab",
                    padding=(18, 9),
                    background=PALETTE["bg"],
                    foreground=PALETTE["muted"],
                    borderwidth=0,
                    font=FONT.BODY_BOLD)
    style.map("TNotebook.Tab",
              background=[("selected", PALETTE["panel"]), ("active", PALETTE["panel_hover"])],
              foreground=[("selected", PALETTE["text"])])

    # ------- buttons -------
    style.configure("TButton",
                    padding=(11, 7),
                    background=PALETTE["panel"],
                    foreground=PALETTE["text"],
                    bordercolor=PALETTE["border"],
                    relief="flat",
                    focusthickness=0,
                    font=FONT.BODY)
    style.map("TButton",
              background=[("active", PALETTE["panel_hover"])],
              bordercolor=[("active", PALETTE["border_strong"])])

    style.configure("Accent.TButton",
                    background=PALETTE["accent"],
                    foreground="#ffffff",
                    padding=(14, 8),
                    relief="flat",
                    borderwidth=0,
                    focusthickness=0,
                    font=FONT.BODY_BOLD)
    style.map("Accent.TButton",
              background=[("active", PALETTE["accent_dark"])])

    style.configure("Sidebar.TButton",
                    background=PALETTE["sidebar"],
                    foreground=PALETTE["text"],
                    bordercolor=PALETTE["border"],
                    padding=(11, 8),
                    relief="flat",
                    borderwidth=0,
                    focusthickness=0,
                    font=FONT.BODY)
    style.map("Sidebar.TButton",
              background=[("active", PALETTE["sidebar_hover"])])

    style.configure("SidebarAccent.TButton",
                    background=PALETTE["accent"],
                    foreground="#ffffff",
                    padding=(14, 10),
                    relief="flat",
                    borderwidth=0,
                    focusthickness=0,
                    font=FONT.BODY_BOLD)
    style.map("SidebarAccent.TButton", background=[("active", PALETTE["accent_dark"])])

    # ------- inputs -------
    style.configure("TEntry",
                    fieldbackground="#ffffff",
                    bordercolor=PALETTE["border"],
                    lightcolor=PALETTE["border"],
                    darkcolor=PALETTE["border"],
                    insertcolor=PALETTE["text"],
                    padding=6)
    style.configure("Sidebar.TEntry",
                    fieldbackground=PALETTE["sidebar_alt"],
                    bordercolor=PALETTE["border"],
                    lightcolor=PALETTE["border"],
                    darkcolor=PALETTE["border"],
                    insertcolor=PALETTE["text"],
                    padding=6)
    style.configure("TSpinbox",
                    fieldbackground="#ffffff",
                    bordercolor=PALETTE["border"],
                    arrowsize=12,
                    padding=4)
    style.configure("Sidebar.TSpinbox",
                    fieldbackground=PALETTE["sidebar_alt"],
                    bordercolor=PALETTE["border"],
                    arrowsize=12,
                    padding=4)
    style.configure("TCombobox",
                    fieldbackground="#ffffff",
                    bordercolor=PALETTE["border"],
                    padding=6)

    # ------- labelled frames -------
    style.configure("TLabelframe", background=PALETTE["panel"],
                    bordercolor=PALETTE["border"], relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=PALETTE["panel"],
                    foreground=PALETTE["muted"], font=FONT.SECTION)

    # ------- radio / check -------
    style.configure("TRadiobutton", background=PALETTE["panel"], foreground=PALETTE["text"])
    style.configure("Sidebar.TRadiobutton", background=PALETTE["sidebar"],
                    foreground=PALETTE["text"], font=FONT.BODY,
                    indicatorcolor=PALETTE["border"])
    style.map("Sidebar.TRadiobutton",
              background=[("active", PALETTE["sidebar_hover"])])
    style.configure("TCheckbutton", background=PALETTE["panel"], foreground=PALETTE["text"])
    style.configure("Sidebar.TCheckbutton",
                    background=PALETTE["sidebar"], foreground=PALETTE["text"], font=FONT.BODY)
    style.map("Sidebar.TCheckbutton",
              background=[("active", PALETTE["sidebar_hover"])])

    # ------- treeview -------
    style.configure("Treeview",
                    background=PALETTE["panel"],
                    fieldbackground=PALETTE["panel"],
                    foreground=PALETTE["text"],
                    bordercolor=PALETTE["border"],
                    rowheight=28,
                    borderwidth=0,
                    font=FONT.BODY)
    style.configure("Treeview.Heading",
                    background=PALETTE["panel_alt"],
                    foreground=PALETTE["muted"],
                    font=FONT.SECTION,
                    bordercolor=PALETTE["border"],
                    relief="flat",
                    padding=(8, 6))
    style.map("Treeview.Heading", background=[("active", PALETTE["panel_hover"])])
    style.map("Treeview",
              background=[("selected", PALETTE["accent_soft"])],
              foreground=[("selected", PALETTE["text"])])

    style.configure("TSeparator", background=PALETTE["divider"])

    # Scrollbars: subtle
    style.configure("Vertical.TScrollbar",
                    background=PALETTE["bg_alt"],
                    troughcolor=PALETTE["panel_alt"],
                    bordercolor=PALETTE["border"],
                    arrowcolor=PALETTE["muted"],
                    relief="flat")


# ----------------------------------------------------------------------
#  Rounded-rect helper (used by RoundedCard)
# ----------------------------------------------------------------------

def _round_rect_points(x1, y1, x2, y2, r):
    """Polygon points for a rounded rectangle at the given coords."""
    r = max(0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1,
        x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2,
        x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2, x1, y2,
        x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
    ]


class RoundedCard(tk.Frame):
    """A rounded white card with a subtle border and an optional accent stripe.

    Place ttk widgets inside :attr:`body` (a normal ``tk.Frame``).
    """

    def __init__(
        self,
        parent: tk.Widget,
        *,
        radius: int = 12,
        bg: str = PALETTE["panel"],
        border: str = PALETTE["border"],
        accent: Optional[str] = None,
        accent_height: int = 3,
        padding: int = 16,
        outer_bg: Optional[str] = None,
    ):
        outer_bg = outer_bg or _safe_parent_bg(parent)
        super().__init__(parent, bg=outer_bg, highlightthickness=0)
        self.radius = radius
        self._fill = bg
        self._border = border
        self._accent = accent
        self._accent_h = accent_height
        self._padding = padding

        self._canvas = tk.Canvas(self, bg=outer_bg, highlightthickness=0, bd=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self.body = tk.Frame(self._canvas, bg=bg)
        self._win = self._canvas.create_window(0, 0, window=self.body, anchor="nw")

        self._bg_id: Optional[int] = None
        self._accent_id: Optional[int] = None

        self.bind("<Configure>", self._redraw)

    def _redraw(self, _event=None):
        if not self.winfo_exists():
            return
        self.update_idletasks()
        w = max(self.winfo_width(), 8)
        h = max(self.winfo_height(), 8)
        self._canvas.configure(width=w, height=h)
        self._canvas.delete("all")

        # Card body
        self._canvas.create_polygon(
            _round_rect_points(0, 0, w, h, self.radius),
            smooth=True, fill=self._fill, outline=self._border, width=1,
        )

        # Accent stripe (top edge, subtle)
        if self._accent:
            r = self.radius
            stripe_pts = _round_rect_points(0, 0, w, self._accent_h + r, r)
            self._canvas.create_polygon(stripe_pts, smooth=True,
                                         fill=self._accent, outline=self._accent)
            self._canvas.create_rectangle(
                0, self._accent_h, w, self._accent_h + 1,
                fill=self._fill, outline=self._fill,
            )

        # Body window with breathing room
        pad = self._padding
        self._canvas.coords(self._win, pad, pad + (self._accent_h if self._accent else 0))
        self._canvas.itemconfigure(
            self._win,
            width=w - 2 * pad,
            height=h - 2 * pad - (self._accent_h if self._accent else 0),
        )


def _safe_parent_bg(widget: tk.Widget) -> str:
    """Return the parent's background colour as a ``#rrggbb`` string."""
    try:
        return widget.cget("bg")
    except tk.TclError:
        try:
            return widget.cget("background")
        except tk.TclError:
            return PALETTE["bg"]


# ----------------------------------------------------------------------
#  Status pill
# ----------------------------------------------------------------------

_STATUS_STYLES = {
    "ok":       (PALETTE["ok"],     PALETTE["ok_soft"],     "Normal"),
    "watch":    (PALETTE["warn"],   PALETTE["warn_soft"],   "Watch"),
    "atypical": (PALETTE["danger"], PALETTE["danger_soft"], "Atypical"),
    "info":     (PALETTE["info"],   PALETTE["info_soft"],   "Info"),
    "unknown":  (PALETTE["muted"],  PALETTE["panel_alt"],   "—"),
    # Aliases
    "normal":   (PALETTE["ok"],     PALETTE["ok_soft"],     "Normal"),
}


class StatusPill(tk.Canvas):
    """A small rounded pill with a coloured dot and a label."""

    def __init__(self, parent: tk.Widget, status: str = "unknown", text: Optional[str] = None,
                 *, height: int = 22):
        bg = _safe_parent_bg(parent)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, height=height)
        self._status = status
        self._text = text
        self._height = height
        # Estimated width — actual width is set in _redraw based on text metrics
        self.configure(width=120)
        self.bind("<Configure>", lambda _e: self._redraw())
        self.after(1, self._redraw)

    def set_status(self, status: str, text: Optional[str] = None) -> None:
        self._status = status
        if text is not None:
            self._text = text
        self._redraw()

    def _redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        fg, bg, default = _STATUS_STYLES.get(self._status, _STATUS_STYLES["unknown"])
        label = self._text or default

        # Measure text
        text_id = self.create_text(0, 0, text=label, font=FONT.PILL, anchor="nw")
        x1, y1, x2, y2 = self.bbox(text_id)
        tw, th = x2 - x1, y2 - y1
        self.delete(text_id)

        pad_x = 9
        dot_r = 3
        dot_gap = 6
        h = self._height
        w = pad_x + dot_r * 2 + dot_gap + tw + pad_x

        self.configure(width=w, height=h)

        # Pill
        self.create_polygon(
            _round_rect_points(0, 0, w, h, h / 2),
            smooth=True, fill=bg, outline=bg,
        )
        # Dot
        cx = pad_x + dot_r
        cy = h / 2
        self.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                         fill=fg, outline=fg)
        # Text
        self.create_text(
            pad_x + dot_r * 2 + dot_gap, h / 2,
            text=label, font=FONT.PILL, fill=fg, anchor="w",
        )


# ----------------------------------------------------------------------
#  Reference-range bar
# ----------------------------------------------------------------------

class ReferenceRangeBar(tk.Canvas):
    """Mini horizontal bar showing where a value sits within a reference range.

    Layout (logical):

        |· · · watch ·|████ normal ████|· · · watch ·|
                              ▲
                           value
    """

    def __init__(self, parent: tk.Widget, *, height: int = 16):
        bg = _safe_parent_bg(parent)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, height=height)
        self._normal = (0.0, 1.0)
        self._watch = (0.0, 1.0)
        self._value = None
        self._height = height
        self.configure(height=height)
        self.bind("<Configure>", lambda _e: self._redraw())

    def configure_range(self, normal, watch, value=None):
        self._normal = tuple(normal)
        self._watch  = tuple(watch)
        self._value  = value
        self._redraw()

    def _redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        w = max(self.winfo_width(), 80)
        h = self._height
        if w < 4 or h < 4:
            return

        lo, hi = self._watch
        n_lo, n_hi = self._normal
        val = self._value

        # Domain: a bit beyond watch range so the value is visible if outside
        domain_lo = lo
        domain_hi = hi
        if val is not None:
            domain_lo = min(domain_lo, val)
            domain_hi = max(domain_hi, val)
        if domain_hi <= domain_lo:
            domain_hi = domain_lo + 1.0

        def _x(v):
            return (v - domain_lo) / (domain_hi - domain_lo) * w

        # Watch band (full)
        track_y0 = h / 2 - 3
        track_y1 = h / 2 + 3
        self.create_polygon(
            _round_rect_points(0, track_y0, w, track_y1, 3),
            smooth=True, fill=PALETTE["warn_soft"], outline=PALETTE["warn_soft"],
        )
        # Normal band overlay
        self.create_rectangle(
            _x(n_lo), track_y0, _x(n_hi), track_y1,
            fill=PALETTE["ok_soft"], outline=PALETTE["ok_soft"],
        )

        # Value marker
        if val is not None:
            x = _x(val)
            colour = PALETTE["ok"] if (n_lo <= val <= n_hi) \
                else (PALETTE["warn"] if (lo <= val <= hi) else PALETTE["danger"])
            self.create_line(x, 0, x, h, fill=colour, width=2)
            self.create_oval(x - 4, h / 2 - 4, x + 4, h / 2 + 4,
                             fill=colour, outline="white", width=1.5)


# ----------------------------------------------------------------------
#  MetricTile — clinical card with title, value/unit, status, ref range
# ----------------------------------------------------------------------

class MetricTile(RoundedCard):
    """Dashboard tile: title, big value + unit, status pill, ref-range bar."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        value: str,
        unit: str = "",
        *,
        caption: str = "",
        status: str = "unknown",
        accent: Optional[str] = None,
        ref_normal=None,
        ref_watch=None,
        ref_value=None,
    ):
        super().__init__(parent, radius=14, accent=accent, accent_height=3,
                         padding=18)

        body = self.body
        body.configure(bg=self._fill)

        # Title row + status pill
        head = tk.Frame(body, bg=self._fill)
        head.pack(fill=tk.X)
        ttk.Label(head, text=title.upper(), style="CardTitle.TLabel").pack(side=tk.LEFT)
        self._pill = StatusPill(head, status=status)
        self._pill.pack(side=tk.RIGHT)

        # Value + unit on same baseline
        value_row = tk.Frame(body, bg=self._fill)
        value_row.pack(fill=tk.X, pady=(8, 0), anchor="w")
        self._value_lbl = ttk.Label(value_row, text=value, style="CardValue.TLabel")
        self._value_lbl.pack(side=tk.LEFT, anchor="s")
        if unit:
            ttk.Label(value_row, text=" " + unit, style="CardUnit.TLabel").pack(side=tk.LEFT, anchor="s",
                                                                                pady=(0, 6))

        # Reference range bar
        if ref_normal is not None and ref_watch is not None:
            self._ref_bar = ReferenceRangeBar(body)
            self._ref_bar.pack(fill=tk.X, pady=(12, 4))
            self._ref_bar.configure_range(ref_normal, ref_watch, ref_value)

            # Range annotation under bar
            lo, hi = ref_normal
            ttk.Label(
                body,
                text=f"Typical  {lo:g}–{hi:g}",
                style="CardCaption.TLabel",
            ).pack(anchor="w")

        if caption:
            ttk.Label(body, text=caption, style="CardCaption.TLabel").pack(anchor="w", pady=(8, 0))

    def set_value(self, value: str) -> None:
        self._value_lbl.config(text=value)


# ----------------------------------------------------------------------
#  SidebarSection — small uppercase header inside the sidebar
# ----------------------------------------------------------------------

class SidebarSection(tk.Frame):
    def __init__(self, parent: tk.Widget, title: str):
        super().__init__(parent, bg=PALETTE["sidebar"])
        ttk.Label(self, text=title.upper(), style="SidebarHeader.TLabel").pack(
            anchor="w", padx=18, pady=(18, 6))
        sep = tk.Frame(self, bg=PALETTE["divider"], height=1)
        sep.pack(fill=tk.X, padx=18)


# ----------------------------------------------------------------------
#  Finding row (used by interpretation panel)
# ----------------------------------------------------------------------

class FindingRow(tk.Frame):
    """One coloured row in the clinical interpretation panel."""

    SEV_COLORS = {
        "ok":       (PALETTE["ok"],      PALETTE["ok_soft"]),
        "watch":    (PALETTE["warn"],    PALETTE["warn_soft"]),
        "atypical": (PALETTE["danger"],  PALETTE["danger_soft"]),
        "info":     (PALETTE["info"],    PALETTE["info_soft"]),
    }

    def __init__(self, parent, severity: str, headline: str, detail: str = ""):
        bg = PALETTE["panel"]
        super().__init__(parent, bg=bg)
        fg, soft = self.SEV_COLORS.get(severity, self.SEV_COLORS["info"])

        # Coloured stripe on the left
        stripe = tk.Frame(self, bg=fg, width=3)
        stripe.pack(side=tk.LEFT, fill=tk.Y)

        body = tk.Frame(self, bg=bg)
        body.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=8)

        head_row = tk.Frame(body, bg=bg)
        head_row.pack(fill=tk.X)
        # Badge
        StatusPill(head_row, status=severity).pack(side=tk.LEFT)
        ttk.Label(head_row, text=headline, font=FONT.BODY_BOLD,
                  background=bg, foreground=PALETTE["text"]).pack(side=tk.LEFT, padx=(8, 0))
        if detail:
            ttk.Label(body, text=detail, font=FONT.SMALL,
                      background=bg, foreground=PALETTE["muted_strong"],
                      wraplength=420, justify="left").pack(anchor="w", pady=(4, 0))
