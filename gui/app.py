"""
Desktop GUI Entry Point for Cliptzy application.
"""

import sys
import os

# Ensure application root directory is in sys.path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Linux / Ubuntu Wayland rendering & button clickability compatibility fixes
if sys.platform.startswith("linux"):
    # Force Xwayland (xcb) by default on Linux to prevent Wayland subsurface QVideoWidget hit-test freezes and visual glitches
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"
    os.environ.setdefault("QSG_RENDER_LOOP", "basic")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow
from gui.login_dialog import LoginDialog
from core.supabase_sync import supabase_sync
from core.config import config
from core.logger import log

def main():
    # Set Qt Attributes for Linux high DPI and rendering stability
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Cliptzy Desktop")
    
    # Load environment variables
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv(os.path.join(app_dir, ".env"))
    except ImportError:
        log.warning("python-dotenv tidak terinstal. Pastikan environment variables sudah diatur.")

    # Initialize Supabase
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY", "")
    
    if not supabase_url or not supabase_key:
        QMessageBox.critical(None, "Error", "Konfigurasi Supabase tidak ditemukan (SUPABASE_URL dan SUPABASE_KEY). Periksa file .env Anda.")
        sys.exit(1)
        
    supabase_sync.initialize(supabase_url, supabase_key)
    
    if supabase_sync.client is None:
        QMessageBox.critical(None, "Error", "Gagal melakukan inisialisasi Supabase client. Pastikan package 'supabase' sudah terinstal.")
        sys.exit(1)
        
    # Show Login Dialog only if session was not restored
    if supabase_sync.user is None:
        login_dialog = LoginDialog()
        if login_dialog.exec() != 1:  # 1 is QDialog.DialogCode.Accepted
            sys.exit(0)
        
    # Define files that should be synced when the app closes
    import os
    os.makedirs("cred", exist_ok=True)
    files_to_sync = ["cred/youtube_token.json"]
    if config.tt_session: files_to_sync.append(config.tt_session)
    if config.cookies_file: files_to_sync.append(config.cookies_file)
    
    window = MainWindow()
    window.show()
    
    # Run the application event loop
    ret = app.exec()
    
    # Sync config up before completely exiting
    log.info("Aplikasi ditutup, melakukan sync up konfigurasi terakhir ke database...")
    config.load_from_file()
    supabase_sync.sync_config_up(config.to_dict())
    
    # Sync storage files up
    log.info("Melakukan sync up file kredensial ke storage...")
    for f in set(files_to_sync):
        if f and os.path.exists(f):
            filename = os.path.basename(f)
            supabase_sync.upload_file(f, filename)
    
    sys.exit(ret)

if __name__ == "__main__":
    main()

