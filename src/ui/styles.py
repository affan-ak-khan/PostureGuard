"""styles.py — Modern dark/light Qt stylesheets for PostureGuard."""

# ── Colour tokens ─────────────────────────────────────────────────────────
STATUS_COLOURS = {
    "GOOD":         "#3fb950",
    "SLOUCHING":    "#d29922",
    "FORWARD_HEAD": "#db6d28",
    "NECK_STRAIN":  "#f85149",
    "TIRED":        "#d29922",
    "DROWSY":       "#f85149",
    "ALERT":        "#3fb950",
    "UNKNOWN":      "#8b949e",
    "NOT_STARTED":  "#8b949e",
    "STOPPED":      "#8b949e",
}


def get_status_colour(status: str) -> str:
    return STATUS_COLOURS.get(status.upper(), "#8b949e")


THEME_PALETTES = {
    "dark": {
        "bg": "#0d1117",
        "bg2": "#161b22",
        "bg3": "#0d1117",
        "border": "#30363d",
        "border2": "#21262d",
        "text": "#e6edf3",
        "muted": "#8b949e",
        "accent": "#58a6ff",
        "accent2": "#79c0ff",
        "green": "#3fb950",
        "yellow": "#d29922",
        "orange": "#db6d28",
        "red": "#f85149",
        "card": "#161b22",
        "surface": "#0d1117",
        "chart": "#161b22",
        "panel": "#0d1117",
    },
    "light": {
        "bg": "#f6f8fc",
        "bg2": "#ffffff",
        "bg3": "#f6f8fc",
        "border": "#d0d7de",
        "border2": "#e4e9ef",
        "text": "#1f2328",
        "muted": "#656d76",
        "accent": "#0969da",
        "accent2": "#218bff",
        "green": "#1a7f37",
        "yellow": "#9a6700",
        "orange": "#bc4c00",
        "red": "#cf222e",
        "card": "#ffffff",
        "surface": "#ffffff",
        "chart": "#ffffff",
        "panel": "#ffffff",
    },
}


def get_theme_palette(theme: str = "dark") -> dict:
    return THEME_PALETTES.get(theme if theme == "light" else "dark", THEME_PALETTES["dark"])


