from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from core.supabase_sync import supabase_sync
import os

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cliptzy - Login")
        self.setFixedSize(350, 160)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Sinkronisasi konfigurasi aktif.\nSilakan login menggunakan Google.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addSpacing(15)
        
        self.btn_login = QPushButton("🌐 Login with Google")
        self.btn_login.setStyleSheet("font-weight: bold; padding: 10px;")
        self.btn_login.clicked.connect(self.do_login)
        layout.addWidget(self.btn_login)
        
        self.btn_cancel = QPushButton("Batal (Keluar Aplikasi)")
        self.btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancel)

    def do_login(self):
        self.btn_login.setEnabled(False)
        self.btn_login.setText("⏳ Membuka Browser...")
        
        # We need to process events so the UI updates before the blocking HTTP server starts
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        success = supabase_sync.login_with_google()
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Login Gagal", "Gagal melakukan login. Pastikan Anda menyetujui akses di browser dan URL redirect (localhost:54321) sudah didaftarkan di Supabase.")
            self.btn_login.setEnabled(True)
            self.btn_login.setText("🌐 Login with Google")
