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
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    # Set Qt Attributes for Linux high DPI and rendering stability
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Cliptzy Desktop")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

