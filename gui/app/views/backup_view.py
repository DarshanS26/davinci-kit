import os
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QFileDialog, QCheckBox, QFrame, QScrollArea
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QFileDialog, QCheckBox, QFrame, QScrollArea
    )
    from PySide6.QtCore import Qt

from ..components.log_viewer import LogViewer
from ..backend.system import get_bin_path
from ..backend.runner import ProcessRunnerThread

class BackupView(QWidget):
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
        title_lbl = QLabel("Resolve Settings Backup & Restore Manager", scroll_content)
        title_lbl.setObjectName("viewTitle")

        sub_lbl = QLabel("Backup or restore DaVinci Resolve configurations, project databases, LUTs, presets, and macros", scroll_content)
        sub_lbl.setObjectName("viewSub")

        header_box.addWidget(title_lbl)
        header_box.addWidget(sub_lbl)
        layout.addLayout(header_box)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        # Card 1: Create Backup
        create_card = QFrame(scroll_content)
        create_card.setObjectName("cardFrame")
        create_layout = QVBoxLayout(create_card)
        create_layout.setContentsMargins(16, 16, 16, 16)
        create_layout.setSpacing(12)

        c_title = QLabel("💾 Create New Backup", create_card)
        c_title.setObjectName("sectionTitle")
        create_layout.addWidget(c_title)

        c_desc = QLabel("Archives ~/.local/share/DaVinciResolve & ~/.config/Blackmagic Design into a compressed tarball.", create_card)
        c_desc.setWordWrap(True)
        c_desc.setStyleSheet("font-size: 11px; color: #7e8299;")
        create_layout.addWidget(c_desc)

        out_layout = QHBoxLayout()
        out_lbl = QLabel("Save to:", create_card)
        out_lbl.setFixedWidth(60)
        self.txt_backup_dir = QLineEdit(os.path.expanduser("~"), create_card)
        btn_browse_dir = QPushButton("Browse...", create_card)
        btn_browse_dir.setObjectName("secondaryBtn")
        btn_browse_dir.clicked.connect(self._browse_backup_dir)
        out_layout.addWidget(out_lbl)
        out_layout.addWidget(self.txt_backup_dir, 1)
        out_layout.addWidget(btn_browse_dir)
        create_layout.addLayout(out_layout)

        self.chk_dry_run = QCheckBox("Dry-run preview (do not create file)", create_card)
        create_layout.addWidget(self.chk_dry_run)

        create_layout.addStretch()

        btn_create = QPushButton("📦 Create Backup Archive", create_card)
        btn_create.setObjectName("primaryBtn")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self._run_backup)
        create_layout.addWidget(btn_create)

        # Card 2: Restore Backup
        restore_card = QFrame(scroll_content)
        restore_card.setObjectName("cardFrame")
        restore_layout = QVBoxLayout(restore_card)
        restore_layout.setContentsMargins(16, 16, 16, 16)
        restore_layout.setSpacing(12)

        r_title = QLabel("↺ Restore from Archive", restore_card)
        r_title.setObjectName("sectionTitle")
        restore_layout.addWidget(r_title)

        r_desc = QLabel("Select a previously generated resolve-backup tarball (.tar.gz) to restore your settings.", restore_card)
        r_desc.setWordWrap(True)
        r_desc.setStyleSheet("font-size: 11px; color: #7e8299;")
        restore_layout.addWidget(r_desc)

        file_layout = QHBoxLayout()
        file_lbl = QLabel("Backup File:", restore_card)
        file_lbl.setFixedWidth(80)
        self.txt_restore_file = QLineEdit(restore_card)
        self.txt_restore_file.setPlaceholderText("Select resolve-backup-*.tar.gz")
        btn_browse_file = QPushButton("Browse...", restore_card)
        btn_browse_file.setObjectName("secondaryBtn")
        btn_browse_file.clicked.connect(self._browse_restore_file)
        file_layout.addWidget(file_lbl)
        file_layout.addWidget(self.txt_restore_file, 1)
        file_layout.addWidget(btn_browse_file)
        restore_layout.addLayout(file_layout)

        restore_layout.addStretch()

        btn_restore = QPushButton("⚡ Restore Resolve Settings", restore_card)
        btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #ffb703;
                color: #090a0c;
                font-weight: 600;
                font-size: 13px;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #ffc83b;
            }
        """)
        btn_restore.clicked.connect(self._run_restore)
        restore_layout.addWidget(btn_restore)

        cards_layout.addWidget(create_card, 1)
        cards_layout.addWidget(restore_card, 1)

        layout.addLayout(cards_layout)

        self.log_viewer = LogViewer("Backup & Restore Log", scroll_content)
        self.log_viewer.setMinimumHeight(160)
        layout.addWidget(self.log_viewer)

        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area, 1)

    def _browse_backup_dir(self):
        from ..components.drop_zone import DropZone
        default_dir = DropZone.get_default_dir()
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Save Backup", default_dir)
        if folder:
            DropZone.save_last_dir(folder)
            self.txt_backup_dir.setText(folder)

    def _browse_restore_file(self):
        from ..components.drop_zone import DropZone
        default_dir = DropZone.get_default_dir()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Backup Tarball", default_dir, "Archive Files (*.tar.gz *.tgz)")
        if file_path:
            DropZone.save_last_dir(file_path)
            self.txt_restore_file.setText(file_path)

    def _run_backup(self):
        dest = self.txt_backup_dir.text().strip()
        cmd = [get_bin_path("resolve-backup")]

        if dest:
            cmd.extend(["-o", dest])
        if self.chk_dry_run.isChecked():
            cmd.append("-n")

        self.log_viewer.clear_log()
        self.log_viewer.append_log(f"[INFO] Creating backup with command: {' '.join(cmd)}")

        self.runner = ProcessRunnerThread(cmd)
        self.runner.output_line.connect(self.log_viewer.append_log)
        self.runner.start()

    def _run_restore(self):
        tarball = self.txt_restore_file.text().strip()
        if not tarball or not os.path.exists(tarball):
            self.log_viewer.append_log("[ERR] Please select a valid .tar.gz backup archive file to restore.")
            return

        cmd = [get_bin_path("resolve-backup"), "--restore", tarball]

        self.log_viewer.clear_log()
        self.log_viewer.append_log(f"[INFO] Restoring backup from: {tarball}")

        self.runner = ProcessRunnerThread(cmd)
        self.runner.output_line.connect(self.log_viewer.append_log)
        self.runner.start()
