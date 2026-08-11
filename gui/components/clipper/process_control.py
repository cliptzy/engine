from typing import Any, cast

import flet as ft

from gui.components.progress_indicator import ProgressIndicator
from gui.event_bus import event_bus


class TaskRow(ft.Container):
    def __init__(self, clip_index: int, initial_stage: str):
        super().__init__()
        self.clip_index = clip_index
        self.padding = ft.Padding(left=12, top=8, right=12, bottom=8)
        self.border_radius = 6
        self.bgcolor = ft.Colors.TRANSPARENT

        self.icon = ft.Icon(ft.Icons.MOVIE, color=ft.Colors.INDIGO, size=20)
        title_text = (
            "Merge Video / Global" if clip_index == 0 else f"Klip #{clip_index}"
        )
        self.title_ui = ft.Text(title_text, weight=ft.FontWeight.BOLD, size=13)
        self.stage_ui = ft.Text(initial_stage, size=12, color=ft.Colors.INDIGO)
        self.spinner = ft.ProgressRing(width=16, height=16, stroke_width=2)

        self.content = ft.Row(
            [
                self.icon,
                ft.Column([self.title_ui, self.stage_ui], spacing=2, expand=True),
                self.spinner,
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def update_state(
        self, new_stage: str, is_done: bool = False, is_error: bool = False
    ):
        self.stage_ui.value = new_stage
        if is_error:
            self.spinner.visible = False
            self.icon.name = ft.Icons.ERROR
            self.icon.color = ft.Colors.ERROR
        elif is_done:
            self.spinner.visible = False
            self.icon.name = ft.Icons.CHECK_CIRCLE
            self.icon.color = ft.Colors.GREEN_400
        else:
            self.spinner.visible = True
            self.icon.name = ft.Icons.MOVIE
            self.icon.color = ft.Colors.INDIGO
        try:
            self.update()
        except Exception:
            pass


class ProcessControl(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.total_clips = 0
        self.padding = 20
        self.border_radius = 12
        self.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)

        # Header
        title = ft.Text(
            "🚀 Dashboard & Kontrol Pemrosesan", size=18, weight=ft.FontWeight.BOLD
        )

        self.stage_text = ft.Text(
            "Status: Idle",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ON_PRIMARY_CONTAINER,
        )
        self.stage_badge = ft.Container(
            content=self.stage_text,
            padding=ft.Padding(left=10, top=4, right=10, bottom=4),
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            border_radius=6,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

        # Global Progress
        self.progress_indicator = ProgressIndicator(
            label="0 / 0 Klip Selesai (0%)", value=0.0
        )

        # Tasks List
        self.tasks_list = ft.ListView(
            spacing=8, height=180, padding=10, auto_scroll=True
        )
        self.tasks_container = ft.Container(
            content=self.tasks_list,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
        )

        self.active_tasks_map: dict[int, TaskRow] = {}
        self.tasks_list.controls.append(
            ft.Container(
                content=ft.Text(
                    "Menunggu instruksi pemrosesan...",
                    color=ft.Colors.OUTLINE,
                    italic=True,
                ),
                padding=20,
                alignment=ft.Alignment(0, 0),
            )
        )

        # Buttons
        self.start_btn = ft.Button(
            content=ft.Text("▶ MULAI PROSES KLIP", weight=ft.FontWeight.BOLD),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE, padding=16
            ),
            on_click=self.on_start_requested,
            expand=True,
        )
        self.cancel_btn = ft.Button(
            content=ft.Text("⏹ BATALKAN", weight=ft.FontWeight.BOLD),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR, padding=16
            ),
            disabled=True,
            on_click=self.on_cancel_requested,
            expand=True,
        )

        self.content = ft.Column(
            [
                ft.Row([title, ft.Container(expand=True), self.stage_badge]),
                ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                self.progress_indicator,
                ft.Text("Daftar Pemrosesan Aktif:", size=14, weight=ft.FontWeight.BOLD),
                self.tasks_container,
                ft.Row([self.start_btn, self.cancel_btn], spacing=12),
            ],
            spacing=16,
        )

    def on_start_requested(self, e: Any = None) -> None:
        self.start_btn.disabled = True
        try:
            self.update()
        except Exception:
            pass
        event_bus.publish("start_process_requested")

    def on_cancel_requested(self, e: Any = None) -> None:
        # Mark all active tasks as cancelled
        for task in self.active_tasks_map.values():
            if task.spinner.visible:
                task.update_state("Dibatalkan!", is_error=True)
        event_bus.publish("cancel_process_requested")

    def update_stage(self, stage_name: str, data: dict) -> None:
        stage_map = {
            "download": "Mengunduh Segmen Video/Audio (yt-dlp)...",
            "crop": "Memotong / Split Screen Video (FFmpeg)...",
            "subtitle_model_load": "Memuat Model Faster-Whisper...",
            "subtitle_transcribe": "Mengekstrak Transkripsi Audio...",
            "ai_detect": "⏳ Menganalisis Momen dengan AI Model...",
            "burn_subtitle": "Merender Subtitle ke Video...",
            "finalize": "Menggabungkan Intro/Outro...",
            "merging": "Menggabungkan Seluruh Klip Video...",
            "done_clip": "Selesai Memproses Klip!",
        }

        display = stage_map.get(stage_name, stage_name)

        if stage_name == "Idle":
            return

        clip_index = 0
        try:
            clip_index = int(data.get("clip_index", 0))
        except (ValueError, TypeError):
            pass

        is_done = stage_name == "done_clip"

        # Remove placeholder if it exists
        if (
            len(self.tasks_list.controls) == 1
            and isinstance(self.tasks_list.controls[0], ft.Container)
            and not isinstance(self.tasks_list.controls[0], TaskRow)
        ):
            self.tasks_list.controls.clear()

        # Track individual clip tasks
        if clip_index not in self.active_tasks_map:
            new_task = TaskRow(clip_index, display)
            self.active_tasks_map[clip_index] = new_task
            self.tasks_list.controls.append(new_task)

        task_ui = self.active_tasks_map[clip_index]

        if is_done:
            task_ui.update_state("Selesai!", is_done=True)

            # Update global progress safely
            # Hitung jumlah task yang sudah selesai (icon = CHECK_CIRCLE) dan clip_index > 0
            done_count = sum(
                1
                for t in self.active_tasks_map.values()
                if not t.spinner.visible
                and t.icon.name == ft.Icons.CHECK_CIRCLE
                and t.clip_index > 0
            )

            if self.total_clips > 0:
                pct = min(1.0, done_count / self.total_clips)
                self.progress_indicator.value = pct
                self.progress_indicator.label = f"{done_count} / {self.total_clips} Klip Selesai ({int(pct * 100)}%)"
        else:
            task_ui.update_state(display, is_done=False)

        try:
            if self.page:
                self.page.update()
            else:
                self.update()
        except Exception:
            pass

    def set_total_targets(self, total: int) -> None:
        self.total_clips = total
        self.progress_indicator.value = 0.0
        self.progress_indicator.label = f"0 / {total} Klip Selesai (0%)"
        try:
            if self.page:
                self.page.update()
            else:
                self.update()
        except Exception:
            pass

    def set_processing(self, processing: bool) -> None:
        self.start_btn.disabled = processing
        self.cancel_btn.disabled = not processing

        if processing:
            self.stage_text.value = "Status: Processing..."
            self.stage_badge.bgcolor = ft.Colors.TEAL_800
            self.stage_text.color = ft.Colors.TEAL_200

            # Clear tasks on start
            self.active_tasks_map.clear()
            self.tasks_list.controls.clear()
        else:
            self.stage_text.value = "Status: Idle"
            self.stage_badge.bgcolor = ft.Colors.PRIMARY_CONTAINER
            self.stage_text.color = ft.Colors.ON_PRIMARY_CONTAINER

            if not self.tasks_list.controls:
                self.tasks_list.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "Menunggu instruksi pemrosesan...",
                            color=ft.Colors.OUTLINE,
                            italic=True,
                        ),
                        padding=20,
                        alignment=ft.Alignment(0, 0),
                    )
                )

        try:
            if self.page:
                self.page.update()
            else:
                self.update()
        except Exception:
            pass
