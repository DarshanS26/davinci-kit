try:
    from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
    from PyQt6.QtCore import Qt
except ImportError:
    from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
    from PySide6.QtCore import Qt

class StatusCard(QFrame):
    def __init__(self, icon: str, title: str, value: str, status_badge: str = None, badge_type: str = "ok", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setMinimumHeight(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Top row: icon + title + badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        icon_lbl = QLabel(icon, self)
        icon_lbl.setStyleSheet("font-size: 16px;")

        title_lbl = QLabel(title, self)
        title_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #8c90a4;")

        top_row.addWidget(icon_lbl)
        top_row.addWidget(title_lbl)
        top_row.addStretch()

        if status_badge:
            badge_lbl = QLabel(status_badge, self)
            bg_color = "rgba(0, 255, 135, 0.1)" if badge_type == "ok" else ("rgba(255, 71, 87, 0.1)" if badge_type == "err" else "rgba(255, 183, 3, 0.1)")
            border_color = "rgba(0, 255, 135, 0.3)" if badge_type == "ok" else ("rgba(255, 71, 87, 0.3)" if badge_type == "err" else "rgba(255, 183, 3, 0.3)")
            text_color = "#00ff87" if badge_type == "ok" else ("#ff4757" if badge_type == "err" else "#ffb703")

            badge_lbl.setStyleSheet(f"""
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                font-size: 11px;
                font-weight: 500;
                padding: 2px 8px;
                border-radius: 4px;
            """)
            top_row.addWidget(badge_lbl)

        # Bottom row: Value
        self.value_lbl = QLabel(value, self)
        self.value_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
        self.value_lbl.setWordWrap(True)

        layout.addLayout(top_row)
        layout.addWidget(self.value_lbl)

    def set_value(self, text: str):
        self.value_lbl.setText(text)
