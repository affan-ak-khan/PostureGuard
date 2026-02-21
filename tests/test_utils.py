"""
test_utils.py — Unit tests for src/utils.py
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# Make the PostureGuard package importable from the tests directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import (
    calculate_angle,
    clamp,
    euclidean_distance,
    frame_to_qt_image,
    score_to_grade,
    seconds_to_hms,
)


class TestCalculateAngle:
    def test_right_angle(self):
        a = np.array([0.0, 1.0])
        b = np.array([0.0, 0.0])
        c = np.array([1.0, 0.0])
        angle = calculate_angle(a, b, c)
        assert abs(angle - 90.0) < 1e-6

    def test_straight_line(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        c = np.array([2.0, 0.0])
        angle = calculate_angle(a, b, c)
        assert abs(angle - 180.0) < 0.01

    def test_zero_angle(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 0.0])
        c = np.array([1.0, 0.0])
        # a == c means angle is 0
        angle = calculate_angle(a, b, c)
        assert angle < 0.01

    def test_45_degree(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 0.0])
        c = np.array([1.0, 1.0])
        angle = calculate_angle(a, b, c)
        assert abs(angle - 45.0) < 1e-6

    def test_degenerate_same_points(self):
        """Should not raise even when vectors are degenerate."""
        a = np.array([0.0, 0.0])
        b = np.array([0.0, 0.0])
        c = np.array([0.0, 0.0])
        angle = calculate_angle(a, b, c)
        assert 0.0 <= angle <= 180.0


class TestSecondsToHms:
    def test_zero(self):
        assert seconds_to_hms(0) == "00:00:00"

    def test_one_hour(self):
        assert seconds_to_hms(3600) == "01:00:00"

    def test_one_minute(self):
        assert seconds_to_hms(60) == "00:01:00"

    def test_mixed(self):
        assert seconds_to_hms(3661) == "01:01:01"

    def test_large(self):
        # 25 hours
        assert seconds_to_hms(25 * 3600) == "25:00:00"


class TestScoreToGrade:
    def test_a_plus(self):
        assert score_to_grade(95.0) == "A+"
        assert score_to_grade(90.0) == "A+"

    def test_a(self):
        assert score_to_grade(85.0) == "A"
        assert score_to_grade(80.0) == "A"

    def test_b(self):
        assert score_to_grade(75.0) == "B"
        assert score_to_grade(70.0) == "B"

    def test_c(self):
        assert score_to_grade(65.0) == "C"
        assert score_to_grade(60.0) == "C"

    def test_f(self):
        assert score_to_grade(59.9) == "F"
        assert score_to_grade(0.0) == "F"


class TestClamp:
    def test_within_range(self):
        assert clamp(5.0, 0.0, 10.0) == 5.0

    def test_below_min(self):
        assert clamp(-1.0, 0.0, 10.0) == 0.0

    def test_above_max(self):
        assert clamp(11.0, 0.0, 10.0) == 10.0

    def test_at_boundary(self):
        assert clamp(0.0, 0.0, 10.0) == 0.0
        assert clamp(10.0, 0.0, 10.0) == 10.0


class TestEuclideanDistance:
    def test_zero(self):
        a = np.array([0.0, 0.0])
        assert euclidean_distance(a, a) == 0.0

    def test_axis_aligned(self):
        a = np.array([0.0, 0.0])
        b = np.array([3.0, 4.0])
        assert abs(euclidean_distance(a, b) - 5.0) < 1e-9


class TestFrameToQtImage:
    def test_none_returns_empty(self):
        img = frame_to_qt_image(None)
        assert img.isNull()

    def test_valid_frame(self):
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        img = frame_to_qt_image(frame)
        assert not img.isNull()
        assert img.width() == 200
        assert img.height() == 100
