"""
Widget for showing execution progress, real-time log terminal, and process controls.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextEdit,
    QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

class LogConsoleWidget(QFrame):
    start_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.total_clips = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header Title & Stage Indicator
        header_layout = QHBoxLayout()
        title_label = QLabel("🚀 Process Dashboard & Log Console")
        title_label.setProperty("class", "section-header")

        self.stage_badge = QLabel("Status: Idle")
        self.stage_badge.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.stage_badge)
        layout.addLayout(header_layout)

        # Progress Bar & Counter Label
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.progress_label = QLabel("0 / 0 Klip")
        self.progress_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #818cf8;")

        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.progress_label)
        layout.addLayout(progress_layout)

        # Real-time Console Log Viewer
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFixedHeight(180)
        self.log_edit.setPlaceholderText("Log proses akan muncul di sini...")
        layout.addWidget(self.log_edit)

        # Control Buttons
        controls_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ MULAI PROSES KLIP")
        self.start_btn.setProperty("class", "primary")
        self.start_btn.setStyleSheet("padding: 10px 24px; font-size: 14px;")
        self.start_btn.clicked.connect(self.start_requested.emit)

        self.cancel_btn = QPushButton("⏹ Batal / Abort")
        self.cancel_btn.setProperty("class", "danger")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)

        self.clear_btn = QPushButton("🗑 Clear Log")
        self.clear_btn.clicked.connect(self.log_edit.clear)

        self.export_btn = QPushButton("💾 Export Log")
        self.export_btn.clicked.connect(self.on_export_log)

        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.cancel_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.clear_btn)
        controls_layout.addWidget(self.export_btn)

        layout.addLayout(controls_layout)

    def append_log(self, text: str):
        self.log_edit.append(text)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def update_stage(self, stage_name: str, data: dict):
        stage_map = {
            "download": "Mengunduh Segmen Audio/Video (yt-dlp)...",
            "crop": "Memotong / Split Screen Video (FFmpeg)...",
            "subtitle_model_load": "Memuat Model Faster-Whisper...",
            "subtitle_transcribe": "Mengekstrak Transkripsi Audio...",
            "ai_detect": "⏳ Menganalisis Momen dengan AI Model...",
            "burn_subtitle": "Melakukan Render Subtitle ke Video...",
            "finalize": "Menggabungkan Intro/Outro...",
            "done_clip": "Selesai Memproses Klip!",
        }

        display = stage_map.get(stage_name, stage_name)
        self.stage_badge.setText(f"Stage: {display}")
        self.stage_badge.setStyleSheet("background-color: #312e81; color: #a5b4fc; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")

        if stage_name == "done_clip":
            done_count = data.get("clip_index", 0)
            if self.total_clips > 0:
                pct = int((done_count / self.total_clips) * 100)
                self.progress_bar.setValue(pct)
                self.progress_label.setText(f"{done_count} / {self.total_clips} Klip")

    def set_total_targets(self, total: int):
        self.total_clips = total
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"0 / {total} Klip")

    def set_processing(self, processing: bool):
        self.start_btn.setEnabled(not processing)
        self.cancel_btn.setEnabled(processing)
        if processing:
            self.stage_badge.setText("Status: Processing...")
            self.stage_badge.setStyleSheet("background-color: #065f46; color: #6ee7b7; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        else:
            self.stage_badge.setText("Status: Idle")
            self.stage_badge.setStyleSheet("background-color: #1e293b; color: #94a3b8; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;")

    def on_export_log(self):
        content = self.log_edit.toPlainText()
        if not content:
            QMessageBox.warning(self, "Peringatan", "Log masih kosong.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Simpan File Log", "cliptzy.log", "Log Files (*.log);;Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "Berhasil", f"Log berhasil disimpan di:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error Export", f"Gagal menyimpan log: {e}")
