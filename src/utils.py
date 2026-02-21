"""
utils.py
Shared helper functions for PostureGuard.
"""
import logging
import math
from typing import Tuple

import cv2
import numpy as np

logger = logging.getLogger("PostureGuard.utils")


def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Return angle in degrees at vertex b formed by segments a-b and c-b."""
    ba = a - b
    bc = c - b
    cos_val = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9)
    return math.degrees(math.acos(float(np.clip(cos_val, -1.0, 1.0))))


def euclidean_distance(p1: np.ndarray, p2: np.ndarray) -> float:
    return float(np.linalg.norm(p1 - p2))


def resize_frame(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)


def frame_to_qt_image(frame: np.ndarray):
    from PyQt5.QtGui import QImage
    if frame is None:
        return QImage()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    return QImage(rgb.data.tobytes(), w, h, ch * w, QImage.Format_RGB888)


def seconds_to_hms(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def score_to_grade(score: float) -> str:
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "F"


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
