import flet as ft
from typing import Any, cast
from core import config

class Preview(ft.Container):
    def __init__(self, on_selection_changed=None, on_ai_scan_requested=None):
        super().__init__()
        self.on_selection_changed = on_selection_changed
        self.on_ai_scan_requested = on_ai_scan_requested

        self.segments_data = []
        self.ai_segments_data = []
        
        self.padding = 16
        self.border_radius = 8
        self.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        
        # UI Elements
        self.video_title = ft.Text("Masukkan URL YouTube lalu klik Load Video", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.video_uploader = ft.Text("Uploader: -", color=ft.Colors.WHITE_54)
        self.video_duration = ft.Text("Durasi: -", color=ft.Colors.WHITE_54)
        
        self.thumbnail_image = ft.Image(
            src="",
            width=160,
            height=90,
            fit=ft.BoxFit.CONTAIN,
            visible=False
        )
        self.thumbnail_placeholder = ft.Container(
            content=ft.Text("No Video Loaded", color=ft.Colors.BLUE_GREY_400),
            width=160,
            height=90,
            bgcolor=ft.Colors.BLUE_GREY_900,
            border=ft.Border.all(1, ft.Colors.BLUE_GREY_700), # type: ignore
            border_radius=8,
            alignment=ft.Alignment.CENTER # type: ignore
        )
        
        # Mode selection
        self.mode_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("heatmap", "1. Heatmap (Most Replayed)"),
                ft.dropdown.Option("custom", "2. Kustom Range (Manual)"),
                ft.dropdown.Option("ai", "3. AI Highlight Detector (LLM)")
            ],
            value="heatmap",
            on_select=self.on_mode_changed, # type: ignore
            expand=True
        )
        
        # Heatmap Page
        self.segment_count_label = ft.Text("Pilih Segmen Heatmap:", color=ft.Colors.WHITE_54)
        self.segment_list = ft.ListView(height=160, spacing=4, )
        self.heatmap_view = ft.Column([
            ft.Row([
                self.segment_count_label,
                ft.Container(expand=True),
                ft.TextButton("Select All", on_click=self.select_all_segments),
                ft.TextButton("Deselect All", on_click=self.deselect_all_segments),
            ]),
            ft.Row([ft.Container(
                content=self.segment_list,
                border_radius=6,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                expand=True
                )
            ])
        ], visible=True)
        
        # Custom Page
        self.start_input = ft.TextField(label="Waktu Mulai", hint_text="detik (contoh: 30) atau MM:SS", expand=True)
        self.end_input = ft.TextField(label="Waktu Selesai", hint_text="detik (contoh: 90) atau MM:SS", expand=True)
        self.custom_view = ft.Row([
            ft.Text("Waktu Mulai:"),
            self.start_input,
            ft.Text("Waktu Selesai:"),
            self.end_input
        ], visible=False)
        
        # AI Page
        self.btn_run_ai_scan = ft.Button(
            content=ft.Text("🤖 Scan Highlights dengan AI"), # type: ignore
            on_click=self.on_run_ai_scan,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
            height=40
        )
        self.ai_segment_count_label = ft.Text("Segmen AI Highlight (Transkripsi Whisper + LLM):", color=ft.Colors.WHITE_54)
        self.ai_segment_list = ft.ListView(height=140, spacing=4)
        self.ai_view = ft.Column([
            self.btn_run_ai_scan,
            self.ai_segment_count_label,
            self.ai_segment_list
        ], visible=False)
        
        self.mode_stack = ft.Column([
            self.heatmap_view,
            self.custom_view,
            self.ai_view
        ])
        
        # Main layout
        self.content = ft.Column([
            ft.Text("📺 Video Preview & Segment Selection", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Stack([
                    self.thumbnail_placeholder,
                    self.thumbnail_image
                ]),
                ft.Column([
                    self.video_title,
                    self.video_uploader,
                    self.video_duration
                ], expand=True)
            ]),
            ft.Row([
                ft.Text("Metode Penentuan Klip:", weight=ft.FontWeight.BOLD),
                self.mode_dropdown
            ]),
            self.mode_stack
        ], spacing=12)

    def set_ai_scanning(self, scanning: bool) -> None:
        if scanning:
            self.btn_run_ai_scan.disabled = True
            # type: ignore
            self.btn_run_ai_scan.text = "⏳ Memproses AI Scan (Whisper + LLM)..." # type: ignore
        else:
            self.btn_run_ai_scan.disabled = False
            # type: ignore
            self.btn_run_ai_scan.text = "🤖 Scan Highlights dengan AI" # type: ignore
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def on_run_ai_scan(self, e: Any) -> None:
        ai_config = {
            "provider": getattr(config, "ai_provider", "ollama"),
            "ollama_host": getattr(config, "ollama_host", "http://localhost:11434"),
            "ollama_model": getattr(config, "ollama_model", "llama3"),
            "gemini_key": getattr(config, "gemini_key", ""),
            "gemini_model": getattr(config, "gemini_model", "gemini-1.5-flash"),
            "openai_key": getattr(config, "openai_key", ""),
            "openai_model": getattr(config, "openai_model", "gpt-4o-mini"),
            "openai_base_url": getattr(config, "openai_base_url", ""),
        }
        if self.on_ai_scan_requested:
            self.on_ai_scan_requested(ai_config)

    def set_preview_data(self, preview: dict) -> None:
        self.video_title.value = preview.get("title", "Unknown Title")
        self.video_uploader.value = f"Uploader: {preview.get('uploader', '-')}"
        
        dur_s = preview.get("duration", 0)
        m, s = divmod(dur_s, 60)
        h, m = divmod(m, 60)
        dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        self.video_duration.value = f"Durasi: {dur_str} ({dur_s}s)"

        thumb_url = preview.get("thumbnail")
        if thumb_url:
            self.thumbnail_image.src = thumb_url
            self.thumbnail_image.visible = True
            self.thumbnail_placeholder.visible = False
        else:
            self.thumbnail_image.visible = False
            self.thumbnail_placeholder.visible = True
        
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def set_scan_data(self, scan_result: dict) -> None:
        self.segments_data = scan_result.get("segments", [])
        self.segment_list.controls.clear()
        
        self.segment_count_label.value = f"Segmen Heatmap Ditemukan ({len(self.segments_data)}):"
        
        for idx, seg in enumerate(self.segments_data, start=1):
            start_s = int(seg.get("start", 0))
            dur_s = int(seg.get("duration", 0))
            score = seg.get("score", 0.0)
            
            m1, s1 = divmod(start_s, 60)
            m2, s2 = divmod(start_s + dur_s, 60)
            time_str = f"{m1:02d}:{s1:02d} - {m2:02d}:{s2:02d}"
            
            item_text = f"Klip #{idx} | {time_str} (durasi: {dur_s}s) | Score: {score:.2f}"
            checkbox = ft.Checkbox(label=item_text, value=True, data=seg, on_change=self.on_checkbox_changed)
            self.segment_list.controls.append(checkbox)
            
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def set_ai_scan_data(self, ai_result: dict) -> None:
        self.ai_segments_data = ai_result.get("segments", [])
        self.ai_segment_list.controls.clear()

        self.ai_segment_count_label.value = f"Segmen AI Highlights Ditemukan ({len(self.ai_segments_data)}):"

        for idx, seg in enumerate(self.ai_segments_data, start=1):
            start_s = int(seg.get("start", 0))
            dur_s = int(seg.get("duration", 0))
            title = seg.get("title", "AI Highlight")
            reason = seg.get("reason", "")
            
            m1, s1 = divmod(start_s, 60)
            m2, s2 = divmod(start_s + dur_s, 60)
            time_str = f"{m1:02d}:{s1:02d} - {m2:02d}:{s2:02d}"

            item_text = f"🤖 Klip #{idx} | {title} [{time_str}] ({dur_s}s) | {reason}"
            checkbox = ft.Checkbox(label=item_text, value=True, data=seg, on_change=self.on_checkbox_changed)
            self.ai_segment_list.controls.append(checkbox)
            
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def select_all_segments(self, e: Any = None) -> None:
        target_list = self.ai_segment_list if self.mode_dropdown.value == "ai" else self.segment_list
        for c in target_list.controls:
            if isinstance(c, ft.Checkbox):
                c.value = True
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass
        if self.on_selection_changed:
            self.on_selection_changed()

    def deselect_all_segments(self, e: Any = None) -> None:
        target_list = self.ai_segment_list if self.mode_dropdown.value == "ai" else self.segment_list
        for c in target_list.controls:
            if isinstance(c, ft.Checkbox):
                c.value = False
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass
        if self.on_selection_changed:
            self.on_selection_changed()

    def on_checkbox_changed(self, e: Any) -> None:
        if self.on_selection_changed:
            self.on_selection_changed()

    def on_mode_changed(self, e: Any) -> None:
        val = self.mode_dropdown.value
        self.heatmap_view.visible = val == "heatmap"
        self.custom_view.visible = val == "custom"
        self.ai_view.visible = val == "ai"
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass
        if self.on_selection_changed:
            self.on_selection_changed()

    def get_selected_mode(self) -> str:
        mode = self.mode_dropdown.value
        return str(mode) if mode else "heatmap"

    def get_selected_segments(self) -> list:
        target_list = self.ai_segment_list if self.mode_dropdown.value == "ai" else self.segment_list
        selected = []
        for c in target_list.controls:
            if isinstance(c, ft.Checkbox) and c.value:
                if c.data is not None:
                    selected.append(c.data)
        return selected

    def get_custom_range(self) -> tuple:
        start_val = self.start_input.value or ""
        end_val = self.end_input.value or ""
        return start_val.strip(), end_val.strip()
