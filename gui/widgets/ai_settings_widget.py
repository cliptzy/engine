"""
Widget for configuring AI Highlights settings.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QGridLayout, QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox, QPlainTextEdit
)
from core import config
from core.ai_detector import DEFAULT_PROMPT_TEMPLATE

class AiSettingsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.init_ui()
        self.load_from_config()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        ai_title = QLabel("🤖 Pengaturan AI Highlights")
        ai_title.setStyleSheet("font-weight: bold; font-size: 13px;")
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

        self.ai_base_url_label = QLabel("Base URL:")
        self.ai_base_url_input = QLineEdit("")
        self.ai_base_url_input.setPlaceholderText("Opsional, untuk 3rd party OpenAI API")
        ai_grid.addWidget(self.ai_base_url_label, 2, 0)
        ai_grid.addWidget(self.ai_base_url_input, 2, 1)

        self.btn_save_ai = QPushButton("💾 Simpan Pengaturan AI")
        self.btn_save_ai.setProperty("class", "primary")
        self.btn_save_ai.clicked.connect(self.save_ai_config)
        ai_grid.addWidget(self.btn_save_ai, 1, 3)

        layout.addLayout(ai_grid)

        layout.addWidget(QLabel("AI Prompt Template:"))
        self.ai_prompt_input = QPlainTextEdit()
        self.ai_prompt_input.setPlaceholderText("Biarkan kosong untuk menggunakan prompt bawaan. Gunakan {transcript_text} untuk menyisipkan transkrip.")
        self.ai_prompt_input.setFixedHeight(120)
        layout.addWidget(self.ai_prompt_input)

    def load_from_config(self):
        provider = getattr(config, "ai_provider", "ollama")
        idx = self.ai_provider_combo.findData(provider)
        if idx >= 0:
            self.ai_provider_combo.setCurrentIndex(idx)
        else:
            self.on_ai_provider_changed(0)

        self.ai_prompt_input.setPlainText(config.ai_prompt or DEFAULT_PROMPT_TEMPLATE)

    def on_ai_provider_changed(self, idx: int):
        provider = self.ai_provider_combo.currentData()
        if provider == "ollama":
            self.ai_key_label.setText("Ollama Host:")
            self.ai_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.ai_key_input.setText(config.ollama_host or "http://localhost:11434")
            self.ai_model_input.setText(config.ollama_model or "llama3")
            self.ai_base_url_label.setVisible(False)
            self.ai_base_url_input.setVisible(False)
        elif provider == "gemini":
            self.ai_key_label.setText("Gemini API Key:")
            self.ai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.ai_key_input.setText(config.gemini_key or "")
            self.ai_key_input.setPlaceholderText("Masukkan Gemini API Key")
            self.ai_model_input.setText(config.gemini_model or "gemini-1.5-flash")
            self.ai_base_url_label.setVisible(False)
            self.ai_base_url_input.setVisible(False)
        elif provider == "openai":
            self.ai_key_label.setText("OpenAI API Key:")
            self.ai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.ai_key_input.setText(config.openai_key or "")
            self.ai_key_input.setPlaceholderText("sk-...")
            self.ai_model_input.setText(config.openai_model or "gpt-4o-mini")
            self.ai_base_url_label.setVisible(True)
            self.ai_base_url_input.setVisible(True)
            self.ai_base_url_input.setText(getattr(config, "openai_base_url", "") or "")

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
            config.openai_base_url = self.ai_base_url_input.text().strip()

        config.ai_prompt = self.ai_prompt_input.toPlainText()

        config.save_to_file("config.json")
        QMessageBox.information(self, "Berhasil", "Pengaturan AI berhasil disimpan!")
