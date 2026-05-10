"""
contact_dialog.py — Contact Us dialog for PostureGuard.
Opens the user's default email client pre-filled via mailto.
"""

import webbrowser
from datetime import datetime
from urllib.parse import quote

from PyQt5.QtCore    import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QMessageBox, QFrame,
)

from src.ui.styles import get_theme_palette

RECIPIENT = "kaffan2025@gmail.com"

# ── Palette ──────────────────────────────────────────────────────────────
BG       = "#0d1117"
BG2      = "#161b22"
BORDER   = "#30363d"
ACCENT   = "#58a6ff"
TEXT     = "#e6edf3"
MUTED    = "#8b949e"
RED      = "#f85149"
GREEN    = "#3fb950"


class ContactDialog(QDialog):
    """Modal dialog to contact the PostureGuard team."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contact Us")
        self.setMinimumWidth(500)
        self.resize(540, 430)
        self.setModal(True)
        self.theme = getattr(parent, "theme", "dark")
        self._build_ui()

    def _apply_theme(self):
        palette = get_theme_palette(self.theme)
        self.setStyleSheet(f"""
            QDialog {{ background: {palette['bg']}; color: {palette['text']}; }}
            QLabel {{ color: {palette['text']}; font-size: 13px; background: transparent; border: none; }}
            QLineEdit, QTextEdit {{
                background: {palette['surface']};
                color: {palette['text']};
                border: 1px solid {palette['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                selection-background-color: {palette['accent']};
            }}
            QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {palette['accent']}; }}
            QPushButton {{
                background: {palette['accent']};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 28px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {palette['accent2']}; }}
            QPushButton:pressed {{ background: {palette['accent']}; }}
            QPushButton#cancelBtn {{
                background: transparent;
                color: {palette['muted']};
                border: 1px solid {palette['border']};
            }}
            QPushButton#cancelBtn:hover {{ border-color: {palette['accent']}; color: {palette['text']}; }}
        """)

    # ─────────────────────────────────────────────────────── UI ──────────

    def _build_ui(self):
        self._apply_theme()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 26, 30, 26)
        lay.setSpacing(14)

        # ── Header ───────────────────────────────────────────────────────
        h_lbl = QLabel("Contact Us")
        h_lbl.setStyleSheet(
            f"color:{ACCENT}; font-size:22px; font-weight:800;"
            f" background:transparent; border:none;"
        )
        sub_lbl = QLabel(f"Your message will be sent to  {RECIPIENT}")
        sub_lbl.setStyleSheet(f"color:{MUTED}; font-size:12px; background:transparent; border:none;")

        lay.addWidget(h_lbl)
        lay.addWidget(sub_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{BORDER}; border:none; max-height:1px;")
        lay.addWidget(sep)

        # ── Form ─────────────────────────────────────────────────────────
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(12)
        form.setFormAlignment(Qt.AlignTop)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Your full name")

        self._id_edit = QLineEdit()
        self._id_edit.setPlaceholderText("User / Employee ID  (optional)")

        self._msg_edit = QTextEdit()
        self._msg_edit.setPlaceholderText(
            "Describe your issue, suggestion, or feedback…"
        )
        self._msg_edit.setMinimumHeight(130)

        lbl_style = (
            f"color:{MUTED}; font-size:12px; font-weight:600;"
            f" background:transparent; border:none;"
        )
        for label_text, widget in (
            ("Name *",    self._name_edit),
            ("User ID",   self._id_edit),
            ("Message *", self._msg_edit),
        ):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(lbl_style)
            form.addRow(lbl, widget)

        lay.addLayout(form)
        lay.addSpacing(6)

        # ── Button row ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        send_btn = QPushButton("📧  Send Message")
        send_btn.clicked.connect(self._send)

        btn_row.addWidget(cancel_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(send_btn)
        lay.addLayout(btn_row)

    # ───────────────────────────────────────────────────── logic ─────────

    def _send(self):
        name = self._name_edit.text().strip()
        uid  = self._id_edit.text().strip()
        msg  = self._msg_edit.toPlainText().strip()

        # Validation
        if not name:
            self._name_edit.setFocus()
            QMessageBox.warning(self, "Missing Field", "Please enter your name.")
            return
        if not msg:
            self._msg_edit.setFocus()
            QMessageBox.warning(self, "Missing Field", "Please enter a message.")
            return

        ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = (
            f"Name:    {name}\n"
            f"User ID: {uid if uid else 'N/A'}\n"
            f"Time:    {ts}\n"
            f"{'─' * 40}\n\n"
            f"{msg}"
        )
        subject = "PostureGuard Contact Message"
        mailto  = (
            f"mailto:{RECIPIENT}"
            f"?subject={quote(subject)}"
            f"&body={quote(body)}"
        )

        try:
            webbrowser.open(mailto)
            QMessageBox.information(
                self,
                "Email Client Opened",
                "Your default email client has been opened with the message "
                "pre-filled.\n\nPlease click  Send  in your email app to deliver it.",
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not open your email client:\n{exc}",
            )
