import os
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QListWidget, QListWidgetItem, QCheckBox, QFrame, QMenu,
        QAbstractItemView, QSizePolicy, QApplication
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QSize, QUrl, QThread
    from PyQt6.QtGui import QAction, QCursor, QDesktopServices, QFontMetrics
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QListWidget, QListWidgetItem, QCheckBox, QFrame, QMenu,
        QAbstractItemView, QSizePolicy, QApplication
    )
    from PySide6.QtCore import Qt, Signal as pyqtSignal, QSize, QUrl, QThread
    from PySide6.QtGui import QAction, QCursor, QDesktopServices, QFontMetrics

from ..backend.inspector import get_file_info, format_size
from ..components.drop_zone import DropZone

class ProbeWorker(QThread):
    file_ready = pyqtSignal(dict)
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal()

    def __init__(self, file_list: list, parent=None):
        super().__init__(parent)
        self.file_list = file_list

    def run(self):
        total = len(self.file_list)
        for i, path in enumerate(self.file_list):
            self.progress.emit(i + 1, total)
            try:
                meta = get_file_info(path)
                if meta and meta.get("valid"):
                    self.file_ready.emit(meta)
            except Exception:
                pass
        self.finished.emit()

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._raw_text = text

    def setText(self, text):
        self._raw_text = text
        super().setText(text)

    def paintEvent(self, event):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._raw_text, Qt.TextElideMode.ElideMiddle, max(10, self.width()))
        super().setText(elided)
        super().paintEvent(event)

class FileQueueItemWidget(QWidget):
    toggled = pyqtSignal(str, bool)

    def __init__(self, meta: dict, parent=None):
        super().__init__(parent)
        self.meta = meta

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        # Checkbox
        self.chk = QCheckBox(self)
        self.chk.setChecked(True)
        self.chk.setFixedSize(18, 18)
        self.chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk.toggled.connect(self._on_toggled)

        # Filename & Details
        info_box = QVBoxLayout()
        info_box.setSpacing(1)

        fname = meta.get("filename", "Unknown")
        lbl_name = ElidedLabel(fname, self)
        lbl_name.setToolTip(fname)
        lbl_name.setStyleSheet("font-weight: 600; color: #f0f2fb; font-size: 12px;")

        # Order: Length • Resolution • Video Codec • Audio Format • Size
        parts = []

        dur_str = meta.get("duration_str", "00:00")
        parts.append(dur_str)

        res_str = meta.get("resolution_str")
        if res_str and res_str != "N/A":
            parts.append(res_str)

        vcodec = meta.get("vcodec")
        if vcodec and vcodec != "none":
            parts.append(vcodec.upper())

        acodec = meta.get("acodec")
        if acodec and acodec != "none":
            parts.append(f"{acodec.upper()} audio")

        size_str = meta.get("filesize_str", "0 MB")
        parts.append(size_str)

        sub_details = "  •  ".join(parts)
        lbl_sub = ElidedLabel(sub_details, self)
        lbl_sub.setToolTip(sub_details)
        lbl_sub.setStyleSheet("font-size: 11px; color: #8c90a4; font-weight: 400;")

        info_box.addWidget(lbl_name)
        info_box.addWidget(lbl_sub)

        layout.addWidget(self.chk)
        layout.addLayout(info_box, 1)

    def _on_toggled(self, checked):
        self.toggled.emit(self.meta.get("path", ""), checked)

