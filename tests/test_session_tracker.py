"""
test_session_tracker.py — Unit tests for src/session_tracker.py
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def qapp():
    """Single QApplication for all Qt-based tests."""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def dm(tmp_path):
    from src.data_manager import DataManager
    db = tmp_path / "test.db"
    manager = DataManager(str(db))
    manager.initialize_database()
    return manager


@pytest.fixture
def tracker(qapp, dm):
    from src.session_tracker import SessionTracker
    return SessionTracker(dm)


@pytest.fixture
def tracker_config(qapp, dm):
    """Tracker created via config-dict constructor (as MainWindow does)."""
    from src.session_tracker import SessionTracker
    cfg = {"app_name": "Test"}
    return SessionTracker(cfg, dm)


class TestConstructor:
    def test_not_running_initially(self, tracker):
        assert not tracker.is_running

    def test_session_id_none_initially(self, tracker):
        assert tracker.session_id is None

    def test_config_dict_constructor(self, tracker_config):
        assert not tracker_config.is_running


class TestSessionLifecycle:
    def test_start_returns_positive_id(self, tracker):
        sid = tracker.start_session()
        assert isinstance(sid, int)
        assert sid > 0
        tracker.stop_session()

    def test_is_running_after_start(self, tracker):
        tracker.start_session()
        assert tracker.is_running
        tracker.stop_session()

    def test_not_running_after_stop(self, tracker):
        tracker.start_session()
        tracker.stop_session()
        assert not tracker.is_running

    def test_stop_returns_stats(self, tracker):
        tracker.start_session()
        stats = tracker.stop_session()
        assert isinstance(stats, dict)
        assert "posture_score" in stats
        assert "elapsed" in stats

    def test_stop_without_start_returns_none(self, tracker):
        result = tracker.stop_session()
        assert result is None

    def test_double_start_resets_session(self, tracker):
        sid1 = tracker.start_session()
        sid2 = tracker.start_session()
        assert sid2 != sid1
        tracker.stop_session()


class TestPostureScore:
    def test_initial_score_is_100(self, tracker):
        tracker.start_session()
        assert tracker.get_posture_score() == 100.0
        tracker.stop_session()

    def test_all_good_posture_score_100(self, tracker):
        tracker.start_session()
        for _ in range(10):
            tracker.record_posture_event({"status": "GOOD", "neck_angle": 65.0})
        assert tracker.get_posture_score() == 100.0
        tracker.stop_session()

    def test_all_bad_posture_score_0(self, tracker):
        tracker.start_session()
        for _ in range(10):
            tracker.record_posture_event({"status": "SLOUCHING", "neck_angle": 25.0})
        assert tracker.get_posture_score() == 0.0
        tracker.stop_session()

    def test_mixed_posture_score(self, tracker):
        tracker.start_session()
        for _ in range(7):
            tracker.record_posture_event({"status": "GOOD", "neck_angle": 65.0})
        for _ in range(3):
            tracker.record_posture_event({"status": "SLOUCHING", "neck_angle": 25.0})
        score = tracker.get_posture_score()
        assert abs(score - 70.0) < 0.1
        tracker.stop_session()


class TestElapsedString:
    def test_format(self, tracker):
        tracker.start_session()
        elapsed = tracker.get_elapsed_str()
        parts = elapsed.split(":")
        assert len(parts) == 3
        tracker.stop_session()


class TestAlertCounting:
    def test_posture_alerts_counted(self, tracker):
        tracker.start_session()
        tracker.record_posture_event({"status": "SLOUCHING", "neck_angle": 25.0})
        tracker.record_posture_event({"status": "FORWARD_HEAD", "neck_angle": 20.0})
        stats = tracker.stop_session()
        assert stats["posture_alerts"] == 2

    def test_drowsiness_alerts_counted(self, tracker):
        tracker.start_session()
        tracker.record_drowsiness_event({"status": "DROWSY", "ear": 0.18, "blink_rate": 5})
        tracker.record_drowsiness_event({"status": "TIRED", "ear": 0.22, "blink_rate": 8})
        stats = tracker.stop_session()
        assert stats["drowsiness_alerts"] == 2

    def test_alert_event_ignored_when_not_running(self, tracker):
        """Recording events when not in a session should be a no-op."""
        tracker.record_posture_event({"status": "SLOUCHING"})
        # Should not raise
