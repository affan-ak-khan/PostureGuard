"""
mongodb_manager.py
MongoDB cloud storage layer for PostureGuard.
Stores all session, posture, drowsiness, settings, and alert data per user
for analytics and multi-device sync.
"""

import logging
import platform
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PostureGuard.mongodb")

try:
    from pymongo import MongoClient, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False
    logger.warning("pymongo not installed — MongoDB sync disabled")


class MongoDBManager:
    """
    Cloud persistence layer that mirrors local SQLite data into MongoDB.

    Collections:
        users              – user profiles & machine info
        sessions           – monitoring sessions per user
        posture_events     – individual posture readings
        drowsiness_events  – individual drowsiness readings
        user_settings      – per-user app settings
        alerts             – alert history per user
        analytics_snapshots– daily analytics rollups
    """

    # Only save to MongoDB on state transitions or problem events.
    # Periodic "good" snapshots are saved at most once per this interval.
    _GOOD_STATE_SNAPSHOT_INTERVAL = timedelta(minutes=5)

    _BAD_POSTURE_STATUSES = {"SLOUCHING", "FORWARD_HEAD", "NECK_STRAIN"}
    _BAD_DROWSINESS_STATUSES = {"TIRED", "DROWSY"}

    def __init__(self, uri: str, db_name: str = "PostureGuard", user_id: str = None):
        self._uri = uri
        self._db_name = db_name
        self._user_id = user_id or self._generate_user_id()
        self._client: Optional[Any] = None
        self._db: Optional[Any] = None
        self._connected = False

        # State tracking to reduce MongoDB writes
        self._last_posture_status: Optional[str] = None
        self._last_drowsiness_status: Optional[str] = None
        self._last_posture_save: Optional[datetime] = None
        self._last_drowsiness_save: Optional[datetime] = None

    # ------------------------------------------------------------------ init
    def connect(self) -> bool:
        """Establish connection to MongoDB Atlas. Returns True on success."""
        if not HAS_PYMONGO:
            logger.error("pymongo is not installed. Run: pip install pymongo[srv]")
            return False
        try:
            self._client = MongoClient(
                self._uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )
            # Force a connection test
            self._client.admin.command("ping")
            self._db = self._client[self._db_name]
            self._connected = True
            self._ensure_indexes()
            self._register_user()
            logger.info("Connected to MongoDB Atlas — db=%s, user=%s", self._db_name, self._user_id)
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            logger.error("MongoDB connection failed: %s", exc)
            self._connected = False
            return False
        except Exception as exc:
            logger.error("Unexpected MongoDB error: %s", exc)
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._connected = False
            logger.info("MongoDB connection closed")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def user_id(self) -> str:
        return self._user_id

    @user_id.setter
    def user_id(self, value: str) -> None:
        self._user_id = value

    # -------------------------------------------------------------- indexes
    def _ensure_indexes(self) -> None:
        """Create indexes for efficient analytics queries."""
        try:
            self._db.sessions.create_index([("user_id", 1), ("start_time", DESCENDING)])
            self._db.posture_events.create_index([("user_id", 1), ("session_id", 1), ("timestamp", DESCENDING)])
            self._db.drowsiness_events.create_index([("user_id", 1), ("session_id", 1), ("timestamp", DESCENDING)])
            self._db.alerts.create_index([("user_id", 1), ("timestamp", DESCENDING)])
            self._db.user_settings.create_index("user_id", unique=True)
            self._db.users.create_index("user_id", unique=True)
            self._db.analytics_snapshots.create_index([("user_id", 1), ("date", DESCENDING)])
            logger.debug("MongoDB indexes ensured")
        except Exception as exc:
            logger.warning("Failed to create indexes: %s", exc)

    # ---------------------------------------------------------- user mgmt
    @staticmethod
    def _generate_user_id() -> str:
        """Generate a stable per-machine user ID."""
        node = uuid.getnode()
        return f"user_{node:012x}"

    def _register_user(self) -> None:
        """Upsert user profile document."""
        if not self._connected:
            return
        try:
            self._db.users.update_one(
                {"user_id": self._user_id},
                {"$set": {
                    "user_id": self._user_id,
                    "machine_name": platform.node(),
                    "os": platform.system(),
                    "os_version": platform.version(),
                    "last_active": datetime.utcnow(),
                    "app_version": "1.0.0",
                }, "$setOnInsert": {
                    "created_at": datetime.utcnow(),
                }},
                upsert=True,
            )
        except Exception as exc:
            logger.warning("Failed to register user: %s", exc)

    # ------------------------------------------------------------ sessions
    def create_session(self, local_session_id: int) -> Optional[str]:
        """Store a new session. Returns the MongoDB _id as string."""
        if not self._connected:
            return None
        # Reset state tracking for the new session
        self._last_posture_status = None
        self._last_drowsiness_status = None
        self._last_posture_save = None
        self._last_drowsiness_save = None
        try:
            doc = {
                "user_id": self._user_id,
                "local_session_id": local_session_id,
                "start_time": datetime.utcnow(),
                "end_time": None,
                "duration_minutes": 0,
                "posture_score": None,
                "total_alerts": 0,
                "status": "active",
                "created_at": datetime.utcnow(),
            }
            result = self._db.sessions.insert_one(doc)
            logger.debug("MongoDB session created: %s", result.inserted_id)
            return str(result.inserted_id)
        except Exception as exc:
            logger.warning("Failed to create MongoDB session: %s", exc)
            return None

    def end_session(self, local_session_id: int, posture_score: float = None,
                    total_alerts: int = 0, duration_minutes: int = 0) -> None:
        """Mark a session as completed with final stats."""
        if not self._connected:
            return
        try:
            self._db.sessions.update_one(
                {"user_id": self._user_id, "local_session_id": local_session_id, "status": "active"},
                {"$set": {
                    "end_time": datetime.utcnow(),
                    "duration_minutes": duration_minutes,
                    "posture_score": posture_score,
                    "total_alerts": total_alerts,
                    "status": "completed",
                    "updated_at": datetime.utcnow(),
                }},
            )
            # Generate daily analytics snapshot
            self._update_daily_snapshot()
            logger.debug("MongoDB session %d ended", local_session_id)
        except Exception as exc:
            logger.warning("Failed to end MongoDB session: %s", exc)

    # --------------------------------------------------------- posture events
    def _should_save_posture(self, status: str) -> bool:
        """Decide whether this posture reading is worth persisting.

        Saves on:
        - Any bad-posture event (SLOUCHING, FORWARD_HEAD, NECK_STRAIN)
        - State transitions (e.g. GOOD → SLOUCHING or SLOUCHING → GOOD)
        - Periodic "GOOD" snapshots (at most every 5 min) so analytics
          still reflect sustained good posture.
        """
        now = datetime.utcnow()
        # Always save bad posture
        if status in self._BAD_POSTURE_STATUSES:
            return True
        # Save state transitions
        if status != self._last_posture_status:
            return True
        # Periodic good-state snapshot
        if self._last_posture_save is None or (now - self._last_posture_save) >= self._GOOD_STATE_SNAPSHOT_INTERVAL:
            return True
        return False

    def log_posture_event(self, local_session_id: int, event_data: dict) -> None:
        """Store a posture event for analytics (only important events)."""
        if not self._connected:
            return
        status = event_data.get("status", "")
        if not self._should_save_posture(status):
            return
        try:
            now = datetime.utcnow()
            is_transition = (status != self._last_posture_status)
            doc = {
                "user_id": self._user_id,
                "session_id": local_session_id,
                "timestamp": now,
                "event_type": status,
                "neck_angle": event_data.get("neck_angle"),
                "shoulder_alignment": event_data.get("shoulder_alignment"),
                "confidence": event_data.get("confidence"),
                "is_transition": is_transition,
            }
            self._db.posture_events.insert_one(doc)
            self._last_posture_status = status
            self._last_posture_save = now
        except Exception as exc:
            logger.warning("Failed to log posture event to MongoDB: %s", exc)

    # ------------------------------------------------------ drowsiness events
    def _should_save_drowsiness(self, status: str) -> bool:
        """Decide whether this drowsiness reading is worth persisting.

        Saves on:
        - Any drowsiness event (TIRED, DROWSY)
        - State transitions (e.g. ALERT → DROWSY or DROWSY → ALERT)
        - Periodic "ALERT" snapshots (at most every 5 min).
        """
        now = datetime.utcnow()
        if status in self._BAD_DROWSINESS_STATUSES:
            return True
        if status != self._last_drowsiness_status:
            return True
        if self._last_drowsiness_save is None or (now - self._last_drowsiness_save) >= self._GOOD_STATE_SNAPSHOT_INTERVAL:
            return True
        return False

    def log_drowsiness_event(self, local_session_id: int, event_data: dict) -> None:
        """Store a drowsiness event for analytics (only important events)."""
        if not self._connected:
            return
        status = event_data.get("status", "ALERT")
        if not self._should_save_drowsiness(status):
            return
        try:
            now = datetime.utcnow()
            is_transition = (status != self._last_drowsiness_status)
            doc = {
                "user_id": self._user_id,
                "session_id": local_session_id,
                "timestamp": now,
                "eye_aspect_ratio": event_data.get("ear"),
                "blink_rate": event_data.get("blink_rate"),
                "drowsiness_level": status,
                "consecutive_closed": event_data.get("consecutive_closed", 0),
                "is_transition": is_transition,
            }
            self._db.drowsiness_events.insert_one(doc)
            self._last_drowsiness_status = status
            self._last_drowsiness_save = now
        except Exception as exc:
            logger.warning("Failed to log drowsiness event to MongoDB: %s", exc)

    # ------------------------------------------------------------- alerts
    def log_alert(self, alert_type: str, severity: str, message: str) -> None:
        """Store an alert event."""
        if not self._connected:
            return
        try:
            doc = {
                "user_id": self._user_id,
                "timestamp": datetime.utcnow(),
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
            }
            self._db.alerts.insert_one(doc)
        except Exception as exc:
            logger.warning("Failed to log alert to MongoDB: %s", exc)

    # ----------------------------------------------------------- settings
    def save_settings(self, settings: dict) -> None:
        """Upsert user settings."""
        if not self._connected:
            return
        try:
            self._db.user_settings.update_one(
                {"user_id": self._user_id},
                {"$set": {
                    "user_id": self._user_id,
                    "settings": settings,
                    "updated_at": datetime.utcnow(),
                }},
                upsert=True,
            )
            logger.debug("Settings saved to MongoDB for user %s", self._user_id)
        except Exception as exc:
            logger.warning("Failed to save settings to MongoDB: %s", exc)

    def get_settings(self) -> Optional[dict]:
        """Retrieve user settings from MongoDB."""
        if not self._connected:
            return None
        try:
            doc = self._db.user_settings.find_one({"user_id": self._user_id})
            return doc.get("settings", {}) if doc else None
        except Exception as exc:
            logger.warning("Failed to get settings from MongoDB: %s", exc)
            return None

    # -------------------------------------------------- analytics / history
    def get_history(self, days: int = 7) -> Optional[Dict[str, Any]]:
        """Aggregate analytics for the last N days (mirrors DataManager.get_history)."""
        if not self._connected:
            return None
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            # Sessions
            sessions = list(self._db.sessions.find(
                {"user_id": self._user_id, "start_time": {"$gte": cutoff}},
            ).sort("start_time", DESCENDING))

            n = len(sessions)
            avg_score = (
                sum(s.get("posture_score") or 0 for s in sessions) / n if n else 0
            )

            # Posture alerts
            p_events = list(self._db.posture_events.find({
                "user_id": self._user_id,
                "timestamp": {"$gte": cutoff},
                "event_type": {"$ne": "GOOD"},
            }))

            # Drowsiness alerts
            d_events = list(self._db.drowsiness_events.find({
                "user_id": self._user_id,
                "timestamp": {"$gte": cutoff},
                "drowsiness_level": {"$ne": "ALERT"},
            }))

            # Daily breakdowns
            daily_posture_alerts: Dict[str, int] = {}
            for e in p_events:
                k = str(e["timestamp"])[:10]
                daily_posture_alerts[k] = daily_posture_alerts.get(k, 0) + 1

            daily_drowsy_alerts: Dict[str, int] = {}
            for e in d_events:
                k = str(e["timestamp"])[:10]
                daily_drowsy_alerts[k] = daily_drowsy_alerts.get(k, 0) + 1

            # Daily scores
            daily_scores_raw: Dict[str, list] = {}
            for s in sessions:
                k = str(s["start_time"])[:10]
                daily_scores_raw.setdefault(k, []).append(s.get("posture_score") or 0)
            daily_scores = {
                k: round(sum(v) / len(v), 1) for k, v in daily_scores_raw.items()
            }

            # Posture distribution
            all_posture = list(self._db.posture_events.find({
                "user_id": self._user_id,
                "timestamp": {"$gte": cutoff},
            }))
            posture_distribution: Dict[str, int] = {}
            for e in all_posture:
                et = e.get("event_type") or "UNKNOWN"
                posture_distribution[et] = posture_distribution.get(et, 0) + 1

            # Daily avg neck angle
            daily_neck_raw: Dict[str, list] = {}
            for e in all_posture:
                if e.get("neck_angle") is not None:
                    k = str(e["timestamp"])[:10]
                    daily_neck_raw.setdefault(k, []).append(e["neck_angle"])
            daily_avg_neck_angle = {
                k: round(sum(v) / len(v), 1) for k, v in daily_neck_raw.items()
            }

            return {
                "sessions": n,
                "avg_posture_score": round(avg_score, 1),
                "good_pct": round(avg_score, 1),
                "posture_alerts": len(p_events),
                "drowsy_alerts": len(d_events),
                "daily_scores": daily_scores,
                "daily_posture_alerts": daily_posture_alerts,
                "daily_drowsy_alerts": daily_drowsy_alerts,
                "posture_distribution": posture_distribution,
                "daily_avg_neck_angle": daily_avg_neck_angle,
            }
        except Exception as exc:
            logger.warning("Failed to get history from MongoDB: %s", exc)
            return None

    def get_all_sessions(self) -> Optional[List[Dict[str, Any]]]:
        """Return all sessions for the current user."""
        if not self._connected:
            return None
        try:
            sessions = list(self._db.sessions.find(
                {"user_id": self._user_id},
            ).sort("start_time", DESCENDING))
            # Convert ObjectId to string for serialization
            for s in sessions:
                s["_id"] = str(s["_id"])
            return sessions
        except Exception as exc:
            logger.warning("Failed to get sessions from MongoDB: %s", exc)
            return None

    def get_user_analytics(self) -> Optional[Dict[str, Any]]:
        """
        Return comprehensive analytics for the current user.
        Designed for dashboards and reporting.
        """
        if not self._connected:
            return None
        try:
            now = datetime.utcnow()

            # Lifetime stats
            total_sessions = self._db.sessions.count_documents({"user_id": self._user_id})
            completed_sessions = self._db.sessions.count_documents({
                "user_id": self._user_id, "status": "completed",
            })
            total_posture_events = self._db.posture_events.count_documents({"user_id": self._user_id})
            total_drowsiness_events = self._db.drowsiness_events.count_documents({"user_id": self._user_id})
            total_alerts = self._db.alerts.count_documents({"user_id": self._user_id})

            # Average session duration
            pipeline = [
                {"$match": {"user_id": self._user_id, "status": "completed"}},
                {"$group": {"_id": None, "avg_duration": {"$avg": "$duration_minutes"},
                            "total_duration": {"$sum": "$duration_minutes"},
                            "avg_score": {"$avg": "$posture_score"}}},
            ]
            agg = list(self._db.sessions.aggregate(pipeline))
            session_stats = agg[0] if agg else {"avg_duration": 0, "total_duration": 0, "avg_score": 0}

            # Posture distribution (all-time)
            posture_pipeline = [
                {"$match": {"user_id": self._user_id}},
                {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
            ]
            posture_dist = {
                r["_id"]: r["count"]
                for r in self._db.posture_events.aggregate(posture_pipeline)
                if r["_id"]
            }

            # Hourly posture pattern (what hours are users most active / worst posture)
            hourly_pipeline = [
                {"$match": {"user_id": self._user_id}},
                {"$group": {
                    "_id": {"$hour": "$timestamp"},
                    "avg_neck_angle": {"$avg": "$neck_angle"},
                    "count": {"$sum": 1},
                }},
                {"$sort": {"_id": 1}},
            ]
            hourly_pattern = {
                r["_id"]: {"avg_neck_angle": round(r["avg_neck_angle"] or 0, 1), "count": r["count"]}
                for r in self._db.posture_events.aggregate(hourly_pipeline)
            }

            # Weekly trend (last 4 weeks)
            four_weeks_ago = now - timedelta(weeks=4)
            weekly_pipeline = [
                {"$match": {"user_id": self._user_id, "start_time": {"$gte": four_weeks_ago}, "status": "completed"}},
                {"$group": {
                    "_id": {"$isoWeek": "$start_time"},
                    "avg_score": {"$avg": "$posture_score"},
                    "sessions": {"$sum": 1},
                    "total_alerts": {"$sum": "$total_alerts"},
                }},
                {"$sort": {"_id": 1}},
            ]
            weekly_trend = [
                {"week": r["_id"], "avg_score": round(r["avg_score"] or 0, 1),
                 "sessions": r["sessions"], "total_alerts": r["total_alerts"]}
                for r in self._db.sessions.aggregate(weekly_pipeline)
            ]

            return {
                "user_id": self._user_id,
                "generated_at": now.isoformat(),
                "lifetime": {
                    "total_sessions": total_sessions,
                    "completed_sessions": completed_sessions,
                    "total_posture_events": total_posture_events,
                    "total_drowsiness_events": total_drowsiness_events,
                    "total_alerts": total_alerts,
                    "total_monitoring_minutes": session_stats.get("total_duration", 0),
                    "avg_session_duration_minutes": round(session_stats.get("avg_duration", 0), 1),
                    "avg_posture_score": round(session_stats.get("avg_score", 0), 1),
                },
                "posture_distribution": posture_dist,
                "hourly_pattern": hourly_pattern,
                "weekly_trend": weekly_trend,
            }
        except Exception as exc:
            logger.warning("Failed to get user analytics: %s", exc)
            return None

    # ------------------------------------------------ daily snapshot (rollup)
    def _update_daily_snapshot(self) -> None:
        """Create/update a daily analytics rollup document for fast dashboard queries."""
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            start = datetime.fromisoformat(f"{today}T00:00:00")
            end = start + timedelta(days=1)

            sessions_today = list(self._db.sessions.find({
                "user_id": self._user_id,
                "start_time": {"$gte": start, "$lt": end},
                "status": "completed",
            }))
            n = len(sessions_today)
            avg_score = sum(s.get("posture_score") or 0 for s in sessions_today) / n if n else 0
            total_duration = sum(s.get("duration_minutes") or 0 for s in sessions_today)
            total_alerts = sum(s.get("total_alerts") or 0 for s in sessions_today)

            posture_events = self._db.posture_events.count_documents({
                "user_id": self._user_id,
                "timestamp": {"$gte": start, "$lt": end},
            })
            drowsiness_events = self._db.drowsiness_events.count_documents({
                "user_id": self._user_id,
                "timestamp": {"$gte": start, "$lt": end},
            })

            self._db.analytics_snapshots.update_one(
                {"user_id": self._user_id, "date": today},
                {"$set": {
                    "user_id": self._user_id,
                    "date": today,
                    "sessions_count": n,
                    "avg_posture_score": round(avg_score, 1),
                    "total_monitoring_minutes": total_duration,
                    "total_alerts": total_alerts,
                    "posture_events_count": posture_events,
                    "drowsiness_events_count": drowsiness_events,
                    "updated_at": datetime.utcnow(),
                }},
                upsert=True,
            )
        except Exception as exc:
            logger.warning("Failed to update daily snapshot: %s", exc)

    # ------------------------------------------- admin: list all users
    def get_all_users_summary(self) -> Optional[List[Dict[str, Any]]]:
        """Return summary for all users (admin/analytics view)."""
        if not self._connected:
            return None
        try:
            users = list(self._db.users.find())
            summaries = []
            for u in users:
                uid = u["user_id"]
                session_count = self._db.sessions.count_documents({"user_id": uid})
                summaries.append({
                    "user_id": uid,
                    "machine_name": u.get("machine_name"),
                    "os": u.get("os"),
                    "last_active": u.get("last_active"),
                    "created_at": u.get("created_at"),
                    "total_sessions": session_count,
                })
            return summaries
        except Exception as exc:
            logger.warning("Failed to get users summary: %s", exc)
            return None
