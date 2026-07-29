"""
Widget for entering YouTube URL and triggering metadata/scan preview.
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QPushButton, QApplication
from PyQt6.QtCore import pyqtSignal

class VideoInputWidget(QFrame):
    fetch_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Tempel URL YouTube di sini (watch / shorts / youtu.be)...")
        self.url_input.returnPressed.connect(self.on_fetch_clicked)

        self.paste_btn = QPushButton("📋 Paste")
        self.paste_btn.clicked.connect(self.on_paste_clicked)

        self.clear_btn = QPushButton("✕ Clear")
        self.clear_btn.clicked.connect(self.url_input.clear)

        self.fetch_btn = QPushButton("🔍 Load Video")
        self.fetch_btn.setProperty("class", "primary")
        self.fetch_btn.clicked.connect(self.on_fetch_clicked)

        layout.addWidget(self.url_input)
        layout.addWidget(self.paste_btn)
        layout.addWidget(self.clear_btn)
        layout.addWidget(self.fetch_btn)

    def on_paste_clicked(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_input.setText(text)

    def on_fetch_clicked(self):
        url = self.url_input.text().strip()
        if url:
            self.fetch_requested.emit(url)

    def set_loading(self, loading: bool):
        self.fetch_btn.setEnabled(not loading)
        self.paste_btn.setEnabled(not loading)
        self.clear_btn.setEnabled(not loading)
        if loading:
            self.fetch_btn.setText("Loading...")
        else:
            self.fetch_btn.setText("🔍 Load Video")
