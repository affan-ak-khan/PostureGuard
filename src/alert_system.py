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
        self._speak(speech)
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
            self._speak(speech)
            self._snooze_voice("drowsiness")
        self._record("drowsiness", level, body)

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

    def _speak(self, text: str) -> None:
        """Speak text using Windows built-in SAPI via PowerShell (no extra packages)."""
        if not self.sound_enabled:
            logger.info("TTS (muted): %s", text)
            return

        vol_percent = self.volume   # 0-100
        safe = text.replace("'", "").replace('"', '')

        ps_script = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Volume = {vol_percent}; "
            f"$s.Rate = 1; "
            f"$s.Speak('{safe}')"
        )

        def _run():
            with self._tts_lock:
                try:
                    subprocess.run(
                        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                        capture_output=True, timeout=15,
                    )
                except Exception as e:
                    logger.warning("TTS error: %s", e)

        threading.Thread(target=_run, daemon=True).start()

    def _record(self, t: str, level: str, msg: str) -> None:
        self._history.append({"type": t, "level": level, "message": msg, "timestamp": time.time()})
        if len(self._history) > 500:
            self._history = self._history[-500:]

