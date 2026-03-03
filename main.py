"""
PostureGuard - AI-Powered Posture and Drowsiness Monitoring System
Main application entry point.
"""

import sys
import json
import logging
import logging.handlers
import socket
import threading
import http.server
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
# Local lib folder (D drive only — no C drive installs needed at runtime)
_LIB_DIR = ROOT_DIR / "lib"
if _LIB_DIR.exists():
    sys.path.insert(0, str(_LIB_DIR))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QTimer

from src.data_manager import DataManager
from src.ui.main_window import MainWindow
from src.ui.landing_window import LandingWindow


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("PostureGuard")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.handlers.TimedRotatingFileHandler(
        log_dir / "postureguard.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def load_config(config_path: Path) -> dict:
    defaults = {
        "app_name": "PostureGuard",
        "version": "1.0.0",
        "camera": {"device_id": 0, "frame_width": 640, "frame_height": 480, "fps": 30},
        "posture": {
            "good_neck_angle_min": 40,
            "good_neck_angle_max": 90,
            "slouch_threshold": 35,
            "forward_head_threshold": 30,
            "baseline_neck_angle": 60,
        },
        "eye_monitor": {
            "ear_threshold": 0.25,
            "tired_threshold": 0.28,
            "blink_threshold": 20,
            "consecutive_frames": 20,
            "tired_frames": 10,
        },
        "alerts": {
            "posture_check_interval": 5,
            "drowsiness_check_interval": 3,
            "snooze_duration": 60,
            "sound_enabled": True,
            "volume": 70,
        },
        "processing": {"skip_frames": 2, "detection_confidence": 0.5},
    }
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return {**defaults, **json.load(f)}
        except Exception:
            pass
    return defaults


def main() -> int:
    root = ROOT_DIR
    log_dir = root / "logs"
    data_dir = root / "data"
    config_path = root / "config.json"

    logger = setup_logging(log_dir)
    logger.info("Starting PostureGuard v1.0.0")

    data_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(config_path)
    logger.info("Configuration loaded")

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # stay alive while waiting for browser
    app.setApplicationName(config.get("app_name", "PostureGuard"))
    app.setApplicationVersion(config.get("version", "1.0.0"))
    app.setOrganizationName("PostureGuard")

    try:
        db_path = data_dir / "sessions.db"
        data_manager = DataManager(str(db_path))
        data_manager.initialize_database()
        logger.info("Database initialised at %s", db_path)
    except Exception as exc:
        logger.critical("Failed to initialise database: %s", exc, exc_info=True)
        QMessageBox.critical(None, "Database Error", f"Cannot initialise database:\n{exc}")
        return 1

    window_ref = []  # keep references alive

    def launch_qt_app():
        """Show the PyQt5 landing window, which leads to the main window."""
        try:
            landing = LandingWindow()
            landing.get_started.connect(launch_main)
            window_ref.append(landing)
            landing.show()
            # Raise after one event-loop tick so content renders before coming to front
            QTimer.singleShot(50, lambda: (landing.raise_(), landing.activateWindow()))
            logger.info("Qt landing window shown")
        except Exception as exc:
            logger.critical("Failed to show landing window: %s", exc, exc_info=True)
            QMessageBox.critical(None, "Startup Error", f"Failed to start:\n{exc}")
            app.quit()

    def launch_main():
        """Open the main monitoring window."""
        try:
            window = MainWindow(config=config, data_manager=data_manager)
            window_ref.append(window)
            window.show()
            logger.info("Main window launched")
        except Exception as exc:
            logger.critical("Failed to launch main window: %s", exc, exc_info=True)
            QMessageBox.critical(None, "Startup Error", f"Failed to start:\n{exc}")
            app.quit()

    # ── Local HTTP bridge ────────────────────────────────────────────────────
    # The HTML landing page calls /launch when the user clicks "Get Started".
    # A QTimer polls the event and opens the Qt app.
    launch_event = threading.Event()
    landing_html = root / "docs" / "landing.html"

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/launch":
                launch_event.set()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')
            elif self.path in ("/", "/index.html"):
                html_bytes = landing_html.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.end_headers()
                self.wfile.write(html_bytes)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *_):
            pass  # suppress console noise

    # ── Find a free port starting at 5000 ───────────────────────────────────
    def _find_port(start=5000, tries=10):
        for p in range(start, start + tries):
            try:
                with socket.socket() as s:
                    s.bind(("", p))
                return p
            except OSError:
                continue
        return start  # last resort — let OS raise if truly unavailable

    port = _find_port()
    bridge = ThreadingHTTPServer(("localhost", port), _Handler)
    threading.Thread(target=bridge.serve_forever, daemon=True).start()

    url = f"http://127.0.0.1:{port}/"

    # ── Print clear URL banner ───────────────────────────────────────────────
    banner = (
        "\n"
        "  ╔══════════════════════════════════════════════╗\n"
        f"  ║  PostureGuard  →  {url:<27}║\n"
        "  ║  Open the URL above in Edge / Chrome        ║\n"
        "  ║  Click  Get Started  to launch the app      ║\n"
        "  ╚══════════════════════════════════════════════╝\n"
    )
    print(banner, flush=True)
    logger.info("Landing page available at %s", url)

    # ── If no HTML page, skip straight to Qt ────────────────────────────────
    if not landing_html.exists():
        logger.warning("landing.html not found, launching Qt directly")
        launch_qt_app()

    # ── Poll for launch signal from browser ─────────────────────────────────
    def _check_launch():
        if launch_event.is_set():
            _poll_timer.stop()
            launch_qt_app()

    _poll_timer = QTimer()
    _poll_timer.timeout.connect(_check_launch)
    _poll_timer.start(150)  # check every 150 ms

    exit_code = app.exec_()
    logger.info("PostureGuard exiting with code %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