class FileQueue(QFrame):
    queue_changed = pyqtSignal()

    def __init__(self, title: str = "Media File Queue", drop_title: str = "Drag & drop files or folder trees", drop_subtitle: str = "Supports video & audio files", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")

        self.selected_files_meta = []
        self.enabled_paths = set()
        self._active_workers = []
        self._accepting_files = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # DropZone Header
        self.drop_zone = DropZone(drop_title, drop_subtitle, parent=self)
        self.drop_zone.paths_dropped.connect(self.add_paths)
        layout.addWidget(self.drop_zone)

        # List Header Row
        hdr_layout = QHBoxLayout()
        lbl_list_title = QLabel(f"📋 {title}", self)
        lbl_list_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #c2c5d6;")
        hdr_layout.addWidget(lbl_list_title)
        hdr_layout.addStretch()

        btn_remove = QPushButton("Remove Selected", self)
        btn_remove.setObjectName("secondaryBtn")
        btn_remove.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        btn_remove.clicked.connect(self.remove_selected)

        btn_clear = QPushButton("Clear All", self)
        btn_clear.setObjectName("secondaryBtn")
        btn_clear.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        btn_clear.clicked.connect(self.clear_all)

        hdr_layout.addWidget(btn_remove)
        hdr_layout.addWidget(btn_clear)
        layout.addLayout(hdr_layout)

        # File ListWidget
        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, 1)

        # Summary Footer
        self.lbl_summary = QLabel("0 files queued", self)
        self.lbl_summary.setStyleSheet("font-size: 11px; color: #8c90a4; font-weight: 500;")
        layout.addWidget(self.lbl_summary)

    def _set_path_enabled(self, path: str, enabled: bool):
        if enabled:
            self.enabled_paths.add(path)
        else:
            self.enabled_paths.discard(path)
        self._update_summary()
        self.queue_changed.emit()

    def add_paths(self, paths: list):
        self._accepting_files = True
        file_list = []
        for p in paths:
            if os.path.isfile(p):
                file_list.append(p)
            elif os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for f in sorted(files):
                        file_list.append(os.path.join(root, f))

        existing_paths = {m["path"] for m in self.selected_files_meta}
        files_to_probe = [f for f in file_list if f not in existing_paths]
        if not files_to_probe:
            return

        worker = ProbeWorker(files_to_probe, self)
        worker.file_ready.connect(self._on_file_probed)
        worker.progress.connect(self._on_probe_progress)
        worker.finished.connect(lambda: self._on_probe_finished(worker))
        self._active_workers.append(worker)
        worker.start()

    def _on_file_probed(self, meta):
        if not self._accepting_files:
            return
        if any(m["path"] == meta["path"] for m in self.selected_files_meta):
            return
        self.selected_files_meta.append(meta)
        self.enabled_paths.add(meta["path"])
        item = QListWidgetItem(self.list_widget)
        item_widget = FileQueueItemWidget(meta, self.list_widget)
        item_widget.toggled.connect(self._set_path_enabled)
        self.list_widget.setItemWidget(item, item_widget)
        item.setSizeHint(item_widget.sizeHint())
        self.queue_changed.emit()

    def _on_probe_progress(self, current, total):
        self.lbl_summary.setText(f"🔍 Scanning {current}/{total} files…")

    def _on_probe_finished(self, worker):
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        self._update_summary()

    def remove_row(self, row: int):
        if not (0 <= row < self.list_widget.count()):
            return
        item = self.list_widget.takeItem(row)
        if row < len(self.selected_files_meta):
            path = self.selected_files_meta[row]["path"]
            self.enabled_paths.discard(path)
            self.selected_files_meta.pop(row)
        self._update_summary()
        self.queue_changed.emit()

    def remove_selected(self):
        selected_rows = [self.list_widget.row(item) for item in self.list_widget.selectedItems()]
        for row in sorted(selected_rows, reverse=True):
            self.remove_row(row)

    def clear_all(self):
        # Stop any active probe workers
        self._accepting_files = False
        for worker in self._active_workers:
            worker.quit()
            worker.wait(1000)  # wait up to 1 second
        self._active_workers.clear()
        self.selected_files_meta.clear()
        self.enabled_paths.clear()
        self.list_widget.clear()
        self._update_summary()
        self.queue_changed.emit()

    def _update_summary(self):
        if not self.selected_files_meta:
            self.lbl_summary.setText("0 files queued")
            return
        total_count = len(self.selected_files_meta)
        selected_count = sum(1 for m in self.selected_files_meta if m["path"] in self.enabled_paths)
        selected_bytes = sum(m["filesize_bytes"] for m in self.selected_files_meta if m["path"] in self.enabled_paths)
        selected_sec = sum(m["duration_sec"] for m in self.selected_files_meta if m["path"] in self.enabled_paths)

        hrs = int(selected_sec // 3600)
        mins = int((selected_sec % 3600) // 60)
        secs = int(selected_sec % 60)
        dur_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

        self.lbl_summary.setText(
            f"📁 {selected_count} selected / {total_count} queued  •  "
            f"{format_size(selected_bytes)} selected  •  {dur_str} selected"
        )

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        row = self.list_widget.row(item)
        if row >= len(self.selected_files_meta):
            return
        meta = self.selected_files_meta[row]

        menu = QMenu(self)
        act_remove = QAction("Remove Item", self)
        act_remove.triggered.connect(lambda checked=False, r=row: self.remove_row(r))

        act_folder = QAction("Show in File Manager", self)
        act_folder.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(meta["path"]))))

        act_copy = QAction("Copy Full Path", self)
        act_copy.triggered.connect(lambda: QApplication.clipboard().setText(meta["path"]))

        menu.addAction(act_remove)
        menu.addAction(act_folder)
        menu.addAction(act_copy)
        menu.exec(QCursor.pos())

    def get_selected_metadata(self) -> list:
        return [m for m in self.selected_files_meta if m["path"] in self.enabled_paths]

    def get_all_metadata(self) -> list:
        return list(self.selected_files_meta)
