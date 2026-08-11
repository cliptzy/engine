from core.uploaders.base import BaseUploader
from core.uploaders.dummy import DummyUploader
from core.uploaders.instagram import InstagramUploader
from core.uploaders.tiktok import TikTokUploader
from core.uploaders.youtube import YouTubeUploader


class UploaderFactory:
    @staticmethod
    def create(platform: str) -> BaseUploader:
        platform = platform.lower()
        if "youtube" in platform:
            return YouTubeUploader()
        elif "tiktok" in platform:
            return TikTokUploader()
        elif "instagram" in platform:
            return InstagramUploader()
        elif "dummy" in platform:
            return DummyUploader(platform.capitalize())
        else:
            raise ValueError(f"Uploader platform tidak didukung: {platform}")
