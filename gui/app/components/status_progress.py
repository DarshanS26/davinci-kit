import os
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
        QPushButton, QFrame, QTextEdit
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QUrl
    from PyQt6.QtGui import QDesktopServices, QTextCursor
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
        QPushButton, QFrame, QTextEdit
    )
    from PySide6.QtCore import Qt, Signal as pyqtSignal, QUrl
    from PySide6.QtGui import QDesktopServices, QTextCursor

class StatusProgress(QWidget):
    cancel_requested = pyqtSignal()

    def __init__(self, title="Processing Status", parent=None):
        super().__init__(parent)
        self.output_dir = ""
        self.is_expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Card Frame
        card = QFrame(self)
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # Header Row: Icon + Status Text + Action Buttons
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        self.lbl_status_icon = QLabel("🟢", card)
        self.lbl_status_icon.setStyleSheet("font-size: 16px;")

        self.lbl_status_text = QLabel("Ready", card)
        self.lbl_status_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")

        self.lbl_current_file = QLabel("", card)
        self.lbl_current_file.setStyleSheet("font-size: 11px; color: #8c90a4;")
        self.lbl_current_file.setWordWrap(True)

        header_row.addWidget(self.lbl_status_icon)
        header_row.addWidget(self.lbl_status_text)
        header_row.addStretch()

        self.btn_open_folder = QPushButton("📂 Open Output Folder", card)
        self.btn_open_folder.setObjectName("primaryBtn")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.hide()
        self.btn_open_folder.clicked.connect(self._open_output)

        self.btn_toggle_logs = QPushButton("🔍 Show Technical Logs", card)
        self.btn_toggle_logs.setObjectName("secondaryBtn")
        self.btn_toggle_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_logs.clicked.connect(self._toggle_logs)

        header_row.addWidget(self.btn_open_folder)
        header_row.addWidget(self.btn_toggle_logs)

        card_layout.addLayout(header_row)
        card_layout.addWidget(self.lbl_current_file)

        # Progress Bar
        self.progress_bar = QProgressBar(card)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1f222d;
                border-radius: 6px;
                background-color: #08090b;
                height: 18px;
                text-align: center;
                color: #ffffff;
                font-size: 11px;
                font-weight: 500;
            }
            QProgressBar::chunk {
                background-color: #00e5ff;
                border-radius: 5px;
            }
        """)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar)

        # Error / Success Friendly Alert Box
        self.msg_box = QFrame(card)
        self.msg_box.setStyleSheet("border-radius: 6px; padding: 8px 12px;")
        msg_layout = QHBoxLayout(self.msg_box)
        msg_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_msg = QLabel("", self.msg_box)
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet("font-size: 12px; font-weight: 500;")
        msg_layout.addWidget(self.lbl_msg)

        self.msg_box.hide()
        card_layout.addWidget(self.msg_box)

        # Technical Logs Drawer (Hidden by default)
        self.log_drawer = QTextEdit(card)
        self.log_drawer.setReadOnly(True)
        self.log_drawer.setMinimumHeight(120)
        self.log_drawer.setStyleSheet("""
            QTextEdit {
                background-color: #07080a;
                color: #00e5ff;
                font-family: 'Fira Code', 'Monospace', monospace;
                font-size: 11px;
                border: 1px solid #1a1c24;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.log_drawer.hide()
        card_layout.addWidget(self.log_drawer)

        layout.addWidget(card)

    def set_idle(self, text="Ready"):
        self.lbl_status_icon.setText("🟢")
        self.lbl_status_text.setText(text)
        self.lbl_status_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        self.lbl_current_file.setText("")
        self.progress_bar.setValue(0)
        self.msg_box.hide()
        self.btn_open_folder.hide()

    def set_running(self, status="Processing...", current_file=""):
        self.lbl_status_icon.setText("⚡")
        self.lbl_status_text.setText(status)
        self.lbl_status_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #00e5ff;")
        if current_file:
            self.lbl_current_file.setText(f"Active File: {os.path.basename(current_file)}")
        self.msg_box.hide()
        self.btn_open_folder.hide()

    def set_progress(self, percent: int):
        self.progress_bar.setValue(percent)

    def set_success(self, message="Batch completed successfully!", output_dir=""):
        self.lbl_status_icon.setText("✅")
        self.lbl_status_text.setText("Completed Successfully")
        self.lbl_status_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #00ff87;")
        self.lbl_current_file.setText("")
        self.progress_bar.setValue(100)

        self.output_dir = output_dir
        self.lbl_msg.setText(f"🎉 {message}")
        self.msg_box.setStyleSheet("background-color: rgba(0, 255, 135, 0.08); border: 1px solid rgba(0, 255, 135, 0.3);")
        self.lbl_msg.setStyleSheet("color: #00ff87; font-size: 12px; font-weight: 500;")
        self.msg_box.show()

        if output_dir and os.path.exists(output_dir):
            self.btn_open_folder.show()

    def set_error(self, message="An error occurred during processing."):
        self.lbl_status_icon.setText("❌")
        self.lbl_status_text.setText("Processing Error")
        self.lbl_status_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #ff4757;")
        self.lbl_current_file.setText("")

        self.lbl_msg.setText(f"⚠️ {message}")
        self.msg_box.setStyleSheet("background-color: rgba(255, 71, 87, 0.08); border: 1px solid rgba(255, 71, 87, 0.3);")
        self.lbl_msg.setStyleSheet("color: #ff4757; font-size: 12px; font-weight: 500;")
        self.msg_box.show()

    def append_log(self, text: str):
        self.log_drawer.append(text)
        self.log_drawer.moveCursor(QTextCursor.MoveOperation.End)

        # Parse high-level status from log line
        if "[INFO]" in text or "[OK]" in text or "Done" in text:
            clean = text.replace("[INFO]", "").replace("[OK]", "").strip()
            if "→" in clean or "Done:" in clean:
                self.lbl_current_file.setText(clean)
        elif "[ERR]" in text or "Failed" in text or "Error" in text:
            clean = text.replace("[ERR]", "").strip()
            self.set_error(clean)

    def clear_logs(self):
        self.log_drawer.clear()

    def _toggle_logs(self):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.log_drawer.show()
            self.btn_toggle_logs.setText("🙈 Hide Technical Logs")
        else:
            self.log_drawer.hide()
            self.btn_toggle_logs.setText("🔍 Show Technical Logs")

    def _open_output(self):
        if self.output_dir and os.path.exists(self.output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_dir))
