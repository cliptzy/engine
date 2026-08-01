"""
Widget for reviewing generated clips, modifying metadata, and uploading to social platforms.
"""

import os
import json
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QCheckBox, QMessageBox, QWidget, QLineEdit, QTextEdit, QGridLayout,
    QProgressBar, QComboBox, QDoubleSpinBox
)
import time
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.ai_detector import ai_detector
from core import config

class AIGenerateMetadataWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, clip_path: str, user_context: str = ""):
        super().__init__()
        self.clip_path = clip_path
        self.user_context = user_context
        
    def run(self):
        try:
            job_dir = os.path.dirname(self.clip_path)
            clip_filename = os.path.basename(self.clip_path)
            clip_text = ""
            
            if clip_filename == "merged.mp4":
                # For merged.mp4, combine metadata from all other clips
                from core.utils import read_json
                import glob
                combined_texts = []
                for meta_path in glob.glob(os.path.join(job_dir, "metadata_[0-9]*.json")):
                    idx = os.path.basename(meta_path).replace("metadata_", "").replace(".json", "")
                    m_data = read_json(meta_path)
                    if m_data:
                        t = m_data.get("title", "")
                        d = m_data.get("description", "")
                        combined_texts.append(f"Klip {idx}: Judul: {t}\nDeskripsi: {d}")
                if combined_texts:
                    clip_text = "Ini adalah kompilasi video panjang dari beberapa momen. Berikut ringkasannya:\n" + "\n\n".join(combined_texts)
                else:
                    self.log_signal.emit("[WARNING] Tidak ada metadata individu yang ditemukan untuk membangun konteks merged.mp4.")
            else:
                idx = clip_filename.replace("clip_", "").replace(".mp4", "")
                
                import glob, re
                ass_files = glob.glob(os.path.join(job_dir, f"clip_{idx}_*.ass"))
                
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
                        from core.utils import read_json
                        transcript_segments = read_json(transcript_file, default=[])
                        clip_text = " ".join([seg.get("text", "") for seg in transcript_segments])
            
            from core.utils import get_preview_data
            preview_data = get_preview_data(job_dir=job_dir)
            youtube_title = preview_data.get("title", "Unknown Video")
            channel_name = preview_data.get("uploader", "Unknown Channel")
            youtube_url = preview_data.get("webpage_url", "")
            language = preview_data.get("language") or "Indonesia"
                
            ai_config = {
                "provider": getattr(config, "ai_provider", "ollama"),
                "ollama_host": getattr(config, "ollama_host", ""),
                "ollama_model": getattr(config, "ollama_model", ""),
                "gemini_key": getattr(config, "gemini_key", ""),
                "gemini_model": getattr(config, "gemini_model", ""),
                "openai_key": getattr(config, "openai_key", ""),
                "openai_model": getattr(config, "openai_model", ""),
                "openai_base_url": getattr(config, "openai_base_url", "")
            }
            
            def event_hook(ev_type, data):
                from gui.globals import signals
                if ev_type == "log":
                    signals.log_message.emit(str(data))
                elif ev_type == "log_inline":
                    signals.log_message_inline.emit(str(data))
                    
            metadata = ai_detector.generate_metadata(
                clip_text=clip_text,
                youtube_title=youtube_title,
                channel_name=channel_name,
                youtube_url=youtube_url,
                ai_config=config.to_dict(),
                user_context=self.user_context,
                event_hook=event_hook,
                language=preview_data.get("language", "Indonesia")
            )
            self.finished_signal.emit(metadata)
            
        except Exception as e:
            self.log_signal.emit(f"[ERROR] Exception saat generate metadata: {e}")
            self.finished_signal.emit({})

