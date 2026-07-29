"""
Widget for configuring clipping parameters, subtitles, aspect ratio, fonts, and assets.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QCheckBox, QSpinBox, QPushButton, QFileDialog, QMessageBox, QLineEdit
)
from core import controller, config

from PyQt6.QtCore import pyqtSignal

class SettingsWidget(QFrame):
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
        grid.addWidget(self.subtitle_check, 1, 0, 1, 2)

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

        self.btn_lock_delay = QPushButton("🔓")
        self.btn_lock_delay.setToolTip("Kunci/Buka Kunci nilai Subtitle Delay agar tidak berubah secara tidak disengaja")
        self.btn_lock_delay.setCheckable(True)
        self.btn_lock_delay.setFixedWidth(36)
        self.btn_lock_delay.toggled.connect(self.on_lock_delay_toggled)

        self.btn_test_sub = QPushButton("👁️ Test Delay")
        self.btn_test_sub.setToolTip("Hasilkan sampel video 10 detik untuk menguji sinkronisasi subtitle delay")
        self.btn_test_sub.clicked.connect(self.test_subtitle_requested.emit)

        delay_layout.addWidget(self.delay_spin, 1)
        delay_layout.addWidget(self.btn_lock_delay)
        delay_layout.addWidget(self.btn_test_sub)
        grid.addLayout(delay_layout, 3, 1)


        grid.addWidget(QLabel("Padding Klip (Detik):"), 3, 2)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 30)
        self.padding_spin.setValue(10)
        grid.addWidget(self.padding_spin, 3, 3)

        layout.addLayout(grid)

        # AI Settings Layout
        ai_title = QLabel("🤖 Pengaturan AI Highlights")
        ai_title.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        layout.addWidget(ai_title)

        ai_grid = QGridLayout()
        ai_grid.setHorizontalSpacing(16)
        ai_grid.setVerticalSpacing(10)
        
        ai_grid.addWidget(QLabel("Provider AI:"), 0, 0)
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItem("Local Ollama (Offline / Local)", "ollama")
        self.ai_provider_combo.addItem("Google Gemini API (Online)", "gemini")
        self.ai_provider_combo.addItem("OpenAI GPT API (Online)", "openai")
        self.ai_provider_combo.currentIndexChanged.connect(self.on_ai_provider_changed)
        ai_grid.addWidget(self.ai_provider_combo, 0, 1)

        self.ai_key_label = QLabel("Ollama Host:")
        self.ai_key_input = QLineEdit("http://localhost:11434")
        ai_grid.addWidget(self.ai_key_label, 0, 2)
        ai_grid.addWidget(self.ai_key_input, 0, 3)

        ai_grid.addWidget(QLabel("Model Name:"), 1, 0)
        self.ai_model_input = QLineEdit("llama3")
        self.ai_model_input.setPlaceholderText("misal: llama3, gemini-1.5-flash, gpt-4o-mini")
        ai_grid.addWidget(self.ai_model_input, 1, 1)

        self.btn_save_ai = QPushButton("💾 Simpan Pengaturan AI")
        self.btn_save_ai.setProperty("class", "primary")
        self.btn_save_ai.clicked.connect(self.save_ai_config)
        ai_grid.addWidget(self.btn_save_ai, 1, 3)

        layout.addLayout(ai_grid)


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

    def load_from_config(self):
        # Crop combo
        crop_idx = self.crop_combo.findData(config.output_ratio)
        if crop_idx >= 0:
            self.crop_combo.setCurrentIndex(crop_idx)

        # Ratio combo
        ratio_idx = self.ratio_combo.findData(config.output_ratio)
        if ratio_idx >= 0:
            self.ratio_combo.setCurrentIndex(ratio_idx)

        self.subtitle_check.setChecked(config.use_subtitle)
        
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

        self.on_subtitle_toggled(config.use_subtitle)
        
        # Load AI config
        provider = getattr(config, "ai_provider", "ollama")
        idx = self.ai_provider_combo.findData(provider)
        if idx >= 0:
            self.ai_provider_combo.setCurrentIndex(idx)
        else:
            self.on_ai_provider_changed(0)

    def on_subtitle_toggled(self, checked: bool):
        self.whisper_combo.setEnabled(checked)
        self.font_combo.setEnabled(checked)
        self.location_combo.setEnabled(checked)
        self.btn_lock_delay.setEnabled(checked)
        if not self.btn_lock_delay.isChecked():
            self.delay_spin.setEnabled(checked)

    def on_lock_delay_toggled(self, locked: bool):
        self.delay_spin.setEnabled(not locked and self.subtitle_check.isChecked())
        if locked:
            self.btn_lock_delay.setText("🔒")
            self.btn_lock_delay.setStyleSheet("background-color: #312e81; color: #a5b4fc;")
        else:
            self.btn_lock_delay.setText("🔓")
            self.btn_lock_delay.setStyleSheet("")

    def on_ai_provider_changed(self, idx: int):
        provider = self.ai_provider_combo.currentData()
        if provider == "ollama":
            self.ai_key_label.setText("Ollama Host:")
            self.ai_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.ai_key_input.setText(config.ollama_host or "http://localhost:11434")
            self.ai_model_input.setText(config.ollama_model or "llama3")
        elif provider == "gemini":
            self.ai_key_label.setText("Gemini API Key:")
            self.ai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.ai_key_input.setText(config.gemini_key or "")
            self.ai_key_input.setPlaceholderText("Masukkan Gemini API Key")
            self.ai_model_input.setText(config.gemini_model or "gemini-1.5-flash")
        elif provider == "openai":
            self.ai_key_label.setText("OpenAI API Key:")
            self.ai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.ai_key_input.setText(config.openai_key or "")
            self.ai_key_input.setPlaceholderText("sk-...")
            self.ai_model_input.setText(config.openai_model or "gpt-4o-mini")

    def save_ai_config(self):
        provider = self.ai_provider_combo.currentData()
        val = self.ai_key_input.text().strip()
        model_val = self.ai_model_input.text().strip()

        config.ai_provider = provider
        if provider == "ollama":
            config.ollama_host = val
            config.ollama_model = model_val
        elif provider == "gemini":
            config.gemini_key = val
            config.gemini_model = model_val
        elif provider == "openai":
            config.openai_key = val
            config.openai_model = model_val

        config.save_to_file("config.json")
        QMessageBox.information(self, "Berhasil", "Pengaturan AI berhasil disimpan!")

    def get_settings_payload(self) -> dict:
        return {

            "crop": self.crop_combo.currentData(),
            "ratio": self.ratio_combo.currentData(),
            "subtitle": self.subtitle_check.isChecked(),
            "whisper_model": self.whisper_combo.currentData(),
            "subtitle_font": self.font_combo.currentData(),
            "subtitle_location": self.location_combo.currentData(),
            "subtitle_delay": self.delay_spin.value(),
            "padding": self.padding_spin.value(),
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
