import os
import json
from typing import Optional, Dict, Any
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
            from supabase import create_client, Client
            self.client = create_client(supabase_url, supabase_key)
            log.info("Supabase client initialized.")
            self.load_session()
        except ImportError:
            log.warning("Package 'supabase' is not installed. Run 'pip install supabase'.")
            self.client = None
        except Exception as e:
            log.error(f"Failed to initialize Supabase client: {e}")
            self.client = None

    def login_with_google(self) -> bool:
        if not self.client:
            log.warning("Supabase client not initialized.")
            return False
            
        import webbrowser
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from urllib.parse import urlparse, parse_qs
        import threading
        
        callback_port = 54321
        redirect_uri = f"http://localhost:{callback_port}"
        
        # We will store the extracted auth code here
        auth_code = [None]
        
        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                
                # Check for error
                if "error" in query_params:
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h1>Login Gagal</h1><p>Terjadi kesalahan atau otorisasi dibatalkan.</p>")
                    return
                
                # PKCE flow returns 'code'
                if "code" in query_params:
                    auth_code[0] = query_params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h1>Login Berhasil!</h1><p>Anda dapat menutup jendela ini dan kembali ke aplikasi Cliptzy.</p>")
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
                pass # suppress console logging for the server

        try:
            # 1. Start local server
            server = HTTPServer(('localhost', callback_port), OAuthCallbackHandler)
            
            # 2. Get OAuth URL with YouTube scope
            res = self.client.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": redirect_uri,
                    "skip_browser_redirect": True,
                    "scopes": "https://www.googleapis.com/auth/youtube.upload"
                }
            })
            
            if not res or not hasattr(res, 'url'):
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
                session_res = self.client.auth.exchange_code_for_session({"auth_code": auth_code[0]})
                if session_res and session_res.user:
                    self.user = session_res.user
                    log.info(f"User logged in via Google: {self.user.id}")
                    
                    # The bucket 'user_files' must be created manually or via SQL migration beforehand.
                    
                    # Save session to file
                    import json
                    import os
                    os.makedirs("cred", exist_ok=True)
                    session_data = {
                        "access_token": session_res.session.access_token,
                        "refresh_token": session_res.session.refresh_token
                    }
                    with open("cred/supabase_session.json", "w") as f:
                        json.dump(session_data, f)
                    
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
        import os, json
        session_file = "cred/supabase_session.json"
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                    access_token = data.get("access_token")
                    refresh_token = data.get("refresh_token")
                    if access_token and refresh_token:
                        res = self.client.auth.set_session(access_token, refresh_token)
                        if res and res.user:
                            self.user = res.user
                            log.info(f"Session restored for user: {self.user.id}")
                            return True
            except Exception as e:
                log.warning(f"Gagal memuat sesi sebelumnya: {e}")
        return False

    def logout(self):
        if self.client:
            try:
                self.client.auth.sign_out()
                self.user = None
                log.info("User logged out.")
            except Exception as e:
                log.error(f"Logout failed: {e}")

    def get_user_id(self) -> Optional[str]:
        if self.user:
            return self.user.id
        return None

    def sync_config_up(self, config_dict: dict) -> bool:
        if not self.client or not self.user:
            return False
        if not config_dict:
            log.warning("Config kosong, dibatalkan untuk sync up agar tidak merusak data cloud.")
            return False
            
        try:
            data = {
                "user_id": self.user.id,
                "config": config_dict
            }
            res = self.client.table("user_configs").upsert(data, on_conflict="user_id").execute()
            log.info("Config synced up to Supabase.")
            return True
        except Exception as e:
            log.error(f"Failed to sync config up: {e}")
            return False

    def sync_config_down(self) -> Optional[Dict[str, Any]]:
        if not self.client or not self.user:
            return None
        try:
            res = self.client.table("user_configs").select("config").eq("user_id", self.user.id).execute()
            if res.data and len(res.data) > 0:
                log.info("Config synced down from Supabase.")
                return res.data[0]["config"]
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
                log.warning(f"File JSON tidak valid {local_path}, dilewati dari upload: {e}")
                return False

        try:
            bucket_path = f"{self.user.id}/{remote_filename}"
            with open(local_path, "rb") as f:
                res = self.client.storage.from_("user_files").upload(
                    file=f,
                    path=bucket_path,
                    file_options={"upsert": "true"}
                )
            log.info(f"File {local_path} uploaded to {bucket_path}")
            return True
        except Exception as e:
            log.warning(f"Failed to upload file {local_path}: {e}")
            return False

    def download_file(self, remote_filename: str, local_path: str) -> bool:
        if not self.client or not self.user:
            return False
        try:
            bucket_path = f"{self.user.id}/{remote_filename}"
            res = self.client.storage.from_("user_files").download(bucket_path)
            
            # Pengecekan ukuran dari memori sebelum ditulis
            if not res or len(res) == 0:
                log.warning(f"File hasil download {bucket_path} kosong, dibatalkan (tidak menimpa lokal).")
                return False
                
            # Pengecekan validitas JSON jika ekstensi json
            if remote_filename.lower().endswith(".json"):
                import json
                try:
                    json.loads(res.decode("utf-8"))
                except Exception as e:
                    log.warning(f"Isi file {bucket_path} bukan JSON yang valid, dibatalkan: {e}")
                    return False
            
            with open(local_path, "wb") as f:
                f.write(res)
            log.info(f"File {bucket_path} downloaded to {local_path}")
            return True
        except Exception as e:
            log.warning(f"Failed to download file {bucket_path}: {e}")
            return False

supabase_sync = SupabaseSyncManager()
