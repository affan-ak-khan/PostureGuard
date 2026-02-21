"""
test_alert_system.py — Unit tests for src/alert_system.py
"""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.alert_system import AlertSystem, GENTLE, MODERATE, SEVERE


@pytest.fixture
def alert():
    return AlertSystem(sound_enabled=False, volume=50, snooze_duration=5)


@pytest.fixture
def alert_from_config():
    cfg = {
        "app_name": "TestGuard",
        "alerts": {
            "sound_enabled": False,
            "volume": 80,
            "snooze_duration": 30,
        }
    }
    return AlertSystem(cfg)


class TestConstructor:
    def test_defaults(self):
        a = AlertSystem()
        assert a.sound_enabled is True
        assert 0.0 <= a.volume <= 1.0
        assert a.snooze_duration == 60

    def test_explicit_params(self, alert):
        assert alert.sound_enabled is False
        assert abs(alert.volume - 0.5) < 1e-6
        assert alert.snooze_duration == 5

    def test_config_dict_constructor(self, alert_from_config):
        assert alert_from_config.sound_enabled is False
        assert abs(alert_from_config.volume - 0.80) < 1e-6
        assert alert_from_config.snooze_duration == 30
        assert alert_from_config.app_name == "TestGuard"

    def test_volume_clamped(self):
        a = AlertSystem(volume=200)
        assert a.volume == 1.0
        a2 = AlertSystem(volume=-50)
        assert a2.volume == 0.0


class TestSnooze:
    def test_snooze_blocks_alerts(self, alert, capsys):
        alert.snooze_alert("posture", 60)
        history_before = len(alert.get_alert_history())
        alert.trigger_posture_alert(GENTLE)
        history_after = len(alert.get_alert_history())
        assert history_after == history_before   # snoozed, no new entry

    def test_snooze_expires(self, alert):
        alert.snooze_alert("posture", 0)
        alert.trigger_posture_alert(GENTLE)
        assert len(alert.get_alert_history()) == 1

    def test_snooze_different_types_independent(self, alert):
        alert.snooze_alert("posture", 60)
        alert.trigger_drowsiness_alert("DROWSY")
        # Drowsiness not snoozed, so it should be recorded
        hist = alert.get_alert_history()
        assert any(h["type"] == "drowsiness" for h in hist)


class TestTriggerPostureAlert:
    def test_gentle_recorded(self, alert):
        alert.trigger_posture_alert(GENTLE)
        h = alert.get_alert_history()
        assert len(h) == 1
        assert h[0]["type"] == "posture"
        assert h[0]["level"] == GENTLE

    def test_moderate_recorded(self, alert):
        alert.trigger_posture_alert(MODERATE, neck_angle=25.0)
        h = alert.get_alert_history()
        assert h[0]["level"] == MODERATE

    def test_severe_recorded(self, alert):
        alert.trigger_posture_alert(SEVERE, neck_angle=10.0)
        h = alert.get_alert_history()
        assert h[0]["level"] == SEVERE


class TestTriggerDrowsinessAlert:
    def test_tired_recorded(self, alert):
        alert.trigger_drowsiness_alert("TIRED")
        h = alert.get_alert_history()
        assert len(h) == 1
        assert h[0]["type"] == "drowsiness"
        assert h[0]["level"] == "TIRED"

    def test_drowsy_recorded(self, alert):
        alert.trigger_drowsiness_alert("DROWSY")
        h = alert.get_alert_history()
        assert h[0]["level"] == "DROWSY"


class TestHistory:
    def test_history_capped_at_500(self, alert):
        for _ in range(510):
            alert.snooze_alert("posture", 0)
            alert.trigger_posture_alert(GENTLE)
        assert len(alert.get_alert_history()) == 500

    def test_set_volume(self, alert):
        alert.set_volume(100)
        assert alert.volume == 1.0
        alert.set_volume(0)
        assert alert.volume == 0.0
