"""Main Tk application — dark futuristic medical layout.

    +----------------------------------------------------------+
    |  HEADER   (title + active session note)                  |
    +----------------------------------------------------------+
    |  PILL TABS  Home · Setup · Dashboard · Acceleration · …  |
    +----------------------------------------------------------+
    |  STATUS BAR                                              |
    +----------------------------------------------------------+
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..clinical_reference import REFERENCE
from ..export import export_session
from ..gait import (
    build_outputs_from_pairs,
    compute_ankle_angle,
    compute_knee_series,
    process_files_ankle,
    process_files_knee,
)
from ..io_utils import parse_range
from ..theme import FONT, PALETTE, PLOT_COLORS, style_mpl
from .plots import (
    build_acceleration_figure,
    build_all_strides_figure,
    build_dashboard_histogram_figure,
    build_dashboard_overlay_figure,
    build_overlay_figure,
)
from .sensor_diagram import build_sensor_diagram
from .widgets import (
    Card,
    MetricTile,
    PillTabBar,
    SectionHeader,
    install_styles,
)


# Plain-language descriptions shown on the back of the dashboard tiles
DESCRIPTIONS = {
    "Cadence": (
        "Number of steps per minute. Calculated from the average time "
        "between consecutive heel strikes on the same foot, across all "
        "kept strides."
    ),
    "Stride Time": (
        "Seconds between two ipsilateral heel strikes — i.e. one full "
        "gait cycle. The card shows the mean ± SD across kept strides."
    ),
    "Stride Length": (
        "Distance the foot travels in one stride. Estimated by double-"
        "integrating the foot's horizontal world acceleration with a "
        "drift correction so velocity returns to zero by stride end."
    ),
    "Walking Speed": (
        "How fast the person is walking. Equal to mean stride length "
        "divided by mean stride time. Available only for ankle sessions, "
        "which carry the foot accelerometer."
    ),
    "Gait Variability": (
        "Stride-to-stride consistency, expressed as a robust coefficient "
        "of variation of stride time. Lower means steadier walking; "
        "higher values can suggest an unsteady gait."
    ),
}


class IMUApp:
    APP_TITLE = "Gait IMU Analyzer"
    APP_SUBTITLE = "Clinical-grade ankle / knee gait analysis from inertial sensors"

    # ------------------------------- Lifecycle ------------------------------
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(self.APP_TITLE)
        self.root.geometry("1480x980")
        self.root.minsize(1180, 760)
        self.root.configure(bg=PALETTE["bg"])

        style_mpl()
        install_styles()

        # State
        self.calibration_enabled = tk.BooleanVar(value=True)
        self.pair_mode = tk.StringVar(value="ankle")
        self.ankle_mode = tk.StringVar(value="dfpf")
        self.show_normative = tk.BooleanVar(value=True)
        self.start_peak_idx = None
        self.pick_mode = False
        self._mpl_cid_click = None
        self._mpl_cid_key = None

        self.stand_win = (3.0, 5.0)
        self.flex_win = None
        self.ankle_zero_win = (3.0, 8.0)
        self.trim_first_n = 0
        self.trim_last_n = 0

        self.last_base = None
        self._raw = None

        self.stride_keep = None
        self._stride_lines = []
        self._allstrides_pick_cid = None
        self.legend_tree = None

        self._loaded_file_a = tk.StringVar(value="")
        self._loaded_file_b = tk.StringVar(value="")
        self._session_note = tk.StringVar(value="No session loaded — open the Home tab to start.")

        # Home-tab diagram canvas (rebuilds on joint change)
        self._home_diagram_holder = None
        self._home_canvas = None
        self.pair_mode.trace_add("write", lambda *_: self._refresh_home_diagram())

        self.canvas_accel = None
        self.canvas_stride = None
        self.canvas_allstrides = None

        self._build_layout()

    # ------------------------------- Layout ---------------------------------
    def _build_layout(self) -> None:
        outer = tk.Frame(self.root, bg=PALETTE["bg"])
        outer.pack(fill=tk.BOTH, expand=True)
        self._build_header(outer)
        self._build_tabs(outer)
        self._build_status_bar(outer)

    def _build_header(self, parent: tk.Frame) -> None:
        header = tk.Frame(parent, bg=PALETTE["bg"])
        header.pack(fill=tk.X)
        inner = tk.Frame(header, bg=PALETTE["bg"])
        inner.pack(fill=tk.X, padx=28, pady=(20, 14))

        brand_row = tk.Frame(inner, bg=PALETTE["bg"])
        brand_row.pack(anchor="w")
        # Glowing dot logo
        dot = tk.Canvas(brand_row, width=18, height=18,
                        bg=PALETTE["bg"], highlightthickness=0)
        # outer glow rings
        dot.create_oval(0, 0, 18, 18, fill="#0e2f3a", outline="")
        dot.create_oval(2, 2, 16, 16, fill="#0e6479", outline="")
        dot.create_oval(5, 5, 13, 13, fill=PALETTE["accent"], outline="")
        dot.pack(side=tk.LEFT, padx=(0, 12), pady=(2, 0))
        tk.Label(brand_row, text=self.APP_TITLE, font=FONT.HEADER,
                 fg=PALETTE["text"], bg=PALETTE["bg"]).pack(side=tk.LEFT)

        tk.Label(inner, text=self.APP_SUBTITLE,
                 font=FONT.SUBHEADER, fg=PALETTE["muted"],
                 bg=PALETTE["bg"]).pack(anchor="w", pady=(4, 0))
        tk.Label(inner, textvariable=self._session_note,
                 font=FONT.SUBHEADER, fg=PALETTE["accent_glow"],
                 bg=PALETTE["bg"]).pack(anchor="w", pady=(8, 0))

        # Glow line under the header
        sep = tk.Frame(parent, bg=PALETTE["accent"], height=1)
        sep.pack(fill=tk.X)
        sep_glow = tk.Frame(parent, bg=PALETTE["accent_soft"], height=1)
        sep_glow.pack(fill=tk.X)

    def _build_tabs(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=PALETTE["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=(14, 0))

        self.tabs = PillTabBar(body)
        self.tabs.pack(fill=tk.BOTH, expand=True)

        self.tab_home       = self.tabs.add_tab("Home")
        self.tab_setup      = self.tabs.add_tab("Setup")
        self.tab_dash       = self.tabs.add_tab("Dashboard")
        self.tab_accel      = self.tabs.add_tab("Acceleration / HS")
        self.tab_stride     = self.tabs.add_tab("Gait-Cycle Overlay")
        self.tab_allstrides = self.tabs.add_tab("All Strides")

        # Build the static tabs (Home, Setup); placeholders for data tabs
        self._build_home_tab()
        self._build_setup_tab()
        self._render_dashboard_placeholder()

        self.tabs.select("Home")

    def _build_status_bar(self, parent: tk.Frame) -> None:
        sep = tk.Frame(parent, bg=PALETTE["divider"], height=1)
        sep.pack(fill=tk.X, side=tk.BOTTOM)
        bar = tk.Frame(parent, bg=PALETTE["bg"], height=30)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self.status_lbl = tk.Label(bar, text="Ready.",
                                   font=FONT.SMALL, fg=PALETTE["muted"],
                                   bg=PALETTE["bg"])
        self.status_lbl.pack(side=tk.LEFT, padx=20, pady=6)
        self.pick_lbl = tk.Label(bar, text="", font=FONT.SMALL,
                                 fg=PALETTE["accent_glow"], bg=PALETTE["bg"])
        self.pick_lbl.pack(side=tk.RIGHT, padx=20)

    # ------------------------------- Home tab -------------------------------
    #
    # Layout: two numbered steps stacked vertically.
    #   STEP 1 — place the sensors (3D diagram on the left, instructions on the right)
    #   STEP 2 — pick a joint and load the two CSVs

    STEP_NUM_FONT = ("Helvetica Neue", 38, "bold")

    def _build_home_tab(self) -> None:
        for w in self.tab_home.winfo_children():
            w.destroy()

        wrap = tk.Frame(self.tab_home, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=12)

        # ------------------- STEP 1 — Place the sensors -------------------
        # NOTE: Step 2 is packed FIRST at the bottom, so it is always visible
        # regardless of how tall Step 1's contents are. Step 1 then fills
        # whatever vertical space is left.
        step1 = Card(wrap, padding=18, radius=18,
                     accent=PALETTE["accent"], accent_height=3)
        s1 = step1.body

        # Header row
        s1_head = tk.Frame(s1, bg=PALETTE["panel"])
        s1_head.pack(fill=tk.X)
        s1_head_left = tk.Frame(s1_head, bg=PALETTE["panel"])
        s1_head_left.pack(side=tk.LEFT)
        tk.Label(s1_head_left, text="STEP 1   ·   PLACE THE SENSORS",
                 font=FONT.SECTION, fg=PALETTE["accent"],
                 bg=PALETTE["panel"]).pack(anchor="w")
        tk.Label(s1_head_left,
                 text="Mount each IMU as shown. Orientation is auto-calibrated "
                      "— exact rotation on the limb is not critical.",
                 font=FONT.SMALL, fg=PALETTE["muted"], bg=PALETTE["panel"]
                 ).pack(anchor="w", pady=(2, 0))

        # Two-column body — placement instructions on the left,
        # the 3-view anatomical diagram on the right.
        s1_body = tk.Frame(s1, bg=PALETTE["panel"])
        s1_body.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        s1_body.columnconfigure(0, weight=0, minsize=320)
        s1_body.columnconfigure(1, weight=1)
        s1_body.rowconfigure(0, weight=1)

        instr_card = Card(s1_body, padding=16, radius=14)
        instr_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._home_instructions_holder = instr_card.body

        leg_card = Card(s1_body, padding=10, radius=14)
        leg_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._home_diagram_holder = leg_card.body

        # ------------------- STEP 2 — Load CSVs -------------------
        step2 = Card(wrap, padding=18, radius=18,
                     accent=PALETTE["accent_glow"], accent_height=3)
        s2 = step2.body
        s2.columnconfigure(0, weight=0)
        s2.columnconfigure(1, weight=1)
        s2.columnconfigure(2, weight=0)

        # Step number
        num2 = tk.Frame(s2, bg=PALETTE["panel"])
        num2.grid(row=0, column=0, sticky="nw", padx=(0, 18))
        tk.Label(num2, text="STEP 2", font=FONT.SECTION,
                 fg=PALETTE["accent_glow"], bg=PALETTE["panel"]).pack(anchor="w")
        tk.Label(num2, text="02", font=self.STEP_NUM_FONT,
                 fg=PALETTE["accent"], bg=PALETTE["panel"]
                 ).pack(anchor="w", pady=(0, 6))
        tk.Label(num2, text="UPLOAD", font=FONT.HEADER,
                 fg=PALETTE["text"], bg=PALETTE["panel"]).pack(anchor="w")

        # Joint + ankle method (centre column, narrow)
        sel_col = tk.Frame(s2, bg=PALETTE["panel"])
        sel_col.grid(row=0, column=1, sticky="nsw", padx=(0, 18))
        tk.Label(sel_col, text="JOINT", font=FONT.SECTION,
                 fg=PALETTE["muted"], bg=PALETTE["panel"]
                 ).pack(anchor="w", pady=(0, 4))
        ttk.Radiobutton(sel_col, text="Ankle  (Foot + Shank)",
                        value="ankle", variable=self.pair_mode,
                        style="Card.TRadiobutton"
                        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(sel_col, text="Knee  (Shank + Thigh)",
                        value="knee", variable=self.pair_mode,
                        style="Card.TRadiobutton"
                        ).pack(anchor="w", pady=2)

        # Ankle-method sub-section (visible only when Ankle is chosen)
        self._home_ankle_method_frame = tk.Frame(sel_col, bg=PALETTE["panel"])
        self._home_ankle_method_frame.pack(anchor="w", fill=tk.X, pady=(10, 0))
        tk.Label(self._home_ankle_method_frame, text="ANKLE ANGLE METHOD",
                 font=FONT.SECTION, fg=PALETTE["muted"], bg=PALETTE["panel"]
                 ).pack(anchor="w", pady=(0, 4))
        ttk.Radiobutton(self._home_ankle_method_frame,
                        text="Functional DF/PF  (default)",
                        value="dfpf", variable=self.ankle_mode,
                        style="Card.TRadiobutton").pack(anchor="w", pady=2)
        ttk.Radiobutton(self._home_ankle_method_frame,
                        text="|SO(3)| relative rotation",
                        value="so3", variable=self.ankle_mode,
                        style="Card.TRadiobutton").pack(anchor="w", pady=2)
        # Manage visibility based on the joint pick
        self.pair_mode.trace_add("write",
                                  lambda *_: self._update_home_ankle_visible())
        self._update_home_ankle_visible()

        # Right-hand: instructions + button
        cta_col = tk.Frame(s2, bg=PALETTE["panel"])
        cta_col.grid(row=0, column=2, sticky="ne")
        tk.Label(cta_col,
                 text="The picker opens twice — first the distal sensor (with "
                      "accelerometer), then the proximal sensor.",
                 font=FONT.SMALL, fg=PALETTE["muted"], bg=PALETTE["panel"],
                 wraplength=300, justify="right"
                 ).pack(anchor="e", pady=(0, 12))
        ttk.Button(cta_col, text="Select CSV files",
                   style="Hero.TButton",
                   command=self.open_files).pack(anchor="e")

        # Loaded files (visible once a session is open)
        self._home_files_frame = tk.Frame(s2, bg=PALETTE["panel"])
        self._home_files_frame.grid(row=1, column=0, columnspan=3,
                                     sticky="ew", pady=(14, 0))
        self._refresh_home_files()

        # ------------------- Pack: Step 2 at the bottom, Step 1 fills above ----
        step2.pack(side=tk.BOTTOM, fill=tk.X)
        step1.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                   pady=(0, 14))

        # Defer figure rendering until after Tk has finished laying out the
        # cards — otherwise the FigureCanvasTkAgg widgets are packed into
        # zero-sized bodies and never resize properly.
        self.tab_home.after_idle(self._refresh_home_diagram)

    def _update_home_ankle_visible(self) -> None:
        if not hasattr(self, "_home_ankle_method_frame"):
            return
        if self.pair_mode.get() == "ankle":
            self._home_ankle_method_frame.pack(anchor="w", fill=tk.X, pady=(10, 0))
        else:
            self._home_ankle_method_frame.pack_forget()

    # Numbered placement instructions per joint pair.
    _PLACEMENT_INSTRUCTIONS = {
        "ankle": [
            ("Foot IMU",
             PALETTE["accent"],
             "Strap to the dorsum (top of the foot), just past the laces. "
             "Cable can run up the front of the ankle."),
            ("Shank IMU",
             PALETTE["accent2"],
             "Strap to the antero-medial mid-shank — the flat bone surface "
             "on the inside-front of your shin, mid-way up."),
        ],
        "knee": [
            ("Shank IMU",
             PALETTE["accent"],
             "Strap to the antero-medial mid-shank — flat bone on the "
             "inside-front of your shin, mid-way up."),
            ("Thigh IMU",
             PALETTE["accent2"],
             "Strap to the antero-lateral mid-thigh — outside-front of the "
             "thigh, mid-way between hip and knee."),
        ],
    }

    def _render_placement_instructions(self) -> None:
        holder = self._home_instructions_holder
        for w in holder.winfo_children():
            w.destroy()

        tk.Label(holder, text="HOW TO PLACE THEM",
                 font=FONT.SECTION, fg=PALETTE["accent"],
                 bg=PALETTE["panel"]).pack(anchor="w")
        tk.Label(holder,
                 text="Match each sensor to the highlighted spot on the leg.",
                 font=FONT.SMALL, fg=PALETTE["muted_strong"],
                 bg=PALETTE["panel"], wraplength=300, justify="left"
                 ).pack(anchor="w", pady=(4, 14))

        items = self._PLACEMENT_INSTRUCTIONS[self.pair_mode.get()]
        for i, (name, color, body) in enumerate(items, start=1):
            row = tk.Frame(holder, bg=PALETTE["panel"])
            row.pack(fill=tk.X, pady=(0, 12))

            num = tk.Canvas(row, width=28, height=28,
                            bg=PALETTE["panel"], highlightthickness=0)
            num.create_oval(2, 2, 26, 26, fill=color, outline="")
            num.create_text(14, 14, text=str(i), fill=PALETTE["bg"],
                            font=FONT.BODY_BOLD)
            num.pack(side=tk.LEFT, anchor="n", padx=(0, 10))

            text_col = tk.Frame(row, bg=PALETTE["panel"])
            text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(text_col, text=name,
                     font=FONT.BODY_BOLD, fg=color,
                     bg=PALETTE["panel"], anchor="w"
                     ).pack(anchor="w")
            tk.Label(text_col, text=body,
                     font=FONT.SMALL, fg=PALETTE["text_soft"],
                     bg=PALETTE["panel"], wraplength=250, justify="left"
                     ).pack(anchor="w", pady=(2, 0))

        # Footer note — orientation auto-calibrated.
        ttk.Separator(holder).pack(fill=tk.X, pady=(4, 10))
        tk.Label(holder,
                 text="Orientation is auto-calibrated on load — the exact "
                      "rotation of each sensor on the limb is not critical.",
                 font=FONT.SMALL, fg=PALETTE["muted"],
                 bg=PALETTE["panel"], wraplength=290, justify="left"
                 ).pack(anchor="w")

    def _refresh_home_diagram(self) -> None:
        """Re-render the Step-1 anatomical leg for the currently chosen joint."""
        if (getattr(self, "_home_diagram_holder", None) is None
                or getattr(self, "_home_instructions_holder", None) is None):
            return

        self._render_placement_instructions()

        for w in self._home_diagram_holder.winfo_children():
            w.destroy()
        fig3 = build_sensor_diagram(self.pair_mode.get())
        self._home_canvas = FigureCanvasTkAgg(fig3, master=self._home_diagram_holder)
        self._home_canvas.draw()
        self._home_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _refresh_home_files(self) -> None:
        if not hasattr(self, "_home_files_frame") or self._home_files_frame is None:
            return
        for w in self._home_files_frame.winfo_children():
            w.destroy()
        a = self._loaded_file_a.get()
        b = self._loaded_file_b.get()
        if not (a or b):
            return
        ttk.Separator(self._home_files_frame).pack(fill=tk.X, pady=(0, 8))
        line = tk.Frame(self._home_files_frame, bg=PALETTE["panel"])
        line.pack(fill=tk.X)
        tk.Label(line, text="LOADED  ", font=FONT.SECTION,
                 fg=PALETTE["accent"], bg=PALETTE["panel"]).pack(side=tk.LEFT)
        joined = "   ·   ".join(s for s in (a, b) if s)
        tk.Label(line, text=joined, font=FONT.SMALL,
                 fg=PALETTE["text_soft"], bg=PALETTE["panel"]
                 ).pack(side=tk.LEFT)

    # ------------------------------- Setup tab ------------------------------
    def _build_setup_tab(self) -> None:
        for w in self.tab_setup.winfo_children():
            w.destroy()

        wrap = tk.Frame(self.tab_setup, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=12)
        wrap.columnconfigure(0, weight=1)
        wrap.columnconfigure(1, weight=1)
        wrap.columnconfigure(2, weight=1)
        wrap.rowconfigure(0, weight=1)

        # Calibration
        cal_card = Card(wrap, padding=18)
        cal_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        SectionHeader(cal_card.body, "Calibration windows").pack(fill=tk.X)
        tk.Label(cal_card.body,
                 text="Time windows (seconds) used to estimate sensor "
                      "orientation. Auto-inferred on load — adjust if needed.",
                 font=FONT.SMALL, fg=PALETTE["muted"], bg=PALETTE["panel"],
                 wraplength=320, justify="left").pack(anchor="w", pady=(6, 12))

        self.entry_stand = self._labelled_entry(cal_card.body, "Standing  (e.g. 3,5)", "3,5")
        self.entry_flex  = self._labelled_entry(cal_card.body, "Flex  (optional)",     "")
        self.entry_zero  = self._labelled_entry(cal_card.body, "Ankle zero  (e.g. 3,8)","3,8")

        ttk.Checkbutton(cal_card.body, text="Zero ankle @ window",
                        variable=self.calibration_enabled
                        ).pack(anchor="w", pady=(8, 12))
        ttk.Button(cal_card.body, text="Apply windows", style="Accent.TButton",
                   command=self.apply_cal_windows).pack(anchor="w")

        # Stride selection
        sel_card = Card(wrap, padding=18)
        sel_card.grid(row=0, column=1, sticky="nsew", padx=6)
        SectionHeader(sel_card.body, "Stride selection").pack(fill=tk.X)
        tk.Label(sel_card.body,
                 text="Trim partial strides at the start or end of the trial, "
                      "or pick a starting heel-strike index.",
                 font=FONT.SMALL, fg=PALETTE["muted"], bg=PALETTE["panel"],
                 wraplength=320, justify="left").pack(anchor="w", pady=(6, 12))

        tk.Label(sel_card.body, text="Trim first / last", font=FONT.SMALL_BOLD,
                 fg=PALETTE["muted_strong"], bg=PALETTE["panel"]
                 ).pack(anchor="w", pady=(0, 4))
        spin_row = tk.Frame(sel_card.body, bg=PALETTE["panel"])
        spin_row.pack(anchor="w", fill=tk.X, pady=(0, 0))
        self.spin_trim_first = ttk.Spinbox(spin_row, from_=0, to=999, width=6)
        self.spin_trim_first.delete(0, tk.END); self.spin_trim_first.insert(0, "0")
        self.spin_trim_first.pack(side=tk.LEFT, padx=(0, 8))
        self.spin_trim_last = ttk.Spinbox(spin_row, from_=0, to=999, width=6)
        self.spin_trim_last.delete(0, tk.END); self.spin_trim_last.insert(0, "0")
        self.spin_trim_last.pack(side=tk.LEFT)

        ttk.Button(sel_card.body, text="Apply trimming", command=self.apply_trimming
                   ).pack(anchor="w", pady=(10, 16))

        tk.Label(sel_card.body, text="Start HS index", font=FONT.SMALL_BOLD,
                 fg=PALETTE["muted_strong"], bg=PALETTE["panel"]).pack(anchor="w")
        hs_row = tk.Frame(sel_card.body, bg=PALETTE["panel"])
        hs_row.pack(anchor="w", fill=tk.X, pady=(4, 0))
        self.start_idx_entry = ttk.Entry(hs_row, width=8)
        self.start_idx_entry.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(hs_row, text="Apply", command=self.apply_start_index
                   ).pack(side=tk.LEFT)
        ttk.Button(sel_card.body, text="Pick on Acceleration plot",
                   command=self.enable_pick_mode).pack(anchor="w", pady=(8, 0))

        # Visualisation + Export
        opt_card = Card(wrap, padding=18)
        opt_card.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        SectionHeader(opt_card.body, "Visualisation").pack(fill=tk.X)
        tk.Label(opt_card.body,
                 text="The ankle angle method is set on the Home tab when you "
                      "pick the joint pair.",
                 font=FONT.SMALL, fg=PALETTE["muted"], bg=PALETTE["panel"],
                 wraplength=300, justify="left").pack(anchor="w", pady=(6, 12))

        ttk.Checkbutton(opt_card.body,
                        text="Show healthy-adult reference band on overlay",
                        variable=self.show_normative,
                        command=self.refresh_views).pack(anchor="w")

        ttk.Separator(opt_card.body).pack(fill=tk.X, pady=(20, 14))
        SectionHeader(opt_card.body, "Export").pack(fill=tk.X)
        tk.Label(opt_card.body,
                 text="Write four CSVs (overlay, all strides, kept strides, metrics).",
                 font=FONT.SMALL, fg=PALETTE["muted"], bg=PALETTE["panel"],
                 wraplength=320, justify="left").pack(anchor="w", pady=(6, 10))
        ttk.Button(opt_card.body, text="Export CSV", style="Accent.TButton",
                   command=self.export_csv).pack(anchor="w")

    def _labelled_entry(self, parent, label: str, initial: str = "") -> ttk.Entry:
        bg = parent.cget("bg")
        tk.Label(parent, text=label, font=FONT.SMALL_BOLD,
                 fg=PALETTE["muted_strong"], bg=bg).pack(anchor="w", pady=(2, 2))
        ent = ttk.Entry(parent, width=20)
        ent.insert(0, initial)
        ent.pack(anchor="w", fill=tk.X, pady=(0, 8))
        return ent

    # ------------------------------- Empty dashboard ------------------------
    def _render_dashboard_placeholder(self) -> None:
        for w in self.tab_dash.winfo_children():
            w.destroy()
        wrap = tk.Frame(self.tab_dash, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=12)
        card = Card(wrap, padding=36)
        card.pack(fill=tk.BOTH, expand=True, padx=120, pady=80)
        tk.Label(card.body,
                 text="Load a session to populate the dashboard.",
                 font=FONT.HEADER, fg=PALETTE["accent_glow"],
                 bg=PALETTE["panel"]).pack(anchor="center", pady=(20, 6))
        tk.Label(card.body,
                 text="Open the Home tab → choose a joint → press Select CSV files.",
                 font=FONT.BODY, fg=PALETTE["muted"],
                 bg=PALETTE["panel"]).pack(anchor="center", pady=(0, 20))

    # ------------------------------- File UI --------------------------------
    def open_files(self) -> None:
        mode = self.pair_mode.get()
        self.start_peak_idx = None
        self.stride_keep = None

        try:
            if mode == "ankle":
                foot = filedialog.askopenfilename(
                    title="Select FOOT IMU CSV (accel + quat)",
                    filetypes=[("CSV Files", "*.csv")])
                if not foot:
                    return
                shank = filedialog.askopenfilename(
                    title="Select SHANK IMU CSV (quat)",
                    filetypes=[("CSV Files", "*.csv")])
                if not shank:
                    return
                base = process_files_ankle(
                    foot, shank,
                    ankle_mode=self.ankle_mode.get(),
                    stand_win=self.stand_win, flex_win=self.flex_win,
                    zero_win=self.ankle_zero_win,
                    zero_enabled=self.calibration_enabled.get(),
                )
                self._maybe_apply_inferred_window(base, fields=("stand", "zero"))
                self._raw = base["raw"]
                self._loaded_file_a.set(f"foot · {os.path.basename(foot)}")
                self._loaded_file_b.set(f"shank · {os.path.basename(shank)}")
                self._session_note.set(f"Ankle session  ·  {base.get('ankle_angle_note','')}")
            else:
                shank = filedialog.askopenfilename(
                    title="Select SHANK IMU CSV (accel + quat)",
                    filetypes=[("CSV Files", "*.csv")])
                if not shank:
                    return
                thigh = filedialog.askopenfilename(
                    title="Select THIGH IMU CSV (quat)",
                    filetypes=[("CSV Files", "*.csv")])
                if not thigh:
                    return
                base = process_files_knee(
                    shank, thigh,
                    stand_win=self.stand_win, flex_win=self.flex_win,
                )
                self._maybe_apply_inferred_window(base, fields=("stand",))
                self._raw = base["raw"]
                self._loaded_file_a.set(f"shank · {os.path.basename(shank)}")
                self._loaded_file_b.set(f"thigh · {os.path.basename(thigh)}")
                self._session_note.set(f"Knee session  ·  static cal {base.get('knee_baseline_note','?')}")

            self.last_base = base
            res = self._build_result()
            self._render_all(res)
            self._refresh_home_files()
            self.tabs.select("Dashboard")
            self.status_lbl.config(text="Files loaded and processed.")
        except Exception as e:
            self._session_note.set(f"Error: {e}")
            self.status_lbl.config(text="Error during processing.")
            messagebox.showerror("Processing error", str(e))
            raise

    def _maybe_apply_inferred_window(self, base, fields=("stand",)) -> None:
        zwin = base.get("inferred_zero_window")
        if not zwin:
            return
        if "stand" in fields and hasattr(self, "entry_stand"):
            self.stand_win = zwin
            self.entry_stand.delete(0, tk.END)
            self.entry_stand.insert(0, f"{zwin[0]:.1f},{zwin[1]:.1f}")
        if "zero" in fields and hasattr(self, "entry_zero"):
            self.ankle_zero_win = zwin
            self.entry_zero.delete(0, tk.END)
            self.entry_zero.insert(0, f"{zwin[0]:.1f},{zwin[1]:.1f}")

    # ------------------------------- Build / render -------------------------
    def _build_result(self):
        return build_outputs_from_pairs(
            self.last_base,
            start_peak_idx=self.start_peak_idx,
            stride_keep=self.stride_keep,
            trim_first=self.trim_first_n,
            trim_last=self.trim_last_n,
        )

    def _render_all(self, res) -> None:
        self.stride_keep = res["keep_mask"].copy()
        self.draw_dashboard(res)
        self.draw_accel_tab(res)
        self.draw_stride_tab(res)
        self.draw_all_strides_tab(res)

    def refresh_views(self) -> None:
        if self.last_base is None:
            return
        res = self._build_result()
        self.draw_dashboard(res)
        self.draw_accel_tab(res)
        self.draw_stride_tab(res)
        self.draw_all_strides_tab(res)

    # ------------------------------- Interactivity --------------------------
    def apply_start_index(self) -> None:
        if self.last_base is None:
            return
        try:
            s = int(self.start_idx_entry.get())
        except ValueError:
            messagebox.showwarning("Input", "Enter a non-negative integer HS index.")
            return
        self.start_peak_idx = max(0, s)
        self.status_lbl.config(text=f"Start HS set to {self.start_peak_idx}")
        self.refresh_views()

    def enable_pick_mode(self) -> None:
        if self.last_base is None:
            messagebox.showinfo("Pick on plot",
                                "Load a session first, then return here.")
            return
        self.tabs.select("Acceleration / HS")
        self.pick_mode = True
        self.pick_lbl.config(text="Click a peak to set start HS  ·  Esc to cancel")
        self.status_lbl.config(text="Pick start HS: click a peak; press Esc to cancel.")
        if self.canvas_accel is not None:
            if self._mpl_cid_click is None:
                self._mpl_cid_click = self.canvas_accel.mpl_connect(
                    "button_press_event", self._on_click_accel)
            if self._mpl_cid_key is None:
                self._mpl_cid_key = self.canvas_accel.mpl_connect(
                    "key_press_event", self._on_key)

    def _on_key(self, event):
        if event.key == "escape":
            self.pick_mode = False
            self.pick_lbl.config(text="")
            self.status_lbl.config(text="Pick cancelled.")

    def _on_click_accel(self, event):
        if not self.pick_mode or event.inaxes is None or self.last_base is None:
            return
        tf = self.last_base["tf"]
        hs = self.last_base["HS_idx"]
        if hs.size == 0:
            return
        j = int(np.argmin(np.abs(tf[hs] - event.xdata)))
        self.start_peak_idx = j
        self.start_idx_entry.delete(0, tk.END)
        self.start_idx_entry.insert(0, str(j))
        self.pick_mode = False
        self.pick_lbl.config(text=f"Start HS set to #{j}")
        self.status_lbl.config(text=f"Start HS set to {j}")
        self.refresh_views()

    def apply_trimming(self) -> None:
        try:
            self.trim_first_n = max(0, int(self.spin_trim_first.get()))
            self.trim_last_n = max(0, int(self.spin_trim_last.get()))
        except ValueError:
            messagebox.showwarning("Input", "Trim values must be non-negative integers.")
            return
        self.status_lbl.config(text=f"Trimming applied: first {self.trim_first_n}, last {self.trim_last_n}")
        self.refresh_views()

    def apply_cal_windows(self) -> None:
        try:
            stand = parse_range(self.entry_stand.get())
            flex = parse_range(self.entry_flex.get()) if self.entry_flex.get().strip() else None
            zero = parse_range(self.entry_zero.get())
        except ValueError as e:
            messagebox.showwarning("Calibration windows", f"Could not parse windows: {e}")
            return
        self.stand_win = stand
        self.flex_win = flex
        self.ankle_zero_win = zero
        self.status_lbl.config(text="Calibration windows applied.")
        self._recompute_angles()

    def _recompute_angles(self) -> None:
        if self.last_base is None or self._raw is None:
            return
        if self._raw.get("mode") == "ankle":
            angle, note = compute_ankle_angle(
                self._raw,
                mode=self.ankle_mode.get(),
                stand_win=self.stand_win, flex_win=self.flex_win,
                zero_win=self.ankle_zero_win,
                zero_enabled=self.calibration_enabled.get(),
            )
            self.last_base["angle_series"] = angle
            self.last_base["ankle_angle_note"] = note
            self._session_note.set(f"Ankle session  ·  {note}")
        else:
            knee, note = compute_knee_series(
                self._raw, stand_win=self.stand_win, flex_win=self.flex_win,
            )
            self.last_base["angle_series"] = knee
            self.last_base["knee_baseline_note"] = note
            self._session_note.set(f"Knee session  ·  static cal {note}")
        self.refresh_views()

    # ------------------------------- Drawing tabs ---------------------------
    def draw_accel_tab(self, res) -> None:
        for w in self.tab_accel.winfo_children():
            w.destroy()
        wrap = tk.Frame(self.tab_accel, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=12)
        card = Card(wrap, padding=10)
        card.pack(fill=tk.BOTH, expand=True)
        fig = build_acceleration_figure(res, start_peak_idx=self.start_peak_idx)
        self.canvas_accel = FigureCanvasTkAgg(fig, master=card.body)
        self.canvas_accel.draw()
        self.canvas_accel.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        if self.pick_mode:
            if self._mpl_cid_click is None:
                self._mpl_cid_click = self.canvas_accel.mpl_connect("button_press_event", self._on_click_accel)
            if self._mpl_cid_key is None:
                self._mpl_cid_key = self.canvas_accel.mpl_connect("key_press_event", self._on_key)

    def draw_stride_tab(self, res) -> None:
        for w in self.tab_stride.winfo_children():
            w.destroy()
        wrap = tk.Frame(self.tab_stride, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=12)
        card = Card(wrap, padding=10)
        card.pack(fill=tk.BOTH, expand=True)
        fig = build_overlay_figure(res, show_normative=self.show_normative.get())
        self.canvas_stride = FigureCanvasTkAgg(fig, master=card.body)
        self.canvas_stride.draw()
        self.canvas_stride.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def draw_all_strides_tab(self, res) -> None:
        for w in self.tab_allstrides.winfo_children():
            w.destroy()
        wrap = tk.Frame(self.tab_allstrides, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=12)

        ctrl_card = Card(wrap, padding=10)
        ctrl_card.pack(fill=tk.X, pady=(0, 8))
        ctrl = ctrl_card.body
        ttk.Button(ctrl, text="Keep all", style="Accent.TButton",
                   command=self._set_all_kept).pack(side=tk.LEFT, padx=(2, 6))
        ttk.Button(ctrl, text="Clear all", command=self._set_none_kept
                   ).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="Recompute from kept",
                   command=self._apply_kept_and_recompute).pack(side=tk.LEFT, padx=8)
        tk.Label(ctrl, text="Click a curve, or double-click a row, to keep / drop a stride.",
                 font=FONT.SMALL, fg=PALETTE["muted"],
                 bg=PALETTE["panel"]).pack(side=tk.LEFT, padx=14)

        body = tk.Frame(wrap, bg=PALETTE["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        plot_card = Card(body, padding=10)
        plot_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        legend_card = Card(body, padding=12)
        legend_card.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        legend_card.configure(width=240)

        fig, lines = build_all_strides_figure(res)
        self._stride_lines = lines
        self.canvas_allstrides = FigureCanvasTkAgg(fig, master=plot_card.body)
        self.canvas_allstrides.draw()
        self.canvas_allstrides.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        if self._allstrides_pick_cid is not None:
            try:
                self.canvas_allstrides.mpl_disconnect(self._allstrides_pick_cid)
            except Exception:
                pass
        self._allstrides_pick_cid = self.canvas_allstrides.mpl_connect(
            "pick_event", self._on_pick_stride)

        self._legend_build(legend_card.body, res.get("keep_mask", np.array([])))

    # ----------- All-strides handlers -----------
    def _on_pick_stride(self, event):
        if not hasattr(event, "artist"):
            return
        line = event.artist
        idx = line.get_gid()
        if idx is None or self.stride_keep is None:
            return
        try:
            i = int(idx)
        except ValueError:
            return
        if i < 0 or i >= len(self.stride_keep):
            return
        self.stride_keep[i] = ~bool(self.stride_keep[i])
        kept = self.stride_keep[i]
        self._style_stride_line(line, kept)
        if self.canvas_allstrides is not None:
            self.canvas_allstrides.draw()
        self._legend_update_row(i, kept)

    def _style_stride_line(self, line, kept) -> None:
        line.set_alpha(0.92 if kept else 0.18)
        line.set_linestyle("-" if kept else "--")
        line.set_linewidth(1.9 if kept else 1.0)
        line.set_color(PLOT_COLORS["stride"] if kept else PLOT_COLORS["stride_off"])

    def _set_all_kept(self) -> None:
        if self.stride_keep is None:
            return
        self.stride_keep[:] = True
        for ln in self._stride_lines:
            self._style_stride_line(ln, True)
        if self.canvas_allstrides is not None:
            self.canvas_allstrides.draw()
        self._legend_update_all()
        self.status_lbl.config(text="All strides kept.")

    def _set_none_kept(self) -> None:
        if self.stride_keep is None:
            return
        self.stride_keep[:] = False
        for ln in self._stride_lines:
            self._style_stride_line(ln, False)
        if self.canvas_allstrides is not None:
            self.canvas_allstrides.draw()
        self._legend_update_all()
        self.status_lbl.config(text="All strides cleared.")

    def _apply_kept_and_recompute(self) -> None:
        self.refresh_views()
        try:
            self.tabs.select("Gait-Cycle Overlay")
        except Exception:
            pass
        self.status_lbl.config(text="Mean / SD and metrics recomputed from kept strides.")

    # ----------- Legend (treeview) -----------
    def _legend_build(self, parent_frame: tk.Frame, keep_mask) -> None:
        for w in parent_frame.winfo_children():
            w.destroy()
        tk.Label(parent_frame, text="STRIDES", font=FONT.SECTION,
                 fg=PALETTE["muted"], bg=PALETTE["panel"]).pack(anchor="w")
        tk.Label(parent_frame, text="Double-click a row to toggle.",
                 font=FONT.SMALL, fg=PALETTE["muted"],
                 bg=PALETTE["panel"]).pack(anchor="w", pady=(2, 8))

        cols = ("Stride", "Keep")
        tree = ttk.Treeview(parent_frame, columns=cols, show="headings",
                            height=20, selectmode="extended")
        tree.heading("Stride", text="Index")
        tree.heading("Keep", text="Keep?")
        tree.column("Stride", width=70, anchor="center")
        tree.column("Keep", width=70, anchor="center")
        vsb = ttk.Scrollbar(parent_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        for i, kept in enumerate(keep_mask):
            iid = str(i)
            tree.insert("", "end", iid=iid, values=(i, "✓" if kept else "—"),
                        tags=("kept" if kept else "off",))
        tree.tag_configure("kept", background=PALETTE["panel"], foreground=PALETTE["text"])
        tree.tag_configure("off",  background=PALETTE["panel_alt"], foreground=PALETTE["muted"])

        tree.bind("<Double-1>", self._legend_on_double_click)
        tree.bind("<<TreeviewSelect>>", self._legend_on_select)
        self.legend_tree = tree

    def _legend_on_double_click(self, event):
        if self.legend_tree is None:
            return
        item = self.legend_tree.identify_row(event.y)
        if item == "":
            return
        i = int(item)
        self.stride_keep[i] = ~bool(self.stride_keep[i])
        kept = self.stride_keep[i]
        self._legend_update_row(i, kept)
        if 0 <= i < len(self._stride_lines):
            self._style_stride_line(self._stride_lines[i], kept)
            if self.canvas_allstrides is not None:
                self.canvas_allstrides.draw()

    def _legend_on_select(self, event):
        if self.legend_tree is None:
            return
        sel_idx = {int(s) for s in self.legend_tree.selection()}
        for i, ln in enumerate(self._stride_lines):
            kept = self.stride_keep[i] if self.stride_keep is not None else True
            ln.set_alpha(0.92 if kept else 0.18)
            ln.set_linestyle("-" if kept else "--")
            ln.set_linewidth(2.6 if i in sel_idx else (1.9 if kept else 1.0))
        if self.canvas_allstrides is not None:
            self.canvas_allstrides.draw()

    def _legend_update_row(self, i, kept) -> None:
        if self.legend_tree is None:
            return
        if self.legend_tree.exists(str(i)):
            self.legend_tree.set(str(i), "Keep", "✓" if kept else "—")
            self.legend_tree.item(str(i), tags=("kept" if kept else "off",))

    def _legend_update_all(self) -> None:
        if self.legend_tree is None or self.stride_keep is None:
            return
        for i, kept in enumerate(self.stride_keep):
            self._legend_update_row(i, kept)

    # ------------------------------- Dashboard ------------------------------
    def draw_dashboard(self, res) -> None:
        for w in self.tab_dash.winfo_children():
            w.destroy()

        n_total = len(res.get("pairs_all", res.get("pairs", [])))
        keep_mask = np.asarray(res.get("keep_mask", np.ones(n_total, dtype=bool)))
        n_kept = int(np.sum(keep_mask)) if n_total else 0

        stride_times = res.get("stride_times_s", np.array([]))
        mu_st = float(np.nanmean(stride_times)) if stride_times.size else np.nan
        sd_st = float(np.nanstd(stride_times)) if stride_times.size else np.nan
        cadence = res.get("cadence_spm", np.nan)
        cv_rob = res.get("cv_robust", np.nan)
        lengths = res.get("stride_lengths_m", np.array([]))
        mu_L = float(np.nanmean(lengths)) if lengths.size else np.nan
        sd_L = float(np.nanstd(lengths)) if lengths.size else np.nan
        speed = res.get("speed_ms", np.nan)

        wrap = tk.Frame(self.tab_dash, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=12)

        # Tile row — flip cards
        tiles_row = tk.Frame(wrap, bg=PALETTE["bg"])
        tiles_row.pack(fill=tk.X, pady=(0, 14))
        for c in range(5):
            tiles_row.columnconfigure(c, weight=1)

        def _accent_for(status):
            return {
                "normal":   PALETTE["ok"],
                "watch":    PALETTE["warn"],
                "atypical": PALETTE["danger"],
            }.get(status, PALETTE["accent"])

        def _make_tile(col: int, title: str, value: str, unit: str,
                       caption: str, status: str, ref, ref_value):
            tile = MetricTile(
                tiles_row, title, value, unit=unit, caption=caption,
                status=status, accent=_accent_for(status),
                ref_normal=ref.normal if ref else None,
                ref_watch=ref.watch if ref else None,
                ref_value=ref_value,
                description=DESCRIPTIONS.get(title, ""),
            )
            tile.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")

        ref = REFERENCE["cadence_spm"]
        _make_tile(0, "Cadence", _fmt(cadence, "{:.1f}"), ref.unit,
                   f"Kept strides {n_kept}/{n_total}" if n_total else "No strides",
                   ref.status(cadence), ref, cadence)

        ref = REFERENCE["stride_time_s"]
        _make_tile(1, "Stride Time",
                   f"{_fmt(mu_st, '{:.2f}')} ± {_fmt(sd_st, '{:.2f}')}", ref.unit,
                   "HS → HS, kept only",
                   ref.status(mu_st), ref, mu_st)

        # Stride length status with speed-context override.
        if res.get("mode", "ankle") == "ankle":
            sl_ref = REFERENCE["stride_length_m"]
            sp_ref = REFERENCE["walking_speed_ms"]
            sl_status = sl_ref.status(mu_L)
            sl_caption = "ZUPT-corrected XY integration"
            sl_low = np.isfinite(mu_L) and mu_L < sl_ref.normal[0]
            sp_low = np.isfinite(speed) and speed < sp_ref.normal[0]
            if sl_low and sp_low and sl_status != "normal":
                # Slow walking → shorter strides is expected, not atypical.
                sl_status = "normal"
                sl_caption = ("Short stride expected because of slow walking "
                              "speed — not necessarily atypical.")
            _make_tile(2, "Stride Length",
                       f"{_fmt(mu_L, '{:.2f}')} ± {_fmt(sd_L, '{:.2f}')}",
                       sl_ref.unit, sl_caption, sl_status, sl_ref, mu_L)
        else:
            tile = MetricTile(
                tiles_row, "Stride Length", "—", unit="",
                caption="Available for ankle sessions only",
                status="unknown", accent=PALETTE["muted"],
                description=DESCRIPTIONS.get("Stride Length", ""),
            )
            tile.grid(row=0, column=2, padx=6, pady=4, sticky="nsew")

        # Walking-speed status with slow-walking context.
        # If speed is below the normal band but still inside the acceptable
        # watch band, treat it as Normal — slow walking is a valid pace,
        # not necessarily a clinical concern. Add a caption that says so.
        sp_ref = REFERENCE["walking_speed_ms"]
        sp_status = sp_ref.status(speed)
        sp_caption = "Mean length ÷ stride time"
        if (np.isfinite(speed)
                and speed < sp_ref.normal[0]
                and speed >= sp_ref.watch[0]):
            sp_status = "normal"
            sp_caption = "Slower than typical — consistent with a slow walking pace."
        _make_tile(3, "Walking Speed", _fmt(speed, "{:.2f}"), sp_ref.unit,
                   sp_caption, sp_status, sp_ref, speed)

        ref = REFERENCE["cv_stride_time_pct"]
        _make_tile(4, "Gait Variability", _fmt(cv_rob, "{:.1f}"), ref.unit,
                   "Robust CV of stride time",
                   ref.status(cv_rob), ref, cv_rob)

        # Bottom: two plots, no interpretation panel
        bottom = tk.Frame(wrap, bg=PALETTE["bg"])
        bottom.pack(fill=tk.BOTH, expand=True)
        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=2)
        bottom.rowconfigure(0, weight=1)

        a = Card(bottom, padding=10)
        a.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        figA, _ = build_dashboard_overlay_figure(res)
        canvasA = FigureCanvasTkAgg(figA, master=a.body)
        canvasA.draw()
        canvasA.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        b = Card(bottom, padding=10)
        b.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        figB, _ = build_dashboard_histogram_figure(res)
        canvasB = FigureCanvasTkAgg(figB, master=b.body)
        canvasB.draw()
        canvasB.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ------------------------------- Export ---------------------------------
    def export_csv(self) -> None:
        if self.last_base is None:
            messagebox.showwarning("Export CSV",
                                   "No data to export yet. Load a session first.")
            return
        res = self._build_result()
        base = filedialog.asksaveasfilename(
            title="Save CSV export (base name)",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile="gait_export.csv",
        )
        if not base:
            return
        written = export_session(res, base)
        self.status_lbl.config(text="Exported: " + ", ".join(os.path.basename(p) for p in written))
        messagebox.showinfo("Export complete", "CSV export complete:\n  " + "\n  ".join(written))


def _fmt(x, fmt, na="—"):
    try:
        if x is None or not np.isfinite(x):
            return na
        return fmt.format(x)
    except Exception:
        return na
