import asyncio

import flet as ft

from core.logger import log
from core.supabase_sync import supabase_sync
from gui.state import app_state


class AnimatedLoginButton(ft.Container):
    def __init__(self, on_click):
        super().__init__()
        self.on_click = on_click
        self.border_radius = 8
        self.padding = ft.Padding(left=24, top=14, right=24, bottom=14)
        self.gradient = ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.DEEP_PURPLE_500, ft.Colors.BLUE_600],
        )
        self.animate_scale = ft.Animation(200, ft.AnimationCurve.EASE_OUT)
        self.on_hover = self._hover

        self.content = ft.Row(
            [
                ft.Icon(ft.Icons.LOGIN, color=ft.Colors.WHITE),
                ft.Text(
                    "Login dengan Google",
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.WHITE,
                    size=16,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        )

    def _hover(self, e):
        if not self.disabled:
            self.scale = 1.05 if e.data == "true" else 1.0
            self.update()


class LoginView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.expand = True
        self.alignment = ft.Alignment(0, 0)

        # Background gradient for the whole view
        self.gradient = ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.SURFACE, "#11111B"],
        )

        self.btn_login = AnimatedLoginButton(on_click=self.start_google_login)

        self.info_text = ft.Text(
            "Silakan login menggunakan Google untuk mengakses aplikasi",
            size=14,
            color=ft.Colors.ON_SURFACE_VARIANT,
            text_align=ft.TextAlign.CENTER,
        )

        self.progress_ring = ft.ProgressRing(
            visible=False, width=24, height=24, color=ft.Colors.BLUE_400
        )
        self.progress_container = ft.Container(
            content=self.progress_ring, height=24, alignment=ft.Alignment.CENTER
        )

        # Login Card with Elevation & Shadow (Rule #1)
        login_card = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=72, color=ft.Colors.BLUE_400),
                    ft.Text("Masuk ke Cliptzy", size=28, weight=ft.FontWeight.W_800),
                    self.info_text,
                    ft.Container(height=16),
                    self.btn_login,
                    ft.Container(height=8),
                    self.progress_container,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            width=400,
            height=500,
            padding=ft.Padding(left=40, top=48, right=40, bottom=48),
            bgcolor=ft.Colors.SURFACE,
            border_radius=24,
            # border=ft.Border(
            #     top=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
            #     bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.05, ft.Colors.WHITE)),
            #     left=ft.BorderSide(1, ft.Colors.with_opacity(0.05, ft.Colors.WHITE)),
            #     right=ft.BorderSide(1, ft.Colors.with_opacity(0.05, ft.Colors.WHITE)),
            # ),
            shadow=ft.BoxShadow(
                blur_radius=30,
                spread_radius=-10,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 15),
            ),
        )

        self.content = login_card

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
                self.info_text.value = (
                    "Silakan login menggunakan Google untuk mengakses aplikasi"
                )
                try:
                    if self.page:
                        self.page.update()
                    else:
                        self.update()
                except Exception:
                    pass

        self._page.run_task(do_login)

    def show_error(self, msg: str):
        from gui.ui_utils import show_snackbar

        show_snackbar(self._page, msg, error=True)

    def show_success(self, msg: str):
        from gui.ui_utils import show_snackbar

        show_snackbar(self._page, msg)
