"""
Widget for displaying video metadata preview, segment selection (Heatmap, Custom, AI Highlights), and AI provider settings.
"""

import urllib.request
import ssl
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QListWidget, QListWidgetItem,
    QCheckBox, QRadioButton, QButtonGroup, QLineEdit, QPushButton, QStackedWidget, QWidget, QComboBox
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from core import config

class ThumbnailLoaderWorker(QThread):
    finished = pyqtSignal(QPixmap)
    error = pyqtSignal()
    
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        
    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            data = urllib.request.urlopen(req, context=ctx).read()
            image = QImage()
            image.loadFromData(data)
            pixmap = QPixmap.fromImage(image)
            self.finished.emit(pixmap)
        except Exception:
            self.error.emit()

class PreviewWidget(QFrame):
    selection_changed = pyqtSignal()
    ai_scan_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.segments_data = []
        self.segments_data = []
        self.ai_segments_data = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header Title
        title_label = QLabel("📺 Video Preview & Segment Selection")
        title_label.setProperty("class", "section-header")
        layout.addWidget(title_label)

        # Video Info Panel (Thumbnail + Details)
        info_layout = QHBoxLayout()
        
        self.thumbnail_label = QLabel("No Video Loaded")
        self.thumbnail_label.setFixedSize(160, 90)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #64748b;")
        info_layout.addWidget(self.thumbnail_label)

        meta_layout = QVBoxLayout()
        self.video_title = QLabel("Masukkan URL YouTube lalu klik Load Video")
        self.video_title.setWordWrap(True)
        self.video_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")

        self.video_uploader = QLabel("Uploader: -")
        self.video_uploader.setProperty("class", "muted")

        self.video_duration = QLabel("Durasi: -")
        self.video_duration.setProperty("class", "muted")

        meta_layout.addWidget(self.video_title)
        meta_layout.addWidget(self.video_uploader)
        meta_layout.addWidget(self.video_duration)
        meta_layout.addStretch()
        info_layout.addLayout(meta_layout, 1)

        layout.addLayout(info_layout)

        # Mode Selection Radio Buttons (1. Heatmap, 2. Manual Custom, 3. AI Highlight)
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Metode Penentuan Klip:")
        mode_label.setStyleSheet("font-weight: 600;")
        
        self.btn_group = QButtonGroup(self)
        self.radio_heatmap = QRadioButton("1. Heatmap (Most Replayed)")
        self.radio_custom = QRadioButton("2. Kustom Range (Manual)")
        self.radio_ai = QRadioButton("3. AI Highlight Detector (LLM)")
        self.radio_heatmap.setChecked(True)

        self.btn_group.addButton(self.radio_heatmap, 1)
        self.btn_group.addButton(self.radio_custom, 2)
        self.btn_group.addButton(self.radio_ai, 3)
        self.btn_group.idToggled.connect(self.on_mode_changed)

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.radio_heatmap)
        mode_layout.addWidget(self.radio_custom)
        mode_layout.addWidget(self.radio_ai)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Stacked view for Heatmap List vs Custom Range inputs vs AI Highlights
        self.mode_stack = QStackedWidget()

        # Page 1: Heatmap Segments List
        heatmap_page = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_page)
        heatmap_layout.setContentsMargins(0, 0, 0, 0)

        list_header_layout = QHBoxLayout()
        self.segment_count_label = QLabel("Pilih Segmen Heatmap:")
        self.segment_count_label.setProperty("class", "muted")

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all_segments)
        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.clicked.connect(self.deselect_all_segments)

        list_header_layout.addWidget(self.segment_count_label)
        list_header_layout.addStretch()
        list_header_layout.addWidget(self.btn_select_all)
        list_header_layout.addWidget(self.btn_deselect_all)
        heatmap_layout.addLayout(list_header_layout)

        self.segment_list = QListWidget()
        self.segment_list.setFixedHeight(160)
        heatmap_layout.addWidget(self.segment_list)

        self.mode_stack.addWidget(heatmap_page)

        # Page 2: Custom Range Inputs
        custom_page = QWidget()
        custom_layout = QHBoxLayout(custom_page)
        custom_layout.setContentsMargins(0, 8, 0, 8)

        custom_layout.addWidget(QLabel("Waktu Mulai:"))
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("detik (contoh: 30) atau MM:SS")
        custom_layout.addWidget(self.start_input)

        custom_layout.addWidget(QLabel("Waktu Selesai:"))
        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("detik (contoh: 90) atau MM:SS")
        custom_layout.addWidget(self.end_input)

        self.mode_stack.addWidget(custom_page)

        # Page 3: AI Highlight Detector
        ai_page = QWidget()
        ai_layout = QVBoxLayout(ai_page)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_layout.setSpacing(12)

        self.btn_run_ai_scan = QPushButton("🤖 Scan Highlights dengan AI")
        self.btn_run_ai_scan.setProperty("class", "primary")
        self.btn_run_ai_scan.setMinimumHeight(40)
        self.btn_run_ai_scan.clicked.connect(self.on_run_ai_scan)
        ai_layout.addWidget(self.btn_run_ai_scan)

        # AI Highlight Segment Checklist ListWidget
        self.ai_segment_count_label = QLabel("Segmen AI Highlight (Transkripsi Whisper + LLM):")
        self.ai_segment_count_label.setProperty("class", "muted")
        ai_layout.addWidget(self.ai_segment_count_label)

        self.ai_segment_list = QListWidget()
        self.ai_segment_list.setFixedHeight(140)
        ai_layout.addWidget(self.ai_segment_list)

        self.mode_stack.addWidget(ai_page)

        layout.addWidget(self.mode_stack)

    def set_ai_scanning(self, scanning: bool):
        if scanning:
            self.btn_run_ai_scan.setEnabled(False)
            self.btn_run_ai_scan.setText("⏳ Memproses AI Scan (Whisper + LLM)...")
        else:
            self.btn_run_ai_scan.setEnabled(True)
            self.btn_run_ai_scan.setText("🤖 Scan Highlights dengan AI")

    def on_run_ai_scan(self):
        ai_config = {
            "provider": getattr(config, "ai_provider", "ollama"),
            "ollama_host": getattr(config, "ollama_host", "http://localhost:11434"),
            "ollama_model": getattr(config, "ollama_model", "llama3"),
            "gemini_key": getattr(config, "gemini_key", ""),
            "gemini_model": getattr(config, "gemini_model", "gemini-1.5-flash"),
            "openai_key": getattr(config, "openai_key", ""),
            "openai_model": getattr(config, "openai_model", "gpt-4o-mini"),
        }
        self.ai_scan_requested.emit(ai_config)

    def set_preview_data(self, preview: dict):
        self.video_title.setText(preview.get("title", "Unknown Title"))
        self.video_uploader.setText(f"Uploader: {preview.get('uploader', '-')}")
        
        dur_s = preview.get("duration", 0)
        m, s = divmod(dur_s, 60)
        h, m = divmod(m, 60)
        dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        self.video_duration.setText(f"Durasi: {dur_str} ({dur_s}s)")

        # Load Thumbnail asynchronously
        thumb_url = preview.get("thumbnail")
        if thumb_url:
            self.thumbnail_label.setText("Memuat Thumbnail...")
            self.thumb_worker = ThumbnailLoaderWorker(thumb_url, self)
            self.thumb_worker.finished.connect(self._on_thumbnail_loaded)
            self.thumb_worker.error.connect(lambda: self.thumbnail_label.setText("Thumbnail N/A"))
            self.thumb_worker.start()
        else:
            self.thumbnail_label.setText("Thumbnail N/A")

    def _on_thumbnail_loaded(self, pixmap: QPixmap):
        scaled = pixmap.scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.thumbnail_label.setPixmap(scaled)

    def set_scan_data(self, scan_result: dict):
        self.segments_data = scan_result.get("segments", [])
        self.segment_list.clear()
        
        self.segment_count_label.setText(f"Segmen Heatmap Ditemukan ({len(self.segments_data)}):")
        
        for idx, seg in enumerate(self.segments_data, start=1):
            start_s = int(seg.get("start", 0))
            dur_s = int(seg.get("duration", 0))
            score = seg.get("score", 0.0)
            
            m1, s1 = divmod(start_s, 60)
            m2, s2 = divmod(start_s + dur_s, 60)
            time_str = f"{m1:02d}:{s1:02d} - {m2:02d}:{s2:02d}"
            
            item_text = f"Klip #{idx} | {time_str} (durasi: {dur_s}s) | Score: {score:.2f}"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, seg)
            self.segment_list.addItem(item)

    def set_ai_scan_data(self, ai_result: dict):
        self.ai_segments_data = ai_result.get("segments", [])
        self.ai_segment_list.clear()

        self.ai_segment_count_label.setText(f"Segmen AI Highlights Ditemukan ({len(self.ai_segments_data)}):")

        for idx, seg in enumerate(self.ai_segments_data, start=1):
            start_s = int(seg.get("start", 0))
            dur_s = int(seg.get("duration", 0))
            title = seg.get("title", "AI Highlight")
            reason = seg.get("reason", "")
            score = seg.get("score", 0.9)

            m1, s1 = divmod(start_s, 60)
            m2, s2 = divmod(start_s + dur_s, 60)
            time_str = f"{m1:02d}:{s1:02d} - {m2:02d}:{s2:02d}"

            item_text = f"🤖 Klip #{idx} | {title} [{time_str}] ({dur_s}s) | {reason}"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, seg)
            self.ai_segment_list.addItem(item)

    def select_all_segments(self):
        target_list = self.ai_segment_list if self.radio_ai.isChecked() else self.segment_list
        for idx in range(target_list.count()):
            target_list.item(idx).setCheckState(Qt.CheckState.Checked)

    def deselect_all_segments(self):
        target_list = self.ai_segment_list if self.radio_ai.isChecked() else self.segment_list
        for idx in range(target_list.count()):
            target_list.item(idx).setCheckState(Qt.CheckState.Unchecked)

    def on_mode_changed(self, btn_id: int, checked: bool):
        if checked:
            # 1: Heatmap (Page 0), 2: Custom (Page 1), 3: AI Highlights (Page 2)
            self.mode_stack.setCurrentIndex(btn_id - 1)

    def get_selected_mode(self) -> str:
        if self.radio_ai.isChecked():
            return "ai"
        elif self.radio_custom.isChecked():
            return "custom"
        return "heatmap"

    def get_selected_segments(self) -> list:
        target_list = self.ai_segment_list if self.radio_ai.isChecked() else self.segment_list
        selected = []
        for idx in range(target_list.count()):
            item = target_list.item(idx)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected

    def get_custom_range(self) -> tuple:
        return self.start_input.text().strip(), self.end_input.text().strip()
