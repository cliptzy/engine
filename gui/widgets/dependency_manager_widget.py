"""
Widget for installing and managing external dependencies (FFmpeg, Deno).
"""
import os
import sys
import zipfile
import urllib.request
import subprocess
import shutil
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class DependencyWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def run(self):
        import ssl
        try:
            # Bypass macOS SSL certificate verification errors globally for this thread
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass

        try:
            self.log_signal.emit("[INFO] Memulai proses instalasi dependensi secara otomatis...")
            app_root = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            bin_dir = os.path.join(app_root, "bin")
            os.makedirs(bin_dir, exist_ok=True)
            self.log_signal.emit(f"[INFO] Direktori bin: {bin_dir}")

            is_windows = sys.platform == "win32"
            is_linux = sys.platform.startswith("linux")
            is_mac = sys.platform == "darwin"

            # 1. Install Deno
            self.log_signal.emit("\n--- Instalasi Deno ---")
            deno_dest = os.path.join(bin_dir, "deno.exe" if is_windows else "deno")
            if is_windows:
                deno_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
            elif is_mac:
                deno_url = "https://github.com/denoland/deno/releases/latest/download/deno-aarch64-apple-darwin.zip"
            else:
                deno_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip"

            deno_zip = os.path.join(bin_dir, "deno.zip")
            self.log_signal.emit(f"Mengunduh Deno dari {deno_url}...")
            
            try:
                urllib.request.urlretrieve(deno_url, deno_zip)
                self.log_signal.emit("Berhasil mengunduh Deno. Mengekstrak...")
                with zipfile.ZipFile(deno_zip, 'r') as zip_ref:
                    zip_ref.extractall(bin_dir)
                os.remove(deno_zip)
                self.log_signal.emit("Deno berhasil diekstrak.")
                if not is_windows:
                    os.chmod(deno_dest, 0o755)
            except Exception as e:
                self.log_signal.emit(f"[ERROR] Gagal mengunduh Deno: {e}")

            # 2. Install FFmpeg
            self.log_signal.emit("\n--- Instalasi FFmpeg ---")
            if is_windows:
                ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                ffmpeg_zip = os.path.join(bin_dir, "ffmpeg.zip")
                self.log_signal.emit(f"Mengunduh FFmpeg dari {ffmpeg_url}...")
                try:
                    urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
                    self.log_signal.emit("Berhasil mengunduh FFmpeg. Mengekstrak...")
                    with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
                        for file_info in zip_ref.infolist():
                            if file_info.filename.endswith("ffmpeg.exe") or file_info.filename.endswith("ffprobe.exe"):
                                file_info.filename = os.path.basename(file_info.filename)
                                zip_ref.extract(file_info, bin_dir)
                    os.remove(ffmpeg_zip)
                    self.log_signal.emit("FFmpeg berhasil diekstrak.")
                except Exception as e:
                    self.log_signal.emit(f"[ERROR] Gagal mengunduh FFmpeg: {e}")
            elif is_linux:
                ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
                ffmpeg_tar = os.path.join(bin_dir, "ffmpeg.tar.xz")
                self.log_signal.emit(f"Mengunduh FFmpeg dari {ffmpeg_url}...")
                try:
                    urllib.request.urlretrieve(ffmpeg_url, ffmpeg_tar)
                    self.log_signal.emit("Berhasil mengunduh FFmpeg. Mengekstrak...")
                    subprocess.run(["tar", "-xf", ffmpeg_tar, "-C", bin_dir, "--strip-components=1", "--wildcards", "*/ffmpeg", "*/ffprobe"], check=True)
                    os.remove(ffmpeg_tar)
                    self.log_signal.emit("FFmpeg berhasil diekstrak.")
                except Exception as e:
                    self.log_signal.emit(f"[ERROR] Gagal mengunduh FFmpeg: {e}")
            elif is_mac:
                ffmpeg_url = "https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip"
                ffmpeg_zip = os.path.join(bin_dir, "ffmpeg.zip")
                self.log_signal.emit(f"Mengunduh FFmpeg dari {ffmpeg_url}...")
                try:
                    urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
                    self.log_signal.emit("Berhasil mengunduh FFmpeg. Mengekstrak...")
                    with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
                        zip_ref.extractall(bin_dir)
                    os.remove(ffmpeg_zip)
                    os.chmod(os.path.join(bin_dir, "ffmpeg"), 0o755)
                    self.log_signal.emit("FFmpeg berhasil diekstrak.")
                except Exception as e:
                    self.log_signal.emit(f"[ERROR] Gagal mengunduh FFmpeg: {e}")

            # Append bin_dir to PATH globally for current session
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
            
            self.log_signal.emit("\n[INFO] Proses instalasi selesai.")
            self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit(f"\n[FATAL ERROR] {e}")
            self.finished_signal.emit(False)


class DependencyManagerWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title_label = QLabel("📦 Pengelola Dependensi Sistem")
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title_label)

        desc_label = QLabel(
            "Unduh dan pasang dependensi yang diperlukan oleh aplikasi secara otomatis "
            "(FFmpeg untuk pemrosesan video, Deno untuk eksekusi skrip). Dependensi ini akan di-install di "
            "folder lokal aplikasi agar tidak mengganggu sistem bawaan Anda."
        )
        desc_label.setWordWrap(True)
        desc_label.setProperty("class", "muted")
        layout.addWidget(desc_label)

        btn_layout = QHBoxLayout()
        self.btn_install = QPushButton("⬇️ Install / Reinstall Dependencies")
        self.btn_install.setProperty("class", "primary")
        self.btn_install.clicked.connect(self.start_installation)
        btn_layout.addWidget(self.btn_install)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def start_installation(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Peringatan", "Proses instalasi sedang berjalan.")
            return

        self.btn_install.setEnabled(False)
        
        self.worker = DependencyWorker()
        from gui.globals import signals
        self.worker.log_signal.connect(signals.log_message.emit)
        self.worker.finished_signal.connect(self.on_installation_finished)
        self.worker.start()

    def on_installation_finished(self, success: bool):
        self.btn_install.setEnabled(True)
        if success:
            QMessageBox.information(self, "Berhasil", "Semua dependensi telah selesai diproses.")
        else:
            QMessageBox.critical(self, "Error", "Proses instalasi selesai dengan pesan kesalahan.")
