"""
main_window.py — Primary application window for PostureGuard.
"""

import logging
import math
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PyQt5.QtCore  import Qt, QTimer, QRectF, pyqtSlot
from PyQt5.QtGui   import (QImage, QPixmap, QIcon, QFont, QPainter,
                            QPainterPath, QColor, QPen, QLinearGradient)
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QGroupBox, QProgressBar,
    QStatusBar, QAction, QMessageBox, QSizePolicy,
    QFrame, QGridLayout, QListWidget, QListWidgetItem,
    QScrollArea, QDialog,
)

try:
    import matplotlib
    matplotlib.use("Qt5Agg")
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from src.camera_handler   import CameraHandler
from src.posture_detector import PostureDetector
from src.eye_monitor      import EyeMonitor
from src.alert_system     import AlertSystem
from src.session_tracker  import SessionTracker
from src.ui.styles        import get_stylesheet, get_status_colour

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── colour palette ─────────────────────────────────────────────────────
BG        = "#0d1117"
BG2       = "#161b22"
BG3       = "#0d1117"
BORDER    = "#30363d"
ACCENT    = "#58a6ff"
ACCENT2   = "#79c0ff"
TEXT      = "#e6edf3"
MUTED     = "#8b949e"
GREEN     = "#3fb950"
YELLOW    = "#d29922"
ORANGE    = "#db6d28"
RED       = "#f85149"


# ── helpers ────────────────────────────────────────────────────────────────

def _hex(h: str) -> QColor:
    return QColor(h)


# ── Animated status badge ─────────────────────────────────────────────────

