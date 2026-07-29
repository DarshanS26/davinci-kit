import os
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QComboBox, QSpinBox, QCheckBox, QLineEdit, QFileDialog,
        QFrame, QSplitter
    )
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QComboBox, QSpinBox, QCheckBox, QLineEdit, QFileDialog,
        QFrame, QSplitter
    )
    from PySide6.QtCore import Qt, Signal as pyqtSignal

from ..components.file_queue import FileQueue
from ..components.preset_pills import PresetPills
from ..backend.system import get_bin_path
from ..backend.runner import ProcessRunnerThread
from ..backend.inspector import calculate_estimated_output, format_size

class TranscodeView(QWidget):
    start_transcode_requested = pyqtSignal(list, list) # (cmd, selected_meta)
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.runner = None
        self.last_output_dir = ""

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Splitter for 60/40 ratio
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(14)

        # Left Column: File Queue
        self.file_queue = FileQueue(
            title="Batch Transcode Queue",
            drop_title="Drag & drop media files or folder trees",
            drop_subtitle="Supports mp4, mkv, mov, avi, mxf and folder trees",
            parent=splitter
        )
        self.file_queue.queue_changed.connect(self._update_estimates)

        # Right Column: Transcode Settings
        right_box = QFrame(splitter)
        right_box.setObjectName("cardFrame")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        opt_title = QLabel("⚙️ Transcode Settings", right_box)
        opt_title.setObjectName("sectionTitle")
        right_layout.addWidget(opt_title)

        # Video Codec
        c_layout = QHBoxLayout()
        c_label = QLabel("Video Codec:", right_box)
        c_label.setFixedWidth(110)
        self.combo_codec = QComboBox(right_box)
        self.combo_codec.addItem("AV1 (.mkv) [Default]", "av1")
        self.combo_codec.addItem("DNxHR (.mov)", "dnxhr")
        self.combo_codec.currentIndexChanged.connect(self._update_estimates)
        c_layout.addWidget(c_label)
        c_layout.addWidget(self.combo_codec, 1)
        right_layout.addLayout(c_layout)

        # Quality Profile Pills
        q_title = QLabel("Quality Profile:", right_box)
        q_title.setStyleSheet("font-weight: 500; color: #a9acbe;")
        right_layout.addWidget(q_title)

        pills_presets = [
            ("lb", "⚡ Proxy (LB)", "Low Bitrate ~100 Mbps (DNxHR LB / AV1 CRF 35)"),
            ("sq", "📹 Standard (SQ)", "Standard ~220 Mbps (DNxHR SQ / AV1 CRF 30)"),
            ("hq", "🎬 High Quality (HQ)", "High Quality ~440 Mbps (DNxHR HQ / AV1 CRF 26) [DEFAULT]"),
            ("hqx", "💎 12-bit (HQX)", "12-bit Quality ~660 Mbps (DNxHR HQX / AV1 CRF 22)"),
            ("444", "👑 Master (444)", "Full 4:4:4 ~880 Mbps (DNxHR 444 / AV1 CRF 20)")
        ]
        self.preset_pills = PresetPills(pills_presets, default_key="hq", max_columns=3, parent=right_box)
        self.preset_pills.preset_selected.connect(self._update_estimates)
        right_layout.addWidget(self.preset_pills)

        # Audio Mode
        a_layout = QHBoxLayout()
        a_label = QLabel("Audio Codec:", right_box)
        a_label.setFixedWidth(110)
        self.combo_audio = QComboBox(right_box)
        self.combo_audio.addItem("PCM 24-bit WAV [Default]", "pcm")
        self.combo_audio.addItem("Auto", "auto")
        self.combo_audio.addItem("FLAC", "flac")
        self.combo_audio.addItem("ALAC", "alac")
        a_layout.addWidget(a_label)
        a_layout.addWidget(self.combo_audio, 1)
        right_layout.addLayout(a_layout)

        # Parallel Jobs
        j_layout = QHBoxLayout()
        j_label = QLabel("Parallel Jobs:", right_box)
        j_label.setFixedWidth(110)
        self.spin_jobs = QSpinBox(right_box)
        cpu_count = max(1, (os.cpu_count() or 4) // 2)
        self.spin_jobs.setRange(1, os.cpu_count() or 16)
        self.spin_jobs.setValue(cpu_count)
        j_layout.addWidget(j_label)
        j_layout.addWidget(self.spin_jobs, 1)
        right_layout.addLayout(j_layout)

        # Output Folder
        out_layout = QHBoxLayout()
        out_label = QLabel("Output Folder:", right_box)
        out_label.setFixedWidth(110)
        self.txt_out_dir = QLineEdit(right_box)
        self.txt_out_dir.setPlaceholderText("Default: <INPUT_DIR>/resolve_ready")
        btn_out_browse = QPushButton("Browse...", right_box)
        btn_out_browse.setObjectName("secondaryBtn")
        btn_out_browse.clicked.connect(self._browse_output)
        out_layout.addWidget(out_label)
        out_layout.addWidget(self.txt_out_dir, 1)
        out_layout.addWidget(btn_out_browse)
        right_layout.addLayout(out_layout)

        self.chk_dry_run = QCheckBox("Dry-run preview (show command without converting)", right_box)
        right_layout.addWidget(self.chk_dry_run)

        # Estimate Banner
        self.est_banner = QFrame(right_box)
        self.est_banner.setStyleSheet("background-color: rgba(0, 229, 255, 0.06); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 6px; padding: 8px;")
        est_box = QHBoxLayout(self.est_banner)
        est_box.setContentsMargins(10, 6, 10, 6)
        self.lbl_est_size = QLabel("📊 Total Input: 0 MB  ➔  Est. Output: ~0 MB", self.est_banner)
        self.lbl_est_size.setStyleSheet("font-size: 12px; font-weight: 500; color: #00e5ff;")
        est_box.addWidget(self.lbl_est_size)
        right_layout.addWidget(self.est_banner)

        right_layout.addStretch()

        # Action Buttons
        act_layout = QHBoxLayout()
        act_layout.setSpacing(10)
        self.btn_start = QPushButton("🚀 Start Transcode", right_box)
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_transcode)

        self.btn_cancel = QPushButton("🛑 Cancel", right_box)
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)

        act_layout.addWidget(self.btn_start, 1)
        act_layout.addWidget(self.btn_cancel)
        right_layout.addLayout(act_layout)

        splitter.addWidget(self.file_queue)
        splitter.addWidget(right_box)
        splitter.setSizes([600, 400])

        main_layout.addWidget(splitter)

    def _browse_output(self):
        from ..components.drop_zone import DropZone
        default_dir = DropZone.get_default_dir()
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", default_dir)
        if folder:
            DropZone.save_last_dir(folder)
            self.txt_out_dir.setText(folder)

    def _update_estimates(self):
        meta_list = self.file_queue.get_selected_metadata()
        if not meta_list:
            self.lbl_est_size.setText("📊 Total Input: 0 MB  ➔  Est. Output: ~0 MB")
            return

        total_input_bytes = sum(m["filesize_bytes"] for m in meta_list)
        total_duration = sum(m["duration_sec"] for m in meta_list)

        codec_val = self.combo_codec.currentData() or "dnxhr"
        q_val = self.preset_pills.selected_key or "sq"

        # Calculate average source bitrate for source-relative AV1 estimates
        total_source_bitrate = sum(m.get("bitrate_mbps", 0) for m in meta_list)
        avg_source_bitrate = total_source_bitrate / len(meta_list) if meta_list else 0

        est = calculate_estimated_output(total_duration, "video", q_val, codec=codec_val, source_bitrate_mbps=avg_source_bitrate)

        self.lbl_est_size.setText(f"📊 Input: {format_size(total_input_bytes)}  ➔  Est. Output: {est['est_str']} ({est['bitrate_mbps']} Mbps)")

    def _start_transcode(self):
        meta_list = self.file_queue.get_selected_metadata()
        if not meta_list:
            return

        codec_val = self.combo_codec.currentData() or "dnxhr"
        q_val = self.preset_pills.selected_key or "sq"
        a_val = self.combo_audio.currentData() or "auto"
        jobs = str(self.spin_jobs.value())

        cmd = [get_bin_path("davinci-kit-transcode"), "-c", codec_val, "-q", q_val, "-a", a_val, "-j", jobs]

        out_dir = self.txt_out_dir.text().strip()
        if out_dir:
            cmd.extend(["-o", out_dir])
            self.last_output_dir = out_dir
        else:
            first_path = meta_list[0]["path"]
            parent_dir = os.path.dirname(first_path) if os.path.isfile(first_path) else first_path
            self.last_output_dir = os.path.join(parent_dir, "resolve_ready")

        if self.chk_dry_run.isChecked():
            cmd.append("-n")

        for meta in meta_list:
            cmd.append(meta["path"])

        self.start_transcode_requested.emit(cmd, meta_list)
