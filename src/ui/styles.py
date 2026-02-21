"""
styles.py — Qt stylesheets and colour constants for PostureGuard.
"""

STATUS_COLOURS = {
    "GOOD":         "#a6e3a1",
    "SLOUCHING":    "#f9e2af",
    "FORWARD_HEAD": "#fab387",
    "NECK_STRAIN":  "#f38ba8",
    "UNKNOWN":      "#6c7086",
    "NOT STARTED":  "#6c7086",
    "STOPPED":      "#6c7086",
    "ALERT":        "#a6e3a1",
    "TIRED":        "#f9e2af",
    "DROWSY":       "#f38ba8",
}

DARK_THEME = """
/* ── Base ── */
QMainWindow, QDialog, QWidget {
    background-color: #11111b;
    color: #cdd6f4;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
/* ── Menu ── */
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #2a2a3d;
    padding: 2px 4px;
}
QMenuBar::item { padding: 4px 10px; border-radius: 5px; }
QMenuBar::item:selected { background-color: #313244; }
QMenu {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 6px 4px;
}
QMenu::item { padding: 6px 24px; border-radius: 5px; }
QMenu::item:selected { background-color: #313244; }
QMenu::separator { height: 1px; background: #313244; margin: 4px 8px; }
/* ── Buttons ── */
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #89b4fa, stop:1 #74c7ec);
    color: #11111b;
    border: none;
    border-radius: 9px;
    padding: 9px 22px;
    font-size: 13px;
    font-weight: 700;
}
QPushButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #b4befe, stop:1 #89b4fa);
}
QPushButton:pressed { background: #585b70; }
QPushButton:disabled { background: #2a2a3d; color: #45475a; border: 1px solid #313244; }
QPushButton#stopButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #f38ba8, stop:1 #e06c8b);
}
QPushButton#stopButton:hover { background: #eba0ac; }
QPushButton#startButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #a6e3a1, stop:1 #5ec566);
    color: #11111b;
}
QPushButton#startButton:hover { background: #b4f0b0; }
QPushButton#iconButton {
    background: #1e1e2e;
    color: #89b4fa;
    border: 1px solid #313244;
    border-radius: 9px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton#iconButton:hover { background: #313244; border-color: #89b4fa; }
/* ── Labels ── */
QLabel { color: #cdd6f4; background: transparent; }
/* ── GroupBox ── */
QGroupBox {
    background-color: #1e1e2e;
    border: 1px solid #2a2a3d;
    border-radius: 12px;
    margin-top: 16px;
    padding: 10px 8px 8px 8px;
    color: #bac2de;
    font-weight: 700;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: #89b4fa;
    font-size: 12px;
    font-weight: 700;
}
/* ── Progress bar ── */
QProgressBar {
    background-color: #2a2a3d;
    border-radius: 6px;
    text-align: center;
    color: #cdd6f4;
    font-weight: 800;
    font-size: 12px;
    min-height: 14px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #a6e3a1, stop:1 #89b4fa);
    border-radius: 6px;
}
/* ── Inputs ── */
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 7px;
    padding: 6px 10px;
    color: #cdd6f4;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDoubleSpinBox:focus {
    border-color: #89b4fa;
    background-color: #24243a;
}
QComboBox::drop-down { border: none; padding-right: 8px; }
/* ── Tabs ── */
QTabWidget::pane {
    border: 1px solid #2a2a3d;
    border-radius: 10px;
    background: #1e1e2e;
}
QTabBar::tab {
    background: #181825;
    color: #6c7086;
    padding: 9px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 3px;
    font-weight: 600;
}
QTabBar::tab:selected { background: #1e1e2e; color: #89b4fa; border-bottom: 2px solid #89b4fa; }
QTabBar::tab:hover { color: #cdd6f4; }
/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #181825; width: 8px; border-radius: 4px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #313244; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #45475a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
/* ── Status bar ── */
QStatusBar {
    background: #181825;
    color: #585b70;
    border-top: 1px solid #2a2a3d;
    font-size: 12px;
    padding: 2px 8px;
}
/* ── List widget ── */
QListWidget {
    background: #181825;
    border: 1px solid #2a2a3d;
    border-radius: 8px;
    color: #cdd6f4;
    padding: 4px;
    outline: none;
}
QListWidget::item { padding: 5px 8px; border-radius: 5px; }
QListWidget::item:selected { background: #313244; color: #cdd6f4; }
QListWidget::item:hover { background: #24243a; }
/* ── Table ── */
QTableWidget {
    background: #1e1e2e;
    gridline-color: #2a2a3d;
    color: #cdd6f4;
    border: 1px solid #2a2a3d;
    border-radius: 8px;
}
QTableWidget::item:selected { background: #313244; }
QHeaderView::section {
    background: #181825;
    color: #89b4fa;
    padding: 7px;
    border: 1px solid #2a2a3d;
    font-weight: 700;
    font-size: 12px;
}
/* ── Checkbox ── */
QCheckBox { color: #cdd6f4; spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 2px solid #45475a;
    border-radius: 5px;
    background: #1e1e2e;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #89b4fa, stop:1 #74c7ec);
    border-color: #89b4fa;
}
/* ── Slider ── */
QSlider::groove:horizontal {
    background: #2a2a3d; height: 6px; border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #89b4fa;
    width: 18px; height: 18px;
    border-radius: 9px;
    margin: -6px 0;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #89b4fa, stop:1 #74c7ec);
    border-radius: 3px;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #eff1f5; color: #4c4f69;
    font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;
}
QMenuBar { background-color: #e6e9ef; color: #4c4f69; border-bottom: 1px solid #ccd0da; padding: 2px; }
QMenuBar::item { padding: 4px 10px; border-radius: 5px; }
QMenuBar::item:selected { background-color: #ccd0da; }
QMenu { background-color: #e6e9ef; border: 1px solid #ccd0da; border-radius: 8px; padding: 6px; }
QMenu::item { padding: 6px 24px; border-radius: 5px; }
QMenu::item:selected { background-color: #ccd0da; }
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1e66f5, stop:1 #1558d6);
    color: #eff1f5; border: none; border-radius: 9px; padding: 9px 22px;
    font-size: 13px; font-weight: 700;
}
QPushButton:hover { background: #209fb5; }
QPushButton:pressed { background: #04a5e5; }
QPushButton:disabled { background: #bcc0cc; color: #8c8fa1; }
QPushButton#stopButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #d20f39, stop:1 #b00726); }
QPushButton#startButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #40a02b, stop:1 #2f7a1e); color: #eff1f5; }
QPushButton#iconButton { background: #e6e9ef; color: #1e66f5; border: 1px solid #ccd0da; border-radius: 9px; padding: 8px 16px; }
QPushButton#iconButton:hover { background: #ccd0da; }
QGroupBox {
    background: #e6e9ef; border: 1px solid #ccd0da; border-radius: 12px;
    margin-top: 16px; padding: 10px 8px 8px 8px;
    color: #5c5f77; font-weight: 700; font-size: 12px;
}
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 14px; padding: 0 6px; color: #1e66f5; }
QProgressBar { background: #ccd0da; border-radius: 6px; text-align: center; color: #4c4f69; font-weight: 800; min-height: 14px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #40a02b, stop:1 #1e66f5); border-radius: 6px; }
QStatusBar { background: #e6e9ef; color: #7c7f93; border-top: 1px solid #ccd0da; font-size: 12px; }
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
    background: #eff1f5; border: 1px solid #ccd0da; border-radius: 7px; padding: 6px 10px; color: #4c4f69;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #1e66f5; }
QTabWidget::pane { border: 1px solid #ccd0da; border-radius: 10px; }
QTabBar::tab { background: #e6e9ef; color: #5c5f77; padding: 9px 20px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; font-weight: 600; }
QTabBar::tab:selected { background: #eff1f5; color: #1e66f5; border-bottom: 2px solid #1e66f5; }
QCheckBox { color: #4c4f69; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #ccd0da; border-radius: 5px; background: #e6e9ef; }
QCheckBox::indicator:checked { background: #1e66f5; border-color: #1e66f5; }
QSlider::groove:horizontal { background: #ccd0da; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #1e66f5; width: 18px; height: 18px; border-radius: 9px; margin: -6px 0; }
QScrollBar:vertical { background: #e6e9ef; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #ccd0da; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QListWidget { background: #e6e9ef; border: 1px solid #ccd0da; border-radius: 8px; color: #4c4f69; outline: none; }
QListWidget::item { padding: 5px 8px; border-radius: 5px; }
QListWidget::item:selected { background: #ccd0da; }
"""


def get_stylesheet(theme: str = "dark") -> str:
    return DARK_THEME if theme.lower() == "dark" else LIGHT_THEME


def get_status_colour(status: str) -> str:
    return STATUS_COLOURS.get(status, "#6c7086")
