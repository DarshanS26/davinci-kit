import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
        QApplication
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
except ImportError:
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
        QApplication
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QKeySequence, QShortcut

from .components.top_bar import TopBar
from .components.tab_bar import TabBar
from .components.status_bar import StatusBar
from .components.log_panel import LogPanel

from .views.transcode_view import TranscodeView
from .views.export_view import ExportView
from .views.audio_view import AudioView
from .views.inspector_view import InspectorView

from .dialogs import WatchDialog, FontDialog, BackupDialog, DiagDialog
from .backend.system import get_bin_path
from .backend.runner import ProcessRunnerThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DaVinci Resolve Kit")
        self.resize(1140, 700)
        self.setMinimumSize(900, 580)

        our_icon = _PROJECT_ROOT / "gui" / "resources" / "resolve-kit.svg"
        icon_path = str(our_icon) if our_icon.exists() else "/opt/resolve/graphics/DV_Resolve.png"
        self.setWindowIcon(QIcon(icon_path))

        self.center_on_screen()

        self.runner = None
        self.active_meta = []

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Bar (40px)
        self.top_bar = TopBar(self)
        self.top_bar.open_diag_requested.connect(self.open_diag_dialog)

        # 2. Tab Bar (36px)
        self.tab_bar = TabBar(self)
        self.tab_bar.tab_changed.connect(self.switch_tab)
        self.tab_bar.open_watch_requested.connect(self.open_watch_dialog)
        self.tab_bar.open_fonts_requested.connect(self.open_font_dialog)
        self.tab_bar.open_backup_requested.connect(self.open_backup_dialog)
        self.tab_bar.open_diag_requested.connect(self.open_diag_dialog)
        self.tab_bar.run_fix_requested.connect(self.run_fix_resolve)

        # 3. Central Stacked Studio Views
        self.stacked_widget = QStackedWidget(self)

        self.view_transcode = TranscodeView(self)
        self.view_export = ExportView(self)
        self.view_audio = AudioView(self)
        self.view_inspector = InspectorView(self)

        # Wire view start signals
        self.view_transcode.start_transcode_requested.connect(self.start_process)
        self.view_export.start_export_requested.connect(self.start_process)
        self.view_audio.start_audio_requested.connect(self.start_process)

        self.view_transcode.cancel_requested.connect(self.cancel_process)
        self.view_export.cancel_requested.connect(self.cancel_process)
        self.view_audio.cancel_requested.connect(self.cancel_process)

        self.view_transcode.file_queue.queue_changed.connect(self._on_queue_updated)
        self.view_export.file_queue.queue_changed.connect(self._on_queue_updated)
        self.view_audio.file_queue.queue_changed.connect(self._on_queue_updated)
        self.view_inspector.file_queue.queue_changed.connect(self._update_status_bar_summary)

        self.stacked_widget.addWidget(self.view_transcode)
        self.stacked_widget.addWidget(self.view_export)
        self.stacked_widget.addWidget(self.view_audio)
        self.stacked_widget.addWidget(self.view_inspector)

        # 4. Collapsible Log Panel
        self.log_panel = LogPanel(self)
        self.log_panel.hide()

        # 5. Persistent Status Bar (32px)
        self.status_bar = StatusBar(self)
        self.status_bar.cancel_requested.connect(self.cancel_process)
        self.status_bar.toggle_logs_requested.connect(self.toggle_logs)

        root_layout.addWidget(self.top_bar)
        root_layout.addWidget(self.tab_bar)
        root_layout.addWidget(self.stacked_widget, 1)
        root_layout.addWidget(self.log_panel)
        root_layout.addWidget(self.status_bar)

        # Setup Keyboard Shortcuts
        self._setup_shortcuts()

        self.switch_tab(0)

    def switch_tab(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        self.tab_bar.set_current_index(index, block_signal=True)
        # Update status bar summary from active view queue
        self._update_status_bar_summary()

    def _on_queue_updated(self):
        # Automatically sync files added in Transcode, Export, or Audio tabs to Inspector
        paths_to_sync = []
        for view in [self.view_transcode, self.view_export, self.view_audio]:
            meta = view.file_queue.get_selected_metadata()
            for m in meta:
                paths_to_sync.append(m["path"])
        if paths_to_sync:
            self.view_inspector.file_queue.add_paths(paths_to_sync)

        self._update_status_bar_summary()

    def _update_status_bar_summary(self):
        current_view = self.stacked_widget.currentWidget()
        if hasattr(current_view, "file_queue"):
            meta = current_view.file_queue.get_selected_metadata()
            if meta:
                self.status_bar.set_idle(f"{len(meta)} file(s) queued")
            else:
                self.status_bar.set_idle("No files queued")

    def start_process(self, cmd: list, selected_meta: list):
        if not cmd or not selected_meta:
            return

        self.active_meta = selected_meta
        current_view = self.stacked_widget.currentWidget()
        output_dir = getattr(current_view, "last_output_dir", "")

        self.log_panel.clear_logs()
        self.log_panel.append_log(f"[INFO] Command: {' '.join(cmd)}")

        first_fn = selected_meta[0].get("filename", "")
        self.status_bar.set_running(f"Processing {len(selected_meta)} item(s)...", first_fn)

        # Enable cancel buttons
        if hasattr(current_view, "btn_start"): current_view.btn_start.setEnabled(False)
        if hasattr(current_view, "btn_cancel"): current_view.btn_cancel.setEnabled(True)

        self.runner = ProcessRunnerThread(cmd)
        self.runner.output_line.connect(self.log_panel.append_log)
        self.runner.progress_changed.connect(self.status_bar.set_progress)
        self.runner.finished_signal.connect(lambda rc, out: self._on_process_finished(rc, out, output_dir))
        self.runner.start()

    def cancel_process(self):
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.status_bar.set_error("Task cancelled by user.")
            self.log_panel.append_log("[WARN] Task cancelled.")
        self._reset_action_buttons()

    def _on_process_finished(self, return_code: int, output: str, output_dir: str):
        self._reset_action_buttons()
        if return_code == 0:
            count = len(self.active_meta) if self.active_meta else 1
            self.status_bar.set_success(f"{count} item(s) processed successfully!", output_dir)
            self.log_panel.append_log("[OK] Process completed successfully.")
        else:
            self.status_bar.set_error("Process encountered errors. Click 'Logs ▾' for details.")
            self.log_panel.append_log(f"[ERR] Process failed with exit code {return_code}.")
            self.log_panel.show()

    def _reset_action_buttons(self):
        for view in [self.view_transcode, self.view_export, self.view_audio]:
            if hasattr(view, "btn_start"): view.btn_start.setEnabled(True)
            if hasattr(view, "btn_cancel"): view.btn_cancel.setEnabled(False)

    def toggle_logs(self):
        if self.log_panel.isVisible():
            self.log_panel.hide()
        else:
            self.log_panel.show()

    # Modal Dialog Callbacks
    def open_diag_dialog(self):
        dlg = DiagDialog(self)
        dlg.exec()

    def open_watch_dialog(self):
        dlg = WatchDialog(self)
        dlg.exec()

    def open_font_dialog(self):
        dlg = FontDialog(self)
        dlg.exec()

    def open_backup_dialog(self):
        dlg = BackupDialog(self)
        dlg.exec()

    def run_fix_resolve(self):
        self.log_panel.clear_logs()
        self.log_panel.append_log("[INFO] Executing resolve-fix...")
        self.log_panel.show()
        bin_path = get_bin_path("resolve-fix")
        self.runner = ProcessRunnerThread([bin_path])
        self.runner.output_line.connect(self.log_panel.append_log)
        self.runner.start()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.switch_tab(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.switch_tab(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.switch_tab(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.switch_tab(3))
        QShortcut(QKeySequence("Ctrl+D"), self, self.open_diag_dialog)

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            win_size = self.geometry()
            x = geo.x() + (geo.width() - win_size.width()) // 2
            y = geo.y() + (geo.height() - win_size.height()) // 2
            self.move(x, y)
