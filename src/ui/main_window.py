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
    QScrollArea,
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
        self.setMinimumWidth(180)
        self.setFixedHeight(42)
        self._apply(MUTED)

    def set_status(self, text: str, hex_colour: str):
        self.setText(text)
        self._apply(hex_colour)

    def _apply(self, bg: str):
        self.setStyleSheet(
            f"background: {bg}22; color: {bg}; border: 2px solid {bg};"
            f" border-radius: 18px;"
            f" font-weight: 800; font-size: 14px; padding: 6px 22px;"
            f" letter-spacing: 1px;"
        )


# ── Score ring (QPainter arc) ─────────────────────────────────────────────

class ScoreRing(QWidget):
    """Circular progress ring showing posture score 0-100."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._score   = 0
        self._colour  = ACCENT
        self.setFixedSize(120, 120)

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
        p.setFont(QFont("Segoe UI", 16, QFont.Bold))
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
        self.setMinimumHeight(56)
        self.setStyleSheet(
            f"QFrame {{ background: {BG2}; border: 1px solid {BORDER};"
            f" border-left: 4px solid {accent}; border-radius: 10px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(1)
        self._lbl = QLabel(label.upper())
        self._lbl.setStyleSheet(
            f"color:{MUTED}; font-size:10px; font-weight:700; letter-spacing:1px;"
            f" border:none; background:transparent;"
        )
        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color:{accent}; font-size:18px; font-weight:800;"
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
        self.setWindowTitle("PostureGuard - AI Posture & Drowsiness Monitor")
        self.setMinimumSize(1180, 740)
        self.resize(1360, 860)

        central = QWidget()
        self.setCentralWidget(central)

        # Outer container with a branded header bar at the top
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # App header bar
        header_bar = QWidget()
        header_bar.setFixedHeight(60)
        header_bar.setStyleSheet(
            f"background: {BG2}; border-bottom: 1px solid {BORDER};"
        )
        hb_lay = QHBoxLayout(header_bar)
        hb_lay.setContentsMargins(20, 0, 20, 0)
        hb_lay.setSpacing(0)
        app_name = QLabel("PostureGuard")
        app_name.setStyleSheet(
            f"color: {ACCENT}; font-size: 20px; font-weight: 800; letter-spacing: -0.5px;"
        )
        app_sub = QLabel("  \u2014  AI Posture & Drowsiness Monitor")
        app_sub.setStyleSheet(f"color: {MUTED}; font-size: 14px; font-weight: 400;")
        self._header_status = QLabel("Idle")
        self._header_status.setStyleSheet(
            f"color: {MUTED}; font-size: 13px; font-weight: 600;"
            f" background: #21262d; border: 1px solid {BORDER};"
            f" border-radius: 12px; padding: 5px 18px;"
        )
        hb_lay.addWidget(app_name)
        hb_lay.addWidget(app_sub)
        hb_lay.addStretch()
        hb_lay.addWidget(self._header_status)
        outer.addWidget(header_bar)

        # Main content area
        content = QWidget()
        outer.addWidget(content, stretch=1)
        root = QHBoxLayout(content)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        # ── LEFT column ───────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(14)

        # Camera feed
        cam_group = QGroupBox("  Camera Feed")
        cam_lay   = QVBoxLayout(cam_group)
        cam_lay.setSpacing(10)
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet(
            f"background:#0d1117; border:1px solid {BORDER}; border-radius:12px;"
            f" color:{MUTED}; font-size:15px;"
        )
        self.camera_label.setText("Press Start Monitoring to begin")
        cam_lay.addWidget(self.camera_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.setObjectName("startButton")
        self.start_btn.setFixedHeight(50)
        self.stop_btn  = QPushButton("Stop Monitoring")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setFixedHeight(50)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        cam_lay.addLayout(btn_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)
        self.dashboard_btn = QPushButton("Dashboard")
        self.settings_btn  = QPushButton("Settings")
        self.calibrate_btn = QPushButton("Calibrate")
        for b in (self.dashboard_btn, self.settings_btn, self.calibrate_btn):
            b.setObjectName("iconButton")
            b.setFixedHeight(44)
            ctrl_row.addWidget(b)
        cam_lay.addLayout(ctrl_row)
        left.addWidget(cam_group, stretch=1)

        # Neck angle sparkline
        neck_group = QGroupBox("  Live Neck Angle")
        neck_lay   = QVBoxLayout(neck_group)
        neck_lay.setContentsMargins(10, 8, 10, 8)
        self._neck_chart = NeckChart()
        self._neck_label = QLabel("--")
        self._neck_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._neck_label.setStyleSheet(f"color:{ACCENT}; font-size:28px; font-weight:800;")
        nh = QHBoxLayout()
        nh.setSpacing(12)
        nh.addWidget(self._neck_chart, stretch=1)
        nh.addWidget(self._neck_label)
        neck_lay.addLayout(nh)
        left.addWidget(neck_group)

        # ── RIGHT column (scrollable) ─────────────────────────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            " QScrollBar:vertical { width: 6px; background: transparent; }"
            f" QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; }}"
            " QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(14)

        # Score ring + session
        sess_group = QGroupBox("  Session")
        sess_lay = QVBoxLayout(sess_group)
        sess_lay.setContentsMargins(14, 14, 14, 14)
        sess_lay.setSpacing(12)

        # Ring row
        ring_row = QHBoxLayout()
        ring_row.setSpacing(16)
        self._score_ring = ScoreRing()
        ring_row.addWidget(self._score_ring, alignment=Qt.AlignCenter)

        ring_info = QVBoxLayout()
        ring_info.setSpacing(6)
        self._card_duration = MetricCard("Duration",      "--:--", ACCENT)
        self._card_score    = MetricCard("Posture Score", "0%",    GREEN)
        ring_info.addWidget(self._card_duration)
        ring_info.addWidget(self._card_score)
        ring_row.addLayout(ring_info, stretch=1)
        sess_lay.addLayout(ring_row)

        # Session # below ring
        self._card_session  = MetricCard("Session #",     "--",    ACCENT2)
        sess_lay.addWidget(self._card_session)
        right.addWidget(sess_group)

        # Posture + eye status
        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        p_group = QGroupBox("  Posture")
        p_lay   = QVBoxLayout(p_group)
        p_lay.setContentsMargins(14, 14, 14, 14)
        p_lay.setSpacing(10)
        self._posture_badge = StatusBadge("NOT STARTED")
        self._posture_badge.setParent(p_group)
        p_lay.addWidget(self._posture_badge, alignment=Qt.AlignHCenter)

        pl_angle = QHBoxLayout()
        pl_angle.setSpacing(6)
        angle_lbl = QLabel("Neck angle")
        angle_lbl.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        pl_angle.addWidget(angle_lbl, stretch=1)
        self._neck_val_lbl  = QLabel("--")
        self._neck_val_lbl.setStyleSheet(f"color:{ACCENT}; font-size:15px; font-weight:700;")
        pl_angle.addWidget(self._neck_val_lbl)
        p_lay.addLayout(pl_angle)

        pl_alerts = QHBoxLayout()
        pl_alerts.setSpacing(6)
        palerts_lbl = QLabel("Alerts today")
        palerts_lbl.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        pl_alerts.addWidget(palerts_lbl, stretch=1)
        self._p_alerts_lbl  = QLabel("0")
        self._p_alerts_lbl.setStyleSheet(f"color:{ORANGE}; font-size:15px; font-weight:700;")
        pl_alerts.addWidget(self._p_alerts_lbl)
        p_lay.addLayout(pl_alerts)
        status_row.addWidget(p_group)

        e_group = QGroupBox("  Eyes")
        e_lay   = QVBoxLayout(e_group)
        e_lay.setContentsMargins(14, 14, 14, 14)
        e_lay.setSpacing(10)
        self._eye_badge = StatusBadge("NOT STARTED")
        e_lay.addWidget(self._eye_badge, alignment=Qt.AlignHCenter)

        el_ear = QHBoxLayout()
        el_ear.setSpacing(6)
        ear_lbl = QLabel("EAR value")
        ear_lbl.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        el_ear.addWidget(ear_lbl, stretch=1)
        self._ear_val_lbl = QLabel("--")
        self._ear_val_lbl.setStyleSheet(f"color:{ACCENT2}; font-size:15px; font-weight:700;")
        el_ear.addWidget(self._ear_val_lbl)
        e_lay.addLayout(el_ear)

        el_alerts = QHBoxLayout()
        el_alerts.setSpacing(6)
        dalerts_lbl = QLabel("Drowsy alerts")
        dalerts_lbl.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        el_alerts.addWidget(dalerts_lbl, stretch=1)
        self._d_alerts_lbl = QLabel("0")
        self._d_alerts_lbl.setStyleSheet(f"color:{RED}; font-size:15px; font-weight:700;")
        el_alerts.addWidget(self._d_alerts_lbl)
        e_lay.addLayout(el_alerts)
        status_row.addWidget(e_group)

        right.addLayout(status_row)

        # Today's stats cards
        stats_group = QGroupBox("  Today's Stats")
        stats_grid  = QGridLayout(stats_group)
        stats_grid.setSpacing(10)
        stats_grid.setContentsMargins(14, 14, 14, 14)
        self._card_sessions   = MetricCard("Sessions",      "0", ACCENT)
        self._card_good_pct   = MetricCard("Good Posture",  "0%", GREEN)
        self._card_slouch     = MetricCard("Slouching",     "0%", YELLOW)
        self._card_d_total    = MetricCard("Drowsy Alerts", "0",  RED)
        stats_grid.addWidget(self._card_sessions,  0, 0)
        stats_grid.addWidget(self._card_good_pct,  0, 1)
        stats_grid.addWidget(self._card_slouch,    1, 0)
        stats_grid.addWidget(self._card_d_total,   1, 1)
        right.addWidget(stats_group)

        # Alert log
        log_group = QGroupBox("  Recent Alerts")
        log_lay   = QVBoxLayout(log_group)
        log_lay.setContentsMargins(12, 12, 12, 12)
        self._alert_list = QListWidget()
        self._alert_list.setMaximumHeight(160)
        self._alert_list.setStyleSheet(
            f"QListWidget {{ background: {BG3}; border: 1px solid {BORDER};"
            f" border-radius: 10px; padding: 6px; font-size: 13px; }}"
            f" QListWidget::item {{ padding: 6px 10px; border-radius: 6px; }}"
            f" QListWidget::item:hover {{ background: {BG2}; }}"
        )
        self._alert_list.setSelectionMode(QListWidget.NoSelection)
        self._alert_list.setFocusPolicy(Qt.NoFocus)
        log_lay.addWidget(self._alert_list)
        right.addWidget(log_group)

        right.addStretch()
        right_scroll.setWidget(right_widget)

        root.addLayout(left,  58)
        root.addWidget(right_scroll, 42)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - press Start Monitoring to begin.")

        # Timers
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

    # ──────────────────────────────────────────── signals ─────────────────

    def _connect_signals(self):
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.dashboard_btn.clicked.connect(self._open_dashboard)
        self.settings_btn.clicked.connect(self._open_settings)
        self.calibrate_btn.clicked.connect(self._open_calibration)

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

    def _open_calibration(self):
        from src.ui.calibration_dialog import CalibrationDialog
        dlg = CalibrationDialog(self.config, self)
        dlg.exec_()

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

