import time
from typing import Dict, Any, Optional
from core.uploaders.base import BaseUploader, UploadResult
from core.logger import log

class DummyUploader:
    """
    A dummy uploader for testing the GUI integration before real platform APIs are implemented.
    """
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        
    def upload(self, file_path: str, metadata: Dict[str, Any], event_hook=None) -> UploadResult:
        # Simulate upload time
        if event_hook:
            log.info( f"[{self.platform_name}] Memulai simulasi upload...")
        time.sleep(2.0)
        return UploadResult(
            success=True,
            platform=self.platform_name,
            url=f"https://dummy.url/{self.platform_name.lower().replace(' ', '')}/12345"
        )
        
    def close(self):
        pass
