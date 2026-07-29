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
        yt_grid.addWidget(QLineEdit(), 0, 1)

        yt_grid.addWidget(QLabel("Client Secret:"), 1, 0)
        yt_grid.addWidget(QLineEdit(), 1, 1)

        yt_grid.addWidget(QLabel("Default Visibility:"), 2, 0)
        yt_vis = QComboBox()
        yt_vis.addItems(["Public", "Unlisted", "Private"])
        yt_grid.addWidget(yt_vis, 2, 1)

        yt_grid.addWidget(QLabel("Default Hashtags:"), 3, 0)
        yt_tags = QLineEdit()
        yt_tags.setPlaceholderText("#Shorts #Viral #Cliptzy")
        yt_grid.addWidget(yt_tags, 3, 1)

        yt_layout.addWidget(yt_box)
        
        yt_auto_check = QCheckBox("Otomatis Upload ke YouTube Shorts begitu klip selesai diproses")
        yt_layout.addWidget(yt_auto_check)
        yt_layout.addStretch()

        tabs.addTab(yt_tab, "🔴 YouTube Shorts")

        # Tab 2: TikTok
        tt_tab = QWidget()
        tt_layout = QVBoxLayout(tt_tab)
        tt_layout.setContentsMargins(12, 12, 12, 12)

        tt_box = QGroupBox("TikTok Content Posting API Settings")
        tt_grid = QGridLayout(tt_box)

        tt_grid.addWidget(QLabel("Open API Access Token / Session:"), 0, 0)
        tt_grid.addWidget(QLineEdit(), 0, 1)

        tt_grid.addWidget(QLabel("Privasi Posting:"), 1, 0)
        tt_priv = QComboBox()
        tt_priv.addItems(["Public (Semua Orang)", "Friends (Teman)", "Private (Hanya Saya)"])
        tt_grid.addWidget(tt_priv, 1, 1)

        tt_grid.addWidget(QLabel("Default Caption:"), 2, 0)
        tt_caption = QLineEdit()
        tt_caption.setPlaceholderText("Cuplikan seru hari ini! #fyp #viral")
        tt_grid.addWidget(tt_caption, 2, 1)

        tt_layout.addWidget(tt_box)

        tt_auto_check = QCheckBox("Otomatis Upload ke TikTok begitu klip selesai diproses")
        tt_layout.addWidget(tt_auto_check)
        tt_layout.addStretch()

        tabs.addTab(tt_tab, "🎵 TikTok")

        # Tab 3: Instagram Reels
        ig_tab = QWidget()
        ig_layout = QVBoxLayout(ig_tab)
        ig_layout.setContentsMargins(12, 12, 12, 12)

        ig_box = QGroupBox("Instagram Graph API Settings")
        ig_grid = QGridLayout(ig_box)

        ig_grid.addWidget(QLabel("Instagram Business Account ID:"), 0, 0)
        ig_grid.addWidget(QLineEdit(), 0, 1)

        ig_grid.addWidget(QLabel("User Access Token:"), 1, 0)
        ig_grid.addWidget(QLineEdit(), 1, 1)

        ig_grid.addWidget(QLabel("Default Caption:"), 2, 0)
        ig_caption = QLineEdit()
        ig_caption.setPlaceholderText("Best moment clip #reels #instagram")
        ig_grid.addWidget(ig_caption, 2, 1)

        ig_layout.addWidget(ig_box)

        ig_auto_check = QCheckBox("Otomatis Upload ke Instagram Reels begitu klip selesai diproses")
        ig_layout.addWidget(ig_auto_check)
        ig_layout.addStretch()

        tabs.addTab(ig_tab, "📸 Instagram Reels")

        layout.addWidget(tabs)

        # Save Settings Button
        save_btn = QPushButton("💾 Simpan Pengaturan Distribution")
        save_btn.setProperty("class", "primary")
        layout.addWidget(save_btn)
