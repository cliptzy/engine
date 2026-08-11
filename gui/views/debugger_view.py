import os
import flet as ft
import asyncio
from core.logger import log
from core.utils import get_app_root
from gui.ui_utils import show_snackbar

class DebuggerView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.spacing = 20
        self.expand = True

        self.file_picker = ft.FilePicker()
        self.page_ref.services.append(self.file_picker)

        self.input_file = ""
        self.input_text = ft.TextField(
            label="Video Input (Untuk Showcase)",
            value="",
            read_only=True,
            expand=True
        )

        self.btn_browse = ft.Button(
            "Browse",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self.on_browse_clicked
        )

        self.btn_test = ft.Button(
            "Test Semua Video Effect (Showcase)",
            icon=ft.Icons.PLAY_CIRCLE_FILL,
            on_click=self.on_test_clicked,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
        )

        self.btn_debug_analyzers = ft.Button(
            "Debug Semua Analyzer (Text/Voice/Visual)",
            icon=ft.Icons.BUG_REPORT,
            on_click=self.on_debug_analyzers_clicked,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
        )

        self.progress_ring = ft.ProgressRing(visible=False)

        self.controls = [
            ft.Text("Debugger & Testing", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Gunakan alat di bawah ini untuk menguji konfigurasi Video Effect secara keseluruhan.", color=ft.Colors.WHITE_70),
            ft.Row([self.input_text, self.btn_browse], alignment=ft.MainAxisAlignment.START),
            ft.Row([self.btn_test, self.btn_debug_analyzers, self.progress_ring], alignment=ft.MainAxisAlignment.START)
        ]

    async def on_browse_clicked(self, e):
        # flet 0.23 async file picker support
        files = await self.file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["mp4", "mkv", "mov", "avi"]
        )
        if files and len(files) > 0:
            self.input_file = files[0].path
            self.input_text.value = self.input_file
            self.btn_test.disabled = False
            self.btn_debug_analyzers.disabled = False
            self.update()

    def on_test_clicked(self, e):
        if not self.input_file or not os.path.exists(self.input_file):
            show_snackbar(self.page_ref, "Silakan pilih video input yang valid terlebih dahulu.")
            return

        self.btn_test.disabled = True
        self.btn_debug_analyzers.disabled = True
        self.progress_ring.visible = True
        self.update()

        output_file = os.path.join(get_app_root(), "video_effects_showcase.mp4")
        show_snackbar(self.page_ref, "Memulai pembuatan Video Effect Showcase. Silakan cek console log...")

        self.page_ref.run_task(self.run_showcase_task, output_file)

    def on_debug_analyzers_clicked(self, e):
        if not self.input_file or not os.path.exists(self.input_file):
            show_snackbar(self.page_ref, "Silakan pilih video input yang valid terlebih dahulu.")
            return

        self.btn_test.disabled = True
        self.btn_debug_analyzers.disabled = True
        self.progress_ring.visible = True
        self.update()

        output_file = os.path.join(get_app_root(), "analyzers_debug_overlay.mp4")
        show_snackbar(self.page_ref, "Memulai pembuatan Debug Overlay Analyzer. Silakan cek console log...")

        self.page_ref.run_task(self.run_debug_analyzers_task, output_file)

    async def run_showcase_task(self, output_file: str):
        from scripts.generate_ve_showcase import generate_ve_showcase

        try:
            success = await asyncio.to_thread(generate_ve_showcase, self.input_file, output_file)

            if success:
                show_snackbar(self.page_ref, f"Berhasil! Showcase disimpan di {output_file}")
            else:
                show_snackbar(self.page_ref, "Gagal membuat showcase. Cek log untuk detail.")
        except Exception as ex:
            log.error(f"Error running showcase script: {ex}")
            show_snackbar(self.page_ref, "Terjadi kesalahan sistem saat menjalankan showcase.")

        self.btn_test.disabled = False
        self.btn_debug_analyzers.disabled = False
        self.progress_ring.visible = False
        self.update()

    async def run_debug_analyzers_task(self, output_file: str):
        from scripts.generate_analyzer_debug import generate_analyzer_debug

        try:
            success = await asyncio.to_thread(generate_analyzer_debug, self.input_file, output_file)

            if success:
                show_snackbar(self.page_ref, f"Berhasil! Debug Video disimpan di {output_file}")
            else:
                show_snackbar(self.page_ref, "Gagal membuat video debug. Cek log untuk detail.")
        except Exception as ex:
            log.error(f"Error running analyzer debug script: {ex}")
            show_snackbar(self.page_ref, "Terjadi kesalahan sistem saat menjalankan analyzer debug.")

        self.btn_test.disabled = False
        self.btn_debug_analyzers.disabled = False
        self.progress_ring.visible = False
        self.update()