class StatusBadge(QLabel):
    def __init__(self, text="--", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(0)
        self.setFixedHeight(30)
        self._apply(MUTED)

    def set_status(self, text: str, hex_colour: str):
        self.setText(text)
        self._apply(hex_colour)

    def _apply(self, bg: str):
        self.setStyleSheet(
            f"background: {bg}22; color: {bg}; border: 2px solid {bg};"
            f" border-radius: 12px;"
            f" font-weight: 800; font-size: 12px; padding: 4px 12px;"
            f" letter-spacing: 1px;"
        )


# ── Score ring (QPainter arc) ─────────────────────────────────────────────

class ScoreRing(QWidget):
    """Circular progress ring showing posture score 0-100."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._score   = 0
        self._colour  = ACCENT
        self.setFixedSize(88, 88)

    def set_score(self, score: int):
        self._score  = max(0, min(100, score))
        # colour by score
        if self._score >= 75:   self._colour = GREEN
        elif self._score >= 50: self._colour = YELLOW
        elif self._score >= 25: self._colour = ORANGE
        else:                   self._colour = RED
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h   = self.width(), self.height()
        margin = 10
        rect   = QRectF(margin, margin, w - 2*margin, h - 2*margin)
        # background ring
        pen = QPen(QColor(BORDER), 12, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)
        # score arc
        pen.setColor(QColor(self._colour))
        pen.setWidth(12)
        p.setPen(pen)
        span = int(self._score / 100 * 360 * 16)
        p.drawArc(rect, 90 * 16, -span)
        # centre text
        p.setPen(QColor(TEXT))
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, f"{self._score}%")


# ── Live neck-angle mini chart ────────────────────────────────────────────

class NeckChart(QWidget):
    """Tiny sparkline showing last N neck angle readings."""

    MAX_POINTS = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: deque = deque(maxlen=self.MAX_POINTS)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def push(self, angle: float):
        self._data.append(angle)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # background
        p.fillRect(0, 0, w, h, QColor(BG3))

        points = list(self._data)
        if len(points) < 2:
            p.setPen(QColor(MUTED))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(0, 0, w, h, Qt.AlignCenter, "Waiting for data...")
            return

        mn, mx = 90, 180       # expected range
        pad = 6

        def _y(v):
            return pad + (1 - (v - mn) / max(mx - mn, 1)) * (h - 2*pad)

        x_step = (w - 2*pad) / max(len(points) - 1, 1)

        # threshold line at 155° (GOOD boundary)
        ty = _y(155)
        p.setPen(QPen(QColor(40, 80, 40), 1, Qt.DashLine))
        p.drawLine(pad, int(ty), w - pad, int(ty))

        # gradient fill under line
        path = QPainterPath()
        path.moveTo(pad, h)
        for i, v in enumerate(points):
            x = pad + i * x_step
            path.lineTo(x, _y(v))
        path.lineTo(pad + (len(points)-1)*x_step, h)
        path.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(88, 166, 255, 80))
        grad.setColorAt(1.0, QColor(88, 166, 255,  0))
        p.fillPath(path, grad)

        # line
        pen = QPen(QColor(ACCENT), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        for i in range(1, len(points)):
            x1 = pad + (i-1) * x_step
            x2 = pad + i     * x_step
            p.drawLine(int(x1), int(_y(points[i-1])),
                       int(x2), int(_y(points[i])))

        # last value label
        last = points[-1]
        clr  = GREEN if last >= 155 else (YELLOW if last >= 130 else RED)
        p.setPen(QColor(clr))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.drawText(w - 56, 2, 54, 16, Qt.AlignRight | Qt.AlignVCenter,
                   f"{last:.0f}°")


# ── Metric card ───────────────────────────────────────────────────────────

class MetricCard(QFrame):
    def __init__(self, label: str, value: str = "--",
                 accent: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(44)
        self.setStyleSheet(
            f"QFrame {{ background: {BG2}; border: 1px solid {BORDER};"
            f" border-left: 3px solid {accent}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(0)
        self._lbl = QLabel(label.upper())
        self._lbl.setStyleSheet(
            f"color:{MUTED}; font-size:9px; font-weight:700; letter-spacing:1px;"
            f" border:none; background:transparent;"
        )
        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color:{accent}; font-size:15px; font-weight:800;"
            f" border:none; background:transparent;"
        )
        lay.addWidget(self._lbl)
        lay.addWidget(self._val)

    def set_value(self, v: str):
        self._val.setText(str(v))


# ── Main window ───────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, config: dict, data_manager, parent=None):
        super().__init__(parent)
        self.config       = config
        self.data_manager = data_manager
        self.theme        = data_manager.get_settings().get("theme", "dark")
        self._session_id  = None
        self._running     = False
        self._last_posture_data: dict = {}
        self._last_eye_data   : dict  = {}

        self.camera_handler   = CameraHandler(config)
        self.posture_detector = PostureDetector(config)
        self.eye_monitor      = EyeMonitor(config)
        self.alert_system     = AlertSystem(config)
        self.session_tracker  = SessionTracker(config, data_manager)

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._apply_theme()
        self._update_buttons_state()

    # ──────────────────────────────────────────── UI build ────────────────

    def _build_ui(self):
        self.setWindowTitle("PostureGuard — AI Posture & Drowsiness Monitor")
        self.setMinimumSize(860, 600)
        self.resize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Slim header bar ───────────────────────────────────────────────
        header_bar = QWidget()
        header_bar.setFixedHeight(48)
        header_bar.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hb = QHBoxLayout(header_bar)
        hb.setContentsMargins(16, 0, 16, 0)
        app_name = QLabel("PostureGuard")
        app_name.setStyleSheet(
            f"color:{ACCENT}; font-size:17px; font-weight:800; letter-spacing:-0.5px;")
        app_sub = QLabel("  —  AI Posture & Drowsiness Monitor")
        app_sub.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        self._header_status = QLabel("● Idle")
        self._header_status.setStyleSheet(
            f"color:{MUTED}; font-size:12px; font-weight:600;"
            f" background:#21262d; border:1px solid {BORDER};"
            f" border-radius:10px; padding:4px 14px;")
        hb.addWidget(app_name)
        hb.addWidget(app_sub)
        hb.addStretch()
        hb.addWidget(self._header_status)
        outer.addWidget(header_bar)

        # ── Body = sidebar + main content ─────────────────────────────
        body = QWidget()
        outer.addWidget(body, stretch=1)
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        # ─── Left sidebar ──────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(90)
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet(
            f"QWidget#sidebar {{ background:{BG2}; border-right:1px solid {BORDER}; }}")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(8, 16, 8, 16)
        sb_lay.setSpacing(6)

        def _nav(icon: str, label: str, tip: str) -> QPushButton:
            btn = QPushButton()
            btn.setObjectName("sideNavBtn")
            btn.setFixedSize(74, 64)
            btn.setToolTip(tip)
            bl = QVBoxLayout(btn)
            bl.setContentsMargins(0, 6, 0, 6)
            bl.setSpacing(3)
            il = QLabel(icon)
            il.setAlignment(Qt.AlignCenter)
            il.setStyleSheet("font-size:22px; background:transparent; border:none;")
            tl = QLabel(label)
            tl.setAlignment(Qt.AlignCenter)
            tl.setStyleSheet(
                f"font-size:10px; color:{MUTED}; background:transparent; border:none;"
                f" font-weight:600;")
            bl.addWidget(il)
            bl.addWidget(tl)
            return btn

        self.dashboard_btn  = _nav("📊", "Analytics",  "Open Analytics Dashboard  (Ctrl+D)")
        self.calibrate_btn  = _nav("🎯", "Calibrate",  "3-step Calibration Wizard")
        self.neck_chart_btn = _nav("📈", "Neck Chart", "Live Neck Angle Chart")
        self.settings_btn   = _nav("⚙",  "Settings",   "Settings  (Ctrl+,)")
        self.contact_btn    = _nav("📧", "Contact",    "Contact Us")
        self._theme_btn     = _nav("🌙", "Theme",      "Toggle Dark / Light Theme")

        for b in (self.dashboard_btn, self.calibrate_btn, self.neck_chart_btn):
            sb_lay.addWidget(b)
        sb_lay.addStretch()
        for b in (self.settings_btn, self.contact_btn, self._theme_btn):
            sb_lay.addWidget(b)

        body_lay.addWidget(sidebar)

        # ─── Main content ───────────────────────────────────────────────
        content = QWidget()
        body_lay.addWidget(content, stretch=1)
        root = QHBoxLayout(content)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ── LEFT: camera + controls ───────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        cam_group = QGroupBox("Camera Feed")
        cam_lay   = QVBoxLayout(cam_group)
        cam_lay.setContentsMargins(8, 8, 8, 8)
        cam_lay.setSpacing(8)

        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(400, 300)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet(
            f"background:#0d1117; border:1px solid {BORDER}; border-radius:8px;"
            f" color:{MUTED}; font-size:13px;")
        self.camera_label.setText("Press  Start  to begin monitoring")
        cam_lay.addWidget(self.camera_label, stretch=1)

        # Start / Stop row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setObjectName("startButton")
        self.start_btn.setFixedHeight(38)
        self.start_btn.setToolTip("Start monitoring  (Ctrl+S)")
        self.stop_btn  = QPushButton("■  Stop")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setFixedHeight(38)
        self.stop_btn.setToolTip("Stop monitoring  (Ctrl+X)")
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        cam_lay.addLayout(btn_row)
        left.addWidget(cam_group, stretch=1)

        # Neck chart & label kept off-layout (fed by signals, displayed in popup)
        self._neck_chart = NeckChart()
        self._neck_label = QLabel("--")
        self._neck_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._neck_label.setStyleSheet(f"color:{ACCENT}; font-size:22px; font-weight:800;")
        self._neck_chart_popup: QDialog | None = None

        # ── RIGHT: score + status (compact, scrollable) ───────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setFixedWidth(290)
        right_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            " QScrollBar:vertical{width:5px;background:transparent;}"
            f" QScrollBar::handle:vertical{{background:{BORDER};border-radius:3px;}}"
            " QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")
        right_widget = QWidget()
        right_widget.setStyleSheet("background:transparent;")
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 4, 0)
        right.setSpacing(8)

        # ── Score ring + session info ─────────────────────────────────────
        sess_group = QGroupBox("Session")
        sess_lay   = QVBoxLayout(sess_group)
        sess_lay.setContentsMargins(10, 10, 10, 10)
        sess_lay.setSpacing(8)

        # Ring + 2 cards side-by-side
        ring_row = QHBoxLayout()
        ring_row.setSpacing(10)
        self._score_ring = ScoreRing()
        self._score_ring.setFixedSize(88, 88)
        ring_row.addWidget(self._score_ring, alignment=Qt.AlignVCenter)
        ring_right = QVBoxLayout()
        ring_right.setSpacing(6)
        self._card_duration = MetricCard("Duration",   "--:--", ACCENT)
        self._card_score    = MetricCard("Score",      "0%",    GREEN)
        self._card_session  = MetricCard("Session #",  "--",    ACCENT2)
        ring_right.addWidget(self._card_duration)
        ring_right.addWidget(self._card_score)
        ring_right.addWidget(self._card_session)
        ring_row.addLayout(ring_right, stretch=1)
        sess_lay.addLayout(ring_row)
        right.addWidget(sess_group)

        # ── Posture status ────────────────────────────────────────────────
        p_group = QGroupBox("Posture")
        p_lay   = QVBoxLayout(p_group)
        p_lay.setContentsMargins(10, 8, 10, 8)
        p_lay.setSpacing(6)
        self._posture_badge = StatusBadge("NOT STARTED")
        self._posture_badge.setMinimumWidth(0)
        p_lay.addWidget(self._posture_badge)

        for attr, lbl_text, colour in (
            ("_neck_val_lbl",  "Neck angle",   ACCENT),
            ("_p_alerts_lbl",  "Alerts today", ORANGE),
        ):
            row = QHBoxLayout()
            row.setSpacing(4)
            l = QLabel(lbl_text)
            l.setStyleSheet(f"color:{MUTED}; font-size:12px;")
            v = QLabel("--")
            v.setStyleSheet(f"color:{colour}; font-size:13px; font-weight:700;")
            setattr(self, attr, v)
            row.addWidget(l, stretch=1)
            row.addWidget(v)
            p_lay.addLayout(row)
        right.addWidget(p_group)

        # ── Eye status ───────────────────────────────────────────────────
        e_group = QGroupBox("Eyes / Drowsiness")
        e_lay   = QVBoxLayout(e_group)
        e_lay.setContentsMargins(10, 8, 10, 8)
        e_lay.setSpacing(6)
        self._eye_badge = StatusBadge("NOT STARTED")
        self._eye_badge.setMinimumWidth(0)
        e_lay.addWidget(self._eye_badge)

        for attr, lbl_text, colour in (
            ("_ear_val_lbl",   "EAR value",     ACCENT2),
            ("_d_alerts_lbl",  "Drowsy alerts", RED),
        ):
            row = QHBoxLayout()
            row.setSpacing(4)
            l = QLabel(lbl_text)
            l.setStyleSheet(f"color:{MUTED}; font-size:12px;")
            v = QLabel("0")
            v.setStyleSheet(f"color:{colour}; font-size:13px; font-weight:700;")
            setattr(self, attr, v)
            row.addWidget(l, stretch=1)
            row.addWidget(v)
            e_lay.addLayout(row)
        right.addWidget(e_group)

        # ── Today's 4 stat cards (2×2 grid) ──────────────────────────────
        stats_group = QGroupBox("Today's Stats")
        stats_grid  = QGridLayout(stats_group)
        stats_grid.setContentsMargins(8, 8, 8, 8)
        stats_grid.setSpacing(6)
        self._card_sessions = MetricCard("Sessions",  "0", ACCENT)
        self._card_good_pct = MetricCard("Good",      "0%", GREEN)
        self._card_slouch   = MetricCard("Slouching", "0%", YELLOW)
        self._card_d_total  = MetricCard("Drowsy",    "0",  RED)
        stats_grid.addWidget(self._card_sessions, 0, 0)
        stats_grid.addWidget(self._card_good_pct, 0, 1)
        stats_grid.addWidget(self._card_slouch,   1, 0)
        stats_grid.addWidget(self._card_d_total,  1, 1)
        right.addWidget(stats_group)

        # ── Alert log ────────────────────────────────────────────────────
        log_group = QGroupBox("Recent Alerts")
        log_lay   = QVBoxLayout(log_group)
        log_lay.setContentsMargins(8, 8, 8, 8)
        self._alert_list = QListWidget()
        self._alert_list.setFixedHeight(120)
        self._alert_list.setStyleSheet(
            f"QListWidget{{background:{BG3};border:1px solid {BORDER};"
            f"border-radius:8px;padding:4px;font-size:11px;}}"
            f"QListWidget::item{{padding:3px 6px;border-radius:4px;}}"
            f"QListWidget::item:hover{{background:{BG2};}}")
        self._alert_list.setSelectionMode(QListWidget.NoSelection)
        self._alert_list.setFocusPolicy(Qt.NoFocus)
        log_lay.addWidget(self._alert_list)
        right.addWidget(log_group)

        right.addStretch()
        right_scroll.setWidget(right_widget)

        root.addLayout(left, stretch=1)
        root.addWidget(right_scroll)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — press Start to begin.")

        # Tick timer
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._on_ui_tick)
        self._ui_timer.setInterval(1000)

    # ──────────────────────────────────────────── menu ────────────────────

    def _build_menu(self):
        mb = self.menuBar()
        file_m = mb.addMenu("File")
        self._act_start = QAction("Start Monitoring", self, shortcut="Ctrl+S",
                                  triggered=self._on_start)
        self._act_stop  = QAction("Stop Monitoring",  self, shortcut="Ctrl+X",
                                  triggered=self._on_stop)
        act_exit = QAction("Exit", self, shortcut="Ctrl+Q", triggered=self.close)
        for a in (self._act_start, self._act_stop, file_m.addSeparator(), act_exit):
            if isinstance(a, QAction):
                file_m.addAction(a)

        view_m = mb.addMenu("View")
        view_m.addAction(QAction("Dashboard", self, shortcut="Ctrl+D",
                                 triggered=self._open_dashboard))
        view_m.addAction(QAction("Toggle Theme", self,
                                 triggered=self._toggle_theme))

        set_m = mb.addMenu("Settings")
        set_m.addAction(QAction("Preferences", self, shortcut="Ctrl+,",
                                triggered=self._open_settings))
        set_m.addAction(QAction("Calibrate", self,
                                triggered=self._open_calibration))

        help_m = mb.addMenu("Help")
        help_m.addAction(QAction("About PostureGuard", self,
                                  triggered=self._show_about))
        help_m.addSeparator()
        help_m.addAction(QAction("Contact Us", self,
                                  triggered=self._open_contact))

    # ──────────────────────────────────────────── signals ─────────────────

    def _connect_signals(self):
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.dashboard_btn.clicked.connect(self._open_dashboard)
        self.settings_btn.clicked.connect(self._open_settings)
        self.calibrate_btn.clicked.connect(self._open_calibration)
        self.contact_btn.clicked.connect(self._open_contact)
        self._theme_btn.clicked.connect(self._toggle_theme)
        self.neck_chart_btn.clicked.connect(self._show_neck_chart_popup)

        self.camera_handler.frame_ready.connect(self._on_raw_frame)
        self.camera_handler.error_occurred.connect(self._on_camera_error)

        self.posture_detector.posture_detected.connect(self._on_posture)
        self.posture_detector.frame_processed.connect(self._show_frame)
        self.eye_monitor.drowsiness_detected.connect(self._on_drowsiness)
        self.session_tracker.stats_updated.connect(self._on_stats)

    def _apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.theme))

    def _update_buttons_state(self):
        self.start_btn.setEnabled(not self._running)
        self.stop_btn.setEnabled(self._running)
        self._act_start.setEnabled(not self._running)
        self._act_stop.setEnabled(self._running)

    # ──────────────────────────────────────────── slots ───────────────────

    @pyqtSlot()
    def _on_start(self):
        if self._running:
            return
        self._running    = True
        self._session_id = self.session_tracker.start_session()
        self.camera_handler.start()
        self.posture_detector.start()
        self.eye_monitor.start()
        self._ui_timer.start()
        self._update_buttons_state()
        self._card_session.set_value(str(self._session_id or "--"))
        self._header_status.setText("\u25cf  Monitoring")
        self._header_status.setStyleSheet(
            f"color: {GREEN}; font-size: 13px; font-weight: 700;"
            f" background: {GREEN}18; border: 2px solid {GREEN};"
            f" border-radius: 12px; padding: 5px 18px;"
        )
        self.status_bar.showMessage(
            f"Monitoring started - session #{self._session_id}")

    @pyqtSlot()
    def _on_stop(self):
        if not self._running:
            return
        self._running = False
        self._ui_timer.stop()
        self.camera_handler.stop()
        self.posture_detector.stop()
        self.eye_monitor.stop()
        summary = self.session_tracker.stop_session() or {}
        self._update_buttons_state()
        self._posture_badge.set_status("STOPPED", MUTED)
        self._eye_badge.set_status("STOPPED", MUTED)
        self._header_status.setText("Idle")
        self._header_status.setStyleSheet(
            f"color: {MUTED}; font-size: 13px; font-weight: 600;"
            f" background: #21262d; border: 1px solid {BORDER};"
            f" border-radius: 12px; padding: 5px 18px;"
        )
        self.camera_label.setPixmap(QPixmap())
        self.camera_label.setText("Monitoring stopped.\nPress Start to begin a new session.")
        score = summary.get("posture_score", 0)
        self.status_bar.showMessage(
            f"Session ended - duration: {summary.get('elapsed_str','--')}  |  "
            f"score: {score:.0f}%"
        )

    @pyqtSlot(np.ndarray)
    def _on_raw_frame(self, frame: np.ndarray):
        self.posture_detector.process_frame(frame)
        self.eye_monitor.process_frame(frame)

    @pyqtSlot(np.ndarray)
    def _show_frame(self, frame: np.ndarray):
        from src.utils import frame_to_qt_image
        img    = frame_to_qt_image(frame)
        pixmap = QPixmap.fromImage(img).scaled(
            self.camera_label.size(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.camera_label.setPixmap(pixmap)

    @pyqtSlot(dict)
    def _on_posture(self, data: dict):
        self._last_posture_data = data
        state  = data.get("status", "UNKNOWN")
        angle  = data.get("neck_angle") or 0.0
        colour = get_status_colour(state)
        self._posture_badge.set_status(state.replace("_", " "), colour)
        self._neck_val_lbl.setText(f"{angle:.1f} deg")
        self._neck_chart.push(angle)
        self._neck_label.setText(f"{angle:.0f} deg")
        clr = GREEN if state == "GOOD" else (YELLOW if state == "SLOUCHING" else RED)
        self._neck_label.setStyleSheet(f"color:{clr}; font-size:28px; font-weight:800;")
        self.session_tracker.record_posture_event(data)
        _sev = {"SLOUCHING": "GENTLE", "FORWARD_HEAD": "MODERATE", "NECK_STRAIN": "SEVERE"}
        if state in _sev:
            self.alert_system.trigger_posture_alert(_sev[state], angle)
            self._add_alert_log(f"Posture: {state.replace('_',' ')} ({angle:.0f} deg)")

    @pyqtSlot(dict)
    def _on_drowsiness(self, data: dict):
        self._last_eye_data = data
        state  = data.get("status", "UNKNOWN")
        ear    = data.get("ear") or 0.0
        colour = get_status_colour(state)
        self._eye_badge.set_status(state, colour)
        self._ear_val_lbl.setText(f"{ear:.3f}")
        self.session_tracker.record_drowsiness_event(data)
        if state in ("TIRED", "DROWSY"):
            self.alert_system.trigger_drowsiness_alert(state)
            icon = "[!]" if state == "DROWSY" else "[!]"
            self._add_alert_log(f"{icon} Eye: {state}  (EAR {ear:.3f})")

    @pyqtSlot(dict)
    def _on_stats(self, stats: dict):
        self._card_duration.set_value(stats.get("elapsed_str", "--"))
        score = int(stats.get("posture_score", 0))
        self._score_ring.set_score(score)
        self._card_score.set_value(f"{score}%")

    @pyqtSlot()
    def _on_ui_tick(self):
        elapsed = self.session_tracker.get_elapsed_str()
        self._card_duration.set_value(elapsed)
        score = int(self.session_tracker.get_posture_score())
        self._score_ring.set_score(score)
        self._card_score.set_value(f"{score}%")
        try:
            hist = self.data_manager.get_history(days=1)
            if hist:
                self._p_alerts_lbl.setText(str(hist.get("posture_alerts", 0)))
                self._d_alerts_lbl.setText(str(hist.get("drowsy_alerts", 0)))
                self._card_sessions.set_value(str(hist.get("sessions", 0)))
                good = hist.get("good_pct", 0)
                self._card_good_pct.set_value(f"{good:.0f}%")
                self._card_d_total.set_value(str(hist.get("drowsy_alerts", 0)))
        except Exception:
            pass

    @pyqtSlot(str)
    def _on_camera_error(self, msg: str):
        self.status_bar.showMessage(f"Camera error: {msg}")
        if self._running:
            self._on_stop()

    def _add_alert_log(self, text: str):
        import datetime
        ts   = datetime.datetime.now().strftime("%H:%M:%S")
        item = QListWidgetItem(f"[{ts}]  {text}")
        item.setForeground(QColor(TEXT))
        self._alert_list.insertItem(0, item)
        if self._alert_list.count() > 50:
            self._alert_list.takeItem(self._alert_list.count() - 1)

    # ──────────────────────────────────────────── menu actions ────────────

    def _open_dashboard(self):
        from src.ui.dashboard import DashboardWindow
        self._dashboard = DashboardWindow(self.data_manager, self.theme, self)
        self._dashboard.show()

    def _open_settings(self):
        from src.ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.config, self.data_manager, self)
        if dlg.exec_():
            new = dlg.get_settings()
            self.data_manager.save_settings(new)
            self.theme = new.get("theme", self.theme)
            self._apply_theme()
            self.alert_system.set_volume(new.get("alert_volume", 70))
            self.status_bar.showMessage("Settings saved.")

    def _open_contact(self):
        from src.ui.contact_dialog import ContactDialog
        dlg = ContactDialog(self)
        dlg.exec_()

    def _open_calibration(self):
        from src.ui.calibration_dialog import CalibrationDialog
        dlg = CalibrationDialog(self.config, self)
        dlg.exec_()

    def _show_neck_chart_popup(self):
        """Open (or bring to front) the floating Live Neck Angle chart window."""
        if self._neck_chart_popup is None:
            dlg = QDialog(self)
            dlg.setWindowTitle("Live Neck Angle Chart")
            dlg.setMinimumSize(480, 200)
            dlg.resize(560, 220)
            dlg.setStyleSheet(self.styleSheet())
            dlg.setWindowFlags(
                Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint
            )
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(12, 12, 12, 12)
            lay.setSpacing(8)

            # Title row
            title_row = QHBoxLayout()
            title_lbl = QLabel("Neck Angle  (deg)")
            title_lbl.setStyleSheet(
                f"color:{MUTED}; font-size:11px; font-weight:700;"
                f" letter-spacing:1px; text-transform:uppercase;"
            )
            self._neck_label.setStyleSheet(
                f"color:{ACCENT}; font-size:24px; font-weight:800;"
            )
            title_row.addWidget(title_lbl, stretch=1)
            title_row.addWidget(self._neck_label)
            lay.addLayout(title_row)

            # Sparkline
            self._neck_chart.setMinimumHeight(120)
            lay.addWidget(self._neck_chart, stretch=1)

            hint = QLabel("\u25b6  Chart updates in real time while monitoring is active.")
            hint.setStyleSheet(f"color:{MUTED}; font-size:11px;")
            lay.addWidget(hint)

            self._neck_chart_popup = dlg

        self._neck_chart_popup.show()
        self._neck_chart_popup.raise_()
        self._neck_chart_popup.activateWindow()

    def _toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self._apply_theme()
        s = self.data_manager.get_settings()
        s["theme"] = self.theme
        self.data_manager.save_settings(s)

    def _show_about(self):
        QMessageBox.about(
            self, "About PostureGuard",
            "<h2>PostureGuard v1.0</h2>"
            "<p>AI-powered posture &amp; drowsiness monitoring.</p>"
            "<p><b>Stack:</b> MediaPipe  |  OpenCV  |  PyQt5  |  Windows SAPI TTS</p>"
        )

    def closeEvent(self, event):
        if self._running:
            self._on_stop()
        self.camera_handler.stop()
        self.posture_detector.stop()
        self.eye_monitor.stop()
        event.accept()

