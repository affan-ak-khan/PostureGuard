"""
posture_detector.py
Real-time posture analysis using MediaPipe Pose Landmarker (Tasks API).
"""

import logging
import math
import time
import urllib.request
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision

logger = logging.getLogger("PostureGuard.posture")

POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
MODELS_DIR = Path(__file__).resolve().parent.parent / "assets" / "models"

# Landmark indices
LEFT_EAR = 7;  RIGHT_EAR = 8
LEFT_SHOULDER = 11; RIGHT_SHOULDER = 12
LEFT_HIP = 23;  RIGHT_HIP = 24


def _ensure_pose_model() -> str:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "pose_landmarker_lite.task"
    if not model_path.exists():
        logger.info("Downloading pose landmark model (~5 MB)...")
        urllib.request.urlretrieve(POSE_MODEL_URL, str(model_path))
        logger.info("Pose model saved to %s", model_path)
    return str(model_path)


class PostureDetector(QThread):
    """
    Processes BGR frames with MediaPipe Pose and emits posture data.

    Signals:
        posture_detected (dict): Posture result.
        frame_processed (np.ndarray): Annotated frame.
    """

    posture_detected = pyqtSignal(dict)
    frame_processed = pyqtSignal(np.ndarray)

    GOOD = "GOOD"
    SLOUCHING = "SLOUCHING"
    FORWARD_HEAD = "FORWARD_HEAD"
    NECK_STRAIN = "NECK_STRAIN"
    UNKNOWN = "UNKNOWN"

    def __init__(self, config: dict = None, parent=None):
        super().__init__(parent)
        cfg = config or {}
        p   = cfg.get("posture", {})
        self.detection_confidence   = cfg.get("processing", {}).get("detection_confidence", 0.5)
        self.slouch_threshold       = p.get("slouch_threshold", 155.0)
        self.forward_head_threshold = p.get("forward_head_threshold", 130.0)
        self.neck_strain_threshold  = p.get("neck_strain_threshold", 100.0)
        self._running    = False
        self._frame: Optional[np.ndarray] = None
        self._landmarker = None
        self._ts         = 0   # monotonic timestamp for VIDEO mode

    def process_frame(self, frame: np.ndarray) -> None:
        self._frame = frame

    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    def run(self) -> None:
        logger.info("PostureDetector started")
        try:
            model_path   = _ensure_pose_model()
            base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
            options = mp_vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.VIDEO,
                num_poses=1,
                min_pose_detection_confidence=self.detection_confidence,
                min_pose_presence_confidence=self.detection_confidence,
                min_tracking_confidence=self.detection_confidence,
            )
            self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:
            logger.error("Failed to initialise PoseLandmarker: %s", exc)
            return
        self._running = True
        while self._running:
            if self._frame is None:
                time.sleep(0.03)
                continue
            frame = self._frame.copy()
            self._frame = None
            result = self._analyze(frame)
            if result:
                self.posture_detected.emit(result)
            time.sleep(0.05)
        if self._landmarker:
            self._landmarker.close()
        logger.info("PostureDetector stopped")

    def _analyze(self, frame: np.ndarray) -> Optional[dict]:
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._ts += 33   # monotonically increasing ~30 fps
        try:
            result = self._landmarker.detect_for_video(mp_image, self._ts)
        except Exception as exc:
            logger.debug("Pose inference error: %s", exc)
            self.frame_processed.emit(frame.copy())
            return None

        annotated = frame.copy()
        if not result.pose_landmarks:
            self.frame_processed.emit(annotated)
            return {
                "status": self.UNKNOWN, "neck_angle": None,
                "shoulder_alignment": None, "confidence": 0.0,
                "timestamp": time.time(),
            }

        lms  = result.pose_landmarks[0]
        h, w = frame.shape[:2]

        def pt(idx):
            lm = lms[idx]
            return np.array([lm.x * w, lm.y * h])

        ear_mid      = (pt(LEFT_EAR) + pt(RIGHT_EAR)) / 2
        shoulder_mid = (pt(LEFT_SHOULDER) + pt(RIGHT_SHOULDER)) / 2
        hip_mid      = (pt(LEFT_HIP) + pt(RIGHT_HIP)) / 2
        ls = pt(LEFT_SHOULDER); rs = pt(RIGHT_SHOULDER)

        neck_angle = self._calc_angle(ear_mid, shoulder_mid, hip_mid)
        sdiff  = abs(ls[1] - rs[1])
        swidth = max(np.linalg.norm(ls - rs), 1e-6)
        shoulder_alignment = math.degrees(math.asin(min(sdiff / swidth, 1.0)))
        status = self._classify(neck_angle)

        vis_idx    = [LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]
        confidence = sum(getattr(lms[i], "visibility", 1.0) or 1.0 for i in vis_idx) / len(vis_idx)

        # Draw skeleton
        for idx in vis_idx:
            cv2.circle(annotated, (int(lms[idx].x * w), int(lms[idx].y * h)), 5, (0, 255, 0), -1)
        for a, b in [(LEFT_EAR, LEFT_SHOULDER), (RIGHT_EAR, RIGHT_SHOULDER),
                     (LEFT_SHOULDER, RIGHT_SHOULDER), (LEFT_SHOULDER, LEFT_HIP),
                     (RIGHT_SHOULDER, RIGHT_HIP), (LEFT_HIP, RIGHT_HIP)]:
            cv2.line(annotated,
                     (int(lms[a].x * w), int(lms[a].y * h)),
                     (int(lms[b].x * w), int(lms[b].y * h)), (0, 200, 255), 2)

        colour = (0, 255, 0) if status == self.GOOD else (0, 0, 255)
        cv2.putText(annotated, f"Neck: {neck_angle:.1f}deg  [{status}]",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2)
        self.frame_processed.emit(annotated)
        return {
            "status": status,
            "neck_angle": round(neck_angle, 2),
            "shoulder_alignment": round(shoulder_alignment, 2),
            "confidence": round(confidence, 3),
            "timestamp": time.time(),
        }

    def _classify(self, neck_angle: float) -> str:
        if neck_angle < self.neck_strain_threshold:
            return self.NECK_STRAIN
        if neck_angle < self.forward_head_threshold:
            return self.FORWARD_HEAD
        if neck_angle < self.slouch_threshold:
            return self.SLOUCHING
        return self.GOOD

    @staticmethod
    def _calc_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        ba = a - b
        bc = c - b
        cos_val = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9)
        return math.degrees(math.acos(float(np.clip(cos_val, -1.0, 1.0))))
