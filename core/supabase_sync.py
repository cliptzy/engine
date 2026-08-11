import json
import os
from typing import Any, Dict, Optional

from core.logger import log


class SupabaseSyncManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseSyncManager, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.user = None
        return cls._instance

    def initialize(self, supabase_url: str, supabase_key: str):
        if not supabase_url or not supabase_key:
            return

        try:
            from supabase import Client, create_client

            self.client = create_client(supabase_url, supabase_key)
            log.info("Supabase client initialized.")
            self.load_session()
        except ImportError:
            log.warning(
                "Package 'supabase' is not installed. Run 'pip install supabase'."
            )
            self.client = None
        except Exception as e:
            log.error(f"Failed to initialize Supabase client: {e}")
            self.client = None

    def login_with_google(self) -> bool:
        if not self.client:
            log.warning("Supabase client not initialized.")
            return False

        import threading
        import webbrowser
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from urllib.parse import parse_qs, urlparse

        callback_port = 54321
        redirect_uri = f"http://localhost:{callback_port}"

        # We will store the extracted auth code here
        auth_code: list[Optional[str]] = [None]

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)

                # Check for error
                if "error" in query_params:
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<h1>Login Gagal</h1><p>Terjadi kesalahan atau otorisasi dibatalkan.</p>"
                    )
                    return

                # PKCE flow returns 'code'
                if "code" in query_params:
                    auth_code[0] = query_params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<h1>Login Berhasil!</h1><p>Anda dapat menutup jendela ini dan kembali ke aplikasi Cliptzy.</p>"
                    )
                else:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    # Fallback for implicit flow (though PKCE is expected)
                    html = b"""
                    <html><body>
                    <script>
                        if (window.location.hash) {
                            // Implicit flow workaround (unlikely if PKCE is forced)
                            document.body.innerHTML = "<h1>Memproses Token...</h1>";
                        } else {
                            document.body.innerHTML = "<h1>Parameter 'code' tidak ditemukan.</h1>";
                        }
                    </script>
                    </body></html>
                    """
                    self.wfile.write(html)

            def log_message(self, format, *args):
                pass  # suppress console logging for the server

        try:
            # 1. Start local server
            server = HTTPServer(("localhost", callback_port), OAuthCallbackHandler)

            # 2. Get OAuth URL with YouTube scope
            from typing import cast

            auth_client = cast(Any, self.client.auth)
            res = auth_client.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {
                        "redirect_to": redirect_uri,
                        "skip_browser_redirect": True,
                        "scopes": "https://www.googleapis.com/auth/youtube.upload",
                    },
                }
            )

            if not res or not hasattr(res, "url"):
                log.error("Gagal mendapatkan URL otorisasi Google dari Supabase.")
                return False

            # 3. Open Browser
            log.info("Membuka browser untuk Google OAuth (beserta izin YouTube)...")
            webbrowser.open(res.url)

            # 4. Wait for a single request (the callback)
            server.handle_request()
            server.server_close()

            # 5. Exchange code for session
            if auth_code[0]:
                log.info("Menerima auth code, menukar dengan session...")
                session_res = self.client.auth.exchange_code_for_session(
                    {"auth_code": auth_code[0]}
                )  # type: ignore
                if session_res and session_res.user:
                    self.user = session_res.user
                    log.info(f"User logged in via Google: {self.user.id}")

                    # The bucket 'user_files' must be created manually or via SQL migration beforehand.

                    # Save session to file
                    from core.config import config
                    from core.utils import write_json

                    config.ensure_cred_dir()
                    session_data = {
                        "access_token": session_res.session.access_token
                        if session_res.session
                        else None,
                        "refresh_token": session_res.session.refresh_token
                        if session_res.session
                        else None,
                    }
                    write_json("cred/supabase_session.json", session_data)

                    return True
                else:
                    log.error("Gagal menukar code dengan session (User None).")
                    return False
            else:
                log.error("Auth code tidak didapatkan dari callback.")
                return False

        except Exception as e:
            log.error(f"Google Login failed: {e}")
            return False

    def load_session(self):
        import os

        from core.utils import read_json

        session_file = "cred/supabase_session.json"
        if os.path.exists(session_file):
            data = read_json(session_file)
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            if access_token and refresh_token:
                try:
                    if not self.client:
                        return False
                    res = self.client.auth.set_session(access_token, refresh_token)
                    if res and res.user:
                        self.user = res.user
                        log.info(f"Session restored for user: {self.user.id}")
                        return True
                except Exception as e:
                    log.warning(f"Gagal memuat sesi sebelumnya: {e}")
        return False

    def get_user_id(self) -> Optional[str]:
        if self.user:
            return self.user.id
        return None

    def sync_config_up(self, config_dict: dict) -> bool:
        if not self.client or not self.user:
            return False
        if not config_dict:
            log.warning(
                "Config kosong, dibatalkan untuk sync up agar tidak merusak data cloud."
            )
            return False

        try:
            data = {"user_id": self.user.id, "config": config_dict}
            res = (
                self.client.table("user_configs")
                .upsert(data, on_conflict="user_id")
                .execute()
            )
            log.info("Config synced up to Supabase.")
            return True
        except Exception as e:
            log.error(f"Failed to sync config up: {e}")
            return False

    def sync_config_down(self) -> Optional[Dict[str, Any]]:
        if not self.client or not self.user:
            return None
        try:
            res = (
                self.client.table("user_configs")
                .select("config")
                .eq("user_id", self.user.id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                log.info("Config synced down from Supabase.")
                row: Any = res.data[0]
                return row["config"]
            return None
        except Exception as e:
            log.error(f"Failed to sync config down: {e}")
            return None

    def upload_file(self, local_path: str, remote_filename: str) -> bool:
        if not self.client or not self.user:
            return False
        if not os.path.exists(local_path):
            return False

        # Pengecekan ukuran file
        if os.path.getsize(local_path) == 0:
            log.warning(f"File {local_path} kosong (0 bytes), dilewati dari upload.")
            return False

        # Pengecekan validitas JSON
        if local_path.lower().endswith(".json"):
            import json

            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception as e:
                log.warning(
                    f"File JSON tidak valid {local_path}, dilewati dari upload: {e}"
                )
                return False

        try:
            bucket_path = f"{self.user.id}/{remote_filename}"
            with open(local_path, "rb") as f:
                res = self.client.storage.from_("user_files").upload(
                    file=f, path=bucket_path, file_options={"upsert": "true"}
                )
            log.info(f"File {local_path} uploaded to {bucket_path}")
            return True
        except Exception as e:
            log.warning(f"Failed to upload file {local_path}: {e}")
            return False

    def download_file(self, remote_filename: str, local_path: str) -> bool:
        if not self.client or not self.user:
            return False
        bucket_path = f"{self.user.id}/{remote_filename}"
        try:
            res = self.client.storage.from_("user_files").download(bucket_path)

            # Pengecekan ukuran dari memori sebelum ditulis
            if not res or len(res) == 0:
                log.warning(
                    f"File hasil download {bucket_path} kosong, dibatalkan (tidak menimpa lokal)."
                )
                return False

            # Pengecekan validitas JSON jika ekstensi json
            if remote_filename.lower().endswith(".json"):
                import json

                try:
                    json.loads(res.decode("utf-8"))
                except Exception as e:
                    log.warning(
                        f"Isi file {bucket_path} bukan JSON yang valid, dibatalkan: {e}"
                    )
                    return False

            os.makedirs(
                os.path.dirname(local_path) if os.path.dirname(local_path) else ".",
                exist_ok=True,
            )
            with open(local_path, "wb") as f:
                f.write(res)
            log.info(f"File {bucket_path} downloaded to {local_path}")
            return True
        except Exception as e:
            log.warning(f"Failed to download file {bucket_path}: {e}")
            return False

    def backup_all(self, on_progress: Optional[Any] = None) -> Dict[str, Any]:
        """Backup config.json dan seluruh file di folder cred/ ke Supabase.

        Args:
            on_progress: Optional callback(label: str, current: int, total: int).

        Returns:
            Dict berisi status backup: success count, fail count, detail.
        """
        if not self.client or not self.user:
            return {
                "success": False,
                "message": "Belum login. Silakan login terlebih dahulu.",
            }

        from core.config import config

        results: Dict[str, bool] = {}
        files_to_backup: list[tuple[str, str]] = []  # (local_path, remote_name)

        # 1. Backup config.json via user_configs table (JSONB)
        config_dict = config.to_dict()

        # 2. Kumpulkan semua file di folder cred/
        cred_dir = "cred"
        if os.path.isdir(cred_dir):
            for filename in os.listdir(cred_dir):
                filepath = os.path.join(cred_dir, filename)
                if os.path.isfile(filepath) and filename != "supabase_session.json":
                    files_to_backup.append((filepath, f"cred/{filename}"))

        # 3. Kumpulkan semua file di folder channels/
        channels_dir = "channels"
        if os.path.isdir(channels_dir):
            for filename in os.listdir(channels_dir):
                filepath = os.path.join(channels_dir, filename)
                if os.path.isfile(filepath):
                    files_to_backup.append((filepath, f"channels/{filename}"))

        # Juga backup config.json via storage sebagai fallback
        config_file = "config.json"
        if os.path.exists(config_file):
            files_to_backup.append((config_file, "config.json"))

        total = len(files_to_backup) + 1  # +1 untuk config table sync
        current = 0

        # Step 1: Sync config ke tabel user_configs
        if on_progress:
            on_progress("Backup config ke database...", current, total)
        config_ok = self.sync_config_up(config_dict)
        results["user_configs (database)"] = config_ok
        current += 1

        # Step 2: Upload semua file ke storage bucket
        for local_path, remote_name in files_to_backup:
            if on_progress:
                on_progress(f"Upload {remote_name}...", current, total)
            ok = self.upload_file(local_path, remote_name)
            results[remote_name] = ok
            current += 1

        if on_progress:
            on_progress("Backup selesai!", total, total)

        success_count = sum(1 for v in results.values() if v)
        fail_count = sum(1 for v in results.values() if not v)

        return {
            "success": fail_count == 0,
            "message": f"Backup selesai: {success_count} berhasil, {fail_count} gagal.",
            "details": results,
            "success_count": success_count,
            "fail_count": fail_count,
        }

    def restore_all(self, on_progress: Optional[Any] = None) -> Dict[str, Any]:
        """Restore config.json dan seluruh file di folder cred/ dari Supabase.

        Args:
            on_progress: Optional callback(label: str, current: int, total: int).

        Returns:
            Dict berisi status restore: success count, fail count, detail.
        """
        if not self.client or not self.user:
            return {
                "success": False,
                "message": "Belum login. Silakan login terlebih dahulu.",
            }

        from core.config import config

        results: Dict[str, bool] = {}

        # Daftar file yang akan di-restore dari storage
        files_to_restore: list[tuple[str, str]] = [
            ("config.json", "config.json"),
        ]

        # File-file kredensial yang umum disimpan di cred/
        cred_files = [
            "cred/youtube_token.json",
            "cred/yt_cookies.txt",
            "cred/tiktok_cookies.txt",
            "cred/instagram_cookies.txt",
        ]
        for cf in cred_files:
            files_to_restore.append((cf, cf))

        # Tambahkan folder channels
        files_to_restore.append(("channels/channels.json", "channels/channels.json"))

        total = len(files_to_restore) + 1  # +1 untuk config table restore
        current = 0

        # Step 1: Restore config dari tabel user_configs
        if on_progress:
            on_progress("Restore config dari database...", current, total)

        cloud_config = self.sync_config_down()
        if cloud_config:
            config.update_from_dict(cloud_config)
            config.save_to_file()
            results["user_configs (database)"] = True
            log.info("Config berhasil di-restore dari tabel user_configs.")
        else:
            results["user_configs (database)"] = False
            log.warning("Tidak ada config ditemukan di tabel user_configs.")
        current += 1

        # Step 2: Download semua file dari storage bucket
        os.makedirs("cred", exist_ok=True)
        os.makedirs("channels", exist_ok=True)
        for remote_name, local_path in files_to_restore:
            if on_progress:
                on_progress(f"Download {remote_name}...", current, total)
            ok = self.download_file(remote_name, local_path)
            results[remote_name] = ok
            current += 1

        # Step 3: Secara dinamis restore file channel individual jika channels.json ada
        channels_file = "channels/channels.json"
        if os.path.exists(channels_file):
            try:
                from core.utils import read_json

                channels_data = read_json(channels_file)
                if isinstance(channels_data, list):
                    # Update total steps
                    total += len(channels_data)
                    for ch in channels_data:
                        ch_id = ch.get("id")
                        if ch_id:
                            ch_filename = f"channels/{ch_id}.json"
                            if on_progress:
                                on_progress(
                                    f"Download {ch_filename}...", current, total
                                )
                            ok = self.download_file(ch_filename, ch_filename)
                            results[ch_filename] = ok
                            current += 1
            except Exception as e_channels:
                log.warning(
                    f"Gagal memulihkan katalog channel individual: {e_channels}"
                )

        if on_progress:
            on_progress("Restore selesai!", total, total)

        # Reload config dari file yang baru didownload
        config.load_from_file()

        success_count = sum(1 for v in results.values() if v)
        fail_count = sum(1 for v in results.values() if not v)

        return {
            "success": True,
            "message": f"Restore selesai: {success_count} berhasil, {fail_count} gagal/tidak ditemukan.",
            "details": results,
            "success_count": success_count,
            "fail_count": fail_count,
        }

    def logout(self):
        if self.client:
            try:
                self.client.auth.sign_out()
                self.user = None
                # Hapus file session lokal
                session_file = "cred/supabase_session.json"
                if os.path.exists(session_file):
                    os.remove(session_file)
                    log.info("Session file dihapus.")
                log.info("User logged out.")
            except Exception as e:
                log.error(f"Logout failed: {e}")

    def is_logged_in(self) -> bool:
        """Cek apakah user sudah login dan session masih aktif."""
        return self.user is not None and self.client is not None

    def get_user_email(self) -> Optional[str]:
        """Mendapatkan email user yang sedang login."""
        if self.user and hasattr(self.user, "email"):
            return self.user.email
        return None

    def get_user_display_name(self) -> Optional[str]:
        """Mendapatkan nama tampilan user dari metadata."""
        if self.user and hasattr(self.user, "user_metadata"):
            metadata = self.user.user_metadata or {}
            return metadata.get("full_name") or metadata.get("name")
        return None

    def get_user_avatar_url(self) -> Optional[str]:
        """Mendapatkan URL avatar user dari metadata Google."""
        if self.user and hasattr(self.user, "user_metadata"):
            metadata = self.user.user_metadata or {}
            return metadata.get("avatar_url") or metadata.get("picture")
        return None


supabase_sync = SupabaseSyncManager()
