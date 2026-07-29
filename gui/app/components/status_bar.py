import os

try:
    from PyQt6.QtWidgets import (
        QWidget, QHBoxLayout, QLabel, QPushButton, QProgressBar
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QUrl
    from PyQt6.QtGui import QDesktopServices
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QHBoxLayout, QLabel, QPushButton, QProgressBar
    )
    from PySide6.QtCore import Qt, Signal as pyqtSignal, QUrl
    from PySide6.QtGui import QDesktopServices

class StatusBar(QWidget):
    cancel_requested = pyqtSignal()
    toggle_logs_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setObjectName("statusBar")

        self.last_output_dir = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Status Icon & Main Message Label
        self.lbl_status = QLabel("🟢 Ready  •  No files queued", self)
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 500; color: #d0d3e5;")
        layout.addWidget(self.lbl_status)

        # Progress Bar (hidden when idle)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #14161f;
                border: 1px solid #242733;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #00e5ff;
                border-radius: 5px;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.lbl_pct = QLabel("", self)
        self.lbl_pct.setStyleSheet("font-size: 11px; font-weight: 600; color: #00e5ff;")
        self.lbl_pct.hide()
        layout.addWidget(self.lbl_pct)

        layout.addStretch()

        # Action Buttons
        self.btn_open_folder = QPushButton("📂 Open Output Folder", self)
        self.btn_open_folder.setObjectName("secondaryBtn")
        self.btn_open_folder.setStyleSheet("padding: 3px 10px; font-size: 11px;")
        self.btn_open_folder.clicked.connect(self._open_folder)
        self.btn_open_folder.hide()
        layout.addWidget(self.btn_open_folder)

        self.btn_cancel = QPushButton("🛑 Cancel", self)
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setStyleSheet("padding: 3px 10px; font-size: 11px;")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        self.btn_cancel.hide()
        layout.addWidget(self.btn_cancel)

        self.btn_toggle_logs = QPushButton("📋 Logs ▾", self)
        self.btn_toggle_logs.setObjectName("secondaryBtn")
        self.btn_toggle_logs.setStyleSheet("padding: 3px 10px; font-size: 11px;")
        self.btn_toggle_logs.clicked.connect(self.toggle_logs_requested.emit)
        layout.addWidget(self.btn_toggle_logs)

    def set_idle(self, summary_text: str = "No files queued"):
        self.lbl_status.setText(f"🟢 Ready  •  {summary_text}")
        self.progress_bar.hide()
        self.lbl_pct.hide()
        self.btn_cancel.hide()
        self.btn_open_folder.hide()

    def set_running(self, action_text: str, current_file: str = ""):
        file_msg = f" ({current_file})" if current_file else ""
        self.lbl_status.setText(f"⚡ {action_text}{file_msg}")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.lbl_pct.setText("0%")
        self.lbl_pct.show()
        self.btn_cancel.show()
        self.btn_open_folder.hide()

    def set_progress(self, percent: int):
        pct = max(0, min(100, percent))
        self.progress_bar.setValue(pct)
        self.lbl_pct.setText(f"{pct}%")

    def set_success(self, message: str, output_folder: str = ""):
        self.last_output_dir = output_folder
        self.lbl_status.setText(f"✅ {message}")
        self.progress_bar.hide()
        self.lbl_pct.hide()
        self.btn_cancel.hide()
        if output_folder and os.path.exists(output_folder):
            self.btn_open_folder.show()
        else:
            self.btn_open_folder.hide()

    def set_error(self, message: str):
        self.lbl_status.setText(f"❌ {message}")
        self.progress_bar.hide()
        self.lbl_pct.hide()
        self.btn_cancel.hide()
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            self.btn_open_folder.show()

    def _open_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output_dir))
