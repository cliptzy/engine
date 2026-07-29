"""
Header widget displaying application title, system status badges, and quick actions.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt
from core import is_ffmpeg_available, config

class HeaderWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerWidget")
        self.setStyleSheet("""
            QFrame#headerWidget {
                background-color: #1e293b;
                border-bottom: 1px solid #334155;
                border-radius: 0px;
            }
        """)
        self.init_ui()


    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # App Logo & Title
        title_label = QLabel("🎬 Cliptzy Desktop")
        title_label.setProperty("class", "title")
        title_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #818cf8;")

        version_label = QLabel("v2.0 Standalone")
        version_label.setStyleSheet("background-color: #312e81; color: #a5b4fc; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;")

        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addStretch()

        # Status Badges
        self.ffmpeg_badge = QLabel()
        self.update_ffmpeg_status()

        self.cookie_badge = QLabel()
        self.update_cookie_status()

        layout.addWidget(self.ffmpeg_badge)
        layout.addWidget(self.cookie_badge)

    def update_ffmpeg_status(self):
        if is_ffmpeg_available():
            self.ffmpeg_badge.setText("FFmpeg: Ready")
            self.ffmpeg_badge.setStyleSheet("background-color: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;")
        else:
            self.ffmpeg_badge.setText("FFmpeg: Missing")
            self.ffmpeg_badge.setStyleSheet("background-color: #7f1d1d; color: #f87171; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;")

    def update_cookie_status(self):
        import os
        if config.cookies_file and os.path.exists(config.cookies_file):
            self.cookie_badge.setText("Cookies: Active")
            self.cookie_badge.setStyleSheet("background-color: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;")
        else:
            self.cookie_badge.setText("Cookies: None")
            self.cookie_badge.setStyleSheet("background-color: #334155; color: #94a3b8; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;")
