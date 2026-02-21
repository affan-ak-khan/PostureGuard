"""
test_data_manager.py — Unit tests for src/data_manager.py
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_manager import DataManager


@pytest.fixture
def dm(tmp_path):
    """Provide a fresh in-memory-backed DataManager for each test."""
    db = tmp_path / "test.db"
    manager = DataManager(str(db))
    manager.initialize_database()
    return manager


class TestInitializeDatabase:
    def test_double_init_is_idempotent(self, dm):
        """Calling initialize_database twice must not raise."""
        dm.initialize_database()

    def test_default_settings_row_created(self, dm):
        settings = dm.get_settings()
        assert isinstance(settings, dict)
        assert "theme" in settings


class TestSessionLifecycle:
    def test_create_session_returns_int(self, dm):
        sid = dm.create_session()
        assert isinstance(sid, int)
        assert sid > 0

    def test_multiple_sessions_have_unique_ids(self, dm):
        ids = [dm.create_session() for _ in range(5)]
        assert len(set(ids)) == 5

    def test_end_session_marks_completed(self, dm):
        sid = dm.create_session()
        dm.end_session(sid)
        stats = dm.get_session_stats(sid)
        assert stats is not None
        assert stats["status"] == "completed"

    def test_end_nonexistent_session_does_not_raise(self, dm):
        dm.end_session(99999)   # Should silently succeed


class TestEventLogging:
    def test_log_posture_event(self, dm):
        sid = dm.create_session()
        dm.log_posture_event(sid, {
            "status": "SLOUCHING", "neck_angle": 28.0, "shoulder_alignment": 5.0
        })
        # No exception means success; verify via end_session score
        dm.end_session(sid)
        stats = dm.get_session_stats(sid)
        assert stats["total_alerts"] >= 1

    def test_log_drowsiness_event(self, dm):
        sid = dm.create_session()
        dm.log_drowsiness_event(sid, {
            "status": "DROWSY", "ear": 0.18, "blink_rate": 25
        })
        dm.end_session(sid)
        stats = dm.get_session_stats(sid)
        assert stats["total_alerts"] >= 1

    def test_posture_score_all_good(self, dm):
        sid = dm.create_session()
        for _ in range(10):
            dm.log_posture_event(sid, {
                "status": "GOOD", "neck_angle": 65.0, "shoulder_alignment": 2.0
            })
        dm.end_session(sid)
        stats = dm.get_session_stats(sid)
        assert stats["posture_score"] == 100.0

    def test_posture_score_all_bad(self, dm):
        sid = dm.create_session()
        for _ in range(10):
            dm.log_posture_event(sid, {
                "status": "SLOUCHING", "neck_angle": 20.0, "shoulder_alignment": 10.0
            })
        dm.end_session(sid)
        stats = dm.get_session_stats(sid)
        assert stats["posture_score"] == 0.0


class TestGetHistory:
    def test_returns_dict(self, dm):
        hist = dm.get_history(days=7)
        assert isinstance(hist, dict)

    def test_empty_history_has_zero_sessions(self, dm):
        hist = dm.get_history(days=7)
        assert hist["sessions"] == 0

    def test_counts_session(self, dm):
        sid = dm.create_session()
        dm.end_session(sid)
        hist = dm.get_history(days=7)
        assert hist["sessions"] >= 1

    def test_daily_scores_key_exists(self, dm):
        hist = dm.get_history(days=7)
        assert "daily_scores" in hist
        assert "daily_posture_alerts" in hist
        assert "daily_drowsy_alerts" in hist


class TestSettings:
    def test_save_and_retrieve_theme(self, dm):
        dm.save_settings({"theme": "light"})
        s = dm.get_settings()
        assert s["theme"] == "light"

    def test_save_custom_extra_field(self, dm):
        dm.save_settings({"theme": "dark", "my_custom_key": "hello"})
        s = dm.get_settings()
        assert s["my_custom_key"] == "hello"

    def test_save_volume(self, dm):
        dm.save_settings({"alert_volume": 80})
        s = dm.get_settings()
        assert s["alert_volume"] == 80


class TestExport:
    def test_export_csv(self, dm, tmp_path):
        sid = dm.create_session()
        dm.end_session(sid)
        out = tmp_path / "export.csv"
        result = dm.export_data(str(out), "csv")
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    def test_export_json(self, dm, tmp_path):
        sid = dm.create_session()
        dm.end_session(sid)
        out = tmp_path / "export.json"
        result = dm.export_data(str(out), "json")
        assert Path(result).exists()

    def test_export_empty_csv(self, dm, tmp_path):
        """Export with no sessions should not raise."""
        out = tmp_path / "empty.csv"
        dm.export_data(str(out), "csv")   # may or may not create file, but must not raise
