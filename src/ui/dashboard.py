"""
dashboard.py — Statistics and charts window for PostureGuard.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PyQt5.QtCore    import Qt, QTimer
from PyQt5.QtGui     import QFont, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QGroupBox,
    QGridLayout, QFrame, QFileDialog, QMessageBox, QSizePolicy, QScrollArea,
)

try:
    import matplotlib
    matplotlib.use("Qt5Agg")
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from src.ui.styles import get_stylesheet, get_status_colour, get_theme_palette

logger = logging.getLogger(__name__)

# ── colour palette (matches main_window) ──────────────────────────────────
BG   = "#0d1117"
BG2  = "#161b22"
BG3  = "#0d1117"
BD   = "#30363d"
BD2  = "#21262d"
ACC  = "#58a6ff"
ACC2 = "#79c0ff"
GRN  = "#3fb950"
YEL  = "#d29922"
ORG  = "#db6d28"
RED  = "#f85149"
MUT  = "#8b949e"
TXT  = "#e6edf3"


def _mpl_axes_style(ax, bg=BG3):
    ax.set_facecolor(bg)
    for sp in ax.spines.values():
        sp.set_color(BD2)
    ax.tick_params(colors=MUT, labelsize=9)
    ax.yaxis.label.set_color(MUT)
    ax.xaxis.label.set_color(MUT)


class StatCard(QFrame):
    """Metric card with coloured left border."""
    def __init__(self, title: str, value: str = "--",
                 colour: str = ACC, icon: str = "", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._theme_palette = get_theme_palette("dark")
        self._colour = colour
        # colour accent bar painted via inner indicator
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(5)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self._tlbl = QLabel(title.upper())
        self._tlbl.setStyleSheet(
            f"color:{MUT}; font-size:10px; font-weight:800;"
            f" letter-spacing:1.4px; background:transparent; border:none;")
        dot = QLabel("●")
        dot.setStyleSheet(
            f"color:{colour}; font-size:11px; background:transparent; border:none;")
        top_row.addWidget(self._tlbl)
        top_row.addStretch()
        top_row.addWidget(dot)
        lay.addLayout(top_row)

        self._vlbl = QLabel(value)
        self._vlbl.setStyleSheet(
            f"color:{colour}; font-size:30px; font-weight:900;"
            f" background:transparent; border:none;")
        lay.addWidget(self._vlbl)

        # bottom accent line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(3)
        line.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {colour}, stop:1 transparent); border:none;")
        lay.addWidget(line)
        self._apply_theme("dark")

    def _apply_theme(self, theme: str):
        self._theme_palette = get_theme_palette(theme)
        self.setStyleSheet(
            f"QFrame {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self._theme_palette['card']}, stop:1 {self._theme_palette['bg2']});"
            f" border:1px solid {self._theme_palette['border']}; border-radius:16px; }}"
        )
        self._tlbl.setStyleSheet(
            f"color:{self._theme_palette['muted']}; font-size:10px; font-weight:800;"
            f" letter-spacing:1.4px; background:transparent; border:none;"
        )
        self._vlbl.setStyleSheet(
            f"color:{self._colour}; font-size:30px; font-weight:900;"
            f" background:transparent; border:none;"
        )

    def set_theme(self, theme: str):
        self._apply_theme(theme)

    def set_value(self, v: str):
        self._vlbl.setText(str(v))


class MplCanvas(FigureCanvas if HAS_MPL else QWidget):
    def __init__(self, parent=None, width=5, height=3.2):
        if not HAS_MPL:
            super().__init__(parent)
            return
        self._theme_palette = get_theme_palette("dark")
        self.fig = Figure(figsize=(width, height), facecolor=self._theme_palette["chart"])
        self.fig.subplots_adjust(left=0.16, right=0.98, top=0.82, bottom=0.28)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_theme(self, theme: str):
        if not HAS_MPL:
            return
        self._theme_palette = get_theme_palette(theme)
        self.fig.set_facecolor(self._theme_palette["chart"])
        self.fig.subplots_adjust(left=0.16, right=0.98, top=0.82, bottom=0.28)
        self.setStyleSheet(f"background:{self._theme_palette['chart']};")
        self.draw_idle()


class DashboardWindow(QMainWindow):
    def __init__(self, data_manager, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.theme        = theme
        self._days        = 7

        self.setWindowTitle("PostureGuard — Dashboard")
        self.setMinimumSize(780, 530)
        self.resize(960, 640)
        self.setStyleSheet(get_stylesheet(theme))
        self._build_ui()
        self._sync_theme_styles()
        self._load_data()

    # ──────────────────────────────────────────── layout ──────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._title_label = QLabel("Dashboard")
        self._title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self._subtitle_label = QLabel("Session history and posture analytics")
        title_col.addWidget(self._title_label)
        title_col.addWidget(self._subtitle_label)

        self._range_combo = QComboBox()
        self._range_combo.addItems(["Last 7 days", "Last 14 days", "Last 30 days"])
        self._range_combo.setFixedWidth(150)
        self._range_combo.setFixedHeight(32)
        self._range_combo.currentIndexChanged.connect(self._on_range_changed)

        self._refresh_btn = QPushButton("\u27f3  Refresh")
        self._refresh_btn.setObjectName("iconButton")
        self._refresh_btn.setFixedWidth(110)
        self._refresh_btn.setFixedHeight(32)
        self._refresh_btn.clicked.connect(self._load_data)

        self._export_btn = QPushButton("\u2b07  Export CSV")
        self._export_btn.setObjectName("iconButton")
        self._export_btn.setFixedWidth(130)
        self._export_btn.setFixedHeight(32)
        self._export_btn.clicked.connect(self._export_csv)

        hdr.addLayout(title_col)
        hdr.addStretch()
        hdr.addWidget(QLabel("Range:"))
        hdr.addWidget(self._range_combo)
        hdr.addSpacing(10)
        hdr.addWidget(self._refresh_btn)
        hdr.addWidget(self._export_btn)
        root.addLayout(hdr)

        cards = QHBoxLayout()
        cards.setSpacing(8)
        self._c_sessions = StatCard("Total Sessions", "--", ACC)
        self._c_score = StatCard("Avg Posture Score", "--", GRN)
        self._c_good_pct = StatCard("Good Posture %", "--", GRN)
        self._c_p_alert = StatCard("Posture Alerts", "--", ORG)
        self._c_d_alert = StatCard("Drowsy Alerts", "--", RED)
        for card in (self._c_sessions, self._c_score, self._c_good_pct, self._c_p_alert, self._c_d_alert):
            cards.addWidget(card)
        root.addLayout(cards)

        if HAS_MPL:
            row1 = QHBoxLayout()
            row1.setSpacing(10)

            g_posture = QGroupBox("  Daily Posture Quality (%)")
            g1 = QVBoxLayout(g_posture)
            g1.setContentsMargins(8, 6, 8, 8)
            self._cv_posture = MplCanvas(self, width=5.5, height=2.4)
            g1.addWidget(self._cv_posture)

            g_alerts = QGroupBox("  Daily Alerts")
            g2 = QVBoxLayout(g_alerts)
            g2.setContentsMargins(8, 6, 8, 8)
            self._cv_alerts = MplCanvas(self, width=5.5, height=2.4)
            g2.addWidget(self._cv_alerts)

            row1.addWidget(g_posture)
            row1.addWidget(g_alerts)
            root.addLayout(row1)

            row2 = QHBoxLayout()
            row2.setSpacing(10)

            g_pie = QGroupBox("  Posture Distribution")
            g3 = QVBoxLayout(g_pie)
            g3.setContentsMargins(8, 6, 8, 8)
            self._cv_pie = MplCanvas(self, width=4, height=2.4)
            g3.addWidget(self._cv_pie)

            g_neck = QGroupBox("  Avg Neck Angle per Day")
            g4 = QVBoxLayout(g_neck)
            g4.setContentsMargins(8, 6, 8, 8)
            self._cv_neck = MplCanvas(self, width=7, height=2.4)
            g4.addWidget(self._cv_neck)

            row2.addWidget(g_pie, stretch=3)
            row2.addWidget(g_neck, stretch=5)
            root.addLayout(row2)
        else:
            root.addWidget(QLabel("Install matplotlib (pip install matplotlib) to see charts."))

    def _sync_theme_styles(self):
        palette = get_theme_palette(self.theme)
        self._theme_palette = palette
        self.centralWidget().setStyleSheet(f"background:{palette['bg']};")
        self._range_combo.setStyleSheet(
            f"QComboBox {{ background:{palette['bg2']}; color:{palette['text']}; border:1px solid {palette['border']};"
            f" border-radius:12px; padding:8px 14px; font-weight:600; }}"
            f"QComboBox:hover {{ border-color:{palette['accent']}; }}"
            f"QComboBox QAbstractItemView {{ background:{palette['bg2']}; color:{palette['text']}; border:1px solid {palette['border']}; selection-background-color:{palette['accent']}; selection-color:#ffffff; }}"
        )
        self._refresh_btn.setStyleSheet(
            f"QPushButton {{ background:{palette['bg2']}; color:{palette['text']}; border:1px solid {palette['border']};"
            f" border-radius:12px; padding:6px 14px; font-weight:700; }}"
            f"QPushButton:hover {{ border-color:{palette['accent']}; color:{palette['accent']}; background:{palette['border2']}; }}"
            f"QPushButton:pressed {{ background:{palette['accent']}; color:#ffffff; }}"
        )
        self._export_btn.setStyleSheet(self._refresh_btn.styleSheet())
        for card in (self._c_sessions, self._c_score, self._c_good_pct, self._c_p_alert, self._c_d_alert):
            card.set_theme(self.theme)
        if HAS_MPL:
            for canvas in (self._cv_posture, self._cv_alerts, self._cv_pie, self._cv_neck):
                canvas.set_theme(self.theme)
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(
                f"QGroupBox {{ background:{palette['bg2']}; border:1px solid {palette['border']}; border-radius:14px; margin-top:10px; padding:14px 10px 10px 10px; }}"
                f"QGroupBox::title {{ color:{palette['muted']}; font-size:11px; font-weight:800; letter-spacing:0.9px; }}"
            )
        self._title_label.setStyleSheet(f"color:{palette['accent']}; letter-spacing:-0.6px; font-weight:800;")
        self._subtitle_label.setStyleSheet(f"color:{palette['muted']}; font-size:12px; font-weight:500;")

    # ──────────────────────────────────────────── data ────────────────────
    def _on_range_changed(self, idx: int):
        self._days = [7, 14, 30][idx]
        self._load_data()

    def _load_data(self):
        try:
            hist = self.data_manager.get_history(days=self._days)
        except Exception as e:
            logger.error("Dashboard load error: %s", e)
            return
        if not hist:
            return

        self._c_sessions.set_value(str(hist.get("sessions", 0)))
        avg  = hist.get("avg_posture_score", 0)
        self._c_score.set_value(f"{avg:.0f}%")
        self._c_good_pct.set_value(f"{hist.get('good_pct', 0):.0f}%")
        self._c_p_alert.set_value(str(hist.get("posture_alerts", 0)))
        self._c_d_alert.set_value(str(hist.get("drowsy_alerts", 0)))

        if HAS_MPL:
            self._draw_posture_line(hist)
            self._draw_alerts_bar(hist)
            self._draw_pie(hist)
            self._draw_neck_line(hist)

    # ──────────────────────────────────────────── charts ──────────────────
    def _draw_posture_line(self, hist: dict):
        cv  = self._cv_posture
        cv.fig.clear()
        ax  = cv.fig.add_subplot(111)
        _mpl_axes_style(ax)
        daily = hist.get("daily_scores", {})
        if daily:
            dates  = sorted(daily.keys())
            scores = [daily[d] for d in dates]
            lbls   = [d[-5:] for d in dates]
            xs     = range(len(lbls))
            # gradient fill
            ax.fill_between(xs, scores, alpha=0.18, color=ACC)
            ax.plot(xs, scores, color=ACC, linewidth=2.2,
                    marker="o", markersize=5, markerfacecolor=BG2,
                    markeredgecolor=ACC, markeredgewidth=2)
            # colour each point
            for i, s in enumerate(scores):
                c = GRN if s >= 75 else (YEL if s >= 50 else RED)
                ax.scatter(i, s, color=c, s=40, zorder=5)
            ax.set_xticks(list(xs))
            ax.set_xticklabels(lbls, rotation=30, ha="right")
            ax.set_ylim(0, 105)
            ax.axhline(75, color=GRN, linewidth=1, linestyle="--", alpha=0.4)
        ax.set_ylabel("Score (%)")
        ax.set_title("Posture Quality",
                     color=TXT, fontsize=10, fontweight="bold", pad=6)
        cv.fig.tight_layout(pad=0.6)
        cv.draw()

    def _draw_alerts_bar(self, hist: dict):
        cv  = self._cv_alerts
        cv.fig.clear()
        ax  = cv.fig.add_subplot(111)
        _mpl_axes_style(ax)
        dp  = hist.get("daily_posture_alerts", {})
        dd  = hist.get("daily_drowsy_alerts",  {})
        all_d = sorted(set(list(dp.keys()) + list(dd.keys())))
        if all_d:
            lbls  = [d[-5:] for d in all_d]
            xs    = np.arange(len(lbls))
            bw    = 0.38
            pv    = [dp.get(d, 0) for d in all_d]
            dv    = [dd.get(d, 0) for d in all_d]
            ax.bar(xs - bw/2, pv, bw, color=ORG, alpha=0.88,
                   label="Posture", edgecolor=BG2, linewidth=0.5)
            ax.bar(xs + bw/2, dv, bw, color=RED, alpha=0.88,
                   label="Drowsy",  edgecolor=BG2, linewidth=0.5)
            ax.set_xticks(xs)
            ax.set_xticklabels(lbls, rotation=30, ha="right")
            leg = ax.legend(facecolor=BD2, edgecolor=BD, labelcolor=TXT,
                            fontsize=9, framealpha=0.9)
        ax.set_ylabel("Count")
        ax.set_title("Daily Alerts",
                     color=TXT, fontsize=10, fontweight="bold", pad=6)
        cv.fig.tight_layout(pad=0.6)
        cv.draw()

    def _draw_pie(self, hist: dict):
        cv  = self._cv_pie
        cv.fig.clear()
        ax  = cv.fig.add_subplot(111)
        ax.set_facecolor(BG2)
        dist = hist.get("posture_distribution", {})
        labels_map = {
            "GOOD":         ("Good",         GRN),
            "SLOUCHING":    ("Slouching",     YEL),
            "FORWARD_HEAD": ("Forward Head",  ORG),
            "NECK_STRAIN":  ("Neck Strain",   RED),
            "UNKNOWN":      ("Unknown",       MUT),
        }
        vals, clrs, lbls = [], [], []
        for k, (name, clr) in labels_map.items():
            v = dist.get(k, 0)
            if v > 0:
                vals.append(v); clrs.append(clr); lbls.append(name)
        if vals:
            wedges, texts, pcts = ax.pie(
                vals, colors=clrs, autopct="%1.0f%%",
                startangle=90, pctdistance=0.78,
                wedgeprops=dict(width=0.55, edgecolor=BG2, linewidth=2),
            )
            for t in texts:   t.set_color(TXT); t.set_fontsize(0)
            for p in pcts:    p.set_color(BG); p.set_fontsize(9); p.set_fontweight("bold")
            ax.legend(wedges, lbls, loc="lower center", ncol=2,
                      facecolor=BD2, edgecolor=BD, labelcolor=TXT,
                      fontsize=8, bbox_to_anchor=(0.5, -0.12))
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    color=MUT, fontsize=11, transform=ax.transAxes)
        ax.set_title("Posture Distribution",
                     color=TXT, fontsize=10, fontweight="bold", pad=6)
        cv.fig.tight_layout(pad=0.6)
        cv.draw()

    def _draw_neck_line(self, hist: dict):
        cv  = self._cv_neck
        cv.fig.clear()
        ax  = cv.fig.add_subplot(111)
        _mpl_axes_style(ax)
        daily_neck = hist.get("daily_avg_neck_angle", {})
        if daily_neck:
            dates  = sorted(daily_neck.keys())
            angles = [daily_neck[d] for d in dates]
            lbls   = [d[-5:] for d in dates]
            xs     = range(len(lbls))
            ax.fill_between(xs, angles, alpha=0.15, color=ACC2)
            ax.plot(xs, angles, color=ACC2, linewidth=2.2,
                    marker="D", markersize=5, markerfacecolor=BG2,
                    markeredgecolor=ACC2, markeredgewidth=2)
            ax.axhline(155, color=GRN, linewidth=1.2, linestyle="--", alpha=0.5,
                       label="Good (≥155°)")
            ax.axhline(130, color=YEL, linewidth=1,   linestyle=":",  alpha=0.5,
                       label="Slouch (≥130°)")
            ax.set_xticks(list(xs))
            ax.set_xticklabels(lbls, rotation=30, ha="right")
            ax.set_ylim(80, 185)
            ax.legend(facecolor=BD2, edgecolor=BD, labelcolor=TXT,
                      fontsize=8, framealpha=0.9)
        else:
            ax.text(0.5, 0.5, "No angle data yet", ha="center", va="center",
                    color=MUT, fontsize=11, transform=ax.transAxes)
        ax.set_ylabel("Angle (°)")
        ax.set_title("Average Neck Angle per Day",
                     color=TXT, fontsize=10, fontweight="bold", pad=6)
        cv.fig.tight_layout(pad=0.6)
        cv.draw()

    # ──────────────────────────────────────────── export ──────────────────
    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Data",
            str(Path(__file__).resolve().parent.parent.parent / "postureguard_export.csv"),
            "CSV files (*.csv)"
        )
        if path:
            try:
                self.data_manager.export_data(path, "csv")
                QMessageBox.information(self, "Export", f"Data exported to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
