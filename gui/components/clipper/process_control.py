import flet as ft
from typing import Any, cast
from gui.event_bus import event_bus
from gui.components.progress_indicator import ProgressIndicator

class ProcessControl(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.total_clips = 0
        self.padding = 16
        self.border_radius = 8
        self.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        
        title = ft.Text("🚀 Process Dashboard & Control", size=18, weight=ft.FontWeight.BOLD)
        
        self.stage_text = ft.Text("Status: Idle", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY_CONTAINER)
        self.stage_badge = ft.Container(
            content=self.stage_text,
            # type: ignore
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),  # type: ignore
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            border_radius=6,
            # type: ignore
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)  # type: ignore
        )
        
        self.progress_indicator = ProgressIndicator(label="0 / 0 Klip", value=0.0)
        
        self.start_btn = ft.Button(
            content=ft.Text("▶ MULAI PROSES KLIP"), # type: ignore
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE, padding=16),
            on_click=self.on_start_requested
        )
        self.cancel_btn = ft.Button(
            content=ft.Text("⏹ Batal / Abort"), # type: ignore
            style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR, padding=16),
            disabled=True,
            on_click=self.on_cancel_requested
        )
        
        self.content = ft.Column(
            cast(list[ft.Control], [
                ft.Row(cast(list[ft.Control], [title, ft.Container(expand=True), self.stage_badge])),
                self.progress_indicator,
                ft.Row(cast(list[ft.Control], [self.start_btn, self.cancel_btn]))
            ]),
            spacing=12
        )

    def on_start_requested(self, e: Any = None) -> None:
        self.start_btn.disabled = True
        try:
            self.update()
        except Exception:
            pass
        event_bus.publish("start_process_requested")
        
    def on_cancel_requested(self, e: Any = None) -> None:
        event_bus.publish("cancel_process_requested")

    def update_stage(self, stage_name: str, data: dict) -> None:
        stage_map = {
            "download": "Mengunduh Segmen Audio/Video (yt-dlp)...",
            "crop": "Memotong / Split Screen Video (FFmpeg)...",
            "subtitle_model_load": "Memuat Model Faster-Whisper...",
            "subtitle_transcribe": "Mengekstrak Transkripsi Audio...",
            "ai_detect": "⏳ Menganalisis Momen dengan AI Model...",
            "burn_subtitle": "Melakukan Render Subtitle ke Video...",
            "finalize": "Menggabungkan Intro/Outro...",
            "done_clip": "Selesai Memproses Klip!",
        }
        
        display = stage_map.get(stage_name, stage_name)
        
        self.stage_text.value = f"Stage: {display}"
        self.stage_badge.bgcolor = ft.Colors.INDIGO_800
        self.stage_text.color = ft.Colors.INDIGO_200
        
        if stage_name == "done_clip":
            try:
                done_count = int(data.get("clip_index", 0))
            except (ValueError, TypeError):
                done_count = self.total_clips
                
            if self.total_clips > 0:
                pct = done_count / self.total_clips
                self.progress_indicator.value = pct
                self.progress_indicator.label = f"{done_count} / {self.total_clips} Klip"
                
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def set_total_targets(self, total: int) -> None:
        self.total_clips = total
        self.progress_indicator.value = 0.0
        self.progress_indicator.label = f"0 / {total} Klip"
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def set_processing(self, processing: bool) -> None:
        self.start_btn.disabled = processing
        self.cancel_btn.disabled = not processing
        
        if processing:
            self.stage_text.value = "Status: Processing..."
            self.stage_badge.bgcolor = ft.Colors.TEAL_800
            self.stage_text.color = ft.Colors.TEAL_200
        else:
            self.stage_text.value = "Status: Idle"
            self.stage_badge.bgcolor = ft.Colors.PRIMARY_CONTAINER
            self.stage_text.color = ft.Colors.ON_PRIMARY_CONTAINER
            
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass
