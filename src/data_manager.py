"""
data_manager.py
SQLite database layer for PostureGuard.
"""

import csv
import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger("PostureGuard.db")

# Python 3.12 deprecates the default datetime adapter/converter.  Register
# explicit replacements so the deprecation warnings are never emitted.
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat(sep=" "))
sqlite3.register_converter(
    "TIMESTAMP",
    lambda b: datetime.fromisoformat(b.decode()),
)


class DataManager:
    """Centralised database access object."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS sessions (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time        TIMESTAMP NOT NULL,
        end_time          TIMESTAMP,
        duration_minutes  INTEGER,
        posture_score     REAL,
        total_alerts      INTEGER DEFAULT 0,
        status            TEXT DEFAULT 'active'
    );
    CREATE TABLE IF NOT EXISTS posture_events (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id          INTEGER,
        timestamp           TIMESTAMP NOT NULL,
        event_type          TEXT,
        neck_angle          REAL,
        shoulder_alignment  REAL,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    CREATE TABLE IF NOT EXISTS drowsiness_events (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id       INTEGER,
        timestamp        TIMESTAMP NOT NULL,
        eye_aspect_ratio REAL,
        blink_rate       INTEGER,
        drowsiness_level TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    CREATE TABLE IF NOT EXISTS user_settings (
        id                       INTEGER PRIMARY KEY,
        posture_sensitivity      INTEGER DEFAULT 5,
        drowsiness_sensitivity   INTEGER DEFAULT 5,
        alert_sound_enabled      BOOLEAN DEFAULT 1,
        alert_volume             INTEGER DEFAULT 70,
        check_interval_seconds   INTEGER DEFAULT 5,
        theme                    TEXT DEFAULT 'dark',
        settings_json            TEXT DEFAULT '{}'
    );
    """

    def __init__(self, db_path: str, mongodb_manager=None):
        self.db_path = str(db_path)
        self._mongo = mongodb_manager  # Optional MongoDBManager instance

    def initialize_database(self) -> None:
        with self._connection() as conn:
            conn.executescript(self.SCHEMA)
            conn.execute("INSERT OR IGNORE INTO user_settings (id) VALUES (1)")
            conn.commit()
        logger.info("Database schema ready at %s", self.db_path)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def set_mongodb(self, mongodb_manager) -> None:
        """Attach a MongoDBManager for cloud sync."""
        self._mongo = mongodb_manager

    def _mongo_async(self, fn, *args, **kwargs) -> None:
        """Run a MongoDB operation in a background thread (fire-and-forget)."""
        if self._mongo and self._mongo.is_connected:
            threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()

    def create_session(self) -> int:
        now = datetime.now()
        with self._connection() as conn:
            cur = conn.execute(
                "INSERT INTO sessions (start_time, status) VALUES (?, 'active')", (now,)
            )
            conn.commit()
            sid = cur.lastrowid
            self._mongo_async(self._mongo_create_session, sid)
            return sid

    def _mongo_create_session(self, session_id: int) -> None:
        try:
            self._mongo.create_session(session_id)
        except Exception as exc:
            logger.warning("MongoDB create_session failed: %s", exc)

    def end_session(self, session_id: int) -> None:
        now = datetime.now()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT start_time FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                return
            start = row["start_time"]
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            duration_minutes = max(int((now - start).total_seconds() / 60), 0)

            events = conn.execute(
                "SELECT event_type FROM posture_events WHERE session_id = ?", (session_id,)
            ).fetchall()
            total = len(events)
            good = sum(1 for e in events if e["event_type"] == "GOOD")
            posture_score = round((good / total) * 100, 1) if total > 0 else 100.0

            alerts = conn.execute(
                "SELECT COUNT(*) as cnt FROM posture_events WHERE session_id = ? AND event_type != 'GOOD'",
                (session_id,),
            ).fetchone()["cnt"]
            drows = conn.execute(
                "SELECT COUNT(*) as cnt FROM drowsiness_events WHERE session_id = ? AND drowsiness_level != 'ALERT'",
                (session_id,),
            ).fetchone()["cnt"]

            conn.execute(
                "UPDATE sessions SET end_time=?, duration_minutes=?, posture_score=?, total_alerts=?, status='completed' WHERE id=?",
                (now, duration_minutes, posture_score, alerts + drows, session_id),
            )
            conn.commit()
            self._mongo_async(
                self._mongo_end_session, session_id, posture_score,
                alerts + drows, duration_minutes,
            )

    def _mongo_end_session(self, session_id, score, alerts, duration):
        try:
            self._mongo.end_session(session_id, posture_score=score,
                                    total_alerts=alerts, duration_minutes=duration)
        except Exception as exc:
            logger.warning("MongoDB end_session failed: %s", exc)

    def log_posture_event(self, session_id: int, event_data: dict) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO posture_events (session_id, timestamp, event_type, neck_angle, shoulder_alignment) VALUES (?,?,?,?,?)",
                (session_id, datetime.now(), event_data.get("status"), event_data.get("neck_angle"), event_data.get("shoulder_alignment")),
            )
            conn.commit()
        self._mongo_async(self._mongo_log_posture, session_id, dict(event_data))

    def _mongo_log_posture(self, session_id, data):
        try:
            self._mongo.log_posture_event(session_id, data)
        except Exception as exc:
            logger.warning("MongoDB log_posture_event failed: %s", exc)

    def log_drowsiness_event(self, session_id: int, event_data: dict) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO drowsiness_events (session_id, timestamp, eye_aspect_ratio, blink_rate, drowsiness_level) VALUES (?,?,?,?,?)",
                (session_id, datetime.now(), event_data.get("ear"), event_data.get("blink_rate"), event_data.get("status", "ALERT")),
            )
            conn.commit()
        self._mongo_async(self._mongo_log_drowsiness, session_id, dict(event_data))

    def _mongo_log_drowsiness(self, session_id, data):
        try:
            self._mongo.log_drowsiness_event(session_id, data)
        except Exception as exc:
            logger.warning("MongoDB log_drowsiness_event failed: %s", exc)

    def get_session_stats(self, session_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def get_history(self, days: int = 7) -> Dict[str, Any]:
        """Return aggregate stats for the last *days* days (used by dashboard & main window)."""
        cutoff = datetime.now() - timedelta(days=days)
        with self._connection() as conn:
            sessions = conn.execute(
                "SELECT * FROM sessions WHERE start_time >= ? ORDER BY start_time DESC",
                (cutoff,),
            ).fetchall()

            n = len(sessions)
            avg_score = (
                sum(r["posture_score"] or 0 for r in sessions) / n if n else 0
            )
            good_pct = avg_score  # posture_score IS the good-posture percentage

            # Posture alert counts  (non-GOOD posture events)
            p_rows = conn.execute(
                "SELECT timestamp FROM posture_events "
                "WHERE timestamp >= ? AND event_type != 'GOOD'",
                (cutoff,),
            ).fetchall()
            d_rows = conn.execute(
                "SELECT timestamp FROM drowsiness_events "
                "WHERE timestamp >= ? AND drowsiness_level != 'ALERT'",
                (cutoff,),
            ).fetchall()

            def _day_key(ts_str):
                try:
                    return str(ts_str)[:10]
                except Exception:
                    return "unknown"

            # Daily breakdowns
            daily_posture_alerts: Dict[str, int] = {}
            for r in p_rows:
                k = _day_key(r["timestamp"])
                daily_posture_alerts[k] = daily_posture_alerts.get(k, 0) + 1

            daily_drowsy_alerts: Dict[str, int] = {}
            for r in d_rows:
                k = _day_key(r["timestamp"])
                daily_drowsy_alerts[k] = daily_drowsy_alerts.get(k, 0) + 1

            # Daily posture scores
            daily_scores: Dict[str, float] = {}
            for row in sessions:
                k = _day_key(row["start_time"])
                existing = daily_scores.get(k, [])
                if isinstance(existing, list):
                    existing.append(row["posture_score"] or 0)
                    daily_scores[k] = existing  # type: ignore
            daily_scores = {
                k: round(sum(v) / len(v), 1) if isinstance(v, list) else v
                for k, v in daily_scores.items()
            }

            # Posture distribution (count of each type)
            posture_distribution: Dict[str, int] = {}
            all_p_events = conn.execute(
                "SELECT event_type FROM posture_events WHERE timestamp >= ?",
                (cutoff,),
            ).fetchall()
            for r in all_p_events:
                et = r["event_type"] or "UNKNOWN"
                posture_distribution[et] = posture_distribution.get(et, 0) + 1

            # Daily average neck angle
            neck_rows = conn.execute(
                "SELECT timestamp, neck_angle FROM posture_events "
                "WHERE timestamp >= ? AND neck_angle IS NOT NULL",
                (cutoff,),
            ).fetchall()
            daily_neck_raw: Dict[str, list] = {}
            for r in neck_rows:
                k = _day_key(r["timestamp"])
                daily_neck_raw.setdefault(k, []).append(r["neck_angle"])
            daily_avg_neck_angle = {
                k: round(sum(v) / len(v), 1)
                for k, v in daily_neck_raw.items()
            }

            return {
                "sessions":              n,
                "avg_posture_score":     round(avg_score, 1),
                "good_pct":              round(good_pct, 1),
                "posture_alerts":        len(p_rows),
                "drowsy_alerts":         len(d_rows),
                "daily_scores":          daily_scores,
                "daily_posture_alerts":  daily_posture_alerts,
                "daily_drowsy_alerts":   daily_drowsy_alerts,
                "posture_distribution":  posture_distribution,
                "daily_avg_neck_angle":  daily_avg_neck_angle,
            }

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY start_time DESC").fetchall()
            return [dict(r) for r in rows]

    def get_settings(self) -> Dict[str, Any]:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM user_settings WHERE id = 1").fetchone()
            if not row:
                return {}
            data = dict(row)
            # Merge extra JSON settings on top
            try:
                extra = json.loads(data.pop("settings_json", "{}") or "{}")
            except Exception:
                extra = {}
            data.update(extra)
            return data

    def save_settings(self, settings: dict) -> None:
        specific_cols = {
            "posture_sensitivity", "drowsiness_sensitivity",
            "alert_sound_enabled", "alert_volume", "check_interval_seconds", "theme",
        }
        specific = {k: v for k, v in settings.items() if k in specific_cols}
        extra    = {k: v for k, v in settings.items() if k not in specific_cols}
        update_parts = {**specific, "settings_json": json.dumps(extra)}
        cols   = ", ".join(f"{k} = ?" for k in update_parts)
        values = list(update_parts.values()) + [1]
        with self._connection() as conn:
            conn.execute(f"UPDATE user_settings SET {cols} WHERE id = ?", values)
            conn.commit()
        self._mongo_async(self._mongo_save_settings, dict(settings))

    def _mongo_save_settings(self, settings):
        try:
            self._mongo.save_settings(settings)
        except Exception as exc:
            logger.warning("MongoDB save_settings failed: %s", exc)

    def export_data(self, output_path: str, fmt: str = "csv") -> str:
        from pathlib import Path
        sessions = self.get_all_sessions()
        out = Path(output_path)
        if fmt == "json":
            out = out.with_suffix(".json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(sessions, f, indent=2, default=str)
        else:
            out = out.with_suffix(".csv")
            if sessions:
                with open(out, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=sessions[0].keys())
                    writer.writeheader()
                    writer.writerows(sessions)
        return str(out)
