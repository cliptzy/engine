"""
Auto Upload & Distribution Widget prepared for YouTube Shorts, TikTok, and Instagram Reels workflow.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QWidget,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt

class AutoUploadWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.init_ui()
        self.load_from_config()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header Title & Description
        header_layout = QVBoxLayout()
        title_label = QLabel("🚀 Auto Upload & Multi-Platform Distribution")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #818cf8;")

        desc_label = QLabel("Integrasi alur kerja publikasi otomatis klip video hasil generator ke berbagai platform media sosial.")
        desc_label.setProperty("class", "muted")

        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        layout.addLayout(header_layout)

        # Tabs for Platforms
        tabs = QTabWidget()

        # Tab 1: YouTube Shorts
        yt_tab = QWidget()
        yt_layout = QVBoxLayout(yt_tab)
        yt_layout.setContentsMargins(12, 12, 12, 12)

        yt_box = QGroupBox("YouTube Data API v3 Settings")
        yt_grid = QGridLayout(yt_box)

        yt_grid.addWidget(QLabel("Client ID (OAuth 2.0):"), 0, 0)
        self.yt_client_id_input = QLineEdit()
        yt_grid.addWidget(self.yt_client_id_input, 0, 1)

        yt_grid.addWidget(QLabel("Client Secret:"), 1, 0)
        self.yt_client_secret_input = QLineEdit()
        yt_grid.addWidget(self.yt_client_secret_input, 1, 1)

        yt_grid.addWidget(QLabel("Default Visibility:"), 2, 0)
        self.yt_visibility_combo = QComboBox()
        self.yt_visibility_combo.addItems(["Public", "Unlisted", "Private"])
        yt_grid.addWidget(self.yt_visibility_combo, 2, 1)

        yt_grid.addWidget(QLabel("Default Hashtags:"), 3, 0)
        self.yt_tags_input = QLineEdit()
        self.yt_tags_input.setPlaceholderText("#Shorts #Viral #Cliptzy")
        yt_grid.addWidget(self.yt_tags_input, 3, 1)

        yt_layout.addWidget(yt_box)
        
        self.yt_auto_check = QCheckBox("Otomatis Upload ke YouTube Shorts begitu klip selesai diproses")
        yt_layout.addWidget(self.yt_auto_check)
        yt_layout.addStretch()

        tabs.addTab(yt_tab, "🔴 YouTube Shorts")

        # Tab 2: TikTok
        tt_tab = QWidget()
        tt_layout = QVBoxLayout(tt_tab)
        tt_layout.setContentsMargins(12, 12, 12, 12)

        tt_box = QGroupBox("TikTok Content Posting API Settings")
        tt_grid = QGridLayout(tt_box)

        tt_grid.addWidget(QLabel("Open API Access Token / Session:"), 0, 0)
        self.tt_session_input = QLineEdit()
        tt_grid.addWidget(self.tt_session_input, 0, 1)

        tt_grid.addWidget(QLabel("Privasi Posting:"), 1, 0)
        self.tt_privacy_combo = QComboBox()
        self.tt_privacy_combo.addItems(["Public (Semua Orang)", "Friends (Teman)", "Private (Hanya Saya)"])
        tt_grid.addWidget(self.tt_privacy_combo, 1, 1)

        tt_grid.addWidget(QLabel("Default Caption:"), 2, 0)
        self.tt_caption_input = QLineEdit()
        self.tt_caption_input.setPlaceholderText("Cuplikan seru hari ini! #fyp #viral")
        tt_grid.addWidget(self.tt_caption_input, 2, 1)

        tt_layout.addWidget(tt_box)

        self.tt_auto_check = QCheckBox("Otomatis Upload ke TikTok begitu klip selesai diproses")
        tt_layout.addWidget(self.tt_auto_check)
        tt_layout.addStretch()

        tabs.addTab(tt_tab, "🎵 TikTok")

        # Tab 3: Instagram Reels
        ig_tab = QWidget()
        ig_layout = QVBoxLayout(ig_tab)
        ig_layout.setContentsMargins(12, 12, 12, 12)

        ig_box = QGroupBox("Instagram Graph API Settings")
        ig_grid = QGridLayout(ig_box)

        ig_grid.addWidget(QLabel("Instagram Business Account ID:"), 0, 0)
        self.ig_business_id_input = QLineEdit()
        ig_grid.addWidget(self.ig_business_id_input, 0, 1)

        ig_grid.addWidget(QLabel("User Access Token:"), 1, 0)
        self.ig_access_token_input = QLineEdit()
        ig_grid.addWidget(self.ig_access_token_input, 1, 1)

        ig_grid.addWidget(QLabel("Default Caption:"), 2, 0)
        self.ig_caption_input = QLineEdit()
        self.ig_caption_input.setPlaceholderText("Best moment clip #reels #instagram")
        ig_grid.addWidget(self.ig_caption_input, 2, 1)

        ig_layout.addWidget(ig_box)

        self.ig_auto_check = QCheckBox("Otomatis Upload ke Instagram Reels begitu klip selesai diproses")
        ig_layout.addWidget(self.ig_auto_check)
        ig_layout.addStretch()

        tabs.addTab(ig_tab, "📸 Instagram Reels")

        layout.addWidget(tabs)

        # Save Settings Button
        save_btn = QPushButton("💾 Simpan Pengaturan Distribution")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self.on_save_settings)
        layout.addWidget(save_btn)

    def load_from_config(self):
        from core.config import config
        self.yt_client_id_input.setText(config.yt_client_id)
        self.yt_client_secret_input.setText(config.yt_client_secret)
        self.yt_visibility_combo.setCurrentText(config.yt_visibility)
        self.yt_tags_input.setText(config.yt_tags)
        self.yt_auto_check.setChecked(config.yt_auto_upload)
        
        self.tt_session_input.setText(config.tt_session)
        self.tt_privacy_combo.setCurrentText(config.tt_privacy)
        self.tt_caption_input.setText(config.tt_caption)
        self.tt_auto_check.setChecked(config.tt_auto_upload)
        
        self.ig_business_id_input.setText(config.ig_business_id)
        self.ig_access_token_input.setText(config.ig_access_token)
        self.ig_caption_input.setText(config.ig_caption)
        self.ig_auto_check.setChecked(config.ig_auto_upload)

    def on_save_settings(self):
        from core.config import config
        from gui.globals import signals
        
        config.yt_client_id = self.yt_client_id_input.text()
        config.yt_client_secret = self.yt_client_secret_input.text()
        config.yt_visibility = self.yt_visibility_combo.currentText()
        config.yt_tags = self.yt_tags_input.text()
        config.yt_auto_upload = self.yt_auto_check.isChecked()
        
        config.tt_session = self.tt_session_input.text()
        config.tt_privacy = self.tt_privacy_combo.currentText()
        config.tt_caption = self.tt_caption_input.text()
        config.tt_auto_upload = self.tt_auto_check.isChecked()
        
        config.ig_business_id = self.ig_business_id_input.text()
        config.ig_access_token = self.ig_access_token_input.text()
        config.ig_caption = self.ig_caption_input.text()
        config.ig_auto_upload = self.ig_auto_check.isChecked()
        
        if config.save_to_file():
            signals.log_message.emit("[INFO] Pengaturan distribusi Auto Upload berhasil disimpan!")
        else:
            signals.log_message.emit("[ERROR] Gagal menyimpan pengaturan Auto Upload.")

