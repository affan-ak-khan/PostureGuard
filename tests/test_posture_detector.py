"""
test_posture_detector.py — Unit tests for PostureDetector's pure logic methods.
No camera or MediaPipe model download is required.
"""

import sys
import math
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.posture_detector import PostureDetector


@pytest.fixture(scope="session")
def qapp():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def detector(qapp):
    cfg = {
        "posture": {"slouch_threshold": 35.0, "forward_head_threshold": 20.0},
        "processing": {"detection_confidence": 0.5},
    }
    return PostureDetector(cfg)


class TestClassify:
    """Test the classification logic _classify(neck_angle) -> str."""

    def test_good_posture(self, detector):
        assert detector._classify(65.0) == PostureDetector.GOOD

    def test_slouching(self, detector):
        # Between forward_head_threshold and slouch_threshold
        assert detector._classify(30.0) == PostureDetector.SLOUCHING

    def test_forward_head(self, detector):
        # Below forward_head_threshold
        assert detector._classify(10.0) == PostureDetector.FORWARD_HEAD

    def test_boundary_at_slouch_threshold(self, detector):
        # Exactly at slouch_threshold: should be GOOD (not SLOUCHING)
        assert detector._classify(35.0) == PostureDetector.GOOD

    def test_boundary_at_forward_head_threshold(self, detector):
        # Exactly at forward_head_threshold: should be SLOUCHING (not FH)
        assert detector._classify(20.0) == PostureDetector.SLOUCHING

    def test_zero_angle(self, detector):
        assert detector._classify(0.0) == PostureDetector.FORWARD_HEAD


class TestCalcAngle:
    """Test the static angle calculator."""

    def test_right_angle(self):
        a = np.array([0.0, 1.0])
        b = np.array([0.0, 0.0])
        c = np.array([1.0, 0.0])
        angle = PostureDetector._calc_angle(a, b, c)
        assert abs(angle - 90.0) < 0.001

    def test_straight_line(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        c = np.array([2.0, 0.0])
        angle = PostureDetector._calc_angle(a, b, c)
        assert abs(angle - 180.0) < 0.01

    def test_symmetric(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 0.0])
        c = np.array([0.0, 1.0])
        angle_abc = PostureDetector._calc_angle(a, b, c)
        angle_cba = PostureDetector._calc_angle(c, b, a)
        assert abs(angle_abc - angle_cba) < 1e-9


class TestConstructorDefaults:
    def test_default_config(self, qapp):
        d = PostureDetector()
        assert d.slouch_threshold == 35.0
        assert d.forward_head_threshold == 30.0

    def test_custom_thresholds(self, qapp):
        cfg = {"posture": {"slouch_threshold": 40.0, "forward_head_threshold": 25.0}}
        d = PostureDetector(cfg)
        assert d.slouch_threshold == 40.0
        assert d.forward_head_threshold == 25.0

    def test_status_not_running(self, detector):
        assert not detector._running
