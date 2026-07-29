import os

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QComboBox, QLineEdit, QFileDialog, QFrame
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QComboBox, QLineEdit, QFileDialog, QFrame
    )
    from PySide6.QtCore import Qt

from ..components.log_viewer import LogViewer
from ..backend.system import get_bin_path
from ..backend.runner import ProcessRunnerThread

class WatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("👁 Watch Folder Auto-Transcode Service")
        self.resize(650, 520)
        self.runner = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title_lbl = QLabel("Watch Folder Auto-Transcode Daemon", self)
        title_lbl.setObjectName("viewTitle")

        sub_lbl = QLabel("Monitors a target folder using inotifywait and automatically transcodes new media files for Resolve", self)
        sub_lbl.setObjectName("viewSub")
        sub_lbl.setWordWrap(True)

        header_box.addWidget(title_lbl)
        header_box.addWidget(sub_lbl)
        layout.addLayout(header_box)

        # Configuration Card
        config_card = QFrame(self)
        config_card.setObjectName("cardFrame")
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(16, 16, 16, 16)
        config_layout.setSpacing(10)

        card_title = QLabel("⚙️ Watch Service Configuration", config_card)
        card_title.setObjectName("sectionTitle")
        config_layout.addWidget(card_title)

        dir_layout = QHBoxLayout()
        dir_label = QLabel("Watch Folder Path:", config_card)
        dir_label.setFixedWidth(130)
        self.txt_watch_dir = QLineEdit(os.path.expanduser("~/Downloads"), config_card)
        btn_browse = QPushButton("Browse...", config_card)
        btn_browse.setObjectName("secondaryBtn")
        btn_browse.clicked.connect(self._browse_watch_dir)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.txt_watch_dir, 1)
        dir_layout.addWidget(btn_browse)
        config_layout.addLayout(dir_layout)

        c_layout = QHBoxLayout()
        c_label = QLabel("Video Codec:", config_card)
        c_label.setFixedWidth(130)
        self.combo_codec = QComboBox(config_card)
        self.combo_codec.addItem("AV1 (.mkv) — Modern SVT-AV1 (4-5x Smaller, Resolve Free) [Default]", "av1")
        self.combo_codec.addItem("DNxHR (.mov) — Avid Intermediate (Fast Decode)", "dnxhr")
        c_layout.addWidget(c_label)
        c_layout.addWidget(self.combo_codec, 1)
        config_layout.addLayout(c_layout)

        q_layout = QHBoxLayout()
        q_label = QLabel("Transcode Quality:", config_card)
        q_label.setFixedWidth(130)
        self.combo_quality = QComboBox(config_card)
        self.combo_quality.addItem("HQ — High Quality (DNxHR HQ / AV1 CRF 26) [Default]", "hq")
        self.combo_quality.addItem("SQ — Standard Quality (DNxHR SQ / AV1 CRF 30)", "sq")
        self.combo_quality.addItem("LB — Low Bitrate / Proxy (DNxHR LB / AV1 CRF 35)", "lb")
        self.combo_quality.addItem("HQX — 12-bit High Quality (DNxHR HQX / AV1 CRF 22)", "hqx")
        self.combo_quality.addItem("444 — 4:4:4 Maximum Quality (DNxHR 444 / AV1 CRF 20)", "444")
        q_layout.addWidget(q_label)
        q_layout.addWidget(self.combo_quality, 1)
        config_layout.addLayout(q_layout)

        a_layout = QHBoxLayout()
        a_label = QLabel("Audio Mode:", config_card)
        a_label.setFixedWidth(130)
        self.combo_audio = QComboBox(config_card)
        self.combo_audio.addItem("PCM — Force Transcode Audio to PCM 24-Bit 48kHz WAV [Default]", "pcm")
        self.combo_audio.addItem("AUTO — Copy Lossless, Transcode AAC/Opus → FLAC", "auto")
        self.combo_audio.addItem("FLAC — Force Transcode Audio to Lossless FLAC", "flac")
        self.combo_audio.addItem("ALAC — Force Transcode Audio to Apple Lossless M4A", "alac")
        a_layout.addWidget(a_label)
        a_layout.addWidget(self.combo_audio, 1)
        config_layout.addLayout(a_layout)

        out_layout = QHBoxLayout()
        out_label = QLabel("Output Folder:", config_card)
        out_label.setFixedWidth(130)
        self.txt_out_dir = QLineEdit(config_card)
        self.txt_out_dir.setPlaceholderText("Default: <WATCH_DIR>/resolve_ready")
        btn_out_browse = QPushButton("Browse...", config_card)
        btn_out_browse.setObjectName("secondaryBtn")
        btn_out_browse.clicked.connect(self._browse_out_dir)
        out_layout.addWidget(out_label)
        out_layout.addWidget(self.txt_out_dir, 1)
        out_layout.addWidget(btn_out_browse)
        config_layout.addLayout(out_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_start = QPushButton("▶️ Start Watch Daemon", config_card)
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_watch)

        self.btn_stop = QPushButton("⏹️ Stop Daemon", config_card)
        self.btn_stop.setObjectName("dangerBtn")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_watch)

        btn_layout.addWidget(self.btn_start, 1)
        btn_layout.addWidget(self.btn_stop)
        config_layout.addLayout(btn_layout)

        layout.addWidget(config_card)

        # Log viewer
        self.log_viewer = LogViewer("Live Ingest Feed", self)
        self.log_viewer.setMinimumHeight(140)
        layout.addWidget(self.log_viewer, 1)

        # Footer Close Button
        footer = QHBoxLayout()
        footer.addStretch()
        btn_close = QPushButton("Close Modal", self)
        btn_close.setObjectName("secondaryBtn")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def _browse_watch_dir(self):
        from ..components.drop_zone import DropZone
        default_dir = DropZone.get_default_dir()
        folder = QFileDialog.getExistingDirectory(self, "Select Watch Folder", default_dir)
        if folder:
            DropZone.save_last_dir(folder)
            self.txt_watch_dir.setText(folder)

    def _browse_out_dir(self):
        from ..components.drop_zone import DropZone
        default_dir = DropZone.get_default_dir()
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", default_dir)
        if folder:
            DropZone.save_last_dir(folder)
            self.txt_out_dir.setText(folder)

    def _start_watch(self):
        watch_path = self.txt_watch_dir.text().strip()
        if not watch_path or not os.path.exists(watch_path):
            self.log_viewer.append_log("[ERR] Specified watch path does not exist.")
            return

        codec_val = self.combo_codec.currentData() or "av1"
        q_val = self.combo_quality.currentData() or "hq"
        a_val = self.combo_audio.currentData() or "auto"
        cmd = [get_bin_path("davinci-kit-watch"), "-c", codec_val, "-q", q_val, "-a", a_val]

        out_dir = self.txt_out_dir.text().strip()
        if out_dir:
            cmd.extend(["-o", out_dir])

        cmd.append(watch_path)

        self.log_viewer.clear_log()
        self.log_viewer.append_log(f"[INFO] Starting davinci-kit-watch daemon on directory: {watch_path}")
        self.log_viewer.append_log(f"[INFO] Command: {' '.join(cmd)}")

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.runner = ProcessRunnerThread(cmd)
        self.runner.output_line.connect(self.log_viewer.append_log)
        self.runner.finished_signal.connect(self._on_finished)
        self.runner.start()

    def _stop_watch(self):
        if self.runner and self.runner.isRunning():
            self.runner.cancel()
            self.log_viewer.append_log("[WARN] Stopping watch daemon...")

    def _on_finished(self, return_code: int, output: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.log_viewer.append_log(f"[INFO] Watch daemon stopped (Exit code: {return_code})")
