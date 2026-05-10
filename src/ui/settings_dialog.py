"""
settings_dialog.py — 5-tab preferences dialog for PostureGuard.
"""

import logging
from PyQt5.QtCore    import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QWidget, QLabel, QCheckBox,
    QSpinBox, QDoubleSpinBox, QComboBox, QSlider,
    QPushButton, QDialogButtonBox, QGroupBox, QSizePolicy,
)

from src.ui.styles import get_theme_palette

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    def __init__(self, config: dict, data_manager, parent=None):
        super().__init__(parent)
        self.config = config
        self.data_manager = data_manager
        self._settings = data_manager.get_settings()
        self.theme = self._settings.get("theme", getattr(parent, "theme", "dark"))

        self.setWindowTitle("PostureGuard — Preferences")
        self.setMinimumSize(580, 520)
        self.resize(620, 580)

        self._build_ui()
        self._apply_theme()
        self._populate()

    def _apply_theme(self):
        palette = get_theme_palette(self.theme)
        self.setStyleSheet(
            f"QDialog {{ background:{palette['bg']}; color:{palette['text']}; }}"
            f"QWidget {{ background: transparent; color:{palette['text']}; }}"
            f"QLabel {{ color:{palette['text']}; background: transparent; }}"
            f"QGroupBox {{ background:{palette['bg2']}; border:1px solid {palette['border']}; border-radius:12px; margin-top:10px; padding:14px 10px 10px 10px; font-weight:700; }}"
            f"QGroupBox::title {{ color:{palette['muted']}; font-size:11px; font-weight:700; letter-spacing:0.8px; }}"
            f"QTabWidget::pane {{ background:{palette['bg2']}; border:1px solid {palette['border']}; border-radius:10px; top:-1px; }}"
            f"QTabBar::tab {{ background: transparent; color:{palette['muted']}; padding: 10px 22px; margin-right:4px; border-bottom:3px solid transparent; font-weight:600; }}"
            f"QTabBar::tab:selected {{ color:{palette['accent']}; border-bottom-color:{palette['accent']}; }}"
            f"QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background:{palette['surface']}; color:{palette['text']}; border:1px solid {palette['border']}; border-radius:8px; padding:8px 12px; }}"
            f"QLineEdit:focus, QTextEdit:focus, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color:{palette['accent']}; }}"
            f"QComboBox QAbstractItemView {{ background:{palette['bg2']}; color:{palette['text']}; border:1px solid {palette['border']}; selection-background-color:{palette['accent']}; selection-color:#ffffff; }}"
            f"QCheckBox {{ spacing:10px; color:{palette['text']}; }}"
            f"QCheckBox::indicator {{ width:20px; height:20px; border-radius:5px; border:2px solid {palette['border']}; background:{palette['surface']}; }}"
            f"QCheckBox::indicator:checked {{ background:{palette['accent']}; border-color:{palette['accent']}; }}"
            f"QSlider::groove:horizontal {{ height:8px; background:{palette['border2']}; border-radius:4px; }}"
            f"QSlider::handle:horizontal {{ background:{palette['accent']}; border:2px solid {palette['accent2']}; width:20px; height:20px; margin:-7px 0; border-radius:11px; }}"
            f"QSlider::sub-page:horizontal {{ background:{palette['accent']}; border-radius:4px; }}"
            f"QDialogButtonBox QPushButton {{ min-width:100px; }}"
        )
        self._header_widget.setStyleSheet(
            f"background:{palette['bg2']}; border-radius:12px; padding:2px;"
        )
        self._title_lbl.setStyleSheet(
            f"color:{palette['accent']}; font-size:18px; font-weight:800; background: transparent;"
        )
        self._desc_lbl.setStyleSheet(
            f"color:{palette['muted']}; font-size:13px; font-weight:400; background: transparent;"
        )

    # ----------------------------------------------------------------- UI ---
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QWidget()
        self._header_widget = hdr
        hdr.setStyleSheet(
            "background: #161b22; border-radius: 12px; padding: 2px;"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 14, 18, 14)
        self._title_lbl = QLabel("Preferences")
        self._title_lbl.setStyleSheet(
            "color: #58a6ff; font-size: 18px; font-weight: 800; background: transparent;"
        )
        self._desc_lbl = QLabel("Customise PostureGuard settings")
        self._desc_lbl.setStyleSheet(
            "color: #8b949e; font-size: 13px; font-weight: 400; background: transparent;"
        )
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(self._title_lbl)
        title_col.addWidget(self._desc_lbl)
        hdr_lay.addLayout(title_col)
        root.addWidget(hdr)

        self._tabs = QTabWidget()

        self._tab_general   = self._make_general_tab()
        self._tab_posture   = self._make_posture_tab()
        self._tab_drowsy    = self._make_drowsy_tab()
        self._tab_alerts    = self._make_alerts_tab()
        self._tab_camera    = self._make_camera_tab()

        self._tabs.addTab(self._tab_general,  "General")
        self._tabs.addTab(self._tab_posture,  "Posture")
        self._tabs.addTab(self._tab_drowsy,   "Drowsiness")
        self._tabs.addTab(self._tab_alerts,   "Alerts")
        self._tabs.addTab(self._tab_camera,   "Camera")
        root.addWidget(self._tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setCenterButtons(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ---- General tab ----
    def _make_general_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 12, 10, 8)
        lay.setSpacing(10)
        grp = QGroupBox("Application")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setContentsMargins(14, 10, 14, 12)
        g.setColumnMinimumWidth(0, 200)

        g.addWidget(QLabel("Theme:"), 0, 0)
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light"])
        g.addWidget(self._theme_combo, 0, 1)

        g.addWidget(QLabel("Check interval (s):"), 1, 0)
        self._check_interval_sb = QSpinBox()
        self._check_interval_sb.setRange(1, 60)
        g.addWidget(self._check_interval_sb, 1, 1)

        self._start_on_launch_cb = QCheckBox("Start monitoring on launch")
        g.addWidget(self._start_on_launch_cb, 2, 0, 1, 2)

        self._minimize_tray_cb = QCheckBox("Minimize to system tray")
        g.addWidget(self._minimize_tray_cb, 3, 0, 1, 2)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    # ---- Posture tab ----
    def _make_posture_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 12, 10, 8)
        lay.setSpacing(10)
        grp = QGroupBox("Posture Thresholds")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setContentsMargins(14, 10, 14, 12)
        g.setColumnMinimumWidth(0, 200)

        g.addWidget(QLabel("Slouch angle threshold (°):"), 0, 0)
        self._slouch_sb = QDoubleSpinBox()
        self._slouch_sb.setRange(5.0, 90.0)
        self._slouch_sb.setSingleStep(1.0)
        g.addWidget(self._slouch_sb, 0, 1)

        g.addWidget(QLabel("Forward head threshold (°):"), 1, 0)
        self._fwd_head_sb = QDoubleSpinBox()
        self._fwd_head_sb.setRange(5.0, 90.0)
        self._fwd_head_sb.setSingleStep(1.0)
        g.addWidget(self._fwd_head_sb, 1, 1)

        g.addWidget(QLabel("Alert cooldown (s):"), 2, 0)
        self._posture_cooldown_sb = QSpinBox()
        self._posture_cooldown_sb.setRange(10, 600)
        g.addWidget(self._posture_cooldown_sb, 2, 1)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    # ---- Drowsiness tab ----
    def _make_drowsy_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 12, 10, 8)
        lay.setSpacing(10)
        grp = QGroupBox("Eye / Drowsiness")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setContentsMargins(14, 10, 14, 12)
        g.setColumnMinimumWidth(0, 200)

        g.addWidget(QLabel("EAR threshold:"), 0, 0)
        self._ear_sb = QDoubleSpinBox()
        self._ear_sb.setRange(0.10, 0.50)
        self._ear_sb.setSingleStep(0.01)
        self._ear_sb.setDecimals(2)
        g.addWidget(self._ear_sb, 0, 1)

        g.addWidget(QLabel("Consecutive closed frames:"), 1, 0)
        self._drowsy_frames_sb = QSpinBox()
        self._drowsy_frames_sb.setRange(5, 60)
        g.addWidget(self._drowsy_frames_sb, 1, 1)

        g.addWidget(QLabel("Alert cooldown (s):"), 2, 0)
        self._drowsy_cooldown_sb = QSpinBox()
        self._drowsy_cooldown_sb.setRange(10, 600)
        g.addWidget(self._drowsy_cooldown_sb, 2, 1)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    # ---- Alerts tab ----
    def _make_alerts_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 12, 10, 8)
        lay.setSpacing(10)
        grp = QGroupBox("Alert Settings")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setContentsMargins(14, 10, 14, 12)
        g.setColumnMinimumWidth(0, 200)

        self._sound_cb = QCheckBox("Enable sound alerts")
        g.addWidget(self._sound_cb, 0, 0, 1, 2)

        self._notif_cb = QCheckBox("Enable desktop notifications")
        g.addWidget(self._notif_cb, 1, 0, 1, 2)

        g.addWidget(QLabel("Volume:"), 2, 0)
        self._volume_sl = QSlider(Qt.Horizontal)
        self._volume_sl.setRange(0, 100)
        g.addWidget(self._volume_sl, 2, 1)
        self._volume_lbl = QLabel("70%")
        self._volume_sl.valueChanged.connect(lambda v: self._volume_lbl.setText(f"{v}%"))
        g.addWidget(self._volume_lbl, 2, 2)

        g.addWidget(QLabel("Snooze duration (min):"), 3, 0)
        self._snooze_sb = QSpinBox()
        self._snooze_sb.setRange(1, 60)
        g.addWidget(self._snooze_sb, 3, 1)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    # ---- Camera tab ----
    def _make_camera_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 12, 10, 8)
        lay.setSpacing(10)
        grp = QGroupBox("Camera Configuration")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setContentsMargins(14, 10, 14, 12)
        g.setColumnMinimumWidth(0, 200)

        g.addWidget(QLabel("Camera device ID:"), 0, 0)
        self._cam_id_sb = QSpinBox()
        self._cam_id_sb.setRange(0, 9)
        g.addWidget(self._cam_id_sb, 0, 1)

        g.addWidget(QLabel("Resolution:"), 1, 0)
        self._res_combo = QComboBox()
        self._res_combo.addItems(["640x480", "1280x720", "1920x1080"])
        g.addWidget(self._res_combo, 1, 1)

        g.addWidget(QLabel("FPS:"), 2, 0)
        self._fps_sb = QSpinBox()
        self._fps_sb.setRange(5, 60)
        g.addWidget(self._fps_sb, 2, 1)

        g.addWidget(QLabel("Skip frames:"), 3, 0)
        self._skip_sb = QSpinBox()
        self._skip_sb.setRange(0, 10)
        g.addWidget(self._skip_sb, 3, 1)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    # ----------------------------------------------------------------- data -
    def _populate(self):
        s = self._settings
        p = self.config.get("posture", {})
        e = self.config.get("eye_monitor", {})
        c = self.config.get("camera", {})

        # General
        idx = self._theme_combo.findText(s.get("theme", "dark"))
        self._theme_combo.setCurrentIndex(max(idx, 0))
        self._check_interval_sb.setValue(s.get("check_interval", 5))
        self._start_on_launch_cb.setChecked(s.get("start_on_launch", False))
        self._minimize_tray_cb.setChecked(s.get("minimize_to_tray", False))

        # Posture
        self._slouch_sb.setValue(p.get("slouch_threshold", 35.0))
        self._fwd_head_sb.setValue(p.get("forward_head_threshold", 30.0))
        self._posture_cooldown_sb.setValue(s.get("posture_cooldown", 60))

        # Drowsiness
        self._ear_sb.setValue(e.get("ear_threshold", 0.25))
        self._drowsy_frames_sb.setValue(e.get("consecutive_frames", 20))
        self._drowsy_cooldown_sb.setValue(s.get("drowsy_cooldown", 60))

        # Alerts
        self._sound_cb.setChecked(s.get("sound_alerts", True))
        self._notif_cb.setChecked(s.get("notifications", True))
        vol = s.get("alert_volume", 70)
        self._volume_sl.setValue(vol)
        self._volume_lbl.setText(f"{vol}%")
        self._snooze_sb.setValue(s.get("snooze_duration", 5))

        # Camera
        self._cam_id_sb.setValue(c.get("device_id", 0))
        res = f"{c.get('width', 640)}x{c.get('height', 480)}"
        ridx = self._res_combo.findText(res)
        self._res_combo.setCurrentIndex(max(ridx, 0))
        self._fps_sb.setValue(c.get("fps", 30))
        self._skip_sb.setValue(self.config.get("processing", {}).get("skip_frames", 2))

    def get_settings(self) -> dict:
        res   = self._res_combo.currentText().split("x")
        width = int(res[0]) if len(res) == 2 else 640
        height = int(res[1]) if len(res) == 2 else 480
        return {
            "theme":             self._theme_combo.currentText(),
            "check_interval":    self._check_interval_sb.value(),
            "start_on_launch":   self._start_on_launch_cb.isChecked(),
            "minimize_to_tray":  self._minimize_tray_cb.isChecked(),
            "slouch_threshold":  self._slouch_sb.value(),
            "forward_head_threshold": self._fwd_head_sb.value(),
            "posture_cooldown":  self._posture_cooldown_sb.value(),
            "ear_threshold":     self._ear_sb.value(),
            "consecutive_frames": self._drowsy_frames_sb.value(),
            "drowsy_cooldown":   self._drowsy_cooldown_sb.value(),
            "sound_alerts":      self._sound_cb.isChecked(),
            "notifications":     self._notif_cb.isChecked(),
            "alert_volume":      self._volume_sl.value(),
            "snooze_duration":   self._snooze_sb.value(),
            "camera_device_id":  self._cam_id_sb.value(),
            "camera_width":      width,
            "camera_height":     height,
            "camera_fps":        self._fps_sb.value(),
            "skip_frames":       self._skip_sb.value(),
        }
