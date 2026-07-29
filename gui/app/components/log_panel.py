import os

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QApplication
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont, QTextCursor
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QApplication
    )
    from PySide6.QtCore import Qt, Signal as pyqtSignal
    from PySide6.QtGui import QFont, QTextCursor

class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.setObjectName("logPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("📋 Execution Log Feed", self)
        lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #c2c5d6;")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        btn_copy = QPushButton("Copy Logs", self)
        btn_copy.setObjectName("secondaryBtn")
        btn_copy.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        btn_copy.clicked.connect(self._copy_logs)

        btn_clear = QPushButton("Clear", self)
        btn_clear.setObjectName("secondaryBtn")
        btn_clear.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        btn_clear.clicked.connect(self.clear_logs)

        btn_close = QPushButton("✕ Hide", self)
        btn_close.setObjectName("secondaryBtn")
        btn_close.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        btn_close.clicked.connect(self.hide)

        hdr_layout.addWidget(btn_copy)
        hdr_layout.addWidget(btn_clear)
        hdr_layout.addWidget(btn_close)
        layout.addLayout(hdr_layout)

        self.txt_logs = QTextEdit(self)
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setFont(QFont("Monospace", 9))
        self.txt_logs.setStyleSheet("""
            QTextEdit {
                background-color: #07080a;
                color: #a0a5ba;
                border: 1px solid #1a1c24;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        layout.addWidget(self.txt_logs, 1)

    def append_log(self, text: str):
        if not text:
            return
        clean_text = text.strip()
        if "[ERR]" in clean_text or "Error" in clean_text or "Failed" in clean_text:
            colored = f'<span style="color: #ff4757;">{clean_text}</span>'
        elif "[OK]" in clean_text or "Done" in clean_text or "SUCCESS" in clean_text:
            colored = f'<span style="color: #2ed573;">{clean_text}</span>'
        elif "[WARN]" in clean_text:
            colored = f'<span style="color: #ffa502;">{clean_text}</span>'
        elif "[INFO]" in clean_text:
            colored = f'<span style="color: #1e90ff;">{clean_text}</span>'
        else:
            colored = f'<span style="color: #a0a5ba;">{clean_text}</span>'

        self.txt_logs.append(colored)
        self.txt_logs.moveCursor(QTextCursor.MoveOperation.End)

    def clear_logs(self):
        self.txt_logs.clear()

    def _copy_logs(self):
        QApplication.clipboard().setText(self.txt_logs.toPlainText())
