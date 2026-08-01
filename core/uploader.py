import time
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class UploadResult:
    success: bool
    platform: str
    url: Optional[str] = None
    error_msg: Optional[str] = None

class BaseUploader(ABC):
    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    @abstractmethod
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        """
        Uploads the given file to the platform.
        metadata contains keys like: 'title', 'description', 'privacy', 'tags'.
        event_hook(kind: str, data: Any) is used to report progress or detailed logs.
        """
        pass

    def close(self):
        """Clean up resources (like browsers) if needed."""
        pass

class DummyUploader(BaseUploader):
    """
    A dummy uploader for testing the GUI integration before real platform APIs are implemented.
    """
    def __init__(self, platform_name: str):
        super().__init__(platform_name)
        
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        # Simulate upload time
        if event_hook:
            event_hook("log", f"[{self.platform_name}] Memulai simulasi upload...")
        time.sleep(2.0)
        return UploadResult(
            success=True,
            platform=self.platform_name,
            url=f"https://dummy.url/{self.platform_name.lower().replace(' ', '')}/12345"
        )

class YouTubeUploader(BaseUploader):
    def __init__(self):
        super().__init__("YouTube Shorts")
        
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        from core.config import config
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import json
        
        if not config.yt_client_id or not config.yt_client_secret:
            return UploadResult(False, self.platform_name, error_msg="Client ID atau Client Secret YouTube belum dikonfigurasi.")
            
        client_config = {
            "installed": {
                "client_id": config.yt_client_id,
                "project_id": "cliptzy-auto-upload",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": config.yt_client_secret,
                "redirect_uris": ["http://localhost"]
            }
        }
        
        scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        creds = None
        token_file = "cred/youtube_token.json"
        
        if os.path.exists(token_file):
            try:
                creds = Credentials.from_authorized_user_file(token_file, scopes)
            except Exception:
                creds = None
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            if not creds:
                flow = InstalledAppFlow.from_client_config(client_config, scopes)
                creds = flow.run_local_server(port=0)
                
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
                
        youtube = build("youtube", "v3", credentials=creds)
        
        # Prepare metadata
        title = metadata.get("title", "Untitled")
        description = metadata.get("description", "")
        tags_str = metadata.get("tags", "")
        tags_list = [t.strip().replace('#', '') for t in tags_str.split() if t.strip()]
        
        # Ensure #shorts is present for YouTube Shorts
        if "#shorts" not in description.lower() and "#shorts" not in title.lower():
            description += "\n#shorts"
            
        if len(title) > 100:
            title = title[:97] + "..."
            
        privacy = "public"
        if config.yt_visibility.lower() == "unlisted":
            privacy = "unlisted"
        elif config.yt_visibility.lower() == "private":
            privacy = "private"
            
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags_list,
                "categoryId": "24" # Entertainment
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False
            }
        }
        
        if "publish_at" in metadata:
            body["status"]["publishAt"] = metadata["publish_at"]
            body["status"]["privacyStatus"] = "private"
        
        
        media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/*")
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status and event_hook:
                prog = int(status.progress() * 100)
                event_hook("log", f"[YouTube] Progress Uploading Chunk: {prog}%")
            
        video_id = response.get("id")
        if video_id:
            url = f"https://youtube.com/shorts/{video_id}"
            return UploadResult(True, self.platform_name, url=url)
        else:
            return UploadResult(False, self.platform_name, error_msg="Video ID tidak ditemukan di response.")

class TikTokUploader(BaseUploader):
    def __init__(self):
        super().__init__("TikTok")
        self.tt_uploader = None
        
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        from core.config import config
        from core.logger import log as logger
        try:
            from tiktok_uploader.upload import TikTokUploader as TTUploader
        except ImportError:
            return UploadResult(False, self.platform_name, error_msg="Modul tiktok-uploader belum diinstal. Jalankan: pip install tiktok-uploader")
            
        cookie_path = config.tt_session
        if not cookie_path or not os.path.exists(cookie_path):
            return UploadResult(False, self.platform_name, error_msg="File cookie TikTok tidak ditemukan atau path belum diatur.")
            
        try:
            title = metadata.get("title", "")
            caption = f"{title} {config.tt_caption}".strip()
                
            if event_hook: event_hook("log", f"[TikTok] Memulai upload menggunakan tiktok-uploader dari file {cookie_path}...")
            logger.info(f"Mengunggah ke TikTok: {file_path}, caption: {caption}")
            
            # Use tiktok-uploader package and reuse instance
            if self.tt_uploader is None:
                self.tt_uploader = TTUploader(cookies=cookie_path, headless=False)
            
            uploader = self.tt_uploader
            
            import datetime
            schedule = None
            if "publish_at" in metadata:
                try:
                    # metadata["publish_at"] format: "YYYY-MM-DDTHH:MM:SS.000Z"
                    time_str = metadata["publish_at"].replace(".000Z", "").replace("Z", "")
                    schedule = datetime.datetime.fromisoformat(time_str)
                    if event_hook: event_hook("log", f"[TikTok] Menjadwalkan upload untuk {schedule}")
                except Exception as e:
                    logger.warning(f"Gagal memparsing jadwal: {e}")
            
            if schedule:
                # `tiktok_uploader` upload_video function with schedule
                success = uploader.upload_video(file_path, description=caption, schedule=schedule)
            else:
                success = uploader.upload_video(file_path, description=caption)

            time.sleep(3)
            
            if not success:
                err_msg = f"Gagal upload video ke TikTok."
                if event_hook: event_hook("log", f"[TikTok] ❌ {err_msg}")
                logger.error(err_msg)
                return UploadResult(False, self.platform_name, error_msg=err_msg)
            
            # Save updated cookies
            if hasattr(uploader, 'page') and uploader.page and hasattr(uploader.page, 'context'):
                try:
                    from tiktok_uploader.auth import save_cookies
                    save_cookies(cookie_path, uploader.page.context.cookies())
                    if event_hook: event_hook("log", "[TikTok] Cookie berhasil diperbarui secara otomatis.")
                except Exception as e:
                    logger.warning(f"Gagal memperbarui cookie TikTok: {e}")

            if event_hook: event_hook("log", "[TikTok] ✅ Upload berhasil!")
            return UploadResult(True, self.platform_name, url="https://www.tiktok.com/profile")
            
        except Exception as e:
            logger.error(f"TikTok Upload error: {str(e)}", exc_info=True)
            return UploadResult(False, self.platform_name, error_msg=f"Gagal upload ke TikTok: {str(e)}")

    def close(self):
        if self.tt_uploader is not None:
            try:
                self.tt_uploader.close()
            except Exception:
                pass
            self.tt_uploader = None

class InstagramUploader(BaseUploader):
    def __init__(self):
        super().__init__("Instagram Reels")
        
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        from core.config import config
        from core.logger import log as logger
        import json
        import os
        try:
            from instagrapi import Client
        except ImportError:
            return UploadResult(False, self.platform_name, error_msg="Modul instagrapi belum diinstal. Jalankan: pip install instagrapi")
            
        if not config.ig_session or not os.path.exists(config.ig_session):
            return UploadResult(False, self.platform_name, error_msg="File cookie Instagram belum diisi atau tidak ditemukan.")
            
        try:
            session_id = ""
            with open(config.ig_session, 'r', encoding='utf-8') as f:
                content = f.read()
                
            try:
                cookies_json = json.loads(content)
                for cookie in cookies_json:
                    if cookie.get('name') == 'sessionid' and 'instagram' in cookie.get('domain', ''):
                        session_id = cookie.get('value', '')
                        break
            except Exception:
                for line in content.splitlines():
                    if line.startswith('#') or not line.strip(): continue
                    parts = line.split('\t')
                    if len(parts) >= 7 and 'instagram.com' in parts[0] and parts[5] == 'sessionid':
                        session_id = parts[6].strip()
                        break

            if not session_id:
                return UploadResult(False, self.platform_name, error_msg="Tidak ditemukan cookie sessionid di dalam file tersebut.")
                
            title = metadata.get("title", "")
            caption = f"{title} {config.ig_caption}".strip()
                
            if event_hook: event_hook("log", f"[Instagram] Memulai login via sessionid...")
            
            cl = Client()
            cl.login_by_sessionid(session_id)
            
            if event_hook: event_hook("log", f"[Instagram] Berhasil login. Memulai upload Reels...")
            logger.info(f"Mengunggah ke Instagram: {file_path}, caption: {caption}")
            
            thumb_path = f"{file_path}.jpg"
            if not os.path.exists(thumb_path):
                import subprocess
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", "00:00:01", "-i", file_path, "-vframes", "1", "-q:v", "2", thumb_path],
                        check=True
                    )
                except Exception as e:
                    logger.warning(f"Gagal generate thumbnail dengan ffmpeg: {e}")

            media = cl.clip_upload(
                file_path,
                caption=caption,
                thumbnail=thumb_path if os.path.exists(thumb_path) else None
            )
            
            if not media:
                err_msg = f"Gagal upload video ke Instagram Reels."
                if event_hook: event_hook("log", f"[Instagram] ❌ {err_msg}")
                logger.error(err_msg)
                return UploadResult(False, self.platform_name, error_msg=err_msg)
            
            # Save updated cookies using instagrapi format
            try:
                new_cookies = []
                for name, value in cl.get_settings().get("cookies", {}).items():
                    new_cookies.append({
                        "name": name,
                        "value": value,
                        "domain": ".instagram.com",
                        "path": "/"
                    })
                from core.utils import write_json
                if write_json(config.ig_session, new_cookies, indent=2):
                    if event_hook: event_hook("log", "[Instagram] Cookie berhasil diperbarui secara otomatis.")
            except Exception as e:
                logger.warning(f"Gagal memperbarui cookie Instagram: {e}")

            media_url = f"https://www.instagram.com/reel/{media.code}/"
            if event_hook: event_hook("log", f"[Instagram] ✅ Upload berhasil! {media_url}")
            return UploadResult(True, self.platform_name, url=media_url)
            
        except Exception as e:
            logger.error(f"Instagram Upload error: {str(e)}", exc_info=True)
            return UploadResult(False, self.platform_name, error_msg=f"Gagal upload ke Instagram: {str(e)}")
