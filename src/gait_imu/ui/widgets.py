"""Reusable styled widgets for the dark futuristic UI.

Includes:

* ``install_styles``  – ttk style installer
* ``Card``            – simple bordered surface with an optional accent stripe
* ``FlipCard``        – like Card, but swaps to a "back" view while hovered
* ``MetricTile``      – a FlipCard preset for clinical dashboard tiles
* ``PillTabBar``      – Canvas-drawn pill tabs (replaces ttk.Notebook)
* ``StatusPill``      – coloured pill with dot + label
* ``ReferenceRangeBar`` – tiny horizontal range bar
* ``FindingRow``      – one row in the clinical interpretation panel
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from ..theme import FONT, PALETTE


# ----------------------------------------------------------------------
#  Rounded-rect helper (used by pill buttons + status pills)
# ----------------------------------------------------------------------

def round_rect_points(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1,
        x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2,
        x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2, x1, y2,
        x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
    ]


# ----------------------------------------------------------------------
#  Style installer
# ----------------------------------------------------------------------

def install_styles() -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Base
    style.configure(".", background=PALETTE["panel"], foreground=PALETTE["text"],
                    font=FONT.BODY)

    # Frames
    for name, bg in [
        ("App.TFrame",       PALETTE["bg"]),
        ("Panel.TFrame",     PALETTE["panel"]),
        ("PanelAlt.TFrame",  PALETTE["panel_alt"]),
        ("Card.TFrame",      PALETTE["panel"]),
    ]:
        style.configure(name, background=bg, borderwidth=0)

    # Labels
    style.configure("TLabel",         background=PALETTE["panel"], foreground=PALETTE["text"])
    style.configure("App.TLabel",     background=PALETTE["bg"],    foreground=PALETTE["text"])
    style.configure("Muted.TLabel",   background=PALETTE["panel"], foreground=PALETTE["muted"])
    style.configure("AppMuted.TLabel",background=PALETTE["bg"],    foreground=PALETTE["muted"])
    style.configure("Header.TLabel",   background=PALETTE["panel"],
                    foreground=PALETTE["text"], font=FONT.HEADER)
    style.configure("AppHeader.TLabel",background=PALETTE["bg"],
                    foreground=PALETTE["text"], font=FONT.HEADER)
    style.configure("Hero.TLabel",     background=PALETTE["panel"],
                    foreground=PALETTE["text"], font=FONT.HERO)
    style.configure("Subheader.TLabel",background=PALETTE["panel"],
                    foreground=PALETTE["muted"], font=FONT.SUBHEADER)
    style.configure("AppSubheader.TLabel", background=PALETTE["bg"],
                    foreground=PALETTE["muted"], font=FONT.SUBHEADER)
    style.configure("Section.TLabel",  background=PALETTE["panel"],
                    foreground=PALETTE["muted"], font=FONT.SECTION)
    style.configure("AppSection.TLabel", background=PALETTE["bg"],
                    foreground=PALETTE["muted"], font=FONT.SECTION)

    # Buttons (ttk fallback — most buttons in the app are custom Canvas pills)
    style.configure("TButton",
                    padding=(12, 8),
                    background=PALETTE["panel_alt"],
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
                    foreground=PALETTE["bg"],
                    padding=(16, 10),
                    relief="flat",
                    borderwidth=0,
                    focusthickness=0,
                    font=FONT.BODY_BOLD)
    style.map("Accent.TButton", background=[("active", PALETTE["accent_glow"])])

    style.configure("Hero.TButton",
                    background=PALETTE["accent"],
                    foreground=PALETTE["bg"],
                    padding=(28, 14),
                    relief="flat",
                    borderwidth=0,
                    focusthickness=0,
                    font=("Helvetica Neue", 13, "bold"))
    style.map("Hero.TButton", background=[("active", PALETTE["accent_glow"])])

    # Inputs
    style.configure("TEntry",
                    fieldbackground=PALETTE["panel_alt"],
                    foreground=PALETTE["text"],
                    bordercolor=PALETTE["border"],
                    lightcolor=PALETTE["border"],
                    darkcolor=PALETTE["border"],
                    insertcolor=PALETTE["accent"],
                    padding=6)
    style.configure("TSpinbox",
                    fieldbackground=PALETTE["panel_alt"],
                    foreground=PALETTE["text"],
                    bordercolor=PALETTE["border"],
                    arrowsize=12,
                    padding=4)
    style.configure("TCombobox",
                    fieldbackground=PALETTE["panel_alt"],
                    foreground=PALETTE["text"],
                    bordercolor=PALETTE["border"],
                    padding=6)

    # Radio / check
    style.configure("TRadiobutton",
                    background=PALETTE["panel"], foreground=PALETTE["text"],
                    font=FONT.BODY, indicatorcolor=PALETTE["panel_alt"])
    style.configure("App.TRadiobutton",
                    background=PALETTE["bg"], foreground=PALETTE["text"],
                    font=FONT.BODY)
    style.configure("Card.TRadiobutton",
                    background=PALETTE["panel"], foreground=PALETTE["text"],
                    font=FONT.BODY)
    style.configure("TCheckbutton",
                    background=PALETTE["panel"], foreground=PALETTE["text"])

    # Treeview
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
    style.configure("TLabelframe",
                    background=PALETTE["panel"], bordercolor=PALETTE["border"],
                    relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label",
                    background=PALETTE["panel"], foreground=PALETTE["muted"],
                    font=FONT.SECTION)


# ----------------------------------------------------------------------
#  Card — Canvas-backed rounded surface with optional accent stripe
# ----------------------------------------------------------------------

def _parent_bg(widget: tk.Widget) -> str:
    """Return ``widget``'s background color, falling back to app bg."""
    for key in ("bg", "background"):
        try:
            v = widget.cget(key)
            if v:
                return v
        except tk.TclError:
            pass
    return PALETTE["bg"]