class UploadWorker(QThread):
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)
    
    def __init__(self, clips: list, platforms: list, metadata_dict: dict):
        super().__init__()
        self.clips = clips
        self.platforms = platforms
        self.metadata_dict = metadata_dict
        self.is_cancelled = False
        
    def run(self):
        from core.uploader import DummyUploader, YouTubeUploader, TikTokUploader, InstagramUploader
        from datetime import datetime, timedelta, timezone
        
        total_tasks = len(self.clips) * len(self.platforms)
        completed = 0
        
        # Instantiate uploaders
        uploaders = []
        for p in self.platforms:
            if p == "YouTube Shorts":
                uploaders.append(YouTubeUploader())
            elif p == "TikTok":
                uploaders.append(TikTokUploader())
            elif p == "Instagram Reels":
                uploaders.append(InstagramUploader())
            else:
                uploaders.append(DummyUploader(p))
                
        from core.config import config
        interval_hours = getattr(config, "upload_interval", 0.0)
        
        # Base time in utc+7 (gmt+7) for Asia/Jakarta (Based on my location :)
        utc7_time = timezone(timedelta(hours=7))
        base_time = datetime.now(utc7_time) + timedelta(minutes=30)
            
        for idx, clip in enumerate(self.clips):
            if self.is_cancelled:
                break
                
            clip_meta = self.metadata_dict.get(clip, {})
            clip_name = os.path.basename(clip)
            
            if interval_hours > 0:
                # Add interval for each subsequent clip
                publish_time = base_time + timedelta(hours=interval_hours * idx)
                clip_meta["publish_at"] = publish_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            for uploader in uploaders:
                if self.is_cancelled:
                    break
                    
                self.status_signal.emit(f"🚀 Mengunggah {clip_name} ke {uploader.platform_name}...")
                self.log_signal.emit(f"[UPLOAD] Memulai upload {clip_name} ke {uploader.platform_name}...")
                
                try:
                    def upload_event_hook(kind, data):
                        if kind == "log":
                            self.log_signal.emit(str(data))
                            
                    result = uploader.upload(clip, clip_meta, event_hook=upload_event_hook)
                    if result.success:
                        self.log_signal.emit(f"[UPLOAD] ✅ Sukses upload ke {uploader.platform_name}: {result.url}")
                    else:
                        self.log_signal.emit(f"[UPLOAD] ❌ Gagal upload ke {uploader.platform_name}: {result.error_msg}")
                except Exception as e:
                    self.log_signal.emit(f"[UPLOAD] ❌ Error Exception ke {uploader.platform_name}: {e}")
                    
                completed += 1
                progress = int((completed / total_tasks) * 100)
                self.progress_signal.emit(progress)
                
                # Sleep delay between uploads to avoid rate limiting
                time.sleep(2.0)
                
        # Clean up uploaders
        for uploader in uploaders:
            if hasattr(uploader, 'close'):
                try:
                    uploader.close()
                except Exception as e:
                    self.log_signal.emit(f"[UPLOAD] Error closing {uploader.platform_name}: {e}")

        if self.is_cancelled:
            self.status_signal.emit("⚠️ Dibatalkan")
        else:
            self.status_signal.emit("✅ Selesai")
        self.finished_signal.emit(True)

class UploaderWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.output_dir = "clips"
        self.worker = None
        self.upload_worker = None
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

        # Top Bar: Project Selector
        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("📂 Pilih Project / Klip Tersimpan:"))
        
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(300)
        project_layout.addWidget(self.project_combo)
        
        self.btn_refresh_projects = QPushButton("🔄 Muat Ulang")
        self.btn_refresh_projects.clicked.connect(self.load_projects)
        project_layout.addWidget(self.btn_refresh_projects)
        
        self.btn_load_project = QPushButton("📥 Buka Project")
        self.btn_load_project.setProperty("class", "primary")
        self.btn_load_project.clicked.connect(self.on_open_project)
        project_layout.addWidget(self.btn_load_project)
        
        project_layout.addStretch()
        layout.addLayout(project_layout)

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
        
        grid.addWidget(QLabel("Konteks Tambahan (AI):"), 3, 0)
        self.context_input = QLineEdit()
        self.context_input.setPlaceholderText("Contoh: Windah basudara mengagetkan penonton tapi malah kaget sendiri.")
        grid.addWidget(self.context_input, 3, 1)
        
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
        
        self.chk_youtube.setChecked(config.upload_youtube)
        self.chk_tiktok.setChecked(config.upload_tiktok)
        self.chk_instagram.setChecked(config.upload_instagram)
        
        self.chk_youtube.toggled.connect(self.on_upload_config_changed)
        self.chk_tiktok.toggled.connect(self.on_upload_config_changed)
        self.chk_instagram.toggled.connect(self.on_upload_config_changed)
        
        chk_layout.addWidget(self.chk_youtube)
        chk_layout.addWidget(self.chk_tiktok)
        chk_layout.addWidget(self.chk_instagram)
        chk_layout.addStretch()
        
        upload_layout.addLayout(chk_layout)
        
        # Interval setting
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interval Jadwal Publish (Jam):"))
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0, 720) # 0 to 30 days
        self.interval_spin.setSingleStep(0.5)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setValue(config.upload_interval)
        self.interval_spin.valueChanged.connect(self.on_upload_config_changed)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        upload_layout.addLayout(interval_layout)
        
        self.btn_upload = QPushButton("📤 Upload Video Tercentang")
        self.btn_upload.setProperty("class", "primary")
        self.btn_upload.setStyleSheet("padding: 10px; font-weight: bold;")
        self.btn_upload.clicked.connect(self.on_upload_clicked)
        upload_layout.addWidget(self.btn_upload)
        
        self.upload_progress = QProgressBar()
        self.upload_progress.setValue(0)
        self.upload_progress.setVisible(False)
        upload_layout.addWidget(self.upload_progress)
        
        self.upload_status_label = QLabel("")
        self.upload_status_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.upload_status_label.setVisible(False)
        upload_layout.addWidget(self.upload_status_label)
        
        right_layout.addWidget(upload_group)
        
        content_layout.addLayout(right_layout, 1)
        layout.addLayout(content_layout)
        
        self.details_panel.setEnabled(False)
        self.current_clip_path = None
        
        self.load_projects()

    def load_projects(self):
        self.project_combo.clear()
        if not os.path.exists(config.output_dir):
            return
            
        projects = []
        for item in os.listdir(config.output_dir):
            item_path = os.path.join(config.output_dir, item)
            if os.path.isdir(item_path):
                preview_file = os.path.join(item_path, "preview.json")
                if os.path.exists(preview_file):
                    projects.append(item)
                    
        # Sort newest first based on directory modification time
        projects.sort(key=lambda x: os.path.getmtime(os.path.join(config.output_dir, x)), reverse=True)
        
        for p in projects:
            self.project_combo.addItem(p, os.path.join(config.output_dir, p))

    def on_open_project(self):
        project_dir = self.project_combo.currentData()
        if not project_dir:
            QMessageBox.warning(self, "Pilih Project", "Tidak ada project yang dipilih.")
            return
            
        import glob
        import re
        clip_files = glob.glob(os.path.join(project_dir, "*.mp4"))
        
        # Filter to only match exactly clip_<number>.mp4
        clip_files = [f for f in clip_files if re.match(r'^(clip_\d+|merged)\.mp4$', os.path.basename(f))]
        
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
            
        clip_files.sort(key=natural_sort_key)
        
        outputs = []
        for cf in clip_files:
            outputs.append({
                "name": os.path.basename(cf),
                "path": cf,
                "size": os.path.getsize(cf)
            })
            
        self.update_outputs(outputs, project_dir)
        from gui.globals import signals
        signals.log_message.emit(f"[INFO] Membuka project: {os.path.basename(project_dir)} ({len(outputs)} klip).")

    def on_upload_config_changed(self):
        config.upload_youtube = self.chk_youtube.isChecked()
        config.upload_tiktok = self.chk_tiktok.isChecked()
        config.upload_instagram = self.chk_instagram.isChecked()
        config.upload_interval = self.interval_spin.value()
        config.save_to_file()

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
                import os
                basename = os.path.basename(path)
                idx = basename.replace("clip_", "").replace(".mp4", "")
                meta_path = os.path.join(output_dir, f"metadata_{idx}.json")
                if os.path.exists(meta_path):
                    from core.utils import read_json
                    saved_meta = read_json(meta_path)
                    if saved_meta:
                        self.clip_metadata[path].update(saved_meta)

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
            
        self.clip_metadata[self.current_clip_path].update({
            "title": self.title_input.text(),
            "description": self.desc_input.toPlainText(),
            "tags": self.tags_input.text()
        })
        
        import os
        from core.utils import write_json
        basename = os.path.basename(self.current_clip_path)
        idx = basename.replace("clip_", "").replace(".mp4", "")
        output_dir = os.path.dirname(self.current_clip_path)
        meta_path = os.path.join(output_dir, f"metadata_{idx}.json")
        write_json(meta_path, self.clip_metadata[self.current_clip_path], indent=2)
            
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
        
        user_context = self.context_input.text().strip()
        self.worker = AIGenerateMetadataWorker(self.current_clip_path, user_context)
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
            combined_tags = metadata["tags"]
            if config.yt_tags:
                combined_tags = f"{config.yt_tags} {combined_tags}".strip()
            self.tags_input.setText(combined_tags)
        
        if "highlight" in metadata and self.current_clip_path:
            self.clip_metadata[self.current_clip_path]["highlight"] = metadata["highlight"]
            
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
        
        self.btn_upload.setEnabled(False)
        self.upload_progress.setVisible(True)
        self.upload_progress.setValue(0)
        self.upload_status_label.setVisible(True)
        self.upload_status_label.setText("⏳ Memulai antrean upload...")
        
        self.upload_worker = UploadWorker(selected_clips, platforms, self.clip_metadata)
        self.upload_worker.progress_signal.connect(self.upload_progress.setValue)
        self.upload_worker.status_signal.connect(self.upload_status_label.setText)
        self.upload_worker.log_signal.connect(signals.log_message.emit)
        self.upload_worker.finished_signal.connect(self.on_upload_finished)
        self.upload_worker.start()

    def on_upload_finished(self, success: bool):
        self.btn_upload.setEnabled(True)
        QMessageBox.information(self, "Upload Selesai", "Proses Auto Upload telah selesai. Cek log untuk melihat hasil per platform.")
