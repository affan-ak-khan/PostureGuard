"""
camera_handler.py
Webcam capture running in a dedicated QThread.
"""

import logging
import time
from typing import Optional

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger("PostureGuard.camera")


class CameraHandler(QThread):
    """
    Continuously captures frames from a webcam and emits them via Qt signal.

    Signals:
        frame_ready (np.ndarray): BGR frame.
        error_occurred (str):     Error message.
        camera_opened ():         Fired once camera is ready.
        camera_closed ():         Fired after camera released.
    """

    frame_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    camera_opened = pyqtSignal()
    camera_closed = pyqtSignal()

    def __init__(
        self,
        config: dict = None,
        device_id: int = 0,
        frame_width: int = 640,
        frame_height: int = 480,
        fps: int = 30,
        skip_frames: int = 2,
        parent=None,
    ):
        super().__init__(parent)
        # Accept flat config dict as first arg (preferred)
        if isinstance(config, dict):
            cam = config.get("camera", {})
            proc = config.get("processing", {})
            self.device_id    = cam.get("device_id",    device_id)
            self.frame_width  = cam.get("frame_width",  frame_width)
            self.frame_height = cam.get("frame_height", frame_height)
            self.fps          = cam.get("fps",          fps)
            self.skip_frames  = max(proc.get("skip_frames", skip_frames), 1)
        else:
            # Legacy: config is actually device_id int
            self.device_id    = config if isinstance(config, int) else device_id
            self.frame_width  = frame_width
            self.frame_height = frame_height
            self.fps          = fps
            self.skip_frames  = max(skip_frames, 1)
        self._running = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_count = 0

    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    def get_available_cameras(self, max_test: int = 5) -> list:
        available = []
        for i in range(max_test):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available

    def run(self) -> None:
        logger.info("Opening camera device %d", self.device_id)
        # Try DSHOW first (Windows), then default
        self._cap = cv2.VideoCapture(self.device_id, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self.device_id)
        if not self._cap.isOpened():
            msg = f"Cannot open camera device {self.device_id}."
            logger.error(msg)
            self.error_occurred.emit(msg)
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        self._running = True
        self.camera_opened.emit()
        logger.info("Camera %d opened (%dx%d @ %d fps)", self.device_id, self.frame_width, self.frame_height, self.fps)

        frame_delay = 1.0 / max(self.fps, 1)

        while self._running:
            t0 = time.perf_counter()
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Frame read failed")
                self.error_occurred.emit("Camera read error — check connection.")
                time.sleep(0.5)
                continue

            self._frame_count += 1
            if self._frame_count % self.skip_frames == 0:
                self.frame_ready.emit(frame)

            elapsed = time.perf_counter() - t0
            sleep_t = frame_delay - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)

        if self._cap and self._cap.isOpened():
            self._cap.release()
        self.camera_closed.emit()
        logger.info("Camera %d released", self.device_id)
