import os
import subprocess

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QApplication
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
except ImportError:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QApplication
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

from ..backend.system import get_bin_path
from ..backend.runner import ProcessRunnerThread

class DiagDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 DaVinci Resolve System Diagnostics")
        self.resize(720, 560)
        self.runner = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title_lbl = QLabel("DaVinci Resolve Linux System Diagnostic", self)
        title_lbl.setObjectName("viewTitle")

        sub_lbl = QLabel("Executes davinci-kit-info script to inspect GPU, VRAM, OpenCL, GLib libraries, and Resolve environment", self)
        sub_lbl.setObjectName("viewSub")
        sub_lbl.setWordWrap(True)

        header_box.addWidget(title_lbl)
        header_box.addWidget(sub_lbl)
        layout.addLayout(header_box)

        # Log View
        self.txt_output = QTextEdit(self)
        self.txt_output.setReadOnly(True)
        self.txt_output.setFont(QFont("Monospace", 9))
        self.txt_output.setStyleSheet("""
            QTextEdit {
                background-color: #07080a;
                color: #00e5ff;
                border: 1px solid #20232d;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.txt_output, 1)

        # Action Footer
        footer = QHBoxLayout()
        btn_run = QPushButton("🔄 Re-run Diagnostic (davinci-kit-info)", self)
        btn_run.setObjectName("primaryBtn")
        btn_run.clicked.connect(self.run_diagnostic)

        btn_copy = QPushButton("Copy Results", self)
        btn_copy.setObjectName("secondaryBtn")
        btn_copy.clicked.connect(self._copy_results)

        btn_close = QPushButton("Close", self)
        btn_close.setObjectName("secondaryBtn")
        btn_close.clicked.connect(self.accept)

        footer.addWidget(btn_run)
        footer.addWidget(btn_copy)
        footer.addStretch()
        footer.addWidget(btn_close)
        layout.addLayout(footer)

        self.run_diagnostic()

    def run_diagnostic(self):
        self.txt_output.clear()
        self.txt_output.append("[INFO] Running davinci-kit-info system diagnostic...\n")
        bin_path = get_bin_path("davinci-kit-info")
        self.runner = ProcessRunnerThread([bin_path])
        self.runner.output_line.connect(self.txt_output.append)
        self.runner.start()

    def _copy_results(self):
        QApplication.clipboard().setText(self.txt_output.toPlainText())
