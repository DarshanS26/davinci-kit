try:
    from PyQt6.QtWidgets import QWidget, QGridLayout, QPushButton
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton
    from PySide6.QtCore import Qt, Signal as pyqtSignal

class PresetPills(QWidget):
    preset_selected = pyqtSignal(str)

    def __init__(self, presets: list, default_key: str = None, max_columns: int = 4, parent=None):
        super().__init__(parent)
        self.presets = presets  # list of tuples: [("key", "Label", "Tooltip")]
        self.buttons = {}

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        row = 0
        col = 0
        for key, label, tooltip in presets:
            btn = QPushButton(label, self)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("presetPill")
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            grid.addWidget(btn, row, col)
            self.buttons[key] = btn

            col += 1
            if col >= max_columns:
                col = 0
                row += 1

        if default_key and default_key in self.buttons:
            self._on_click(default_key)
        elif self.buttons:
            first_key = list(self.buttons.keys())[0]
            self._on_click(first_key)

        self.setStyleSheet("""
            QPushButton#presetPill {
                background-color: #101217;
                color: #8c90a4;
                border: 1px solid #242733;
                border-radius: 12px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton#presetPill:hover {
                background-color: #1a1d26;
                color: #ffffff;
                border-color: #383c4e;
            }
            QPushButton#presetPill:checked {
                background-color: rgba(0, 229, 255, 0.12);
                color: #00e5ff;
                border-color: #00e5ff;
                font-weight: 600;
            }
        """)

    def _on_click(self, selected_key: str):
        self.current_key = selected_key
        for key, btn in self.buttons.items():
            btn.setChecked(key == selected_key)
        self.preset_selected.emit(selected_key)

    @property
    def selected_key(self) -> str:
        return getattr(self, "current_key", "")

    def set_preset(self, key: str):
        if key in self.buttons:
            self._on_click(key)
