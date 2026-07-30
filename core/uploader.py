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
    def upload(self, file_path: str, metadata: Dict[str, Any]) -> UploadResult:
        """
        Uploads the given file to the platform.
        metadata contains keys like: 'title', 'description', 'privacy', 'tags'.
        """
        pass

class DummyUploader(BaseUploader):
    """
    A dummy uploader for testing the GUI integration before real platform APIs are implemented.
    """
    def __init__(self, platform_name: str):
        super().__init__(platform_name)
        
    def upload(self, file_path: str, metadata: Dict[str, Any]) -> UploadResult:
        # Simulate upload time
        time.sleep(2.0)
        return UploadResult(
            success=True,
            platform=self.platform_name,
            url=f"https://dummy.url/{self.platform_name.lower().replace(' ', '')}/12345"
        )

class YouTubeUploader(BaseUploader):
    def __init__(self):
        super().__init__("YouTube Shorts")
        
    def upload(self, file_path: str, metadata: Dict[str, Any]) -> UploadResult:
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
        token_file = "youtube_token.json"
        
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
            
        video_id = response.get("id")
        if video_id:
            url = f"https://youtube.com/shorts/{video_id}"
            return UploadResult(True, self.platform_name, url=url)
        else:
            return UploadResult(False, self.platform_name, error_msg="Video ID tidak ditemukan di response.")

class TikTokUploader(BaseUploader):
    def __init__(self):
        super().__init__("TikTok")
        
    def upload(self, file_path: str, metadata: Dict[str, Any]) -> UploadResult:
        from core.config import config
        from core.logger import log as logger
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
        except ImportError:
            return UploadResult(False, self.platform_name, error_msg="Modul playwright belum diinstal. Jalankan: pip install playwright && playwright install")
            
        session_id = config.tt_session
        if not session_id:
            return UploadResult(False, self.platform_name, error_msg="Session ID TikTok belum dikonfigurasi.")
            
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                
                # Set cookie sessionid
                context.add_cookies([{
                    'name': 'sessionid',
                    'value': session_id,
                    'domain': '.tiktok.com',
                    'path': '/'
                }])
                
                page = context.new_page()
                page.set_default_timeout(60000)
                
                logger.info("Membuka halaman upload TikTok...")
                page.goto("https://www.tiktok.com/creator-center/upload?from=upload")
                
                # Wait for file input and upload file
                logger.info("Menunggu elemen input file...")
                # Usually tiktok uses an iframe for the uploader, so we locate the file input
                # Try finding in page
                file_input = page.locator("input[type='file']").first
                file_input.wait_for(state="attached", timeout=30000)
                
                logger.info("Mengunggah file video...")
                file_input.set_input_files(file_path)
                
                # Wait for upload to complete
                # Usually there's an uploading indicator or the caption box becomes interactable
                logger.info("Menunggu video selesai diunggah...")
                # The editor for caption
                editor_selector = ".public-DraftEditor-content, .editor, div[contenteditable='true']"
                page.wait_for_selector(editor_selector, timeout=120000)
                
                # Fill caption
                title = metadata.get("title", "")
                caption = f"{title} {config.tt_caption}".strip()
                logger.info(f"Mengetik caption: {caption}")
                
                editor = page.locator(editor_selector).first
                editor.click()
                
                # Clear existing and type new
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(caption, delay=100)
                
                # Set privacy
                privacy = config.tt_privacy.lower()
                logger.info(f"Mengatur privasi ke: {config.tt_privacy}")
                
                # Find privacy dropdown, usually contains text 'Public' by default
                try:
                    privacy_dropdown = page.locator("div:has-text('Public')").locator("xpath=..").locator("div[role='combobox'], div[role='button']").first
                    if privacy_dropdown.count() > 0:
                        privacy_dropdown.click(timeout=5000)
                        
                        if "private" in privacy:
                            page.locator("div[role='option']:has-text('Private')").first.click(timeout=5000)
                        elif "friend" in privacy:
                            page.locator("div[role='option']:has-text('Friends')").first.click(timeout=5000)
                        else:
                            page.locator("div[role='option']:has-text('Public')").first.click(timeout=5000)
                except Exception as e:
                    logger.warning(f"Gagal mengatur privasi, menggunakan default: {str(e)}")
                
                # Wait a bit
                page.wait_for_timeout(2000)
                
                # Click post
                logger.info("Mengeklik tombol Post...")
                post_button = page.locator("button:has-text('Post'), div:has-text('Post')[role='button']").last
                post_button.click()
                
                # Wait for success dialog or redirection
                logger.info("Menunggu konfirmasi upload...")
                try:
                    # Look for confirmation modal or 'Manage your posts' text
                    page.wait_for_selector("div:has-text('Manage your posts')", timeout=30000)
                except PlaywrightTimeoutError:
                    pass
                    
                browser.close()
                
                return UploadResult(True, self.platform_name, url="https://www.tiktok.com/profile")
                
        except Exception as e:
            logger.error(f"TikTok Upload error: {str(e)}", exc_info=True)
            return UploadResult(False, self.platform_name, error_msg=f"Gagal upload ke TikTok: {str(e)}")
