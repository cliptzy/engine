import core.bootstrap
import os
import sys

import flet as ft
from core.config import config
from gui.theme import build_theme
from gui.state import app_state

w = 1024
h = 768

def main(page: ft.Page) -> None:
    """Initialization"""
    config.load_from_file()

    """Flet application entry point."""
    page.title = "Cliptzy Desktop"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = build_theme()
    page.padding = 8
    page.window.min_width = w
    page.window.min_height = h
    page.window.width = w
    page.window.height = h
    
    # Load fonts
    from core.utils import get_app_root
    base_dir = get_app_root()
    page.fonts = {
        "Inter": os.path.join(base_dir, "assets", "fonts", "Inter-Regular.ttf"),
        "Inter Bold": os.path.join(base_dir, "assets", "fonts", "Inter-Bold.ttf")
    }

    # Scaffold the main layout elements
    from gui.layout import Header, Sidebar, MainLayout
    from gui.router import Router
    from gui.components.log_viewer import LogViewer
    from gui.layout.footer import StatusBar
    from gui.views.login_view import LoginView
    from gui.event_bus import event_bus
    
    app_bar = Header()
    
    def on_navigate(index: int) -> None:
        routes = ["clipper", "creator_hub", "sfx", "settings"]
        if 0 <= index < len(routes):
            app_state.set_page(routes[index])
    
    sidebar = Sidebar(on_navigate=on_navigate)
    router = Router(page, app_state)
    main_layout = MainLayout(sidebar, router.wrapper)
    log_viewer = LogViewer(height=120, expand=False)
    status_bar = StatusBar()
    
    login_view = LoginView(page)
    
    def build_app_ui():
        """Bangun UI utama aplikasi (hanya jika sudah login)."""
        page.controls.clear()
        app_bar.refresh_profile()
        page.add(app_bar, main_layout, log_viewer, status_bar)
        app_state.set_page("clipper")
        router.initialize()
        page.update()
        
        # Check for updates in background
        async def check_update_worker():
            import asyncio
            from core.updater import check_for_updates
            from core.logger import log
            
            try:
                # Run sync HTTP request in thread pool
                has_update, new_ver, release_url = await asyncio.to_thread(check_for_updates)
                if has_update and new_ver and release_url:
                    log.info(f"Pembaruan tersedia: {new_ver}. Menampilkan notifikasi ke pengguna.")
                    
                    async def on_download_click(e):
                        await ft.UrlLauncher().launch_url(release_url)
                        dialog.open = False
                        page.update()
                        
                    def on_close_click(e):
                        dialog.open = False
                        page.update()
                        
                    dialog = ft.AlertDialog(
                        title=ft.Text("Pembaruan Tersedia 🚀", weight=ft.FontWeight.BOLD),
                        content=ft.Text(f"Versi terbaru Cliptzy ({new_ver}) telah tersedia!\nSilakan unduh untuk mendapatkan fitur dan perbaikan terbaru."),
                        actions=[
                            ft.TextButton("Nanti Saja", on_click=on_close_click),
                            ft.Button("Unduh Sekarang", on_click=on_download_click, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                    )
                    page.overlay.append(dialog)
                    dialog.open = True
                    page.update()
            except Exception as e:
                log.warning(f"Error saat menjalankan update checker: {e}")

        page.run_task(check_update_worker)
        
    def show_login_ui():
        """Tampilkan halaman login (kunci aplikasi)."""
        page.controls.clear()
        page.add(login_view)
        page.update()

    def on_login_success(*args, **kwargs):
        """Handler saat login berhasil — unlock aplikasi."""
        build_app_ui()
    
    def on_logout(*args, **kwargs):
        """Handler saat logout — kunci aplikasi kembali ke login."""
        # Reset login view state
        login_view.btn_login.disabled = False
        login_view.progress_ring.visible = False
        login_view.info_text.value = "Silakan login menggunakan Google untuk mengakses aplikasi"
        show_login_ui()
        
    event_bus.subscribe("LOGIN_SUCCESS", on_login_success)
    event_bus.subscribe("LOGOUT", on_logout)

    # Initialize Supabase Sync
    from core.supabase_sync import supabase_sync
    
    # Check if a local .env exists (for development)
    dotenv_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(dotenv_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dotenv_path = os.path.join(base_dir, ".env")
        
    if os.path.exists(dotenv_path):
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=dotenv_path)
    
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY", "")
    
    # Fallback to auto-generated _build_env if env vars not set (e.g., in standalone build)
    if not supabase_url or not supabase_key:
        try:
            from core import _build_env
            from core.security import deobfuscate
            if hasattr(_build_env, "SUPABASE_URL_OBFUSCATED"):
                supabase_url = deobfuscate(_build_env.SUPABASE_URL_OBFUSCATED)
            if hasattr(_build_env, "SUPABASE_SECRET_KEY_OBFUSCATED"):
                supabase_key = deobfuscate(_build_env.SUPABASE_SECRET_KEY_OBFUSCATED)
        except ImportError:
            pass
            
    supabase_sync.initialize(supabase_url, supabase_key)

    # Check session — Kunci aplikasi jika belum login
    is_logged_in = supabase_sync.load_session()
    if is_logged_in:
        build_app_ui()
    else:
        show_login_ui()

def run_gui() -> None:
    """Wrapper to start the Flet app."""
    ft.run(main=main)
