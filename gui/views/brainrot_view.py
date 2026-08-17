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
        self.scroll = ft.ScrollMode.AUTO

        self.topic_input = ft.TextField(
            label="Topik Percakapan (Contoh: Kenapa Netflix ada iklan)",
            expand=True,
        )

        def generate_random_topic(e):
            import random
            topics = [
                "Kenapa orang suka makan seblak pedas gila",
                "Misteri kenapa kucing suka menjatuhkan barang",
                "Alasan kenapa alien belum mengunjungi bumi",
                "Debat apakah bubur ayam harus diaduk atau tidak",
                "Kenapa bangun pagi selalu terasa berat",
                "Mitos kecoa terbang yang bikin panik",
                "Gimana jadinya kalau dinosaurus masih hidup",
                "Kenapa kita sering lupa mau ngomong apa",
                "Konspirasi kenapa printer selalu rusak saat buru-buru",
                "Alasan kenapa hari senin terasa sangat panjang"
            ]
            self.topic_input.value = random.choice(topics)
            self.update()

        self.btn_random_topic = ft.IconButton(
            icon=ft.Icons.SHUFFLE,
            on_click=generate_random_topic,
            tooltip="Pilih Topik Acak",
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
        
        topic_row = ft.Row([self.topic_input, self.btn_random_topic, self.language_input])

        self.broll_input = ft.TextField(
            label="Path File B-Roll Video (.mp4)",
            expand=True,
            hint_text="/path/to/minecraft_parkour.mp4",
        )
        
        self.broll_picker = ft.FilePicker()
        self.clone_picker = ft.FilePicker()
        if hasattr(self.page_ref, "services"):
            self.page_ref.services.extend([self.broll_picker, self.clone_picker])
        else:
            self.page_ref.overlay.extend([self.broll_picker, self.clone_picker])

        async def pick_broll_result(e):
            files = await self.broll_picker.pick_files(allow_multiple=False)
            if files and len(files) > 0:
                self.broll_input.value = files[0].path or ""
                self.update()

        self.btn_pick_broll = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            on_click=pick_broll_result,
            tooltip="Pilih File Video B-Roll",
        )

        broll_row = ft.Row([self.broll_input, self.btn_pick_broll])

        # Narrator Setup
        self.narrator_name = ft.TextField(label="Nama Narator", value="Narator", expand=1)
        self.narrator_voice = ft.Dropdown(
            label="Suara Narator", 
            options=self._get_voice_options(),
            value="am_adam",
            expand=1
        )
        self.narrator_img = ft.TextField(label="Path Gambar (Opsional)", expand=1)
        narrator_row = ft.Row([self.narrator_name, self.narrator_voice, self.narrator_img])
        
        self.clone_input = ft.TextField(label="Path Audio Voice Clone (Opsional)", expand=True)
        async def pick_clone_result(e):
            files = await self.clone_picker.pick_files(allow_multiple=False)
            if files and len(files) > 0:
                self.clone_input.value = files[0].path or ""
                self.update()
        
        self.btn_pick_clone = ft.IconButton(
            icon=ft.Icons.AUDIO_FILE,
            on_click=pick_clone_result,
            tooltip="Pilih File Audio untuk Voice Cloning",
        )
        clone_row = ft.Row([self.clone_input, self.btn_pick_clone])

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
            ft.Text("Brainrot Video Generator (Story Mode)", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Buat video short viral dengan cerita AI dan B-Roll otomatis layaknya Reddit Story.", color=ft.Colors.WHITE_70),
            ft.Divider(),
            topic_row,
            broll_row,
            ft.Text("Pengaturan Narator", size=18, weight=ft.FontWeight.BOLD),
            narrator_row,
            clone_row,
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
        self.clone_input.disabled = is_loading
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
                result_data = await asyncio.to_thread(
                    brainrot_script_generator.generate_script,
                    topic or "",
                    self.narrator_name.value or "",
                    dataclasses.asdict(config.ai),
                    hook,
                    lang or "id"
                )
                
                if not result_data or not isinstance(result_data, dict) or "script" not in result_data:
                    app_state.append_log("Error: Gagal membuat script dari AI.")
                    return
                
                script = result_data["script"]
                metadata = {
                    "title": result_data.get("title", f"Cerita {topic}"),
                    "tags": result_data.get("tags", ["brainrot", "story"])
                }

                # Assign voice & images
                for line in script:
                    line["voice"] = self.narrator_voice.value or ""
                    line["image"] = self.narrator_img.value or ""
                    line["voice_clone"] = self.clone_input.value or ""

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
                
                meta_path = os.path.join(job_dir, "metadata_brainrot.json")
                import json
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                
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
