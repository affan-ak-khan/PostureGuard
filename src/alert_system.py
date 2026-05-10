"""
alert_system.py
Desktop notifications + voice alerts (Windows SAPI via PowerShell) for PostureGuard.
No extra packages required — uses the built-in Windows Speech API.
"""

import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("PostureGuard.alerts")

try:
    import winsound
    _WINSOUND = True
except ImportError:
    _WINSOUND = False

try:
    from plyer import notification as _notify
    _PLYER = True
except ImportError:
    _PLYER = False
    logger.warning("plyer not available — desktop notifications disabled")

GENTLE   = "GENTLE"
MODERATE = "MODERATE"
SEVERE   = "SEVERE"


class AlertSystem:
    """Manages desktop notifications and voice alerts."""

    def __init__(self, config=None, sound_enabled=True, volume=70, snooze_duration=60, app_name="PostureGuard"):
        if isinstance(config, dict):
            alerts = config.get("alerts", {})
            sound_enabled   = alerts.get("sound_enabled", sound_enabled)
            volume          = alerts.get("volume", volume)
            snooze_duration = alerts.get("snooze_duration", snooze_duration)
            app_name        = config.get("app_name", app_name)
        self.sound_enabled      = bool(sound_enabled)
        self.volume             = max(0, min(100, int(volume)))
        self.snooze_duration    = snooze_duration   # desktop notification cooldown
        self.voice_cooldown     = 15                # voice speaks every 15 s
        self.app_name           = app_name
        self._snooze_until: dict      = {}   # desktop notification snooze
        self._voice_until: dict       = {}   # voice-only cooldown
        self._history: list           = []
        self._tts_lock                = threading.Lock()
        self._mongodb = None  # Optional MongoDBManager for cloud logging
        self._sounds_dir = Path(__file__).resolve().parent.parent / "assets" / "sounds"

    def set_mongodb(self, mongodb_manager) -> None:
        """Attach a MongoDBManager to log alerts to the cloud."""
        self._mongodb = mongodb_manager

    # ---------------------------------------------------------------- public --
    def trigger_posture_alert(self, severity=GENTLE, neck_angle=0.0) -> None:
        if self._is_snoozed("posture"):
            return
        msgs = {
            GENTLE:   (
                "Posture Reminder",
                "Please check your posture. Sit up straight.",
                "Please check your posture. Sit up straight.",
            ),
            MODERATE: (
                "Posture Warning",
                f"Poor posture! Neck angle: {neck_angle:.0f}°",
                f"Warning! Your neck angle is not good. It is at {neck_angle:.0f} degrees. Please correct your posture.",
            ),
            SEVERE: (
                "Bad Posture!",
                "Severe neck strain — sit up straight NOW!",
                "Alert! Severe neck strain detected. Please sit up straight immediately.",
            ),
        }
        title, body, speech = msgs.get(severity, msgs[GENTLE])
        self._notify(title, body)
        self._play_and_speak("posture_alert.wav", speech)
        self._record("posture", severity, body)
        self.snooze_alert("posture")

    def trigger_drowsiness_alert(self, level="TIRED") -> None:
        notify_blocked = self._is_snoozed("drowsiness")
        voice_blocked  = self._is_voice_snoozed("drowsiness")
        if notify_blocked and voice_blocked:
            return
        msgs = {
            "TIRED":  (
                "Feeling Tired?",
                "You seem tired \u2014 take a short break.",
                "You are feeling tired. Please take a short break and rest your eyes.",
            ),
            "DROWSY": (
                "WAKE UP!",
                "Drowsiness detected! Take a break immediately.",
                "Wake up! You are drowsy. Please stop and take a break immediately.",
            ),
        }
        title, body, speech = msgs.get(level, msgs["TIRED"])
        if not notify_blocked:
            self._notify(title, body)
            self.snooze_alert("drowsiness")
        if not voice_blocked:
            self._play_and_speak("drowsiness_alert.wav", speech)
            self._snooze_voice("drowsiness")
        self._record("drowsiness", level, body)

    def trigger_shoulder_alert(self, severity=GENTLE, tilt=0.0) -> None:
        notify_blocked = self._is_snoozed("shoulder")
        voice_blocked  = self._is_voice_snoozed("shoulder")
        if notify_blocked and voice_blocked:
            return
        msgs = {
            GENTLE: (
                "Shoulder Alignment",
                f"Shoulder tilt detected ({tilt:.0f}°). Please level your shoulders.",
                "Your shoulder posture is not correct.",
            ),
            SEVERE: (
                "Shoulder Misalignment",
                f"Severe shoulder tilt ({tilt:.0f}°). Please correct your posture.",
                "Your shoulder posture is not correct.",
            ),
        }
        title, body, speech = msgs.get(severity, msgs[GENTLE])
        if not notify_blocked:
            self._notify(title, body)
            self.snooze_alert("shoulder")
        if not voice_blocked:
            self._play_and_speak("posture_alert.wav", speech)
            self._snooze_voice("shoulder")
        self._record("shoulder", severity, body)

    def snooze_alert(self, alert_type: str, duration: Optional[int] = None) -> None:
        dur = duration if duration is not None else self.snooze_duration
        self._snooze_until[alert_type] = time.time() + dur

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, int(volume)))

    def get_alert_history(self) -> list:
        return list(self._history)

    # --------------------------------------------------------------- private --
    def _is_snoozed(self, t: str) -> bool:
        return time.time() < self._snooze_until.get(t, 0)

    def _is_voice_snoozed(self, t: str) -> bool:
        return time.time() < self._voice_until.get(t, 0)

    def _snooze_voice(self, t: str) -> None:
        self._voice_until[t] = time.time() + self.voice_cooldown

    def _notify(self, title: str, message: str) -> None:
        if _PLYER:
            try:
                _notify.notify(title=title, message=message, app_name=self.app_name, timeout=5)
            except Exception as e:
                logger.warning("Notification failed: %s", e)
        else:
            logger.info("ALERT — %s: %s", title, message)

    def _play_sound(self, filename: str) -> None:
        if not self.sound_enabled:
            return
        sound_path = self._sounds_dir / filename
        if not sound_path.exists():
            logger.warning("Alert sound missing: %s", sound_path)
            return

        def _run():
            try:
                if _WINSOUND:
                    winsound.PlaySound(str(sound_path), winsound.SND_FILENAME)
                else:
                    logger.info("Alert sound requested but winsound is unavailable: %s", sound_path)
            except Exception as e:
                logger.warning("Sound playback failed: %s", e)

        threading.Thread(target=_run, daemon=True).start()

    def _play_and_speak(self, sound_file: str, text: str) -> None:
        if not self.sound_enabled:
            logger.info("TTS (muted): %s", text)
            return

        def _run():
            with self._tts_lock:
                try:
                    sound_path = self._sounds_dir / sound_file
                    if sound_path.exists() and _WINSOUND:
                        winsound.PlaySound(str(sound_path), winsound.SND_FILENAME)
                    elif not sound_path.exists():
                        logger.warning("Alert sound missing: %s", sound_path)
                    self._speak_sync(text)
                except Exception as e:
                    logger.warning("Alert playback failed: %s", e)

        threading.Thread(target=_run, daemon=True).start()

    def _speak(self, text: str) -> None:
        self._speak_sync(text)

    def _speak_sync(self, text: str) -> None:
        """Speak text using Windows built-in SAPI via PowerShell (no extra packages)."""
        vol_percent = self.volume   # 0-100
        safe = text.replace("'", "").replace('"', '')

        ps_script = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Volume = {vol_percent}; "
            f"$s.Rate = 1; "
            f"$s.Speak('{safe}')"
        )

        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                capture_output=True, timeout=15,
            )
        except Exception as e:
            logger.warning("TTS error: %s", e)

    def _record(self, t: str, level: str, msg: str) -> None:
        self._history.append({"type": t, "level": level, "message": msg, "timestamp": time.time()})
        if len(self._history) > 500:
            self._history = self._history[-500:]
        # Sync alert to MongoDB (fire-and-forget)
        if self._mongodb and self._mongodb.is_connected:
            threading.Thread(
                target=self._mongo_log_alert, args=(t, level, msg), daemon=True,
            ).start()

    def _mongo_log_alert(self, alert_type: str, severity: str, message: str) -> None:
        try:
            self._mongodb.log_alert(alert_type, severity, message)
        except Exception as e:
            logger.warning("MongoDB alert log failed: %s", e)

