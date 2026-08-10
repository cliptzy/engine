import flet as ft
from core.supabase_sync import supabase_sync
from gui.state import app_state
from core.logger import log
import asyncio

class LoginView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.expand = True
        self.alignment = ft.Alignment(0, 0)
        
        self.btn_login = ft.Button(
            "Login dengan Google", 
            icon=ft.Icons.LOGIN,
            on_click=self.start_google_login,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
        )
        
        self.info_text = ft.Text(
            "Silakan login menggunakan Google untuk mengakses aplikasi",
            size=16,
            text_align=ft.TextAlign.CENTER
        )
        
        self.progress_ring = ft.ProgressRing(visible=False)
        
        self.content = ft.Column(
            [
                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.BLUE_400),
                ft.Text("Login", size=28, weight=ft.FontWeight.BOLD),
                self.info_text,
                ft.Container(height=20),
                self.btn_login,
                ft.Container(height=20),
                self.progress_ring
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )

    def start_google_login(self, e):
        self.btn_login.disabled = True
        self.progress_ring.visible = True
        self.info_text.value = "Silakan ikuti instruksi di browser Anda..."
        self.update()
        
        async def do_login():
            import asyncio
            success = await asyncio.to_thread(supabase_sync.login_with_google)
            
            if success:
                log.info("Berhasil login dengan Supabase via supabase_sync!")
                self.show_success("Login Berhasil! Membuka aplikasi...")
                
                # Notify app to unlock UI
                from gui.event_bus import event_bus
                event_bus.publish("LOGIN_SUCCESS")
            else:
                self.show_error("Login dibatalkan atau gagal.")
                self.btn_login.disabled = False
                self.progress_ring.visible = False
                self.info_text.value = "Silakan login menggunakan Google untuk mengakses aplikasi"
                try:
                    if self.page: self.page.update()
                    else: self.update()
                except Exception:
                    pass

        self._page.run_task(do_login)

    def show_error(self, msg: str):
        from gui.ui_utils import show_snackbar
        show_snackbar(self._page, msg, error=True)
        
    def show_success(self, msg: str):
        from gui.ui_utils import show_snackbar
        show_snackbar(self._page, msg)
