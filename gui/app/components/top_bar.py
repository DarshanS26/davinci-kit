import os
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QHBoxLayout, QLabel, QPushButton, QMenu, QToolTip
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
    from PyQt6.QtGui import QAction, QCursor
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QHBoxLayout, QLabel, QPushButton, QMenu, QToolTip
    )
    from PySide6.QtCore import Qt, Signal as pyqtSignal, QTimer, QThread
    from PySide6.QtGui import QAction, QCursor

from ..backend.system import check_gpu_info, get_disk_usage, check_glib_mismatches

class TopBar(QWidget):
    open_diag_requested = pyqtSignal()
    open_watch_requested = pyqtSignal()
    open_fonts_requested = pyqtSignal()
    open_backup_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setObjectName("topBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Left: Brand logo + title
        brand_box = QHBoxLayout()
        brand_box.setSpacing(8)

        self.lbl_logo = QLabel("🎬", self)
        self.lbl_logo.setStyleSheet("font-size: 18px;")

        self.lbl_title = QLabel("DaVinci Resolve Kit", self)
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;")

        self.lbl_subtitle = QLabel("Linux Studio", self)
        self.lbl_subtitle.setStyleSheet("font-size: 11px; color: #6c7086; font-weight: 400; margin-left: 2px;")

        brand_box.addWidget(self.lbl_logo)
        brand_box.addWidget(self.lbl_title)
        brand_box.addWidget(self.lbl_subtitle)
        layout.addLayout(brand_box)

        # Center: Health Indicators
        self.health_box = QHBoxLayout()
        self.health_box.setSpacing(12)

        self.lbl_gpu = QLabel("GPU: Checking...", self)
        self.lbl_gpu.setStyleSheet("font-size: 12px; color: #a9acbe; padding: 2px 8px; background: #14161f; border-radius: 4px;")

        self.lbl_disk = QLabel("Disk: Checking...", self)
        self.lbl_disk.setStyleSheet("font-size: 12px; color: #a9acbe; padding: 2px 8px; background: #14161f; border-radius: 4px;")

        self.lbl_glib = QLabel("GLib: Checking...", self)
        self.lbl_glib.setStyleSheet("font-size: 12px; color: #a9acbe; padding: 2px 8px; background: #14161f; border-radius: 4px;")

        self.health_box.addWidget(self.lbl_gpu)
        self.health_box.addWidget(self.lbl_disk)
        self.health_box.addWidget(self.lbl_glib)
        layout.addLayout(self.health_box)

        layout.addStretch()

        # Right: Actions
        self.btn_diag = QPushButton("🔍 Diagnostic", self)
        self.btn_diag.setObjectName("secondaryBtn")
        self.btn_diag.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        self.btn_diag.setToolTip("Run system diagnostic (Ctrl+D)")
        self.btn_diag.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_diag.clicked.connect(self.open_diag_requested.emit)
        layout.addWidget(self.btn_diag)

        # Deferred async: run system checks after window appears.
        # nvidia-smi can take 500-1700ms when GPU is in D3 sleep on hybrid laptops.
        QTimer.singleShot(0, self._async_refresh)

    def _async_refresh(self):
        """Runs health checks in a background thread."""
        self._health_thread = _HealthCheckThread(self)
        self._health_thread.results_ready.connect(self._apply_health)
        self._health_thread.start()

    def refresh_health(self):
        """Synchronous refresh — for manual refresh after diagnostics."""
        results = {
            "gpu": check_gpu_info(),
            "disk": get_disk_usage(),
            "glib": check_glib_mismatches(),
        }
        self._apply_health(results)

    def _apply_health(self, results):
        """Receives results from background thread and updates labels."""
        # GPU Info
        gpu = results["gpu"]
        if gpu["available"]:
            self.lbl_gpu.setText(f"🟢 GPU: {gpu['model']}")
            self.lbl_gpu.setToolTip(f"Vendor: {gpu['vendor']}\nDriver: {gpu['driver']}\nVRAM: {gpu['vram_used']}/{gpu['vram_total']}")
        else:
            self.lbl_gpu.setText("⚪ GPU: Not detected")
            self.lbl_gpu.setToolTip("No GPU detected")

        # Disk Info
        disk = results["disk"]
        if disk["free_gb"] > 20:
            self.lbl_disk.setText(f"🟢 Disk: {disk['free_gb']} GB free")
        elif disk["free_gb"] > 5:
            self.lbl_disk.setText(f"🟡 Disk: {disk['free_gb']} GB free")
        else:
            self.lbl_disk.setText(f"🔴 Disk: {disk['free_gb']} GB free")
        self.lbl_disk.setToolTip(f"Path: {disk['path']}\nTotal: {disk['total_gb']} GB\nUsed: {disk['used_gb']} GB ({disk['percent_used']}%)")

        # GLib Info
        glib = results["glib"]
        resolve_fix_exists = os.path.exists(os.path.expanduser("~/.local/bin/resolve-fix")) or os.path.exists("/usr/bin/resolve-fix")

        if not glib.get("resolve_installed", True):
            self.lbl_glib.setText("🔴 Resolve: Missing")
            self.lbl_glib.setToolTip("DaVinci Resolve is not found at /opt/resolve")
        elif glib["count"] == 0:
            self.lbl_glib.setText("🟢 GLib: OK")
            self.lbl_glib.setToolTip("No GLib library mismatches found with DaVinci Resolve")
        else:
            if resolve_fix_exists:
                self.lbl_glib.setText(f"🟡 GLib: Workaround Active")
                self.lbl_glib.setToolTip(
                    f"Found {glib['count']} library mismatch(es).\n"
                    "Common on rolling-release distros. Use resolve-fix if Resolve crashes."
                )
            else:
                self.lbl_glib.setText(f"🔴 GLib: Workaround Needed")
                self.lbl_glib.setToolTip(
                    f"Found {glib['count']} library mismatch(es).\n"
                    "resolve-fix is not installed. Use resolve-fix if Resolve crashes."
                )


class _HealthCheckThread(QThread):
    """Runs health checks in background to avoid blocking UI on GPU wake."""
    results_ready = pyqtSignal(dict)

    def run(self):
        results = {
            "gpu": check_gpu_info(),
            "disk": get_disk_usage(),
            "glib": check_glib_mismatches(),
        }
        self.results_ready.emit(results)
