"""
eye_monitor.py
Drowsiness detection via MediaPipe Face Landmarker (Tasks API) and Eye Aspect Ratio.
"""

import logging
import time
import urllib.request
from collections import deque
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision

logger = logging.getLogger("PostureGuard.eyes")

FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)
MODELS_DIR = Path(__file__).resolve().parent.parent / "assets" / "models"

LEFT_EYE_IDX  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]


def _ensure_face_model() -> str:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "face_landmarker.task"
    if not model_path.exists():
        logger.info("Downloading face landmark model (~45 MB)...")
        urllib.request.urlretrieve(FACE_MODEL_URL, str(model_path))
        logger.info("Face model saved to %s", model_path)
    return str(model_path)


class EyeMonitor(QThread):
    """
    Processes camera frames and detects drowsiness via EAR.

    Signals:
        drowsiness_detected (dict): Drowsiness result.
        frame_processed (np.ndarray): Annotated frame.
    """

    drowsiness_detected = pyqtSignal(dict)
    frame_processed = pyqtSignal(np.ndarray)

    ALERT = "ALERT"
    TIRED = "TIRED"
    DROWSY = "DROWSY"

    def __init__(self, config: dict = None, parent=None):
        super().__init__(parent)
        cfg = config or {}
        e = cfg.get("eye_monitor", {})
        self.ear_threshold = e.get("ear_threshold", 0.25)
        self.tired_threshold = e.get("tired_threshold", 0.28)
        self.consecutive_frames = e.get("consecutive_frames", 20)
        self.tired_frames = e.get("tired_frames", 10)
        self.detection_confidence = cfg.get("processing", {}).get("detection_confidence", 0.5)
        self._running = False
        self._frame: Optional[np.ndarray] = None
        self._landmarker = None
        self._blink_events: deque = deque()
        self._in_blink = False
        self._consecutive_closed = 0
        self._ts = 0   # monotonic timestamp for VIDEO mode

    def process_frame(self, frame: np.ndarray) -> None:
        self._frame = frame

    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    def run(self) -> None:
        logger.info("EyeMonitor started")
        try:
            model_path   = _ensure_face_model()
            base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
            options = mp_vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.VIDEO,
                num_faces=1,
                min_face_detection_confidence=self.detection_confidence,
                min_face_presence_confidence=self.detection_confidence,
                min_tracking_confidence=self.detection_confidence,
            )
            self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        except Exception as exc:
            logger.error("Failed to initialise FaceLandmarker: %s", exc)
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
                self.drowsiness_detected.emit(result)
            time.sleep(0.05)
        if self._landmarker:
            self._landmarker.close()
        logger.info("EyeMonitor stopped")

    def _analyze(self, frame: np.ndarray) -> Optional[dict]:
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._ts += 33
        try:
            result = self._landmarker.detect_for_video(mp_image, self._ts)
        except Exception as exc:
            logger.debug("Face inference error: %s", exc)
            return None

        if not result.face_landmarks:
            return {"status": self.ALERT, "ear": None, "blink_rate": 0,
                    "drowsiness_level": self.ALERT, "consecutive_closed": 0,
                    "timestamp": time.time()}

        face_lm = result.face_landmarks[0]
        h, w    = frame.shape[:2]

        def lm_pt(idx):
            l = face_lm[idx]
            return np.array([l.x * w, l.y * h])

        left_pts  = [lm_pt(i) for i in LEFT_EYE_IDX]
        right_pts = [lm_pt(i) for i in RIGHT_EYE_IDX]
        left_ear  = self._eye_aspect_ratio(left_pts)
        right_ear = self._eye_aspect_ratio(right_pts)
        avg_ear   = (left_ear + right_ear) / 2.0

        if avg_ear < self.ear_threshold:
            self._consecutive_closed += 1
            if not self._in_blink:
                self._in_blink = True
                self._blink_events.append(time.time())
        else:
            self._in_blink = False
            self._consecutive_closed = 0

        now = time.time()
        while self._blink_events and (now - self._blink_events[0]) > 60:
            self._blink_events.popleft()
        blink_rate = len(self._blink_events)

        if self._consecutive_closed >= self.consecutive_frames:
            status = self.DROWSY
        elif self._consecutive_closed >= self.tired_frames and avg_ear < self.tired_threshold:
            status = self.TIRED
        else:
            status = self.ALERT

        annotated = frame.copy()
        cmap = {self.ALERT: (0, 255, 0), self.TIRED: (0, 165, 255), self.DROWSY: (0, 0, 255)}
        colour = cmap[status]
        for pts in [left_pts, right_pts]:
            hull = cv2.convexHull(np.array(pts, dtype=np.int32))
            cv2.drawContours(annotated, [hull], -1, colour, 1)
        cv2.putText(annotated, f"EAR:{avg_ear:.2f} [{status}] Blinks:{blink_rate}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, colour, 2)
        self.frame_processed.emit(annotated)

        return {"status": status, "ear": round(avg_ear, 4), "blink_rate": blink_rate,
                "drowsiness_level": status, "consecutive_closed": self._consecutive_closed,
                "timestamp": now}

    @staticmethod
    def _eye_aspect_ratio(eye: list) -> float:
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        return (A + B) / (2.0 * max(C, 1e-6))
