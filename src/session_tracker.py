"""
session_tracker.py
Tracks an active monitoring session: elapsed time, alert counts, posture scores.
"""

import logging
import time
from typing import Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from src.data_manager import DataManager

logger = logging.getLogger("PostureGuard.session")


class SessionTracker(QObject):
    """
    Manages the lifecycle of a monitoring session.

    Signals:
        tick (int): Elapsed seconds every second.
        stats_updated (dict): Session stats every 10 s.
        session_ended (dict): Final stats on stop.
    """

    tick = pyqtSignal(int)
    stats_updated = pyqtSignal(dict)
    session_ended = pyqtSignal(dict)

    def __init__(self, config_or_dm, data_manager: DataManager = None, autosave_interval: int = 30, parent=None):
        super().__init__(parent)
        # Accept (config, data_manager) or (data_manager,) calling conventions
        if isinstance(config_or_dm, DataManager):
            self._dm = config_or_dm
        else:
            # config_or_dm is a config dict; data_manager is the real DM
            self._dm = data_manager
        self._autosave_interval = autosave_interval
        self._session_id: Optional[int] = None
        self._elapsed = 0
        self._is_running = False
        self._posture_alerts = 0
        self._drowsiness_alerts = 0
        self._good_posture_count = 0
        self._total_posture_events = 0
        self._last_posture: dict = {}
        self._last_drowsiness: dict = {}

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._on_tick)

    @property
    def session_id(self) -> Optional[int]:
        return self._session_id

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start_session(self) -> int:
        if self._is_running:
            self.stop_session()
        self._session_id = self._dm.create_session()
        self._elapsed = 0
        self._posture_alerts = 0
        self._drowsiness_alerts = 0
        self._good_posture_count = 0
        self._total_posture_events = 0
        self._is_running = True
        self._tick_timer.start()
        logger.info("Session %d started", self._session_id)
        return self._session_id

    def stop_session(self) -> Optional[dict]:
        if not self._is_running or self._session_id is None:
            return None
        self._tick_timer.stop()
        self._is_running = False
        self._dm.end_session(self._session_id)
        stats = self._build_stats()
        self.session_ended.emit(stats)
        logger.info("Session %d stopped", self._session_id)
        return stats

    def record_posture_event(self, data: dict) -> None:
        if not self._is_running or self._session_id is None:
            return
        self._last_posture = data
        self._total_posture_events += 1
        status = data.get("status", "")
        if status == "GOOD":
            self._good_posture_count += 1
        elif status in ("SLOUCHING", "FORWARD_HEAD", "NECK_STRAIN"):
            self._posture_alerts += 1
        self._dm.log_posture_event(self._session_id, data)

    def record_drowsiness_event(self, data: dict) -> None:
        if not self._is_running or self._session_id is None:
            return
        self._last_drowsiness = data
        if data.get("status") in ("TIRED", "DROWSY"):
            self._drowsiness_alerts += 1
        self._dm.log_drowsiness_event(self._session_id, data)

    def get_posture_score(self) -> float:
        if self._total_posture_events == 0:
            return 100.0
        return round((self._good_posture_count / self._total_posture_events) * 100, 1)

    def get_elapsed_str(self) -> str:
        h, rem = divmod(self._elapsed, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _on_tick(self) -> None:
        self._elapsed += 1
        self.tick.emit(self._elapsed)
        if self._elapsed % 10 == 0:
            self.stats_updated.emit(self._build_stats())

    def _build_stats(self) -> dict:
        return {
            "session_id": self._session_id,
            "elapsed": self._elapsed,
            "elapsed_str": self.get_elapsed_str(),
            "posture_score": self.get_posture_score(),
            "posture_alerts": self._posture_alerts,
            "drowsiness_alerts": self._drowsiness_alerts,
            "total_alerts": self._posture_alerts + self._drowsiness_alerts,
            "last_posture": self._last_posture,
            "last_drowsiness": self._last_drowsiness,
        }
