"""
test_camera_handler.py — Unit tests for CameraHandler's constructor and config parsing.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.camera_handler import CameraHandler


@pytest.fixture(scope="session")
def qapp():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TestConstructorFromConfig:
    def test_default_params(self, qapp):
        h = CameraHandler()
        assert h.device_id == 0
        assert h.frame_width == 640
        assert h.frame_height == 480
        assert h.fps == 30
        assert h.skip_frames >= 1

    def test_config_dict_camera_keys(self, qapp):
        cfg = {
            "camera": {
                "device_id": 1,
                "frame_width": 1280,
                "frame_height": 720,
                "fps": 60,
            },
            "processing": {"skip_frames": 3},
        }
        h = CameraHandler(cfg)
        assert h.device_id == 1
        assert h.frame_width == 1280
        assert h.frame_height == 720
        assert h.fps == 60
        assert h.skip_frames == 3

    def test_config_dict_empty_uses_defaults(self, qapp):
        h = CameraHandler({})
        assert h.device_id == 0
        assert h.frame_width == 640
        assert h.frame_height == 480
        assert h.fps == 30
        assert h.skip_frames >= 1

    def test_skip_frames_minimum_1(self, qapp):
        cfg = {"camera": {}, "processing": {"skip_frames": 0}}
        h = CameraHandler(cfg)
        assert h.skip_frames == 1

    def test_not_running_initially(self, qapp):
        h = CameraHandler()
        assert not h._running

    def test_cap_none_initially(self, qapp):
        h = CameraHandler()
        assert h._cap is None


class TestConstructorLegacy:
    """Verify the integer device_id legacy calling convention still works."""

    def test_int_device_id(self, qapp):
        h = CameraHandler(2)
        assert h.device_id == 2
