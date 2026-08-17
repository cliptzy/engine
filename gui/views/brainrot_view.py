import os
import asyncio
from typing import Optional

import flet as ft

from core.logger import log
from core.config import config
from core.processing.tts_engine import VOICE_MAP
from gui.state import app_state
from gui.event_bus import event_bus

class BrainrotView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.spacing = 20
        self.expand = True

        self.topic_input = ft.TextField(
            label="Topik Percakapan (Contoh: Kenapa Netflix ada iklan)",
            expand=True,
        )

        self.language_input = ft.Dropdown(
            label="Bahasa Skrip",
            options=[
                ft.dropdown.Option("Indonesian"),
                ft.dropdown.Option("English"),
                ft.dropdown.Option("Japanese"),
                ft.dropdown.Option("Korean"),
                ft.dropdown.Option("Spanish"),
            ],
            value="English", # Default to English for Bark compatibility
            width=150,
        )
        
        topic_row = ft.Row([self.topic_input, self.language_input])

        self.broll_input = ft.TextField(
            label="Path File B-Roll Video (.mp4)",
            expand=True,
            hint_text="/path/to/minecraft_parkour.mp4",
        )
        
        self.broll_picker = ft.FilePicker()
        if hasattr(self.page_ref, "services"):
            self.page_ref.services.append(self.broll_picker)
        else:
            self.page_ref.overlay.append(self.broll_picker)

        async def pick_broll_result(e):
            files = await self.broll_picker.pick_files(allow_multiple=False)
            if files and len(files) > 0:
                self.broll_input.value = files[0].path
                self.update()

        self.btn_pick_broll = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            on_click=pick_broll_result,
            tooltip="Pilih File Video B-Roll",
        )

        broll_row = ft.Row([self.broll_input, self.btn_pick_broll])

        # Character 1 Setup
        self.char1_name = ft.TextField(label="Nama Karakter 1", value="Spongebob", expand=1)
        self.char1_voice = ft.Dropdown(
            label="Suara Karakter 1", 
            options=self._get_voice_options(),
            value="id-ID-ArdiNeural",
            expand=1
        )
        self.char1_img = ft.TextField(label="Path Gambar 1 (Opsional)", expand=1)
        
        char1_row = ft.Row([self.char1_name, self.char1_voice, self.char1_img])

        # Character 2 Setup
        self.char2_name = ft.TextField(label="Nama Karakter 2", value="Mr. Krabs", expand=1)
        self.char2_voice = ft.Dropdown(
            label="Suara Karakter 2", 
            options=self._get_voice_options(),
            value="id-ID-GadisNeural",
            expand=1
        )
        self.char2_img = ft.TextField(label="Path Gambar 2 (Opsional)", expand=1)
        
        char2_row = ft.Row([self.char2_name, self.char2_voice, self.char2_img])

        self.generate_btn = ft.Button(
            "Generate Brainrot Video",
            icon=ft.Icons.MOVIE_CREATION,
            on_click=self.on_generate_click,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
            height=50,
        )

        self.controls = [
            ft.Text("Brainrot Video Generator", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Buat video short viral dengan percakapan AI dan B-Roll otomatis.", color=ft.Colors.WHITE_70),
            ft.Divider(),
            topic_row,
            broll_row,
            ft.Text("Pengaturan Karakter", size=18, weight=ft.FontWeight.BOLD),
            char1_row,
            char2_row,
            ft.Container(height=20),
            self.generate_btn,
        ]

    def _get_voice_options(self) -> list[ft.dropdown.Option]:
        options = []
        for lang, genders in VOICE_MAP.items():
            for gender, voice_id in genders.items():
                options.append(ft.dropdown.Option(key=voice_id, text=f"{lang.upper()} - {gender.capitalize()} ({voice_id})"))
        return options

    def set_loading(self, is_loading: bool):
        self.generate_btn.disabled = is_loading
        self.topic_input.disabled = is_loading
        self.broll_input.disabled = is_loading
        self.update()

    def on_generate_click(self, e):
        topic = self.topic_input.value
        broll = self.broll_input.value
        lang = self.language_input.value
        if not topic or not broll:
            app_state.append_log("Error: Topik dan B-Roll tidak boleh kosong.")
            return
            
        if not os.path.exists(broll):
            app_state.append_log("Error: File B-Roll tidak ditemukan.")
            return

        app_state.set_processing(True, "Memulai pipeline Brainrot...")
        self.set_loading(True)

        async def brainrot_worker():
            try:
                from core.ai.script_generator import brainrot_script_generator
                from core.processing.brainrot_processor import process_brainrot
                from core.utils import get_app_root
                import uuid

                # Event hook untuk logging
                def hook(event_type, data):
                    if event_type in ["status", "ai_status", "stage"]:
                        app_state.set_processing(True, str(data))
                        app_state.append_log(str(data))
                    elif event_type == "log":
                        app_state.append_log(str(data))

                # 1. Generate Script
                log.info("Generating Brainrot script...")
                import dataclasses
                script = await asyncio.to_thread(
                    brainrot_script_generator.generate_script,
                    topic,
                    self.char1_name.value,
                    self.char2_name.value,
                    dataclasses.asdict(config.ai),
                    hook,
                    lang
                )
                
                if not script:
                    app_state.append_log("Error: Gagal membuat script dari AI.")
                    return

                # Assign voice & images
                for line in script:
                    if line.get("speaker") == self.char1_name.value:
                        line["voice"] = self.char1_voice.value
                        line["image"] = self.char1_img.value
                    else:
                        line["voice"] = self.char2_voice.value
                        line["image"] = self.char2_img.value

                # 2. Process Video
                job_id = str(uuid.uuid4())[:8]
                job_dir = os.path.join(get_app_root(), "clips", f"brainrot_{job_id}")
                os.makedirs(job_dir, exist_ok=True)
                
                out_path = os.path.join(job_dir, "final_brainrot.mp4")

                log.info("Processing Brainrot video...")
                await process_brainrot(
                    job_dir=job_dir,
                    b_roll_path=broll,
                    script_data=script,
                    output_path=out_path,
                    event_hook=hook
                )
                
                app_state.append_log(f"Brainrot Selesai! Tersimpan di: {out_path}")
            except Exception as ex:
                import traceback
                log.error(f"Brainrot worker error: {ex}\\n{traceback.format_exc()}")
                app_state.append_log(f"Error Brainrot: {ex}")
            finally:
                self.set_loading(False)
                app_state.set_processing(False)
                self.page_ref.update()

        self.page_ref.run_task(brainrot_worker)