class Card(tk.Frame):
    """Rounded card with hairline border + optional accent stripe.

    Drawn via a ``tk.Canvas`` polygon so corners are actually rounded.
    Pack widgets into ``self.body`` (a normal :class:`tk.Frame`).
    """

    def __init__(
        self,
        parent: tk.Widget,
        *,
        radius: int = 14,
        accent: Optional[str] = None,
        accent_height: int = 3,
        padding: int = 16,
        bg: str = PALETTE["panel"],
        border: str = PALETTE["border"],
    ):
        outer_bg = _parent_bg(parent)
        super().__init__(parent, bg=outer_bg, highlightthickness=0, bd=0)
        self._radius = radius
        self._accent = accent
        self._accent_h = accent_height
        self._padding = padding
        self._bg = bg
        self._border_default = border
        self._border = border

        self._canvas = tk.Canvas(self, bg=outer_bg, highlightthickness=0, bd=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self.body = tk.Frame(self._canvas, bg=bg, highlightthickness=0, bd=0)
        self._win_id = self._canvas.create_window(0, 0, window=self.body, anchor="nw")

        # Re-render the rounded background whenever the card is resized.
        self.bind("<Configure>", self._on_resize)

    def set_border(self, color: str) -> None:
        """Outline colour (used to "glow" on hover)."""
        if color == self._border:
            return
        self._border = color
        self._redraw()

    # -------------- internal --------------
    def _on_resize(self, _e):
        self._redraw()

    def _redraw(self) -> None:
        if not self.winfo_exists():
            return
        w = max(self.winfo_width(), 8)
        h = max(self.winfo_height(), 8)
        self._canvas.configure(width=w, height=h)
        self._canvas.delete("bg")

        # Rounded panel background
        self._canvas.create_polygon(
            round_rect_points(1, 1, w - 1, h - 1, self._radius),
            smooth=True, fill=self._bg, outline=self._border, width=1,
            tags="bg",
        )

        # Optional accent strip at top — clipped to the rounded corners
        if self._accent:
            r = self._radius
            stripe = round_rect_points(1, 1, w - 1, self._accent_h + r, r)
            self._canvas.create_polygon(stripe, smooth=True,
                                         fill=self._accent, outline=self._accent,
                                         tags="bg")
            # Square the stripe at the bottom
            self._canvas.create_rectangle(
                1, self._accent_h, w - 1, self._accent_h + 1,
                fill=self._bg, outline=self._bg, tags="bg")

        # Position and size the body window inside the rounded area
        top = self._padding + (self._accent_h if self._accent else 0)
        self._canvas.coords(self._win_id, self._padding, top)
        self._canvas.itemconfigure(
            self._win_id,
            width=max(1, w - 2 * self._padding),
            height=max(1, h - 2 * self._padding - (self._accent_h if self._accent else 0)),
        )
        self._canvas.tag_lower("bg")


# ----------------------------------------------------------------------
#  FlipCard — swap to a "back" view while hovered (rounded)
# ----------------------------------------------------------------------

class FlipCard(Card):
    """Rounded card that swaps body content on hover."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        front_builder: Callable[[tk.Frame], None],
        back_builder: Callable[[tk.Frame], None],
        radius: int = 14,
        accent: Optional[str] = None,
        accent_height: int = 3,
        padding: int = 16,
        bg: str = PALETTE["panel"],
        border: str = PALETTE["border"],
    ):
        super().__init__(parent, radius=radius, accent=accent,
                         accent_height=accent_height, padding=padding,
                         bg=bg, border=border)
        self._front_builder = front_builder
        self._back_builder = back_builder
        self._showing_back = False
        self._after_id: Optional[str] = None

        self._show_front()

    # ----- face management -----
    def _clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    def _show_front(self):
        self._clear_body()
        self._front_builder(self.body)
        self._bind_recursive(self)

    def _show_back(self):
        self._clear_body()
        self._back_builder(self.body)
        self._bind_recursive(self)

    def _bind_recursive(self, w: tk.Widget) -> None:
        try:
            w.bind("<Enter>", self._on_enter, "+")
            w.bind("<Leave>", self._on_leave, "+")
        except tk.TclError:
            return
        for c in w.winfo_children():
            self._bind_recursive(c)

    def _on_enter(self, _e):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        if not self._showing_back:
            self._showing_back = True
            self._show_back()
            self.set_border(PALETTE["accent"])

    def _on_leave(self, _e):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(80, self._maybe_show_front)

    def _maybe_show_front(self):
        self._after_id = None
        x, y = self.winfo_pointerxy()
        x0 = self.winfo_rootx(); y0 = self.winfo_rooty()
        x1 = x0 + self.winfo_width(); y1 = y0 + self.winfo_height()
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            if self._showing_back:
                self._showing_back = False
                self._show_front()
                self.set_border(self._border_default)


# ----------------------------------------------------------------------
#  Status pill
# ----------------------------------------------------------------------

_STATUS_STYLES = {
    "ok":       (PALETTE["ok"],     PALETTE["ok_soft"],     "Normal"),
    "watch":    (PALETTE["warn"],   PALETTE["warn_soft"],   "Watch"),
    "atypical": (PALETTE["danger"], PALETTE["danger_soft"], "Atypical"),
    "info":     (PALETTE["info"],   PALETTE["info_soft"],   "Info"),
    "unknown":  (PALETTE["muted"],  PALETTE["panel_alt"],   "—"),
    "normal":   (PALETTE["ok"],     PALETTE["ok_soft"],     "Normal"),
}


class StatusPill(tk.Frame):
    def __init__(self, parent: tk.Widget, status: str = "unknown",
                 text: Optional[str] = None, *, bg_parent: Optional[str] = None):
        outer = bg_parent or _safe_parent_bg(parent)
        super().__init__(parent, bg=outer, highlightthickness=0, bd=0)
        fg, soft, default = _STATUS_STYLES.get(status, _STATUS_STYLES["unknown"])
        label = text or default

        pill = tk.Frame(self, bg=soft, highlightthickness=0, bd=0)
        pill.pack()
        inner = tk.Frame(pill, bg=soft)
        inner.pack(padx=10, pady=4)

        dot = tk.Canvas(inner, width=8, height=8, bg=soft, highlightthickness=0, bd=0)
        dot.create_oval(1, 1, 7, 7, fill=fg, outline=fg)
        dot.pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(inner, text=label, font=FONT.PILL, fg=fg, bg=soft).pack(side=tk.LEFT)


_safe_parent_bg = _parent_bg  # backwards-compatible alias


# ----------------------------------------------------------------------
#  Reference-range bar
# ----------------------------------------------------------------------

class ReferenceRangeBar(tk.Canvas):
    def __init__(self, parent: tk.Widget, *, height: int = 14):
        bg = _safe_parent_bg(parent)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, height=height)
        self._normal = (0.0, 1.0)
        self._watch = (0.0, 1.0)
        self._value = None
        self._height = height
        self.bind("<Configure>", lambda *_args: self._redraw())

    def configure_range(self, normal, watch, value=None):
        self._normal = tuple(normal)
        self._watch = tuple(watch)
        self._value = value
        self._redraw()

    def _redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        w = max(self.winfo_width(), 80)
        h = self._height

        lo, hi = self._watch
        n_lo, n_hi = self._normal
        val = self._value

        domain_lo, domain_hi = lo, hi
        if val is not None:
            domain_lo = min(domain_lo, val)
            domain_hi = max(domain_hi, val)
        if domain_hi <= domain_lo:
            domain_hi = domain_lo + 1.0

        def _x(v):
            return (v - domain_lo) / (domain_hi - domain_lo) * w

        # Watch band (ghost)
        ty0, ty1 = h // 2 - 2, h // 2 + 2
        self.create_rectangle(0, ty0, w, ty1,
                              fill=PALETTE["panel_alt"], outline=PALETTE["panel_alt"])
        # Normal band (cyan-tint)
        self.create_rectangle(_x(n_lo), ty0, _x(n_hi), ty1,
                              fill=PALETTE["accent_soft"], outline=PALETTE["accent_soft"])

        if val is not None:
            x = _x(val)
            colour = (PALETTE["ok"] if (n_lo <= val <= n_hi)
                      else (PALETTE["warn"] if (lo <= val <= hi) else PALETTE["danger"]))
            self.create_line(x, 0, x, h, fill=colour, width=2)
            self.create_oval(x - 3, h // 2 - 3, x + 3, h // 2 + 3,
                             fill=colour, outline=PALETTE["panel"], width=1)


# ----------------------------------------------------------------------
#  MetricTile  — flip-on-hover dashboard tile
# ----------------------------------------------------------------------

class MetricTile(FlipCard):
    """Front: title + value + status + ref-range bar.
    Back: a plain-language description of what the metric is.
    """

    # Conservative wraplength — text needs to fit even on narrow tiles.
    WRAP = 200

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
        description: str = "",
    ):
        # Keep references for builders (closures need them)
        self._title = title
        self._value = value
        self._unit = unit
        self._caption = caption
        self._status = status
        self._ref_normal = ref_normal
        self._ref_watch = ref_watch
        self._ref_value = ref_value
        self._description = description

        super().__init__(
            parent,
            front_builder=self._build_front,
            back_builder=self._build_back,
            radius=16,
            accent=accent,
            accent_height=3,
            padding=18,
        )

    # ---- FRONT ----
    def _build_front(self, body: tk.Frame) -> None:
        bg = body.cget("bg")

        head = tk.Frame(body, bg=bg)
        head.pack(fill=tk.X)
        tk.Label(head, text=self._title.upper(), font=FONT.SECTION,
                 fg=PALETTE["muted"], bg=bg).pack(side=tk.LEFT)
        StatusPill(head, status=self._status, bg_parent=bg).pack(side=tk.RIGHT)

        value_row = tk.Frame(body, bg=bg)
        value_row.pack(fill=tk.X, pady=(8, 0), anchor="w")
        tk.Label(value_row, text=self._value, font=FONT.METRIC,
                 fg=PALETTE["text"], bg=bg).pack(side=tk.LEFT, anchor="s")
        if self._unit:
            tk.Label(value_row, text=" " + self._unit, font=FONT.METRIC_UNIT,
                     fg=PALETTE["muted_strong"], bg=bg
                     ).pack(side=tk.LEFT, anchor="s", pady=(0, 6))

        if self._ref_normal is not None and self._ref_watch is not None:
            bar_wrap = tk.Frame(body, bg=bg)
            bar_wrap.pack(fill=tk.X, pady=(12, 4))
            bar = ReferenceRangeBar(bar_wrap)
            bar.pack(fill=tk.X)
            self.after(1, lambda: bar.configure_range(
                self._ref_normal, self._ref_watch, self._ref_value))

            lo, hi = self._ref_normal
            tk.Label(body, text=f"Typical  {lo:g}–{hi:g}",
                     font=FONT.SMALL, fg=PALETTE["muted"], bg=bg
                     ).pack(anchor="w")

        if self._caption:
            tk.Label(body, text=self._caption, font=FONT.SMALL,
                     fg=PALETTE["muted"], bg=bg, justify="left",
                     wraplength=self.WRAP
                     ).pack(anchor="w", pady=(8, 0))

        tk.Label(body, text="HOVER FOR DETAILS  ›", font=FONT.SMALL_BOLD,
                 fg=PALETTE["accent"], bg=bg
                 ).pack(anchor="w", pady=(8, 0))

    # ---- BACK ----
    def _build_back(self, body: tk.Frame) -> None:
        bg = body.cget("bg")

        tk.Label(body, text=self._title.upper(), font=FONT.SECTION,
                 fg=PALETTE["accent"], bg=bg).pack(anchor="w")
        tk.Label(body, text="WHAT IT MEASURES",
                 font=FONT.SECTION, fg=PALETTE["muted"],
                 bg=bg).pack(anchor="w", pady=(2, 8))

        if self._description:
            tk.Label(body, text=self._description,
                     font=FONT.BODY, fg=PALETTE["text_soft"],
                     bg=bg, justify="left", wraplength=self.WRAP
                     ).pack(anchor="w", pady=(2, 0))

        # Current value at the bottom
        current = (f"current  =  {self._value}  {self._unit}"
                   if self._unit else f"current  =  {self._value}")
        tk.Label(body, text=current, font=FONT.MONO,
                 fg=PALETTE["accent_glow"], bg=bg
                 ).pack(anchor="w", pady=(14, 0))


# ----------------------------------------------------------------------
#  PillTabBar — futuristic pill-style tabs
# ----------------------------------------------------------------------

class PillTabBar(tk.Frame):
    """Custom tab bar — a row of Canvas-drawn pill buttons over a stack
    of content frames. API mimics ``ttk.Notebook``:

        tabs = PillTabBar(parent)
        f = tabs.add_tab("Home")
        ...
        tabs.select("Home")
    """

    PAD_X = 22
    HEIGHT = 38
    GAP = 8
    RADIUS = 18

    def __init__(self, parent: tk.Widget):
        super().__init__(parent, bg=PALETTE["bg"], highlightthickness=0, bd=0)

        # Tab bar row
        self._bar = tk.Frame(self, bg=PALETTE["bg"], highlightthickness=0, bd=0)
        self._bar.pack(fill=tk.X, side=tk.TOP, padx=2, pady=(2, 6))

        # Content area (stacked frames)
        self._content = tk.Frame(self, bg=PALETTE["bg"], highlightthickness=0, bd=0)
        self._content.pack(fill=tk.BOTH, expand=True)

        self._tabs: List[Tuple[str, tk.Canvas, tk.Frame]] = []
        self._active: Optional[str] = None

    # -------------------- public API --------------------
    def add_tab(self, name: str) -> tk.Frame:
        canvas = tk.Canvas(self._bar,
                           bg=PALETTE["bg"], highlightthickness=0, bd=0,
                           height=self.HEIGHT)
        # Width is set after measuring text
        canvas.pack(side=tk.LEFT, padx=(0, self.GAP))

        # Hidden frame for this tab's content
        frame = tk.Frame(self._content, bg=PALETTE["bg"], highlightthickness=0, bd=0)

        canvas.bind("<Button-1>", lambda _e, n=name: self.select(n))
        canvas.bind("<Enter>",    lambda _e, n=name: self._set_hover(n, True))
        canvas.bind("<Leave>",    lambda _e, n=name: self._set_hover(n, False))

        self._tabs.append((name, canvas, frame))

        # Render this pill
        self._render_pill(canvas, name, active=False, hover=False)

        if self._active is None:
            self.select(name)
        return frame

    def select(self, name: str) -> None:
        # Hide all, show selected
        for n, _, f in self._tabs:
            f.pack_forget()
        for n, _, f in self._tabs:
            if n == name:
                f.pack(fill=tk.BOTH, expand=True)
                self._active = n
                break
        # Re-render all pills with new active state
        for n, c, _ in self._tabs:
            self._render_pill(c, n, active=(n == self._active), hover=False)

    def get_frame(self, name: str) -> Optional[tk.Frame]:
        for n, _, f in self._tabs:
            if n == name:
                return f
        return None

    # -------------------- private --------------------
    def _set_hover(self, name: str, hovering: bool) -> None:
        for n, c, _ in self._tabs:
            if n == name:
                self._render_pill(c, n,
                                  active=(n == self._active),
                                  hover=hovering)
                return

    def _render_pill(self, canvas: tk.Canvas, label: str,
                     *, active: bool, hover: bool) -> None:
        canvas.delete("all")

        # Measure the label
        tmp = canvas.create_text(0, 0, text=label, font=FONT.TAB, anchor="nw")
        x1, y1, x2, y2 = canvas.bbox(tmp)
        tw = x2 - x1
        canvas.delete(tmp)

        w = tw + self.PAD_X * 2
        h = self.HEIGHT
        canvas.configure(width=w, height=h)

        if active:
            fill = PALETTE["accent"]
            fg = PALETTE["bg"]
            outline = PALETTE["accent_glow"]
            outline_w = 1
        elif hover:
            fill = PALETTE["panel_hover"]
            fg = PALETTE["accent_glow"]
            outline = PALETTE["border_strong"]
            outline_w = 1
        else:
            fill = PALETTE["panel"]
            fg = PALETTE["muted_strong"]
            outline = PALETTE["border"]
            outline_w = 1

        # Glow halo for active tab — a few faint outer strokes
        if active:
            glow = PALETTE["accent_glow"]
            for offset, alpha_color in ((4, "#16414e"), (3, "#1c5566"), (2, "#22687e")):
                canvas.create_polygon(
                    round_rect_points(offset, offset, w - offset, h - offset, self.RADIUS),
                    smooth=True, fill="", outline=alpha_color, width=2)

        canvas.create_polygon(
            round_rect_points(2, 2, w - 2, h - 2, self.RADIUS),
            smooth=True, fill=fill, outline=outline, width=outline_w,
        )
        canvas.create_text(w / 2, h / 2, text=label, font=FONT.TAB,
                           fill=fg, anchor="center")


# ----------------------------------------------------------------------
#  Finding row (clinical interpretation panel)
# ----------------------------------------------------------------------

class FindingRow(tk.Frame):
    SEV_COLORS = {
        "ok":       (PALETTE["ok"],      PALETTE["ok_soft"]),
        "watch":    (PALETTE["warn"],    PALETTE["warn_soft"]),
        "atypical": (PALETTE["danger"],  PALETTE["danger_soft"]),
        "info":     (PALETTE["info"],    PALETTE["info_soft"]),
    }

    def __init__(self, parent, severity: str, headline: str, detail: str = ""):
        bg = _safe_parent_bg(parent)
        super().__init__(parent, bg=bg)
        fg, _ = self.SEV_COLORS.get(severity, self.SEV_COLORS["info"])

        stripe = tk.Frame(self, bg=fg, width=3)
        stripe.pack(side=tk.LEFT, fill=tk.Y)

        body = tk.Frame(self, bg=bg)
        body.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=8)

        head_row = tk.Frame(body, bg=bg)
        head_row.pack(fill=tk.X)
        StatusPill(head_row, status=severity, bg_parent=bg).pack(side=tk.LEFT)
        tk.Label(head_row, text=headline, font=FONT.BODY_BOLD,
                 fg=PALETTE["text"], bg=bg).pack(side=tk.LEFT, padx=(8, 0))
        if detail:
            tk.Label(body, text=detail, font=FONT.SMALL,
                     fg=PALETTE["text_soft"], bg=bg,
                     wraplength=420, justify="left").pack(anchor="w", pady=(4, 0))


# ----------------------------------------------------------------------
#  SectionHeader (for setup tab cards)
# ----------------------------------------------------------------------

class SectionHeader(tk.Frame):
    def __init__(self, parent: tk.Widget, title: str, *, on_panel: bool = True):
        bg = PALETTE["panel"] if on_panel else PALETTE["bg"]
        super().__init__(parent, bg=bg)
        tk.Label(self, text=title.upper(), font=FONT.SECTION,
                 fg=PALETTE["muted"], bg=bg).pack(anchor="w", pady=(0, 4))
        sep = tk.Frame(self, bg=PALETTE["divider"], height=1)
        sep.pack(fill=tk.X)
