import flet as ft
from typing import cast, Any
from core.config import config

class SettingsView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.expand = True
        self.padding = 20

        # --- AI Settings ---
        self.ai_provider_dropdown = ft.Dropdown(
            label="Provider AI",
            options=[
                ft.dropdown.Option("ollama", "Local Ollama (Offline / Local)"),
                ft.dropdown.Option("gemini", "Google Gemini API (Online)"),
                ft.dropdown.Option("openai", "OpenAI GPT API (Online)")
            ],
            value=config.ai.provider,
            on_select=self.on_ai_provider_changed, # type: ignore
            expand=True
        )

        self.ai_key_input = ft.TextField(label="Ollama Host / API Key", value=config.ai.ollama_host, expand=True)
        self.ai_model_input = ft.TextField(label="Model Name", value=config.ai.ollama_model, hint_text="misal: llama3, gemini-1.5-flash, gpt-4o-mini", expand=True)
        self.ai_base_url_input = ft.TextField(label="Base URL", value=config.ai.openai_base_url, expand=True, hint_text="Opsional, untuk 3rd party OpenAI API", visible=False)

        self.on_ai_provider_changed(None) # init fields

        ai_settings_content = ft.Column([
            ft.Row(cast(list[ft.Control], [self.ai_provider_dropdown, self.ai_key_input]), expand=True),
            ft.Row(cast(list[ft.Control], [self.ai_base_url_input, self.ai_model_input]), expand=True)
        ], spacing=10)

        # --- System Settings ---
        self.output_dir_input = ft.TextField(label="Direktori Output (Default: clips)", value=config.output_dir, expand=True)

        system_settings_content = ft.Column([
            ft.Row(cast(list[ft.Control], [self.output_dir_input]), expand=True),
        ], spacing=10)

        # --- Platform Settings Pickers ---
        self.tt_cookies_picker = ft.FilePicker()
        self.ig_cookies_picker = ft.FilePicker()
        self._page.services.append(self.tt_cookies_picker)
        self._page.services.append(self.ig_cookies_picker)

        # --- Platform Settings ---
        self.default_hashtags = ft.TextField(
            label="Default Hashtags & Global Description",
            value=config.default_hashtags,
            hint_text="#Shorts #Viral #Cliptzy #fyp",
            multiline=True,
            min_lines=3,
            expand=True
        )

        self.yt_client_id = ft.TextField(label="Client ID (OAuth 2.0)", value=config.youtube.client_id, expand=True)
        self.yt_client_secret = ft.TextField(label="Client Secret", value=config.youtube.client_secret, password=True, can_reveal_password=True, expand=True)
        self.yt_visibility = ft.Dropdown(
            label="Default Visibility",
            options=[ft.dropdown.Option("Public"), ft.dropdown.Option("Unlisted"), ft.dropdown.Option("Private")],
            value=config.youtube.visibility or "Public",
            expand=True
        )

        yt_tab_content = ft.Container(
            content=ft.Column([
                ft.Row(cast(list[ft.Control], [self.yt_client_id]), expand=True),
                ft.Row(cast(list[ft.Control], [self.yt_client_secret]), expand=True),
                ft.Row(cast(list[ft.Control], [self.yt_visibility]), expand=True)
            ], spacing=10),
            padding=16
        )

        self.tt_session = ft.TextField(label="File Cookies TikTok (.txt/.json)", value=config.tiktok.session, expand=True)
        self.btn_import_tt_cookies = ft.Button(
            content=ft.Text("Import Cookies"),
            on_click=self.on_import_tt_cookies_clicked
        )
        self.tt_privacy = ft.Dropdown(
            label="Privasi Posting",
            options=[ft.dropdown.Option("Public (Semua Orang)"), ft.dropdown.Option("Friends (Teman)"), ft.dropdown.Option("Private (Hanya Saya)")],
            value=config.tiktok.privacy or "Public (Semua Orang)",
            expand=True
        )

        tt_tab_content = ft.Container(
            content=ft.Column([
                ft.Row(cast(list[ft.Control], [self.tt_session, self.btn_import_tt_cookies]), expand=True),
                ft.Row(cast(list[ft.Control], [self.tt_privacy]), expand=True)
            ], spacing=10),
            padding=16
        )

        self.ig_session = ft.TextField(label="File Cookies Instagram (.txt/.json)", value=config.instagram.session, expand=True)
        self.btn_import_ig_cookies = ft.Button(
            content=ft.Text("Import Cookies"),
            on_click=self.on_import_ig_cookies_clicked
        )

        ig_tab_content = ft.Container(
            content=ft.Column([
                ft.Row(cast(list[ft.Control], [self.ig_session, self.btn_import_ig_cookies]), expand=True)
            ], spacing=10),
            padding=16
        )

        self.platform_tabs = ft.Tabs(
            selected_index=0,
            length=3,
            content=ft.Column([
                ft.TabBar(
                    tabs=[
                        ft.Tab(label=ft.Text("🔴 YouTube Shorts")), # type: ignore
                        ft.Tab(label=ft.Text("🎵 TikTok")), # type: ignore
                        ft.Tab(label=ft.Text("📸 Instagram Reels")), # type: ignore
                    ]
                ),
                ft.TabBarView(
                    controls=[
                        yt_tab_content,
                        tt_tab_content,
                        ig_tab_content
                    ],
                    expand=True
                )
            ], expand=True),
            expand=1,
            height=350
        )

        self.btn_check_all_auth = ft.Button(
            content=ft.Row(
                controls=cast(list[ft.Control], [
                    ft.Icon(ft.Icons.LOCK_OPEN, size=18),
                    ft.Text("🔍 Cek Status Autentikasi Semua Platform")
                ]),
                tight=True,
                spacing=8
            ),
            on_click=self.check_all_platforms_auth,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.INDIGO_700,
                color=ft.Colors.WHITE
            )
        )
        self.auth_check_progress = ft.ProgressBar(visible=False, width=400)
        self.auth_check_result_text = ft.Text("", size=13, color=ft.Colors.GREY_400)

        platform_settings_layout = ft.Column([
            ft.Row(cast(list[ft.Control], [self.default_hashtags]), expand=True),
            ft.Container(height=10),
            self.platform_tabs,
            ft.Container(height=10),
            ft.Row(cast(list[ft.Control], [self.btn_check_all_auth]), alignment=ft.MainAxisAlignment.START),
            ft.Container(height=4),
            self.auth_check_progress,
            self.auth_check_result_text
        ])

        # --- Cloud Sync / Account Settings ---
        cloud_sync_content = self._build_cloud_sync_section()

        # --- Dependency Manager Settings ---
        dep_manager_content = self._build_dep_manager_section()

        # Build Expansion Panel
        self.expansion_panel = ft.ExpansionPanelList(
            expand_icon_color=ft.Colors.WHITE,
            elevation=8,
            divider_color=ft.Colors.TRANSPARENT,
            controls=[
                ft.ExpansionPanel(
                    header=ft.ListTile(title=ft.Text("🤖 Pengaturan AI Highlights")),
                    content=ft.Container(ai_settings_content, padding=16)
                ),
                ft.ExpansionPanel(
                    header=ft.ListTile(title=ft.Text("⚙️ Pengaturan Sistem")),
                    content=ft.Container(system_settings_content, padding=16)
                ),
                ft.ExpansionPanel(
                    header=ft.ListTile(title=ft.Text("🌐 Konfigurasi Platform")),
                    content=ft.Container(platform_settings_layout, padding=16)
                ),
                ft.ExpansionPanel(
                    header=ft.ListTile(title=ft.Text("☁️ Akun & Cloud Sync")),
                    content=ft.Container(cloud_sync_content, padding=16),
                ),
                ft.ExpansionPanel(
                    header=ft.ListTile(title=ft.Text("📦 Pengelola Dependensi Sistem")),
                    content=ft.Container(dep_manager_content, padding=16)
                )
            ]
        )

        self.save_btn = ft.Button(
            content=ft.Text("💾 Simpan Pengaturan"), # type: ignore
            on_click=self.save_settings,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE
            )
        )

        self.clear_cache_btn = ft.Button(
            content=ft.Text("🧹 Bersihkan Cache (Menghitung...)"), # type: ignore
            on_click=self.clear_cache,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.RED_700,
                color=ft.Colors.WHITE
            )
        )

        self.content = ft.Column(
            controls=[
                ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
                self.expansion_panel,
                ft.Row(
                    controls=cast(list[ft.Control], [
                        self.clear_cache_btn,
                        ft.Container(expand=True),
                        self.save_btn
                    ])
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=20
        )

    def _build_cloud_sync_section(self) -> ft.Column:
        """Bangun section Cloud Sync: info akun, backup, restore, logout."""
        from core.supabase_sync import supabase_sync

        # Info akun user
        user_name = supabase_sync.get_user_display_name() or "Pengguna"
        user_email = supabase_sync.get_user_email() or "-"
        avatar_url = supabase_sync.get_user_avatar_url()

        # Avatar
        if avatar_url:
            avatar_widget = ft.CircleAvatar(
                foreground_image_src=avatar_url,
                radius=28
            )
        else:
            avatar_widget = ft.CircleAvatar( # type: ignore
                content=ft.Text(user_name[0].upper() if user_name else "?", size=24),
                radius=28,
                bgcolor=ft.Colors.BLUE_700
            )

        user_info = ft.Row(
            controls=cast(list[ft.Control], [
                avatar_widget,
                ft.Column([
                    ft.Text(user_name, size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(user_email, size=13, color=ft.Colors.GREY_400),
                ], spacing=2)
            ]),
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Status sync
        self.sync_status_text = ft.Text(
            "Siap untuk backup atau restore.",
            size=13,
            color=ft.Colors.GREY_400,
            italic=True
        )

        self.sync_progress = ft.ProgressBar(visible=False, width=400)

        # Tombol Backup
        self.backup_btn = ft.Button(
            content=ft.Row( # type: ignore
                controls=cast(list[ft.Control], [
                    ft.Icon(ft.Icons.CLOUD_UPLOAD, size=18),
                    ft.Text("Backup ke Cloud")
                ]),
                tight=True,
                spacing=8
            ),
            on_click=self._on_backup_click,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.TEAL_700,
                color=ft.Colors.WHITE
            ),
            tooltip="Upload config.json dan semua file di folder cred/ ke Supabase"
        )

        # Tombol Restore
        self.restore_btn = ft.Button(
            content=ft.Row( # type: ignore
                controls=cast(list[ft.Control], [
                    ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=18),
                    ft.Text("Restore dari Cloud")
                ]),
                tight=True,
                spacing=8
            ),
            on_click=self._on_restore_click,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.DEEP_PURPLE_700,
                color=ft.Colors.WHITE
            ),
            tooltip="Download config.json dan semua file di folder cred/ dari Supabase"
        )

        # Tombol Logout
        self.logout_btn = ft.Button(
            content=ft.Row( # type: ignore
                controls=cast(list[ft.Control], [
                    ft.Icon(ft.Icons.LOGOUT, size=18),
                    ft.Text("Logout")
                ]),
                tight=True,
                spacing=8
            ),
            on_click=self._on_logout_click,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.RED_700,
                color=ft.Colors.WHITE
            ),
            tooltip="Keluar dari akun dan kunci aplikasi"
        )

        # Keterangan
        info_text = ft.Text(
            "Backup & Restore menyimpan/memulihkan config.json dan seluruh channel dan kredensial Anda ke/dari database.",
            size=12,
            color=ft.Colors.GREY_500,
            italic=True
        )

        return ft.Column([
            user_info,
            ft.Divider(height=16, color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            info_text,
            ft.Container(height=8),
            ft.Row(
                controls=cast(list[ft.Control], [
                    self.backup_btn,
                    self.restore_btn,
                ]),
                spacing=12,
                wrap=True
            ),
            ft.Container(height=4),
            self.sync_progress,
            self.sync_status_text,
            ft.Divider(height=16, color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            ft.Row(
                controls=cast(list[ft.Control], [self.logout_btn]),
                alignment=ft.MainAxisAlignment.END
            )
        ], spacing=8)

    def _set_sync_buttons_enabled(self, enabled: bool) -> None:
        """Enable/disable tombol backup, restore, logout."""
        self.backup_btn.disabled = not enabled
        self.restore_btn.disabled = not enabled
        self.logout_btn.disabled = not enabled

    def _on_backup_click(self, e) -> None:
        """Handler tombol Backup — jalankan di background task."""
        self._set_sync_buttons_enabled(False)
        self.sync_progress.visible = True
        self.sync_progress.value = None  # indeterminate
        self.sync_status_text.value = "Memulai backup..."
        self.sync_status_text.color = ft.Colors.AMBER_400
        self._page.update()

        async def do_backup():
            import asyncio
            from core.supabase_sync import supabase_sync

            def on_progress(label: str, current: int, total: int):
                self.sync_status_text.value = label
                if total > 0:
                    self.sync_progress.value = current / total
                try:
                    self._page.update()
                except Exception:
                    pass

            result = await asyncio.to_thread(supabase_sync.backup_all, on_progress)

            self._set_sync_buttons_enabled(True)
            self.sync_progress.visible = False

            if result.get("success"):
                self.sync_status_text.value = f"✅ {result.get('message', 'Backup berhasil!')}"
                self.sync_status_text.color = ft.Colors.GREEN_400
                self._show_snackbar(f"Backup berhasil! ({result.get('success_count', 0)} item)", ft.Colors.GREEN_700)
            else:
                self.sync_status_text.value = f"⚠️ {result.get('message', 'Backup selesai dengan beberapa error.')}"
                self.sync_status_text.color = ft.Colors.ORANGE_400
                self._show_snackbar(result.get('message', 'Backup selesai dengan error.'), ft.Colors.ORANGE_700)

            self._page.update()

        self._page.run_task(do_backup)

    def _on_restore_click(self, e) -> None:
        """Handler tombol Restore — konfirmasi dulu, lalu jalankan di background task."""

        def on_confirm(e_dialog):
            dialog.open = False
            self._page.update()
            self._execute_restore()

        def on_cancel(e_dialog):
            dialog.open = False
            self._page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Konfirmasi Restore"),
            content=ft.Text(
                "Data lokal (config.json dan folder cred/) akan DITIMPA dengan data dari cloud.\n\n"
                "Apakah Anda yakin ingin melanjutkan?"
            ),
            actions=[
                ft.TextButton("Batal", on_click=on_cancel),
                ft.TextButton("Ya, Restore", on_click=on_confirm, style=ft.ButtonStyle(color=ft.Colors.RED_400)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _execute_restore(self) -> None:
        """Eksekusi restore di background."""
        self._set_sync_buttons_enabled(False)
        self.sync_progress.visible = True
        self.sync_progress.value = None
        self.sync_status_text.value = "Memulai restore..."
        self.sync_status_text.color = ft.Colors.AMBER_400
        self._page.update()

        async def do_restore():
            import asyncio
            from core.supabase_sync import supabase_sync

            def on_progress(label: str, current: int, total: int):
                self.sync_status_text.value = label
                if total > 0:
                    self.sync_progress.value = current / total
                try:
                    self._page.update()
                except Exception:
                    pass

            result = await asyncio.to_thread(supabase_sync.restore_all, on_progress)

            self._set_sync_buttons_enabled(True)
            self.sync_progress.visible = False

            msg = result.get('message', 'Restore selesai.')
            success_count = result.get('success_count', 0)
            fail_count = result.get('fail_count', 0)

            if fail_count == 0:
                self.sync_status_text.value = f"✅ {msg}"
                self.sync_status_text.color = ft.Colors.GREEN_400
                self._show_snackbar(f"Restore berhasil! ({success_count} item)", ft.Colors.GREEN_700)
            else:
                self.sync_status_text.value = f"⚠️ {msg}"
                self.sync_status_text.color = ft.Colors.ORANGE_400
                self._show_snackbar(msg, ft.Colors.ORANGE_700)

            self._page.update()

        self._page.run_task(do_restore)

    def _on_logout_click(self, e) -> None:
        """Handler tombol Logout — konfirmasi, logout, dan kunci aplikasi."""

        def on_confirm(e_dialog):
            dialog.open = False
            self._page.update()
            self._execute_logout()

        def on_cancel(e_dialog):
            dialog.open = False
            self._page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Konfirmasi Logout"),
            content=ft.Text(
                "Anda akan keluar dari akun dan aplikasi akan terkunci.\n"
                "Pastikan Anda sudah melakukan backup sebelum logout."
            ),
            actions=[
                ft.TextButton("Batal", on_click=on_cancel),
                ft.TextButton("Ya, Logout", on_click=on_confirm, style=ft.ButtonStyle(color=ft.Colors.RED_400)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _execute_logout(self) -> None:
        """Eksekusi logout dan kirim event untuk kunci aplikasi."""
        from core.supabase_sync import supabase_sync
        from gui.event_bus import event_bus

        supabase_sync.logout()
        self._show_snackbar("Berhasil logout. Aplikasi dikunci.", ft.Colors.BLUE_700)

        # Kirim event LOGOUT untuk mengunci aplikasi kembali ke halaman login
        event_bus.publish("LOGOUT")

    def did_mount(self) -> None:
        self.update_dependency_status()
        self.update_cache_size()

    def update_dependency_status(self) -> None:
        """Memeriksa status, versi, dan lokasi path dari FFmpeg dan Deno."""
        from core.dependency_manager import get_dependency_info

        # Check FFmpeg
        ff_ok, ff_ver, ff_path = get_dependency_info("ffmpeg")
        if ff_ok:
            self.ffmpeg_status_text.value = f"Terpasang (v{ff_ver})\nLokasi: {ff_path}"
            self.ffmpeg_status_text.color = ft.Colors.GREEN_400
        else:
            self.ffmpeg_status_text.value = "❌ Tidak Terpasang"
            self.ffmpeg_status_text.color = ft.Colors.RED_400

        # Check Deno
        deno_ok, deno_ver, deno_path = get_dependency_info("deno")
        if deno_ok:
            self.deno_status_text.value = f"Terpasang (v{deno_ver})\nLokasi: {deno_path}"
            self.deno_status_text.color = ft.Colors.GREEN_400
        else:
            self.deno_status_text.value = "❌ Tidak Terpasang"
            self.deno_status_text.color = ft.Colors.RED_400

        try:
            self.ffmpeg_status_text.update()
            self.deno_status_text.update()
        except Exception:
            pass

    def _build_dep_manager_section(self) -> ft.Column:
        self.dep_status_text = ft.Text("Klik tombol di bawah untuk memeriksa/memasang dependensi.", size=13, color=ft.Colors.GREY_400)
        self.dep_progress = ft.ProgressBar(visible=False, width=400)

        self.ffmpeg_status_text = ft.Text("Memeriksa...", color=ft.Colors.GREY_400, size=13)
        self.deno_status_text = ft.Text("Memeriksa...", color=ft.Colors.GREY_400, size=13)

        self.dep_info_table = ft.Column([
            ft.Row(controls=cast(list[ft.Control], [
                ft.Text("🎬 FFmpeg:", weight=ft.FontWeight.BOLD, size=13, width=90),
                self.ffmpeg_status_text
            ]), vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row(controls=cast(list[ft.Control], [
                ft.Text("🦕 Deno:", weight=ft.FontWeight.BOLD, size=13, width=90),
                self.deno_status_text
            ]), vertical_alignment=ft.CrossAxisAlignment.START)
        ], spacing=10)

        self.btn_install_deps = ft.Button(
            content=ft.Row(
                controls=cast(list[ft.Control], [
                    ft.Icon(ft.Icons.DOWNLOAD, size=18),
                    ft.Text("⬇️ Install / Reinstall Dependencies")
                ]),
                tight=True,
                spacing=8
            ),
            on_click=self.start_dependency_installation,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE
            ),
            tooltip="Unduh Deno dan FFmpeg ke direktori bin aplikasi"
        )

        desc = ft.Text(
            "Unduh dan pasang dependensi yang diperlukan oleh aplikasi secara otomatis "
            "(FFmpeg untuk pemrosesan video, Deno untuk eksekusi skrip). Dependensi ini akan di-install di "
            "folder lokal aplikasi agar tidak mengganggu sistem bawaan Anda.",
            size=13,
            color=ft.Colors.GREY_400
        )

        return ft.Column([
            desc,
            ft.Container(height=4),
            self.dep_info_table,
            ft.Divider(height=16, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
            self.btn_install_deps,
            ft.Container(height=4),
            self.dep_progress,
            self.dep_status_text
        ], spacing=8)

    def start_dependency_installation(self, e) -> None:
        from core.dependency_manager import install_dependencies
        from gui.state import app_state

        self.btn_install_deps.disabled = True
        self.dep_progress.visible = True
        self.dep_progress.value = None
        self.dep_status_text.value = "Memulai instalasi dependensi..."
        self.dep_status_text.color = ft.Colors.AMBER_400
        self._page.update()

        def emit_log(msg: str):
            app_state.append_log(msg)
            self.dep_status_text.value = msg
            try:
                self._page.update()
            except Exception:
                pass

        async def do_installation():
            import asyncio
            success = await asyncio.to_thread(install_dependencies, emit_log)

            self.btn_install_deps.disabled = False
            self.dep_progress.visible = False

            if success:
                self.dep_status_text.value = "✅ Semua dependensi berhasil dipasang!"
                self.dep_status_text.color = ft.Colors.GREEN_400
                self._show_snackbar("Instalasi dependensi berhasil!", ft.Colors.GREEN_700)
            else:
                self.dep_status_text.value = "❌ Gagal memasang beberapa dependensi. Periksa log."
                self.dep_status_text.color = ft.Colors.RED_400
                self._show_snackbar("Gagal memasang dependensi.", ft.Colors.RED_700)

            # Cek status ulang setelah selesai
            self.update_dependency_status()
            self._page.update()

        self._page.run_task(do_installation)

    async def on_import_tt_cookies_clicked(self, e) -> None:
        files = await self.tt_cookies_picker.pick_files(
            dialog_title="Pilih File Cookies TikTok (JSON/TXT)",
            allowed_extensions=["txt", "json"]
        )
        if files and len(files) > 0 and files[0].path:
            import shutil
            import os
            try:
                config.ensure_cred_dir()
                target_path = "cred/tiktok_cookies.txt"
                shutil.copy(files[0].path, target_path)
                self.tt_session.value = target_path
                try:
                    self.tt_session.update()
                except Exception:
                    pass
                self._show_snackbar(f"File cookies TikTok berhasil diimpor ke '{target_path}'", ft.Colors.GREEN_700)
            except Exception as ex:
                self._show_snackbar(f"Gagal mengimpor cookies: {ex}", ft.Colors.RED_700)

    async def on_import_ig_cookies_clicked(self, e) -> None:
        files = await self.ig_cookies_picker.pick_files(
            dialog_title="Pilih File Cookies Instagram (JSON/TXT)",
            allowed_extensions=["txt", "json"]
        )
        if files and len(files) > 0 and files[0].path:
            import shutil
            import os
            try:
                config.ensure_cred_dir()
                target_path = "cred/instagram_cookies.txt"
                shutil.copy(files[0].path, target_path)
                self.ig_session.value = target_path
                try:
                    self.ig_session.update()
                except Exception:
                    pass
                self._show_snackbar(f"File cookies Instagram berhasil diimpor ke '{target_path}'", ft.Colors.GREEN_700)
            except Exception as ex:
                self._show_snackbar(f"Gagal mengimpor cookies: {ex}", ft.Colors.RED_700)

    def check_all_platforms_auth(self, e) -> None:
        self.btn_check_all_auth.disabled = True
        self.auth_check_progress.visible = True
        self.auth_check_progress.value = None
        self.auth_check_result_text.value = "Memeriksa status autentikasi semua platform..."
        self.auth_check_result_text.color = ft.Colors.AMBER_400
        self._page.update()

        async def do_check():
            import asyncio
            from core.auth_checker import check_youtube_auth, check_tiktok_auth, check_instagram_auth

            # Cek YouTube
            self.auth_check_result_text.value = "Memeriksa YouTube Shorts..."
            self._page.update()
            yt_ok, yt_msg = await asyncio.to_thread(check_youtube_auth)

            # Cek TikTok
            self.auth_check_result_text.value = "Memeriksa TikTok..."
            self._page.update()
            config.tiktok.session = self.tt_session.value or ""
            tt_ok, tt_msg = await asyncio.to_thread(check_tiktok_auth)

            # Cek Instagram
            self.auth_check_result_text.value = "Memeriksa Instagram Reels..."
            self._page.update()
            config.instagram.session = self.ig_session.value or ""
            ig_ok, ig_msg = await asyncio.to_thread(check_instagram_auth)

            self.btn_check_all_auth.disabled = False
            self.auth_check_progress.visible = False

            # Format report
            report = (
                f"🔴 YouTube: {'✅ Valid' if yt_ok else '❌ Gagal'} - {yt_msg}\n\n"
                f"🎵 TikTok: {'✅ Valid' if tt_ok else '❌ Gagal'} - {tt_msg}\n\n"
                f"📸 Instagram: {'✅ Valid' if ig_ok else '❌ Gagal'} - {ig_msg}"
            )
            self.auth_check_result_text.value = report
            self.auth_check_result_text.color = ft.Colors.WHITE

            if yt_ok and tt_ok and ig_ok:
                self._show_snackbar("Semua platform valid!", ft.Colors.GREEN_700)
            else:
                self._show_snackbar("Beberapa platform gagal diautentikasi.", ft.Colors.ORANGE_700)

            self._page.update()

        self._page.run_task(do_check)

    def _show_snackbar(self, message: str, color) -> None:
        """Tampilkan SnackBar notifikasi."""
        snack = ft.SnackBar(ft.Text(message, color=ft.Colors.WHITE), bgcolor=color) # type: ignore
        self._page.overlay.append(snack)
        snack.open = True
        self._page.update()

    def on_ai_provider_changed(self, e = None) -> None:
        provider = self.ai_provider_dropdown.value
        if provider == "ollama":
            self.ai_key_input.label = "Ollama Host"
            self.ai_key_input.password = False
            self.ai_key_input.value = config.ai.ollama_host or "http://localhost:11434"
            self.ai_model_input.value = config.ai.ollama_model or "llama3"
            self.ai_base_url_input.visible = False
        elif provider == "gemini":
            self.ai_key_input.label = "Gemini API Key"
            self.ai_key_input.password = True
            self.ai_key_input.value = config.ai.gemini_key or ""
            self.ai_model_input.value = config.ai.gemini_model or "gemini-1.5-flash"
            self.ai_base_url_input.visible = False
        elif provider == "openai":
            self.ai_key_input.label = "OpenAI API Key"
            self.ai_key_input.password = True
            self.ai_key_input.value = config.ai.openai_key or ""
            self.ai_model_input.value = config.ai.openai_model or "gpt-4o-mini"
            self.ai_base_url_input.visible = True
            self.ai_base_url_input.value = config.ai.openai_base_url or ""

        if self._page:
            try:
                self._page.update()
            except Exception:
                pass

    def save_settings(self, e) -> None:
        provider = self.ai_provider_dropdown.value
        val = self.ai_key_input.value.strip() if self.ai_key_input.value else ""
        model_val = self.ai_model_input.value.strip() if self.ai_model_input.value else ""

        config.ai.provider = provider or "ollama"
        if provider == "ollama":
            config.ai.ollama_host = val
            config.ai.ollama_model = model_val
        elif provider == "gemini":
            config.ai.gemini_key = val
            config.ai.gemini_model = model_val
        elif provider == "openai":
            config.ai.openai_key = val
            config.ai.openai_model = model_val
            config.ai.openai_base_url = self.ai_base_url_input.value.strip() if self.ai_base_url_input.value else ""

        # System settings
        if self.output_dir_input.value: config.output_dir = self.output_dir_input.value

        # Normalize hashtags
        config.default_hashtags = self.default_hashtags.value or ""
        config.default_hashtags = " ".join(config.default_hashtags.splitlines())
        config.default_hashtags = " ".join(list(dict.fromkeys(config.default_hashtags.split(" "))))

        # Platform settings
        config.youtube.client_id = self.yt_client_id.value or ""
        config.youtube.client_secret = self.yt_client_secret.value or ""
        config.youtube.visibility = self.yt_visibility.value or "Public"

        config.tiktok.session = self.tt_session.value or ""
        config.tiktok.privacy = self.tt_privacy.value or "Public (Semua Orang)"

        config.instagram.session = self.ig_session.value or ""

        if config.save_to_file():
            self._show_snackbar("Pengaturan berhasil disimpan!", ft.Colors.GREEN_700)

    def update_cache_size(self) -> None:
        async def run_calc():
            import asyncio
            import os

            def calc():
                total_size = 0
                folder_path = "clips"
                if os.path.exists(folder_path):
                    for dirpath, dirnames, filenames in os.walk(folder_path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if not os.path.islink(fp):
                                try:
                                    total_size += os.path.getsize(fp)
                                except Exception:
                                    pass
                return total_size / (1024 * 1024)

            size_mb = await asyncio.to_thread(calc)
            self.clear_cache_btn.content = ft.Text(f"🧹 Bersihkan Cache ({size_mb:.2f} MB)") # type: ignore
            try:
                self.clear_cache_btn.update()
            except Exception:
                pass

        self._page.run_task(run_calc)

    def clear_cache(self, e) -> None:
        self.clear_cache_btn.disabled = True
        self.clear_cache_btn.content = ft.Text("🧹 Sedang membersihkan...") # type: ignore
        try:
            self.clear_cache_btn.update()
        except Exception:
            pass

        async def run_clear():
            import asyncio
            import shutil
            import os

            def clear_ops():
                folder_path = "clips"
                if os.path.exists(folder_path):
                    for filename in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as ex:
                            from core.logger import log
                            log.warning(f"Gagal menghapus {file_path}: {ex}")

            await asyncio.to_thread(clear_ops)
            self.clear_cache_btn.disabled = False
            self._show_snackbar("Cache clips berhasil dibersihkan!", ft.Colors.GREEN_700)
            self.update_cache_size()

        self._page.run_task(run_clear)
