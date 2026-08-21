import asyncio
import os

import flet as ft

from core.logger import log
from core.utils import get_app_root
from gui.ui_utils import show_snackbar


class DebuggerView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.spacing = 20
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO

        self.file_picker = ft.FilePicker()
        self.page_ref.services.append(self.file_picker)

        self.input_file = ""
        self.input_text = ft.TextField(
            label="Video Input (Untuk Showcase)", value="", read_only=True, expand=True
        )

        self.btn_browse = ft.Button(
            "Browse", icon=ft.Icons.FOLDER_OPEN, on_click=self.on_browse_clicked
        )

        self.btn_test = ft.Button(
            "Test Semua Video Effect (Showcase)",
            icon=ft.Icons.PLAY_CIRCLE_FILL,
            on_click=self.on_test_clicked,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
        )

        self.btn_debug_analyzers = ft.Button(
            "Debug Semua Analyzer (Text/Voice/Visual)",
            icon=ft.Icons.BUG_REPORT,
            on_click=self.on_debug_analyzers_clicked,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        )

        self.btn_test_ai = ft.Button(
            "Test Respon AI",
            icon=ft.Icons.SMART_TOY,
            on_click=self.on_test_ai_clicked,
            disabled=False,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_700, color=ft.Colors.WHITE),
        )

        self.btn_test_ai_metadata = ft.Button(
            "Test AI Metadata",
            icon=ft.Icons.SUBTITLES,
            on_click=self.on_test_ai_metadata_clicked,
            disabled=False,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_700, color=ft.Colors.WHITE),
        )

        self.progress_ring = ft.ProgressRing(visible=False)

        self.controls = [
            ft.Text("Debugger & Testing", size=24, weight=ft.FontWeight.BOLD),
            
            ft.Text("1. Input File", size=18, weight=ft.FontWeight.W_600),
            ft.Text(
                "Pilih video untuk dites.",
                color=ft.Colors.WHITE_70,
            ),
            ft.Row(
                [self.input_text, self.btn_browse], alignment=ft.MainAxisAlignment.START
            ),
            ft.Divider(height=20, color=ft.Colors.WHITE_24),
            
            ft.Text("2. Rendering & Analyzers", size=18, weight=ft.FontWeight.W_600),
            ft.Text(
                "Uji coba rendering ffmpeg dan filter overlay.",
                color=ft.Colors.WHITE_70,
            ),
            ft.Row(
                [
                    self.btn_test,
                    self.btn_debug_analyzers,
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            ft.Divider(height=20, color=ft.Colors.WHITE_24),
            
            ft.Text("3. Artificial Intelligence", size=18, weight=ft.FontWeight.W_600),
            ft.Text(
                "Uji koneksi LLM untuk deteksi momen dan generasi metadata teks.",
                color=ft.Colors.WHITE_70,
            ),
            ft.Row(
                [
                    self.btn_test_ai,
                    self.btn_test_ai_metadata,
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            
            ft.Container(
                content=self.progress_ring,
                alignment=ft.Alignment.CENTER,
                padding=20
            ),
        ]

    async def on_browse_clicked(self, e):
        # flet 0.23 async file picker support
        files = await self.file_picker.pick_files(
            allow_multiple=False, allowed_extensions=["mp4", "mkv", "mov", "avi"]
        )
        if files and len(files) > 0:
            self.input_file = files[0].path
            self.input_text.value = self.input_file or ""
            self.btn_test.disabled = False
            self.btn_debug_analyzers.disabled = False
            self.update()

    def on_test_clicked(self, e):
        if not self.input_file or not os.path.exists(self.input_file):
            show_snackbar(
                self.page_ref, "Silakan pilih video input yang valid terlebih dahulu."
            )
            return

        self.btn_test.disabled = True
        self.btn_debug_analyzers.disabled = True
        self.btn_test_ai.disabled = True
        self.btn_test_ai_metadata.disabled = True
        self.progress_ring.visible = True
        self.update()

        output_file = os.path.join(get_app_root(), "video_effects_showcase.mp4")
        show_snackbar(
            self.page_ref,
            "Memulai pembuatan Video Effect Showcase. Silakan cek console log...",
        )

        self.page_ref.run_task(self.run_showcase_task, output_file)

    def on_debug_analyzers_clicked(self, e):
        if not self.input_file or not os.path.exists(self.input_file):
            show_snackbar(
                self.page_ref, "Silakan pilih video input yang valid terlebih dahulu."
            )
            return

        self.btn_test.disabled = True
        self.btn_debug_analyzers.disabled = True
        self.btn_test_ai.disabled = True
        self.btn_test_ai_metadata.disabled = True
        self.progress_ring.visible = True
        self.update()

        output_file = os.path.join(get_app_root(), "analyzers_debug_overlay.mp4")
        show_snackbar(
            self.page_ref,
            "Memulai pembuatan Debug Overlay Analyzer. Silakan cek console log...",
        )

        self.page_ref.run_task(self.run_debug_analyzers_task, output_file)

    async def run_showcase_task(self, output_file: str):
        from scripts.generate_ve_showcase import generate_ve_showcase

        try:
            success = await asyncio.to_thread(
                generate_ve_showcase, str(self.input_file), output_file
            )

            if success:
                show_snackbar(
                    self.page_ref, f"Berhasil! Showcase disimpan di {output_file}"
                )
            else:
                show_snackbar(
                    self.page_ref, "Gagal membuat showcase. Cek log untuk detail."
                )
        except Exception as ex:
            log.error(f"Error running showcase script: {ex}")
            show_snackbar(
                self.page_ref, "Terjadi kesalahan sistem saat menjalankan showcase."
            )

        self.btn_test.disabled = False
        self.btn_debug_analyzers.disabled = False
        self.btn_test_ai.disabled = False
        self.btn_test_ai_metadata.disabled = False
        self.progress_ring.visible = False
        self.update()

    async def run_debug_analyzers_task(self, output_file: str):
        from scripts.generate_analyzer_debug import generate_analyzer_debug

        try:
            success = await asyncio.to_thread(
                generate_analyzer_debug, str(self.input_file), output_file
            )

            if success:
                show_snackbar(
                    self.page_ref, f"Berhasil! Debug Video & CSV disimpan di {output_file}"
                )
            else:
                show_snackbar(
                    self.page_ref, "Gagal membuat video debug. Cek log untuk detail."
                )
        except Exception as ex:
            log.error(f"Error running analyzer debug script: {ex}")
            show_snackbar(
                self.page_ref,
                "Terjadi kesalahan sistem saat menjalankan analyzer debug.",
            )

        self.btn_test.disabled = False
        self.btn_debug_analyzers.disabled = False
        self.btn_test_ai.disabled = False
        self.btn_test_ai_metadata.disabled = False
        self.progress_ring.visible = False
        self.update()

    def on_test_ai_clicked(self, e):
        self.btn_test.disabled = True
        self.btn_debug_analyzers.disabled = True
        self.btn_test_ai.disabled = True
        self.btn_test_ai_metadata.disabled = True
        self.progress_ring.visible = True
        self.update()

        show_snackbar(
            self.page_ref,
            "Memulai tes koneksi & respons AI. Silakan cek console log...",
        )
        self.page_ref.run_task(self.run_test_ai_task)

    async def run_test_ai_task(self):
        import os
        from core.ai.detector import ai_detector
        from core.config import config
        from core.utils import read_json, write_json

        transcript_data = []

        if self.input_file and os.path.exists(self.input_file):
            folder_dir = os.path.dirname(self.input_file)
            base_name = os.path.basename(self.input_file)
            transcript_file = os.path.join(folder_dir, f"{base_name}_transcript.json")
            
            if os.path.exists(transcript_file):
                log.info(f"Menggunakan file transcript aktual: {transcript_file}")
                transcript_data = read_json(transcript_file, default=[])

            if not transcript_data:
                log.info(f"Tidak menemukan transcript JSON, mengekstrak transkrip dari {base_name}...")
                show_snackbar(self.page_ref, f"Mengekstrak transkripsi teks dari {base_name} (Whisper)...")
                
                from core.subtitle import transcribe_audio_file
                try:
                    transcript_data = await asyncio.to_thread(
                        transcribe_audio_file,
                        self.input_file,
                        whisper_model=config.subtitle.whisper_model,
                        event_hook=None
                    )
                    
                    if transcript_data:
                        write_json(transcript_file, transcript_data, indent=2)
                        log.info(f"Transkrip berhasil diekstrak dan disimpan ke: {transcript_file}")
                except Exception as ex:
                    log.error(f"Gagal mengekstrak transkrip: {ex}")
                    show_snackbar(self.page_ref, f"Gagal mengekstrak transkrip: {ex}", True)

        if not transcript_data:
            log.warning("Gagal mendapatkan transkrip aktual, menggunakan data dummy sebagai fallback.")
            transcript_data = [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Halo teman-teman, ini adalah percobaan AI dummy.",
                },
                {
                    "start": 2.0,
                    "end": 6.0,
                    "text": "Apakah AI bisa mendeteksi momen lucu dari teks ini? Hahaha lucu sekali!",
                },
                {
                    "start": 6.0,
                    "end": 10.0,
                    "text": "Kalau berhasil berarti koneksi ke AI provider aman dan parsing JSON bekerja.",
                },
            ]

        try:
            ai_config = config.to_dict()

            def event_hook(hook_type, message):
                log.info(f"[AI Hook] {hook_type}: {message}")
                
            show_snackbar(self.page_ref, "Mengirim transkrip ke AI Provider...")

            results = await asyncio.to_thread(
                ai_detector.detect_highlights,
                transcript_data,
                ai_config,
                event_hook,
                None,
            )

            if results:
                show_snackbar(
                    self.page_ref,
                    f"Berhasil! AI merespons dengan {len(results)} momen.",
                )
                log.info(f"Hasil Test AI: {results}")
            else:
                show_snackbar(
                    self.page_ref,
                    "AI berhasil dihubungi namun tidak mengembalikan momen/JSON valid.",
                    True,
                )
        except Exception as ex:
            log.error(f"Error saat tes respon AI: {ex}")
            show_snackbar(
                self.page_ref,
                "Terjadi kesalahan sistem saat mencoba menghubungi AI.",
                True,
            )

        self.btn_test_ai.disabled = False
        self.btn_test_ai_metadata.disabled = False
        if self.input_file:
            self.btn_test.disabled = False
            self.btn_debug_analyzers.disabled = False
        self.progress_ring.visible = False
        self.update()

    def on_test_ai_metadata_clicked(self, e):
        self.btn_test.disabled = True
        self.btn_debug_analyzers.disabled = True
        self.btn_test_ai.disabled = True
        self.btn_test_ai_metadata.disabled = True
        self.progress_ring.visible = True
        self.update()

        show_snackbar(
            self.page_ref,
            "Memulai tes AI Metadata. Silakan cek console log...",
        )
        self.page_ref.run_task(self.run_test_ai_metadata_task)

    async def run_test_ai_metadata_task(self):
        import os
        from core.ai.detector import ai_detector
        from core.config import config
        from core.utils import read_json, write_json
        import asyncio

        clip_text = "Gila guys, kalian lihat nggak tadi? Astaga, monster itu tiba-tiba muncul dari kegelapan! Jantung gue hampir copot rasanya. Oke, kita coba pelan-pelan ke sana ya..."
        youtube_title = "MOMEN PALING HOROR DI GAME INI! - Power Drill Massacre"
        channel_name = "Windah Basudara"
        youtube_url = "https://youtube.com/watch?v=gBSX9DPhRqg"
        
        user_context = "Video gaming walkthrough dengan reaksi heboh dan kaget."
        language = "Indonesia"
        
        words_data = [
            {"word": "Gila", "start": 0.0, "end": 0.3},
            {"word": "guys,", "start": 0.3, "end": 0.7},
            {"word": "kalian", "start": 0.7, "end": 1.0},
            {"word": "lihat", "start": 1.0, "end": 1.4},
            {"word": "nggak", "start": 1.4, "end": 1.8},
            {"word": "tadi?", "start": 1.8, "end": 2.2},
            {"word": "Astaga,", "start": 2.5, "end": 3.0},
            {"word": "monster", "start": 3.0, "end": 3.4},
            {"word": "itu", "start": 3.4, "end": 3.6},
            {"word": "tiba-tiba", "start": 3.6, "end": 4.1},
            {"word": "muncul", "start": 4.1, "end": 4.5},
            {"word": "dari", "start": 4.5, "end": 4.8},
            {"word": "kegelapan!", "start": 4.8, "end": 5.5},
            {"word": "Jantung", "start": 6.0, "end": 6.5},
            {"word": "gue", "start": 6.5, "end": 6.8},
            {"word": "hampir", "start": 6.8, "end": 7.2},
            {"word": "copot", "start": 7.2, "end": 7.6},
            {"word": "rasanya.", "start": 7.6, "end": 8.0},
        ]
        
        visual_emotions = [
            {"time": 0.0, "emotion": "surprise"},
            {"time": 2.5, "emotion": "fear"},
            {"time": 6.0, "emotion": "sad"}
        ]
        
        audio_emotions = [
            {"time": 0.0, "event": "excited"},
            {"time": 2.5, "event": "fear"},
            {"time": 6.0, "event": "neutral"}
        ]

        try:
            ai_config = config.to_dict()

            def event_hook(hook_type, message):
                log.info(f"[AI Hook] {hook_type}: {message}")

            show_snackbar(self.page_ref, "Mengirim data ke AI Provider...")

            results = await asyncio.to_thread(
                ai_detector.generate_metadata,
                clip_text=clip_text,
                youtube_title=youtube_title,
                channel_name=channel_name,
                youtube_url=youtube_url,
                ai_config=ai_config,
                user_context=user_context,
                event_hook=event_hook,
                language=language,
                words_data=words_data,
                visual_emotions=visual_emotions,
                audio_emotions=audio_emotions,
            )

            if results:
                show_snackbar(
                    self.page_ref, f"Berhasil! Metadata di-generate (Cek Console)."
                )
                log.info(f"Hasil Test AI Metadata: {results}")
            else:
                show_snackbar(
                    self.page_ref,
                    "AI berhasil dihubungi namun gagal generate metadata valid.",
                    True,
                )
        except Exception as ex:
            log.error(f"Error saat tes AI Metadata: {ex}")
            show_snackbar(
                self.page_ref,
                "Terjadi kesalahan sistem saat mencoba menghubungi AI.",
                True,
            )

        self.btn_test_ai.disabled = False
        self.btn_test_ai_metadata.disabled = False
        if self.input_file:
            self.btn_test.disabled = False
            self.btn_debug_analyzers.disabled = False
        self.progress_ring.visible = False
        self.update()


def generate_emotion_chart_png(
    visual_data: list,
    text_data: list,
    voice_data: list,
    output_path: str
) -> bool:
    """
    Menghasilkan gambar grafik line chart diagram alur emosi per detik 
    pada masing-masing variabel penilaian (Visual, Teks, dan Voice).
    
    Fungsi ini digunakan untuk keperluan penilaian atau laporan.
    
    Contoh format input data:
    visual_data = [{"time": 0.0, "emotion": "marah"}, {"time": 1.0, "emotion": "neutral"}]
    text_data = [{"time": 0.0, "emotion": "neutral"}]
    voice_data = [{"time": 0.0, "event": "scream"}] # bisa pakai key 'event' atau 'emotion'
    """
    try:
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot Visual
        if visual_data:
            t_vis = [float(item.get("time", 0.0)) for item in visual_data]
            v_vis = [str(item.get("emotion", "unknown")).capitalize() for item in visual_data]
            ax.plot(t_vis, v_vis, marker='o', label='Visual', color='blue', linestyle='-')

        # Plot Teks
        if text_data:
            t_text = [float(item.get("time", 0.0)) for item in text_data]
            v_text = [str(item.get("emotion", "unknown")).capitalize() for item in text_data]
            ax.plot(t_text, v_text, marker='s', label='Teks', color='green', linestyle='--')

        # Plot Voice
        if voice_data:
            t_voice = [float(item.get("time", 0.0)) for item in voice_data]
            v_voice = [str(item.get("event", item.get("emotion", "unknown"))).capitalize() for item in voice_data]
            ax.plot(t_voice, v_voice, marker='^', label='Voice', color='red', linestyle=':')

        ax.set_xlabel('Waktu (Detik)')
        ax.set_ylabel('Variabel Penilaian (Emosi / Event)')
        ax.set_title('Grafik Diagram Alur Emosi Per Detik')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()
        plt.savefig(output_path, format='png', dpi=300)
        plt.close(fig)
        
        return True
    except Exception as ex:
        from core.logger import log
        log.error(f"Gagal generate gambar grafik emosi: {ex}")
        return False
