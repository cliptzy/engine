import flet as ft
from core.sfx import sfx_manager
import os
import subprocess
import asyncio

class SFXView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.spacing = 15
        self.scroll = ft.ScrollMode.AUTO
        self.expand = True
        
        from typing import Any
        self.current_player: Any = None
        self.current_playing_btn: Any = None
        
        self.emotion_dropdown = ft.Dropdown(
            label="Pilih Emosi",
            options=[],
            on_select=self.on_emotion_change, 
            expand=True
        )
        self.sfx_list_view = ft.ListView(spacing=10, expand=True)
        
        self.file_picker = ft.FilePicker()
        self.page_ref.services.append(self.file_picker)
        
        self.btn_add_emotion = ft.Button("Tambah Emosi Baru", icon=ft.Icons.ADD, on_click=self.on_add_emotion)
        self.btn_add_sfx = ft.Button("Tambah SFX ke Emosi ini", icon=ft.Icons.MUSIC_NOTE, on_click=self.on_add_sfx, disabled=True)
        
        self.tf_emotion_desc = ft.TextField(
            label="Deskripsi / Kata Kunci (Panduan untuk AI)",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
            on_change=self.on_desc_change,
            disabled=True
        )
        
        self.content_controls = [
            ft.Text("Manajemen SFX (Sound Effects)", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("SFX yang didaftarkan di sini akan disisipkan secara acak saat subtitle klip memiliki emosi yang sesuai."),
            ft.Row([
                self.emotion_dropdown,
                self.btn_add_emotion
            ]),
            self.tf_emotion_desc,
            ft.Divider(),
            ft.Row([
                ft.Text("Daftar File SFX:", size=16, weight=ft.FontWeight.BOLD),
                self.btn_add_sfx
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.sfx_list_view
        ]
        
        self.controls = self.content_controls
        
    def did_mount(self):
        sfx_manager.load()
        self.update_emotion_dropdown()
        
    def update_emotion_dropdown(self):
        self.emotion_dropdown.options = [
            ft.dropdown.Option(key) for key in sfx_manager.sfx_map.keys()
        ]
        if self.emotion_dropdown.value not in sfx_manager.sfx_map:
            self.emotion_dropdown.value = None
            self.btn_add_sfx.disabled = True
            
        self.refresh_sfx_list()
        try:
            self.update()
        except Exception:
            pass
            
    def on_emotion_change(self, e):
        if self.emotion_dropdown.value:
            self.btn_add_sfx.disabled = False
            self.tf_emotion_desc.disabled = False
        else:
            self.btn_add_sfx.disabled = True
            self.tf_emotion_desc.disabled = True
        self.refresh_sfx_list()
        
    def on_desc_change(self, e):
        emotion = self.emotion_dropdown.value
        if emotion and emotion in sfx_manager.sfx_map:
            emo_data = sfx_manager.sfx_map[emotion]
            if isinstance(emo_data, dict):
                emo_data["desc"] = self.tf_emotion_desc.value
            else:
                sfx_manager.sfx_map[emotion] = {"desc": self.tf_emotion_desc.value, "files": emo_data}
            sfx_manager.save()
            
    def refresh_sfx_list(self):
        self.sfx_list_view.controls.clear()
        
        emotion = self.emotion_dropdown.value
        if not emotion or emotion not in sfx_manager.sfx_map:
            self.tf_emotion_desc.value = ""
            self.sfx_list_view.controls.append(ft.Text("Pilih emosi terlebih dahulu."))
            try:
                self.update()
            except Exception:
                pass
            return
            
        emo_data = sfx_manager.sfx_map[emotion]
        desc = emo_data.get("desc", "") if isinstance(emo_data, dict) else ""
        self.tf_emotion_desc.value = desc
        
        sfx_list = emo_data.get("files", []) if isinstance(emo_data, dict) else emo_data
        
        if not sfx_list:
            self.sfx_list_view.controls.append(ft.Text("Tidak ada SFX untuk emosi ini."))
        else:
            from core.utils import get_app_root
            for idx, filename in enumerate(sfx_list):
                file_path = os.path.join(get_app_root(), "assets", "audio", filename)
                is_exist = os.path.exists(file_path)
                
                status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN) if is_exist else ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED)
                status_text = "File Ditemukan" if is_exist else "File Hilang!"
                
                btn_play = ft.IconButton(ft.Icons.PLAY_ARROW, tooltip="Play", disabled=not is_exist) # type: ignore
                
                def make_play_click(fname, btn):
                    async def play_click(e):
                        is_stopping_current = (getattr(self, 'current_playing_btn', None) == btn)
                        
                        # Matikan audio yang sedang diputar jika ada
                        if getattr(self, 'current_player', None):
                            try:
                                self.current_player.kill()
                            except Exception:
                                pass
                            self.current_player = None
                            
                        # Reset tombol sebelumnya yang sedang memutar
                        if getattr(self, 'current_playing_btn', None):
                            self.current_playing_btn.icon = ft.Icons.PLAY_ARROW
                            self.current_playing_btn.tooltip = "Play"
                            try:
                                self.current_playing_btn.update()
                            except Exception:
                                pass
                            self.current_playing_btn = None

                        if is_stopping_current:
                            # Jika pengguna menekan tombol Stop pada audio ini, cukup berhenti
                            btn.icon = ft.Icons.PLAY_ARROW
                            btn.tooltip = "Play"
                            btn.update()
                            return

                        fp = os.path.join(get_app_root(), "assets", "audio", fname)
                        if os.path.exists(fp):
                            abs_path = os.path.abspath(fp)
                            try:
                                self.current_player = await asyncio.create_subprocess_exec(
                                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", abs_path,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                                )
                                btn.icon = ft.Icons.STOP
                                btn.tooltip = "Stop"
                                btn.update()
                                self.current_playing_btn = btn
                                
                                await self.current_player.wait()
                                
                                # Jika tombol ini masih menjadi tombol aktif saat pemutaran selesai
                                if getattr(self, 'current_playing_btn', None) == btn:
                                    btn.icon = ft.Icons.PLAY_ARROW
                                    btn.tooltip = "Play"
                                    try:
                                        btn.update()
                                    except Exception:
                                        pass
                                    self.current_playing_btn = None
                            except Exception as ex:
                                from gui.state import app_state
                                app_state.append_log(f"Gagal memutar audio: {ex}")
                        else:
                            from gui.state import app_state
                            app_state.append_log(f"Error: {fname} tidak ditemukan di assets/audio/")
                    return lambda e: self.page_ref.run_task(play_click, e)
                    
                btn_play.on_click = make_play_click(filename, btn_play)
                    
                def make_delete_click(emo, index):
                    def delete_click(e):
                        if isinstance(sfx_manager.sfx_map[emo], dict):
                            sfx_manager.sfx_map[emo]["files"].pop(index)
                        else:
                            sfx_manager.sfx_map[emo].pop(index) # type: ignore
                        sfx_manager.save()
                        self.refresh_sfx_list()
                    return delete_click
                
                row = ft.Container(
                    content=ft.Row([
                        status_icon,
                        ft.Text(filename, expand=True, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(status_text, size=12, color=ft.Colors.GREEN if is_exist else ft.Colors.RED),
                        btn_play,
                        ft.IconButton(ft.Icons.DELETE, on_click=make_delete_click(emotion, idx), tooltip="Hapus", icon_color=ft.Colors.RED) # type: ignore
                    ]),
                    padding=10,
                    bgcolor=ft.Colors.TRANSPARENT,
                    border_radius=8
                )
                self.sfx_list_view.controls.append(row)
                
        try:
            self.update()
        except Exception:
            pass
            
    def on_add_emotion(self, e):
        def add_click(e2):
            val = tf_emo.value
            if val and val not in sfx_manager.sfx_map:
                sfx_manager.sfx_map[val] = {"desc": "", "files": []}
                sfx_manager.save()
                self.emotion_dropdown.value = val
                self.update_emotion_dropdown()
            dialog.open = False
            self.page_ref.update()
            
        tf_emo = ft.TextField(label="Nama Emosi (contoh: happy, sad)")
        dialog = ft.AlertDialog(
            title=ft.Text("Tambah Emosi Baru"),
            content=tf_emo,
            actions=[ft.TextButton("Batal", on_click=lambda e: setattr(dialog, 'open', False) or self.page_ref.update()), ft.TextButton("Simpan", on_click=add_click)]
        )
        self.page_ref.overlay.append(dialog)
        dialog.open = True
        self.page_ref.update()
    def update_audio_dropdown(self):
        from core.utils import get_app_root
        import glob
        audio_dir = os.path.join(get_app_root(), "assets", "audio")
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)
        files = [os.path.basename(p) for p in glob.glob(os.path.join(audio_dir, "*.mp3"))]
        files += [os.path.basename(p) for p in glob.glob(os.path.join(audio_dir, "*.wav"))]
        files = list(set(files))
        if hasattr(self, 'dialog_dropdown'):
            self.dialog_dropdown.options = [ft.dropdown.Option(f) for f in files]
            try:
                self.dialog_dropdown.update()
            except Exception:
                pass

    def on_add_sfx(self, e):
        emotion = self.emotion_dropdown.value
        if not emotion: return
        
        self.dialog_dropdown = ft.Dropdown(label="Pilih File Audio", expand=True)
        self.update_audio_dropdown()
        def add_click(e2):
            val = self.dialog_dropdown.value
            if val:
                if isinstance(sfx_manager.sfx_map[emotion], dict):
                    if val not in sfx_manager.sfx_map[emotion]["files"]:
                        sfx_manager.sfx_map[emotion]["files"].append(val)
                else:
                    if val not in sfx_manager.sfx_map[emotion]:
                        sfx_manager.sfx_map[emotion].append(val) # type: ignore
                sfx_manager.save()
                self.refresh_sfx_list()
            self.add_dialog.open = False
            self.page_ref.update()
            
        async def handle_upload(e):
            files = await self.file_picker.pick_files(allowed_extensions=["mp3", "wav"])
            if files:
                import shutil
                from core.utils import get_app_root
                import os
                audio_dir = os.path.join(get_app_root(), "assets", "audio")
                if not os.path.exists(audio_dir):
                    os.makedirs(audio_dir)
                for f in files:
                    if f.path:
                        dest = os.path.join(audio_dir, f.name)
                        shutil.copy(f.path, dest)
                        self.update_audio_dropdown()
                        self.dialog_dropdown.value = f.name
                self.page_ref.update()
                
        btn_upload = ft.Button("Upload", icon=ft.Icons.UPLOAD, on_click=lambda e: self.page_ref.run_task(handle_upload, e))
        row_content = ft.Row([self.dialog_dropdown, btn_upload])
        
        self.add_dialog = ft.AlertDialog(
            title=ft.Text(f"Tambah SFX ke '{emotion}'"),
            content=row_content,
            actions=[ft.TextButton("Batal", on_click=lambda e: setattr(self.add_dialog, 'open', False) or self.page_ref.update()), ft.TextButton("Simpan", on_click=add_click)]
        )
        self.page_ref.overlay.append(self.add_dialog)
        self.add_dialog.open = True
        self.page_ref.update()
