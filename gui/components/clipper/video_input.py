import flet as ft
from typing import Any, cast
from core import controller
from gui.event_bus import event_bus

class VideoInput(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.padding = 16
        self.border_radius = 8
        
        self.url_input = ft.TextField(
            hint_text="Tempel URL YouTube di sini (watch / shorts / youtu.be)...",
            expand=True,
            on_submit=self.on_fetch_clicked
        )
        
        self.import_cookies_btn = ft.Button(
            content=ft.Text("🔑 Import Cookies"), # type: ignore
            on_click=self.on_cookies_picked
        )
        
        self.fetch_btn = ft.Button(
            content=ft.Text("🔍 Load Video"), # type: ignore
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE),
            on_click=self.on_fetch_clicked
        )
        
        # type: ignore
        self.cookies_picker = ft.FilePicker()
        self.page_ref.services.append(self.cookies_picker)
        
        self.content = ft.Row(
            controls=cast(list[ft.Control], [
                self.url_input,
                self.import_cookies_btn,
                self.fetch_btn
            ]),
            spacing=8
        )
        
    async def on_cookies_picked(self, e: Any) -> None:
        files = await self.cookies_picker.pick_files(
            dialog_title="Pilih File Cookies Netscape",
            allowed_extensions=["txt"]
        )
        if files and len(files) > 0 and files[0].path:
            try:
                controller.import_cookies(files[0].path)
                self._show_snackbar("File cookies.txt berhasil diimpor!")
            except Exception as ex:
                self._show_snackbar(f"Gagal mengimpor cookies: {ex}", error=True)

    def on_fetch_clicked(self, e: Any = None) -> None:
        url = self.url_input.value.strip() if self.url_input.value else ""
        if url:
            event_bus.publish("fetch_requested", url=url)

    def set_loading(self, loading: bool) -> None:
        self.fetch_btn.disabled = loading
        # type: ignore
        self.fetch_btn.text = "Loading..." if loading else "🔍 Load Video"  # type: ignore
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
