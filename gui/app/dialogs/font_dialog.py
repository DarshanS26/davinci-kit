import os

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QListWidget, QFrame
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QListWidget, QFrame
    )
    from PySide6.QtCore import Qt

from ..components.log_viewer import LogViewer
from ..backend.system import get_bin_path
from ..backend.runner import ProcessRunnerThread

class FontDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔤 Fusion Font Path Repair Utility")
        self.resize(560, 440)
        self.runner = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title_lbl = QLabel("Fusion Font Path Repair Utility", self)
        title_lbl.setObjectName("viewTitle")

        sub_lbl = QLabel("Fixes DaVinci Resolve Fusion font map so user-installed fonts (~/.local/share/fonts) display properly", self)
        sub_lbl.setObjectName("viewSub")
        sub_lbl.setWordWrap(True)

        header_box.addWidget(title_lbl)
        header_box.addWidget(sub_lbl)
        layout.addLayout(header_box)

        card = QFrame(self)
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        info_lbl = QLabel("ℹ️ DaVinci Resolve Fusion on Linux defaults to checking only /usr/share/fonts. Running this fix updates Resolve's configuration path map to include user fonts.", card)
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 12px; color: #a9acbe;")
        card_layout.addWidget(info_lbl)

        font_paths_lbl = QLabel("Detected System & User Font Paths:", card)
        font_paths_lbl.setObjectName("sectionTitle")
        card_layout.addWidget(font_paths_lbl)

        self.font_list = QListWidget(card)
        self.font_list.setFixedHeight(75)

        user_fonts_1 = os.path.expanduser("~/.local/share/fonts")
        user_fonts_2 = os.path.expanduser("~/.fonts")
        sys_fonts = "/usr/share/fonts"

        for p in [user_fonts_1, user_fonts_2, sys_fonts]:
            status = "✅ Exists" if os.path.exists(p) else "📁 Will be scanned"
            self.font_list.addItem(f"{p} ({status})")

        card_layout.addWidget(self.font_list)

        btn_fix_fonts = QPushButton("🔤 Apply Font Path Fix (davinci-kit-fonts)", card)
        btn_fix_fonts.setObjectName("primaryBtn")
        btn_fix_fonts.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fix_fonts.clicked.connect(self._run_font_fix)

        card_layout.addWidget(btn_fix_fonts)
        layout.addWidget(card)

        self.log_viewer = LogViewer("Font Fixer Log", self)
        self.log_viewer.setMinimumHeight(110)
        layout.addWidget(self.log_viewer, 1)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        btn_close = QPushButton("Close", self)
        btn_close.setObjectName("secondaryBtn")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def _run_font_fix(self):
        self.log_viewer.clear_log()
        self.log_viewer.append_log("[INFO] Running davinci-kit-fonts script...")
        bin_path = get_bin_path("davinci-kit-fonts")
        self.runner = ProcessRunnerThread([bin_path])
        self.runner.output_line.connect(self.log_viewer.append_log)
        self.runner.start()
