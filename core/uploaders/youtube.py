import os
from typing import Dict, Any
from core.uploaders.base import BaseUploader, UploadResult

class YouTubeUploader:
    def __init__(self):
        self.platform_name = "YouTube Shorts"
        
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        from core.config import config
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        
        if not config.youtube.client_id or not config.youtube.client_secret:
            return UploadResult(False, self.platform_name, error_msg="Client ID atau Client Secret YouTube belum dikonfigurasi.")
            
        client_config = {
            "installed": {
                "client_id": config.youtube.client_id,
                "project_id": "cliptzy-auto-upload",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": config.youtube.client_secret,
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
        tags_raw = metadata.get("tags", "")
        if isinstance(tags_raw, list):
            tags_list = [t.strip().replace('#', '') for t in tags_raw if t.strip()]
        else:
            tags_list = [t.strip().replace('#', '') for t in tags_raw.split() if t.strip()]
        
        # Ensure #shorts is present for YouTube Shorts
        if "#shorts" not in description.lower() and "#shorts" not in title.lower():
            description += "\n#shorts"
            
        if len(title) > 100:
            title = title[:97] + "..."
            
        privacy = "public"
        if config.youtube.visibility.lower() == "unlisted":
            privacy = "unlisted"
        elif config.youtube.visibility.lower() == "private":
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

    def close(self):
        pass
