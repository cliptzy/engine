"""
Widget for reviewing generated clips, modifying metadata, and uploading to social platforms.
"""

import os
import json
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QCheckBox, QMessageBox, QWidget, QLineEdit, QTextEdit, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.ai_detector import ai_detector
from core import config

class AIGenerateMetadataWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, clip_path: str):
        super().__init__()
        self.clip_path = clip_path
        
    def run(self):
        try:
            job_dir = os.path.dirname(self.clip_path)
            clip_filename = os.path.basename(self.clip_path)
            idx = clip_filename.replace("clip_", "").replace(".mp4", "")
            
            import glob, re
            ass_files = glob.glob(os.path.join(job_dir, f"clip_{idx}_*.ass"))
            
            clip_text = ""
            if ass_files:
                ass_file = ass_files[0]
                try:
                    with open(ass_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("Dialogue:"):
                                parts = line.split(",", 9)
                                if len(parts) >= 10:
                                    raw_text = parts[9].strip()
                                    clean_text = re.sub(r'\{.*?\}', '', raw_text)
                                    clip_text += clean_text + " "
                except Exception as e:
                    self.log_signal.emit(f"[WARNING] Gagal membaca {ass_file}: {e}")
            
            if not clip_text.strip():
                self.log_signal.emit(f"[WARNING] Teks subtitle klip kosong atau file .ass tidak ditemukan untuk {clip_filename}. Mencoba fallback ke transkrip utama...")
                transcript_file = os.path.join(job_dir, "transcript.json")
                if os.path.exists(transcript_file):
                    with open(transcript_file, "r", encoding="utf-8") as f:
                        transcript_segments = json.load(f)
                        clip_text = " ".join([seg.get("text", "") for seg in transcript_segments])
            
            preview_file = os.path.join(job_dir, "preview.json")
            youtube_title = "Unknown Video"
            channel_name = "Unknown Channel"
            if os.path.exists(preview_file):
                try:
                    with open(preview_file, "r", encoding="utf-8") as f:
                        preview_data = json.load(f)
                        youtube_title = preview_data.get("title", "Unknown Video")
                        channel_name = preview_data.get("uploader", "Unknown Channel")
                except Exception as e:
                    self.log_signal.emit(f"[WARNING] Gagal membaca preview.json: {e}")
                
            ai_config = {
                "provider": getattr(config, "ai_provider", "ollama"),
                "ollama_host": getattr(config, "ollama_host", ""),
                "ollama_model": getattr(config, "ollama_model", ""),
                "gemini_key": getattr(config, "gemini_key", ""),
                "gemini_model": getattr(config, "gemini_model", ""),
                "openai_key": getattr(config, "openai_key", ""),
                "openai_model": getattr(config, "openai_model", "")
            }
            
            def event_hook(ev_type, data):
                if ev_type == "log":
                    self.log_signal.emit(str(data))
                    
            metadata = ai_detector.generate_metadata(
                clip_text=clip_text,
                youtube_title=youtube_title,
                channel_name=channel_name,
                ai_config=ai_config,
                event_hook=event_hook
            )
            self.finished_signal.emit(metadata)
            
        except Exception as e:
            self.log_signal.emit(f"[ERROR] Exception saat generate metadata: {e}")
            self.finished_signal.emit({})

class UploaderWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.output_dir = "clips"
        self.worker = None
        # clip_path -> dict of metadata
        self.clip_metadata = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_label = QLabel("📤 Uploader & Metadata Manager")
        title_label.setProperty("class", "section-header")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        content_layout = QHBoxLayout()

        # Left Column: Checkable List of Clips
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Daftar Klip Siap Upload (Centang untuk pilih):"))
        self.clip_list = QListWidget()
        self.clip_list.setFixedWidth(250)
        self.clip_list.itemClicked.connect(self.on_clip_selected)
        left_layout.addWidget(self.clip_list)

        content_layout.addLayout(left_layout)

        # Right Column: Metadata Details
        right_layout = QVBoxLayout()
        
        self.details_panel = QWidget()
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Form
        grid = QGridLayout()
        
        grid.addWidget(QLabel("Title (Judul):"), 0, 0)
        self.title_input = QLineEdit()
        grid.addWidget(self.title_input, 0, 1)
        
        grid.addWidget(QLabel("Description:"), 1, 0)
        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(80)
        grid.addWidget(self.desc_input, 1, 1)
        
        grid.addWidget(QLabel("Hashtags/Tags:"), 2, 0)
        self.tags_input = QLineEdit()
        grid.addWidget(self.tags_input, 2, 1)
        
        details_layout.addLayout(grid)
        
        # Button Generate
        btn_layout = QHBoxLayout()
        self.btn_generate = QPushButton("✨ Auto Generate via AI")
        self.btn_generate.setProperty("class", "primary")
        self.btn_generate.clicked.connect(self.on_generate_ai)
        
        self.btn_save = QPushButton("💾 Simpan Metadata")
        self.btn_save.clicked.connect(self.on_save_metadata)
        
        btn_layout.addWidget(self.btn_generate)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        details_layout.addLayout(btn_layout)
        
        right_layout.addWidget(self.details_panel)
        right_layout.addStretch()
        
        # Upload Section
        upload_group = QFrame()
        upload_group.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 6px; padding: 10px; }")
        upload_layout = QVBoxLayout(upload_group)
        
        upload_layout.addWidget(QLabel("Platform Tujuan Upload:"))
        
        chk_layout = QHBoxLayout()
        self.chk_youtube = QCheckBox("YouTube Shorts")
        self.chk_tiktok = QCheckBox("TikTok")
        self.chk_instagram = QCheckBox("Instagram Reels")
        
        chk_layout.addWidget(self.chk_youtube)
        chk_layout.addWidget(self.chk_tiktok)
        chk_layout.addWidget(self.chk_instagram)
        chk_layout.addStretch()
        
        upload_layout.addLayout(chk_layout)
        
        self.btn_upload = QPushButton("📤 Upload Video Tercentang")
        self.btn_upload.setProperty("class", "primary")
        self.btn_upload.setStyleSheet("padding: 10px; font-weight: bold;")
        self.btn_upload.clicked.connect(self.on_upload_clicked)
        upload_layout.addWidget(self.btn_upload)
        
        right_layout.addWidget(upload_group)
        
        content_layout.addLayout(right_layout, 1)
        layout.addLayout(content_layout)
        
        self.details_panel.setEnabled(False)
        self.current_clip_path = None

    def update_outputs(self, outputs: list, output_dir: str):
        self.output_dir = output_dir
        self.clip_list.clear()
        for item in outputs:
            name = item.get("name")
            path = item.get("path")
            size_mb = item.get("size", 0) / (1024 * 1024)
            
            list_item = QListWidgetItem(f"{name} ({size_mb:.1f} MB)")
            list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            list_item.setCheckState(Qt.CheckState.Unchecked)
            list_item.setData(Qt.ItemDataRole.UserRole, path)
            self.clip_list.addItem(list_item)
            
            if path not in self.clip_metadata:
                self.clip_metadata[path] = {"title": name, "description": "", "tags": ""}

    def on_clip_selected(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
            
        self.current_clip_path = path
        self.details_panel.setEnabled(True)
        
        meta = self.clip_metadata.get(path, {})
        self.title_input.setText(meta.get("title", ""))
        self.desc_input.setPlainText(meta.get("description", ""))
        self.tags_input.setText(meta.get("tags", ""))
        
    def on_save_metadata(self):
        if not self.current_clip_path:
            return
            
        self.clip_metadata[self.current_clip_path] = {
            "title": self.title_input.text(),
            "description": self.desc_input.toPlainText(),
            "tags": self.tags_input.text()
        }
        
        from gui.globals import signals
        signals.log_message.emit(f"[INFO] Metadata disimpan untuk: {os.path.basename(self.current_clip_path)}")

    def on_generate_ai(self):
        if not self.current_clip_path:
            return
            
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Proses Berjalan", "Harap tunggu, proses AI sedang berjalan.")
            return
            
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("⏳ Sedang Generate...")
        
        self.worker = AIGenerateMetadataWorker(self.current_clip_path)
        from gui.globals import signals
        self.worker.log_signal.connect(signals.log_message.emit)
        self.worker.finished_signal.connect(self.on_generate_finished)
        self.worker.start()
        
    def on_generate_finished(self, metadata: dict):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("✨ Auto Generate via AI")
        
        if not metadata:
            QMessageBox.warning(self, "Gagal", "Gagal meng-generate metadata. Cek log untuk detail.")
            return
            
        if "title" in metadata:
            self.title_input.setText(metadata["title"])
        if "description" in metadata:
            self.desc_input.setPlainText(metadata["description"])
        if "tags" in metadata:
            self.tags_input.setText(metadata["tags"])
            
        self.on_save_metadata()
        QMessageBox.information(self, "Berhasil", "Metadata sukses di-generate oleh AI!")
        
    def on_upload_clicked(self):
        selected_clips = []
        for i in range(self.clip_list.count()):
            item = self.clip_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_clips.append(item.data(Qt.ItemDataRole.UserRole))
                
        if not selected_clips:
            QMessageBox.warning(self, "Pilih Klip", "Harap centang setidaknya satu video yang ingin di-upload.")
            return
            
        platforms = []
        if self.chk_youtube.isChecked():
            platforms.append("YouTube Shorts")
        if self.chk_tiktok.isChecked():
            platforms.append("TikTok")
        if self.chk_instagram.isChecked():
            platforms.append("Instagram Reels")
            
        if not platforms:
            QMessageBox.warning(self, "Pilih Platform", "Harap centang setidaknya satu platform tujuan upload.")
            return
            
        from gui.globals import signals
        signals.log_message.emit(f"[UPLOAD] Mempersiapkan {len(selected_clips)} video ke {', '.join(platforms)}...")
        
        msg = f"Mempersiapkan {len(selected_clips)} video untuk di-upload ke {', '.join(platforms)}.\nFitur integrasi upload riil sedang dikembangkan."
        QMessageBox.information(self, "Upload Simulasi", msg)
