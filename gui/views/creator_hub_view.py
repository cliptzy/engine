import threading
import flet as ft
from typing import Any, Callable, Optional, cast

from core.channel_manager import channel_manager
from core.models import VideoInfo
from core.logger import log
from gui.components.video_card import VideoCard


class CreatorHubView(ft.Container):
    def __init__(self, on_video_select: Optional[Callable[[str], Any]] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.expand = True
        self.on_video_select = on_video_select
        
        self.active_channel_id: Optional[str] = None
        self.current_tab = "upload"
        self.current_page = 1
        self.current_search = ""
        self.current_sort = "views"
        self.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        self.padding = 16
        self.border_radius = 8
        self._build_ui()
        self.load_channels()

    def _build_ui(self):
        self.input_handle = ft.TextField(
            hint_text="Tambah YouTuber: username (@WindahBasudara) atau URL channel...",
            expand=True,
            on_submit=self.on_add_channel,
        )
        self.btn_add_channel = ft.Button(
            "➕ Daftarkan YouTuber",
            on_click=self.on_add_channel,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY)
        )
        self.btn_reload_channels = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Muat Ulang Daftar YouTuber",
            on_click=lambda _: self.load_channels()
        )
        top_bar = ft.Row(
            controls=cast(list[ft.Control], [
                ft.Text("🎮 YouTuber Channel Catalog", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                self.btn_reload_channels,
                self.input_handle,
                self.btn_add_channel
            ]),
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        self.channels_grid = ft.GridView(
            expand=True,
            runs_count=3,
            max_extent=350,
            child_aspect_ratio=3.0,
            spacing=10,
            run_spacing=10,
        )
        self.channels_page = ft.Column(
            expand=True,
            controls=cast(list[ft.Control], [
                ft.Text("Pilih YouTuber untuk menjelajahi daftar video Upload & Live Stream:", color=ft.Colors.OUTLINE),
                self.channels_grid
            ])
        )

        self.active_channel_title = ft.Text("Channel: -", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.LIGHT_BLUE_400)
        self.active_channel_subs = ft.Text("- subscriber", color=ft.Colors.OUTLINE)
        
        self.radio_uploads = ft.Radio(value="upload", label="📹 Uploads")
        self.radio_live = ft.Radio(value="live", label="🔴 Live Streams")
        self.tab_group = ft.RadioGroup(
            value="upload",
            content=ft.Row(controls=cast(list[ft.Control], [self.radio_uploads, self.radio_live]))
        )
        self.tab_group.on_change = self.on_tab_changed # type: ignore
        
        self.search_input = ft.TextField(
            hint_text="🔍 Cari judul video...", 
            expand=True,
            on_change=self.on_search_changed
        )
        self.sort_combo = ft.Dropdown(
            options=[
                ft.dropdown.Option("views", "🔥 Views Terbanyak"),
                ft.dropdown.Option("newest", "🆕 Terbaru"),
                ft.dropdown.Option("duration", "⏱ Durasi Terlama"),
            ],
            value="views",
            width=200
        )
        self.sort_combo.on_change = self.on_sort_changed # type: ignore
        
        self.videos_grid = ft.GridView(
            expand=True,
            runs_count=4,
            max_extent=250,
            child_aspect_ratio=0.8,
            spacing=14,
            run_spacing=14,
        )
        
        self.btn_prev_page = ft.Button("◀ Prev", on_click=self.on_prev_page, disabled=True)
        self.page_info_label = ft.Text("Halaman 1 dari 1", weight=ft.FontWeight.BOLD)
        self.btn_next_page = ft.Button("Next ▶", on_click=self.on_next_page, disabled=True)
        
        self.videos_page = ft.Column(
            expand=True,
            visible=False,
            controls=cast(list[ft.Control], [
                ft.Row(controls=cast(list[ft.Control], [
                    ft.TextButton("⬅ Kembali ke Daftar YouTuber", on_click=self.show_channels_grid),
                    self.active_channel_title,
                    self.active_channel_subs
                ])),
                ft.Row(controls=cast(list[ft.Control], [
                    self.tab_group,
                    self.search_input,
                    ft.Text("Urutkan:"),
                    self.sort_combo
                ])),
                self.videos_grid,
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=cast(list[ft.Control], [
                        self.btn_prev_page,
                        self.page_info_label,
                        self.btn_next_page
                    ])
                )
            ])
        )

        self.content = ft.Column(
            expand=True,
            controls=cast(list[ft.Control], [
                top_bar,
                self.channels_page,
                self.videos_page
            ])
        )

    def load_channels(self):
        self.channels_grid.controls.clear()
        channels = channel_manager.get_all_channels()
        for ch in channels:
            card = self.create_channel_card(ch)
            self.channels_grid.controls.append(card)
        try:
            self.page.update()
        except Exception:
            pass

    def create_channel_card(self, ch: dict) -> ft.Control:
        c_id = ch.get("id")
        c_name = ch.get("name", "YouTuber")
        c_subs = ch.get("subscribers_str", "")
        handle = ch.get("handle", "@channel")
        avatar_url = ch.get("avatar")

        avatar_content: ft.Control
        if avatar_url:
            avatar_content = ft.Image(src=avatar_url, width=54, height=54, fit=ft.BoxFit.COVER, border_radius=27)
        else:
            avatar_content = ft.Container(
                width=54, height=54, border_radius=27, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                content=ft.Text("🎮", size=20), alignment=ft.Alignment(0, 0)
            )

        def on_hover(e) -> None:
            e.control.scale = 1.02 if e.data == "true" else 1.0 # type: ignore
            e.control.update() # type: ignore

        b_side = ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)
        card = ft.Container(
            padding=10,
            border=ft.Border(top=b_side, bottom=b_side, left=b_side, right=b_side),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE,
            on_click=lambda e: self.open_channel_catalog(c_id, c_name, c_subs), # type: ignore
            on_hover=on_hover,
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            content=ft.Row(
                spacing=12,
                controls=cast(list[ft.Control], [
                    avatar_content,
                    ft.Column(
                        expand=True,
                        spacing=4,
                        controls=cast(list[ft.Control], [
                            ft.Text(str(c_name), weight=ft.FontWeight.BOLD, size=14),
                            ft.Text(f"{handle} • {c_subs}", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("▶ Jelajahi Video Catalog", size=11, color=ft.Colors.LIGHT_BLUE_400, weight=ft.FontWeight.BOLD)
                        ])
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED_400,
                        tooltip=f"Hapus {c_name}",
                        on_click=lambda e, cid=c_id, cname=c_name: self.delete_channel(e, cid, cname)
                    )
                ])
            )
        )
        return card

    def on_add_channel(self, e: Any):
        query = self.input_handle.value
        if not query:
            return
            
        self.btn_add_channel.disabled = True
        self.btn_add_channel.text = "⏳ Scraping Channel..." # type: ignore
        if self.page:
            self.page.update()
            
        async def scrape_worker():
            import asyncio
            from core.logger import log
            try:
                log.info(f"Scraping channel Youtube: {query}")
                ch_data = await asyncio.to_thread(channel_manager.add_channel_by_url_or_handle, query) # type: ignore
                if ch_data:
                    log.info(f"Berhasil mendaftarkan channel: {ch_data.get('name')}")
                    self.input_handle.value = ""
                    self.load_channels()
                    self.open_channel_catalog(
                        ch_data.get("id"), 
                        str(ch_data.get("name", "")), 
                        str(ch_data.get("subscribers_str", ""))
                    )
            except Exception as ex:
                log.error(f"Gagal menambahkan channel: {ex}")
            finally:
                self.btn_add_channel.disabled = False
                self.btn_add_channel.text = "➕ Daftarkan YouTuber" # type: ignore
                if self.page:
                    self.page.update()

        if self.page:
            self.page.run_task(scrape_worker)

    def delete_channel(self, e: Any, channel_id: Optional[str], channel_name: str) -> None:
        if not channel_id:
            return
        from core.channel_manager import channel_manager
        # Disable button to indicate action and prevent duplicate clicks
        e.control.disabled = True
        try:
            channel_manager.delete_channel(channel_id)
            self.load_channels()
            snack = ft.SnackBar(ft.Text(f"Channel {channel_name} berhasil dihapus!"), bgcolor=ft.Colors.GREEN_700) # type: ignore
            if self.page:
                self.page.overlay.append(snack)
                snack.open = True
                self.page.update()
        except Exception as ex:
            log.error(f"Gagal menghapus channel: {ex}")

    def show_channels_grid(self, e: Any = None):
        self.channels_page.visible = True
        self.videos_page.visible = False
        if self.page:
            self.page.update()

    def open_channel_catalog(self, channel_id: Optional[str], channel_name: str, channel_subs: str = ""):
        if not channel_id:
            return
        self.active_channel_id = channel_id
        self.active_channel_title.value = f"Channel: {channel_name}"
        self.active_channel_subs.value = channel_subs
        self.current_page = 1
        
        self.channels_page.visible = False
        self.videos_page.visible = True
        
        self.load_video_catalog()

    def on_tab_changed(self, e: Any):
        self.current_tab = str(self.tab_group.value)
        self.current_page = 1
        self.load_video_catalog()

    def on_search_changed(self, e: Any):
        self.current_search = str(self.search_input.value).strip()
        self.current_page = 1
        self.load_video_catalog()

    def on_sort_changed(self, e: Any):
        self.current_sort = str(self.sort_combo.value)
        self.current_page = 1
        self.load_video_catalog()

    def on_prev_page(self, e: Any):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_video_catalog()

    def on_next_page(self, e: Any):
        self.current_page += 1
        self.load_video_catalog()

    def load_video_catalog(self):
        if not self.active_channel_id:
            return
            
        res = channel_manager.get_channel_videos_catalog(
            channel_id=self.active_channel_id,
            tab=self.current_tab,
            search=self.current_search,
            sort_by=self.current_sort,
            page=self.current_page,
            per_page=12
        )
        
        videos = res.get("videos", [])
        total_pages = res.get("total_pages", 1)
        self.current_page = res.get("current_page", 1)
        
        self.page_info_label.value = f"Halaman {self.current_page} dari {total_pages} ({res.get('total_items', 0)} video)"
        self.btn_prev_page.disabled = (self.current_page <= 1)
        self.btn_next_page.disabled = (self.current_page >= total_pages)
        
        self.videos_grid.controls.clear()
        for v in videos:
            v_id = v.get("id", "")
            title = v.get("title", "Untitled")
            duration = v.get("duration", 0)
            url = v.get("url", "")
            thumbnail = v.get("thumbnail", "")
            
            vi = VideoInfo(
                video_id=v_id,
                title=title,
                duration=float(duration),
                url=url,
                thumbnail_url=thumbnail
            )
            card = VideoCard(video_info=vi, on_click=self._create_video_click_handler(url))
            self.videos_grid.controls.append(card)
            
        if self.page:
            self.page.update()

    def _create_video_click_handler(self, url: str) -> Callable[[Any], None]:
        def handler(e: Any):
            if self.on_video_select:
                self.on_video_select(url)
        return handler
