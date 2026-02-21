"""
test_eye_monitor.py — Unit tests for EyeMonitor's pure logic methods.
No camera or MediaPipe model download is required.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eye_monitor import EyeMonitor


@pytest.fixture(scope="session")
def qapp():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def monitor(qapp):
    cfg = {
        "eye_monitor": {
            "ear_threshold": 0.25,
            "tired_threshold": 0.28,
            "consecutive_frames": 20,
            "tired_frames": 10,
        },
        "processing": {"detection_confidence": 0.5},
    }
    return EyeMonitor(cfg)


class TestEyeAspectRatio:
    """Test the EAR calculation with known geometry."""

    def _make_open_eye(self):
        """Construct a "wide open" eye: horizontal width 10, vertical height 4."""
        return [
            np.array([0.0, 5.0]),    # 0 left corner
            np.array([3.0, 7.0]),    # 1 upper-left
            np.array([7.0, 7.0]),    # 2 upper-right
            np.array([10.0, 5.0]),   # 3 right corner
            np.array([7.0, 3.0]),    # 4 lower-right
            np.array([3.0, 3.0]),    # 5 lower-left
        ]

    def _make_closed_eye(self):
        """Construct a closed eye: upper & lower pairs overlap at the same y."""
        # 0=left-corner, 3=right-corner define width;
        # pairs (1,5) and (2,4) are overlapping (eye shut)
        return [
            np.array([0.0, 5.0]),    # 0 left corner
            np.array([3.0, 5.0]),    # 1 upper-left  (same y as lower-left)
            np.array([7.0, 5.0]),    # 2 upper-right (same y as lower-right)
            np.array([10.0, 5.0]),   # 3 right corner
            np.array([7.0, 5.0]),    # 4 lower-right (overlaps 2)
            np.array([3.0, 5.0]),    # 5 lower-left  (overlaps 1)
        ]

    def test_open_eye_ear_above_threshold(self):
        eye = self._make_open_eye()
        ear = EyeMonitor._eye_aspect_ratio(eye)
        assert ear > 0.25

    def test_closed_eye_ear_near_zero(self):
        eye = self._make_closed_eye()
        ear = EyeMonitor._eye_aspect_ratio(eye)
        assert ear < 0.05

    def test_ear_nonnegative(self):
        eye = self._make_open_eye()
        assert EyeMonitor._eye_aspect_ratio(eye) >= 0.0


class TestConstructor:
    def test_default_thresholds(self, qapp):
        m = EyeMonitor()
        assert m.ear_threshold == 0.25
        assert m.consecutive_frames == 20

    def test_custom_config(self, monitor):
        assert monitor.ear_threshold == 0.25
        assert monitor.tired_threshold == 0.28
        assert monitor.consecutive_frames == 20
        assert monitor.tired_frames == 10

    def test_not_running_initially(self, monitor):
        assert not monitor._running

    def test_blink_events_empty(self, monitor):
        assert len(monitor._blink_events) == 0


class TestDrowsinessConstants:
    def test_status_constants_exist(self):
        assert EyeMonitor.ALERT == "ALERT"
        assert EyeMonitor.TIRED == "TIRED"
        assert EyeMonitor.DROWSY == "DROWSY"
