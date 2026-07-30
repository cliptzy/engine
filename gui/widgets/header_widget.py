"""
Header widget displaying application title, system status badges, and quick actions.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, QTimer
from core import config
from core.utils import is_ffmpeg_available, is_deno_available
import subprocess

try:
    import psutil
except ImportError:
    psutil = None

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

class StatsWorker(QThread):
    stats_updated = pyqtSignal(list)

    def run(self):
        import sys
        import re
        import subprocess

        stats_text = []
        if psutil:
            try:
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory()
                mem_used = mem.used / (1024**3)
                mem_total = mem.total / (1024**3)
                stats_text.append(f"CPU: {cpu}%")
                stats_text.append(f"RAM: {mem_used:.1f}/{mem_total:.1f}GB")
            except Exception:
                stats_text.append("CPU/RAM: N/A")
        else:
            stats_text.append("CPU/RAM: N/A")

        gpu_found = False
        if sys.platform == "darwin":
            try:
                # Use class filter to be faster
                res = subprocess.run(["ioreg", "-l", "-c", "IOAccelerator"], capture_output=True, text=True)
                if res.returncode == 0:
                    match = re.search(r'"GPU Activity\(%\)"=(\d+)', res.stdout)
                    if not match:
                        match = re.search(r'"Device Utilization %"=(\d+)', res.stdout)
                    if match:
                        stats_text.append(f"GPU: {match.group(1)}%")
                        gpu_found = True
            except Exception:
                pass
                
        if not gpu_found:
            try:
                res = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True)
                if res.returncode == 0:
                    gpu_util = res.stdout.strip().split('\n')[0]
                    stats_text.append(f"GPU: {gpu_util}%")
            except Exception:
                pass
                
        self.stats_updated.emit(stats_text)


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

        # Status Badges Layout
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)
        
        # System Stats
        self.stats_badge = QLabel()
        self.stats_badge.setStyleSheet("background-color: #334155; color: #cbd5e1; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;")
        
        # Dependencies Status
        self.ffmpeg_badge = QLabel()
        self.deno_badge = QLabel()
        self.cookie_badge = QLabel()

        status_layout.addWidget(self.stats_badge)
        status_layout.addWidget(self.ffmpeg_badge)
        status_layout.addWidget(self.deno_badge)
        status_layout.addWidget(self.cookie_badge)

        layout.addLayout(status_layout)

        # Initial Updates
        self.update_ffmpeg_status()
        self.update_deno_status()
        self.update_cookie_status()

        # Timer for stats update
        self.stats_worker = StatsWorker(self)
        self.stats_worker.stats_updated.connect(self.on_stats_updated)
        
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.request_system_stats)
        self.stats_timer.start(2500)  # Update every 2.5 seconds
        
        self.request_system_stats()

    def request_system_stats(self):
        if not self.stats_worker.isRunning():
            self.stats_worker.start()
            
    def on_stats_updated(self, stats_text):
        self.stats_badge.setText(" | ".join(stats_text))

    def update_deno_status(self):
        if is_deno_available():
            self.deno_badge.setText("Deno: Ready")
            self.deno_badge.setStyleSheet("background-color: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;")
        else:
            self.deno_badge.setText("Deno: Missing")
            self.deno_badge.setStyleSheet("background-color: #7f1d1d; color: #f87171; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;")

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
