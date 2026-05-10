"""
calibration_dialog.py — 3-step calibration wizard for PostureGuard.
"""

import logging
import numpy as np
from PyQt5.QtCore    import Qt, QTimer, pyqtSlot
from PyQt5.QtGui     import QImage, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QStackedWidget, QGroupBox, QSizePolicy,
    QMessageBox, QWidget,
)

from src.ui.styles import get_theme_palette

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class CalibrationDialog(QDialog):
    """
    3-step wizard:
      Step 0 — Camera preview & instructions
      Step 1 — Capture baseline posture (N frames)
      Step 2 — Done / save result
    """
    BASELINE_FRAMES = 120     # ~4 s @ 30 fps

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.theme = getattr(parent, "theme", "dark")
        self._cap   = None
        self._landmarker = None
        self._frame_count = 0
        self._neck_angles: list = []
        self._result: dict      = {}

        self.setWindowTitle("PostureGuard — Calibration")
        self.setMinimumSize(500, 400)
        self.resize(560, 460)
        self.setModal(True)

        self._build_ui()
        self._apply_theme()
        self._goto_step(0)
        self._start_camera()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)   # ~30 fps

    # ----------------------------------------------------------- UI build ---
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        # Title
        self._title_lbl = QLabel()
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet(
            "font-size:15px; font-weight:800; color:#58a6ff;"
            " letter-spacing:-0.3px; margin:2px 0;"
        )
        root.addWidget(self._title_lbl)

        # Step indicator dots
        self._step_dots = QLabel()
        self._step_dots.setAlignment(Qt.AlignCenter)
        self._step_dots.setStyleSheet("font-size: 22px; margin-bottom: 4px;")
        root.addWidget(self._step_dots)

        # Steps (stacked)
        self._stack = QStackedWidget()

        # --- Page 0: Camera preview ---
        p0 = QWidget()
        l0 = QVBoxLayout(p0)
        self._cam_label = QLabel("Initialising camera…")
        self._cam_label.setMinimumSize(300, 200)
        self._cam_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._cam_label.setAlignment(Qt.AlignCenter)
        self._cam_label.setStyleSheet(
            "background:#0d1117; border:1px solid #30363d; border-radius:12px;"
            " color:#8b949e; font-size:13px;"
        )
        instructions = QLabel(
            "Position yourself so your full upper body is visible.\n"
            "Sit up straight with your head level, then click Next."
        )
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("font-size:13px; padding:4px;")
        l0.addWidget(self._cam_label)
        l0.addWidget(instructions)
        self._stack.addWidget(p0)

        # --- Page 1: Capture baseline ---
        p1 = QWidget()
        l1 = QVBoxLayout(p1)
        lbl1 = QLabel("Hold a straight posture while we capture your baseline.\nPlease stay still.")
        lbl1.setAlignment(Qt.AlignCenter)
        lbl1.setWordWrap(True)
        lbl1.setStyleSheet("font-size:13px; padding:4px;")
        self._baseline_pb = QProgressBar()
        self._baseline_pb.setRange(0, self.BASELINE_FRAMES)
        self._baseline_pb.setFormat("Capturing\u2026 %v / %m frames")
        self._baseline_pb.setFixedHeight(28)
        self._cam_label2 = QLabel("Camera feed")
        self._cam_label2.setMinimumSize(300, 180)
        self._cam_label2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._cam_label2.setAlignment(Qt.AlignCenter)
        self._cam_label2.setStyleSheet(
            "background:#0d1117; border:1px solid #30363d; border-radius:12px;"
            " color:#8b949e; font-size:13px;"
        )
        l1.addWidget(self._cam_label2)
        l1.addWidget(lbl1)
        l1.addWidget(self._baseline_pb)
        self._stack.addWidget(p1)

        # --- Page 2: Done ---
        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        l2.setAlignment(Qt.AlignCenter)
        done_lbl = QLabel("✅  Calibration complete!")
        done_lbl.setAlignment(Qt.AlignCenter)
        done_lbl.setStyleSheet("font-size:22px; font-weight:800; color:#3fb950;")
        self._result_lbl = QLabel("")
        self._result_lbl.setAlignment(Qt.AlignCenter)
        self._result_lbl.setWordWrap(True)
        self._result_lbl.setStyleSheet("font-size:15px; padding:10px;")
        l2.addWidget(done_lbl)
        l2.addWidget(self._result_lbl)
        self._stack.addWidget(p2)

        root.addWidget(self._stack)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.setSpacing(10)
        self._back_btn = QPushButton("\u2190 Back")
        self._back_btn.setFixedHeight(36)
        self._back_btn.setObjectName("iconButton")
        self._back_btn.clicked.connect(self._on_back)
        self._next_btn = QPushButton("Next \u2192")
        self._next_btn.setFixedHeight(36)
        self._next_btn.clicked.connect(self._on_next)
        self._finish_btn = QPushButton("\u2713  Finish")
        self._finish_btn.setFixedHeight(36)
        self._finish_btn.setObjectName("startButton")
        self._finish_btn.clicked.connect(self.accept)
        self._finish_btn.setVisible(False)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(36)
        self._cancel_btn.setObjectName("iconButton")
        self._cancel_btn.clicked.connect(self.reject)
        nav.addWidget(self._cancel_btn)
        nav.addStretch()
        nav.addWidget(self._back_btn)
        nav.addWidget(self._next_btn)
        nav.addWidget(self._finish_btn)
        root.addLayout(nav)

    def _apply_theme(self):
        palette = get_theme_palette(self.theme)
        self.setStyleSheet(
            f"QDialog {{ background:{palette['bg']}; color:{palette['text']}; }}"
            f"QLabel {{ color:{palette['text']}; background: transparent; }}"
            f"QGroupBox {{ background:{palette['bg2']}; border:1px solid {palette['border']}; border-radius:12px; }}"
            f"QProgressBar {{ background:{palette['border2']}; border:1px solid {palette['border']}; border-radius:8px; text-align:center; color:{palette['text']}; }}"
            f"QProgressBar::chunk {{ background:{palette['accent']}; border-radius:7px; }}"
            f"QPushButton {{ background:{palette['bg2']}; color:{palette['text']}; border:1px solid {palette['border']}; border-radius:8px; font-weight:700; }}"
            f"QPushButton:hover {{ border-color:{palette['accent']}; color:{palette['accent']}; }}"
            f"QPushButton#startButton {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {palette['green']}, stop:1 {palette['accent']}); color:#ffffff; border:1px solid {palette['green']}; }}"
            f"QPushButton#iconButton {{ background:{palette['bg2']}; color:{palette['muted']}; border:1px solid {palette['border']}; }}"
        )
        self._title_lbl.setStyleSheet(f"font-size:15px; font-weight:800; color:{palette['accent']}; letter-spacing:-0.3px; margin:2px 0;")
        self._step_dots.setStyleSheet(f"font-size: 22px; margin-bottom: 4px; color: {palette['muted']};")
        self._cam_label.setStyleSheet(
            f"background:{palette['surface']}; border:1px solid {palette['border']}; border-radius:12px;"
            f" color:{palette['muted']}; font-size:13px;"
        )
        self._cam_label2.setStyleSheet(
            f"background:{palette['surface']}; border:1px solid {palette['border']}; border-radius:12px;"
            f" color:{palette['muted']}; font-size:13px;"
        )
        self._baseline_pb.setStyleSheet(
            f"QProgressBar {{ background:{palette['border2']}; border:1px solid {palette['border']}; border-radius:8px; text-align:center; color:{palette['text']}; }}"
            f"QProgressBar::chunk {{ background:{palette['accent']}; border-radius:7px; }}"
        )
        self._title_lbl.setText(self._title_lbl.text())

    def _goto_step(self, step: int):
        self._step = step
        self._stack.setCurrentIndex(step)
        titles = [
            "Step 1 of 3 — Camera Preview",
            "Step 2 of 3 — Capture Baseline",
            "Step 3 of 3 — Done",
        ]
        self._title_lbl.setText(titles[step])        # Update step dots
        dots = []
        for i in range(3):
            if i == step:
                dots.append('\u25cf')  # filled circle
            elif i < step:
                dots.append('\u25cf')  # filled (completed)
            else:
                dots.append('\u25cb')  # empty circle
        colours = []
        for i in range(3):
            if i < step:
                colours.append('#3fb950')  # green for completed
            elif i == step:
                colours.append('#58a6ff')  # accent blue for current
            else:
                colours.append('#30363d')  # muted for future
        dot_html = '  '.join(
            f'<span style="color:{c};">{d}</span>' for d, c in zip(dots, colours)
        )
        self._step_dots.setText(dot_html)
        self._back_btn.setEnabled(step > 0)
        self._next_btn.setVisible(step < 2)
        self._finish_btn.setVisible(step == 2)
        if step == 1:
            self._frame_count = 0
            self._neck_angles.clear()
            self._baseline_pb.setValue(0)
            self._next_btn.setEnabled(False)

    # ------------------------------------------------------ camera helpers --
    def _start_camera(self):
        if not HAS_CV2:
            return
        device_id = self.config.get("camera", {}).get("device_id", 0)
        self._cap = cv2.VideoCapture(device_id, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(device_id)
        # Pre-load pose landmarker once (reused each frame)
        self._landmarker = None
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision as mp_vision
            from src.posture_detector import _ensure_pose_model
            model_path   = _ensure_pose_model()
            base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
            options = mp_vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.IMAGE,
                num_poses=1,
            )
            self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:
            logger.warning("Could not load pose model for calibration: %s", exc)

    def _stop_camera(self):
        self._timer.stop()
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._cap = None
        if self._landmarker:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None

    @pyqtSlot()
    def _tick(self):
        if not self._cap or not self._cap.isOpened():
            return
        ret, frame = self._cap.read()
        if not ret:
            return

        # Show frame on whichever label is visible
        if self._step == 0:
            self._display(frame, self._cam_label)
        elif self._step == 1:
            self._display(frame, self._cam_label2)
            self._capture_baseline(frame)

    def _display(self, frame, label: QLabel):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pm  = QPixmap.fromImage(img).scaled(
            label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        label.setPixmap(pm)

    def _capture_baseline(self, frame):
        """Try to estimate neck angle from frame and accumulate."""
        angle = self._estimate_neck_angle(frame)
        if angle is not None:
            self._neck_angles.append(angle)
        self._frame_count += 1
        self._baseline_pb.setValue(self._frame_count)

        if self._frame_count >= self.BASELINE_FRAMES:
            self._finish_baseline()

    def _estimate_neck_angle(self, frame) -> "float | None":
        """Estimate neck angle from frame using pre-loaded landmarker."""
        try:
            import mediapipe as mp
            from src.utils import calculate_angle
            if self._landmarker is None:
                return None
            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = self._landmarker.detect(mp_image)
            if res.pose_landmarks:
                lms = res.pose_landmarks[0]
                ear_mid = (np.array([lms[7].x, lms[7].y]) + np.array([lms[8].x, lms[8].y])) / 2
                sho_mid = (np.array([lms[11].x, lms[11].y]) + np.array([lms[12].x, lms[12].y])) / 2
                hip_mid = (np.array([lms[23].x, lms[23].y]) + np.array([lms[24].x, lms[24].y])) / 2
                return calculate_angle(ear_mid, sho_mid, hip_mid)
        except Exception:
            pass
        return None

    def _finish_baseline(self):
        self._next_btn.setEnabled(True)
        if self._neck_angles:
            mean_angle = float(np.mean(self._neck_angles))
            self._result = {"baseline_neck_angle": mean_angle}
            # Store in config
            self.config.setdefault("posture", {})["baseline_neck_angle"] = mean_angle
            self._result_lbl.setText(
                f"Baseline neck angle: <b>{mean_angle:.1f}°</b><br>"
                "PostureGuard will use this as your ideal posture reference."
            )
        else:
            self._result_lbl.setText("Could not detect pose. Default thresholds will be used.")
        self._goto_step(2)

    # ----------------------------------------------------- nav buttons ------
    def _on_next(self):
        if self._step == 0:
            self._goto_step(1)
        elif self._step == 1:
            # Force finish if somehow button is enabled early
            self._finish_baseline()

    def _on_back(self):
        if self._step > 0:
            self._goto_step(self._step - 1)

    def get_result(self) -> dict:
        return self._result

    def closeEvent(self, event):
        self._stop_camera()
        super().closeEvent(event)

    def reject(self):
        self._stop_camera()
        super().reject()

    def accept(self):
        self._stop_camera()
        super().accept()
