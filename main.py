"""
PostureGuard - AI-Powered Posture and Drowsiness Monitoring System
Main application entry point.
"""

import sys
import json
import logging
import logging.handlers
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
# Local lib folder (D drive only — no C drive installs needed at runtime)
_LIB_DIR = ROOT_DIR / "lib"
if _LIB_DIR.exists():
    sys.path.insert(0, str(_LIB_DIR))

from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QColor

from src.data_manager import DataManager
from src.ui.main_window import MainWindow


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


def create_splash(app: QApplication) -> QSplashScreen:
    pixmap = QPixmap(480, 280)
    pixmap.fill(QColor("#1e1e2e"))
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.showMessage(
        "Loading PostureGuard...",
        Qt.AlignHCenter | Qt.AlignBottom,
        QColor("#cdd6f4"),
    )
    splash.show()
    app.processEvents()
    return splash


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
    app.setApplicationName(config.get("app_name", "PostureGuard"))
    app.setApplicationVersion(config.get("version", "1.0.0"))
    app.setOrganizationName("PostureGuard")

    splash = create_splash(app)

    try:
        db_path = data_dir / "sessions.db"
        data_manager = DataManager(str(db_path))
        data_manager.initialize_database()
        logger.info("Database initialised at %s", db_path)
    except Exception as exc:
        logger.critical("Failed to initialise database: %s", exc, exc_info=True)
        QMessageBox.critical(None, "Database Error", f"Cannot initialise database:\n{exc}")
        return 1

    window_ref = []

    def launch_main():
        splash.close()
        try:
            window = MainWindow(config=config, data_manager=data_manager)
            window_ref.append(window)  # keep reference alive
            window.show()
            logger.info("Main window launched")
        except Exception as exc:
            logger.critical("Failed to launch main window: %s", exc, exc_info=True)
            QMessageBox.critical(None, "Startup Error", f"Failed to start:\n{exc}")
            app.quit()

    QTimer.singleShot(1500, launch_main)
    exit_code = app.exec_()
    logger.info("PostureGuard exiting with code %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
