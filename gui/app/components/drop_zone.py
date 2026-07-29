import os
from pathlib import Path

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog, QPushButton, QHBoxLayout, QSizePolicy
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QDragEnterEvent, QDropEvent
except ImportError:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog, QPushButton, QHBoxLayout, QSizePolicy
    from PySide6.QtCore import Qt, Signal as pyqtSignal
    from PySide6.QtGui import QDragEnterEvent, QDropEvent

class DropZone(QWidget):
    paths_dropped = pyqtSignal(list)

    def __init__(self, title="Drag & drop media files or folders here", subtitle="Supports .mp4, .mkv, .mov, .avi, .mxf and directory trees", parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setObjectName("dropZone")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel("🎬", self)
        self.icon_label.setStyleSheet("font-size: 24px;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title, self)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #e2e4ed;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sub_label = QLabel(subtitle, self)
        self.sub_label.setWordWrap(True)
        self.sub_label.setStyleSheet("font-size: 11px; font-weight: 400; color: #7e8299;")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_files = QPushButton("📁 Browse Files", self)
        self.btn_files.setObjectName("secondaryBtn")
        self.btn_files.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_files.setStyleSheet("padding: 7px 16px; min-height: 28px;")
        self.btn_files.clicked.connect(self._browse_files)

        self.btn_folder = QPushButton("📂 Browse Folder", self)
        self.btn_folder.setObjectName("secondaryBtn")
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_folder.setStyleSheet("padding: 7px 16px; min-height: 28px;")
        self.btn_folder.clicked.connect(self._browse_folder)

        btn_layout.addWidget(self.btn_files)
        btn_layout.addWidget(self.btn_folder)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.sub_label)
        layout.addLayout(btn_layout)

        self.update_style(False)

    def update_style(self, dragging: bool):
        if dragging:
            self.setStyleSheet("""
                #dropZone {
                    border: 1.5px dashed #00e5ff;
                    border-radius: 8px;
                    background-color: rgba(0, 229, 255, 0.05);
                }
            """)
        else:
            self.setStyleSheet("""
                #dropZone {
                    border: 1.5px dashed #262936;
                    border-radius: 8px;
                    background-color: #0b0c0f;
                }
                #dropZone:hover {
                    border-color: #383c4e;
                    background-color: #0f1014;
                }
            """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.update_style(True)

    def dragLeaveEvent(self, event):
        self.update_style(False)

    def dropEvent(self, event: QDropEvent):
        self.update_style(False)
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.toLocalFile()]
        if paths:
            self.paths_dropped.emit(paths)

    def _get_default_dir(self) -> str:
        downloads = os.path.expanduser("~/Downloads")
        return downloads if os.path.exists(downloads) else os.path.expanduser("~")

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Media Files", self._get_default_dir(),
            "Media Files (*.mp4 *.mkv *.mov *.avi *.mxf *.webm *.flv *.ts *.m2ts *.mts *.wav *.mp3 *.flac *.aac)"
        )
        if files:
            self.paths_dropped.emit(files)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self._get_default_dir())
        if folder:
            self.paths_dropped.emit([folder])
