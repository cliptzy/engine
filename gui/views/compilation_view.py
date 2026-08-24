import asyncio
import os
from typing import List, Optional

import flet as ft

from core.config import config
from core.controller import controller
from core.logger import log
from core.use_cases.compile_video import CompilationItem
from gui.components.progress_indicator import ProgressIndicator
from gui.event_bus import event_bus


class CompilationItemControl(ft.Container):
    def __init__(
        self,
        item: CompilationItem,
        on_delete,
        on_move_up,
        on_move_down,
    ):
        super().__init__()
        self.item = item
        self.on_delete = on_delete
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down

        self.padding = ft.Padding(16, 12, 16, 12)
        self.border_radius = 8
        self.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
        self.animate_scale = ft.Animation(200, ft.AnimationCurve.EASE_OUT)
        
        def on_hover(e):
            e.control.scale = 1.02 if e.data == "true" else 1.0
            e.control.update()
            
        self.on_hover = on_hover

        self.number_text = ft.Text(
            f"#{self.item.number}",
            weight=ft.FontWeight.W_800,
            size=18,
            color=ft.Colors.PRIMARY,
        )

        self.file_name_text = ft.Text(
            os.path.basename(self.item.file_path),
            size=14,
            color=ft.Colors.ON_SURFACE_VARIANT,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
            tooltip=self.item.file_path,
        )

        self.moment_input = ft.TextField(
            value=self.item.moment_name,
            label="Nama Momen",
            hint_text="Contoh: Momen Paling Absurd",
            expand=True,
            dense=True,
            on_change=self._on_moment_change,
        )

        self.content = ft.Row(
            [
                ft.Container(
                    content=self.number_text,
                    width=40,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Column(
                    [
                        self.file_name_text,
                        self.moment_input,
                    ],
                    expand=True,
                    spacing=4,
                ),
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_UPWARD,
                            tooltip="Geser ke Atas",
                            on_click=lambda _: self.on_move_up(self),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ARROW_DOWNWARD,
                            tooltip="Geser ke Bawah",
                            on_click=lambda _: self.on_move_down(self),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.ERROR,
                            tooltip="Hapus Item",
                            on_click=lambda _: self.on_delete(self),
                        ),
                    ],
                    spacing=0,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _on_moment_change(self, e):
        self.item.moment_name = e.control.value

    def update_number(self, new_number: int):
        self.item.number = new_number
        self.number_text.value = f"#{new_number}"
        self.update()


class CompilationView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.expand = True
        self.padding = ft.Padding(24, 16, 24, 16)
        
        self.items: List[CompilationItem] = []
        self.item_controls: List[CompilationItemControl] = []
        self.is_processing = False
        self._cancel_flag = False

        # --- UI Components ---
        
        self.file_picker = ft.FilePicker()
        self.save_picker = ft.FilePicker()
        self.load_picker = ft.FilePicker()
        
        if hasattr(self._page, "services"):
            self._page.services.extend([self.file_picker, self.save_picker, self.load_picker])
        else:
            self._page.overlay.extend([self.file_picker, self.save_picker, self.load_picker])

        self.btn_add_files = ft.Button(
            content=ft.Row([ft.Icon(ft.Icons.ADD_TO_DRIVE), ft.Text("Tambah Video")]),
            on_click=self.on_add_files_click,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
        )

        self.btn_generate = ft.Button(
            content=ft.Row([ft.Icon(ft.Icons.PLAY_ARROW), ft.Text("Mulai Kompilasi")]),
            on_click=self.on_generate_click,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.DEEP_PURPLE_700,
                color=ft.Colors.WHITE,
                padding=ft.Padding(24, 16, 24, 16),
            ),
        )

        self.btn_cancel = ft.Button(
            content=ft.Row([ft.Icon(ft.Icons.CANCEL), ft.Text("Batalkan")]),
            on_click=self.on_cancel_click,
            visible=False,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.ERROR,
                color=ft.Colors.WHITE,
            ),
        )

        self.btn_save_preset = ft.Button(
            content=ft.Row([ft.Icon(ft.Icons.SAVE), ft.Text("Simpan Preset")]),
            on_click=self.on_save_preset_click,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        self.btn_load_preset = ft.Button(
            content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN), ft.Text("Muat Preset")]),
            on_click=self.on_load_preset_click,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

        self.list_container = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8)
        self.empty_text = ft.Text(
            "Belum ada video ditambahkan. Klik 'Tambah Video' untuk memulai.",
            color=ft.Colors.ON_SURFACE_VARIANT,
            italic=True,
            text_align=ft.TextAlign.CENTER,
        )

        # Settings Configuration
        self.dropdown_ordering = ft.Dropdown(
            label="Urutan Numbering",
            options=[
                ft.dropdown.Option("countdown", "Countdown (Misal: 5 ke 1)"),
                ft.dropdown.Option("countup", "Countup (Misal: 1 ke 5)"),
            ],
            value=config.compilation.ordering,
            on_select=self.on_ordering_change,
            width=250,
            dense=True,
        )

        self.toggle_tts = ft.Switch(
            label="Narasi TTS",
            value=config.compilation.use_tts,
            on_change=self.on_tts_change,
        )

        self.toggle_subtitle = ft.Switch(
            label="Generate Subtitle",
            value=config.compilation.use_subtitle,
            on_change=self.on_subtitle_change,
        )

        self.dropdown_crop_mode = ft.Dropdown(
            label="Mode Crop Video",
            options=[
                ft.dropdown.Option("default", "Default (Fit to Screen)"),
                ft.dropdown.Option("center_face", "Center Face Tracking"),
                ft.dropdown.Option("blur_bg", "Blurred Background"),
                ft.dropdown.Option("no_crop", "Original Aspect Ratio"),
            ],
            value=config.compilation.crop_mode or "default",
            on_select=self.on_crop_mode_change,
            width=250,
            dense=True,
        )

        self.progress_indicator = ProgressIndicator()
        
        event_bus.subscribe("PROGRESS", self._handle_progress)

        self._build_layout()
        self._refresh_list()

    def _build_layout(self):
        header = ft.Row(
            [
                ft.Icon(ft.Icons.COLLECTIONS, size=32, color=ft.Colors.DEEP_PURPLE_400),
                ft.Text("Mode Kompilasi", size=28, weight=ft.FontWeight.W_800),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        description = ft.Text(
            "Buat video kompilasi \"Top N\" dari beberapa momen video Anda.\n"
            "Setiap video akan diberi numbering card dan digabungkan menjadi satu.",
            color=ft.Colors.ON_SURFACE_VARIANT,
            size=14,
        )

        settings_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Pengaturan Kompilasi", weight=ft.FontWeight.W_600, size=16),
                    ft.Row(
                        [
                            self.dropdown_ordering,
                            self.dropdown_crop_mode,
                            self.toggle_tts,
                            self.toggle_subtitle,
                        ],
                        wrap=True,
                        spacing=16,
                    ),
                ],
                spacing=16,
            ),
            padding=ft.Padding(16, 16, 16, 16),
            border_radius=8,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )

        list_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Daftar Video", weight=ft.FontWeight.W_600, size=16),
                            ft.Row(
                                [
                                    self.btn_load_preset,
                                    self.btn_save_preset,
                                    self.btn_add_files,
                                ],
                                spacing=8,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=8),
                    self.list_container,
                ],
                spacing=8,
            ),
            padding=ft.Padding(16, 16, 16, 16),
            border_radius=8,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            expand=True,
        )

        actions_row = ft.Row(
            [self.btn_cancel, self.btn_generate],
            alignment=ft.MainAxisAlignment.END,
            spacing=16,
        )

        self.content = ft.Column(
            [
                header,
                description,
                ft.Container(height=8),
                settings_card,
                list_card,
                self.progress_indicator,
                actions_row,
            ],
            expand=True,
            spacing=16,
        )

    async def on_save_preset_click(self, e):
        import json
        if not self.items:
            self._show_snackbar("Tidak ada daftar video untuk disimpan.", error=True)
            return
            
        file_path = await self.save_picker.save_file(
            allowed_extensions=["json"],
            file_name="compilation_preset.json"
        )
        if file_path:
            preset_data = [
                {"file_path": item.file_path, "moment_name": item.moment_name}
                for item in self.items
            ]
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(preset_data, f, indent=4)
                self._show_snackbar(f"Preset berhasil disimpan: {os.path.basename(file_path)}")
            except Exception as ex:
                self._show_snackbar(f"Gagal menyimpan preset: {ex}", error=True)

    async def on_load_preset_click(self, e):
        import json
        files = await self.load_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["json"],
        )
        if files and files[0].path:
            try:
                with open(files[0].path, "r", encoding="utf-8") as f:
                    preset_data = json.load(f)
                
                if isinstance(preset_data, list):
                    self.items.clear()
                    for data in preset_data:
                        if isinstance(data, dict) and "file_path" in data and "moment_name" in data:
                            if os.path.exists(data["file_path"]):
                                self.items.append(CompilationItem(
                                    file_path=data["file_path"],
                                    moment_name=data["moment_name"]
                                ))
                            else:
                                log.warning(f"File klip tidak ditemukan: {data['file_path']}")
                    self._refresh_list()
                    self._show_snackbar("Preset berhasil dimuat.")
                else:
                    self._show_snackbar("Format preset tidak valid.", error=True)
            except Exception as ex:
                self._show_snackbar(f"Gagal memuat preset: {ex}", error=True)

    async def on_add_files_click(self, e):
        files = await self.file_picker.pick_files(
            allow_multiple=True,
            allowed_extensions=["mp4", "mkv", "avi", "mov"],
        )
        if files:
            for f in files:
                item = CompilationItem(
                    file_path=f.path or "",
                    moment_name=f"Momen {len(self.items) + 1}",
                )
                self.items.append(item)
            self._refresh_list()

    def _refresh_list(self):
        self.list_container.controls.clear()
        self.item_controls.clear()
        
        if not self.items:
            self.list_container.controls.append(self.empty_text)
            self.btn_generate.disabled = True
        else:
            total = len(self.items)
            is_countdown = self.dropdown_ordering.value == "countdown"
            
            for i, item in enumerate(self.items):
                item.number = total - i if is_countdown else i + 1
                
                ctrl = CompilationItemControl(
                    item=item,
                    on_delete=self.on_item_delete,
                    on_move_up=self.on_item_move_up,
                    on_move_down=self.on_item_move_down,
                )
                self.item_controls.append(ctrl)
                self.list_container.controls.append(ctrl)
                
            self.btn_generate.disabled = False
            
        try:
            self.update()
        except RuntimeError:
            pass

    def on_item_delete(self, ctrl: CompilationItemControl):
        if ctrl.item in self.items:
            self.items.remove(ctrl.item)
            self._refresh_list()

    def on_item_move_up(self, ctrl: CompilationItemControl):
        idx = self.items.index(ctrl.item)
        if idx > 0:
            self.items[idx], self.items[idx - 1] = self.items[idx - 1], self.items[idx]
            self._refresh_list()

    def on_item_move_down(self, ctrl: CompilationItemControl):
        idx = self.items.index(ctrl.item)
        if idx < len(self.items) - 1:
            self.items[idx], self.items[idx + 1] = self.items[idx + 1], self.items[idx]
            self._refresh_list()

    def on_ordering_change(self, e):
        if e.control.value:
            config.compilation.ordering = e.control.value
            config.save_to_file()
            self._refresh_list()

    def on_tts_change(self, e):
        config.compilation.use_tts = e.control.value
        config.save_to_file()

    def on_subtitle_change(self, e):
        config.compilation.use_subtitle = e.control.value
        config.save_to_file()
        
    def on_crop_mode_change(self, e):
        if e.control.value:
            config.compilation.crop_mode = e.control.value
            config.save_to_file()

    def on_generate_click(self, e):
        if not self.items:
            return
            
        self.is_processing = True
        self._cancel_flag = False
        
        self.btn_generate.disabled = True
        self.btn_generate.content = ft.Row([ft.Icon(ft.Icons.HOURGLASS_TOP), ft.Text("Memproses...")])
        self.btn_cancel.visible = True
        # Reset progress bar manually
        self.progress_indicator.label = "Memulai..."
        self.progress_indicator.value = 0.0
        
        for ctrl in self.item_controls:
            ctrl.disabled = True
        self.dropdown_ordering.disabled = True
        self.dropdown_crop_mode.disabled = True
        self.toggle_tts.disabled = True
        self.toggle_subtitle.disabled = True
        self.btn_add_files.disabled = True
        
        self.update()

        def _is_cancelled():
            return self._cancel_flag

        payload_items = [
            {"file_path": item.file_path, "moment_name": item.moment_name}
            for item in self.items
        ]

        async def _run_task():
            try:
                result = await asyncio.to_thread(
                    controller.execute_compilation,
                    payload_items,
                    _is_cancelled
                )
                
                if self._cancel_flag:
                    self._show_snackbar("Proses kompilasi dibatalkan.")
                elif result and result.get("success", 0) > 0:
                    self._show_snackbar("✅ Kompilasi berhasil dibuat!")
                    if result.get("output_dir"):
                        self._show_result_dialog(result)
                else:
                    self._show_snackbar("❌ Gagal membuat kompilasi.", error=True)
                    
            except Exception as ex:
                log.error(f"Error during compilation: {ex}")
                self._show_snackbar(f"Error: {ex}", error=True)
            finally:
                self._finish_processing()

        self._page.run_task(_run_task)

    def on_cancel_click(self, e):
        self._cancel_flag = True
        self.btn_cancel.disabled = True
        self.btn_cancel.content = ft.Row([ft.Icon(ft.Icons.CANCEL), ft.Text("Membatalkan...")])
        self.update()

    def _finish_processing(self):
        self.is_processing = False
        self._cancel_flag = False
        
        self.btn_generate.disabled = False
        self.btn_generate.content = ft.Row([ft.Icon(ft.Icons.PLAY_ARROW), ft.Text("Mulai Kompilasi")])
        self.btn_cancel.visible = False
        self.btn_cancel.disabled = False
        self.btn_cancel.content = ft.Row([ft.Icon(ft.Icons.CANCEL), ft.Text("Batalkan")])
        
        for ctrl in self.item_controls:
            ctrl.disabled = False
        self.dropdown_ordering.disabled = False
        self.dropdown_crop_mode.disabled = False
        self.toggle_tts.disabled = False
        self.toggle_subtitle.disabled = False
        self.btn_add_files.disabled = False
        
        self.update()

    def _show_snackbar(self, text: str, error: bool = False):
        color = ft.Colors.ERROR if error else ft.Colors.GREEN_700
        snack = ft.SnackBar(ft.Text(text), bgcolor=color)
        self._page.overlay.append(snack)
        snack.open = True
        self._page.update()

    def _show_result_dialog(self, result: dict):
        output_dir = result.get("output_dir", "")
        def close_dlg(e):
            dlg.open = False
            self._page.update()
            
        def open_folder(e):
            import subprocess
            import sys
            try:
                if sys.platform == "win32":
                    os.startfile(output_dir)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", output_dir])
                else:
                    subprocess.Popen(["xdg-open", output_dir])
            except Exception as ex:
                log.error(f"Gagal membuka folder: {ex}")

        dlg = ft.AlertDialog(
            title=ft.Text("Kompilasi Selesai 🎉", weight=ft.FontWeight.BOLD),
            content=ft.Text(f"Video kompilasi berhasil disimpan di:\n{output_dir}"),
            actions=[
                ft.Button(content=ft.Text("Buka Folder"), on_click=open_folder),
                ft.Button(
                    content=ft.Text("Tutup"),
                    on_click=close_dlg,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY)
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

    def _handle_progress(self, data: dict):
        stage = data.get("label", "")
        current = data.get("current", 0)
        total = data.get("total", 0)
        self.progress_indicator.label = stage
        if total > 0:
            self.progress_indicator.value = current / total
