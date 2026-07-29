try:
    from PyQt6.QtWidgets import (
        QWidget, QHBoxLayout, QLabel, QPushButton, QMenu, QSizePolicy
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QAction, QCursor
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QHBoxLayout, QLabel, QPushButton, QMenu, QSizePolicy
    )
    from PySide6.QtCore import Qt, Signal as pyqtSignal
    from PySide6.QtGui import QAction, QCursor

class TabBar(QWidget):
    tab_changed = pyqtSignal(int)
    open_watch_requested = pyqtSignal()
    open_fonts_requested = pyqtSignal()
    open_backup_requested = pyqtSignal()
    open_diag_requested = pyqtSignal()
    run_fix_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setObjectName("tabBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(6)

        # Primary Tabs
        self.tabs_data = [
            ("📥 Transcode", 0, "Ctrl+1"),
            ("📤 Export", 1, "Ctrl+2"),
            ("🎵 Audio", 2, "Ctrl+3"),
            ("🔍 Inspector", 3, "Ctrl+4")
        ]

        self.tab_buttons = []
        for text, index, shortcut in self.tabs_data:
            btn = QPushButton(text, self)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("tabBtn")
            btn.setToolTip(f"Switch tab ({shortcut})")
            btn.clicked.connect(lambda checked, idx=index: self.set_current_index(idx))
            layout.addWidget(btn)
            self.tab_buttons.append(btn)

        layout.addStretch()

        # Secondary Dropdowns
        # 1. Watch Menu Button
        self.btn_watch_menu = QPushButton("👁️ Watch Daemon ▾", self)
        self.btn_watch_menu.setObjectName("tabDropdownBtn")
        self.btn_watch_menu.setCursor(Qt.CursorShape.PointingHandCursor)

        watch_menu = QMenu(self.btn_watch_menu)
        act_watch_cfg = QAction("⚙️ Configure Watch Folder...", self)
        act_watch_cfg.triggered.connect(self.open_watch_requested.emit)
        watch_menu.addAction(act_watch_cfg)
        self.btn_watch_menu.setMenu(watch_menu)

        # 2. Tools Menu Button
        self.btn_tools_menu = QPushButton("🔧 Tools ▾", self)
        self.btn_tools_menu.setObjectName("tabDropdownBtn")
        self.btn_tools_menu.setCursor(Qt.CursorShape.PointingHandCursor)

        tools_menu = QMenu(self.btn_tools_menu)

        act_fix = QAction("🛠️ Fix & Launch Resolve (davinci-kit-fix)", self)
        act_fix.triggered.connect(self.run_fix_requested.emit)
        tools_menu.addAction(act_fix)

        tools_menu.addSeparator()

        act_fonts = QAction("🔤 Fusion Fonts Repair...", self)
        act_fonts.triggered.connect(self.open_fonts_requested.emit)
        tools_menu.addAction(act_fonts)

        act_backup = QAction("💾 Backup & Restore Settings...", self)
        act_backup.triggered.connect(self.open_backup_requested.emit)
        tools_menu.addAction(act_backup)

        act_diag = QAction("📊 System Diagnostics...", self)
        act_diag.triggered.connect(self.open_diag_requested.emit)
        tools_menu.addAction(act_diag)

        self.btn_tools_menu.setMenu(tools_menu)

        layout.addWidget(self.btn_watch_menu)
        layout.addWidget(self.btn_tools_menu)

        self.set_current_index(0)

    def set_current_index(self, index: int, block_signal: bool = False):
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == index)
        if not block_signal:
            self.tab_changed.emit(index)
