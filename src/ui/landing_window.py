"""
landing_window.py — PostureGuard welcome / landing screen.
Shown once at startup; emits get_started signal when user clicks the button.
"""

from PyQt5.QtCore    import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGraphicsOpacityEffect,
)


class LandingWindow(QMainWindow):
    """Frameless gradient landing screen."""
    get_started = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PostureGuard")
        self.setMinimumSize(680, 480)
        self.resize(860, 560)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self._drag_pos = None
        self._build_ui()
        self._fade_in()

    # ──────────────────────────────────────────────────────── UI ───────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setObjectName("landingRoot")
        central.setStyleSheet("""
            QWidget#landingRoot {
                background: qlineargradient(
                    x1:0 y1:0 x2:1 y2:1,
                    stop:0   #060d18,
                    stop:0.4 #0d0921,
                    stop:1   #060d18
                );
            }
        """)

        central.mousePressEvent   = self._mouse_press
        central.mouseMoveEvent    = self._mouse_move
        central.mouseReleaseEvent = self._mouse_release

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top bar (close btn) ─────────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(16, 10, 16, 0)
        top_bar.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(34, 34)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.35);
                border: 1px solid rgba(255,255,255,0.12);
                font-size: 16px;
                border-radius: 17px;
            }
            QPushButton:hover {
                background: rgba(248,81,73,0.25);
                color: #f85149;
                border-color: #f85149;
            }
        """)
        close_btn.clicked.connect(self.close)
        top_bar.addWidget(close_btn)
        outer.addLayout(top_bar)

        outer.addStretch(1)

        # ── Center card ─────────────────────────────────────────────────
        card_wrap = QHBoxLayout()
        card_wrap.addStretch(1)

        card = QFrame()
        card.setMaximumWidth(660)
        card.setMinimumWidth(480)
        card.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 28px;
            }
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 30, 40, 30)
        cl.setSpacing(0)

        # Badge
        badge = QLabel("✦  AI Health Monitoring")
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("""
            color: #7ab3ff;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            background: rgba(88,166,255,0.10);
            border: 1px solid rgba(88,166,255,0.25);
            border-radius: 16px;
            padding: 4px 14px;
        """)
        badge_row = QHBoxLayout()
        badge_row.addStretch()
        badge_row.addWidget(badge)
        badge_row.addStretch()
        cl.addLayout(badge_row)
        cl.addSpacing(10)

        # App name
        name_lbl = QLabel("PostureGuard")
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("""
            color: white;
            font-size: 36px;
            font-weight: 800;
            letter-spacing: -1px;
            background: transparent;
            border: none;
        """)
        cl.addWidget(name_lbl)
        cl.addSpacing(6)

        tagline = QLabel("Your AI Companion for Better Posture & Focused Work")
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setWordWrap(True)
        tagline.setStyleSheet("""
            color: rgba(200,215,255,0.70);
            font-size: 13px;
            font-weight: 400;
            background: transparent;
            border: none;
        """)
        cl.addWidget(tagline)
        cl.addSpacing(14)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.08); border: none; max-height:1px;")
        cl.addWidget(sep)
        cl.addSpacing(12)

        # Description
        desc = QLabel(
            "Real-time AI monitors your posture and alertness while you work — "
            "alerting you the moment you slouch, crane your neck, or start to doze."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("""
            color: rgba(190,210,255,0.50);
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        cl.addWidget(desc)
        cl.addSpacing(18)

        # Feature pills
        feat_row = QHBoxLayout()
        feat_row.setSpacing(8)
        for icon, label in (
            ("🧍", "Posture AI"),
            ("👁️", "Drowsiness"),
            ("📊", "Analytics"),
            ("🔔", "Alerts"),
        ):
            pill = QFrame()
            pill.setStyleSheet("""
                QFrame {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.09);
                    border-radius: 12px;
                }
            """)
            pl = QVBoxLayout(pill)
            pl.setContentsMargins(10, 8, 10, 8)
            pl.setSpacing(2)
            il = QLabel(icon)
            il.setAlignment(Qt.AlignCenter)
            il.setStyleSheet("font-size:18px; background:transparent; border:none;")
            tl = QLabel(label)
            tl.setAlignment(Qt.AlignCenter)
            tl.setStyleSheet(
                "color:rgba(180,210,255,0.65); font-size:10px;"
                " background:transparent; border:none;"
            )
            pl.addWidget(il)
            pl.addWidget(tl)
            feat_row.addWidget(pill)
        cl.addLayout(feat_row)
        cl.addSpacing(22)

        # Get Started button
        gs_btn = QPushButton("▶   Get Started")
        gs_btn.setFixedHeight(46)
        gs_btn.setMinimumWidth(200)
        gs_btn.setCursor(Qt.PointingHandCursor)
        gs_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0 y1:0 x2:1 y2:0,
                    stop:0 #4facfe, stop:1 #7c6eff
                );
                color: white;
                font-size: 14px;
                font-weight: 700;
                border: none;
                border-radius: 23px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0 y1:0 x2:1 y2:0,
                    stop:0 #74c4ff, stop:1 #9f91ff
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1:0 y1:0 x2:1 y2:0,
                    stop:0 #3b9cfe, stop:1 #6252ef
                );
            }
        """)
        gs_btn.clicked.connect(self._launch)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(gs_btn)
        btn_row.addStretch()
        cl.addLayout(btn_row)

        card_wrap.addWidget(card)
        card_wrap.addStretch(1)
        outer.addLayout(card_wrap)

        outer.addStretch(1)

        # Footer
        ver_lbl = QLabel("v1.0.0  •  Powered by MediaPipe & OpenCV  •  PostureGuard")
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setStyleSheet(
            "color:rgba(255,255,255,0.18); font-size:11px; background:transparent;"
        )
        outer.addWidget(ver_lbl)
        outer.addSpacing(8)

    # ──────────────────────────────────────────────────── logic ────────────

    def _fade_in(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self._anim = QPropertyAnimation(effect, b"opacity", self)
        self._anim.setDuration(600)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def _launch(self):
        self.setGraphicsEffect(None)
        self.get_started.emit()
        self.close()

    # ──────────────────────────── frameless drag support ───────────────────

    def _mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def _mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def _mouse_release(self, _event):
        self._drag_pos = None
