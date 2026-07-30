"""
Widget for entering YouTube URL and triggering metadata/scan preview.
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QPushButton, QApplication, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
from core import controller

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

        self.import_cookies_btn = QPushButton("🔑 Import Cookies")
        self.import_cookies_btn.clicked.connect(self.on_upload_cookies)

        self.fetch_btn = QPushButton("🔍 Load Video")
        self.fetch_btn.setProperty("class", "primary")
        self.fetch_btn.clicked.connect(self.on_fetch_clicked)

        layout.addWidget(self.url_input)
        layout.addWidget(self.import_cookies_btn)
        layout.addWidget(self.fetch_btn)

    def on_upload_cookies(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File Cookies Netscape", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                controller.import_cookies(file_path)
                QMessageBox.information(self, "Berhasil", "File cookies.txt berhasil diimpor!")
            except Exception as e:
                QMessageBox.critical(self, "Error Cookies", f"Gagal mengimpor cookies: {e}")

    def on_fetch_clicked(self):
        url = self.url_input.text().strip()
        if url:
            self.fetch_requested.emit(url)

    def set_loading(self, loading: bool):
        self.fetch_btn.setEnabled(not loading)
        if loading:
            self.fetch_btn.setText("Loading...")
        else:
            self.fetch_btn.setText("🔍 Load Video")
