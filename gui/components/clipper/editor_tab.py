import os
import flet as ft
import json
from core.utils import read_json, write_json
from core.logger import log
from core.vfx import vfx_manager
from core.sfx import sfx_manager
from core.overlay import overlay_manager

class EditorTab(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.spacing = 20

        self.project_dropdown = ft.Dropdown(
            label="Pilih Project",
            on_select=self.on_project_changed,
            expand=True
        )
        self.clip_dropdown = ft.Dropdown(
            label="Pilih Klip",
            on_select=self.on_clip_changed,
            expand=True
        )
        self.refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Refresh List",
            on_click=self.load_projects
        )

        self.selection_row = ft.Row([
            self.project_dropdown,
            self.clip_dropdown,
            self.refresh_btn
        ])

        self.timeline_list = ft.ListView(
            spacing=10,
            padding=10,
            expand=True
        )

        # Load options (emotions) from SFX/VFX configs
        self.available_emotions = list(sfx_manager.sfx_map)

        self.emotion_filter_dropdown = ft.Dropdown(
            label="Filter Emosi",
            options=[ft.dropdown.Option("Semua")],
            value="Semua",
            on_select=self.on_filter_changed,
            expand=False
        )
        self.vfx_override_dropdown = ft.Dropdown(label="VFX Override", dense=True) # type: ignore
        self.sfx_override_dropdown = ft.Dropdown(label="SFX Override", dense=True) # type: ignore
        self.overlay_override_dropdown = ft.Dropdown(label="Overlay Override", dense=True) # type: ignore

        self.edit_effect_dialog = ft.AlertDialog(
            title=ft.Text("Edit Override Efek"),
            content=ft.Column([
                self.vfx_override_dropdown,
                self.sfx_override_dropdown,
                self.overlay_override_dropdown
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Simpan", on_click=self.save_effect_override),
                ft.TextButton("Batal", on_click=self.close_effect_dialog)
            ]
        )

        self.controls = [
            ft.Text("Editor Phase (Timeline, VFX, SFX, Overlays)", size=20, weight=ft.FontWeight.BOLD),
            ft.Text("Sesuaikan timeline emosi, VFX, SFX, dan Overlay untuk segmen video.", color=ft.Colors.WHITE_70),
            self.selection_row,
            self.emotion_filter_dropdown,
            ft.Container(
                content=self.timeline_list,
                bgcolor=ft.Colors.TRANSPARENT,
                border_radius=5,
                padding=10,
                expand=True
            )
        ]

        self.expand = True

        self.current_metadata = None
        self.current_metadata_path = None

    def did_mount(self):
        self.load_projects()

    def load_projects(self, e=None):
        self.project_dropdown.options.clear()
        self.clip_dropdown.options.clear()
        self.timeline_list.controls.clear()

        if os.path.exists("clips"):
            for folder in os.listdir("clips"):
                folder_path = os.path.join("clips", folder)
                if os.path.isdir(folder_path):
                    self.project_dropdown.options.append(
                        ft.dropdown.Option(key=folder, text=folder)
                    )

        self.update()

    def on_project_changed(self, e):
        project_id = self.project_dropdown.value
        if not project_id: return

        self.clip_dropdown.options.clear()
        self.timeline_list.controls.clear()

        folder_path = os.path.join("clips", project_id)
        if os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                if file.startswith("metadata_") and file.endswith(".json") and "merge" not in file:
                    self.clip_dropdown.options.append(
                        ft.dropdown.Option(key=file, text=file)
                    )

        if self.clip_dropdown.options:
            self.clip_dropdown.value = self.clip_dropdown.options[0].key
            self.on_clip_changed(None)
        else:
            self.update()

    def on_clip_changed(self, e):
        project_id = self.project_dropdown.value
        clip_file = self.clip_dropdown.value
        if not project_id or not clip_file: return

        self.current_metadata_path = os.path.join("clips", project_id, clip_file)
        if os.path.exists(self.current_metadata_path):
            self.current_metadata = read_json(self.current_metadata_path)
            self.render_timeline()

    def render_timeline(self):
        self.timeline_list.controls.clear()
        if not self.current_metadata: return

        enriched = self.current_metadata.get("enriched_transcript", [])

        unique_emotions = set()
        for w in enriched:
            unique_emotions.add(w.get("emotion", "neutral"))

        current_filter = self.emotion_filter_dropdown.value
        self.emotion_filter_dropdown.options = [ft.dropdown.Option("Semua")] + [ft.dropdown.Option(e) for e in sorted(list(unique_emotions))]
        if current_filter not in unique_emotions and current_filter != "Semua":
            self.emotion_filter_dropdown.value = "Semua"
            filter_val = "Semua"
        else:
            filter_val = current_filter

        visual_emotions = self.current_metadata.get("visual_emotions", [])

        for i, word_data in enumerate(enriched):
            emotion = word_data.get("emotion", "neutral")
            if filter_val != "Semua" and emotion != filter_val:
                continue
            word = word_data.get("word", "")
            start = word_data.get("start", 0)
            end = word_data.get("end", 0)
            voice_level = word_data.get("voice_level", "normal")
            color_hex = word_data.get("color", "#FFFFFF")

            safe_color = color_hex if str(color_hex).startswith("#") else ft.Colors.WHITE

            # Temukan visual emotion yang terjadi pada waktu kata ini diucapkan
            visual_emo_text = ""
            for ve in visual_emotions:
                ve_time = ve.get("time", 0)
                if start <= ve_time <= end:
                    ve_emo = ve.get("emotion", "")
                    ve_score = ve.get("score", 0.0)
                    visual_emo_text = f"📷 {ve_emo} ({ve_score:.1f}%)"
                    break

            emo_dropdown = ft.Dropdown(
                value=emotion,
                options=[ft.dropdown.Option(e) for e in self.available_emotions],
                width=150,
                data=i, # store index
                on_select=self.on_emotion_changed,
                dense=True
            )

            color_preview = ft.Container(
                width=16, height=16, border_radius=8,
                bgcolor=safe_color,
                tooltip=f"Warna: {color_hex}"
            )

            info_col = ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.MIC, size=14, color=ft.Colors.WHITE_70),
                    ft.Text(f"Voice: {voice_level}", size=12, color=ft.Colors.WHITE_70)
                ], spacing=5),
                ft.Text(visual_emo_text, size=12, color=ft.Colors.BLUE_300) if visual_emo_text else ft.Container()
            ], spacing=2, width=150)

            edit_btn = ft.IconButton(
                icon=ft.Icons.SETTINGS,
                tooltip="Edit Override Efek",
                data=i,
                on_click=self.open_effect_dialog
            )

            row = ft.Row([
                ft.Text(f"[{start:.2f}s - {end:.2f}s]", width=120),
                ft.Row([color_preview, ft.Text(f'"{word}"', weight=ft.FontWeight.BOLD)], width=200),
                info_col,
                ft.Row([emo_dropdown, edit_btn])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            self.timeline_list.controls.append(row)

        if not enriched:
            self.timeline_list.controls.append(ft.Text("Tidak ada transkripsi pada klip ini.", color=ft.Colors.RED_400))

        self.update()

    def on_emotion_changed(self, e):
        if not self.current_metadata or not self.current_metadata_path: return
        idx = e.control.data
        new_emotion = e.control.value

        enriched = self.current_metadata.get("enriched_transcript", [])
        if idx < len(enriched):
            enriched[idx]["emotion"] = new_emotion
            # Save immediately
            try:
                write_json(self.current_metadata_path, self.current_metadata, indent=2)
                log.info(f"Updated emotion for word '{enriched[idx].get('word')}' to '{new_emotion}'")
            except Exception as ex:
                log.error(f"Failed to save metadata: {ex}")

    def on_filter_changed(self, e):
        self.render_timeline()
        try:
            if self.page: self.page.update()
            else: self.update()
        except Exception: pass

    def open_effect_dialog(self, e):
        idx = e.control.data
        if not self.current_metadata: return
        enriched = self.current_metadata.get("enriched_transcript", [])
        if idx >= len(enriched): return

        word_data = enriched[idx]
        emotion = word_data.get("emotion", "neutral")

        # Populate options based on current emotion
        self.vfx_override_dropdown.options = [
            ft.dropdown.Option(key="random", text="Random (Default)"),
        ]
        vfx_list = vfx_manager.vfx_map.get(emotion, [])
        for i_vfx, vf in enumerate(vfx_list):
            if isinstance(vf, dict) and vf.get("name"):
                label = str(vf.get("name"))
            else:
                label = json.dumps(vf) if vf else "None"
            if len(label) > 40: label = label[:37] + "..."
            self.vfx_override_dropdown.options.append(ft.dropdown.Option(key=str(i_vfx), text=label))

        self.sfx_override_dropdown.options = [
            ft.dropdown.Option(key="random", text="Random (Default)"),
        ]
        sfx_data = sfx_manager.sfx_map.get(emotion, {})
        sfx_list = sfx_data.get("files", []) if isinstance(sfx_data, dict) else (sfx_data if isinstance(sfx_data, list) else [])
        for i_sfx, sf in enumerate(sfx_list):
            label = sf if sf else "None (No Effect)"
            self.sfx_override_dropdown.options.append(ft.dropdown.Option(key=str(i_sfx), text=label))

        self.overlay_override_dropdown.options = [
            ft.dropdown.Option(key="random", text="Random (Default)"),
        ]
        ov_list = overlay_manager.overlay_map.get(emotion, [])
        for i_ov, ov in enumerate(ov_list):
            if isinstance(ov, dict) and ov.get("name"):
                label = str(ov.get("name"))
            else:
                label = ov.get("file", "None") if isinstance(ov, dict) else "None"
            self.overlay_override_dropdown.options.append(ft.dropdown.Option(key=str(i_ov), text=label))

        self.vfx_override_dropdown.value = str(word_data.get("vfx_override", "random"))
        self.sfx_override_dropdown.value = str(word_data.get("sfx_override", "random"))
        self.overlay_override_dropdown.value = str(word_data.get("overlay_override", "random"))
        self.edit_effect_dialog.data = idx
        if self.edit_effect_dialog not in self.page_ref.overlay:
            self.page_ref.overlay.append(self.edit_effect_dialog)
        self.edit_effect_dialog.open = True
        self.page_ref.update()

    def save_effect_override(self, e):
        idx = self.edit_effect_dialog.data
        if not self.current_metadata or not self.current_metadata_path: return
        enriched = self.current_metadata.get("enriched_transcript", [])
        if idx < len(enriched):
            enriched[idx]["vfx_override"] = self.vfx_override_dropdown.value
            enriched[idx]["sfx_override"] = self.sfx_override_dropdown.value
            enriched[idx]["overlay_override"] = self.overlay_override_dropdown.value

            try:
                write_json(self.current_metadata_path, self.current_metadata, indent=2)
                log.info(f"Updated effect overrides for word idx {idx}")
            except Exception as ex:
                log.error(f"Failed to save metadata overrides: {ex}")

        self.edit_effect_dialog.open = False
        self.page_ref.update()

    def close_effect_dialog(self, e):
        self.edit_effect_dialog.open = False
        self.page_ref.update()
