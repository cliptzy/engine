"""
Widget for configuring clipping parameters, subtitles, aspect ratio, fonts, and assets.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QCheckBox, QSpinBox, QPushButton, QFileDialog, QMessageBox, QLineEdit
)
from core import controller, config

from PyQt6.QtCore import pyqtSignal

class ClipConfigWidget(QFrame):
    test_subtitle_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.init_ui()
        self.load_from_config()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header Title
        title_label = QLabel("⚙️ Pengaturan Klip & Subtitle")
        title_label.setProperty("class", "section-header")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        # Row 0: Crop Mode & Aspect Ratio Preset
        grid.addWidget(QLabel("Mode Crop Video:"), 0, 0)
        self.crop_combo = QComboBox()
        self.crop_combo.addItem("Default (Center Crop)", "default")
        self.crop_combo.addItem("Split Left (Top: Center, Bottom: Left Facecam)", "split_left")
        self.crop_combo.addItem("Split Right (Top: Center, Bottom: Right Facecam)", "split_right")
        self.crop_combo.addItem("Full (Fit Screen & Blurred BG)", "full")
        grid.addWidget(self.crop_combo, 0, 1)

        grid.addWidget(QLabel("Rasio Output:"), 0, 2)
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItem("9:16 (Shorts / Reels / TikTok)", "9:16")
        self.ratio_combo.addItem("1:1 (Square Feed)", "1:1")
        self.ratio_combo.addItem("16:9 (Landscape YouTube)", "16:9")
        self.ratio_combo.addItem("Original Video", "original")
        grid.addWidget(self.ratio_combo, 0, 3)

        # Row 1: Subtitle Enable & Whisper Model
        self.subtitle_check = QCheckBox("Aktifkan Auto Subtitle (Faster-Whisper)")
        self.subtitle_check.toggled.connect(self.on_subtitle_toggled)
        self.highlight_check = QCheckBox("Burn Teks Highlight AI")
        
        row1_box = QHBoxLayout()
        row1_box.addWidget(self.subtitle_check)
        row1_box.addWidget(self.highlight_check)
        grid.addLayout(row1_box, 1, 0, 1, 2)

        grid.addWidget(QLabel("Model Whisper:"), 1, 2)
        self.whisper_combo = QComboBox()
        for model in ["tiny", "base", "small", "medium", "large-v3"]:
            self.whisper_combo.addItem(f"{model} (Faster-Whisper)", model)
        grid.addWidget(self.whisper_combo, 1, 3)

        # Row 2: Subtitle Font & Location
        grid.addWidget(QLabel("Font Subtitle:"), 2, 0)
        self.font_combo = QComboBox()
        for font in controller.get_available_fonts():
            self.font_combo.addItem(font, font)
        grid.addWidget(self.font_combo, 2, 1)

        grid.addWidget(QLabel("Lokasi Subtitle:"), 2, 2)
        self.location_combo = QComboBox()
        self.location_combo.addItem("Bawah (Bottom)", "bottom")
        self.location_combo.addItem("Tengah (Center)", "center")
        grid.addWidget(self.location_combo, 2, 3)

        # Row 3: Subtitle Delay & Padding
        grid.addWidget(QLabel("Subtitle Delay (ms):"), 3, 0)
        delay_layout = QHBoxLayout()
        delay_layout.setSpacing(8)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(-5000, 5000)
        self.delay_spin.setSingleStep(100)

        self.btn_test_sub = QPushButton("👁️ Test Delay")
        self.btn_test_sub.setToolTip("Hasilkan sampel video 10 detik untuk menguji sinkronisasi subtitle delay")
        self.btn_test_sub.clicked.connect(self.test_subtitle_requested.emit)

        delay_layout.addWidget(self.delay_spin, 1)
        delay_layout.addWidget(self.btn_test_sub)
        grid.addLayout(delay_layout, 3, 1)


        grid.addWidget(QLabel("Padding Klip (Detik):"), 3, 2)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 30)
        self.padding_spin.setValue(10)
        grid.addWidget(self.padding_spin, 3, 3)
        
        # Row 4: Font Size & Color
        grid.addWidget(QLabel("Ukuran Font:"), 4, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(20, 150)
        self.font_size_spin.setValue(60)
        grid.addWidget(self.font_size_spin, 4, 1)

        grid.addWidget(QLabel("Warna Teks:"), 4, 2)
        self.color_combo = QComboBox()
        self.color_combo.addItem("Kuning", "&H0000FFFF")
        self.color_combo.addItem("Putih", "&H00FFFFFF")
        self.color_combo.addItem("Hijau", "&H0000FF00")
        self.color_combo.addItem("Merah", "&H000000FF")
        self.color_combo.addItem("Biru", "&H00FF0000")
        grid.addWidget(self.color_combo, 4, 3)

        # Row 5: Background & Animation
        grid.addWidget(QLabel("Background:"), 5, 0)
        self.bg_combo = QComboBox()
        self.bg_combo.addItem("Kotak Hitam", 3)
        self.bg_combo.addItem("Outline Hitam", 1)
        grid.addWidget(self.bg_combo, 5, 1)

        grid.addWidget(QLabel("Efek Animasi:"), 5, 2)
        self.anim_combo = QComboBox()
        self.anim_combo.addItem("Tanpa Animasi", "none")
        self.anim_combo.addItem("Scale Up", "scale")
        grid.addWidget(self.anim_combo, 5, 3)

        # Row 6: Max Words per Subtitle & Hardware Acceleration
        grid.addWidget(QLabel("Maks Kata / Muncul:"), 6, 0)
        self.max_words_spin = QSpinBox()
        self.max_words_spin.setRange(1, 15)
        self.max_words_spin.setValue(3)
        grid.addWidget(self.max_words_spin, 6, 1)

        grid.addWidget(QLabel("Akselerasi Hardware:"), 6, 2)
        self.hw_combo = QComboBox()
        self.hw_combo.addItem("CPU (Lambat, Stabil)", "cpu")
        self.hw_combo.addItem("Mac (VideoToolbox)", "mac")
        self.hw_combo.addItem("AMD (AMF)", "amd")
        self.hw_combo.addItem("NVIDIA (NVENC)", "nvidia")
        self.hw_combo.addItem("Intel (QuickSync)", "intel")
        grid.addWidget(self.hw_combo, 6, 3)
        
        self._detect_hw_accel()

        layout.addLayout(grid)

        # Assets & Cookies Buttons
        assets_layout = QHBoxLayout()
        assets_layout.setSpacing(10)

        self.btn_cookies = QPushButton("🔑 Upload Cookies.txt")
        self.btn_cookies.clicked.connect(self.on_upload_cookies)

        self.btn_intro = QPushButton("🎬 Set Video Intro")
        self.btn_intro.clicked.connect(self.on_set_intro)

        self.btn_outro = QPushButton("🎬 Set Video Outro")
        self.btn_outro.clicked.connect(self.on_set_outro)

        assets_layout.addWidget(self.btn_cookies)
        assets_layout.addWidget(self.btn_intro)
        assets_layout.addWidget(self.btn_outro)
        layout.addLayout(assets_layout)

        # Global Lock and Save
        self.btn_lock_all = QPushButton("🔒 Kunci dan Simpan Pengaturan")
        self.btn_lock_all.setProperty("class", "primary")
        self.btn_lock_all.setCheckable(True)
        self.btn_lock_all.toggled.connect(self.on_lock_all_toggled)
        layout.addWidget(self.btn_lock_all)

    def _detect_hw_accel(self):
        import subprocess
        supported = ["cpu"]
        try:
            res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                out = res.stdout.lower()
                if "h264_nvenc" in out:
                    supported.append("nvidia")
                if "h264_amf" in out:
                    supported.append("amd")
                if "h264_qsv" in out:
                    supported.append("intel")
                if "h264_videotoolbox" in out:
                    supported.append("mac")
        except Exception:
            pass

        i = 0
        while i < self.hw_combo.count():
            data = self.hw_combo.itemData(i)
            if data not in supported:
                self.hw_combo.removeItem(i)
            else:
                i += 1

    def load_from_config(self):
        # Crop combo
        crop_idx = self.crop_combo.findData(config.crop_mode)
        if crop_idx >= 0:
            self.crop_combo.setCurrentIndex(crop_idx)

        # Ratio combo
        ratio_idx = self.ratio_combo.findData(config.output_ratio)
        if ratio_idx >= 0:
            self.ratio_combo.setCurrentIndex(ratio_idx)

        self.subtitle_check.setChecked(config.use_subtitle)
        self.highlight_check.setChecked(config.use_highlight)
        
        whisper_idx = self.whisper_combo.findData(config.whisper_model)
        if whisper_idx >= 0:
            self.whisper_combo.setCurrentIndex(whisper_idx)

        font_idx = self.font_combo.findData(config.subtitle_font)
        if font_idx >= 0:
            self.font_combo.setCurrentIndex(font_idx)

        loc_idx = self.location_combo.findData(config.subtitle_location)
        if loc_idx >= 0:
            self.location_combo.setCurrentIndex(loc_idx)

        self.delay_spin.setValue(int(config.subtitle_delay * 1000))
        self.padding_spin.setValue(config.padding)
        
        self.font_size_spin.setValue(config.subtitle_font_size)
        color_idx = self.color_combo.findData(config.subtitle_color)
        if color_idx >= 0:
            self.color_combo.setCurrentIndex(color_idx)
            
        bg_idx = self.bg_combo.findData(config.subtitle_border_style)
        if bg_idx >= 0:
            self.bg_combo.setCurrentIndex(bg_idx)
            
        anim_idx = self.anim_combo.findData(config.subtitle_animation)
        if anim_idx >= 0:
            self.anim_combo.setCurrentIndex(anim_idx)
            
        self.max_words_spin.setValue(config.subtitle_max_words)

        hw_idx = self.hw_combo.findData(config.hw_accel)
        if hw_idx >= 0:
            self.hw_combo.setCurrentIndex(hw_idx)

        self.on_subtitle_toggled(config.use_subtitle)
        
        if config.ui_locked:
            self.btn_lock_all.setChecked(True)
        


    def on_subtitle_toggled(self, checked: bool):
        self.whisper_combo.setEnabled(checked)
        self.font_combo.setEnabled(checked)
        self.location_combo.setEnabled(checked)
        self.font_size_spin.setEnabled(checked)
        self.color_combo.setEnabled(checked)
        self.bg_combo.setEnabled(checked)
        self.anim_combo.setEnabled(checked)
        self.max_words_spin.setEnabled(checked)
        self.delay_spin.setEnabled(checked)
        self.btn_test_sub.setEnabled(checked)

    def on_lock_all_toggled(self, locked: bool):
        self.crop_combo.setEnabled(not locked)
        self.ratio_combo.setEnabled(not locked)
        self.subtitle_check.setEnabled(not locked)
        self.highlight_check.setEnabled(not locked)
        self.padding_spin.setEnabled(not locked)
        self.hw_combo.setEnabled(not locked)
        
        if not locked:
            self.on_subtitle_toggled(self.subtitle_check.isChecked())
            self.btn_lock_all.setText("🔒 Kunci dan Simpan Pengaturan")
            self.btn_lock_all.setStyleSheet("")
        else:
            self.whisper_combo.setEnabled(False)
            self.font_combo.setEnabled(False)
            self.location_combo.setEnabled(False)
            self.font_size_spin.setEnabled(False)
            self.color_combo.setEnabled(False)
            self.bg_combo.setEnabled(False)
            self.anim_combo.setEnabled(False)
            self.max_words_spin.setEnabled(False)
            self.delay_spin.setEnabled(False)
            self.btn_test_sub.setEnabled(False)
            
            self.btn_lock_all.setText("🔓 Buka Kunci Pengaturan")
            self.btn_lock_all.setStyleSheet("background-color: #312e81; color: #a5b4fc;")
            
        payload = self.get_settings_payload()
        config_data = {
            "crop_mode": payload["crop"],
            "output_ratio": payload["ratio"],
            "use_subtitle": payload["subtitle"],
            "use_highlight": payload.get("use_highlight", False),
            "whisper_model": payload["whisper_model"],
            "subtitle_font": payload["subtitle_font"],
            "subtitle_location": payload["subtitle_location"],
            "subtitle_delay": payload["subtitle_delay"] / 1000.0,
            "subtitle_font_size": payload["subtitle_font_size"],
            "subtitle_color": payload["subtitle_color"],
            "subtitle_bg_color": payload["subtitle_bg_color"],
            "subtitle_border_style": payload["subtitle_border_style"],
            "subtitle_animation": payload["subtitle_animation"],
            "subtitle_max_words": payload["subtitle_max_words"],
            "padding": payload["padding"],
            "hw_accel": payload["hw_accel"],
            "ui_locked": locked
        }
        config.update_from_dict(config_data)
        if config.save_to_file():
            from gui.globals import signals
            state = "terkunci" if locked else "terbuka"
            signals.log_message.emit(f"[INFO] Pengaturan berhasil disimpan secara permanen (Status: {state}).")
        else:
            from gui.globals import signals
            signals.log_message.emit("[ERROR] Gagal menyimpan pengaturan ke config.json.")



    def get_settings_payload(self) -> dict:
        return {

            "crop": self.crop_combo.currentData(),
            "ratio": self.ratio_combo.currentData(),
            "subtitle": self.subtitle_check.isChecked(),
            "use_highlight": self.highlight_check.isChecked(),
            "whisper_model": self.whisper_combo.currentData(),
            "subtitle_font": self.font_combo.currentData(),
            "subtitle_location": self.location_combo.currentData(),
            "subtitle_delay": self.delay_spin.value(),
            "subtitle_font_size": self.font_size_spin.value(),
            "subtitle_color": self.color_combo.currentData(),
            "subtitle_bg_color": "&H80000000",
            "subtitle_border_style": self.bg_combo.currentData(),
            "subtitle_animation": self.anim_combo.currentData(),
            "subtitle_max_words": self.max_words_spin.value(),
            "padding": self.padding_spin.value(),
            "hw_accel": self.hw_combo.currentData(),
        }

    def on_upload_cookies(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File Cookies Netscape", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                controller.import_cookies(file_path)
                QMessageBox.information(self, "Berhasil", "File cookies.txt berhasil diimpor!")
            except Exception as e:
                QMessageBox.critical(self, "Error Cookies", f"Gagal mengimpor cookies: {e}")

    def on_set_intro(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Video Intro", "", "Video Files (*.mp4 *.mkv *.mov);;All Files (*)")
        if file_path:
            try:
                dest = controller.set_intro_video(file_path)
                QMessageBox.information(self, "Berhasil", f"Video intro berhasil diset:\n{dest}")
            except Exception as e:
                QMessageBox.critical(self, "Error Intro", f"Gagal mengeset intro: {e}")

    def on_set_outro(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Video Outro", "", "Video Files (*.mp4 *.mkv *.mov);;All Files (*)")
        if file_path:
            try:
                dest = controller.set_outro_video(file_path)
                QMessageBox.information(self, "Berhasil", f"Video outro berhasil diset:\n{dest}")
            except Exception as e:
                QMessageBox.critical(self, "Error Outro", f"Gagal mengeset outro: {e}")
