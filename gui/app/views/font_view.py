import os
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QLabel, QPushButton,
        QListWidget, QFrame, QScrollArea
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QLabel, QPushButton,
        QListWidget, QFrame, QScrollArea
    )
    from PySide6.QtCore import Qt

from ..components.log_viewer import LogViewer
from ..backend.system import get_bin_path
from ..backend.runner import ProcessRunnerThread

class FontView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.runner = None

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title_lbl = QLabel("Fusion Font Path Repair Utility", scroll_content)
        title_lbl.setObjectName("viewTitle")

        sub_lbl = QLabel("Fixes DaVinci Resolve Fusion font map so user-installed fonts (~/.local/share/fonts) display properly", scroll_content)
        sub_lbl.setObjectName("viewSub")

        header_box.addWidget(title_lbl)
        header_box.addWidget(sub_lbl)
        layout.addLayout(header_box)

        card = QFrame(scroll_content)
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        info_lbl = QLabel("ℹ️ DaVinci Resolve Fusion on Linux defaults to checking only /usr/share/fonts. Running this fix updates Resolve's configuration path map to include user fonts.", card)
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 12px; color: #a9acbe;")
        card_layout.addWidget(info_lbl)

        font_paths_lbl = QLabel("Detected System & User Font Paths:", card)
        font_paths_lbl.setObjectName("sectionTitle")
        card_layout.addWidget(font_paths_lbl)

        self.font_list = QListWidget(card)
        self.font_list.setMinimumHeight(100)

        user_fonts_1 = os.path.expanduser("~/.local/share/fonts")
        user_fonts_2 = os.path.expanduser("~/.fonts")
        sys_fonts = "/usr/share/fonts"

        for p in [user_fonts_1, user_fonts_2, sys_fonts]:
            status = "✅ Exists" if os.path.exists(p) else "📁 Will be scanned"
            self.font_list.addItem(f"{p} ({status})")

        card_layout.addWidget(self.font_list)

        btn_fix_fonts = QPushButton("🔤 Apply Font Path Fix (resolve-fonts)", card)
        btn_fix_fonts.setObjectName("primaryBtn")
        btn_fix_fonts.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fix_fonts.clicked.connect(self._run_font_fix)

        card_layout.addWidget(btn_fix_fonts)
        layout.addWidget(card)

        self.log_viewer = LogViewer("Font Fixer Log", scroll_content)
        self.log_viewer.setMinimumHeight(160)
        layout.addWidget(self.log_viewer)

        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area, 1)

    def _run_font_fix(self):
        self.log_viewer.clear_log()
        self.log_viewer.append_log("[INFO] Running resolve-fonts script...")
        bin_path = get_bin_path("resolve-fonts")
        self.runner = ProcessRunnerThread([bin_path])
        self.runner.output_line.connect(self.log_viewer.append_log)
        self.runner.start()