# ── Dark theme stylesheet ────────────────────────────────────────────────
DARK_THEME = """
/* ── Global ─────────────────────────────────────────────── */
* {
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size:   13px;
    color:       #e6edf3;
}

QMainWindow, QDialog {
    background: #0d1117;
}

/* ── Menu bar ───────────────────────────────────────────── */
QMenuBar {
    background: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 600;
}
QMenuBar::item {
    padding: 6px 14px;
    border-radius: 6px;
    color: #8b949e;
}
QMenuBar::item:selected {
    background: #21262d;
    color: #e6edf3;
}
QMenu {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 28px 8px 16px;
    border-radius: 6px;
    color: #e6edf3;
}
QMenu::item:selected {
    background: #58a6ff;
    color: #0d1117;
}
QMenu::separator {
    height: 1px;
    background: #30363d;
    margin: 4px 12px;
}

/* ── Group boxes ────────────────────────────────────────── */
QGroupBox {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    margin-top: 10px;
    padding: 14px 10px 10px 10px;
    font-weight: 700;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 3px 10px;
    color: #8b949e;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

/* ── Buttons ────────────────────────────────────────────── */
QPushButton {
    background: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 600;
    min-height: 18px;
}
QPushButton:hover {
    background: #30363d;
    border-color: #58a6ff;
    color: #ffffff;
}
QPushButton:pressed {
    background: #58a6ff;
    color: #0d1117;
}
QPushButton:disabled {
    background: #161b22;
    color: #484f58;
    border-color: #21262d;
}

QPushButton#startButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #238636, stop:1 #2ea043);
    color: #ffffff;
    border: 1px solid #2ea043;
    font-weight: 700;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px 20px;
}
QPushButton#startButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2ea043, stop:1 #3fb950);
    border-color: #3fb950;
}
QPushButton#startButton:disabled {
    background: #161b22;
    color: #484f58;
    border-color: #21262d;
}

QPushButton#stopButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #b62324, stop:1 #da3633);
    color: #ffffff;
    border: 1px solid #da3633;
    font-weight: 700;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px 20px;
}
QPushButton#stopButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #da3633, stop:1 #f85149);
    border-color: #f85149;
}
QPushButton#stopButton:disabled {
    background: #161b22;
    color: #484f58;
    border-color: #21262d;
}

QPushButton#iconButton {
    background: #161b22;
    color: #8b949e;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#iconButton:hover {
    background: #21262d;
    color: #58a6ff;
    border-color: #58a6ff;
}

/* ── Sidebar nav buttons ──────────────────────────────── */
QPushButton#sideNavBtn {
    background: transparent;
    border: none;
    border-radius: 12px;
    color: #8b949e;
}
QPushButton#sideNavBtn:hover {
    background: rgba(88,166,255,0.15);
    color: #58a6ff;
    border: 1px solid rgba(88,166,255,0.25);
}
QPushButton#sideNavBtn:hover QLabel {
    color: #58a6ff;
}
QPushButton#sideNavBtn:pressed {
    background: rgba(88,166,255,0.25);
}

/* ── Tooltips ─────────────────────────────────────── */
QToolTip {
    background: #1c2128;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

/* ── Inputs ─────────────────────────────────────────────── */
QComboBox {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 14px;
    color: #e6edf3;
    font-size: 14px;
    min-height: 18px;
}
QComboBox:hover {
    border-color: #58a6ff;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8b949e;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    selection-background-color: #58a6ff;
    selection-color: #0d1117;
    padding: 4px;
    outline: none;
}

QSpinBox, QDoubleSpinBox {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e6edf3;
    font-size: 14px;
    min-height: 18px;
}
QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #58a6ff;
}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: #21262d;
    border: none;
    width: 22px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #30363d;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #8b949e;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #8b949e;
}

/* ── Checkbox ───────────────────────────────────────────── */
QCheckBox {
    spacing: 10px;
    font-size: 14px;
    color: #e6edf3;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 2px solid #30363d;
    background: #0d1117;
}
QCheckBox::indicator:hover {
    border-color: #58a6ff;
}
QCheckBox::indicator:checked {
    background: #58a6ff;
    border-color: #58a6ff;
}

/* ── Slider ─────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 8px;
    background: #21262d;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #58a6ff;
    border: 2px solid #79c0ff;
    width: 20px;
    height: 20px;
    margin: -7px 0;
    border-radius: 11px;
}
QSlider::handle:horizontal:hover {
    background: #79c0ff;
}
QSlider::sub-page:horizontal {
    background: #58a6ff;
    border-radius: 4px;
}

/* ── Progress bar ───────────────────────────────────────── */
QProgressBar {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    text-align: center;
    font-size: 12px;
    font-weight: 600;
    color: #e6edf3;
    min-height: 24px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #58a6ff, stop:1 #79c0ff);
    border-radius: 7px;
}

/* ── Tabs ───────────────────────────────────────────────── */
QTabWidget::pane {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: #8b949e;
    padding: 10px 24px;
    margin-right: 4px;
    border-bottom: 3px solid transparent;
    font-size: 13px;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #58a6ff;
    border-bottom-color: #58a6ff;
}
QTabBar::tab:hover:!selected {
    color: #e6edf3;
    border-bottom-color: #30363d;
}

/* ── List widget ────────────────────────────────────────── */
QListWidget {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 6px;
    font-size: 13px;
    outline: none;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 0;
}
QListWidget::item:hover {
    background: #161b22;
}

/* ── Scroll bars ────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #484f58;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 5px;
    min-width: 30px;
}

/* ── Status bar ─────────────────────────────────────────── */
QStatusBar {
    background: #161b22;
    border-top: 1px solid #30363d;
    color: #8b949e;
    font-size: 13px;
    padding: 4px 16px;
}

/* ── Labels (general) ───────────────────────────────────── */
QLabel {
    color: #e6edf3;
    background: transparent;
    font-size: 14px;
}

/* ── Dialog button box ──────────────────────────────────── */
QDialogButtonBox QPushButton {
    min-width: 100px;
}

/* ── Tooltips ───────────────────────────────────────────── */
QToolTip {
    background: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
"""


