import os

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QFrame, QSplitter, QScrollArea, QListWidget, QListWidgetItem,
        QApplication
    )
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QFrame, QSplitter, QScrollArea, QListWidget, QListWidgetItem,
        QApplication
    )
    from PySide6.QtCore import Qt, Signal as pyqtSignal

from ..components.file_queue import FileQueue
from ..backend.inspector import get_detailed_media_info

class InspectorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_meta = None

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(14)

        # Left Column: File Queue
        self.file_queue = FileQueue(
            title="Media Inspection Queue",
            drop_title="Drag & drop media files to inspect",
            drop_subtitle="Inspect container, video/audio streams, and Resolve compatibility",
            parent=splitter
        )
        self.file_queue.list_widget.currentItemChanged.connect(self._on_item_changed)
        self.file_queue.queue_changed.connect(self._on_queue_changed)

        # Right Column: Detail Inspector Panel
        right_container = QWidget(splitter)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # ScrollArea for deep media inspection card view
        self.scroll_area = QScrollArea(right_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 8, 0)
        self.scroll_layout.setSpacing(14)

        # Empty State Label
        self.lbl_empty = QLabel("🔍 Select or drop a file on the left to inspect technical details and Resolve compatibility", self.scroll_content)
        self.lbl_empty.setWordWrap(True)
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setStyleSheet("color: #6c7086; font-size: 13px; margin: 40px;")
        self.scroll_layout.addWidget(self.lbl_empty)

        self.scroll_area.setWidget(self.scroll_content)
        right_layout.addWidget(self.scroll_area)

        splitter.addWidget(self.file_queue)
        splitter.addWidget(right_container)
        splitter.setSizes([450, 550])

        main_layout.addWidget(splitter)

    def _on_queue_changed(self):
        meta_list = self.file_queue.get_selected_metadata()
        if meta_list and self.file_queue.list_widget.count() > 0:
            if not self.file_queue.list_widget.currentItem():
                self.file_queue.list_widget.setCurrentRow(0)
        else:
            self.clear_inspection()

    def _on_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        row = self.file_queue.list_widget.row(current)
        meta_list = self.file_queue.get_selected_metadata()
        if 0 <= row < len(meta_list):
            file_path = meta_list[row]["path"]
            self.inspect_file(file_path)

    def clear_inspection(self):
        # Clear layout children
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.lbl_empty = QLabel("🔍 Select or drop a file on the left to inspect technical details and Resolve compatibility", self.scroll_content)
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setStyleSheet("color: #6c7086; font-size: 13px; margin: 40px;")
        self.scroll_layout.addWidget(self.lbl_empty)

    def inspect_file(self, file_path: str):
        detailed = get_detailed_media_info(file_path)
        if not detailed.get("valid"):
            return

        # Clear layout children
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        summary = detailed["summary"]
        container = detailed["container"]
        video = detailed["video"]
        audio_streams = detailed["audio_streams"]
        compat = detailed["compat"]

        # 1. Header Card (File Title & Location)
        hdr_card = QFrame(self.scroll_content)
        hdr_card.setObjectName("cardFrame")
        hdr_box = QVBoxLayout(hdr_card)
        hdr_box.setContentsMargins(16, 14, 16, 14)
        hdr_box.setSpacing(4)

        lbl_fname = QLabel(summary["filename"], hdr_card)
        lbl_fname.setWordWrap(True)
        lbl_fname.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        lbl_fpath = QLabel(file_path, hdr_card)
        lbl_fpath.setWordWrap(True)
        lbl_fpath.setStyleSheet("font-size: 11px; color: #7e8299;")
        lbl_fpath.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        hdr_box.addWidget(lbl_fname)
        hdr_box.addWidget(lbl_fpath)
        self.scroll_layout.addWidget(hdr_card)

        # 2. DaVinci Resolve Free (Linux) Compatibility Card
        compat_card = QFrame(self.scroll_content)
        compat_card.setObjectName("compatCard")

        bg_color = "rgba(0, 229, 255, 0.05)" if compat["verdict"] == "full" else ("rgba(255, 183, 77, 0.06)" if "partial" in compat["verdict"] else "rgba(255, 82, 82, 0.06)")
        border_color = compat["badge_color"]

        compat_card.setStyleSheet(f"""
            QFrame#compatCard {{
                border: 1px solid {border_color};
                border-radius: 8px;
                background-color: {bg_color};
            }}
            QLabel {{
                border: none;
                background: transparent;
                padding: 0px;
            }}
        """)
        c_box = QVBoxLayout(compat_card)
        c_box.setContentsMargins(16, 14, 16, 14)
        c_box.setSpacing(10)

        # Status Title
        badge_lbl = QLabel(compat["title"], compat_card)
        badge_lbl.setWordWrap(True)
        badge_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {compat['badge_color']};")
        c_box.addWidget(badge_lbl)

        # Summary Description
        summary_lbl = QLabel(compat["summary"], compat_card)
        summary_lbl.setWordWrap(True)
        summary_lbl.setStyleSheet("font-size: 12px; color: #a9acbe;")
        c_box.addWidget(summary_lbl)

        # Issues
        if compat["structured_issues"]:
            c_box.addSpacing(4)
            iss_title = QLabel("Issues", compat_card)
            iss_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #8c90a4; text-transform: uppercase;")
            c_box.addWidget(iss_title)

            for issue in compat["structured_issues"]:
                row_layout = QHBoxLayout()
                row_layout.setSpacing(8)

                lbl_label = QLabel(issue["label"] + ":", compat_card)
                lbl_label.setFixedWidth(50)
                lbl_label.setStyleSheet("font-size: 12px; color: #ff8a80; font-weight: bold;")

                lbl_text = QLabel(issue["text"], compat_card)
                lbl_text.setWordWrap(True)
                lbl_text.setStyleSheet("font-size: 12px; color: #f0f2fb;")

                row_layout.addWidget(lbl_label)
                row_layout.addWidget(lbl_text, 1)
                c_box.addLayout(row_layout)



        self.scroll_layout.addWidget(compat_card)

        # 3. Container Card
        cnt_card = QFrame(self.scroll_content)
        cnt_card.setObjectName("cardFrame")
        cnt_box = QVBoxLayout(cnt_card)
        cnt_box.setContentsMargins(16, 14, 16, 14)
        cnt_box.setSpacing(10)

        cnt_title = QLabel("📦 Container Info", cnt_card)
        cnt_title.setObjectName("sectionTitle")
        cnt_box.addWidget(cnt_title)

        cnt_grid = self._create_prop_grid([
            ("Format", container.get("format_long", "N/A")),
            ("File Size", container.get("size_str", "N/A")),
            ("Duration", container.get("duration_str", "N/A")),
            ("Bitrate", container.get("bitrate_str", "N/A")),
            ("Streams", f"{container.get('nb_streams', 1)} total"),
            ("Created", container.get("created", "N/A")),
            ("Device / Tag", container.get("device", "N/A"))
        ], cnt_card)
        cnt_box.addLayout(cnt_grid)
        self.scroll_layout.addWidget(cnt_card)

        # 4. Video Stream Card
        if video:
            v_card = QFrame(self.scroll_content)
            v_card.setObjectName("cardFrame")
            v_box = QVBoxLayout(v_card)
            v_box.setContentsMargins(16, 14, 16, 14)
            v_box.setSpacing(10)

            v_title = QLabel("🎥 Video Stream", v_card)
            v_title.setObjectName("sectionTitle")
            v_box.addWidget(v_title)

            v_grid = self._create_prop_grid([
                ("Codec", f"{video['codec']} ({video['codec_long']})"),
                ("Profile", video["profile"]),
                ("Resolution", video["resolution"]),
                ("Frame Rate", video["fps"]),
                ("Bit Depth", video["bit_depth"]),
                ("Chroma Subsampling", video["chroma"]),
                ("Color Space", video["color_space"]),
                ("Color Transfer", video["color_transfer"]),
                ("Color Primaries", video["color_primaries"]),
                ("Color Range", video["color_range"]),
                ("Bitrate", video["bitrate"]),
                ("Frame Count", video["nb_frames"]),
                ("Aspect Ratio", video["aspect"])
            ], v_card)
            v_box.addLayout(v_grid)
            self.scroll_layout.addWidget(v_card)

        # 5. Audio Stream Card(s)
        if audio_streams:
            for idx, a_strm in enumerate(audio_streams):
                a_card = QFrame(self.scroll_content)
                a_card.setObjectName("cardFrame")
                a_box = QVBoxLayout(a_card)
                a_box.setContentsMargins(16, 14, 16, 14)
                a_box.setSpacing(10)

                a_title = QLabel(f"🎵 Audio Stream #{idx + 1}", a_card)
                a_title.setObjectName("sectionTitle")
                a_box.addWidget(a_title)

                a_grid = self._create_prop_grid([
                    ("Codec", f"{a_strm['codec']} ({a_strm['codec_long']})"),
                    ("Profile", a_strm["profile"]),
                    ("Sample Rate", a_strm["sample_rate"]),
                    ("Channels", a_strm["channels"]),
                    ("Sample Format", a_strm["sample_fmt"]),
                    ("Bitrate", a_strm["bitrate"])
                ], a_card)
                a_box.addLayout(a_grid)
                self.scroll_layout.addWidget(a_card)

        self.scroll_layout.addStretch()

    def _create_prop_grid(self, props: list, parent=None) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(6)
        for label, val in props:
            row = QHBoxLayout()
            l_lbl = QLabel(label + ":", parent)
            l_lbl.setFixedWidth(140)
            l_lbl.setStyleSheet("font-size: 12px; color: #8c90a4; font-weight: 500;")

            v_lbl = QLabel(str(val), parent)
            v_lbl.setWordWrap(True)
            v_lbl.setStyleSheet("font-size: 12px; color: #f0f2fb; font-weight: 400;")
            v_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            row.addWidget(l_lbl)
            row.addWidget(v_lbl, 1)
            box.addLayout(row)
        return box
