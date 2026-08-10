from gui.ui_utils import show_snackbar
import flet as ft
from os import path
from typing import Any, Optional, cast
from core import controller, config
from gui.event_bus import event_bus
from gui.components.spin_box import SpinBox

class ClipConfig(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.padding = 16
        self.border_radius = 8
        self.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)

        # type: ignore
        self.intro_picker = ft.FilePicker()
        self.outro_picker = ft.FilePicker()
        self.watermark_picker = ft.FilePicker()
        self.video_frame_picker = ft.FilePicker()
        self.page_ref.services.extend([self.intro_picker, self.outro_picker, self.watermark_picker, self.video_frame_picker])

        self.title = ft.Text("⚙️ Pengaturan Klip & Subtitle", size=18, weight=ft.FontWeight.BOLD)

        self.crop_combo = ft.Dropdown(
            label="Mode Crop Video",
            options=[
                ft.dropdown.Option("default", "Default (Center Crop)"),
                ft.dropdown.Option("center_face", "Center Face Track (Dinamis Mengikuti Wajah)"),
                ft.dropdown.Option("split_left", "Split Left (Top: Center, Bottom: Left Facecam)"),
                ft.dropdown.Option("split_right", "Split Right (Top: Center, Bottom: Right Facecam)"),
                ft.dropdown.Option("split_face", "Split Face Track (Top: Center, Bottom: Dynamic Face)"),
                ft.dropdown.Option("full", "Full (Fit Screen & Blurred BG)"),
                ft.dropdown.Option("full_face", "Full + Face Track (Dynamic Face)"),
                ft.dropdown.Option("multi_face", "Multi Face Track (Podcast: Face1 + Full + Face2)"),
            ],
            expand=1
        )

        self.ratio_combo = ft.Dropdown(
            label="Rasio Output",
            options=[
                ft.dropdown.Option("9:16", "9:16 (Shorts / Reels / TikTok)"),
                ft.dropdown.Option("1:1", "1:1 (Square Feed)"),
                ft.dropdown.Option("16:9", "16:9 (Landscape YouTube)"),
                ft.dropdown.Option("original", "Original Video"),
            ],
            expand=1
        )

        self.libass_warning = ft.Container(
            content=ft.Text("⚠️ FFmpeg tidak memiliki libass — subtitle tidak akan di-render.", color=ft.Colors.AMBER_200, size=12),
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.AMBER),
            border_radius=6,
            padding=ft.Padding(left=10, top=6, right=10, bottom=6),
            visible=False,
        )
        self.highlight_check = ft.Checkbox(label="Highlight Text")
        self.emotion_check = ft.Checkbox(label="Deteksi Emosi Wajah Visual")
        self.voice_analysis_check = ft.Checkbox(label="Deteksi Emosi Suara (SER)")
        self.generate_intro_check = ft.Checkbox(label="Generate Intro", on_change=self.on_generate_intro_toggled)
        self.merge_clips_check = ft.Checkbox(label="Merge Clips", tooltip="Gabungkan semua klip (split) menjadi satu video kompilasi panjang")
        self.debug_mode_check = ft.Checkbox(label="Debug Mode", on_change=self.on_debug_mode_toggled)

        self.whisper_combo = ft.Dropdown(
            label="Model Whisper",
            options=[ft.dropdown.Option(m, f"{m} (Faster-Whisper)") for m in ["tiny", "base", "small", "medium", "large-v3"]],
            expand=1
        )

        self.font_combo = ft.Dropdown(
            label="Font Subtitle",
            options=[ft.dropdown.Option(f, f) for f in controller.get_available_fonts()],
            expand=1
        )

        self.location_combo = ft.Dropdown(
            label="Lokasi Subtitle",
            options=[
                ft.dropdown.Option("bottom", "Bawah (Bottom)"),
                ft.dropdown.Option("center", "Tengah (Center)"),
            ],
            expand=1
        )

        self.delay_spin = SpinBox(min_value=-5000, max_value=5000, step=100, label="Subtitle Delay (ms)")
        self.padding_spin = SpinBox(min_value=-30, max_value=60, step=1, value=0, label="Padding Klip (Detik)")
        self.min_duration_spin = SpinBox(min_value=10, max_value=600, step=10, value=60, label="Min Durasi (Detik)")

        self.font_size_spin = SpinBox(min_value=20, max_value=150, step=1, value=60, label="Ukuran Font")

        self.color_combo = ft.Dropdown(
            label="Warna Teks",
            options=[
                ft.dropdown.Option("&H0000FFFF", "Kuning"),
                ft.dropdown.Option("&H00FFFFFF", "Putih"),
                ft.dropdown.Option("&H0000FF00", "Hijau"),
                ft.dropdown.Option("&H000000FF", "Merah"),
                ft.dropdown.Option("&H00FF0000", "Biru"),
            ],
            expand=1
        )

        self.bg_combo = ft.Dropdown(
            label="Background",
            options=[
                ft.dropdown.Option("3", "Kotak Hitam"),
                ft.dropdown.Option("1", "Outline Hitam"),
            ],
            expand=1
        )

        self.anim_combo = ft.Dropdown(
            label="Efek Animasi",
            options=[
                ft.dropdown.Option("none", "Tanpa Animasi"),
                ft.dropdown.Option("scale", "Timbul (Scale Up) Per Kata"),
            ],
            expand=1
        )

        self.style_combo = ft.Dropdown(
            label="Style Subtitle",
            options=[
                ft.dropdown.Option("plain", "Plain (Teks Polos)"),
                ft.dropdown.Option("full_color", "Full Color (Warna Emosi + Efek)"),
            ],
            expand=1
        )

        self.max_words_spin = SpinBox(min_value=1, max_value=15, step=1, value=3, label="Maks Kata / Muncul")

        self.hw_combo = ft.Dropdown(
            label="Akselerasi Hardware",
            options=[
                ft.dropdown.Option("cpu", "CPU (Lambat, Stabil)"),
                ft.dropdown.Option("mac", "Mac (VideoToolbox)"),
                ft.dropdown.Option("amd", "AMD (AMF)"),
                ft.dropdown.Option("nvidia", "NVIDIA (NVENC)"),
                ft.dropdown.Option("intel", "Intel (QuickSync)"),
            ],
            expand=1
        )

        self.tts_lang_combo = ft.Dropdown(
            label="Bahasa TTS AI",
            options=[
                ft.dropdown.Option("default", "Default (Otomatis)"),
                ft.dropdown.Option("id", "Indonesia (ID)"),
                ft.dropdown.Option("en", "English (EN)"),
                ft.dropdown.Option("es", "Espanol (ES)"),
                ft.dropdown.Option("ja", "Japanese (JA)"),
                ft.dropdown.Option("ko", "Korean (KO)"),
                ft.dropdown.Option("ms", "Melayu (MS)"),
            ],
            expand=1
        )

        self.tts_voice_combo = ft.Dropdown(
            label="Suara TTS",
            options=[
                ft.dropdown.Option("female", "Wanita (Female)"),
                ft.dropdown.Option("male", "Pria (Male)"),
            ],
            expand=1
        )

        self.watermark_pos_combo = ft.Dropdown(
            label="Posisi Watermark",
            options=[
                ft.dropdown.Option("top", "Atas (Top)"),
                ft.dropdown.Option("center", "Tengah (Center)"),
                ft.dropdown.Option("bottom", "Bawah (Bottom)"),
            ],
            expand=1
        )

        # type: ignore
        self.btn_intro = ft.Button("🎬 Set Video Intro", on_click=self.on_intro_picked) # type: ignore
        # type: ignore
        self.btn_watermark = ft.Button("💧 Set Watermark", on_click=self.on_watermark_picked) # type: ignore
        # type: ignore
        self.btn_video_frame = ft.Button("🖼️ Pilih Frame Video", on_click=self.on_video_frame_picked) # type: ignore
        # type: ignore
        self.btn_outro = ft.Button("🎬 Set Video Outro", on_click=self.on_outro_picked) # type: ignore

        # Check outro, watermark, and video frame
        self.on_toggle_outro_btn()
        self.on_toggle_watermark_btn()
        self.on_toggle_video_frame_btn()

        # type: ignore
        self.btn_lock_all = ft.Button("🔒 Kunci dan Simpan Pengaturan", on_click=self.on_lock_all_toggled) # type: ignore
        self.btn_lock_all.data = False

        grid_controls = cast(list[ft.Control], [
            ft.Row(cast(list[ft.Control], [self.crop_combo, self.ratio_combo])),
            self.libass_warning,
            ft.Row(cast(list[ft.Control], [self.highlight_check, self.emotion_check, self.voice_analysis_check, self.generate_intro_check, self.merge_clips_check]), alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(cast(list[ft.Control], [self.whisper_combo, self.font_combo])),
            ft.Row(cast(list[ft.Control], [self.delay_spin, self.padding_spin, self.min_duration_spin]), alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(cast(list[ft.Control], [self.color_combo, self.location_combo])),
            ft.Row(cast(list[ft.Control], [self.bg_combo, self.anim_combo, self.style_combo])),
            ft.Row(cast(list[ft.Control], [self.max_words_spin, self.font_size_spin, self.hw_combo])),
            ft.Row(cast(list[ft.Control], [self.tts_lang_combo, self.tts_voice_combo])),
            ft.Row(cast(list[ft.Control], [self.watermark_pos_combo, self.debug_mode_check]), alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(cast(list[ft.Control], [self.btn_intro, self.btn_watermark, self.btn_video_frame, self.btn_outro]), alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(cast(list[ft.Control], [self.btn_lock_all]), alignment=ft.MainAxisAlignment.CENTER),
        ])

        self.content = ft.Column([self.title] + grid_controls, spacing=12)

    def load_from_config(self) -> None:
        self.crop_combo.value = config.crop_mode
        self.ratio_combo.value = config.output_ratio

        # Subtitle is always enabled (mandatory) — no checkbox to load
        self.highlight_check.value = config.ai.use_highlight
        self.emotion_check.value = config.ai.use_emotion_detection
        self.voice_analysis_check.value = config.ai.use_voice_analysis
        self.generate_intro_check.value = config.ai.use_generate_intro
        self.merge_clips_check.value = config.merge_clips
        self.on_generate_intro_toggled(None)

        self.whisper_combo.value = config.subtitle.whisper_model
        self.font_combo.value = config.subtitle.font
        self.location_combo.value = config.subtitle.location
        self.delay_spin.value = int(config.subtitle.delay * 1000)
        self.padding_spin.value = config.padding
        self.min_duration_spin.value = config.min_duration
        self.font_size_spin.value = config.subtitle.font_size
        self.color_combo.value = config.subtitle.color
        self.bg_combo.value = str(config.subtitle.border_style)
        self.anim_combo.value = config.subtitle.animation
        self.style_combo.value = config.subtitle.style
        self.max_words_spin.value = config.subtitle.max_words
        self.hw_combo.value = config.hw_accel

        self.tts_lang_combo.value = config.tts_language
        self.tts_voice_combo.value = config.tts_voice
        self.watermark_pos_combo.value = config.watermark_position

        # Subtitle always enabled — no toggle needed

        if config.ui_locked:
            self._lock_ui(True)
            self.btn_lock_all.data = True

        self.on_toggle_video_frame_btn()

        try:
            if self.page_ref: self.page_ref.update()
            else: self.update()
        except Exception:
            pass

    def detect_hw_accel(self) -> None:
        async def worker():
            import asyncio
            import subprocess
            import os

            supported = ["cpu"]

            def test_encoder(enc):
                try:
                    res = subprocess.run(
                        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=256x256", "-vframes", "1", "-c:v", enc, "-f", "null", "-"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    return res.returncode == 0
                except Exception:
                    return False

            if await asyncio.to_thread(test_encoder, "h264_nvenc"): supported.append("nvidia")
            if await asyncio.to_thread(test_encoder, "h264_amf"): supported.append("amd")
            if await asyncio.to_thread(test_encoder, "h264_qsv"): supported.append("intel")
            if await asyncio.to_thread(test_encoder, "h264_videotoolbox"): supported.append("mac")

            original_options = [
                ft.dropdown.Option("cpu", "CPU (Lambat, Stabil)"),
                ft.dropdown.Option("mac", "Mac (VideoToolbox)"),
                ft.dropdown.Option("amd", "AMD (AMF)"),
                ft.dropdown.Option("nvidia", "NVIDIA (NVENC)"),
                ft.dropdown.Option("intel", "Intel (QuickSync)"),
            ]

            options = [opt for opt in original_options if opt.key in supported]
            self.hw_combo.options = options

            if self.hw_combo.value not in supported:
                self.hw_combo.value = "cpu"

            try:
                if self.page_ref: self.page_ref.update()
                else: self.update()
            except Exception:
                pass

        if self.page_ref:
            self.page_ref.run_task(worker)
        else:
            import asyncio
            import threading
            threading.Thread(target=asyncio.run, args=(worker(),), daemon=True).start()

    def detect_libass(self) -> None:
        from core.utils import is_ffmpeg_libass_supported
        if not is_ffmpeg_libass_supported():
            self.libass_warning.visible = True
        else:
            self.libass_warning.visible = False
        try:
            if self.page_ref: self.page_ref.update()
            else: self.update()
        except Exception:
            pass

    async def on_intro_picked(self, e) -> None:
        files = await self.intro_picker.pick_files(
            dialog_title="Pilih Video Intro",
            allowed_extensions=["mp4", "mkv", "mov"]
        )
        if files and len(files) > 0 and files[0].path:
            try:
                dest = controller.set_intro_video(files[0].path)
                show_snackbar(self.page_ref, f"Video intro berhasil diset:\n{dest}")
            except Exception as ex:
                show_snackbar(self.page_ref, f"Gagal mengeset intro: {ex}", error=True)

    async def on_outro_picked(self, e) -> None:
        files = await self.outro_picker.pick_files(
            dialog_title="Pilih Video Outro",
            allowed_extensions=["mp4", "mkv", "mov"]
        )
        if files and len(files) > 0 and files[0].path:
            try:
                dest = controller.set_outro_video(files[0].path)
                self.on_toggle_outro_btn()
                show_snackbar(self.page_ref, f"Video outro berhasil diset:\n{dest}")
            except Exception as ex:
                show_snackbar(self.page_ref, f"Gagal mengeset outro: {ex}", error=True)

    def on_clear_outro_picked(self, e) -> None:
        """Menghapus pilihan video outro dari konfigurasi."""
        try:
            controller.clear_outro_video()
            self.on_toggle_outro_btn()
            show_snackbar(self.page_ref, "Video outro berhasil dihapus.")
        except Exception as ex:
            show_snackbar(self.page_ref, f"Gagal menghapus outro: {ex}", error=True)

    def on_toggle_outro_btn(self) -> None:
        if config.outro_video is not None:
            print(config.outro_video)
            if path.exists(config.outro_video):
                self.btn_outro.content = "🎬 Hapus Video Outro"
                self.btn_outro.color = ft.Colors.RED
                self.btn_outro.on_click = self.on_clear_outro_picked
            else:
                self.btn_outro.content = "🎬 Video Tidak Ditemukan"
                self.btn_outro.color = ft.Colors.RED
                self.btn_outro.on_click = self.on_clear_outro_picked
        else:
            self.btn_outro.content = "🎬 Pilih Video Outro"
            self.btn_outro.color = None
            self.btn_outro.on_click = self.on_outro_picked

        try:
            self.btn_outro.update()
        except Exception:
            pass

        try:
            if self.page_ref: self.page_ref.update()
            else: self.update()
        except Exception:
            pass

    async def on_watermark_picked(self, e) -> None:
        files = await self.watermark_picker.pick_files(
            dialog_title="Pilih Watermark Image",
            allowed_extensions=["png", "jpg", "jpeg"]
        )
        if files and len(files) > 0 and files[0].path:
            try:
                dest = controller.set_watermark_image(files[0].path)
                self.on_toggle_watermark_btn()
                show_snackbar(self.page_ref, f"Watermark berhasil diset:\n{dest}")
            except Exception as ex:
                show_snackbar(self.page_ref, f"Gagal mengeset watermark: {ex}", error=True)

    def on_clear_watermark_picked(self, e) -> None:
        try:
            controller.clear_watermark_image()
            self.on_toggle_watermark_btn()
            show_snackbar(self.page_ref, "Watermark berhasil dihapus.")
        except Exception as ex:
            show_snackbar(self.page_ref, f"Gagal menghapus watermark: {ex}", error=True)

    def on_toggle_watermark_btn(self) -> None:
        if config.watermark_image is not None:
            if path.exists(config.watermark_image):
                self.btn_watermark.content = "💧 Hapus Watermark"
                self.btn_watermark.color = ft.Colors.RED
                self.btn_watermark.on_click = self.on_clear_watermark_picked
            else:
                self.btn_watermark.content = "💧 File Tidak Ditemukan"
                self.btn_watermark.color = ft.Colors.RED
                self.btn_watermark.on_click = self.on_clear_watermark_picked
        else:
            self.btn_watermark.content = "💧 Pilih Watermark"
            self.btn_watermark.color = None
            self.btn_watermark.on_click = self.on_watermark_picked

    async def on_video_frame_picked(self, e) -> None:
        files = await self.video_frame_picker.pick_files(
            dialog_title="Pilih Frame Video",
            allowed_extensions=["mp4", "mkv", "mov", "avi"]
        )
        if files and len(files) > 0 and files[0].path:
            try:
                dest = controller.set_video_frame(files[0].path)
                self.on_toggle_video_frame_btn()
                show_snackbar(self.page_ref, f"Frame video berhasil diset:\n{dest}")
            except Exception as ex:
                show_snackbar(self.page_ref, f"Gagal mengeset frame video: {ex}", error=True)

    def on_clear_video_frame_picked(self, e) -> None:
        try:
            controller.clear_video_frame()
            self.on_toggle_video_frame_btn()
            show_snackbar(self.page_ref, "Frame video berhasil dihapus.")
        except Exception as ex:
            show_snackbar(self.page_ref, f"Gagal menghapus frame video: {ex}", error=True)

    def on_toggle_video_frame_btn(self) -> None:
        if config.video_frame is not None:
            if path.exists(config.video_frame):
                self.btn_video_frame.content = "🖼️ Hapus Frame Video"
                self.btn_video_frame.color = ft.Colors.RED
                self.btn_video_frame.on_click = self.on_clear_video_frame_picked
            else:
                self.btn_video_frame.content = "🖼️ File Tidak Ditemukan"
                self.btn_video_frame.color = ft.Colors.RED
                self.btn_video_frame.on_click = self.on_clear_video_frame_picked
        else:
            self.btn_video_frame.content = "🖼️ Pilih Frame Video"
            self.btn_video_frame.color = None
            self.btn_video_frame.on_click = self.on_video_frame_picked

        try:
            self.btn_video_frame.update()
        except Exception:
            pass

        try:
            if self.page_ref: self.page_ref.update()
            else: self.update()
        except Exception:
            pass



    def on_generate_intro_toggled(self, e) -> None:
        self.btn_intro.disabled = bool(self.generate_intro_check.value)
        try:
            if self.page_ref: self.page_ref.update()
            else: self.update()
        except Exception:
            pass

    def on_debug_mode_toggled(self, e) -> None:
        config.debug_mode = bool(self.debug_mode_check.value)

    def on_lock_all_toggled(self, e) -> None:
        locked = not self.btn_lock_all.data
        self.btn_lock_all.data = locked
        self._lock_ui(locked)

        config_data = {
            "crop_mode": self.crop_combo.value,
            "output_ratio": self.ratio_combo.value,
            "use_subtitle": True,
            "use_highlight": bool(self.highlight_check.value),
            "use_emotion_detection": bool(self.emotion_check.value),
            "use_voice_analysis": bool(self.voice_analysis_check.value),
            "use_generate_intro": bool(self.generate_intro_check.value),
            "merge_clips": bool(self.merge_clips_check.value),
            "whisper_model": self.whisper_combo.value,
            "subtitle_font": self.font_combo.value,
            "subtitle_location": self.location_combo.value,
            "subtitle_delay": self.delay_spin.value / 1000.0,
            "subtitle_font_size": self.font_size_spin.value,
            "subtitle_color": self.color_combo.value,
            "subtitle_bg_color": "&H80000000",
            "subtitle_border_style": int(self.bg_combo.value) if self.bg_combo.value else 3,
            "subtitle_animation": self.anim_combo.value,
            "subtitle_style": self.style_combo.value,
            "subtitle_max_words": self.max_words_spin.value,
            "padding": self.padding_spin.value,
            "min_duration": self.min_duration_spin.value,
            "tts_language": self.tts_lang_combo.value,
            "tts_voice": self.tts_voice_combo.value,
            "watermark_position": self.watermark_pos_combo.value,
            "hw_accel": self.hw_combo.value,
            "ui_locked": locked
        }
        config.update_from_dict(config_data)
        if config.save_to_file():
            event_bus.publish("log_message", text=f"[INFO] Pengaturan berhasil disimpan secara permanen (Status: {'terkunci' if locked else 'terbuka'}).")
        else:
            event_bus.publish("log_message", text="[ERROR] Gagal menyimpan pengaturan ke config.json.")

    def _lock_ui(self, locked: bool) -> None:
        self.crop_combo.disabled = locked
        self.ratio_combo.disabled = locked
        self.highlight_check.disabled = locked
        self.emotion_check.disabled = locked
        self.voice_analysis_check.disabled = locked
        self.generate_intro_check.disabled = locked
        self.merge_clips_check.disabled = locked
        self.padding_spin.disabled = locked
        self.min_duration_spin.disabled = locked
        self.hw_combo.disabled = locked
        self.tts_lang_combo.disabled = locked
        self.tts_voice_combo.disabled = locked
        self.watermark_pos_combo.disabled = locked
        self.whisper_combo.disabled = locked
        self.font_combo.disabled = locked
        self.location_combo.disabled = locked
        self.font_size_spin.disabled = locked
        self.color_combo.disabled = locked
        self.bg_combo.disabled = locked
        self.anim_combo.disabled = locked
        self.max_words_spin.disabled = locked
        self.delay_spin.disabled = locked
        self.style_combo.disabled = locked

        if not locked:
            self.detect_libass()
            # type: ignore
            self.btn_lock_all.text = "🔒 Kunci dan Simpan Pengaturan"  # type: ignore
            self.btn_lock_all.style = ft.ButtonStyle()
        else:
            # type: ignore
            self.btn_lock_all.text = "🔓 Buka Kunci Pengaturan"  # type: ignore
            self.btn_lock_all.style = ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_800, color=ft.Colors.INDIGO_200)

        try:
            if self.page_ref: self.page_ref.update()
            else: self.update()
        except Exception:
            pass


