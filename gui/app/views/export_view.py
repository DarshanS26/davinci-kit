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
from ..backend.system import get_bin_path
from ..backend.runner import ProcessRunnerThread
from ..backend.inspector import calculate_estimated_output, format_size

class ExportView(QWidget):
    start_export_requested = pyqtSignal(list, list) # (cmd, selected_meta)
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
            title="Export Delivery Queue",
            drop_title="Drag & drop rendered master files",
            drop_subtitle="Select rendered .mov, .mxf, or .mp4 files from Resolve",
            parent=splitter
        )
        self.file_queue.queue_changed.connect(self._update_estimates)

        # Right Column: Export Settings
        right_box = QFrame(splitter)
        right_box.setObjectName("cardFrame")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        opt_title = QLabel("🌐 Export & Delivery Settings", right_box)
        opt_title.setObjectName("sectionTitle")
        right_layout.addWidget(opt_title)

        # Resolution Scaling Combo
        res_layout = QHBoxLayout()
        res_label = QLabel("Resolution:", right_box)
        res_label.setFixedWidth(110)
        self.combo_res = QComboBox(right_box)
        self.combo_res.addItem("Original (No Scaling) [Default]", "original")
        self.combo_res.addItem("1080p — 1920x1080 (Full HD)", "1080p")
        self.combo_res.addItem("4K — 3840x2160 (Ultra HD)", "4k")
        self.combo_res.addItem("1440p — 2560x1440 (QHD)", "1440p")
        self.combo_res.addItem("720p — 1280x720 (HD)", "720p")
        self.combo_res.addItem("480p — 854x480 (SD)", "480p")
        self.combo_res.currentIndexChanged.connect(self._update_estimates)
        res_layout.addWidget(res_label)
        res_layout.addWidget(self.combo_res, 1)
        right_layout.addLayout(res_layout)

        # Delivery Codec Combo (Single control per setting)
        p_layout = QHBoxLayout()
        p_label = QLabel("Delivery Codec:", right_box)
        p_label.setFixedWidth(110)
        self.combo_preset = QComboBox(right_box)
        self.combo_preset.addItem("NVENC H.264 (MP4) — Fast NVIDIA GPU Hardware Encode [Default]", "nvenc")
        self.combo_preset.addItem("NVENC H.265 (MP4) — Fast NVIDIA GPU Hardware Encode", "nvenc265")
        self.combo_preset.addItem("H.264 (MP4) — Web & YouTube Delivery (CPU)", "youtube")
        self.combo_preset.addItem("H.265 / HEVC (MP4) — High Efficiency Web Delivery (CPU)", "h265")
        self.combo_preset.addItem("SVT-AV1 (MP4) — Modern Ultra-Compact Codec", "av1")
        self.combo_preset.addItem("ProRes 422 (MOV) — 10-Bit Intermediate Master", "prores")
        self.combo_preset.addItem("VP9 (WebM) — Open Web Streaming", "webm")
        self.combo_preset.addItem("Archive (MKV) — Near Lossless (H.264 + FLAC)", "archive")
        self.combo_preset.currentIndexChanged.connect(self._update_estimates)
        p_layout.addWidget(p_label)
        p_layout.addWidget(self.combo_preset, 1)
        right_layout.addLayout(p_layout)

        # Parallel Jobs & Custom CRF
        opt_row = QHBoxLayout()
        j_label = QLabel("Parallel Jobs:", right_box)
        j_label.setFixedWidth(110)
        self.spin_jobs = QSpinBox(right_box)
        cpu_count = max(1, (os.cpu_count() or 4) // 2)
        self.spin_jobs.setRange(1, os.cpu_count() or 16)
        self.spin_jobs.setValue(cpu_count)
        opt_row.addWidget(j_label)
        opt_row.addWidget(self.spin_jobs, 1)

        self.chk_crf = QCheckBox("Custom CRF:", right_box)
        self.chk_crf.setStyleSheet("margin-left: 10px;")
        self.spin_crf = QSpinBox(right_box)
        self.spin_crf.setRange(0, 51)
        self.spin_crf.setValue(18)
        self.spin_crf.setEnabled(False)
        self.chk_crf.toggled.connect(self.spin_crf.setEnabled)
        self.chk_crf.toggled.connect(self._update_estimates)
        self.spin_crf.valueChanged.connect(self._update_estimates)
        opt_row.addWidget(self.chk_crf)
        opt_row.addWidget(self.spin_crf)
        right_layout.addLayout(opt_row)

        # Audio Override
        audio_row = QHBoxLayout()
        a_label = QLabel("Audio Codec:", right_box)
        a_label.setFixedWidth(110)
        self.combo_audio = QComboBox(right_box)
        self.combo_audio.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_audio.setMinimumContentsLength(15)
        self.combo_audio.addItem("Preset Default [Default]", "")
        self.combo_audio.addItem("AAC — 192 kbps (universal web)", "aac")
        self.combo_audio.addItem("PCM — 24-bit lossless", "pcm_s24le")
        self.combo_audio.addItem("FLAC — lossless compressed", "flac")
        self.combo_audio.addItem("ALAC — Apple lossless", "alac")
        self.combo_audio.addItem("Opus — 128 kbps (compact)", "libopus")
        self.combo_audio.addItem("MP3 — 320 kbps (compact lossy)", "libmp3lame")
        audio_row.addWidget(a_label)
        audio_row.addWidget(self.combo_audio, 1)
        right_layout.addLayout(audio_row)

        # Output Folder
        out_layout = QHBoxLayout()
        out_label = QLabel("Output Folder:", right_box)
        out_label.setFixedWidth(110)
        self.txt_out_dir = QLineEdit(right_box)
        self.txt_out_dir.setPlaceholderText("Default: Same directory as source file")
        btn_out_browse = QPushButton("Browse...", right_box)
        btn_out_browse.setObjectName("secondaryBtn")
        btn_out_browse.clicked.connect(self._browse_output)
        out_layout.addWidget(out_label)
        out_layout.addWidget(self.txt_out_dir, 1)
        out_layout.addWidget(btn_out_browse)
        right_layout.addLayout(out_layout)

        self.chk_dry_run = QCheckBox("Dry-run preview (show ffmpeg command without running)", right_box)
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
        self.btn_start = QPushButton("📤 Convert for Delivery", right_box)
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_export)

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
        default_dir = os.path.expanduser("~/Downloads") if os.path.exists(os.path.expanduser("~/Downloads")) else os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", default_dir)
        if folder:
            self.txt_out_dir.setText(folder)

    def _update_estimates(self):
        meta_list = self.file_queue.get_selected_metadata()
        if not meta_list:
            self.lbl_est_size.setText("📊 Total Input: 0 MB  ➔  Est. Output: ~0 MB")
            return

        total_input_bytes = sum(m["filesize_bytes"] for m in meta_list)
        total_duration = sum(m["duration_sec"] for m in meta_list)

        preset = self.combo_preset.currentData() or "youtube"
        res_val = self.combo_res.currentData() or "original"
        crf_val = self.spin_crf.value() if self.chk_crf.isChecked() else None

        est = calculate_estimated_output(total_duration, "export", preset, resolution=res_val, crf_override=crf_val)

        self.lbl_est_size.setText(f"📊 Input: {format_size(total_input_bytes)}  ➔  Est. Output: {est['est_str']} ({est['bitrate_mbps']} Mbps)")

    def _start_export(self):
        meta_list = self.file_queue.get_selected_metadata()
        if not meta_list:
            return

        preset = self.combo_preset.currentData() or "youtube"
        cmd = [get_bin_path("resolve-export"), "-p", preset]

        res_val = self.combo_res.currentData() or "original"
        if res_val != "original":
            cmd.extend(["-r", res_val])

        if self.chk_crf.isChecked():
            cmd.extend(["-C", str(self.spin_crf.value())])

        audio_override = self.combo_audio.currentData() if self.combo_audio.currentData() else ""
        if audio_override:
            cmd.extend(["-A", audio_override])

        jobs = str(self.spin_jobs.value())
        if self.spin_jobs.value() > 1:
            cmd.extend(["-j", jobs])

        out_dir = self.txt_out_dir.text().strip()
        if out_dir:
            cmd.extend(["-o", out_dir])
            self.last_output_dir = out_dir
        else:
            first_path = meta_list[0]["path"]
            self.last_output_dir = os.path.dirname(first_path)

        if self.chk_dry_run.isChecked():
            cmd.append("-n")

        for meta in meta_list:
            cmd.append(meta["path"])

        self.start_export_requested.emit(cmd, meta_list)
