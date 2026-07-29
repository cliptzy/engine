"""
Main Window container for Cliptzy PyQt6 Desktop GUI Application.
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QScrollArea,
    QMessageBox, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QUrl

from gui.styles import DARK_STYLESHEET
from gui.utils import get_app_icon
from gui.widgets.header_widget import HeaderWidget
from gui.widgets.sidebar_widget import SidebarWidget
from gui.widgets.video_input_widget import VideoInputWidget
from gui.widgets.preview_widget import PreviewWidget
from gui.widgets.settings_widget import SettingsWidget
from gui.widgets.log_console_widget import LogConsoleWidget
from gui.widgets.media_player_widget import MediaPlayerWidget
from gui.widgets.auto_upload_widget import AutoUploadWidget
from gui.widgets.creator_hub_widget import CreatorHubWidget
from gui.workers import PreviewWorker, ScanWorker, ClipWorker, SubtitlePreviewWorker, AIScanWorker
from core import controller



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cliptzy Desktop Standalone")
        self.setWindowIcon(get_app_icon())
        self.resize(1150, 880)
        self.setMinimumSize(900, 650)
        self.setAcceptDrops(True)

        self.preview_worker = None
        self.scan_worker = None
        self.clip_worker = None

        self.init_ui()
        self.init_system_tray()
        self.setStyleSheet(DARK_STYLESHEET)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Header Widget (Flat Navbar)
        self.header_widget = HeaderWidget(central_widget)
        root_layout.addWidget(self.header_widget)

        # Main Body Layout (Sidebar + Stacked Page View)
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 2. Sidebar Navigation Widget
        self.sidebar_widget = SidebarWidget(central_widget)
        self.sidebar_widget.page_changed.connect(self.on_page_changed)
        self.sidebar_widget.clear_cache_requested.connect(self.on_clear_cache)
        body_layout.addWidget(self.sidebar_widget)

        # 3. Stacked View for Navigation Pages
        self.stacked_view = QStackedWidget(central_widget)

        # --- Page 0: YouTube Clipper Main Dashboard ---
        clipper_page = QWidget()
        clipper_layout = QVBoxLayout(clipper_page)
        clipper_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(clipper_page)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #0f172a; }")

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # Clipper Components
        self.input_widget = VideoInputWidget(scroll_content)
        self.input_widget.fetch_requested.connect(self.on_fetch_requested)
        content_layout.addWidget(self.input_widget)

        self.preview_widget = PreviewWidget(scroll_content)
        self.preview_widget.ai_scan_requested.connect(self.on_run_ai_scan)
        content_layout.addWidget(self.preview_widget)

        self.settings_widget = SettingsWidget(scroll_content)
        self.settings_widget.test_subtitle_requested.connect(self.on_test_subtitle_preview)
        content_layout.addWidget(self.settings_widget)

        self.log_widget = LogConsoleWidget(scroll_content)
        self.log_widget.start_requested.connect(self.on_start_clipping)
        self.log_widget.cancel_requested.connect(self.on_cancel_clipping)
        content_layout.addWidget(self.log_widget)

        self.player_widget = MediaPlayerWidget(scroll_content)
        content_layout.addWidget(self.player_widget)

        scroll_area.setWidget(scroll_content)
        clipper_layout.addWidget(scroll_area)
        self.stacked_view.addWidget(clipper_page)

        # --- Page 1: Creator Channel Hub ---
        self.creator_hub_widget = CreatorHubWidget(self.stacked_view)
        self.creator_hub_widget.video_selected_signal.connect(self.on_creator_video_selected)
        self.stacked_view.addWidget(self.creator_hub_widget)

        # --- Page 2: Auto Upload & Distribution View ---
        self.auto_upload_widget = AutoUploadWidget(self.stacked_view)
        self.stacked_view.addWidget(self.auto_upload_widget)

        # --- Page 3: Standalone Settings View ---
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        self.page_settings_widget = SettingsWidget(settings_page)
        settings_layout.addWidget(self.page_settings_widget)
        settings_layout.addStretch()
        self.stacked_view.addWidget(settings_page)





        body_layout.addWidget(self.stacked_view, 1)
        root_layout.addLayout(body_layout, 1)

    def init_system_tray(self):
        """Initializes System Tray Icon and Context Menu."""
        self.tray_icon = QSystemTrayIcon(get_app_icon(), self)
        self.tray_icon.setToolTip("Cliptzy Desktop Standalone")

        tray_menu = QMenu()
        show_action = tray_menu.addAction("🎬 Tampilkan Cliptzy")
        show_action.triggered.connect(self.show_and_activate)

        open_folder_action = tray_menu.addAction("📂 Buka Output Folder")
        open_folder_action.triggered.connect(self.player_widget.on_open_folder)

        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("✕ Keluar")
        quit_action.triggered.connect(self.close)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_and_activate(self):
        self.show()
        self.activateWindow()

    def notify_user(self, title: str, message: str, icon_type=QSystemTrayIcon.MessageIcon.Information):
        """Sends native desktop notification via System Tray."""
        if self.tray_icon and self.tray_icon.isSystemTrayAvailable():
            self.tray_icon.showMessage(title, message, icon_type, 5000)

    # --- Drag and Drop Handling ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext == ".txt":
                        try:
                            controller.import_cookies(file_path)
                            self.header_widget.update_cookie_status()
                            self.log_widget.append_log(f"[DRAG-DROP] Cookies berhasil diimpor: {file_path}")
                            QMessageBox.information(self, "Cookies Import", f"Berhasil mengimpor cookies:\n{file_path}")
                        except Exception as e:
                            QMessageBox.critical(self, "Error Cookies", str(e))
                    elif ext in [".mp4", ".mkv", ".mov"]:
                        reply = QMessageBox.question(
                            self,
                            "Import Video Media",
                            f"File video terdeteksi:\n{file_path}\n\nIngin jadikan sebagai Video Intro? (Pilih 'No' untuk Video Outro)",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            dest = controller.set_intro_video(file_path)
                            self.log_widget.append_log(f"[DRAG-DROP] Intro video diset: {dest}")
                        elif reply == QMessageBox.StandardButton.No:
                            dest = controller.set_outro_video(file_path)
                            self.log_widget.append_log(f"[DRAG-DROP] Outro video diset: {dest}")
        elif mime.hasText():
            text = mime.text().strip()
            if text.startswith("http"):
                self.input_widget.url_input.setText(text)
                self.on_fetch_requested(text)

    # --- Navigation & Control Events ---
    def on_page_changed(self, index: int):
        self.stacked_view.setCurrentIndex(index)

    def on_clear_cache(self):
        reply = QMessageBox.question(
            self,
            "Konfirmasi Hapus Cache",
            "Apakah Anda yakin ingin menghapus seluruh cache segmen (segments.json) dan file video klip hasil olahan di folder 'clips/'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                res = controller.clear_cache_and_clips()
                del_count = res.get("deleted_files", 0)
                del_mb = res.get("deleted_size_mb", 0.0)
                
                # Reset UI components
                self.player_widget.update_outputs([], "clips")
                self.log_widget.append_log(f"[INFO] Cache berhasil dibersihkan! {del_count} file terhapus ({del_mb} MB terbebaskan).")
                
                QMessageBox.information(
                    self,
                    "Cache Dibersihkan",
                    f"Berhasil membersihkan cache dan klip!\n{del_count} file terhapus ({del_mb} MB terbebaskan)."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error Hapus Cache", f"Gagal membersihkan cache: {e}")

    def on_fetch_requested(self, url: str):
        self.input_widget.set_loading(True)
        self.log_widget.append_log(f"[INFO] Memuat metadata untuk: {url}")

        # Worker 1: Preview Metadata
        self.preview_worker = PreviewWorker(url)
        self.preview_worker.finished_signal.connect(self.on_preview_loaded)
        self.preview_worker.error_signal.connect(self.on_fetch_error)
        self.preview_worker.start()

        # Worker 2: Scan Heatmap
        self.scan_worker = ScanWorker(url)
        self.scan_worker.finished_signal.connect(self.on_scan_completed)
        self.scan_worker.error_signal.connect(self.on_fetch_error)
        self.scan_worker.start()

    def on_preview_loaded(self, preview_data: dict):
        self.preview_widget.set_preview_data(preview_data)
        self.log_widget.append_log(f"[SUCCESS] Metadata berhasil dimuat: {preview_data.get('title')}")

    def on_scan_completed(self, scan_result: dict):
        self.input_widget.set_loading(False)
        self.preview_widget.set_scan_data(scan_result)
        self.log_widget.append_log(f"[SUCCESS] Heatmap scan selesai! {len(scan_result.get('segments', []))} segmen ditemukan.")

    def on_fetch_error(self, err_msg: str):
        self.input_widget.set_loading(False)
        self.log_widget.append_log(f"[ERROR] Gagal memuat video: {err_msg}")
        QMessageBox.critical(self, "Error Fetch Video", f"Gagal memuat informasi video:\n{err_msg}")

    def on_start_clipping(self):
        url = self.input_widget.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Peringatan", "Silakan masukkan URL YouTube terlebih dahulu.")
            return

        payload = self.settings_widget.get_settings_payload()
        payload["url"] = url

        mode = self.preview_widget.get_selected_mode()
        payload["mode"] = mode

        if mode in ["heatmap", "ai"]:
            segments = self.preview_widget.get_selected_segments()
            if not segments:
                QMessageBox.warning(self, "Peringatan", f"Pilih minimal 1 segmen {'AI Highlight' if mode=='ai' else 'heatmap'} untuk diproses.")
                return
            payload["segments"] = segments
        else:
            start_str, end_str = self.preview_widget.get_custom_range()
            if not start_str or not end_str:
                QMessageBox.warning(self, "Peringatan", "Masukkan Waktu Mulai dan Waktu Selesai untuk mode kustom.")
                return
            payload["start"] = start_str
            payload["end"] = end_str

        self.log_widget.set_processing(True)
        self.log_widget.append_log("[INFO] Memulai eksekusi pembuatan klip...")


        self.clip_worker = ClipWorker(payload)
        self.clip_worker.log_signal.connect(self.log_widget.append_log)
        self.clip_worker.stage_signal.connect(self.on_worker_stage)
        self.clip_worker.finished_signal.connect(self.on_clip_finished)
        self.clip_worker.error_signal.connect(self.on_clip_error)
        self.clip_worker.start()

    def on_worker_stage(self, stage_name: str, data: dict):
        if stage_name == "total_targets":
            self.log_widget.set_total_targets(data.get("total", 0))
        else:
            self.log_widget.update_stage(stage_name, data)

    def on_cancel_clipping(self):
        if self.clip_worker and self.clip_worker.isRunning():
            self.clip_worker.cancel()
            self.log_widget.append_log("[WARNING] Membatalkan proses...")

    def on_clip_finished(self, result: dict):
        self.log_widget.set_processing(False)
        outputs = result.get("outputs", [])
        output_dir = result.get("output_dir", "clips")
        
        self.log_widget.append_log(f"[SUCCESS] Pembuatan klip selesai! {len(outputs)} klip berhasil dibuat.")
        self.player_widget.update_outputs(outputs, output_dir)
        self.notify_user("Cliptzy - Clipping Selesai", f"Berhasil memproses {len(outputs)} video klip!", QSystemTrayIcon.MessageIcon.Information)
        QMessageBox.information(self, "Selesai", f"Berhasil memproses klip!\n{len(outputs)} video tersimpan di folder:\n{output_dir}")

    def on_clip_error(self, err_msg: str):
        self.log_widget.set_processing(False)
        self.log_widget.append_log(f"[ERROR] Gagal memproses klip: {err_msg}")
        self.notify_user("Cliptzy - Clipping Gagal", f"Error: {err_msg}", QSystemTrayIcon.MessageIcon.Warning)
        QMessageBox.critical(self, "Error Clipping", f"Gagal membuat klip:\n{err_msg}")

    def on_test_subtitle_preview(self):
        url = self.input_widget.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Peringatan", "Silakan masukkan URL YouTube terlebih dahulu untuk menguji subtitle.")
            return

        payload = self.settings_widget.get_settings_payload()
        payload["url"] = url
        payload["mode"] = self.preview_widget.get_selected_mode()
        if payload["mode"] == "heatmap":
            segments = self.preview_widget.get_selected_segments()
            if segments:
                payload["segments"] = segments

        self.log_widget.set_processing(True)
        self.log_widget.append_log(f"[PREVIEW] Menggenerate sampel video 10 detik untuk menguji Subtitle Delay: {payload.get('subtitle_delay')}ms...")

        self.sub_preview_worker = SubtitlePreviewWorker(payload)
        self.sub_preview_worker.log_signal.connect(self.log_widget.append_log)
        self.sub_preview_worker.stage_signal.connect(self.on_worker_stage)
        self.sub_preview_worker.finished_signal.connect(self.on_subtitle_preview_finished)
        self.sub_preview_worker.error_signal.connect(self.on_clip_error)
        self.sub_preview_worker.start()

    def on_subtitle_preview_finished(self, sample_path: str):
        self.log_widget.set_processing(False)
        self.log_widget.append_log(f"[SUCCESS] Sampel subtitle preview berhasil dibuat: {sample_path}")
        
        sample_item = [{
            "name": "👁️ Sample Subtitle Test (10s).mp4",
            "path": sample_path,
            "size": os.path.getsize(sample_path) if os.path.exists(sample_path) else 0
        }]
        output_dir = os.path.dirname(sample_path)
        self.player_widget.update_outputs(sample_item, output_dir)
        
        QMessageBox.information(
            self,
            "Preview Subtitle Siap",
            "Sampel video 10 detik dengan subtitle telah diputar di player video!\n\nPeriksa apakah animasi kata subtitle sudah pas dengan suara pembicara. Anda dapat mengubah nilai delay (ms) dan menekan 'Test Delay' kembali bila perlu."
        )

    def on_run_ai_scan(self, ai_config: dict):
        url = self.input_widget.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Peringatan", "Masukkan URL YouTube terlebih dahulu untuk menjalankan deteksi AI.")
            return

        self.preview_widget.set_ai_scanning(True)
        self.log_widget.set_processing(True)
        self.log_widget.append_log(f"[AI] Memulai ekstraksi audio & deteksi highlight AI via {ai_config.get('provider', 'ollama').upper()}...")

        self.ai_worker = AIScanWorker(url, ai_config)
        self.ai_worker.log_signal.connect(self.log_widget.append_log)
        self.ai_worker.stage_signal.connect(self.on_worker_stage)
        self.ai_worker.finished_signal.connect(self.on_ai_scan_completed)
        self.ai_worker.error_signal.connect(self.on_ai_scan_error)
        self.ai_worker.start()

    def on_ai_scan_completed(self, ai_result: dict):
        self.preview_widget.set_ai_scanning(False)
        self.log_widget.set_processing(False)
        self.preview_widget.set_ai_scan_data(ai_result)
        count = len(ai_result.get("segments", []))
        self.log_widget.append_log(f"[SUCCESS] AI Highlight Detection selesai! {count} momen menarik teridentifikasi.")
        QMessageBox.information(
            self,
            "AI Highlights Siap",
            f"Berhasil mendeteksi {count} momen menarik dari transkrip video!\n\nSilakan centang segmen AI yang ingin di-clip lalu klik 'MULAI PROSES KLIP'."
        )

    def on_ai_scan_error(self, err_msg: str):
        self.preview_widget.set_ai_scanning(False)
        self.log_widget.set_processing(False)
        self.log_widget.append_log(f"[ERROR] Gagal memproses AI Highlight Scan: {err_msg}")
        QMessageBox.critical(self, "Error AI Scan", f"Gagal mengirim/mendeteksi AI highlights:\n\n{err_msg}\n\nCatatan: Transkrip audio telah tersimpan. Anda dapat mencoba lagi tanpa transkripsi ulang setelah memeriksa API Key / Server AI.")

    def on_creator_video_selected(self, url: str):
        self.input_widget.url_input.setText(url)
        self.sidebar_widget.switch_page(0)
        self.log_widget.append_log(f"[CREATOR HUB] Memilih video dari katalog channel: {url}")
        self.on_fetch_requested(url)




