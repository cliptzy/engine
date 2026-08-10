from gui.ui_utils import show_snackbar
import flet as ft
from typing import Any, cast
import os
import glob
import re
import json
import flet_video as ftv
from core.config import config
from gui.event_bus import event_bus
from core.logger import log
from core.utils import open_dir

class UploadDistribution(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.padding = 16
        self.border_radius = 8
        self.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        
        self.current_project_dir = ""
        self.current_clip_path = ""
        self.current_clip_index = ""
        self._video_player_active = False
        
        # --- Project Selector ---
        self.project_dropdown = ft.Dropdown(
            label="📂 Pilih Project / Klip Tersimpan",
            options=[],
            on_select=self.on_project_selected, # type: ignore
            expand=True
        )
        self.refresh_projects_btn = ft.IconButton(icon=ft.Icons.REFRESH, on_click=self.load_projects, tooltip="Refresh") # type: ignore
        self.open_project_dir_btn = ft.IconButton(icon=ft.Icons.FOLDER_OPEN, on_click=self.open_project_dir, tooltip="Open Folder")
        
        # --- Left: Clip List ---
        self.clip_list = ft.ListView(expand=True, spacing=2)
        self.clips_to_upload = [] # holds dicts or checkboxes
        
        # --- Right: Video Player ---
        # Jangan langsung inisialisasi Video — buat placeholder dulu
        self._video_player: ftv.Video | None = None
        
        self.video_placeholder = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, size=48, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("Pilih klip untuk memutar video", color=ft.Colors.BLUE_GREY_400, size=14)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8
            ),
            bgcolor=ft.Colors.BLACK_87,
            border_radius=8,
            alignment=ft.Alignment.CENTER, # type: ignore
            expand=True
        )
        
        self.video_container = ft.Container(
            content=self.video_placeholder,
            bgcolor=ft.Colors.BLACK_87,
            border_radius=8,
            alignment=ft.Alignment.CENTER, # type: ignore
            expand=True
        )
        
        # --- Metadata Editor ---
        self.meta_title = ft.TextField(label="Judul Video", expand=True)
        self.meta_tags = ft.TextField(label="Hashtags (pisahkan dengan spasi)", value=config.default_hashtags, expand=True)
        self.btn_save_meta = ft.Button("Simpan Metadata", icon=ft.Icons.SAVE, on_click=self.save_metadata)
        self.btn_ai_meta = ft.Button("Generate dengan AI", icon=ft.Icons.AUTO_AWESOME, on_click=self.generate_ai_metadata)
        
        # --- Upload Settings ---
        self.platform_yt = ft.Checkbox(label="YouTube Shorts", value=config.youtube.auto_upload)
        self.platform_tt = ft.Checkbox(label="TikTok", value=config.tiktok.auto_upload)
        self.platform_ig = ft.Checkbox(label="Instagram Reels", value=config.instagram.auto_upload)
        self.upload_interval_input = ft.TextField(label="Interval (Jam)", value=str(config.upload_interval), width=100)
        self.max_effects_input = ft.TextField(label="Max Efek/Klip", value=str(config.max_effects_per_clip), width=120)
        
        import datetime
        self.schedule_date_picker = ft.DatePicker(
            on_change=self.on_schedule_date_change,
            first_date=datetime.datetime.now(),
        )
        self.schedule_time_picker = ft.TimePicker(
            on_change=self.on_schedule_time_change,
        )
        self._page.overlay.extend([self.schedule_date_picker, self.schedule_time_picker])
        
        self.schedule_date = None
        self.schedule_time = None
        
        def show_time(e):
            self.schedule_time_picker.open = True
            self._page.update()

        self.btn_pick_date = ft.TextButton("Set Tanggal", icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: self._page.show_dialog(self.schedule_date_picker))
        self.btn_pick_time = ft.TextButton("Set Waktu", icon=ft.Icons.ACCESS_TIME, on_click=show_time)
        self.btn_clear_schedule = ft.IconButton(icon=ft.Icons.CLEAR, on_click=self.clear_schedule, tooltip="Reset Jadwal")
        self.lbl_schedule_info = ft.Text("Jadwal Mulai: Segera (+30 menit)", size=12, color=ft.Colors.BLUE_GREY_400)
        
        self.upload_btn = ft.Button(
            content=ft.Text("📤 Upload Video Terpilih"), # type: ignore
            on_click=self.handle_upload,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
        )
        
        self._is_upload_cancelled = False
        self.cancel_upload_btn = ft.Button(
            content=ft.Text("❌ Batal Upload"), # type: ignore
            on_click=self.cancel_upload,
            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
            visible=False
        )
        
        self.render_btn = ft.Button(
            content=ft.Text("🎬 Render Terpilih"), # type: ignore
            on_click=self.handle_render,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
        )
        self.upload_progress = ft.ProgressBar(visible=False)
        self.upload_status_text = ft.Text("", size=13, color=ft.Colors.GREY_400)
        
        # --- Volume Control ---
        self.volume_slider = ft.Slider(
            min=0,
            max=100,
            value=80,
            divisions=20,
            label="{value}%",
            on_change=self.on_volume_changed,
            width=100
        )
        
        # --- Play/Pause Button ---
        self.play_pause_btn = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_size=24,
            on_click=self.on_play_pause_click,
            tooltip="Play/Pause"
        )
        
        # --- Timeline Slider ---
        self.timeline_slider = ft.Slider(
            min=0,
            max=100,
            value=0,
            on_change=self.on_timeline_changed,
            expand=True
        )
        
        # --- Time Labels ---
        self.current_time_text = ft.Text("00:00", size=12, color=ft.Colors.BLUE_GREY_400)
        self.total_time_text = ft.Text("00:00", size=12, color=ft.Colors.BLUE_GREY_400)
        
        # --- Row Media Controls ---
        self.media_controls_row = ft.Row(
            controls=[
                self.play_pause_btn,
                self.current_time_text,
                self.timeline_slider,
                self.total_time_text,
                ft.Icon(ft.Icons.VOLUME_UP, size=18, color=ft.Colors.BLUE_GREY_400),
                self.volume_slider,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        )
        
        # --- Layout Assembly ---
        left_panel = ft.Column([
            ft.Text("Daftar Klip:", weight=ft.FontWeight.BOLD),
            ft.Container(self.clip_list, border=ft.Border.all(1, ft.Colors.OUTLINE), border_radius=5, padding=5, expand=True)
        ], expand=1)
        
        right_panel = ft.Column([
            self.video_container,
            self.media_controls_row
        ], expand=2)
        
        top_split = ft.Row([left_panel, right_panel], height=300)
        
        meta_panel = ft.Column([
            ft.Text("Metadata Editor", weight=ft.FontWeight.BOLD),
            self.meta_title,
            self.meta_tags,
            ft.Row([self.btn_save_meta, self.btn_ai_meta])
        ])
        
        upload_panel = ft.Column([
            ft.Row([
                self.platform_yt, self.platform_tt, self.platform_ig, 
                self.upload_interval_input, self.max_effects_input
            ]),
            ft.Row([
                self.btn_pick_date, self.btn_pick_time, self.btn_clear_schedule, self.lbl_schedule_info
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.upload_progress,
            self.upload_status_text,
            ft.Row([
                ft.Container(expand=True), 
                self.cancel_upload_btn,
                self.render_btn,
                self.upload_btn
            ])
        ])

        self.content = ft.Column([
            ft.Row([self.project_dropdown, self.refresh_projects_btn, self.open_project_dir_btn]),
            top_split,
            ft.Divider(),
            meta_panel,
            ft.Divider(),
            upload_panel
        ])
        
        self.load_projects(None)

    def on_schedule_date_change(self, e: Any) -> None:
        import datetime
        val = e.control.value
        if val:
            # Flet DatePicker value adalah naive datetime dalam UTC.
            # Konversi ke zona waktu lokal pengguna agar tanggal tidak mundur 1 hari (contoh: 17:00 UTC menjadi keesokan harinya).
            val = val.replace(tzinfo=datetime.timezone.utc).astimezone()
            self.schedule_date = val.date()
        else:
            self.schedule_date = None
        self.update_schedule_info()

    def on_schedule_time_change(self, e: Any) -> None:
        self.schedule_time = e.control.value
        self.update_schedule_info()
        
    def clear_schedule(self, e: Any) -> None:
        self.schedule_date = None
        self.schedule_time = None
        self.update_schedule_info()

    def update_schedule_info(self) -> None:
        if self.schedule_date and self.schedule_time:
            self.lbl_schedule_info.value = f"Jadwal Mulai: {self.schedule_date.strftime('%Y-%m-%d')} {self.schedule_time.strftime('%H:%M')}"
        elif self.schedule_date:
            self.lbl_schedule_info.value = f"Jadwal Mulai: {self.schedule_date.strftime('%Y-%m-%d')} (00:00)"
        elif self.schedule_time:
            import datetime
            self.schedule_date = datetime.datetime.now().date()
            self.lbl_schedule_info.value = f"Jadwal Mulai: Hari ini {self.schedule_time.strftime('%H:%M')}"
        else:
            self.lbl_schedule_info.value = "Jadwal Mulai: Segera (+30 menit)"
            
        try:
            self.lbl_schedule_info.update()
        except Exception:
            pass

    def _create_video_player(self, path: str) -> ftv.Video:
        """Buat instansi video player baru dengan controls kustom."""
        abs_path = os.path.abspath(path)
        initial_vol = int(self.volume_slider.value if self.volume_slider.value is not None else 80)
        return ftv.Video(
            expand=True,
            playlist=[ftv.VideoMedia(abs_path)],
            controls=None,
            autoplay=False,
            muted=False,
            fit=ft.BoxFit.CONTAIN,
            aspect_ratio=9/16,
            volume=initial_vol,
            on_load=self.on_video_load,
            on_error=lambda e: log.error(f"❌ Video player error: {e.data}"),
            on_position_change=self.on_video_position_change,
            on_duration_change=self.on_video_duration_change,
            on_complete=self.on_video_complete,
        )

    def on_volume_changed(self, e: Any) -> None:
        """Ubah volume video player secara real-time."""
        vol = int(e.control.value)
        if self._video_player:
            self._video_player.volume = vol
            try:
                self._video_player.update()
            except Exception:
                pass

    def on_video_load(self, e: Any) -> None:
        # Set icon button ke Pause karena autoplay=True
        self.play_pause_btn.icon = ft.Icons.PAUSE
        try:
            self.play_pause_btn.update()
        except Exception:
            pass

    def on_video_complete(self, e: Any) -> None:
        # Kembalikan icon ke Play saat selesai
        self.play_pause_btn.icon = ft.Icons.PLAY_ARROW
        try:
            self.play_pause_btn.update()
        except Exception:
            pass

    def on_video_position_change(self, e: Any) -> None:
        pos: ft.Duration = e.data
        self.timeline_slider.value = pos.in_milliseconds
        self.current_time_text.value = self._format_ms(pos.in_milliseconds)
        try:
            self.timeline_slider.update()
            self.current_time_text.update()
        except Exception:
            pass

    def on_video_duration_change(self, e: Any) -> None:
        dur: ft.Duration = e.data
        self.timeline_slider.max = dur.in_milliseconds
        self.total_time_text.value = self._format_ms(dur.in_milliseconds)
        try:
            self.timeline_slider.update()
            self.total_time_text.update()
        except Exception:
            pass

    async def on_timeline_changed(self, e: Any) -> None:
        val = int(e.control.value)
        if self._video_player:
            await self._video_player.seek(val)

    async def on_play_pause_click(self, e: Any) -> None:
        if self._video_player:
            await self._video_player.play_or_pause()
            is_playing = await self._video_player.is_playing()
            self.play_pause_btn.icon = ft.Icons.PAUSE if is_playing else ft.Icons.PLAY_ARROW
            try:
                self.play_pause_btn.update()
            except Exception:
                pass

    def _format_ms(self, ms: int) -> str:
        seconds = ms // 1000
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def open_project_dir(self) -> None:
        if os.path.exists(config.output_dir):
            open_dir(config.output_dir)

    def load_projects(self, e: Any) -> None:
        self.project_dropdown.options.clear()
        if os.path.exists(config.output_dir):
            projects = []
            for item in os.listdir(config.output_dir):
                item_path = os.path.join(config.output_dir, item)
                if os.path.isdir(item_path):
                    if os.path.exists(os.path.join(item_path, "preview.json")):
                        projects.append(item)
            projects.sort(key=lambda x: os.path.getmtime(os.path.join(config.output_dir, x)), reverse=True)
            for p in projects:
                self.project_dropdown.options.append(ft.dropdown.Option(p))
                
            if projects:
                self.project_dropdown.value = projects[0]
                self.on_project_selected(None)
                
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def on_project_selected(self, e: Any) -> None:
        project_name = self.project_dropdown.value
        if not project_name:
            return
            
        self.current_project_dir = os.path.join(config.output_dir, project_name)
        
        meta_files = glob.glob(os.path.join(self.current_project_dir, "metadata_*.json"))
        mp4_files = glob.glob(os.path.join(self.current_project_dir, "*.mp4"))
        
        clip_indices = []
        for mf in meta_files:
            bname = os.path.basename(mf)
            if bname.startswith("metadata_") and bname != "metadata_merge.json":
                idx_str = bname.replace("metadata_", "").replace(".json", "")
                if idx_str.isdigit():
                    clip_indices.append(int(idx_str))
                    
        for mf in mp4_files:
            if os.path.basename(mf) == "merged.mp4":
                clip_indices.append("merge")
                
        clip_indices = list(set(clip_indices))
        
        def sort_key(x):
            if isinstance(x, int): return x
            return 9999
        clip_indices.sort(key=sort_key)
        
        self.clip_list.controls.clear()
        self.clips_to_upload.clear()
        
        first_clip_path = None
        first_clip_name = None
        
        for idx in clip_indices:
            if idx == "merge":
                display_name = "merged.mp4"
                video_path = os.path.join(self.current_project_dir, "merged.mp4")
                status = "✅ Rendered"
            else:
                display_name = f"clip_{idx}.mp4"
                video_path = os.path.join(self.current_project_dir, f"clip_{idx}.mp4")
                
                # Search for nosub file with any timestamp/crop_mode suffix
                nosub_matches = glob.glob(os.path.join(self.current_project_dir, f"clip_{idx}_*_nosub.mp4"))
                nosub_path = nosub_matches[0] if nosub_matches else os.path.join(self.current_project_dir, f"clip_{idx}_nosub.mp4")
                
                if os.path.exists(video_path):
                    status = "✅ Rendered"
                else:
                    video_path = nosub_path # Fallback to preview nosub
                    status = "🕒 Perlu Render"
                    
            if not first_clip_path:
                first_clip_path = video_path
                first_clip_name = display_name
                
            # Checkbox for upload/render
            chk = ft.Checkbox(value=False, data={"index": idx, "path": video_path, "status": status})
            self.clips_to_upload.append(chk)
            
            # Clickable row to load video
            def make_on_click(path=video_path, name=display_name):
                return lambda e: self.load_clip_data(path, name)
                
            status_color = ft.Colors.GREEN_400 if "Rendered" in status else ft.Colors.ORANGE_400
            
            row = ft.Row([
                chk,
                ft.TextButton(f"{display_name}", on_click=make_on_click()),
                ft.Text(f"[{status}]", color=status_color, size=12)
            ])
            self.clip_list.controls.append(row)
            
        if first_clip_path and first_clip_name:
            self.load_clip_data(first_clip_path, first_clip_name)
        else:
            # Tidak ada klip — tampilkan placeholder
            self._show_video_placeholder()
            
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def _show_video_placeholder(self) -> None:
        """Tampilkan placeholder saat tidak ada video yang dimuat."""
        self.video_container.content = self.video_placeholder
        self._video_player_active = False

    def load_clip_data(self, path: str, bname: str) -> None:
        self.current_clip_path = path
        
        # Validasi file ada dan tidak kosong
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            log.warning(f"File klip tidak valid: {path}")
            self._show_video_placeholder()
            return
        
        # Load Video — buat video player baru dengan controls
        player = self._create_video_player(path)
        self.video_container.content = player
        self._video_player = player
        self._video_player_active = True
        try:
            self.video_container.update()
        except Exception:
            pass
        
        # Extract index
        m = re.match(r'^clip_(\d+)\.mp4$', bname)
        if m:
            self.current_clip_index = m.group(1)
        elif bname == "merged.mp4":
            self.current_clip_index = "merge"
        else:
            self.current_clip_index = ""
            
        # Load Metadata if exists
        self.meta_title.value = ""
        self.meta_tags.value = ""
        
        if self.current_clip_index:
            meta_path = os.path.join(self.current_project_dir, f"metadata_{self.current_clip_index}.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.meta_title.value = data.get("title", "")
                        
                        tags = data.get("tags", [])
                        if isinstance(tags, list):
                            tags = " ".join(tags)
                        
                        self.meta_tags.value = tags
                except Exception as ex:
                    log.error(f"Gagal memuat metadata: {ex}")
                    
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception:
            pass

    def save_metadata(self, e: Any) -> None:
        if not self.current_clip_index:
            return
        meta_path = os.path.join(self.current_project_dir, f"metadata_{self.current_clip_index}.json")
        
        data = {}
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
        data["title"] = self.meta_title.value
        data["tags"] = (self.meta_tags.value or "").split()
        
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        show_snackbar(self._page, "Metadata berhasil disimpan!")

    def generate_ai_metadata(self, e: Any) -> None:
        if not self.current_clip_index:
            return

        from core.utils import get_preview_data
            
        # We need transcript to generate metadata. Let's read it from the existing metadata file.
        meta_path = os.path.join(self.current_project_dir, f"metadata_{self.current_clip_index}.json")
        preview_data = get_preview_data(self.current_project_dir)
        transcript = ""
        youtube_title = preview_data.get("title") or ""
        channel_name = preview_data.get("uploader") or ""
        
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # We might not have the raw transcript saved in metadata, but we might have 'highlight' or 'description'
                    # Usually, the detector gets the raw transcript. If not available, we use the old description/highlight as context.
                    transcript = data.get("highlight", data.get("description", ""))
            except Exception:
                pass
                
        # Get preview data for context
        preview_path = os.path.join(self.current_project_dir, "preview.json")
        if os.path.exists(preview_path):
            try:
                with open(preview_path, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
                    youtube_title = pdata.get("title", "")
                    channel_name = pdata.get("uploader", "")
            except Exception:
                pass
                
        if not transcript and not youtube_title:
            show_snackbar(self._page, "Tidak ada konteks video (transkrip/judul) untuk AI.", error=True)
            return
            
        # Run AI generation in background
        async def run_ai():
            import asyncio
            from core.ai.detector import ai_detector
            from gui.state import app_state
            
            app_state.append_log("Memulai Generate Metadata AI (Upload & Distribution)...")
            
            def hook(ev, data=None):
                if ev == "log":
                    app_state.append_log(str(data))
                    
            try:
                ai_config = config.to_dict()
                result = await asyncio.to_thread(
                    ai_detector.generate_metadata,
                    clip_text=transcript,
                    youtube_title=youtube_title,
                    channel_name=channel_name,
                    youtube_url=preview_data.get("webpage_url") or "",
                    ai_config=ai_config,
                    event_hook=hook,
                    language=preview_data.get("language") or "id"
                )
                if result:
                    self.meta_title.value = result.get("title", self.meta_title.value)
                    
                    new_tags = result.get("tags", [])
                    if isinstance(new_tags, list):
                        new_tags = " ".join(new_tags)
                        
                    self.meta_tags.value = new_tags
                    
                    app_state.append_log("Berhasil men-generate metadata dengan AI.")
                    self.save_metadata(None)
                    
                    if self.page: self.page.update()
            except Exception as ex:
                app_state.append_log(f"AI Error: {ex}")
                
        if self.page:
            self.page.run_task(run_ai)

    def cancel_upload(self, e: Any) -> None:
        self._is_upload_cancelled = True
        self.upload_status_text.value = "Sedang membatalkan upload..."
        self.upload_status_text.color = ft.Colors.RED_400
        self.cancel_upload_btn.disabled = True
        try:
            self._page.update()
        except Exception:
            pass

    def handle_upload(self, e: Any) -> None:
        selected_clips = [chk.data for chk in self.clips_to_upload if chk.value]
        if not selected_clips:
            show_snackbar(self._page, "Pilih setidaknya satu klip untuk di-upload!", error=True)
            return
            
        platforms = []
        if self.platform_yt.value: platforms.append("YouTube Shorts")
        if self.platform_tt.value: platforms.append("TikTok")
        if self.platform_ig.value: platforms.append("Instagram Reels")
        
        if not platforms:
            show_snackbar(self._page, "Pilih setidaknya satu platform tujuan upload!", error=True)
            return

        # Ambil interval
        try:
            interval_hours = float(str(self.upload_interval_input.value))
        except ValueError:
            interval_hours = 0.0

        try:
            config.max_effects_per_clip = int(str(self.max_effects_input.value))
        except ValueError:
            config.max_effects_per_clip = 3

        # Update config
        config.youtube.auto_upload = bool(self.platform_yt.value)
        config.tiktok.auto_upload = bool(self.platform_tt.value)
        config.instagram.auto_upload = bool(self.platform_ig.value)
        config.upload_interval = interval_hours
        config.save_to_file()

        # Disable UI & Tampilkan progress
        self.upload_btn.disabled = True
        self.cancel_upload_btn.visible = True
        self.cancel_upload_btn.disabled = False
        self.upload_progress.visible = True
        self.upload_progress.value = 0.0
        self._is_upload_cancelled = False
        self.upload_status_text.value = "Mempersiapkan upload..."
        self.upload_status_text.color = ft.Colors.AMBER_400
        self._page.update()

        async def run_uploader_task():
            import asyncio
            from core.uploaders.factory import UploaderFactory
            import datetime
            from gui.state import app_state
            
            # Load metadata untuk masing-masing klip terpilih
            metadata_dict = {}
            for clip_item in selected_clips:
                clip_path = clip_item["path"]
                bname = os.path.basename(clip_path)
                m = re.match(r'^clip_(\d+)\.mp4$', bname)
                if m:
                    idx = m.group(1)
                elif bname == "merged.mp4":
                    idx = "merge"
                else:
                    idx = ""
                
                # Baca file metadata jika ada
                meta = {"title": bname, "tags": ""}
                if idx:
                    meta_path = os.path.join(self.current_project_dir, f"metadata_{idx}.json")
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f_meta:
                                saved_meta = json.load(f_meta)
                                if saved_meta:
                                    tags_raw = saved_meta.get("tags", "")
                                    if isinstance(tags_raw, list):
                                        saved_meta["tags"] = " ".join(tags_raw)
                                    meta.update(saved_meta)
                        except Exception:
                            pass
                
                # Tambahkan default hashtags tanpa menimpa metadata tags
                default_tags = (config.default_hashtags or "").split()
                meta_tags = meta.get("tags", "").split()
                for dt in default_tags:
                    if dt not in meta_tags:
                        meta_tags.append(dt)
                meta["tags"] = " ".join(meta_tags)
                
                metadata_dict[clip_path] = meta

            total_tasks = len(selected_clips) * len(platforms)
            completed = 0

            # Instantiate uploaders
            uploaders = []
            for p in platforms:
                try:
                    uploader = await asyncio.to_thread(UploaderFactory.create, p)
                    uploaders.append(uploader)
                except Exception as ex:
                    app_state.append_log(f"[UPLOAD] Gagal memuat uploader {p}: {ex}")

            utc7_time = datetime.timezone(datetime.timedelta(hours=7))
            
            def adjust_for_quiet_hours(dt: datetime.datetime) -> tuple[datetime.datetime, bool]:
                # Jam sepi: 00:00 s/d 05:59 (WIB / UTC+7)
                if dt.hour < 6:
                    adjusted_dt = dt.replace(hour=6, minute=0, second=0, microsecond=0)
                    return adjusted_dt, True
                return dt, False

            if getattr(self, "schedule_date", None):
                s_date = self.schedule_date
                s_time = getattr(self, "schedule_time", None) or datetime.time(0, 0)
                dt_naive = datetime.datetime.combine(s_date, s_time)
                base_time = dt_naive.replace(tzinfo=utc7_time)
            else:
                base_time = datetime.datetime.now(utc7_time) + datetime.timedelta(minutes=30)

            last_publish_time = None
            for idx_clip, clip_item in enumerate(selected_clips):
                if self._is_upload_cancelled:
                    break
                    
                clip = clip_item["path"]
                clip_meta = metadata_dict.get(clip, {})
                clip_name = os.path.basename(clip)
                
                # Konstruksi description menggunakan title + hashtags
                title_val = clip_meta.get("title", "")
                tags_val = clip_meta.get("tags", "")
                clip_meta["description"] = f"{title_val}\n\n{tags_val}".strip()
                
                is_scheduled = interval_hours > 0 or getattr(self, "schedule_date", None)
                if is_scheduled:
                    publish_time = base_time + datetime.timedelta(hours=interval_hours * idx_clip)
                else:
                    publish_time = base_time

                orig_publish_time = publish_time

                # Jalankan guard jam sepi
                publish_time, _ = adjust_for_quiet_hours(publish_time)
                
                # Pastikan minimal ada selisih interval_hours dengan klip sebelumnya jika dijadwalkan
                if last_publish_time is not None and interval_hours > 0:
                    min_publish_time = last_publish_time + datetime.timedelta(hours=interval_hours)
                    if publish_time < min_publish_time:
                        publish_time = min_publish_time

                adjusted = (publish_time != orig_publish_time)
                if adjusted:
                    msg = f"[UPLOAD] ⚠️ Jadwal publikasi untuk {clip_name} digeser ke {publish_time.strftime('%d-%m-%Y %H:%M WIB')} (semula {orig_publish_time.strftime('%H:%M WIB')}) karena masuk jam sepi atau menyesuaikan antrean."
                    app_state.append_log(msg)
                    log.info(msg)

                last_publish_time = publish_time

                if is_scheduled or adjusted:
                    publish_time_utc = publish_time.astimezone(datetime.timezone.utc)
                    clip_meta["publish_at"] = publish_time_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

                for uploader in uploaders:
                    if self._is_upload_cancelled:
                        break
                        
                    log_msg = f"[UPLOAD] Memulai upload {clip_name} ke {uploader.platform_name}..."
                    app_state.append_log(log_msg)
                    self.upload_status_text.value = f"Mengunggah {clip_name} ke {uploader.platform_name}..."
                    self._page.update()

                    # Lakukan upload di thread blocking I/O
                    def do_upload():
                        try:
                            def hook(kind, data):
                                if kind == "log":
                                    app_state.append_log(str(data))
                            return uploader.upload(clip, clip_meta, event_hook=hook)
                        except Exception as ex_upload:
                            log.error(f"Uploader exception: {ex_upload}")
                            from core.uploaders.base import UploadResult
                            return UploadResult(success=False, platform=uploader.platform_name, error_msg=str(ex_upload))

                    result = await asyncio.to_thread(do_upload)
                    
                    if result.success:
                        app_state.append_log(f"[UPLOAD] ✅ Sukses upload ke {uploader.platform_name}: {result.url}")
                    else:
                        app_state.append_log(f"[UPLOAD] ❌ Gagal upload ke {uploader.platform_name}: {result.error_msg}")

                    completed += 1
                    self.upload_progress.value = completed / total_tasks
                    self._page.update()
                    
                    await asyncio.sleep(2.0)

            # Close uploaders
            for uploader in uploaders:
                if hasattr(uploader, 'close'):
                    try:
                        await asyncio.to_thread(uploader.close)
                    except Exception as e_close:
                        app_state.append_log(f"[UPLOAD] Gagal menutup uploader {uploader.platform_name}: {e_close}")

            # Selesai
            self.upload_btn.disabled = False
            self.cancel_upload_btn.visible = False
            self.upload_progress.visible = False
            
            if self._is_upload_cancelled:
                self.upload_status_text.value = "⚠️ Upload Dibatalkan"
                self.upload_status_text.color = ft.Colors.RED_400
                show_snackbar(self._page, "Proses upload dibatalkan.", error=True)

        self._page.run_task(run_uploader_task)
    def handle_render(self, e: Any) -> None:
        """Handler for Render Project button."""
        selected_items = [chk.data for chk in self.clips_to_upload if chk.value]
        if not selected_items:
            from gui.state import app_state
            app_state.append_log("Pilih minimal satu klip untuk di-render.")
            return
            
        project_name = self.project_dropdown.value
        if not project_name: return
        
        segments = []
        for item in selected_items:
            idx = item["index"]
            if idx == "merge": continue
            segments.append({"original_index": idx, "start": 0, "duration": 0})
            
        if not segments:
            from gui.state import app_state
            app_state.append_log("Tidak ada klip individual yang dipilih untuk dirender.")
            return

        payload = {
            "video_id": project_name,
            "segments": segments,
            "subtitle": True
        }
        
        try:
            config.max_effects_per_clip = int(str(self.max_effects_input.value))
        except ValueError:
            config.max_effects_per_clip = 3
        config.save_to_file()
        
        from gui.state import app_state
        from core.controller import controller
        from core.logger import log
        
        self._is_upload_cancelled = False
        app_state.set_processing(True, "Merender klip...")
        self.upload_progress.visible = True
        self.upload_progress.value = None
        self.upload_status_text.value = f"Merender {len(segments)} klip..."
        self.cancel_upload_btn.visible = True
        
        try:
            self.update()
        except Exception:
            pass

        class FletProgressReporter:
            def __init__(self, view):
                self.view = view
            def on_progress(self, label: str, current: int, total: int) -> None:
                if label == "total_targets":
                    self.view.upload_status_text.value = f"Total target: {total}"
                else:
                    self.view.upload_status_text.value = f"{label}: klip {current}/{total}"
                try:
                    self.view.update()
                except Exception: pass
            def on_log(self, message: str) -> None:
                app_state.append_log(message)
            def on_error(self, error: str) -> None:
                app_state.append_log(f"Error: {error}")
            def on_finished(self, result: Any) -> None:
                pass

        controller.reporter = FletProgressReporter(self)
        controller.render_uc.reporter = controller.reporter

        async def render_worker():
            import asyncio
            try:
                def check_cancelled():
                    return self._is_upload_cancelled

                log.info(f"Memulai render untuk project: {project_name}")
                res = await asyncio.to_thread(controller.execute_rendering, payload, check_cancelled)

                if self._is_upload_cancelled:
                    log.warning("Proses render dibatalkan.")
                    app_state.append_log("Render dibatalkan.")
                else:
                    success = res.get("success", 0)
                    log.info(f"Render selesai! Berhasil merender {success} klip.")
                    app_state.append_log(f"Render Selesai: {success} klip dirender.")
                    self.on_project_selected(None) # Refresh list
            except Exception as e:
                log.error(f"Error render: {e}")
                app_state.append_log(f"Error render: {e}")
            finally:
                app_state.set_processing(False)
                self.upload_progress.visible = False
                self.upload_status_text.value = ""
                self.cancel_upload_btn.visible = False
                try:
                    if self.page: self.page.update()
                    else: self.update()
                except Exception:
                    pass

        if self.page:
            self.page.run_task(render_worker)
