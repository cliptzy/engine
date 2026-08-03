import os
import time
from typing import Dict, Any
from core.uploaders.base import BaseUploader, UploadResult

class TikTokUploader:
    def __init__(self):
        self.platform_name = "TikTok"
        self.tt_uploader = None
        
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        from core.config import config
        from core.logger import log as logger
        try:
            from tiktok_uploader.upload import TikTokUploader as TTUploader
        except ImportError:
            return UploadResult(False, self.platform_name, error_msg="Modul tiktok-uploader belum diinstal. Jalankan: pip install tiktok-uploader")
            
        cookie_path = config.tiktok.session
        if not cookie_path or not os.path.exists(cookie_path):
            return UploadResult(False, self.platform_name, error_msg="File cookie TikTok tidak ditemukan atau path belum diatur.")
            
        try:
            title = metadata.get("title", "")
            caption = f"{title} {config.tiktok.caption}".strip()
                
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
                    save_cookies(cookie_path, uploader.page.context.cookies()) # type: ignore
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
