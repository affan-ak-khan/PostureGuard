"""
landing_window.py — PostureGuard welcome / landing screen.
Shown once at startup; emits get_started signal when user clicks the final step.
"""

from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QGraphicsOpacityEffect,
)


class LandingWindow(QMainWindow):
    """Frameless animated four-step landing screen."""

    get_started = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PostureGuard")
        self.setMinimumSize(780, 560)
        self.resize(980, 640)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self._drag_pos = None
        self._page_index = 0
        self._page_titles = []
        self._build_ui()
        self._center_on_screen()
        self._fade_in()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setObjectName("landingRoot")
        central.setStyleSheet("""
            QWidget#landingRoot {
                background: qlineargradient(
                    x1:0 y1:0 x2:1 y2:1,
                    stop:0 #060d18,
                    stop:0.45 #0d0921,
                    stop:1 #060d18
                );
            }
        """)
        central.mousePressEvent = self._mouse_press
        central.mouseMoveEvent = self._mouse_move
        central.mouseReleaseEvent = self._mouse_release

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(16, 12, 16, 0)
        top_bar.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(34, 34)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.03);
                color: rgba(255,255,255,0.55);
                border: 1px solid rgba(255,255,255,0.12);
                font-size: 16px;
                border-radius: 17px;
            }
            QPushButton:hover {
                background: rgba(248,81,73,0.22);
                color: #f85149;
                border-color: #f85149;
            }
        """)
        close_btn.clicked.connect(self.close)
        top_bar.addWidget(close_btn)
        outer.addLayout(top_bar)

        outer.addStretch(1)

        shell = QFrame()
        shell.setMaximumWidth(860)
        shell.setMinimumWidth(620)
        shell.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 28px;
            }
        """)
        shell_lay = QVBoxLayout(shell)
        shell_lay.setContentsMargins(28, 24, 28, 22)
        shell_lay.setSpacing(16)

        header = QVBoxLayout()
        header.setSpacing(6)
        badge = QLabel("FOUR STEP INTRO")
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("""
            color: #8cbcff;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 2px;
            background: rgba(88,166,255,0.10);
            border: 1px solid rgba(88,166,255,0.22);
            border-radius: 16px;
            padding: 4px 14px;
        """)
        title = QLabel("PostureGuard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: white;
            font-size: 38px;
            font-weight: 900;
            letter-spacing: -1px;
            background: transparent;
            border: none;
        """)
        subtitle = QLabel("Move through a quick guided tour before the main monitor opens.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("""
            color: rgba(200,215,255,0.70);
            font-size: 13px;
            background: transparent;
            border: none;
        """)
        header.addWidget(badge)
        header.addWidget(title)
        header.addWidget(subtitle)
        shell_lay.addLayout(header)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")
        self._stack.setContentsMargins(0, 0, 0, 0)

        pages = [
            self._make_page(
                "1 / 4",
                "Welcome to your focus companion",
                "PostureGuard watches your posture and alertness while you work, without getting in the way.",
                ["Real-time detection", "Session tracking", "Smart alerts"],
                "Continue",
            ),
            self._make_page(
                "2 / 4",
                "Splash into posture insights",
                "The app reads neck angle, shoulder tilt, and posture quality so you can catch problems early.",
                ["Neck angle monitoring", "Shoulder tilt checks", "Daily quality charts"],
                "Next",
            ),
            self._make_page(
                "3 / 4",
                "Stay ahead of drowsiness",
                "Eye monitoring detects tiredness and drowsy patterns, then alerts you with clear feedback.",
                ["EAR tracking", "Drowsy alert history", "Sound notifications"],
                "Next",
            ),
            self._make_page(
                "4 / 4",
                "Ready to start?",
                "Click Get Started to open the main workspace and begin monitoring in the full dashboard.",
                ["Analytics", "Live camera feed", "Theme support"],
                "Get Started",
                final=True,
            ),
        ]
        for page in pages:
            self._stack.addWidget(page)
            self._page_titles.append(page.property("pageTitle"))

        shell_lay.addWidget(self._stack)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self._dots = []
        for i in range(4):
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet("background: rgba(255,255,255,0.20); border-radius: 5px;")
            self._dots.append(dot)
            footer.addWidget(dot)
        footer.addStretch()
        hint = QLabel("Click through the cards to animate into the main app")
        hint.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px; background: transparent; border: none;")
        footer.addWidget(hint)
        shell_lay.addLayout(footer)

        wrap = QHBoxLayout()
        wrap.addStretch(1)
        wrap.addWidget(shell)
        wrap.addStretch(1)
        outer.addLayout(wrap)

        outer.addStretch(1)

        ver_lbl = QLabel("v1.0.0  •  Powered by MediaPipe & OpenCV  •  PostureGuard")
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setStyleSheet("color: rgba(255,255,255,0.18); font-size: 11px; background: transparent; border: none;")
        outer.addWidget(ver_lbl)
        outer.addSpacing(8)

        self._refresh_dots()

    def _make_page(self, step_text, title, description, bullets, button_text, final=False):
        page = QWidget()
        page.setProperty("pageTitle", title)
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(14)

        step = QLabel(step_text)
        step.setAlignment(Qt.AlignLeft)
        step.setStyleSheet("color: #8cbcff; font-size: 11px; font-weight: 800; letter-spacing: 1.8px; background: transparent; border: none;")
        lay.addWidget(step)

        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("color: white; font-size: 28px; font-weight: 800; letter-spacing: -0.6px; background: transparent; border: none;")
        lay.addWidget(title_lbl)

        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: rgba(200,215,255,0.68); font-size: 14px; line-height: 1.5; background: transparent; border: none;")
        lay.addWidget(desc)

        card_row = QHBoxLayout()
        card_row.setSpacing(10)
        for item in bullets:
            mini = QFrame()
            mini.setStyleSheet("""
                QFrame {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.09);
                    border-radius: 14px;
                }
            """)
            mini_lay = QVBoxLayout(mini)
            mini_lay.setContentsMargins(12, 10, 12, 10)
            mini_lay.setSpacing(4)
            mark = QLabel("•")
            mark.setAlignment(Qt.AlignLeft)
            mark.setStyleSheet("color: #5fb0ff; font-size: 20px; font-weight: 900; background: transparent; border: none;")
            text = QLabel(item)
            text.setWordWrap(True)
            text.setStyleSheet("color: rgba(230,237,243,0.88); font-size: 12px; background: transparent; border: none;")
            mini_lay.addWidget(mark)
            mini_lay.addWidget(text)
            card_row.addWidget(mini)
        lay.addLayout(card_row)

        lay.addStretch(1)

        action = QPushButton(f"▶   {button_text}")
        action.setFixedHeight(48)
        action.setMinimumWidth(220)
        action.setCursor(Qt.PointingHandCursor)
        action.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0 y1:0 x2:1 y2:0, stop:0 #4facfe, stop:1 #7c6eff);
                color: white;
                font-size: 14px;
                font-weight: 800;
                border: none;
                border-radius: 24px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0 y1:0 x2:1 y2:0, stop:0 #74c4ff, stop:1 #9f91ff);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0 y1:0 x2:1 y2:0, stop:0 #3b9cfe, stop:1 #6252ef);
            }
        """)
        action.clicked.connect(self._advance if not final else self._launch)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(action)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        page.setProperty("actionButton", action)
        return page

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        fg = self.frameGeometry()
        fg.moveCenter(screen.center())
        self.move(fg.topLeft())

    def _fade_in(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self._intro_anim = QPropertyAnimation(effect, b"opacity", self)
        self._intro_anim.setDuration(700)
        self._intro_anim.setStartValue(0.0)
        self._intro_anim.setEndValue(1.0)
        self._intro_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._intro_anim.start()

    def _refresh_dots(self):
        for index, dot in enumerate(self._dots):
            if index == self._page_index:
                dot.setStyleSheet("background: #5fb0ff; border-radius: 5px;")
            else:
                dot.setStyleSheet("background: rgba(255,255,255,0.20); border-radius: 5px;")

    def _transition_to(self, next_index: int):
        next_index = max(0, min(self._stack.count() - 1, next_index))
        if next_index == self._page_index:
            return

        current = self._stack.currentWidget()
        current_effect = QGraphicsOpacityEffect(current)
        current.setGraphicsEffect(current_effect)

        next_widget = self._stack.widget(next_index)
        next_effect = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(next_effect)
        next_effect.setOpacity(0.0)

        self._stack.setCurrentIndex(next_index)
        self._page_index = next_index
        self._refresh_dots()

        fade_out = QPropertyAnimation(current_effect, b"opacity", self)
        fade_out.setDuration(180)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.OutCubic)

        fade_in = QPropertyAnimation(next_effect, b"opacity", self)
        fade_in.setDuration(260)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade_out)
        group.addAnimation(fade_in)

        def _cleanup():
            current.setGraphicsEffect(None)
            next_widget.setGraphicsEffect(None)

        group.finished.connect(_cleanup)
        group.start(QPropertyAnimation.DeleteWhenStopped)

    def _advance(self):
        self._transition_to(self._page_index + 1)

    def _launch(self):
        self.get_started.emit()
        self.close()

    def _mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def _mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def _mouse_release(self, _event):
        self._drag_pos = None