# ── Light theme stylesheet ───────────────────────────────────────────────
LIGHT_THEME = """
/* ── Global ─────────────────────────────────────────────── */
* {
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size:   13px;
    color:       #1f2328;
}

QMainWindow, QDialog {
    background: #ffffff;
}

QMenuBar {
    background: #f6f8fa;
    border-bottom: 1px solid #d0d7de;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 600;
}
QMenuBar::item {
    padding: 6px 14px;
    border-radius: 6px;
    color: #656d76;
}
QMenuBar::item:selected {
    background: #eaeef2;
    color: #1f2328;
}
QMenu {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 28px 8px 16px;
    border-radius: 6px;
    color: #1f2328;
}
QMenu::item:selected {
    background: #0969da;
    color: #ffffff;
}

QGroupBox {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    margin-top: 10px;
    padding: 14px 10px 10px 10px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 3px 10px;
    color: #656d76;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
}

QPushButton {
    background: #f6f8fa;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background: #eaeef2;
    border-color: #0969da;
}
QPushButton:pressed {
    background: #0969da;
    color: #ffffff;
}
QPushButton:disabled {
    background: #f6f8fa;
    color: #afb8c1;
    border-color: #eaeef2;
}

QPushButton#startButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #1a7f37, stop:1 #2da44e);
    color: #ffffff;
    border: 1px solid #2da44e;
    font-weight: 700;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px 20px;
}
QPushButton#startButton:hover {
    background: #2da44e;
}

QPushButton#stopButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #cf222e, stop:1 #fa4549);
    color: #ffffff;
    border: 1px solid #cf222e;
    font-weight: 700;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px 20px;
}

QPushButton#iconButton {
    background: #ffffff;
    color: #656d76;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 12px;
}
QPushButton#iconButton:hover {
    color: #0969da;
    border-color: #0969da;
}

/* ── Sidebar nav buttons ────────────────────────────── */
QPushButton#sideNavBtn {
    background: transparent;
    border: none;
    border-radius: 10px;
    color: #656d76;
}
QPushButton#sideNavBtn:hover {
    background: rgba(9,105,218,0.12);
    color: #0969da;
}
QPushButton#sideNavBtn:pressed {
    background: rgba(9,105,218,0.20);
}

/* ── Tooltips ───────────────────────────────────── */
QToolTip {
    background: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

QComboBox {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 8px 14px;
    color: #1f2328;
    min-height: 18px;
}
QComboBox:hover {
    border-color: #0969da;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #d0d7de;
    selection-background-color: #0969da;
    selection-color: #ffffff;
}

QSpinBox, QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1f2328;
    min-height: 18px;
}
QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #0969da;
}

QCheckBox {
    spacing: 10px;
    color: #1f2328;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 2px solid #d0d7de;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #0969da;
    border-color: #0969da;
}

QSlider::groove:horizontal {
    height: 8px;
    background: #eaeef2;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #0969da;
    border: 2px solid #218bff;
    width: 20px;
    height: 20px;
    margin: -7px 0;
    border-radius: 11px;
}
QSlider::sub-page:horizontal {
    background: #0969da;
    border-radius: 4px;
}

QProgressBar {
    background: #eaeef2;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    text-align: center;
    font-size: 12px;
    font-weight: 600;
    color: #1f2328;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #0969da, stop:1 #218bff);
    border-radius: 7px;
}

QTabWidget::pane {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 10px;
}
QTabBar::tab {
    background: transparent;
    color: #656d76;
    padding: 10px 24px;
    margin-right: 4px;
    border-bottom: 3px solid transparent;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #0969da;
    border-bottom-color: #0969da;
}
QTabBar::tab:hover:!selected {
    color: #1f2328;
}

QListWidget {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    padding: 6px;
    font-size: 13px;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 0;
}
QListWidget::item:hover {
    background: #f6f8fa;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #d0d7de;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QStatusBar {
    background: #f6f8fa;
    border-top: 1px solid #d0d7de;
    color: #656d76;
    font-size: 13px;
}

QLabel {
    color: #1f2328;
    background: transparent;
}

QToolTip {
    background: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 10px;
}
"""


def get_stylesheet(theme: str = "dark") -> str:
    return LIGHT_THEME if theme == "light" else DARK_THEME
