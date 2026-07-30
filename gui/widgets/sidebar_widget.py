"""
Sidebar navigation widget for Cliptzy desktop app.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

class SidebarWidget(QFrame):
    page_changed = pyqtSignal(int)
    clear_cache_requested = pyqtSignal()
    restore_config_requested = pyqtSignal()
    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self.setStyleSheet("""
            QFrame#sidebarWidget {
                background-color: #0f172a;
                border-right: 1px solid #334155;
                min-width: 220px;
                max-width: 220px;
            }
            QPushButton.nav-btn {
                background-color: transparent;
                color: #94a3b8;
                text-align: left;
                padding: 12px 16px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }
            QPushButton.nav-btn:hover {
                background-color: #1e293b;
                color: #f8fafc;
            }
            QPushButton.nav-btn.active {
                background-color: #312e81;
                color: #818cf8;
                border-left: 4px solid #6366f1;
            }
            QPushButton.danger-action {
                background-color: #7f1d1d;
                color: #fca5a5;
                text-align: left;
                padding: 10px 14px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton.danger-action:hover {
                background-color: #991b1b;
                color: #ffffff;
            }
        """)
        self.nav_buttons = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        # Brand / Menu Label
        menu_title = QLabel("MAIN MENU")
        menu_title.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-bottom: 8px;")
        layout.addWidget(menu_title)

        # Nav Button 1: YouTube Clipper
        self.btn_clipper = QPushButton("✂️ YouTube Clipper")
        self.btn_clipper.setProperty("class", "nav-btn active")
        self.btn_clipper.clicked.connect(lambda: self.switch_page(0))
        layout.addWidget(self.btn_clipper)
        self.nav_buttons.append(self.btn_clipper)

        # Nav Button 2: Creator Channel Hub
        self.btn_creator_hub = QPushButton("🎮 Creator Hub")
        self.btn_creator_hub.setProperty("class", "nav-btn")
        self.btn_creator_hub.clicked.connect(lambda: self.switch_page(1))
        layout.addWidget(self.btn_creator_hub)
        self.nav_buttons.append(self.btn_creator_hub)

        # Nav Button 3: Auto Upload & Distribution
        self.btn_autoupload = QPushButton("🚀 Auto Upload Platform")
        self.btn_autoupload.setProperty("class", "nav-btn")
        self.btn_autoupload.clicked.connect(lambda: self.switch_page(2))
        layout.addWidget(self.btn_autoupload)
        self.nav_buttons.append(self.btn_autoupload)

        # Nav Button 4: Settings & Assets
        self.btn_settings = QPushButton("⚙️ Pengaturan App")
        self.btn_settings.setProperty("class", "nav-btn")
        self.btn_settings.clicked.connect(lambda: self.switch_page(3))
        layout.addWidget(self.btn_settings)
        self.nav_buttons.append(self.btn_settings)




        layout.addStretch()

        # Action: Restore Config
        self.btn_restore_config = QPushButton("☁️ Restore Config dari Cloud")
        self.btn_restore_config.setProperty("class", "nav-btn")
        self.btn_restore_config.setStyleSheet("color: #38bdf8;") # Light blue for distinction
        self.btn_restore_config.clicked.connect(self.restore_config_requested.emit)
        layout.addWidget(self.btn_restore_config)

        # Action: Logout
        self.btn_logout = QPushButton("🚪 Logout Akun")
        self.btn_logout.setProperty("class", "nav-btn")
        self.btn_logout.setStyleSheet("color: #fbbf24;") # Yellow
        self.btn_logout.clicked.connect(self.logout_requested.emit)
        layout.addWidget(self.btn_logout)

        # Action: Clear Cache & Generated Clips
        self.btn_clear_cache = QPushButton("🧹 Bersihkan Cache & Klip")
        self.btn_clear_cache.setProperty("class", "danger-action")
        self.btn_clear_cache.clicked.connect(self.clear_cache_requested.emit)
        layout.addWidget(self.btn_clear_cache)

    def switch_page(self, index: int):
        for idx, btn in enumerate(self.nav_buttons):
            if idx == index:
                btn.setProperty("class", "nav-btn active")
            else:
                btn.setProperty("class", "nav-btn")
            btn.setStyle(btn.style())
        self.page_changed.emit(index)
