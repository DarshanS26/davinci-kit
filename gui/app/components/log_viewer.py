try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton, QLabel
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QTextCursor
except ImportError:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton, QLabel
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTextCursor

class LogViewer(QWidget):
    def __init__(self, title="Terminal Log", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.title_lbl = QLabel(title, self)
        self.title_lbl.setStyleSheet("font-weight: 500; color: #7e8299; font-size: 11px;")

        self.btn_clear = QPushButton("Clear", self)
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_clear.clicked.connect(self.clear_log)

        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(self.btn_clear)

        self.text_area = QTextEdit(self)
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: #07080a;
                color: #00e5ff;
                font-family: 'Fira Code', 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
                font-weight: 400;
                border: 1px solid #1a1c24;
                border-radius: 6px;
                padding: 8px 10px;
            }
        """)

        layout.addLayout(header)
        layout.addWidget(self.text_area)

    def append_log(self, text: str):
        import re
        clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)

        color_style = "color: #b0b3c6;"
        if "[OK]" in clean or "[SUCCESS]" in clean or "Done" in clean:
            color_style = "color: #00ff87; font-weight: 500;"
        elif "[ERR]" in clean or "Error" in clean or "Failed" in clean:
            color_style = "color: #ff4757; font-weight: 500;"
        elif "[WARN]" in clean or "Warning" in clean:
            color_style = "color: #ffb703; font-weight: 500;"
        elif "[INFO]" in clean:
            color_style = "color: #00e5ff;"

        escaped = clean.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        html = f'<span style="{color_style}">{escaped}</span>'

        self.text_area.append(html)
        self.text_area.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self):
        self.text_area.clear()
