"""Main Tk application — clinical Apple-Health-inspired layout.

Components:

    +-------------+----------------------------------------------+
    |             |  HEADER (title + session note)               |
    |  SIDEBAR    +----------------------------------------------+
    |  controls   |  TABS  (Dashboard · Acceleration · Overlay   |
    |             |        · All Strides · Metrics)              |
    |             +----------------------------------------------+
    |             |  STATUS BAR                                  |
    +-------------+----------------------------------------------+
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..clinical_reference import REFERENCE, interpret_session
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
from .widgets import (
    FindingRow,
    MetricTile,
    RoundedCard,
    SidebarSection,
    StatusPill,
    install_styles,
)


SIDEBAR_WIDTH = 320


class IMUApp:
    """Top-level application controller."""

    APP_TITLE = "Gait IMU Analyzer"
    APP_SUBTITLE = "Clinical-grade ankle / knee gait analysis from inertial sensors"

    # ---- Lifecycle ---------------------------------------------------------
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(self.APP_TITLE)
        self.root.geometry("1560x1020")
        self.root.minsize(1320, 860)
        self.root.configure(bg=PALETTE["bg"])

        style_mpl()
        install_styles()

        # State
        self.calibration_enabled = tk.BooleanVar(value=True)
        self.pair_mode = tk.StringVar(value="knee")
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

        # Sidebar / header bindings
        self._loaded_file_a = tk.StringVar(value="—")
        self._loaded_file_b = tk.StringVar(value="—")
        self._session_note = tk.StringVar(value="No session loaded")

        self._build_layout()

    # ---- Layout ------------------------------------------------------------
    def _build_layout(self) -> None:
        outer = tk.Frame(self.root, bg=PALETTE["bg"])
        outer.pack(fill=tk.BOTH, expand=True)
        self._build_sidebar(outer)

        main = tk.Frame(outer, bg=PALETTE["bg"])
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_header(main)
        self._build_tabs(main)
        self._build_status_bar(main)

    # ---- Sidebar -----------------------------------------------------------
    def _build_sidebar(self, parent: tk.Frame) -> None:
        # Outer container so we can render a hairline border on the right edge
        wrap = tk.Frame(parent, bg=PALETTE["sidebar"], width=SIDEBAR_WIDTH)
        wrap.pack(side=tk.LEFT, fill=tk.Y)
        wrap.pack_propagate(False)
        # Right hairline
        rule = tk.Frame(wrap, bg=PALETTE["divider"], width=1)
        rule.pack(side=tk.RIGHT, fill=tk.Y)
        sb = tk.Frame(wrap, bg=PALETTE["sidebar"])
        sb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Brand block
        brand = tk.Frame(sb, bg=PALETTE["sidebar"])
        brand.pack(fill=tk.X, padx=20, pady=(22, 10))
        brand_row = tk.Frame(brand, bg=PALETTE["sidebar"])
        brand_row.pack(fill=tk.X)
        # Pseudo-logo: blue dot
        logo = tk.Canvas(brand_row, width=14, height=14, bg=PALETTE["sidebar"],
                         highlightthickness=0)
        logo.create_oval(1, 1, 13, 13, fill=PALETTE["accent"], outline=PALETTE["accent"])
        logo.pack(side=tk.LEFT, padx=(0, 8), pady=(2, 0))
        ttk.Label(brand_row, text="Gait IMU", style="Sidebar.TLabel",
                  font=("Helvetica Neue", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(brand, text="CLINICAL ANALYZER", style="SidebarHeader.TLabel"
                  ).pack(anchor="w", padx=(22, 0), pady=(2, 0))

        sep = tk.Frame(sb, bg=PALETTE["divider"], height=1)
        sep.pack(fill=tk.X, padx=20, pady=(8, 0))

        # ----- Joint -----
        SidebarSection(sb, "Joint").pack(fill=tk.X)
        joint_box = tk.Frame(sb, bg=PALETTE["sidebar"])
        joint_box.pack(fill=tk.X, padx=20, pady=(8, 4))
        ttk.Radiobutton(joint_box, text="Ankle  ·  Foot + Shank",
                        value="ankle", variable=self.pair_mode,
                        style="Sidebar.TRadiobutton").pack(anchor="w", pady=3)
        ttk.Radiobutton(joint_box, text="Knee  ·  Shank + Thigh",
                        value="knee", variable=self.pair_mode,
                        style="Sidebar.TRadiobutton").pack(anchor="w", pady=3)

        # ----- Ankle Method -----
        SidebarSection(sb, "Ankle Angle").pack(fill=tk.X)
        ankle_box = tk.Frame(sb, bg=PALETTE["sidebar"])
        ankle_box.pack(fill=tk.X, padx=20, pady=(8, 4))
        self.combo_ankle = ttk.Combobox(ankle_box, textvariable=self.ankle_mode,
                                        state="readonly", values=["dfpf", "so3"], width=14)
        self.combo_ankle.pack(anchor="w")
        ttk.Checkbutton(ankle_box, text="Zero ankle @ window",
                        variable=self.calibration_enabled,
                        style="Sidebar.TCheckbutton").pack(anchor="w", pady=(8, 0))

        # ----- Calibration windows -----
        SidebarSection(sb, "Calibration Windows").pack(fill=tk.X)
        cal = tk.Frame(sb, bg=PALETTE["sidebar"])
        cal.pack(fill=tk.X, padx=20, pady=(8, 4))

        for row, (label, attr_initial) in enumerate([
            ("Standing  (s)",          "3,5"),
            ("Flex  (s, optional)",    ""),
            ("Ankle zero  (s)",        "3,8"),
        ]):
            ttk.Label(cal, text=label, style="SidebarMuted.TLabel").grid(
                row=row * 2, column=0, sticky="w", pady=(4, 2))
            ent = ttk.Entry(cal, width=18, style="Sidebar.TEntry")
            ent.insert(0, attr_initial)
            ent.grid(row=row * 2 + 1, column=0, sticky="we", pady=(0, 6))
            if row == 0:
                self.entry_stand = ent
            elif row == 1:
                self.entry_flex = ent
            else:
                self.entry_zero = ent

        ttk.Button(cal, text="Apply windows", style="SidebarAccent.TButton",
                   command=self.apply_cal_windows).grid(
            row=10, column=0, sticky="we", pady=(6, 0))

        # ----- Stride selection -----
        SidebarSection(sb, "Stride Selection").pack(fill=tk.X)
        sel = tk.Frame(sb, bg=PALETTE["sidebar"])
        sel.pack(fill=tk.X, padx=20, pady=(8, 4))

        ttk.Label(sel, text="Trim first / last", style="SidebarMuted.TLabel"
                  ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(2, 4))
        self.spin_trim_first = ttk.Spinbox(sel, from_=0, to=999, width=6, style="Sidebar.TSpinbox")
        self.spin_trim_first.delete(0, tk.END); self.spin_trim_first.insert(0, "0")
        self.spin_trim_first.grid(row=1, column=0, sticky="w", padx=(0, 6))
        self.spin_trim_last = ttk.Spinbox(sel, from_=0, to=999, width=6, style="Sidebar.TSpinbox")
        self.spin_trim_last.delete(0, tk.END); self.spin_trim_last.insert(0, "0")
        self.spin_trim_last.grid(row=1, column=1, sticky="w")

        ttk.Button(sel, text="Apply trimming", style="Sidebar.TButton",
                   command=self.apply_trimming).grid(
            row=2, column=0, columnspan=2, sticky="we", pady=(8, 6))

        ttk.Label(sel, text="Start HS index", style="SidebarMuted.TLabel"
                  ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.start_idx_entry = ttk.Entry(sel, width=10, style="Sidebar.TEntry")
        self.start_idx_entry.grid(row=4, column=0, sticky="we", padx=(0, 6))
        ttk.Button(sel, text="Apply", style="Sidebar.TButton",
                   command=self.apply_start_index).grid(row=4, column=1, sticky="we")
        ttk.Button(sel, text="Pick on plot", style="Sidebar.TButton",
                   command=self.enable_pick_mode).grid(
            row=5, column=0, columnspan=2, sticky="we", pady=(6, 2))

        # ----- Visualization -----
        SidebarSection(sb, "Visualization").pack(fill=tk.X)
        viz = tk.Frame(sb, bg=PALETTE["sidebar"])
        viz.pack(fill=tk.X, padx=20, pady=(8, 4))
        ttk.Checkbutton(viz, text="Show healthy-adult reference",
                        variable=self.show_normative,
                        style="Sidebar.TCheckbutton",
                        command=self.refresh_views).pack(anchor="w")

        # ----- Session actions -----
        SidebarSection(sb, "Session").pack(fill=tk.X)
        actions = tk.Frame(sb, bg=PALETTE["sidebar"])
        actions.pack(fill=tk.X, padx=20, pady=(10, 18))
        ttk.Button(actions, text="Select CSVs", style="SidebarAccent.TButton",
                   command=self.open_files).pack(fill=tk.X)
        ttk.Button(actions, text="Export CSV", style="Sidebar.TButton",
                   command=self.export_csv).pack(fill=tk.X, pady=(8, 0))

        # Loaded files panel — pinned at the bottom
        files_frame = tk.Frame(sb, bg=PALETTE["sidebar_alt"])
        files_frame.pack(side=tk.BOTTOM, fill=tk.X)
        inner = tk.Frame(files_frame, bg=PALETTE["sidebar_alt"])
        inner.pack(fill=tk.X, padx=20, pady=14)
        ttk.Label(inner, text="LOADED", background=PALETTE["sidebar_alt"],
                  foreground=PALETTE["muted"], font=FONT.SECTION).pack(anchor="w")
        ttk.Label(inner, textvariable=self._loaded_file_a,
                  background=PALETTE["sidebar_alt"], foreground=PALETTE["text_soft"],
                  wraplength=260, font=FONT.SMALL).pack(anchor="w", pady=(4, 0))
        ttk.Label(inner, textvariable=self._loaded_file_b,
                  background=PALETTE["sidebar_alt"], foreground=PALETTE["text_soft"],
                  wraplength=260, font=FONT.SMALL).pack(anchor="w", pady=(2, 0))

    # ---- Header ------------------------------------------------------------
    def _build_header(self, parent: tk.Frame) -> None:
        header = tk.Frame(parent, bg=PALETTE["bg"])
        header.pack(fill=tk.X)
        inner = tk.Frame(header, bg=PALETTE["bg"])
        inner.pack(fill=tk.X, padx=28, pady=(22, 16))

        left = tk.Frame(inner, bg=PALETTE["bg"])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(left, text=self.APP_TITLE, style="AppHeader.TLabel").pack(anchor="w")
        ttk.Label(left, text=self.APP_SUBTITLE, style="AppSubheader.TLabel"
                  ).pack(anchor="w", pady=(2, 0))
        ttk.Label(left, textvariable=self._session_note, style="AppSubheader.TLabel"
                  ).pack(anchor="w", pady=(8, 0))

    # ---- Tabs --------------------------------------------------------------
    def _build_tabs(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=PALETTE["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=(8, 0))

        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill=tk.BOTH, expand=True)

        self.tab_dash = ttk.Frame(self.tabs, style="App.TFrame")
        self.tab_accel = ttk.Frame(self.tabs, style="App.TFrame")
        self.tab_stride = ttk.Frame(self.tabs, style="App.TFrame")
        self.tab_allstrides = ttk.Frame(self.tabs, style="App.TFrame")
        self.tab_metrics = ttk.Frame(self.tabs, style="App.TFrame")

        self.tabs.add(self.tab_dash,        text="  Dashboard  ")
        self.tabs.add(self.tab_accel,       text="  Acceleration / HS  ")
        self.tabs.add(self.tab_stride,      text="  Gait-Cycle Overlay  ")
        self.tabs.add(self.tab_allstrides,  text="  All Strides  ")
        self.tabs.add(self.tab_metrics,     text="  Metrics  ")

        self.canvas_accel = None
        self.canvas_stride = None
        self.canvas_allstrides = None

        # Metrics tab uses a styled card around a Text widget
        metrics_wrap = tk.Frame(self.tab_metrics, bg=PALETTE["bg"])
        metrics_wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=12)
        card = RoundedCard(metrics_wrap, radius=14, padding=18)
        card.pack(fill=tk.BOTH, expand=True)
        self.metrics_text = tk.Text(
            card.body, wrap="word",
            bg=PALETTE["panel"], fg=PALETTE["text"],
            font=FONT.MONO,
            relief="flat",
            padx=16, pady=12,
            highlightthickness=0,
            borderwidth=0,
        )
        self.metrics_text.pack(fill=tk.BOTH, expand=True)

        self._render_dashboard_placeholder()

    # ---- Status bar --------------------------------------------------------
    def _build_status_bar(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg=PALETTE["bg"], height=32)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        sep = tk.Frame(bar, bg=PALETTE["divider"], height=1)
        sep.pack(fill=tk.X, side=tk.TOP)

        self.status_lbl = ttk.Label(bar, text="Ready.", style="AppMuted.TLabel")
        self.status_lbl.pack(side=tk.LEFT, padx=20, pady=6)

        self.pick_lbl = ttk.Label(bar, text="", style="AppMuted.TLabel")
        self.pick_lbl.pack(side=tk.RIGHT, padx=20)

    # ---- Empty dashboard ---------------------------------------------------
    def _render_dashboard_placeholder(self) -> None:
        for w in self.tab_dash.winfo_children():
            w.destroy()
        wrap = tk.Frame(self.tab_dash, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=20)
        card = RoundedCard(wrap, radius=18, padding=36)
        card.pack(fill=tk.BOTH, expand=True, padx=120, pady=80)
        msg = ttk.Label(
            card.body,
            text=("Load a session to populate the dashboard.\n"
                  "Use the sidebar  ·  Session  ·  Select CSVs."),
            style="Muted.TLabel",
            justify="center",
            font=("Helvetica Neue", 13),
        )
        msg.pack(expand=True, pady=80)

    # ---- File UI -----------------------------------------------------------
    def open_files(self) -> None:
        mode = self.pair_mode.get()
        self.start_peak_idx = None
        self.stride_keep = None

        try:
            if mode == "ankle":
                foot = filedialog.askopenfilename(title="Select FOOT IMU CSV (accel + quat)",
                                                  filetypes=[("CSV Files", "*.csv")])
                if not foot:
                    return
                shank = filedialog.askopenfilename(title="Select SHANK IMU CSV (quat)",
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
                shank = filedialog.askopenfilename(title="Select SHANK IMU CSV (accel + quat)",
                                                   filetypes=[("CSV Files", "*.csv")])
                if not shank:
                    return
                thigh = filedialog.askopenfilename(title="Select THIGH IMU CSV (quat)",
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
        if "stand" in fields:
            self.stand_win = zwin
            self.entry_stand.delete(0, tk.END)
            self.entry_stand.insert(0, f"{zwin[0]:.1f},{zwin[1]:.1f}")
        if "zero" in fields:
            self.ankle_zero_win = zwin
            self.entry_zero.delete(0, tk.END)
            self.entry_zero.insert(0, f"{zwin[0]:.1f},{zwin[1]:.1f}")

    # ---- Build / render ----------------------------------------------------
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
        self.fill_metrics_tab(res)

    def refresh_views(self) -> None:
        if self.last_base is None:
            return
        res = self._build_result()
        self.draw_dashboard(res)
        self.draw_accel_tab(res)
        self.draw_stride_tab(res)
        self.draw_all_strides_tab(res)
        self.fill_metrics_tab(res)

    # ---- Interactivity -----------------------------------------------------
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
            return
        self.pick_mode = True
        self.pick_lbl.config(text="Click a peak to set start HS  ·  Esc to cancel")
        self.status_lbl.config(text="Pick start HS: click a peak; press Esc to cancel.")
        if self.canvas_accel is not None:
            if self._mpl_cid_click is None:
                self._mpl_cid_click = self.canvas_accel.mpl_connect("button_press_event", self._on_click_accel)
            if self._mpl_cid_key is None:
                self._mpl_cid_key = self.canvas_accel.mpl_connect("key_press_event", self._on_key)

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

    # ---- Drawing tabs ------------------------------------------------------
    def draw_accel_tab(self, res) -> None:
        for w in self.tab_accel.winfo_children():
            w.destroy()
        wrap = tk.Frame(self.tab_accel, bg=PALETTE["bg"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=12)
        card = RoundedCard(wrap, radius=14, padding=14)
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
        card = RoundedCard(wrap, radius=14, padding=14)
        card.pack(fill=tk.BOTH, expand=True)

        fig = build_overlay_figure(res, show_normative=self.show_normative.get())
        self.canvas_stride = FigureCanvasTkAgg(fig, master=card.body)
        self.canvas_stride.draw()
        self.canvas_stride.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def draw_all_strides_tab(self, res) -> None:
        for w in self.tab_allstrides.winfo_children():
            w.destroy()

        # Top control bar
        ctrl_card = RoundedCard(self.tab_allstrides, radius=12, padding=10,
                                outer_bg=PALETTE["bg"])
        ctrl_card.pack(fill=tk.X, padx=8, pady=(12, 6))
        ctrl = ctrl_card.body
        ttk.Button(ctrl, text="Keep all", style="Accent.TButton",
                   command=self._set_all_kept).pack(side=tk.LEFT, padx=(2, 6))
        ttk.Button(ctrl, text="Clear all",
                   command=self._set_none_kept).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="Recompute from kept",
                   command=self._apply_kept_and_recompute).pack(side=tk.LEFT, padx=8)
        ttk.Label(ctrl, text="Click a curve, or double-click a row, to keep / drop a stride.",
                  style="Muted.TLabel").pack(side=tk.LEFT, padx=14)

        body = tk.Frame(self.tab_allstrides, bg=PALETTE["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 12))
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        plot_card = RoundedCard(body, radius=14, padding=12, outer_bg=PALETTE["bg"])
        plot_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        legend_card = RoundedCard(body, radius=14, padding=12, outer_bg=PALETTE["bg"])
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
        self._allstrides_pick_cid = self.canvas_allstrides.mpl_connect("pick_event", self._on_pick_stride)

        self._legend_build(legend_card.body, res.get("keep_mask", np.array([])))

    # ---- All-strides handlers ----
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
        self.status_lbl.config(text="All strides cleared (none kept).")

    def _apply_kept_and_recompute(self) -> None:
        self.refresh_views()
        try:
            self.tabs.select(self.tab_stride)
        except Exception:
            pass
        self.status_lbl.config(text="Mean / SD and metrics recomputed from kept strides.")

    # ---- Legend (treeview) ----
    def _legend_build(self, parent_frame: tk.Frame, keep_mask) -> None:
        for w in parent_frame.winfo_children():
            w.destroy()

        ttk.Label(parent_frame, text="STRIDES", style="CardTitle.TLabel"
                  ).pack(anchor="w")
        ttk.Label(parent_frame, text="Double-click a row to toggle.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 8))

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
            tag = "kept" if kept else "off"
            tree.insert("", "end", iid=iid, values=(i, "✓" if kept else "—"), tags=(tag,))
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

    # ---- Metrics text ------------------------------------------------------
    def fill_metrics_tab(self, res) -> None:
        self.metrics_text.delete("1.0", tk.END)
        n_kept = res["stride_times_s"].size
        total = len(res.get("pairs_all", res.get("pairs", [])))
        kept_now = int(np.sum(res.get("keep_mask", np.ones(total, dtype=bool)))) if total else 0

        msg = []
        msg.append(f"PAIR MODE         :  {res.get('mode','ankle').upper()}")
        if res.get("mode") == "knee" and res.get("knee_baseline_note"):
            msg.append(f"KNEE STATIC CAL   :  {res['knee_baseline_note']}")
        if res.get("mode") == "ankle" and res.get("ankle_angle_note"):
            msg.append(f"ANKLE METHOD      :  {res['ankle_angle_note']}")
        if self.start_peak_idx is not None:
            msg.append(f"START HS INDEX    :  {self.start_peak_idx}")
        msg.append(f"KEPT  /  TOTAL    :  {kept_now} / {total}")
        msg.append("")

        if n_kept:
            mu = float(np.nanmean(res["stride_times_s"]))
            sd = float(np.nanstd(res["stride_times_s"]))
            msg.append(f"Stride time         : {mu:.3f} ± {sd:.3f} s")
            if np.isfinite(res.get("cadence_spm", np.nan)):
                msg.append(f"Cadence             : {res['cadence_spm']:.1f} steps/min")
        if res.get("stride_lengths_m", np.array([])).size:
            muL = float(np.nanmean(res["stride_lengths_m"]))
            sdL = float(np.nanstd(res["stride_lengths_m"]))
            msg.append(f"Stride length       : {muL:.3f} ± {sdL:.3f} m")
            if np.isfinite(res.get("speed_ms", np.nan)):
                msg.append(f"Walking speed       : {res['speed_ms']:.3f} m/s")
        if np.isfinite(res.get("cv_robust", np.nan)):
            msg.append(f"Variability (rob)   : {res['cv_robust']:.2f} %")
        if np.isfinite(res.get("cv_classic", np.nan)):
            msg.append(f"Variability (cls)   : {res['cv_classic']:.2f} %")

        msg.append("")
        msg.append(f"HS detected raw     : {len(res['HS_idx_raw'])}")
        msg.append(f"HS kept (filtered)  : {len(res['HS_idx'])}")
        msg.append(f"Stride segments     : {len(res['pairs'])}")

        if kept_now == 0 and total > 0:
            msg.append("\n⚠  No strides kept — toggle some on the All Strides tab or press Keep all.")

        self.metrics_text.insert(tk.END, "\n".join(msg))

    # ---- Dashboard ---------------------------------------------------------
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
        wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=8)

        # ---- Headline cards ----
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

        # Cadence
        ref = REFERENCE["cadence_spm"]
        s = ref.status(cadence)
        MetricTile(
            tiles_row, "Cadence",
            _fmt(cadence, "{:.1f}"), unit=ref.unit,
            caption=f"Kept strides {n_kept}/{n_total}" if n_total else "No strides",
            status=s, accent=_accent_for(s),
            ref_normal=ref.normal, ref_watch=ref.watch, ref_value=cadence,
        ).grid(row=0, column=0, padx=6, pady=4, sticky="nsew")

        # Stride time
        ref = REFERENCE["stride_time_s"]
        s = ref.status(mu_st)
        MetricTile(
            tiles_row, "Stride Time",
            f"{_fmt(mu_st, '{:.2f}')} ± {_fmt(sd_st, '{:.2f}')}", unit=ref.unit,
            caption="HS → HS, kept only",
            status=s, accent=_accent_for(s),
            ref_normal=ref.normal, ref_watch=ref.watch, ref_value=mu_st,
        ).grid(row=0, column=1, padx=6, pady=4, sticky="nsew")

        # Stride length (ankle only)
        if res.get("mode", "ankle") == "ankle":
            ref = REFERENCE["stride_length_m"]
            s = ref.status(mu_L)
            MetricTile(
                tiles_row, "Stride Length",
                f"{_fmt(mu_L, '{:.2f}')} ± {_fmt(sd_L, '{:.2f}')}", unit=ref.unit,
                caption="ZUPT-corrected XY integration",
                status=s, accent=_accent_for(s),
                ref_normal=ref.normal, ref_watch=ref.watch, ref_value=mu_L,
            ).grid(row=0, column=2, padx=6, pady=4, sticky="nsew")
        else:
            MetricTile(
                tiles_row, "Stride Length", "—", unit="",
                caption="Available for ankle pipeline",
                status="unknown", accent=PALETTE["muted"],
            ).grid(row=0, column=2, padx=6, pady=4, sticky="nsew")

        # Walking speed
        ref = REFERENCE["walking_speed_ms"]
        s = ref.status(speed)
        MetricTile(
            tiles_row, "Walking Speed",
            _fmt(speed, "{:.2f}"), unit=ref.unit,
            caption="Mean length ÷ stride time",
            status=s, accent=_accent_for(s),
            ref_normal=ref.normal, ref_watch=ref.watch, ref_value=speed,
        ).grid(row=0, column=3, padx=6, pady=4, sticky="nsew")

        # Variability
        ref = REFERENCE["cv_stride_time_pct"]
        s = ref.status(cv_rob)
        MetricTile(
            tiles_row, "Gait Variability",
            _fmt(cv_rob, "{:.1f}"), unit=ref.unit,
            caption="Robust CV of stride time",
            status=s, accent=_accent_for(s),
            ref_normal=ref.normal, ref_watch=ref.watch, ref_value=cv_rob,
        ).grid(row=0, column=4, padx=6, pady=4, sticky="nsew")

        # ---- Bottom: plots + interpretation ----
        bottom = tk.Frame(wrap, bg=PALETTE["bg"])
        bottom.pack(fill=tk.BOTH, expand=True)
        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=2)
        bottom.columnconfigure(2, weight=3)
        bottom.rowconfigure(0, weight=1)

        # Plot A — overlay
        a = RoundedCard(bottom, radius=14, padding=12, outer_bg=PALETTE["bg"])
        a.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        figA = build_dashboard_overlay_figure(res)
        canvasA = FigureCanvasTkAgg(figA, master=a.body)
        canvasA.draw()
        canvasA.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Plot B — stride-time histogram
        b = RoundedCard(bottom, radius=14, padding=12, outer_bg=PALETTE["bg"])
        b.grid(row=0, column=1, sticky="nsew", padx=6)
        figB = build_dashboard_histogram_figure(res)
        canvasB = FigureCanvasTkAgg(figB, master=b.body)
        canvasB.draw()
        canvasB.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Interpretation panel
        c = RoundedCard(bottom, radius=14, padding=18, outer_bg=PALETTE["bg"])
        c.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self._render_interpretation(c.body, res, n_kept, n_total)

    def _render_interpretation(self, parent, res, n_kept, n_total) -> None:
        head = tk.Frame(parent, bg=PALETTE["panel"])
        head.pack(fill=tk.X)
        ttk.Label(head, text="CLINICAL INTERPRETATION",
                  style="CardTitle.TLabel").pack(side=tk.LEFT)

        # Overall status pill
        findings = interpret_session(res)
        worst = "ok"
        for f in findings:
            if f.severity == "atypical":
                worst = "atypical"; break
            if f.severity == "watch" and worst != "atypical":
                worst = "watch"
            if f.severity == "info" and worst not in ("atypical", "watch"):
                worst = "info"
        StatusPill(head, status=worst,
                   text={"ok": "Within range", "watch": "Review",
                         "atypical": "Atypical", "info": "Info"}.get(worst, "—")
                   ).pack(side=tk.RIGHT)

        ttk.Label(parent,
                  text="Plain-language findings using healthy-adult level-walking references.",
                  style="Muted.TLabel", wraplength=420, justify="left"
                  ).pack(anchor="w", pady=(8, 10))

        # Findings list (scrollable)
        list_wrap = tk.Frame(parent, bg=PALETTE["panel"])
        list_wrap.pack(fill=tk.BOTH, expand=True)
        for i, f in enumerate(findings):
            row = FindingRow(list_wrap, f.severity, f.headline, f.detail)
            row.pack(fill=tk.X, pady=(0 if i == 0 else 4, 0))

        # Footer note
        foot = tk.Frame(parent, bg=PALETTE["panel"])
        foot.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(foot, text="Reference cues only — not diagnostic.",
                  style="Muted.TLabel").pack(side=tk.LEFT)

    # ---- Export ------------------------------------------------------------
    def export_csv(self) -> None:
        if self.last_base is None:
            messagebox.showwarning("Export CSV",
                                   "No data to export yet. Load and process a session first.")
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
