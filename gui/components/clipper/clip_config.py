import flet as ft
from typing import Any, cast
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
        self.page_ref.services.extend([self.intro_picker, self.outro_picker])
        
        self.title = ft.Text("⚙️ Pengaturan Klip & Subtitle", size=18, weight=ft.FontWeight.BOLD)
        
        self.crop_combo = ft.Dropdown(
            label="Mode Crop Video",
            options=[
                ft.dropdown.Option("default", "Default (Center Crop)"),
                ft.dropdown.Option("split_left", "Split Left (Top: Center, Bottom: Left Facecam)"),
                ft.dropdown.Option("split_right", "Split Right (Top: Center, Bottom: Right Facecam)"),
                ft.dropdown.Option("split_face", "Split Face Track (Top: Center, Bottom: Dynamic Face)"),
                ft.dropdown.Option("full", "Full (Fit Screen & Blurred BG)"),
                ft.dropdown.Option("full_face", "Full + Face Track (Dynamic Face)"),
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
        
        self.subtitle_check = ft.Checkbox(label="Auto Subtitle", on_change=self.on_subtitle_toggled)
        self.highlight_check = ft.Checkbox(label="Highlight Text")
        self.generate_intro_check = ft.Checkbox(label="Generate Intro", on_change=self.on_generate_intro_toggled)
        self.merge_clips_check = ft.Checkbox(label="Merge Clips", tooltip="Gabungkan semua klip (split) menjadi satu video kompilasi panjang")
        
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
        self.padding_spin = SpinBox(min_value=-30, max_value=30, step=1, value=0, label="Padding Klip (Detik)")
        self.max_duration_spin = SpinBox(min_value=10, max_value=600, step=10, value=60, label="Maks Durasi (Detik)")
        
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
                ft.dropdown.Option("scale", "Scale Up"),
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
        
        # type: ignore
        self.btn_intro = ft.Button("🎬 Set Video Intro", on_click=self.on_intro_picked) # type: ignore
        # type: ignore
        self.btn_outro = ft.Button("🎬 Set Video Outro", on_click=self.on_outro_picked) # type: ignore
        
        # type: ignore
        self.btn_lock_all = ft.Button("🔒 Kunci dan Simpan Pengaturan", on_click=self.on_lock_all_toggled) # type: ignore
        self.btn_lock_all.data = False
        
        grid_controls = cast(list[ft.Control], [
            ft.Row(cast(list[ft.Control], [self.crop_combo, self.ratio_combo])),
            ft.Row(cast(list[ft.Control], [self.subtitle_check, self.highlight_check, self.generate_intro_check, self.merge_clips_check]), alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(cast(list[ft.Control], [self.whisper_combo, self.font_combo])),
            ft.Row(cast(list[ft.Control], [self.delay_spin, self.padding_spin, self.max_duration_spin, self.font_size_spin]), alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(cast(list[ft.Control], [self.color_combo, self.location_combo])),
            ft.Row(cast(list[ft.Control], [self.bg_combo, self.anim_combo])),
            ft.Row(cast(list[ft.Control], [self.max_words_spin, self.hw_combo])),
            ft.Row(cast(list[ft.Control], [self.tts_lang_combo, self.tts_voice_combo])),
            ft.Row(cast(list[ft.Control], [self.btn_intro, self.btn_outro]), alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(cast(list[ft.Control], [self.btn_lock_all]), alignment=ft.MainAxisAlignment.CENTER),
        ])
        
        self.content = ft.Column([self.title] + grid_controls, spacing=12)
        
    def load_from_config(self) -> None:
        self.crop_combo.value = config.crop_mode
        self.ratio_combo.value = config.output_ratio
        
        self.subtitle_check.value = config.subtitle.enabled
        self.highlight_check.value = config.ai.use_highlight
        self.generate_intro_check.value = config.ai.use_generate_intro
        self.merge_clips_check.value = config.merge_clips
        self.on_generate_intro_toggled(None)
        
        self.whisper_combo.value = config.subtitle.whisper_model
        self.font_combo.value = config.subtitle.font
        self.location_combo.value = config.subtitle.location
        self.delay_spin.value = int(config.subtitle.delay * 1000)
        self.padding_spin.value = config.padding
        self.max_duration_spin.value = config.max_duration
        self.font_size_spin.value = config.subtitle.font_size
        self.color_combo.value = config.subtitle.color
        self.bg_combo.value = str(config.subtitle.border_style)
        self.anim_combo.value = config.subtitle.animation
        self.max_words_spin.value = config.subtitle.max_words
        self.hw_combo.value = config.hw_accel
        
        self.tts_lang_combo.value = config.tts_language
        self.tts_voice_combo.value = config.tts_voice
        
        self.on_subtitle_toggled(None)
        
        if config.ui_locked:
            self._lock_ui(True)
            self.btn_lock_all.data = True
            
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass
            
    def detect_hw_accel(self) -> None:
        import subprocess
        supported = ["cpu"]
        try:
            res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                out = res.stdout.lower()
                if "h264_nvenc" in out: supported.append("nvidia")
                if "h264_amf" in out: supported.append("amd")
                if "h264_qsv" in out: supported.append("intel")
                if "h264_videotoolbox" in out: supported.append("mac")
        except Exception:
            pass
        
        options = []
        for opt in self.hw_combo.options:
            if opt.key in supported:
                options.append(opt)
        self.hw_combo.options = options
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass
            
    def detect_libass(self) -> None:
        from core.utils import is_ffmpeg_libass_supported
        if not is_ffmpeg_libass_supported():
            self.subtitle_check.disabled = True
            self.subtitle_check.value = False
            self.subtitle_check.label = "Auto Subtitle (Missing libass)"
            self.subtitle_check.tooltip = "FFmpeg di sistem ini tidak memiliki library libass."
            self.on_subtitle_toggled(None)
        else:
            self.subtitle_check.label = "Auto Subtitle"
            self.subtitle_check.tooltip = ""
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    async def on_intro_picked(self, e: Any) -> None:
        files = await self.intro_picker.pick_files(
            dialog_title="Pilih Video Intro",
            allowed_extensions=["mp4", "mkv", "mov"]
        )
        if files and len(files) > 0 and files[0].path:
            try:
                dest = controller.set_intro_video(files[0].path)
                self._show_snackbar(f"Video intro berhasil diset:\n{dest}")
            except Exception as ex:
                self._show_snackbar(f"Gagal mengeset intro: {ex}", error=True)

    async def on_outro_picked(self, e: Any) -> None:
        files = await self.outro_picker.pick_files(
            dialog_title="Pilih Video Outro",
            allowed_extensions=["mp4", "mkv", "mov"]
        )
        if files and len(files) > 0 and files[0].path:
            try:
                dest = controller.set_outro_video(files[0].path)
                self._show_snackbar(f"Video outro berhasil diset:\n{dest}")
            except Exception as ex:
                self._show_snackbar(f"Gagal mengeset outro: {ex}", error=True)

    def on_subtitle_toggled(self, e: Any) -> None:
        checked = bool(self.subtitle_check.value)
        self.whisper_combo.disabled = not checked
        self.font_combo.disabled = not checked
        self.location_combo.disabled = not checked
        self.font_size_spin.disabled = not checked
        self.color_combo.disabled = not checked
        self.bg_combo.disabled = not checked
        self.anim_combo.disabled = not checked
        self.max_words_spin.disabled = not checked
        self.delay_spin.disabled = not checked
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def on_generate_intro_toggled(self, e: Any) -> None:
        self.btn_intro.disabled = bool(self.generate_intro_check.value)
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def on_lock_all_toggled(self, e: Any) -> None:
        locked = not self.btn_lock_all.data
        self.btn_lock_all.data = locked
        self._lock_ui(locked)
        
        config_data = {
            "crop_mode": self.crop_combo.value,
            "output_ratio": self.ratio_combo.value,
            "use_subtitle": bool(self.subtitle_check.value),
            "use_highlight": bool(self.highlight_check.value),
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
            "subtitle_max_words": self.max_words_spin.value,
            "padding": self.padding_spin.value,
            "max_duration": self.max_duration_spin.value,
            "tts_language": self.tts_lang_combo.value,
            "tts_voice": self.tts_voice_combo.value,
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
        self.subtitle_check.disabled = locked
        self.highlight_check.disabled = locked
        self.generate_intro_check.disabled = locked
        self.merge_clips_check.disabled = locked
        self.padding_spin.disabled = locked
        self.max_duration_spin.disabled = locked
        self.hw_combo.disabled = locked
        self.tts_lang_combo.disabled = locked
        self.tts_voice_combo.disabled = locked
        
        if not locked:
            self.detect_libass()
            self.on_subtitle_toggled(None)
            # type: ignore
            self.btn_lock_all.text = "🔒 Kunci dan Simpan Pengaturan"  # type: ignore
            self.btn_lock_all.style = ft.ButtonStyle()
        else:
            self.whisper_combo.disabled = True
            self.font_combo.disabled = True
            self.location_combo.disabled = True
            self.font_size_spin.disabled = True
            self.color_combo.disabled = True
            self.bg_combo.disabled = True
            self.anim_combo.disabled = True
            self.max_words_spin.disabled = True
            self.delay_spin.disabled = True
            self.tts_lang_combo.disabled = True
            self.tts_voice_combo.disabled = True
            
            # type: ignore
            self.btn_lock_all.text = "🔓 Buka Kunci Pengaturan"  # type: ignore
            self.btn_lock_all.style = ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_800, color=ft.Colors.INDIGO_200)
            
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def _show_snackbar(self, message: str, error: bool = False) -> None:
        color = ft.Colors.ERROR if error else ft.Colors.ON_SURFACE
        sb = ft.SnackBar(ft.Text(message, color=color))
        sb.open = True
        self.page_ref.overlay.append(sb)
        self.page_ref.update()
