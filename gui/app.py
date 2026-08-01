"""
Desktop GUI Entry Point for Cliptzy application.
"""

import sys
import os

if len(sys.argv) >= 3 and sys.argv[1] == "-m" and sys.argv[2] == "yt_dlp":
    import yt_dlp
    sys.argv = [sys.argv[0]] + sys.argv[3:]
    try:
        sys.exit(yt_dlp.main())
    except SystemExit as e:
        sys.exit(e.code)


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
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(app_dir, ".env"))
    except ImportError:
        log.warning("python-dotenv tidak terinstal. Pastikan environment variables sudah diatur.")

    # Initialize Supabase
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY", "")
    
    if not supabase_url or not supabase_key:
        try:
            from core._build_env import SUPABASE_URL, SUPABASE_SECRET_KEY
            supabase_url = supabase_url or SUPABASE_URL
            supabase_key = supabase_key or SUPABASE_SECRET_KEY
        except ImportError:
            pass
            
    if not supabase_url or not supabase_key:
        QMessageBox.critical(None, "Error", "Konfigurasi Supabase tidak ditemukan (SUPABASE_URL dan SUPABASE_KEY). Periksa file .env Anda atau kompilasi ulang.")
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
        
    # Create cred directory if it doesn't exist
    config.ensure_cred_dir()
    
    window = MainWindow()
    window.show()
    
    # Run the application event loop
    ret = app.exec()
    
    sys.exit(ret)

if __name__ == "__main__":
    main()

