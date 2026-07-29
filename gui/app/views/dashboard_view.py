import os
from pathlib import Path

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QScrollArea
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
except ImportError:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QScrollArea
    from PySide6.QtCore import Qt, QTimer, QThread, Signal as pyqtSignal

from ..components.status_card import StatusCard
from ..components.log_viewer import LogViewer
from ..backend.system import check_gpu_info, check_opencl_info, check_glib_mismatches, get_disk_usage, get_bin_path
from ..backend.runner import ProcessRunnerThread

class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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

        # Header Title
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title_lbl = QLabel("System Dashboard & Diagnostics", scroll_content)
        title_lbl.setObjectName("viewTitle")

        sub_lbl = QLabel("DaVinci Resolve Linux system health, GPU status, library fixups, and quick launcher", scroll_content)
        sub_lbl.setObjectName("viewSub")

        header_box.addWidget(title_lbl)
        header_box.addWidget(sub_lbl)
        layout.addLayout(header_box)

        # Alert Banner
        self.alert_frame = QFrame(scroll_content)
        self.alert_frame.setObjectName("alertFrame")
        alert_layout = QHBoxLayout(self.alert_frame)
        alert_layout.setContentsMargins(14, 10, 14, 10)
        alert_layout.setSpacing(10)

        self.alert_icon = QLabel("⚠️", self.alert_frame)
        self.alert_icon.setStyleSheet("font-size: 18px;")

        self.alert_text = QLabel("Checking library compatibility...", self.alert_frame)
        self.alert_text.setStyleSheet("font-size: 12px; color: #ffb703; font-weight: 500;")
        self.alert_text.setWordWrap(True)

        self.btn_fix_launch = QPushButton("🛠️ Fix & Launch Resolve", self.alert_frame)
        self.btn_fix_launch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fix_launch.setStyleSheet("""
            QPushButton {
                background-color: #ffb703;
                color: #090a0c;
                font-weight: 600;
                font-size: 12px;
                border-radius: 5px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #ffc83b;
            }
        """)
        self.btn_fix_launch.clicked.connect(self._run_resolve_fix)

        alert_layout.addWidget(self.alert_icon)
        alert_layout.addWidget(self.alert_text, 1)
        alert_layout.addWidget(self.btn_fix_launch)
        self.alert_frame.hide()

        layout.addWidget(self.alert_frame)

        # Status Cards Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        self.card_gpu = StatusCard("🎮", "NVIDIA GPU", "Detecting...", "GPU Active", "ok")
        self.card_opencl = StatusCard("⚡", "OpenCL Acceleration", "Detecting...", "CUDA Ready", "ok")
        self.card_disk = StatusCard("💾", "Storage Space", "Calculating...", "Space OK", "ok")
        self.card_glib = StatusCard("📦", "Resolve Libraries", "Scanning...", "Status", "ok")

        grid.addWidget(self.card_gpu, 0, 0)
        grid.addWidget(self.card_opencl, 0, 1)
        grid.addWidget(self.card_disk, 1, 0)
        grid.addWidget(self.card_glib, 1, 1)

        layout.addLayout(grid)

        # Quick Launch Card
        actions_card = QFrame(scroll_content)
        actions_card.setObjectName("cardFrame")
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(16, 12, 16, 12)

        actions_title = QLabel("🚀 Quick Launch", actions_card)
        actions_title.setObjectName("sectionTitle")

        btn_run_info = QPushButton("📊 Run Full Diagnostic", actions_card)
        btn_run_info.setObjectName("secondaryBtn")
        btn_run_info.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run_info.clicked.connect(self._run_resolve_info)

        btn_launch_prime = QPushButton("🎬 Launch Resolve (PRIME)", actions_card)
        btn_launch_prime.setObjectName("primaryBtn")
        btn_launch_prime.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_launch_prime.clicked.connect(self._launch_prime)

        actions_layout.addWidget(actions_title)
        actions_layout.addStretch()
        actions_layout.addWidget(btn_run_info)
        actions_layout.addWidget(btn_launch_prime)

        layout.addWidget(actions_card)

        # Log Viewer
        self.log_viewer = LogViewer("Diagnostic Log Output", scroll_content)
        self.log_viewer.setMinimumHeight(160)
        layout.addWidget(self.log_viewer)

        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

        # Deferred async: run system checks AFTER window is shown so UI appears instantly.
        # The NVIDIA GPU may be in D3 sleep state on hybrid laptops — waking it takes
        # 500-1700ms. Running this synchronously blocks the UI thread and delays the
        # window appearance by 1-2 seconds. QTimer.singleShot(0) defers execution to
        # the next event loop iteration, after the window is already visible.
        QTimer.singleShot(0, self._async_refresh)

    def _async_refresh(self):
        """Runs system checks in a background thread to avoid blocking the UI."""
        self._diag_thread = _DiagnosticThread(self)
        self._diag_thread.results_ready.connect(self._apply_diagnostic_results)
        self._diag_thread.start()

    def _apply_diagnostic_results(self, results):
        """Receives results from the background thread and updates the UI."""
        gpu = results["gpu"]
        if gpu["available"]:
            self.card_gpu.set_value(f"{gpu['gpu_name']}\n{gpu['vram_used']} / {gpu['vram_total']} VRAM")
        else:
            self.card_gpu.set_value("No NVIDIA GPU detected")

        cl = results["opencl"]
        if cl["available"]:
            self.card_opencl.set_value(cl["platform"])
        else:
            self.card_opencl.set_value("No OpenCL Platform found")

        disk = results["disk"]
        self.card_disk.set_value(f"{disk['free_gb']} GB Free ({disk['percent_used']}% used of {disk['total_gb']} GB)")

        glib = results["glib"]
        resolve_fix_exists = os.path.exists(os.path.expanduser("~/.local/bin/resolve-fix")) or os.path.exists("/usr/bin/resolve-fix")

        if not glib["resolve_installed"]:
            self.card_glib.set_value("DaVinci Resolve not found at /opt/resolve")
            self.alert_text.setText("DaVinci Resolve installation was not found at /opt/resolve.")
            self.alert_frame.setStyleSheet("QFrame#alertFrame { background-color: rgba(255, 82, 82, 0.08); border: 1px solid rgba(255, 82, 82, 0.3); border-radius: 8px; }")
            self.alert_frame.show()
        elif glib["count"] > 0:
            if resolve_fix_exists:
                self.card_glib.set_value(f"🟡 GLib: Workaround Active")
                self.alert_text.setText(f"Found {glib['count']} library mismatch(es). Use resolve-fix if Resolve crashes.")
                self.alert_frame.setStyleSheet("QFrame#alertFrame { background-color: rgba(255, 183, 3, 0.08); border: 1px solid rgba(255, 183, 3, 0.3); border-radius: 8px; }")
                self.alert_frame.show()
            else:
                self.card_glib.set_value(f"🔴 GLib: Workaround Needed")
                self.alert_text.setText(f"Found {glib['count']} library mismatch(es). resolve-fix is needed to launch Resolve safely.")
                self.alert_frame.setStyleSheet("QFrame#alertFrame { background-color: rgba(255, 82, 82, 0.08); border: 1px solid rgba(255, 82, 82, 0.3); border-radius: 8px; }")
                self.alert_frame.show()
        else:
            self.card_glib.set_value("All libraries aligned & working")
            self.alert_frame.hide()

    def refresh_diagnostics(self):
        """Synchronous refresh — kept for manual diagnostic runs."""
        results = {
            "gpu": check_gpu_info(),
            "opencl": check_opencl_info(),
            "disk": get_disk_usage(),
            "glib": check_glib_mismatches(),
        }
        self._apply_diagnostic_results(results)


    def _launch_prime(self):
        self.log_viewer.append_log("[INFO] Launching DaVinci Resolve via PRIME offload...")
        bin_path = get_bin_path("resolve-fix")
        self.runner = ProcessRunnerThread([bin_path])
        self.runner.output_line.connect(self.log_viewer.append_log)
        self.runner.start()

    def _run_resolve_fix(self):
        self.log_viewer.append_log("[INFO] Running resolve-fix launcher script...")
        bin_path = get_bin_path("resolve-fix")
        self.runner = ProcessRunnerThread([bin_path])
        self.runner.output_line.connect(self.log_viewer.append_log)
        self.runner.start()

    def _run_resolve_info(self):
        self.log_viewer.clear_log()
        self.log_viewer.append_log("[INFO] Running system diagnostic (resolve-info)...")
        bin_path = get_bin_path("resolve-info")
        self.runner = ProcessRunnerThread([bin_path])
        self.runner.output_line.connect(self.log_viewer.append_log)
        self.runner.finished_signal.connect(lambda code, out: self.refresh_diagnostics())
        self.runner.start()


class _DiagnosticThread(QThread):
    """Runs system diagnostic checks in a background thread to avoid blocking the UI."""
    results_ready = pyqtSignal(dict)

    def run(self):
        results = {
            "gpu": check_gpu_info(),
            "opencl": check_opencl_info(),
            "disk": get_disk_usage(),
            "glib": check_glib_mismatches(),
        }
        self.results_ready.emit(results)
