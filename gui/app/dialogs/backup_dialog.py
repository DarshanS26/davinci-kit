import os

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QFileDialog, QCheckBox, QFrame
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QFileDialog, QCheckBox, QFrame
    )
    from PySide6.QtCore import Qt

from ..components.log_viewer import LogViewer
from ..backend.system import get_bin_path
from ..backend.runner import ProcessRunnerThread

class BackupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💾 Resolve Settings Backup & Restore Manager")
        self.resize(680, 520)
        self.runner = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title_lbl = QLabel("Resolve Settings Backup & Restore Manager", self)
        title_lbl.setObjectName("viewTitle")

        sub_lbl = QLabel("Backup or restore DaVinci Resolve configurations, project databases, LUTs, presets, and macros", self)
        sub_lbl.setObjectName("viewSub")
        sub_lbl.setWordWrap(True)

        header_box.addWidget(title_lbl)
        header_box.addWidget(sub_lbl)
        layout.addLayout(header_box)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        # Card 1: Create Backup
        create_card = QFrame(self)
        create_card.setObjectName("cardFrame")
        create_layout = QVBoxLayout(create_card)
        create_layout.setContentsMargins(14, 14, 14, 14)
        create_layout.setSpacing(10)

        c_title = QLabel("💾 Create New Backup", create_card)
        c_title.setObjectName("sectionTitle")
        create_layout.addWidget(c_title)

        c_desc = QLabel("Archives ~/.local/share/DaVinciResolve & ~/.config/Blackmagic Design into a compressed tarball.", create_card)
        c_desc.setWordWrap(True)
        c_desc.setStyleSheet("font-size: 11px; color: #7e8299;")
        create_layout.addWidget(c_desc)

        out_layout = QHBoxLayout()
        out_lbl = QLabel("Save to:", create_card)
        out_lbl.setFixedWidth(55)
        self.txt_backup_dir = QLineEdit(os.path.expanduser("~"), create_card)
        btn_browse_dir = QPushButton("Browse...", create_card)
        btn_browse_dir.setObjectName("secondaryBtn")
        btn_browse_dir.clicked.connect(self._browse_backup_dir)
        out_layout.addWidget(out_lbl)
        out_layout.addWidget(self.txt_backup_dir, 1)
        out_layout.addWidget(btn_browse_dir)
        create_layout.addLayout(out_layout)

        self.chk_dry_run = QCheckBox("Dry-run preview", create_card)
        create_layout.addWidget(self.chk_dry_run)

        create_layout.addStretch()

        btn_create = QPushButton("📦 Create Backup Archive", create_card)
        btn_create.setObjectName("primaryBtn")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self._run_backup)
        create_layout.addWidget(btn_create)

        # Card 2: Restore Backup
        restore_card = QFrame(self)
        restore_card.setObjectName("cardFrame")
        restore_layout = QVBoxLayout(restore_card)
        restore_layout.setContentsMargins(14, 14, 14, 14)
        restore_layout.setSpacing(10)

        r_title = QLabel("↺ Restore from Archive", restore_card)
        r_title.setObjectName("sectionTitle")
        restore_layout.addWidget(r_title)

        r_desc = QLabel("Select a previously generated resolve-backup tarball (.tar.gz) to restore your settings.", restore_card)
        r_desc.setWordWrap(True)
        r_desc.setStyleSheet("font-size: 11px; color: #7e8299;")
        restore_layout.addWidget(r_desc)

        file_layout = QHBoxLayout()
        file_lbl = QLabel("Backup File:", restore_card)
        file_lbl.setFixedWidth(75)
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
                font-size: 12px;
                border-radius: 6px;
                padding: 7px 14px;
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

        self.log_viewer = LogViewer("Backup & Restore Log", self)
        self.log_viewer.setMinimumHeight(130)
        layout.addWidget(self.log_viewer, 1)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        btn_close = QPushButton("Close Modal", self)
        btn_close.setObjectName("secondaryBtn")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def _browse_backup_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Save Backup", os.path.expanduser("~"))
        if folder:
            self.txt_backup_dir.setText(folder)

    def _browse_restore_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Backup Tarball", os.path.expanduser("~"), "Archive Files (*.tar.gz *.tgz)")
        if file_path:
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
